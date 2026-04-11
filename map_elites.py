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


def _suggest_lambdas(archive: Archive) -> Dict[str, float]:
    """
    Sugere LAMBDA_DRIFT e LAMBDA_MATCHUP baseado na fronteira empírica do archive.

    LAMBDA_DRIFT   = |Δbalance_error / Δdrift_penalty| no joelho da fronteira.
                     Representa quanto equilíbrio se ganha por unidade de drift permitido.
    LAMBDA_MATCHUP = 1 / range(matchup_pen na fronteira).
                     Normaliza a penalidade de matchup para escala comparável ao balance_error.
    """
    frontier = _compute_frontier(archive)
    points:     List[Tuple[float, float]] = []
    pen_values: List[float]               = []

    for cell in frontier:
        if cell is not None:
            _, detail = archive[cell]
            points.append((detail.balance_error, detail.drift_penalty))
            pen_values.append(detail.matchup_dominance_penalty)

    if len(points) < 2:
        return {"LAMBDA_DRIFT": 0.5, "LAMBDA_MATCHUP": 1.0, "LAMBDA": 0.2}

    knee = _find_knee(points)
    i    = knee

    if 0 < i < len(points) - 1:
        d_bal   = abs(points[i + 1][0] - points[i - 1][0])
        d_drift = abs(points[i + 1][1] - points[i - 1][1])
    elif i == 0:
        d_bal   = abs(points[1][0] - points[0][0])
        d_drift = abs(points[1][1] - points[0][1])
    else:
        d_bal   = abs(points[-1][0] - points[-2][0])
        d_drift = abs(points[-1][1] - points[-2][1])

    lambda_drift = round(d_bal / d_drift, 3) if d_drift > 1e-6 else 0.0

    pen_range      = max(pen_values) - min(pen_values) if pen_values else 0.5
    lambda_matchup = round(1.0 / max(pen_range, 0.1), 2)

    return {"LAMBDA_DRIFT": lambda_drift, "LAMBDA_MATCHUP": lambda_matchup, "LAMBDA": 0.2}


# ─── Output ───────────────────────────────────────────────────────────────────

def _print_heatmap(archive: Archive) -> None:
    """Imprime heatmap ASCII do grid. Cada célula mostra matchup_dominance_penalty."""
    col_w    = 6
    x_labels = [f"{GRID_X_MAX * (bx + 0.5) / GRID_X_BINS:.2f}" for bx in range(GRID_X_BINS)]

    print("\n=== Heatmap: matchup_dominance_penalty (.. = vazia, menor = melhor) ===\n")
    print(f"  drift  |  " + "".join(f"{v:>{col_w}}" for v in x_labels))
    print(f"         |  " + "-" * (col_w * GRID_X_BINS))

    for by in range(GRID_Y_BINS - 1, -1, -1):   # alto drift no topo
        y_center = GRID_Y_MAX * (by + 0.5) / GRID_Y_BINS
        row      = f"  {y_center:.3f}  |  "
        for bx in range(GRID_X_BINS):
            if (bx, by) in archive:
                val  = archive[(bx, by)][1].matchup_dominance_penalty
                row += f"{val:>{col_w}.2f}"
            else:
                row += f"{'..':<{col_w}}"
        print(row)

    print(f"         |")
    print(f"  bal_err:  " + "".join(f"{v:>{col_w}}" for v in x_labels))
    print(f"{'':30s}balance_error ->\n")


def _print_frontier(archive: Archive) -> None:
    """Imprime fronteira de trade-off e marca o joelho."""
    frontier = _compute_frontier(archive)
    points: List[Tuple[float, float, float]] = []   # (balance_error, drift, matchup_pen)

    for cell in frontier:
        if cell is not None:
            _, detail = archive[cell]
            points.append((detail.balance_error, detail.drift_penalty, detail.matchup_dominance_penalty))

    print("=== Frontier trade-off (best balance_error per drift level) ===\n")

    if not points:
        print("  (nenhuma célula preenchida)")
        return

    knee = _find_knee([(p[0], p[1]) for p in points])

    for i, (bal, drift, pen) in enumerate(points):
        marker = "  <- joelho" if i == knee else ""
        print(f"  drift={drift:.3f}  ->  balance_error={bal:.3f}   matchup_pen={pen:.2f}{marker}")
    print()


# ─── Loop principal ───────────────────────────────────────────────────────────

def run_map_elites(
    seed:         Optional[int] = None,
    n_init:       int           = N_INIT,
    n_iterations: int           = N_ITERATIONS,
    verbose:      bool          = True,
) -> Archive:
    """
    Executa o MAP-Elites completo.

    Args:
        seed:         semente para reprodutibilidade (None = aleatório).
        n_init:       indivíduos avaliados na inicialização.
        n_iterations: iterações do loop principal.
        verbose:      imprime progresso a cada 1.000 iterações.

    Returns:
        Archive preenchido: Dict[(bx, by), (Individual, FitnessDetail)].
    """
    if seed is not None:
        random.seed(seed)

    archive: Archive = {}

    # ── Inicialização ─────────────────────────────────────────────────────────
    if verbose:
        print(f"Inicializando {n_init} indivíduos (paralelo com N_WORKERS={N_WORKERS})...")

    init_pop = [Individual.from_canonical()] + [Individual.random() for _ in range(n_init - 1)]
    details  = _evaluate_batch(init_pop)

    for ind, detail in zip(init_pop, details):
        _place(archive, ind, detail)

    if verbose:
        print(f"Archive inicial: {len(archive)}/{GRID_X_BINS * GRID_Y_BINS} células\n")

    # ── Loop ──────────────────────────────────────────────────────────────────
    for iteration in range(1, n_iterations + 1):
        key    = random.choice(list(archive.keys()))
        parent = archive[key][0]
        child  = _mutate_from(parent)
        detail = _evaluate(child)
        _place(archive, child, detail)

        if verbose and iteration % 1000 == 0:
            best_bal   = min(d.balance_error  for _, d in archive.values())
            best_drift = min(d.drift_penalty  for _, d in archive.values())
            print(
                f"[{iteration:6d}/{n_iterations}]  "
                f"células={len(archive):2d}/{GRID_X_BINS * GRID_Y_BINS}  "
                f"melhor_bal={best_bal:.3f}  melhor_drift={best_drift:.3f}"
            )

    return archive


# ─── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MAP-Elites -- análise do espaço de soluções")
    parser.add_argument("--seed",         type=int, default=None, help="Semente aleatória")
    parser.add_argument("--n-init",       type=int, default=N_INIT,       help="Indivíduos iniciais")
    parser.add_argument("--n-iterations", type=int, default=N_ITERATIONS, help="Iterações do loop")
    parser.add_argument("--quiet",        action="store_true",            help="Suprime progresso")
    args = parser.parse_args()

    archive = run_map_elites(
        seed=args.seed,
        n_init=args.n_init,
        n_iterations=args.n_iterations,
        verbose=not args.quiet,
    )

    _print_heatmap(archive)
    _print_frontier(archive)

    lambdas = _suggest_lambdas(archive)
    print("=== Calibração sugerida de lambdas ===\n")
    print(f"  LAMBDA_DRIFT   = {lambdas['LAMBDA_DRIFT']}")
    print(f"  LAMBDA_MATCHUP = {lambdas['LAMBDA_MATCHUP']}")
    print(f"  LAMBDA         = {lambdas['LAMBDA']}  (mantém -- attribute_cost não afeta o trade-off central)")
    print()


if __name__ == "__main__":
    main()
