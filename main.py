"""
Ponto de entrada do experimento.
Rode com: python main.py [--seed N] [--quiet] [--log-every N]
"""

import argparse
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ga import run, log_matchup_matrix
from archetypes import ARCHETYPE_ORDER, ARCHETYPES


def parse_args():
    parser = argparse.ArgumentParser(description="AG para balanceamento de personagens")
    parser.add_argument("--seed",      type=int, default=None, help="Semente aleatória")
    parser.add_argument("--quiet",     action="store_true",    help="Suprime log por geração")
    parser.add_argument("--log-every", type=int, default=1,    help="Loga a cada N gerações")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run(
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


if __name__ == "__main__":
    main()
