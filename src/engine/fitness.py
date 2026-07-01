"""
Fitness do AG via round-robin completo (C(5,2)=10 matchups × SIMS_PER_MATCHUP).

    fitness = -(LAMBDA_DRIFT     × drift_penalty
              + LAMBDA_DOMINANCE × dominance_penalty)

Os mesmos dois termos do NSGA-II — lá como objetivos de Pareto (sem ponderação),
aqui como soma ponderada. O escalar é um ponto do trade-off que o NSGA-II mapeia.
"""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from .combat import seed_combat, simulate_combat
from .config import (
    ATTRIBUTE_BOUNDS,
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
    GLOBAL_CONVERGENCE_THRESHOLD,
    LAMBDA_DOMINANCE,
    LAMBDA_DRIFT,
    MATCHUP_FLOOR,
    MATCHUP_THRESHOLD,
    MATCHUP_WR_CAP,
    N_WORKERS,
    SIMS_PER_MATCHUP,
)
from .individual import Individual

_ATTR_MAXES: List[float] = [hi for _, hi in ATTRIBUTE_BOUNDS]


# ─────────────────────────────────────────────────────────────────────────────
# Reprodutibilidade — Common Random Numbers (reset ao seed-base)
# ─────────────────────────────────────────────────────────────────────────────
# Quando um seed-base é definido (via set_seed_base), toda avaliação reseta o RNG
# do combate ao MESMO _SEED_BASE antes do round-robin. Assim todo indivíduo é
# avaliado sob o mesmo stream de RNG (Common Random Numbers): a diferença de
# fitness reflete genes, não sorteio → seleção menos enganada e paisagem mais lisa.
# Reprodutível independente de qual worker/agendamento avalia.

_SEED_BASE: Optional[int] = None


def set_seed_base(seed: Optional[int]) -> None:
    """Define o seed-base do processo. None desliga a semeadura (usa entropia)."""
    global _SEED_BASE
    _SEED_BASE = seed


def get_seed_base() -> Optional[int]:
    return _SEED_BASE


# ─────────────────────────────────────────────────────────────────────────────
# Resultado detalhado
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FitnessDetail:
    fitness:                float
    winrates:               List[float]
    drift_penalty:          float = 0.0
    archetype_deviations:   List[float] = field(default_factory=list)
    matchup_winrates:       Dict[Tuple[int, int], float] = field(default_factory=dict)
    matchup_scores:         Dict[Tuple[int, int], float] = field(default_factory=dict)
    matchup_decisiveness:   Dict[Tuple[int, int], float] = field(default_factory=dict)
    dominance_penalty:      float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Métricas por personagem
# ─────────────────────────────────────────────────────────────────────────────


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


def _fight_score(result, hp_max_i: float, hp_max_j: float) -> float:
    """Score por-luta de i ∈ [0, 1] como margem contínua.
    KO: 0.5 + 0.5·(HP_frac do vencedor) — esmaga → ~1.0; ganha no fio → ~0.5.
    Timeout: fração de HP% (já contínua, ~0.5 quando equilibrado)."""
    if result.ko:
        if result.winner == 0:
            return 0.5 + 0.5 * (result.hp_remaining[0] / hp_max_i if hp_max_i > 0 else 0.0)
        return 0.5 - 0.5 * (result.hp_remaining[1] / hp_max_j if hp_max_j > 0 else 0.0)
    hp_pct_i = result.hp_remaining[0] / hp_max_i if hp_max_i > 0 else 0.0
    hp_pct_j = result.hp_remaining[1] / hp_max_j if hp_max_j > 0 else 0.0
    total_pct = hp_pct_i + hp_pct_j
    return hp_pct_i / total_pct if total_pct > 0 else 0.5


