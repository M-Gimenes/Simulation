"""
NSGA-II — variante multi-objetivo do AG (Deb et al., 2002).

Otimiza simultaneamente (dominance_penalty, drift_penalty) sem ponderação,
produzindo Pareto front e extraindo 5 representantes (best_dominance, best_drift,
knee_point, ideal_point, scalar_optimum).

A busca ignora os `LAMBDA_*` — eles entram **só** em `scalar_optimum`, que é um
comparável de reporting: o ponto da fronteira que o AG escalar deveria ter encontrado.
"""
from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .combat import seed_combat
from .config import (
    N_WORKERS,
    NSGA2_GENERATIONS,
    NSGA2_POP_SIZE,
)
from .fitness import (
    evaluate_objectives,
    generation_seed,
    get_lambdas,
    parallel_map,
    set_seed_base,
)
from .individual import Individual
from .operators import crossover, mutate, nsga2_binary_tournament
from .paths import NSGA2_RESULTS_PATH
from .provenance import stamp


# ─────────────────────────────────────────────────────────────────────────────
# Dominação de Pareto
# ─────────────────────────────────────────────────────────────────────────────


def _dominates(a: Individual, b: Individual) -> bool:
    strictly_better = False
    for oa, ob in zip(a.objectives, b.objectives):
        if oa > ob:
            return False
        if oa < ob:
            strictly_better = True
    return strictly_better


# ─────────────────────────────────────────────────────────────────────────────
# Non-dominated sort (Deb 2002)
# ─────────────────────────────────────────────────────────────────────────────


