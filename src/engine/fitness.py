"""
Fitness do AG via round-robin completo (C(5,2)=10 matchups × SIMS_PER_MATCHUP).

    fitness = -(LAMBDA_DRIFT     × drift_penalty
              + LAMBDA_DOMINANCE × dominance_penalty)

Os mesmos dois termos do NSGA-II — lá como objetivos de Pareto (sem ponderação),
aqui como soma ponderada. O escalar é um ponto do trade-off que o NSGA-II mapeia.

`drift_penalty` mede identidade ESTRUTURAL (os genes continuam reconhecíveis). A
identidade FUNCIONAL — como o personagem joga — e o ciclo de vantagens ficam fora
do fitness, como métricas post-hoc independentes.
"""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from .combat import seed_combat, simulate_combat
from .archetypes import ArchetypeDefinition, ArchetypeID
from .config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
    DRIFT_DEFINING_WEIGHT,
    GENE_BOUNDS,
    GENE_NAMES,
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

_GENE_RANGES: List[float] = [hi - lo for lo, hi in GENE_BOUNDS]
_DRIFT_WEIGHTS: Dict[ArchetypeID, List[float]] = {}


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
class DominanceTerms:
    """Os três sinais que compõem o `dominance_penalty`, guardados separados.
    O composto sozinho esconde de onde vem a diferença entre dois indivíduos —
    um pode perder no termo primário e outro num secundário com metade do peso."""
    global_term: float
    cap_term:    float
    decis_term:  float

    @property
    def total(self) -> float:
        return (
            DOMINANCE_GLOBAL_WEIGHT * self.global_term
            + DOMINANCE_CAP_WEIGHT   * self.cap_term
            + DOMINANCE_DECIS_WEIGHT * self.decis_term
        )

    def as_dict(self) -> Dict[str, float]:
        return {
            "global_term": self.global_term,
            "cap_term":    self.cap_term,
            "decis_term":  self.decis_term,
        }


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
    dominance_terms:        Optional[DominanceTerms] = None


# ─────────────────────────────────────────────────────────────────────────────
# Métricas por personagem
# ─────────────────────────────────────────────────────────────────────────────


def drift_weights(archetype: ArchetypeDefinition) -> List[float]:
    """Peso de cada um dos 10 genes no drift do arquétipo: DRIFT_DEFINING_WEIGHT
    para os `defining_genes`, 1.0 para o resto. Cacheado por arquétipo."""
    cached = _DRIFT_WEIGHTS.get(archetype.id)
    if cached is None:
        defining = set(archetype.defining_genes)
        cached = [
            DRIFT_DEFINING_WEIGHT if name in defining else 1.0
            for name in GENE_NAMES
        ]
        _DRIFT_WEIGHTS[archetype.id] = cached
    return cached


def canonical_genes(archetype: ArchetypeDefinition) -> List[float]:
    """Os 10 genes canônicos na ordem de `Character.genes()`."""
    return list(archetype.initial_attributes) + list(archetype.initial_weights)


def gene_drift(value: float, canonical: float, gene_index: int) -> float:
    """Desvio normalizado de um gene: fração do RANGE do bound, com sinal.
    Normalizar por `(hi − lo)` e não por `hi` evita subestimar genes de `lo` alto
    (HP vai de 250 a 450: mover 162 é 81% do range, não 36% do máximo)."""
    return (value - canonical) / _GENE_RANGES[gene_index]


def _archetype_deviation(char) -> float:
    """Identidade ESTRUTURAL do personagem: RMS ponderada dos desvios normalizados
    em relação ao canônico. Os `defining_genes` do arquétipo pesam mais — mover o
    que torna o personagem reconhecível custa mais que mover o resto."""
    weights = drift_weights(char.archetype)
    num = 0.0
    for i, (g, c, w) in enumerate(
        zip(char.genes(), canonical_genes(char.archetype), weights)
    ):
        d = gene_drift(g, c, i)
        num += w * d * d
    return math.sqrt(num / sum(weights))


