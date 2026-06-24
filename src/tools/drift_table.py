"""
Tabela de drift — decompõe o `drift_penalty` por personagem e por gene.

Para cada personagem mostra, gene a gene, o valor canônico vs o evoluído, o Δ
absoluto e o Δ normalizado. A normalização é a **mesma do fitness**: atributos
divididos pelo máximo do bound, pesos crus (já em [0, 1]). O desvio por
personagem (`deviation_i`) é obtido de `fitness._archetype_deviation` — portanto
idêntico ao que entra no `drift_penalty` — e a média dos 5 é o próprio
`drift_penalty`.

Uso:
    py -m src.tools.drift_table              # canônico (sanity — drift ≈ 0)
    py -m src.tools.drift_table --evolved    # melhor indivíduo do AG (results.json)
    py -m src.tools.drift_table --nsga2 [REP]  # representante do NSGA-II
"""

from __future__ import annotations

import argparse
import math
from typing import List, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import ATTRIBUTE_BOUNDS, ATTRIBUTE_NAMES, WEIGHT_NAMES
from src.engine.fitness import _archetype_deviation  # single source do deviation_i
from src.engine.individual import Individual

# Mesma referência de normalização usada em fitness._archetype_deviation.
_ATTR_MAXES: List[float] = [hi for _, hi in ATTRIBUTE_BOUNDS]


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (results.json)"
    return Individual.from_canonical(), "CANÔNICO (sanity — drift ≈ 0)"


def _bar(v: float, w: int = 20, vmax: float = 0.5) -> str:
    filled = max(0, min(w, int((v / vmax) * w)))
    return "█" * filled + "░" * (w - filled)


def _norm_genes(char) -> List[float]:
    """Vetor de genes normalizados (mesma convenção do drift: atributos /máx, pesos crus)."""
    return [a / m for a, m in zip(char.attributes, _ATTR_MAXES)] + list(char.weights)


def _mean_pairwise_distance(ind: Individual) -> float:
    """Distância euclidiana média entre os 5 personagens (mede homogeneização):
    baixa vs o canônico = os 5 convergiram entre si."""
    vecs = [_norm_genes(c) for c in ind.characters]
    dists = [
        math.sqrt(sum((x - y) ** 2 for x, y in zip(vecs[i], vecs[j])))
        for i in range(len(vecs)) for j in range(i + 1, len(vecs))
    ]
    return sum(dists) / len(dists) if dists else 0.0


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tabela de drift por gene e por personagem")
    parser.add_argument(
        "--evolved", action="store_true",
        help="Usa o melhor indivíduo salvo em results.json (default: canônico)",
    )
    parser.add_argument(
        "--nsga2", metavar="REP", nargs="?", const="knee_point",
        help="Usa representante do NSGA-II "
             "(knee_point|best_dominance|best_drift|ideal_point). Default: knee_point",
    )
    return parser


def print_drift_report(ind: Individual, label: str) -> None:
    print("\n" + "═" * 72)
    print(f"  TABELA DE DRIFT — {label}")
    print("  Δ norm: atributos por /máx do bound, pesos crus (idêntico ao drift_penalty)")
    print("═" * 72)

    deviations: List[float] = []
    for aid in ARCHETYPE_ORDER:
        char          = ind.get(aid)
        canon_attrs   = list(char.archetype.initial_attributes)
        canon_weights = list(char.archetype.initial_weights)
        dev           = _archetype_deviation(char)
        deviations.append(dev)

        print(f"\n  {ARCHETYPES[aid].name}")
        print(f"    {'gene':18}{'canônico':>10}{'evoluído':>10}{'Δ':>10}{'Δ norm':>9}")
        print(f"    {'─' * 57}")
        for name, c, e, m in zip(ATTRIBUTE_NAMES, canon_attrs, char.attributes, _ATTR_MAXES):
            d = e - c
            print(f"    {name:18}{c:>10.2f}{e:>10.2f}{d:>+10.2f}{d / m:>+9.3f}")
        for name, c, e in zip(WEIGHT_NAMES, canon_weights, char.weights):
            d = e - c
            print(f"    {name:18}{c:>10.2f}{e:>10.2f}{d:>+10.2f}{d:>+9.3f}")
        print(f"    {'─' * 57}")
        print(f"    desvio (deviation_i): {dev:.4f}")

    print("\n" + "═" * 72)
    print("  RESUMO — desvio por personagem")
    print("═" * 72 + "\n")
    for aid, dev in zip(ARCHETYPE_ORDER, deviations):
        print(f"  {ARCHETYPES[aid].name:14} [{_bar(dev)}] {dev:.4f}")
    mean_dev = sum(deviations) / len(deviations)
    print(f"\n  drift_penalty (média dos 5): {mean_dev:.4f}")

    # Diferenciação entre personagens (homogeneização) — distância par-a-par dos 5.
    diff = _mean_pairwise_distance(ind)
    diff_canon = _mean_pairwise_distance(Individual.from_canonical())
    ratio = diff / diff_canon if diff_canon > 0 else 1.0
    print(f"\n  Diferenciação (distância média par-a-par dos 5 personagens):")
    print(f"    canônico {diff_canon:.3f}  |  este {diff:.3f}  |  ratio {ratio:.2f}")
    print(f"    ratio ~1 = diferenciação preservada;  < 1 = homogeneização (os 5 convergiram)")


def main() -> None:
    args = _build_argparser().parse_args()
    ind, label = _load_individual(args)
    print_drift_report(ind, label)


if __name__ == "__main__":
    main()
