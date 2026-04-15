"""
Função de fitness para o AG.

Avaliação via round-robin completo:
  C(5,2) = 10 matchups × SIMS_PER_MATCHUP simulações por indivíduo.

Fórmula:
  fitness = (1 - balance_error)
          - LAMBDA         * attribute_cost
          - LAMBDA_DRIFT   * drift_penalty
          - LAMBDA_MATCHUP * matchup_dominance_penalty

Componentes:
  balance_error             = mean(|wr_i - 0.5|)
  attribute_cost            = 1 - mean(specialization_i)
  drift_penalty             = mean(archetype_deviation_i)
  matchup_dominance_penalty = max(excess_ij) sobre os 10 pares
"""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from statistics import mean
from typing import Dict, List, Tuple

from combat import simulate_combat
from config import (
    ATTRIBUTE_BOUNDS,
    BALANCE_MODE,
    LAMBDA,
    LAMBDA_DRIFT,
    LAMBDA_MATCHUP,
    MATCHUP_THRESHOLD,
    N_WORKERS,
    SIMS_PER_MATCHUP,
)
from individual import Individual

assert BALANCE_MODE in ("matchup", "aggregate"), f"BALANCE_MODE inválido: {BALANCE_MODE!r}"

# Teto de cada atributo — normaliza genes para [0, 1].
_ATTR_MAXES: List[float] = [hi for _, hi in ATTRIBUTE_BOUNDS]


# ─────────────────────────────────────────────────────────────────────────────
# Resultado detalhado
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FitnessDetail:
    """Resultado completo da avaliação de um indivíduo."""

    fitness:                   float
    winrates:                  List[float]                    # WR agregado por personagem (ordem ARCHETYPE_ORDER)
    balance_error:             float                          # mean(|wr_i - 0.5|)
    attribute_cost:            float                          # 1 - mean(specialization_i)
    drift_penalty:             float = 0.0                   # mean(archetype_deviation_i)
    archetype_deviations:      List[float] = field(default_factory=list)
    matchup_winrates:          Dict[Tuple[int, int], float] = field(default_factory=dict)  # (i,j) → WR de i, i < j
    matchup_dominance_penalty: float = 0.0                   # max(excess_ij) normalizado em [0, 1]


# ─────────────────────────────────────────────────────────────────────────────
# Métricas por personagem
# ─────────────────────────────────────────────────────────────────────────────


def _specialization(char) -> float:
    """
    Dispersão interna dos atributos normalizados: max − min ∈ [0, 1].

    0.0 → atributos homogêneos (sem identidade).
    1.0 → máxima diferença interna (altamente especializado).
    """
    norm = [a / m for a, m in zip(char.attributes, _ATTR_MAXES)]
    return max(norm) - min(norm)


def _archetype_deviation(char) -> float:
    """
    Distância Euclidiana normalizada ao perfil canônico ∈ [0, 1].

    0.0 → idêntico ao canônico; 1.0 → maximamente distante.
    Atributos normalizados pelo teto; pesos já estão em [0, 1].
    """
    attr_sq = sum(
        ((a - c) / m) ** 2
        for a, c, m in zip(char.attributes, char.archetype.initial_attributes, _ATTR_MAXES)
    )
    weight_sq = sum(
        (w - c) ** 2
        for w, c in zip(char.weights, char.archetype.initial_weights)
    )
    n_genes = len(char.attributes) + len(char.weights)
    return math.sqrt((attr_sq + weight_sq) / n_genes)


def _matchup_dominance(matchup_winrates: Dict[Tuple[int, int], float]) -> float:
    """
    Penalidade do pior matchup: max(excess_ij) normalizado em [0, 1].

    Usa max (não mean) para que um único matchup dominante force correção
    sem ser diluído pelos demais pares.
    """
    scale = 0.5 - MATCHUP_THRESHOLD
    return mean(
        max(0.0, (abs(wr - 0.5) - MATCHUP_THRESHOLD) / scale)
        for wr in matchup_winrates.values()
    )


