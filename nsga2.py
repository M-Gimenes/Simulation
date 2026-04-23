"""
NSGA-II — Algoritmo genético multi-objetivo (Deb et al., 2002).

Otimiza 3 objetivos simultaneamente:
  f1 = balance_error             (equilíbrio agregado — WR médio)
  f2 = matchup_dominance_penalty (pior matchup direto)
  f3 = drift_penalty             (preservação de arquétipo)

Todos minimizados, todos em [0, 1].
"""
from __future__ import annotations

import json
import math
import random
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config import N_WORKERS, NSGA2_GENERATIONS, NSGA2_POP_SIZE
from fitness import evaluate_objectives
from individual import Individual
from operators import crossover, mutate, nsga2_binary_tournament


# ─────────────────────────────────────────────────────────────────────────────
# Dominação de Pareto
# ─────────────────────────────────────────────────────────────────────────────


def _dominates(a: Individual, b: Individual) -> bool:
    """
    `a` domina `b` sse a.f_i ≤ b.f_i para todo i E a.f_j < b.f_j para algum j.

    Pressupõe que ambos têm `objectives` preenchido.
    """
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
    """
    Particiona a população em fronteiras não-dominadas (Deb 2002, O(MN²)).

    Atribui `ind.rank` in-place (0 = melhor).
    Retorna `[[rank_0], [rank_1], ...]`.

    Trabalha com índices internamente (não `.index()`) — evita bug quando
    múltiplos indivíduos têm o mesmo conteúdo comparável (ex.: clones do canônico).
    """
    n = len(population)
    dominates_set    = [[] for _ in range(n)]   # dominates_set[i] = índices dominados por i (S_i — Deb 2002)
    domination_count = [0] * n                  # domination_count[i] = quantos dominam i

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
    front_indices.pop()   # último é vazio — sentinela do while

    return [[population[i] for i in indices] for indices in front_indices]


# ─────────────────────────────────────────────────────────────────────────────
# Crowding distance (Deb 2002)
# ─────────────────────────────────────────────────────────────────────────────


def crowding_distance_assignment(front: List[Individual]) -> None:
    """
    Atribui `ind.crowding` in-place para cada indivíduo da fronteira.

    Fronteiras com ≤ 2 pontos: todos recebem +inf (preferência máxima).
    Caso geral: para cada objetivo m, ordena pela m-ésima componente;
    extremos recebem +inf, intermediários recebem distância normalizada.
    """
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
            continue   # todos iguais neste objetivo — intermediários inalterados
        for i in range(1, size - 1):
            if math.isinf(front[i].crowding):
                continue
            front[i].crowding += (front[i + 1].objectives[m] - front[i - 1].objectives[m]) / span


# ─────────────────────────────────────────────────────────────────────────────
# Seleção dos 5 representantes da fronteira final
# ─────────────────────────────────────────────────────────────────────────────


def _best_in(front: List[Individual], objective_idx: int) -> Individual:
    return min(front, key=lambda ind: ind.objectives[objective_idx])


def _euclidean_norm(objs) -> float:
    return math.sqrt(sum(o * o for o in objs))


def _distance_to_plane(point, plane_p, plane_normal_unit) -> float:
    """Distância perpendicular de `point` ao plano (p0, n̂)."""
    d = sum((p - p0) * n for p, p0, n in zip(point, plane_p, plane_normal_unit))
    return abs(d)


def _cross3(u, v):
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def _dist_to_line(objs, anchor, line, line_norm) -> float:
    """Distância perpendicular de `objs` à reta definida por `anchor + t*line`."""
    d = tuple(a - b for a, b in zip(objs, anchor))
    proj = sum(di * li for di, li in zip(d, line)) / line_norm
    perp_sq = sum(di * di for di in d) - proj * proj
    return math.sqrt(max(0.0, perp_sq))


def _find_knee(front: List[Individual], extremes: List[Individual]) -> Individual:
    """
    Knee point = indivíduo mais distante do plano formado pelos 3 extremos.

    Se os 3 extremos forem colineares (plano degenerado), fallback para o
    ponto mais distante da reta entre o 1º e o 3º extremo.
    """
    p1 = extremes[0].objectives
    p2 = extremes[1].objectives
    p3 = extremes[2].objectives
    u = tuple(a - b for a, b in zip(p2, p1))
    v = tuple(a - b for a, b in zip(p3, p1))
    n = _cross3(u, v)
    norm_n = _euclidean_norm(n)
    if norm_n == 0.0:
        # Fallback: distância à reta p1–p3 (extremos colineares — plano degenerado)
        line = tuple(a - b for a, b in zip(p3, p1))
        line_norm = _euclidean_norm(line)
        if line_norm == 0.0:
            return front[0]
        return max(front, key=lambda ind: _dist_to_line(ind.objectives, p1, line, line_norm))

    n_hat = tuple(ni / norm_n for ni in n)
    return max(front, key=lambda ind: _distance_to_plane(ind.objectives, p1, n_hat))


