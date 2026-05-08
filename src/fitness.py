"""
Fitness do AG via round-robin completo (C(5,2)=10 matchups × SIMS_PER_MATCHUP).

    fitness = -(LAMBDA_SPECIALIZATION × specialization_penalty
              + LAMBDA_DRIFT          × drift_penalty
              + LAMBDA_DOMINANCE      × dominance_penalty)

NSGA-II usa apenas (dominance_penalty, drift_penalty) sem ponderação.
"""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Tuple

from .combat import simulate_combat
from .config import (
    ATTRIBUTE_BOUNDS,
    LAMBDA_DOMINANCE,
    LAMBDA_DRIFT,
    LAMBDA_SPECIALIZATION,
    MATCHUP_THRESHOLD,
    N_WORKERS,
    SIMS_PER_MATCHUP,
)
from .individual import Individual

_ATTR_MAXES: List[float] = [hi for _, hi in ATTRIBUTE_BOUNDS]


# ─────────────────────────────────────────────────────────────────────────────
# Resultado detalhado
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FitnessDetail:
    fitness:                float
    winrates:               List[float]
    specialization_penalty: float
    drift_penalty:          float = 0.0
    archetype_deviations:   List[float] = field(default_factory=list)
    matchup_winrates:       Dict[Tuple[int, int], float] = field(default_factory=dict)
    matchup_scores:         Dict[Tuple[int, int], float] = field(default_factory=dict)
    dominance_penalty:      float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Métricas por personagem
# ─────────────────────────────────────────────────────────────────────────────


def _specialization(char) -> float:
    norm = [a / m for a, m in zip(char.attributes, _ATTR_MAXES)]
    return max(norm) - min(norm)


def _archetype_deviation(char) -> float:
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


def _dominance_penalty(matchup_scores: Dict[Tuple[int, int], float]) -> float:
    scale = 0.5 - MATCHUP_THRESHOLD
    excesses = [
        max(0.0, (abs(s - 0.5) - MATCHUP_THRESHOLD) / scale)
        for s in matchup_scores.values()
    ]
    return math.sqrt(sum(e * e for e in excesses) / len(excesses))


# ─────────────────────────────────────────────────────────────────────────────
# Round-robin
# ─────────────────────────────────────────────────────────────────────────────


def _run_round_robin(
    chars: List, sims: int
) -> Tuple[
    List[int],
    List[int],
    Dict[Tuple[int, int], int],
    Dict[Tuple[int, int], float],
]:
    n = len(chars)
    wins        = [0] * n
    total_games = [0] * n
    matchup_wins:   Dict[Tuple[int, int], int]   = {}
    matchup_scores: Dict[Tuple[int, int], float] = {}

    for i, j in combinations(range(n), 2):
        matchup_wins[(i, j)] = 0
        score_sum = 0.0
        for _ in range(sims):
            result = simulate_combat(chars[i], chars[j])
            if result.winner == 0:
                wins[i] += 1
                matchup_wins[(i, j)] += 1
            else:
                wins[j] += 1
            total_games[i] += 1
            total_games[j] += 1

            if result.ko:
                score_sum += 1.0 if result.winner == 0 else 0.0
            else:
                hp_pct_i = result.hp_remaining[0] / chars[i].hp
                hp_pct_j = result.hp_remaining[1] / chars[j].hp
                total_pct = hp_pct_i + hp_pct_j
                score_sum += hp_pct_i / total_pct if total_pct > 0 else 0.5

        matchup_scores[(i, j)] = score_sum / sims

    return wins, total_games, matchup_wins, matchup_scores


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_detail_n(individual: Individual, sims: int) -> FitnessDetail:
    chars = individual.characters
    n     = len(chars)

    wins, total_games, matchup_wins, matchup_scores = _run_round_robin(chars, sims)

    winrates         = [wins[i] / total_games[i] for i in range(n)]
    matchup_winrates = {key: v / sims for key, v in matchup_wins.items()}

    specialization_penalty = 1.0 - sum(_specialization(c) for c in chars) / n
    archetype_deviations   = [_archetype_deviation(c) for c in chars]
    drift_penalty          = sum(archetype_deviations) / n
    dominance_pen          = _dominance_penalty(matchup_scores)

    fitness = -(
        LAMBDA_SPECIALIZATION * specialization_penalty
        + LAMBDA_DRIFT        * drift_penalty
        + LAMBDA_DOMINANCE    * dominance_pen
    )

    return FitnessDetail(
        fitness=fitness,
        winrates=winrates,
        specialization_penalty=specialization_penalty,
        drift_penalty=drift_penalty,
        archetype_deviations=archetype_deviations,
        matchup_winrates=matchup_winrates,
        matchup_scores=matchup_scores,
        dominance_penalty=dominance_pen,
    )


def evaluate_detail(individual: Individual) -> FitnessDetail:
    return evaluate_detail_n(individual, SIMS_PER_MATCHUP)


def evaluate(individual: Individual) -> float:
    if individual.is_evaluated:
        return individual.fitness
    detail = evaluate_detail(individual)
    individual.fitness = detail.fitness
    return detail.fitness


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação em lote
# ─────────────────────────────────────────────────────────────────────────────


def _eval_worker(ind: Individual) -> float:
    return evaluate_detail(ind).fitness


def evaluate_population(population: List[Individual]) -> None:
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


# ─────────────────────────────────────────────────────────────────────────────
# NSGA-II — avaliação multi-objetivo
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_objectives(individual: Individual) -> Tuple[float, float]:
    if individual.objectives is not None:
        return individual.objectives
    detail = evaluate_detail(individual)
    objs = (detail.dominance_penalty, detail.drift_penalty)
    individual.objectives = objs
    return objs
