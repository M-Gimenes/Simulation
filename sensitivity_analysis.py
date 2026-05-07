"""
Análise de sensibilidade — Δ WR por (arquétipo × atributo) ao perturbar genes em ±σ.

Atributos com |Δ| médio abaixo do piso binomial são genes neutros — o AG não os
enxerga via seleção. Usa pareamento de seeds: o mesmo seed do `random` é fixado
antes de cada par (+σ, -σ), isolando o efeito do gene do RNG.

Uso:
    py sensitivity_analysis.py
    py sensitivity_analysis.py --sims 500
    py sensitivity_analysis.py --sigma-mult 2
    py sensitivity_analysis.py --workers 1
"""

from __future__ import annotations

import argparse
import random
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple

from archetypes import ARCHETYPE_ORDER, ARCHETYPES
from config import ATTRIBUTE_BOUNDS, ATTRIBUTE_MUTATION_SIGMA, ATTRIBUTE_NAMES
from fitness import evaluate_detail_n
from individual import Individual


Task = Tuple[int, int, float, int, int]


def _eval_task(task: Task) -> float:
    char_idx, attr_idx, delta, sims, seed = task

    random.seed(seed)
    ind = Individual.from_canonical()
    char = ind.characters[char_idx]
    lo, hi = ATTRIBUTE_BOUNDS[attr_idx]
    char.attributes[attr_idx] = max(lo, min(hi, char.attributes[attr_idx] + delta))
    char.clip()
    ind.invalidate_fitness()

    detail = evaluate_detail_n(ind, sims=sims)
    return detail.winrates[char_idx]


def _classify(magnitude: float) -> str:
    if magnitude >= 0.05:
        return "✓ visível"
    if magnitude < 0.03:
        return "✗ neutro"
    return "~ borderline"


def _build_tasks(sigmas: List[float], sims: int, base_seed: int) -> List[Task]:
    tasks: List[Task] = []
    for i in range(len(ARCHETYPE_ORDER)):
        for j in range(len(ATTRIBUTE_NAMES)):
            seed = base_seed + i * 100 + j
            tasks.append((i, j, +sigmas[j], sims, seed))
            tasks.append((i, j, -sigmas[j], sims, seed))
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sims", type=int, default=200)
    parser.add_argument("--sigma-mult", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    sigmas = [
        ATTRIBUTE_MUTATION_SIGMA * (hi - lo) * args.sigma_mult
        for lo, hi in ATTRIBUTE_BOUNDS
    ]
    tasks = _build_tasks(sigmas, args.sims, args.seed)

    n_chars = len(ARCHETYPE_ORDER)
    n_attrs = len(ATTRIBUTE_NAMES)

    print("─" * 80)
    workers_label = "serial" if args.workers == 1 else f"{args.workers or 'auto'} workers"
    print(f"  Análise de sensibilidade — {args.sims} sims/matchup, σ × {args.sigma_mult}, {workers_label}")
    print(f"  {len(tasks)} avaliações ({n_chars} arquétipos × {n_attrs} atributos × 2 direções)")
    print("─" * 80)

    if args.workers == 1:
        results = [_eval_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            results = list(ex.map(_eval_task, tasks))

    deltas = [[0.0] * n_attrs for _ in range(n_chars)]
    for k, (char_idx, attr_idx, delta, _, _) in enumerate(tasks):
        wr = results[k]
        if delta > 0:
            deltas[char_idx][attr_idx] += wr
        else:
            deltas[char_idx][attr_idx] -= wr

    for i, aid in enumerate(ARCHETYPE_ORDER):
        name = ARCHETYPES[aid].name
        for j, attr_name in enumerate(ATTRIBUTE_NAMES):
            print(f"  {name:14} {attr_name:18} σ={sigmas[j]:>6.2f}  Δ={deltas[i][j]:+.1%}")
        print()

    # ── Matriz ────────────────────────────────────────────────────────────────

    print("═" * 80)
    print("  Matriz |Δ WR|  (linha = arquétipo perturbado, coluna = atributo)")
    print("═" * 80)
    header = f"  {'':14}" + "".join(f"{n[:6]:>8}" for n in ATTRIBUTE_NAMES) + f"  {'média':>7}"
    print(header)
    print("  " + "─" * (len(header) - 2))

    col_means = [0.0] * n_attrs
    for i, aid in enumerate(ARCHETYPE_ORDER):
        row = [abs(d) for d in deltas[i]]
        print(f"  {ARCHETYPES[aid].name:14}"
              + "".join(f"{v:>8.1%}" for v in row)
              + f"  {sum(row)/n_attrs:>7.1%}")
        for j in range(n_attrs):
            col_means[j] += row[j] / n_chars

    print("  " + "─" * (len(header) - 2))
    print(f"  {'média':14}" + "".join(f"{m:>8.1%}" for m in col_means))

    # ── Ranking ───────────────────────────────────────────────────────────────

    print()
    print("═" * 80)
    print("  Ranking de sensibilidade — atributos ordenados por |Δ WR| médio")
    print("═" * 80)
    print(f"  Piso de ruído binomial estimado: ±{(0.25 / (4 * args.sims)) ** 0.5:.1%}")
    print(f"  (4 matchups × {args.sims} sims = {4 * args.sims} simulações por personagem)")
    print()

    ranked = sorted(zip(ATTRIBUTE_NAMES, col_means), key=lambda x: x[1], reverse=True)
    for name, m in ranked:
        print(f"    {name:18} {m:>6.1%}  {_classify(m)}")


if __name__ == "__main__":
    main()