def _dominance_penalty(
    winrates: List[float],
    matchup_winrates: Dict[Tuple[int, int], float],
    matchup_decisiveness: Dict[Tuple[int, int], float],
) -> float:
    """Soma ponderada de três sinais cegos à direção (formulação C2). Nenhum codifica
    QUEM deveria vencer cada par — o ciclo de vantagens segue métrica post-hoc.

    PRIMÁRIO — balanço GLOBAL por personagem (`global_excess = |WR − 0.5| / 0.5`, RMS
    sobre os 5): nenhum boneco domina o roster. NÃO empurra cada par a 50%, então um
    boneco a 50% global pode vencer 2 e perder 2 — o espaço em que o ciclo vive.
    SECUNDÁRIO (teto) — hard-counter por par (`cap_excess`, |WR − 0.5| além de
    MATCHUP_WR_CAP, RMS sobre os 10): mantém as arestas do ciclo como vantagens, não
    como counters esmagadores (ex.: 100×0).
    SECUNDÁRIO (qualidade) — decisividade por luta fora da banda
    [MATCHUP_FLOOR, MATCHUP_THRESHOLD] (RMS sobre os 10): guarda contra blowout (toda
    luta um massacre, mesmo com WR equilibrada)."""
    global_excesses = [abs(wr - 0.5) / 0.5 for wr in winrates]
    global_term = math.sqrt(sum(e * e for e in global_excesses) / len(global_excesses))

    cap_scale  = 0.5 - MATCHUP_WR_CAP
    over_scale = 0.5 - MATCHUP_THRESHOLD
    cap_excesses:   List[float] = []
    decis_excesses: List[float] = []
    for key in matchup_decisiveness:
        wr = matchup_winrates[key]
        d  = matchup_decisiveness[key]
        cap_excesses.append(max(0.0, abs(wr - 0.5) - MATCHUP_WR_CAP) / cap_scale)
        decis_over  = max(0.0, d - MATCHUP_THRESHOLD) / over_scale
        decis_under = max(0.0, MATCHUP_FLOOR - d) / MATCHUP_FLOOR
        decis_excesses.append(decis_over + decis_under)
    cap_term   = math.sqrt(sum(e * e for e in cap_excesses) / len(cap_excesses))
    decis_term = math.sqrt(sum(e * e for e in decis_excesses) / len(decis_excesses))

    return (
        DOMINANCE_GLOBAL_WEIGHT * global_term
        + DOMINANCE_CAP_WEIGHT   * cap_term
        + DOMINANCE_DECIS_WEIGHT * decis_term
    )


# ─────────────────────────────────────────────────────────────────────────────
# Predicados de equilíbrio (C2) — fonte única consumida por ga.py e pelas tools
# ─────────────────────────────────────────────────────────────────────────────


def character_balanced(global_wr: float) -> bool:
    """Personagem globalmente equilibrado: WR global dentro de
    GLOBAL_CONVERGENCE_THRESHOLD de 50% (i.e. em [0.40, 0.60]). É o headline de
    equilíbrio sob C2 — nenhum boneco domina o roster."""
    return abs(global_wr - 0.5) <= GLOBAL_CONVERGENCE_THRESHOLD


def is_hard_counter(matchup_wr: float) -> bool:
    """Par é counter duro quando |WR − 0.5| > MATCHUP_WR_CAP (fora de [0.35, 0.65]):
    counter esmagador, não vantagem de ciclo. Dentro do teto, o par é uma aresta
    de ciclo permitida."""
    return abs(matchup_wr - 0.5) > MATCHUP_WR_CAP


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
    Dict[Tuple[int, int], float],
]:
    n = len(chars)
    wins        = [0] * n
    total_games = [0] * n
    matchup_wins:         Dict[Tuple[int, int], int]   = {}
    matchup_scores:       Dict[Tuple[int, int], float] = {}
    matchup_decisiveness: Dict[Tuple[int, int], float] = {}

    for i, j in combinations(range(n), 2):
        matchup_wins[(i, j)] = 0
        score_sum = 0.0
        decis_sum = 0.0
        for _ in range(sims):
            result = simulate_combat(chars[i], chars[j])
            if result.winner == 0:
                wins[i] += 1
                matchup_wins[(i, j)] += 1
            else:
                wins[j] += 1
            total_games[i] += 1
            total_games[j] += 1

            score_i = _fight_score(result, chars[i].hp, chars[j].hp)
            score_sum += score_i
            decis_sum += abs(score_i - 0.5)

        matchup_scores[(i, j)]       = score_sum / sims
        matchup_decisiveness[(i, j)] = decis_sum / sims

    return wins, total_games, matchup_wins, matchup_scores, matchup_decisiveness


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_detail_n(individual: Individual, sims: int) -> FitnessDetail:
    if _SEED_BASE is not None:
        seed_combat(_SEED_BASE)

    chars = individual.characters
    n     = len(chars)

    wins, total_games, matchup_wins, matchup_scores, matchup_decisiveness = (
        _run_round_robin(chars, sims)
    )

    winrates         = [wins[i] / total_games[i] for i in range(n)]
    matchup_winrates = {key: v / sims for key, v in matchup_wins.items()}

    archetype_deviations = [_archetype_deviation(c) for c in chars]
    drift_penalty        = sum(archetype_deviations) / n
    dominance_pen        = _dominance_penalty(winrates, matchup_winrates, matchup_decisiveness)

    fitness = -(
        LAMBDA_DRIFT     * drift_penalty
        + LAMBDA_DOMINANCE * dominance_pen
    )

    return FitnessDetail(
        fitness=fitness,
        winrates=winrates,
        drift_penalty=drift_penalty,
        archetype_deviations=archetype_deviations,
        matchup_winrates=matchup_winrates,
        matchup_scores=matchup_scores,
        matchup_decisiveness=matchup_decisiveness,
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

    with ProcessPoolExecutor(
        max_workers=N_WORKERS, initializer=set_seed_base, initargs=(_SEED_BASE,)
    ) as executor:
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
