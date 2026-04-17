"""
Ponto de entrada do experimento.
Rode com: py main.py [--algorithm ga|nsga2] [--seed N] [--quiet] [--log-every N] [--plot-3d]
"""

import argparse
import json
import sys
import os
import datetime
sys.path.insert(0, os.path.dirname(__file__))

from ga import run as run_ga, log_matchup_matrix
from archetypes import ARCHETYPE_ORDER, ARCHETYPES


def parse_args():
    parser = argparse.ArgumentParser(description="AG para balanceamento de personagens")
    parser.add_argument("--algorithm", choices=["ga", "nsga2"], default="ga",
                        help="Algoritmo evolutivo (default: ga)")
    parser.add_argument("--seed",      type=int, default=None, help="Semente aleatória")
    parser.add_argument("--quiet",     action="store_true",    help="Suprime log por geração")
    parser.add_argument("--log-every", type=int, default=1,    help="Loga a cada N gerações (só AG)")
    parser.add_argument("--plot-3d",   action="store_true",    help="Gera plot 3D adicional (só NSGA-II)")
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
        print(f"    def={char.defense:.1f}  stun={char.stun:.1f}  kb={char.knockback:.1f}  rec={char.recovery:.1f}")
        print(f"    w=[ret={char.w_retreat:.2f}  def={char.w_defend:.2f}  agg={char.w_aggressiveness:.2f}]")
        print()

    print("\n=== Matriz de matchup (WR direto) ===\n")
    log_matchup_matrix(result.best_detail, indent="  ")
    print()
    print(f"  Células: WR da linha contra a coluna (verde ≥55%, vermelho ≤45%)")

    print(f"Parada: {result.stop_reason}")
    print(f"Geração: {result.generation}")
    print(f"Fitness: {result.best.fitness:+.4f}")
    print(f"Balance error:             {result.best_detail.balance_error:.4f}")
    print(f"Matchup dominance penalty: {result.best_detail.matchup_dominance_penalty:.4f}")

    out = {"best_individual": [c.genes() for c in result.best.characters]}
    with open("results.json", "w") as fh:
        json.dump(out, fh)
    print("\nIndivíduo salvo em results.json")


def _main_nsga2(args):
    from nsga2 import run as run_nsga2, save_results
    from nsga2_plots import save_plots

    result = run_nsga2(seed=args.seed, verbose=not args.quiet)

    save_results(result, "nsga2_results.json")
    print(f"\nFronteira salva em nsga2_results.json  ({len(result.pareto_front)} indivíduos)")

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = os.path.join("plots", "nsga2", timestamp)
    save_plots(result, outdir, plot_3d=args.plot_3d)
    print(f"Plots salvos em {outdir}")

    print("\n=== Representantes da fronteira ===\n")
    for name, ind in result.representatives.items():
        bal, mat, drf = ind.objectives
        print(f"  {name:15s}  bal={bal:.4f}  mat={mat:.4f}  drift={drf:.4f}")


def main():
    args = parse_args()
    if args.algorithm == "ga":
        _main_ga(args)
    else:
        _main_nsga2(args)


if __name__ == "__main__":
    main()
