"""
MAP-Elites para análise do espaço de soluções.

Mapeia o trade-off balance_error × drift_penalty usando qualidade = matchup_dominance_penalty.
Rode com: py map_elites.py

Saída:
  - Heatmap ASCII do grid (80 células: 10 × 8)
  - Fronteira de trade-off empírica
  - Sugestão calibrada de LAMBDA_DRIFT e LAMBDA_MATCHUP para o GA principal
"""
from __future__ import annotations

import math
import random
import argparse
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Tuple
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from individual import Individual
from fitness import FitnessDetail, evaluate_detail
from operators import mutate
from config import N_WORKERS

# ─── Constantes do grid ───────────────────────────────────────────────────────

GRID_X_BINS = 10     # balance_error
GRID_Y_BINS = 8      # drift_penalty
GRID_X_MAX  = 0.5    # máximo teórico de balance_error
GRID_Y_MAX  = 0.6    # máximo observado de drift_penalty

N_INIT       = 200
N_ITERATIONS = 50_000

Archive = Dict[Tuple[int, int], Tuple[Individual, FitnessDetail]]


# ─── Grid ─────────────────────────────────────────────────────────────────────

def _bucket(val: float, lo: float, hi: float, n: int) -> int:
    """Mapeia val em [lo, hi) para índice de bucket [0, n-1]. Faz clamp nos extremos."""
    if val >= hi:
        return n - 1
    if val < lo:
        return 0
    return int((val - lo) / (hi - lo) * n)


def _place(archive: Archive, ind: Individual, detail: FitnessDetail) -> None:
    """Insere ind no archive se a célula estiver vazia ou se a qualidade for melhor."""
    bx  = _bucket(detail.balance_error, 0.0, GRID_X_MAX, GRID_X_BINS)
    by  = _bucket(detail.drift_penalty,  0.0, GRID_Y_MAX, GRID_Y_BINS)
    key = (bx, by)
    if key not in archive or detail.matchup_dominance_penalty < archive[key][1].matchup_dominance_penalty:
        archive[key] = (ind, detail)


# ─── Avaliação e mutação ──────────────────────────────────────────────────────

def _evaluate(ind: Individual) -> FitnessDetail:
    """Avalia um indivíduo e retorna FitnessDetail completo."""
    return evaluate_detail(ind)


def _mutate_from(ind: Individual) -> Individual:
    """Clona ind e aplica mutação gaussiana. O original não é modificado."""
    child = ind.clone()
    mutate(child)
    return child


def _evaluate_batch(population: List[Individual]) -> List[FitnessDetail]:
    """
    Avalia uma lista de indivíduos em paralelo (reutiliza N_WORKERS de config).
    Retorna FitnessDetail para cada indivíduo, na mesma ordem.
    """
    if N_WORKERS == 1:
        return [evaluate_detail(ind) for ind in population]
    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        return list(executor.map(evaluate_detail, population))


# ─── Análise do archive ───────────────────────────────────────────────────────

def _compute_frontier(archive: Archive) -> List[Optional[Tuple[int, int]]]:
    """
    Para cada bucket de drift_penalty (by), retorna a célula com menor balance_error (bx).
    Retorna lista de comprimento GRID_Y_BINS; None onde o bucket de drift está vazio.
    """
    result: List[Optional[Tuple[int, int]]] = []
    for by in range(GRID_Y_BINS):
        best_bx: Optional[int] = None
        for bx in range(GRID_X_BINS):
            if (bx, by) in archive:
                if best_bx is None or bx < best_bx:
                    best_bx = bx
        result.append((best_bx, by) if best_bx is not None else None)
    return result


def _find_knee(points: List[Tuple[float, float]]) -> int:
    """
    Retorna o índice do joelho numa lista de (balance_error, drift_penalty)
    usando o método de maior distância perpendicular à reta que conecta
    o primeiro e o último ponto.
    """
    if len(points) < 3:
        return len(points) // 2
    x1, y1 = points[0]
    x2, y2 = points[-1]
    dx, dy  = x2 - x1, y2 - y1
    length  = math.sqrt(dx * dx + dy * dy)
    if length < 1e-9:
        return 0
    best_dist, knee = -1.0, 0
    for i, (x, y) in enumerate(points):
        dist = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / length
        if dist > best_dist:
            best_dist, knee = dist, i
    return knee
