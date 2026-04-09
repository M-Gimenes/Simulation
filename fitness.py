"""
Função de fitness para o AG.

Avaliação via round-robin completo:
  - C(5,2) = 10 matchups únicos por indivíduo
  - Cada matchup rodado SIMS_PER_MATCHUP vezes para estabilizar o winrate
  - Winrate de cada personagem = vitórias / partidas_totais (4 oponentes × SIMS)

Fitness:
    balance_error  = mean(|winrate_i - 0.5|)          para cada personagem i
    attribute_cost = 1 - mean_specialization           sobre todos os personagens
    drift_penalty  = mean(archetype_deviation_i)       sobre todos os personagens
    fitness = (1 - balance_error) - LAMBDA * attribute_cost - LAMBDA_DRIFT * drift_penalty

  Specialization de um personagem = max(attrs_norm) - min(attrs_norm)
    - 0.0 = todos os atributos idênticos (super-herói homogêneo ou zero-herói)
    - 1.0 = máxima diferença entre maior e menor atributo (altamente especializado)

  attribute_cost = 0.0 → todos muito especializados (desejável)
  attribute_cost = 1.0 → todos homogêneos (penalizado)

  archetype_deviation_i = distância Euclidiana normalizada ao perfil canônico
    - 0.0 = idêntico ao canônico
    - 1.0 = maximamente distante do canônico

  LAMBDA_DRIFT controla o trade-off central do TCC:
    - 0.0 → evolução completamente livre; o AG pode redesenhar os personagens
            arbitrariamente para atingir equilíbrio (homogeneização possível)
    - alto → forte âncora ao canônico; preservação forçada, pode impedir convergência
    - médio → o AG evolui livremente mas paga custo por se afastar da identidade;
              equilíbrio e preservação competem — resultado mensurável e analisável
"""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from typing import List

from combat import simulate_combat
from config import ATTRIBUTE_BOUNDS, LAMBDA, LAMBDA_DRIFT, N_WORKERS, SIMS_PER_MATCHUP
from individual import Individual

# Máximos por atributo para normalização — escala de cada gene para [0, 1].
# HP tem escala própria (0–2000); demais atributos ficam em (0–100).
_ATTR_MAXES = [b[1] for b in ATTRIBUTE_BOUNDS]


# ─────────────────────────────────────────────────────────────────────────────
# Resultado detalhado (útil para logging e análise)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FitnessDetail:
    fitness: float
    winrates: List[float]              # winrate de cada personagem (ordem ARCHETYPE_ORDER)
    balance_error: float
    attribute_cost: float
    drift_penalty: float = 0.0        # mean(archetype_deviations) — entra no fitness via LAMBDA_DRIFT
    archetype_deviations: List[float] = field(default_factory=list)
    # distância normalizada de cada personagem ao canônico (0=idêntico, 1=máximo possível)


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(individual: Individual) -> float:
    """
    Calcula o fitness do indivíduo via round-robin completo.
    Armazena o resultado em individual.fitness e retorna o valor.
    Não reavalia se individual.is_evaluated == True.
    """
    if individual.is_evaluated:
        return individual.fitness

    detail = evaluate_detail(individual)
    individual.fitness = detail.fitness
    return detail.fitness


def evaluate_detail(individual: Individual) -> FitnessDetail:
    """
    Versão completa: retorna FitnessDetail com winrates por personagem.
    Usa SIMS_PER_MATCHUP. Sempre reavalia (ignora cache de fitness).
    """
    return evaluate_detail_n(individual, SIMS_PER_MATCHUP)


def _compute_archetype_deviations(individual: Individual) -> List[float]:
    """
    Distância normalizada de cada personagem em relação ao seu perfil canônico.

    Para cada personagem: distância Euclidiana no espaço de genes normalizado,
    dividida pela raiz do número de genes (escala: 0 = idêntico, 1 = oposto máximo).

    Atributos normalizados por 100; pesos já estão em [0,1].
    """
    deviations = []
    for char in individual.characters:
        attr_sq = sum(
            ((a - c) / m) ** 2
            for a, c, m in zip(char.attributes, char.archetype.initial_attributes, _ATTR_MAXES)
        )
        weight_sq = sum(
            (w - c) ** 2
            for w, c in zip(char.weights, char.archetype.initial_weights)
        )
        n_genes = len(char.attributes) + len(char.weights)
        deviations.append(math.sqrt((attr_sq + weight_sq) / n_genes))
    return deviations


def evaluate_detail_n(individual: Individual, sims: int) -> FitnessDetail:
    """
    Igual a evaluate_detail mas com número de simulações configurável.
    Usado para confirmação de convergência com mais sims (menos ruído).
    """
    chars = individual.characters
    n = len(chars)

    wins        = [0] * n
    total_games = [0] * n

    # Round-robin: C(n,2) = 10 matchups únicos
    for i, j in combinations(range(n), 2):
        for _ in range(sims):
            result = simulate_combat(chars[i], chars[j])
            if result.winner == 0:
                wins[i] += 1
            else:
                wins[j] += 1
            total_games[i] += 1
            total_games[j] += 1

    # Winrate por personagem
    winrates = [wins[i] / total_games[i] for i in range(n)]

    # Balance error: desvio médio de cada winrate em relação a 0.5
    balance_error = sum(abs(wr - 0.5) for wr in winrates) / n

    # Attribute cost baseado em especialização por personagem.
    #
    # specialization_i = max(attrs_norm) - min(attrs_norm)  ∈ [0, 1]
    #   - 0.0: todos os atributos idênticos (super-herói ou zero-herói homogêneo)
    #   - 1.0: máxima diferença interno (personagem altamente especializado)
    #
    # attribute_cost = 1 - mean(specialization_i)
    #   - 0.0: arquétipos muito especializados → sem penalidade
    #   - 1.0: todos homogêneos → penalidade máxima
    #
    # Isso desincentiva homogeneização (o antigo ótimo degenerado com atributos
    # baixos uniformes) sem bloquear valores altos quando são a identidade do arquétipo.
    per_char_spec = []
    for char in chars:
        norm = [a / m for a, m in zip(char.attributes, _ATTR_MAXES)]
        per_char_spec.append(max(norm) - min(norm))
    attribute_cost = 1.0 - (sum(per_char_spec) / len(per_char_spec))

    # Desvio arquetípico: distância normalizada de cada personagem ao seu canônico.
    # Entra no fitness como penalidade suave controlada por LAMBDA_DRIFT.
    # Com LAMBDA_DRIFT=0.0, comportamento idêntico à versão sem âncora.
    archetype_deviations = _compute_archetype_deviations(individual)
    drift_penalty = sum(archetype_deviations) / len(archetype_deviations)

    fitness = (1.0 - balance_error) - LAMBDA * attribute_cost - LAMBDA_DRIFT * drift_penalty

    return FitnessDetail(
        fitness=fitness,
        winrates=winrates,
        balance_error=balance_error,
        attribute_cost=attribute_cost,
        drift_penalty=drift_penalty,
        archetype_deviations=archetype_deviations,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação em lote (população inteira)
# ─────────────────────────────────────────────────────────────────────────────

def _eval_worker(ind: Individual) -> float:
    """Worker para avaliação paralela — roda em processo separado."""
    return evaluate_detail(ind).fitness


def evaluate_population(population: List[Individual]) -> None:
    """
    Avalia todos os indivíduos não avaliados da população.

    Com N_WORKERS != 1, usa ProcessPoolExecutor para avaliar em paralelo,
    aproveitando todos os núcleos da CPU (speedup ~= número de núcleos).
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
