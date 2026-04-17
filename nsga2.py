"""
NSGA-II — Algoritmo genético multi-objetivo (Deb et al., 2002).

Otimiza 3 objetivos simultaneamente:
  f1 = balance_error             (equilíbrio agregado — WR médio)
  f2 = matchup_dominance_penalty (pior matchup direto)
  f3 = drift_penalty             (preservação de arquétipo)

Todos minimizados, todos em [0, 1].
"""
from __future__ import annotations

from typing import List

from individual import Individual


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