# ─────────────────────────────────────────────────────────────────────────────
# Round-robin
# ─────────────────────────────────────────────────────────────────────────────


def _run_round_robin(
    chars: List, sims: int
) -> Tuple[List[int], List[int], Dict[Tuple[int, int], int]]:
    """
    Executa C(n,2) matchups × sims simulações cada.

    Retorna:
      wins         — vitórias acumuladas por personagem
      total_games  — partidas totais por personagem
      matchup_wins — vitórias de i no head-to-head (i, j), i < j
    """
    n = len(chars)
    wins        = [0] * n
    total_games = [0] * n
    matchup_wins: Dict[Tuple[int, int], int] = {}

    for i, j in combinations(range(n), 2):
        matchup_wins[(i, j)] = 0
        for _ in range(sims):
            result = simulate_combat(chars[i], chars[j])
            if result.winner == 0:
                wins[i] += 1
                matchup_wins[(i, j)] += 1
            else:
                wins[j] += 1
            total_games[i] += 1
            total_games[j] += 1

    return wins, total_games, matchup_wins


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_detail_n(individual: Individual, sims: int) -> FitnessDetail:
    """Avalia o indivíduo com `sims` simulações por matchup."""
    chars = individual.characters
    n     = len(chars)

    wins, total_games, matchup_wins = _run_round_robin(chars, sims)

    winrates         = [wins[i] / total_games[i] for i in range(n)]
    matchup_winrates = {key: v / sims for key, v in matchup_wins.items()}

    if BALANCE_MODE == "matchup":
        balance_error = sum(abs(wr - 0.5) for wr in matchup_winrates.values()) / len(matchup_winrates)
    else:
        balance_error = sum(abs(wr - 0.5) for wr in winrates) / n
    attribute_cost            = 1.0 - sum(_specialization(c) for c in chars) / n
    archetype_deviations      = [_archetype_deviation(c) for c in chars]
    drift_penalty             = sum(archetype_deviations) / n
    matchup_dominance_penalty = _matchup_dominance(matchup_winrates)

    fitness = (
        (1.0 - balance_error)
        - LAMBDA         * attribute_cost
        - LAMBDA_DRIFT   * drift_penalty
        - LAMBDA_MATCHUP * matchup_dominance_penalty
    )

    return FitnessDetail(
        fitness=fitness,
        winrates=winrates,
        balance_error=balance_error,
        attribute_cost=attribute_cost,
        drift_penalty=drift_penalty,
        archetype_deviations=archetype_deviations,
        matchup_winrates=matchup_winrates,
        matchup_dominance_penalty=matchup_dominance_penalty,
    )


def evaluate_detail(individual: Individual) -> FitnessDetail:
    """Avalia com SIMS_PER_MATCHUP simulações. Sempre reavalia (ignora cache)."""
    return evaluate_detail_n(individual, SIMS_PER_MATCHUP)


def evaluate(individual: Individual) -> float:
    """
    Calcula e cacheia o fitness do indivíduo. Retorna o valor.
    Não reavalia se individual.is_evaluated == True.
    """
    if individual.is_evaluated:
        return individual.fitness
    detail = evaluate_detail(individual)
    individual.fitness = detail.fitness
    return detail.fitness


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação em lote
# ─────────────────────────────────────────────────────────────────────────────


def _eval_worker(ind: Individual) -> float:
    """Worker para avaliação paralela — roda em processo separado."""
    return evaluate_detail(ind).fitness


def evaluate_population(population: List[Individual]) -> None:
    """
    Avalia todos os indivíduos não avaliados da população.
    Usa ProcessPoolExecutor quando N_WORKERS != 1 (speedup ≈ nº de núcleos).
    """
    unevaluated = [ind for ind in population if not ind.is_evaluated]
    if not unevaluated:
        return

    if N_WORKERS == 1 or len(unevaluated) == 1:
        for ind in unevaluated:
            evaluate(ind)
        return

    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        fitnesses = list(executor.map(_eval_worker, unevaluated))

    for ind, fit in zip(unevaluated, fitnesses):
        ind.fitness = fit
