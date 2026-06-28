"""
Ponto de entrada do experimento.
Rode com: py main.py [--algorithm ga|nsga2] [--seed N] [--quiet] [--log-every N] [--plot-3d]
"""

import argparse
import datetime
import json

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.ga import run as run_ga, log_matchup_matrix
from src.engine.paths import GA_RESULTS_PATH, NSGA2_PLOTS_DIR, NSGA2_RESULTS_PATH, PROJECT_ROOT, RESULTS_DIR


def parse_args():
    parser = argparse.ArgumentParser(description="AG para balanceamento de personagens")
    parser.add_argument("--algorithm", choices=["ga", "nsga2"], default="ga",
                        help="Algoritmo evolutivo (default: ga)")
    parser.add_argument("--seed",      type=int, default=None, help="Semente aleatória")
    parser.add_argument("--quiet",     action="store_true",    help="Suprime log por geração")
    parser.add_argument("--log-every", type=int, default=1,    help="Loga a cada N gerações (só AG)")
    return parser.parse_args()


def _main_ga(args):
    result = run_ga(
        seed=args.seed,
        verbose=not args.quiet,
        log_every=args.log_every,
    )

    print("\n=== Personagens evoluídos ===\n")
    for i, aid in enumerate(ARCHETYPE_ORDER):
        char = result.best.get(aid)
        wr   = result.best_detail.winrates[i]
        print(f"  {ARCHETYPES[aid].name}")
        print(f"    WR: {wr:.1%}  |  hp={char.hp:.1f}  dmg={char.damage:.1f}  "
              f"cd={char.attack_cooldown:.1f}  rng={char.range_:.1f}  spd={char.speed:.1f}")
        print(f"    stun={char.stun:.2f}  kb={char.knockback:.1f}")
        print(f"    w=[ret={char.w_retreat:.2f}  def={char.w_defend:.2f}  agg={char.w_aggressiveness:.2f}]")
        print()

    print("\n=== Matriz de matchup (WR direto) ===\n")
    log_matchup_matrix(result.best_detail, indent="  ")
    print()
    print(f"  Células: WR da linha contra a coluna (verde ≥55%, vermelho ≤45%)")

    print(f"Parada: {result.stop_reason}")
    print(f"Geração: {result.generation}")
    print(f"Fitness: {result.best.fitness:+.4f}")
    print(f"Dominance penalty:      {result.best_detail.dominance_penalty:.4f}")
    print(f"Drift penalty:          {result.best_detail.drift_penalty:.4f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = {"best_individual": [c.genes() for c in result.best.characters]}
    with open(GA_RESULTS_PATH, "w") as fh:
        json.dump(out, fh)
    print(f"\nIndivíduo salvo em {GA_RESULTS_PATH.relative_to(PROJECT_ROOT)}")


def _main_nsga2(args):
    from src.engine.config import HYPERVOLUME_REFERENCE
    from src.engine.nsga2 import run as run_nsga2, save_results
    from src.engine.pareto_metrics import hypervolume_2d, spacing
    from src.tools.nsga2_plots import save_plots

    result = run_nsga2(seed=args.seed, verbose=not args.quiet)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_results(result, NSGA2_RESULTS_PATH)
    print(f"\nFronteira salva em {NSGA2_RESULTS_PATH.relative_to(PROJECT_ROOT)}  ({len(result.pareto_front)} indivíduos)")

    objs = [ind.objectives for ind in result.pareto_front]
    hv = hypervolume_2d(objs, HYPERVOLUME_REFERENCE)
    sp = spacing(objs)
    print(f"Hipervolume (ref={HYPERVOLUME_REFERENCE}): {hv:.4f}  |  spacing: {sp:.4f}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = NSGA2_PLOTS_DIR / timestamp
    save_plots(result, outdir)
    print(f"Plots salvos em {outdir.relative_to(PROJECT_ROOT)}")

    print("\n=== Representantes da fronteira ===\n")
    for name, ind in result.representatives.items():
        dom, drift = ind.objectives
        print(f"  {name:15s}  dom={dom:.4f}  drift={drift:.4f}")


def main():
    args = parse_args()
    if args.algorithm == "ga":
        _main_ga(args)
    else:
        _main_nsga2(args)


if __name__ == "__main__":
    main()