def select_representatives(front: List[Individual]) -> dict:
    """
    Retorna 5 representantes da fronteira de Pareto:
      - 3 extremos (melhor em cada objetivo)
      - knee_point  — ponto de máxima curvatura (mais distante do plano dos extremos)
      - ideal_point — mais próximo da utopia (0, 0, 0) em distância Euclidiana

    Ordem dos objetivos: (balance_error, matchup_dominance_penalty, drift_penalty).
    """
    best_balance = _best_in(front, 0)
    best_matchup = _best_in(front, 1)
    best_drift   = _best_in(front, 2)
    ideal        = min(front, key=lambda ind: _euclidean_norm(ind.objectives))
    knee         = _find_knee(front, [best_balance, best_matchup, best_drift])

    return {
        "best_balance": best_balance,
        "best_matchup": best_matchup,
        "best_drift":   best_drift,
        "knee_point":   knee,
        "ideal_point":  ideal,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class GenerationStats:
    generation:          int
    front_sizes:         List[int]               # tamanho de cada fronteira em R (após merge)
    best_per_objective:  List[float]             # melhor valor em cada um dos 3 objetivos
    elapsed_s:           float


@dataclass
class NSGAResult:
    pareto_front:    List[Individual]            # rank=0 da população final
    representatives: Dict[str, Individual]       # 5 representantes
    history:         List[GenerationStats]
    generations_run: int
    seed:            Optional[int] = None


def _objectives_worker(ind: Individual) -> Tuple[float, float, float]:
    return evaluate_objectives(ind)


def _evaluate_population(pop: List[Individual]) -> None:
    unevaluated = [ind for ind in pop if ind.objectives is None]
    if not unevaluated:
        return
    if N_WORKERS == 1 or len(unevaluated) == 1:
        for ind in unevaluated:
            evaluate_objectives(ind)
        return
    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        results = list(executor.map(_objectives_worker, unevaluated))
    for ind, objs in zip(unevaluated, results):
        ind.objectives = objs


def _assign_rank_and_crowding(pop: List[Individual]) -> List[List[Individual]]:
    """Aplica non-dominated sort e crowding distance em toda a população; retorna fronteiras."""
    fronts = fast_non_dominated_sort(pop)
    for front in fronts:
        crowding_distance_assignment(front)
    return fronts


def _select_next_population(
    fronts: List[List[Individual]], target_size: int
) -> List[Individual]:
    """
    Preenche P_next com fronteiras em ordem de rank. Fronteira que "transborda"
    é ordenada por crowding desc e truncada ao tamanho restante.
    """
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
        mutate(child)   # calls invalidate_fitness() → resets objectives; rank/crowding default to None
        offspring.append(child)
    return offspring


def _log_generation(stats: GenerationStats, verbose: bool) -> None:
    if not verbose:
        return
    bals, mats, drfs = stats.best_per_objective
    print(
        f"Gen {stats.generation:4d} | "
        f"front0={stats.front_sizes[0]:3d}  "
        f"bal={bals:.4f}  mat={mats:.4f}  drift={drfs:.4f}  "
        f"({stats.elapsed_s:.1f}s)"
    )


def run(
    seed:          Optional[int] = None,
    pop_size:      int           = NSGA2_POP_SIZE,
    n_generations: int           = NSGA2_GENERATIONS,
    verbose:       bool          = True,
) -> NSGAResult:
    """Executa o NSGA-II e retorna a fronteira + 5 representantes."""
    if seed is not None:
        random.seed(seed)

    t_start = time.time()

    population = [Individual.from_canonical()] + [
        Individual.random() for _ in range(pop_size - 1)
    ]
    _evaluate_population(population)
    _assign_rank_and_crowding(population)

    history: List[GenerationStats] = []

    for gen in range(n_generations):
        offspring = _generate_offspring(population, pop_size)
        _evaluate_population(offspring)

        combined = population + offspring
        fronts   = _assign_rank_and_crowding(combined)
        population = _select_next_population(fronts, pop_size)

        best_per_obj = [min(ind.objectives[m] for ind in population) for m in range(3)]
        stats = GenerationStats(
            generation=gen,
            front_sizes=[len(f) for f in fronts],
            best_per_objective=best_per_obj,
            elapsed_s=time.time() - t_start,
        )
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


def save_results(result: NSGAResult, path: str = "results/nsga2_results.json") -> None:
    """
    Salva fronteira, representantes e histórico em JSON.
    """
    data = {
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
                "gen":                s.generation,
                "front_sizes":        s.front_sizes,
                "best_per_objective": s.best_per_objective,
                "elapsed_s":          round(s.elapsed_s, 3),
            }
            for s in result.history
        ],
    }
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