def fast_non_dominated_sort(population: List[Individual]) -> List[List[Individual]]:
    # Trabalha com índices (não .index()) — múltiplos indivíduos com o mesmo
    # conteúdo comparável (ex.: clones do canônico) quebram .index() silenciosamente.
    n = len(population)
    dominates_set    = [[] for _ in range(n)]
    domination_count = [0] * n

    for i in range(n):
        for j in range(i + 1, n):
            if _dominates(population[i], population[j]):
                dominates_set[i].append(j)
                domination_count[j] += 1
            elif _dominates(population[j], population[i]):
                dominates_set[j].append(i)
                domination_count[i] += 1

    front_indices: List[List[int]] = [[]]
    for p in range(n):
        if domination_count[p] == 0:
            population[p].rank = 0
            front_indices[0].append(p)

    k = 0
    while front_indices[k]:
        next_front: List[int] = []
        for p in front_indices[k]:
            for q in dominates_set[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    population[q].rank = k + 1
                    next_front.append(q)
        k += 1
        front_indices.append(next_front)
    front_indices.pop()

    return [[population[i] for i in indices] for indices in front_indices]


# ─────────────────────────────────────────────────────────────────────────────
# Crowding distance (Deb 2002)
# ─────────────────────────────────────────────────────────────────────────────


def crowding_distance_assignment(front: List[Individual]) -> None:
    size = len(front)
    if size <= 2:
        for ind in front:
            ind.crowding = math.inf
        return

    for ind in front:
        ind.crowding = 0.0

    n_objectives = len(front[0].objectives)
    for m in range(n_objectives):
        front.sort(key=lambda ind: ind.objectives[m])
        f_min = front[0].objectives[m]
        f_max = front[-1].objectives[m]
        span  = f_max - f_min
        front[0].crowding  = math.inf
        front[-1].crowding = math.inf
        if span == 0:
            continue
        for i in range(1, size - 1):
            if math.isinf(front[i].crowding):
                continue
            front[i].crowding += (front[i + 1].objectives[m] - front[i - 1].objectives[m]) / span


# ─────────────────────────────────────────────────────────────────────────────
# Seleção dos representantes da fronteira final
# ─────────────────────────────────────────────────────────────────────────────


def _best_in(front: List[Individual], objective_idx: int) -> Individual:
    return min(front, key=lambda ind: ind.objectives[objective_idx])


def _euclidean_norm(objs) -> float:
    return math.sqrt(sum(o * o for o in objs))


def scalar_objective(objs) -> float:
    """O objetivo do AG escalar aplicado a um ponto da fronteira:
    `λ_dominance·dominance + λ_drift·drift`. É a ÚNICA coisa no NSGA-II que olha os
    `LAMBDA_*`, e é reporting, não busca — serve para extrair o ponto comparável ao que
    o escalar otimiza.

    Consequência que o sweep de λ usa: a FRONTEIRA é λ-independente, só a escolha do
    `scalar_optimum` não é. Uma execução do NSGA-II serve todos os braços do sweep —
    basta re-derivar este mínimo sob cada λ, sem re-rodar a busca. Por isso lê
    `fitness.get_lambdas()` (o λ em vigor) e não a constante do `config.py`."""
    dominance, drift = objs
    lambda_drift, lambda_dominance = get_lambdas()
    return lambda_dominance * dominance + lambda_drift * drift


def _normalizer(front: List[Individual]):
    """Leva cada objetivo a [0, 1] pela amplitude DESTA fronteira: 0 = o melhor valor
    da fronteira naquele objetivo, 1 = o pior. Objetivo constante vira 0."""
    n_obj = len(front[0].objectives)
    lows  = [min(ind.objectives[m] for ind in front) for m in range(n_obj)]
    spans = [max(ind.objectives[m] for ind in front) - lows[m] for m in range(n_obj)]

    def normalized(ind: Individual) -> Tuple[float, ...]:
        return tuple((o - lo) / span if span > 0 else 0.0
                     for o, lo, span in zip(ind.objectives, lows, spans))
    return normalized


def select_representatives(front: List[Individual]) -> dict:
    """Cinco pontos que resumem a fronteira. Os quatro primeiros são geométricos
    (extremos, joelho e o mais próximo do ponto utópico); `scalar_optimum` é o
    comparável do AG escalar — ver `scalar_objective`.

    O joelho e o ideal são medidos com os objetivos NORMALIZADOS pela amplitude da
    fronteira. Em unidades cruas a geometria dependeria da escala de cada objetivo —
    `dominance` vai até 2,0 e `drift` fica em décimos —, e o "ponto de maior curvatura"
    ou o "mais próximo do ideal" sairia decidido pela unidade de medida, não pelo
    trade-off. O ideal é o ponto utópico da fronteira (o melhor de cada objetivo), não a
    origem: a origem não é alcançável por nenhum ponto e fica a distâncias diferentes em
    cada eixo."""
    best_dominance = _best_in(front, 0)
    best_drift     = _best_in(front, 1)
    scalar_opt     = min(front, key=lambda ind: scalar_objective(ind.objectives))

    normalized = _normalizer(front)
    ideal      = min(front, key=lambda ind: _euclidean_norm(normalized(ind)))

    p1        = normalized(best_dominance)
    p2        = normalized(best_drift)
    line      = (p2[0] - p1[0], p2[1] - p1[1])
    line_norm = math.sqrt(line[0] ** 2 + line[1] ** 2)

    if line_norm == 0.0 or len(front) <= 2:
        knee = front[0]
    else:
        def _dist(ind):
            q     = normalized(ind)
            d     = (q[0] - p1[0], q[1] - p1[1])
            proj  = (d[0] * line[0] + d[1] * line[1]) / line_norm
            perp2 = d[0] ** 2 + d[1] ** 2 - proj ** 2
            return math.sqrt(max(0.0, perp2))
        knee = max(front, key=_dist)

    return {
        "best_dominance": best_dominance,
        "best_drift":     best_drift,
        "knee_point":     knee,
        "ideal_point":    ideal,
        # Comparável direto do AG escalar: o ponto da fronteira que minimiza a MESMA
        # soma ponderada que o escalar otimiza. Sem ele a comparação entre os dois
        # algoritmos usaria `ideal_point`, que é geométrico e cego aos λ — outro ponto.
        "scalar_optimum": scalar_opt,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class GenerationStats:
    generation:        int
    # `front_sizes` mede a população COMBINADA (2×pop) — é dela que sai o número de
    # fronts. `front0_selected` e `front0_ranges` medem a população SELECIONADA (pop),
    # que é a que sobrevive. Misturar as duas fazia o log imprimir `front0=302` num
    # pop de 300, ao lado de faixas calculadas sobre outros indivíduos.
    front_sizes:       List[int]
    front0_selected:   int
    front0_ranges:     List[Tuple[float, float]]
    gen_elapsed_s:     float
    total_elapsed_s:   float


@dataclass
class NSGAResult:
    pareto_front:    List[Individual]
    representatives: Dict[str, Individual]
    history:         List[GenerationStats]
    generations_run: int
    seed:            Optional[int] = None


def _objectives_worker(ind: Individual) -> Tuple[float, float]:
    return evaluate_objectives(ind)


def _evaluate_population(pop: List[Individual]) -> None:
    unevaluated = [ind for ind in pop if ind.objectives is None]
    if not unevaluated:
        return
    if N_WORKERS == 1 or len(unevaluated) == 1:
        for ind in unevaluated:
            evaluate_objectives(ind)
        return
    for ind, objs in zip(unevaluated, parallel_map(_objectives_worker, unevaluated)):
        ind.objectives = objs


def _assign_rank_and_crowding(pop: List[Individual]) -> List[List[Individual]]:
    fronts = fast_non_dominated_sort(pop)
    for front in fronts:
        crowding_distance_assignment(front)
    return fronts


def _select_next_population(
    fronts: List[List[Individual]], target_size: int
) -> List[Individual]:
    next_pop: List[Individual] = []
    for front in fronts:
        if len(next_pop) + len(front) <= target_size:
            next_pop.extend(front)
        else:
            remaining = target_size - len(next_pop)
            front_sorted = sorted(front, key=lambda ind: ind.crowding, reverse=True)
            next_pop.extend(front_sorted[:remaining])
            break
    return next_pop


def _generate_offspring(parents: List[Individual], size: int) -> List[Individual]:
    offspring: List[Individual] = []
    while len(offspring) < size:
        p1 = nsga2_binary_tournament(parents)
        p2 = nsga2_binary_tournament(parents)
        child = crossover(p1, p2)
        mutate(child)
        offspring.append(child)
    return offspring


def _log_generation(stats: GenerationStats, verbose: bool) -> None:
    if not verbose:
        return
    (dom_lo, dom_hi), (drift_lo, drift_hi) = stats.front0_ranges
    front0 = stats.front0_selected
    n_fronts = len(stats.front_sizes)
    print(
        f"Gen {stats.generation:4d} | "
        f"front0={front0:3d}/{n_fronts:<2d}  "
        f"dom∈[{dom_lo:.3f}, {dom_hi:.3f}]  "
        f"drift∈[{drift_lo:.3f}, {drift_hi:.3f}]  "
        f"Δ{stats.gen_elapsed_s:5.1f}s · {stats.total_elapsed_s:6.1f}s"
    )


def run(
    seed:          Optional[int] = None,
    pop_size:      int           = NSGA2_POP_SIZE,
    n_generations: int           = NSGA2_GENERATIONS,
    verbose:       bool          = True,
) -> NSGAResult:
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        seed_combat(seed)
    set_seed_base(generation_seed(seed, 0) if seed is not None else None)

    t_start = time.time()

    # População inicial 100% ALEATÓRIA — sem o seed canônico que o AG escalar usa.
    # Motivo: `drift = 0` é o mínimo global do objetivo e o canônico o atinge de graça
    # na geração 0. Dominá-lo exigiria `drift < 0`, que não existe — então ele e sua
    # vizinhança ficam IMORTAIS no rank 0 por pior que seja o equilíbrio deles. Medido
    # (pop 120, 60 gerações, seed 42): 40 dos 78 pontos da fronteira final ficavam com
    # `dominance >= 1.0` (tão desequilibrados quanto o canônico intocado), ocupando um
    # terço da população e um terço do esforço reprodutivo; o min dominance estagnava em
    # 0,2233. E o crowding não limpa: ele só poda quando um front TRANSBORDA a população,
    # e front0 (78) nunca passou de 120. Sem o seed: min dominance 0,0896, ainda caindo
    # na geração 50, e 1 de 44 pontos na região inútil.
    # No AG escalar o mesmo seed AJUDA (fitness é um número só, ele é ruim nele e some
    # depois de doar genes), então lá ele fica. A assimetria é deliberada.
    population = [Individual.random() for _ in range(pop_size)]
    _evaluate_population(population)
    _assign_rank_and_crowding(population)

    if verbose:
        print(
            f"NSGA-II | pop={pop_size}  gens={n_generations}  workers={N_WORKERS}  "
            f"objectives=(dominance, drift)"
        )

    history: List[GenerationStats] = []
    t_prev = time.time()

    for gen in range(n_generations):
        offspring = _generate_offspring(population, pop_size)
        if seed is not None:
            # Stream NOVO. Aqui a rotação custa o dobro do que custa no AG escalar:
            # a ordenação por dominância compara pais e filhos dentro do MESMO
            # `combined`, e objetivos medidos em streams diferentes não são
            # comparáveis — então os pais têm de ser reavaliados junto, 2×pop por
            # geração em vez de pop.
            set_seed_base(generation_seed(seed, gen + 1))
        # Invalidar vale COM E SEM semente: sem ela, um pai que tirou uma avaliação de
        # sorte sobreviveria no rank 0 para sempre, sem nunca regredir à média.
        for ind in population:
            ind.invalidate_fitness()

        # Pais + filhos numa chamada só: `_evaluate_population` filtra quem tem objetivo
        # em cache, então sem rotação isto avalia só os filhos.
        combined = population + offspring
        _evaluate_population(combined)
        fronts   = _assign_rank_and_crowding(combined)
        population = _select_next_population(fronts, pop_size)

        front0 = [ind for ind in population if ind.rank == 0]
        front0_ranges = [
            (min(ind.objectives[m] for ind in front0),
             max(ind.objectives[m] for ind in front0))
            for m in range(2)
        ]
        t_now = time.time()
        stats = GenerationStats(
            generation=gen,
            front_sizes=[len(f) for f in fronts],
            front0_selected=len(front0),
            front0_ranges=front0_ranges,
            gen_elapsed_s=t_now - t_prev,
            total_elapsed_s=t_now - t_start,
        )
        t_prev = t_now
        history.append(stats)
        _log_generation(stats, verbose)

    pareto_front    = [ind for ind in population if ind.rank == 0]
    representatives = select_representatives(pareto_front)

    return NSGAResult(
        pareto_front=pareto_front,
        representatives=representatives,
        history=history,
        generations_run=n_generations,
        seed=seed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Serialização JSON
# ─────────────────────────────────────────────────────────────────────────────

def _individual_to_dict(ind: Individual) -> dict:
    return {
        "genes":      [c.genes() for c in ind.characters],
        "objectives": list(ind.objectives),
    }


def save_results(result: NSGAResult, path: Path = NSGA2_RESULTS_PATH) -> None:
    data = {
        "provenance":      stamp(),
        "algorithm":       "nsga2",
        "seed":            result.seed,
        "generations_run": result.generations_run,
        "pareto_front":    [_individual_to_dict(ind) for ind in result.pareto_front],
        "representatives": {
            name: _individual_to_dict(ind)
            for name, ind in result.representatives.items()
        },
        "history": [
            {
                "gen":             s.generation,
                "front_sizes":     s.front_sizes,
                "front0_selected": s.front0_selected,
                "front0_ranges":   [list(r) for r in s.front0_ranges],
                "gen_elapsed_s":   round(s.gen_elapsed_s, 3),
                "total_elapsed_s": round(s.total_elapsed_s, 3),
            }
            for s in result.history
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
