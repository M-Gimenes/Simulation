"""
Fitness do AG via round-robin completo (C(5,2)=10 matchups × SIMS_PER_MATCHUP).

    fitness = -(λ_drift     × drift_penalty
              + λ_dominance × dominance_penalty)

Os dois λ vêm de `config.py` mas são **estado de processo** (`set_lambdas` /
`get_lambdas`), para que o sweep possa variá-los sem editar o arquivo.

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
from typing import Dict, List, NamedTuple, Optional, Tuple

from .combat import seed_combat, simulate_combat
from .archetypes import ArchetypeDefinition, ArchetypeID
from .config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
    DRIFT_DEFINING_WEIGHT,
    GENERATION_SEED_STRIDE,
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
    WEIGHT_NAMES,
)
from .individual import Individual
from .provenance import override as _register_override

_GENE_RANGES: List[float] = [hi - lo for lo, hi in GENE_BOUNDS]
N_WEIGHT_GENES: int = len(WEIGHT_NAMES)
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
# Pesos do fitness como ESTADO DE PROCESSO
# ─────────────────────────────────────────────────────────────────────────────
# Os pesos do escalar (λ) e os três do `dominance` não são lidos direto do módulo, e sim
# mantidos como estado: os sweeps de calibração os variam entre execuções, e um
# `from .config import X` congela o valor no import.
#
# Mesmo padrão do `_SEED_BASE`, inclusive na parte que mais importa — a propagação aos
# workers (ver `runtime_state` / `init_worker`): no Windows o pool nasce por spawn e
# re-importa o módulo, então sem propagar explicitamente os workers avaliariam com os
# pesos do `config.py` enquanto o pai usa os do braço, e a divergência sairia como
# RESULTADO em vez de erro — um braço inteiro medindo a configuração errada, sem sintoma.
#
# Duas portas por peso, de propósito: `set_*` só muda o processo (é o que os workers
# chamam) e `set_*_override` muda e **registra no carimbo de proveniência**, para que o
# artefato do braço não afirme o valor do arquivo. Quem carimba é o pai; se os workers
# registrassem, o override seria contado N vezes sem efeito nenhum.

_LAMBDA_DRIFT:     float = LAMBDA_DRIFT
_LAMBDA_DOMINANCE: float = LAMBDA_DOMINANCE
_DOM_GLOBAL:       float = DOMINANCE_GLOBAL_WEIGHT
_DOM_CAP:          float = DOMINANCE_CAP_WEIGHT
_DOM_DECIS:        float = DOMINANCE_DECIS_WEIGHT


def set_lambdas(drift: float, dominance: float) -> None:
    """Define os pesos do escalar neste processo."""
    global _LAMBDA_DRIFT, _LAMBDA_DOMINANCE
    _LAMBDA_DRIFT, _LAMBDA_DOMINANCE = drift, dominance


def set_lambdas_override(drift: float, dominance: float) -> None:
    """Como `set_lambdas`, e registra no carimbo. É o ponto de entrada das tools."""
    set_lambdas(drift, dominance)
    _register_override("LAMBDA_DRIFT", drift)
    _register_override("LAMBDA_DOMINANCE", dominance)


def get_lambdas() -> Tuple[float, float]:
    """`(drift, dominance)` em vigor — fonte única, consumida também pelo
    `nsga2.scalar_objective`, senão o representante comparável sairia de um λ e o
    escalar de outro."""
    return _LAMBDA_DRIFT, _LAMBDA_DOMINANCE


def set_dominance_weights(global_w: float, cap_w: float, decis_w: float) -> None:
    """Define os pesos dos três termos do `dominance_penalty` neste processo."""
    global _DOM_GLOBAL, _DOM_CAP, _DOM_DECIS
    _DOM_GLOBAL, _DOM_CAP, _DOM_DECIS = global_w, cap_w, decis_w


def set_dominance_weights_override(global_w: float, cap_w: float, decis_w: float) -> None:
    """Como `set_dominance_weights`, e registra no carimbo."""
    set_dominance_weights(global_w, cap_w, decis_w)
    _register_override("DOMINANCE_GLOBAL_WEIGHT", global_w)
    _register_override("DOMINANCE_CAP_WEIGHT", cap_w)
    _register_override("DOMINANCE_DECIS_WEIGHT", decis_w)


def get_dominance_weights() -> Tuple[float, float, float]:
    return _DOM_GLOBAL, _DOM_CAP, _DOM_DECIS


class RuntimeState(NamedTuple):
    """Todo o estado de processo que um worker **não** herda por spawn.

    Existe como um objeto só, e não como argumentos soltos do `init_worker`, porque o modo
    de falha aqui é *esquecer de propagar um*: o pool passaria a avaliar sob uma
    configuração diferente da do pai e o resultado sairia como número plausível. Com um
    bundle, acrescentar um peso novo ao estado o propaga automaticamente — e os nomes
    documentam o que atravessa a fronteira."""
    seed_base:        Optional[int]
    lambda_drift:     float
    lambda_dominance: float
    dominance_global: float
    dominance_cap:    float
    dominance_decis:  float


def runtime_state() -> RuntimeState:
    return RuntimeState(_SEED_BASE, _LAMBDA_DRIFT, _LAMBDA_DOMINANCE,
                        _DOM_GLOBAL, _DOM_CAP, _DOM_DECIS)


def generation_seed(base: int, generation: int) -> int:
    """Stream de avaliação de UMA geração — a fonte única do protocolo, consumida
    pelo AG escalar e pelo NSGA-II (protocolo igual nos dois, senão a comparação
    entre eles confundiria algoritmo com forma de avaliar).

    Toda a geração é avaliada sob o mesmo stream (CRN: a diferença de fitness entre
    indivíduos reflete genes, não sorteio), e o stream MUDA a cada geração. É a troca
    que impede a população de se ajustar a uma realização específica do RNG — ver o
    comentário de `GENERATION_SEED_STRIDE` no `config.py` para os números."""
    return base * GENERATION_SEED_STRIDE + generation


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
            _DOM_GLOBAL * self.global_term
            + _DOM_CAP   * self.cap_term
            + _DOM_DECIS * self.decis_term
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


def drift_genes(char) -> List[float]:
    """Os genes do personagem na forma em que o DRIFT os compara: atributos
    intactos, e os 3 pesos REESCALADOS para a mesma soma dos canônicos.

    Por quê: a intenção é sorteada proporcionalmente a `(w_retreat, w_defend,
    w_aggressiveness)`, então multiplicar os três por `k > 0` não muda **nada** no
    combate — é um grau de liberdade behaviouralmente nulo. Sem o reescalonamento o
    drift cobra por essa diferença invisível. Medido no indivíduo evoluído: **7,5%**
    do drift médio (pior caso Rushdown 15,1%), com os `k` ótimos entre 0,58 e 0,70 —
    o AG inflava a escala dos pesos e o drift cobrava pela inflação.

    Fonte única: `_archetype_deviation` e o `drift_table` consomem esta função, senão
    o total e a coluna por gene discordariam nos pesos."""
    genes = list(char.genes())
    canon = canonical_genes(char.archetype)
    total = sum(genes[-N_WEIGHT_GENES:])
    if total > 0:
        scale = sum(canon[-N_WEIGHT_GENES:]) / total
        for i in range(len(genes) - N_WEIGHT_GENES, len(genes)):
            genes[i] *= scale
    # total == 0 não é reescalável e o combate cai para GUARDA: é comportamento
    # genuinamente distinto, então o desvio cru (grande) é a leitura correta.
    return genes


def _archetype_deviation(char) -> float:
    """Identidade ESTRUTURAL do personagem: RMS ponderada dos desvios normalizados
    em relação ao canônico. Os `defining_genes` do arquétipo pesam mais — mover o
    que torna o personagem reconhecível custa mais que mover o resto. Compara sobre
    `drift_genes`, não sobre os genes crus — ver a justificativa lá."""
    weights = drift_weights(char.archetype)
    num = 0.0
    for i, (g, c, w) in enumerate(
        zip(drift_genes(char), canonical_genes(char.archetype), weights)
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
        _LAMBDA_DRIFT     * drift_penalty
        + _LAMBDA_DOMINANCE * dominance_pen
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


def init_worker(state: RuntimeState) -> None:
    """Aplica no worker o estado de processo do pai. Ver `RuntimeState`."""
    set_seed_base(state.seed_base)
    set_lambdas(state.lambda_drift, state.lambda_dominance)
    set_dominance_weights(state.dominance_global, state.dominance_cap, state.dominance_decis)


def evaluate_population(population: List[Individual]) -> None:
    unevaluated = [ind for ind in population if not ind.is_evaluated]
    if not unevaluated:
        return

    if N_WORKERS == 1 or len(unevaluated) == 1:
        for ind in unevaluated:
            evaluate(ind)
        return

    with ProcessPoolExecutor(
        max_workers=N_WORKERS, initializer=init_worker, initargs=(runtime_state(),)
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