def _fight_score(result, hp_max_i: float, hp_max_j: float) -> float:
    """Score por-luta de i ∈ [0, 1] como margem contínua.
    Empate: 0.5 (margem nula). KO: 0.5 + 0.5·(HP_frac do vencedor) — esmaga → ~1.0;
    ganha no fio → ~0.5. Timeout: fração de HP% (já contínua, ~0.5 quando equilibrado)."""
    if result.is_draw:
        return 0.5
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
) -> DominanceTerms:
    """Três sinais cegos à direção (formulação C2). Nenhum codifica
    QUEM deveria vencer cada par — o ciclo de vantagens segue métrica post-hoc.

    PRIMÁRIO — balanço GLOBAL por personagem (`global_excess = |WR − 0.5| / 0.5`, RMS
    sobre os 5): nenhum boneco domina o roster. NÃO empurra cada par a 50%, então um
    boneco a 50% global pode vencer 2 e perder 2 — o espaço em que o ciclo vive.
    SECUNDÁRIO (teto) — hard-counter por par (`cap_excess`, |WR − 0.5| além de
    MATCHUP_WR_CAP, RMS sobre os 10): mantém as arestas do ciclo como vantagens, não
    como counters esmagadores (ex.: 100×0).
    SECUNDÁRIO (qualidade) — decisividade por luta fora da banda
    [MATCHUP_FLOOR, MATCHUP_THRESHOLD] (RMS sobre os 10). O TETO guarda contra blowout
    (toda luta um massacre, mesmo com WR equilibrada). O PISO é só guarda de
    degenerescência — fica abaixo da faixa do espelho puro e não morde em operação
    normal: empurrar contra luta apertada seria empurrar contra o termo primário."""
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

    return DominanceTerms(global_term, cap_term, decis_term)


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


def roster_balanced(detail: "FitnessDetail") -> bool:
    """Critério de equilíbrio C2 sobre UMA avaliação: nenhum boneco domina o roster
    (WR global dentro de `GLOBAL_CONVERGENCE_THRESHOLD` de 50%) **e** nenhum par é
    counter duro (`|WR_par − 0.5| ≤ MATCHUP_WR_CAP`). NÃO exige cada par a 50% —
    arestas de ciclo são permitidas, e é justamente esse o espaço em que o ciclo vive.

    É a definição de equilíbrio do projeto, em um lugar só: `ga.run` usa como gate de
    convergência e como confirmação, e o `multi_run` como veredito por semente."""
    return (
        all(character_balanced(wr) for wr in detail.winrates)
        and not any(is_hard_counter(wr) for wr in detail.matchup_winrates.values())
    )


# ─────────────────────────────────────────────────────────────────────────────
# Round-robin
# ─────────────────────────────────────────────────────────────────────────────


def _run_round_robin(
    chars: List, sims: int
) -> Tuple[
    List[float],
    List[int],
    Dict[Tuple[int, int], float],
    Dict[Tuple[int, int], float],
    Dict[Tuple[int, int], float],
]:
    n = len(chars)
    wins        = [0.0] * n
    total_games = [0] * n
    matchup_wins:         Dict[Tuple[int, int], float] = {}
    matchup_scores:       Dict[Tuple[int, int], float] = {}
    matchup_decisiveness: Dict[Tuple[int, int], float] = {}

    for i, j in combinations(range(n), 2):
        matchup_wins[(i, j)] = 0.0
        score_sum = 0.0
        decis_sum = 0.0
        for _ in range(sims):
            result = simulate_combat(chars[i], chars[j])
            if result.winner == 0:
                wins[i] += 1.0
                matchup_wins[(i, j)] += 1.0
            elif result.winner == 1:
                wins[j] += 1.0
            else:                              # empate — meia vitória para cada lado
                wins[i] += 0.5
                wins[j] += 0.5
                matchup_wins[(i, j)] += 0.5
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
    dominance_terms      = _dominance_penalty(winrates, matchup_winrates, matchup_decisiveness)
    dominance_pen        = dominance_terms.total

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
        dominance_terms=dominance_terms,
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
