"""
Tabela de drift — decompõe o `drift_penalty` por personagem e por gene.

Para cada personagem mostra, gene a gene, o valor canônico vs o evoluído, o Δ
absoluto, o Δ normalizado e o peso do gene no drift. A normalização é a **mesma do
fitness** (`fitness.gene_drift`): fração do range do bound, `(x − lo) / (hi − lo)`.
Genes marcados com ★ são os `defining_genes` do arquétipo e pesam
`DRIFT_DEFINING_WEIGHT`× no desvio. O desvio por personagem (`deviation_i`) vem de
`fitness._archetype_deviation` — portanto idêntico ao que entra no `drift_penalty`
— e a média dos 5 é o próprio `drift_penalty`.

Os 3 pesos comportamentais aparecem marcados com `~`: eles são comparados
**reescalados** para a soma canônica (`fitness.drift_genes`), porque só a razão entre
eles afeta o combate. A coluna `evoluído` mostra o valor cru; a `Δ norm` sai da forma
comparada, que é a que soma no `deviation_i`.

Uso:
    py -m src.analysis.drift_table              # canônico (sanity — drift ≈ 0)
    py -m src.analysis.drift_table --evolved    # melhor indivíduo do AG (single_run/ga.json)
    py -m src.analysis.drift_table --nsga2 [REP]  # representante do NSGA-II
"""

from __future__ import annotations

import argparse
import math
from typing import List, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import ATTRIBUTE_BOUNDS, GENE_NAMES
from src.engine.fitness import (  # single source do deviation_i e da normalização
    N_WEIGHT_GENES,
    _archetype_deviation,
    canonical_genes,
    drift_genes,
    drift_weights,
    gene_drift,
)
from src.engine.individual import Individual


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (single_run/ga.json)"
    return Individual.from_canonical(), "CANÔNICO (sanity — drift ≈ 0)"


def _bar(v: float, w: int = 20, vmax: float = 0.5) -> str:
    filled = max(0, min(w, int((v / vmax) * w)))
    return "█" * filled + "░" * (w - filled)


def _norm_genes(char) -> List[float]:
    """Vetor comparável entre personagens: atributos normalizados pelo range do bound
    (mesma convenção do drift) e os pesos como probabilidade de intenção — só a razão
    entre eles age no combate, então a escala não pode contar como diferença."""
    attributes = [(g - lo) / (hi - lo) for g, (lo, hi) in zip(char.attributes, ATTRIBUTE_BOUNDS)]
    return attributes + char.intention_probabilities()


def mean_pairwise_distance(ind: Individual) -> float:
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
        help="Usa o melhor indivíduo salvo em single_run/ga.json (default: canônico)",
    )
    parser.add_argument(
        "--nsga2", metavar="REP", nargs="?", const="knee_point",
        help="Usa representante do NSGA-II "
             "(knee_point|best_dominance|best_drift|ideal_point|scalar_optimum). Default: knee_point",
    )
    return parser


def print_drift_report(ind: Individual, label: str) -> None:
    print("\n" + "═" * 72)
    print(f"  TABELA DE DRIFT — {label}")
    print("  Δ norm: fração do range do bound;  ★ = gene definidor (pesa mais no drift)")
    print("═" * 72)

    deviations: List[float] = []
    for aid in ARCHETYPE_ORDER:
        char    = ind.get(aid)
        dev     = _archetype_deviation(char)
        weights = drift_weights(char.archetype)
        deviations.append(dev)

        # `Δ norm` tem de sair de `drift_genes` — a mesma forma que o
        # `_archetype_deviation` compara — senão a coluna não soma no total: os 3
        # pesos entram reescalados para a soma canônica (só a razão afeta o combate).
        compared = drift_genes(char)

        print(f"\n  {ARCHETYPES[aid].name}")
        print(f"    {'gene':18}{'canônico':>10}{'evoluído':>10}{'Δ':>10}{'Δ norm':>9}{'peso':>7}")
        print(f"    {'─' * 64}")
        for i, (name, c, e, w) in enumerate(
            zip(GENE_NAMES, canonical_genes(char.archetype), char.genes(), weights)
        ):
            mark = "★" if name in char.archetype.defining_genes else " "
            rescaled = compared[i] != e
            print(f"    {mark} {name:16}{c:>10.2f}{e:>10.2f}{e - c:>+10.2f}"
                  f"{gene_drift(compared[i], c, i):>+9.3f}{w:>7.1f}"
                  f"{'  ~' if rescaled else ''}")
        print(f"    {'─' * 64}")
        raw_sum = sum(char.genes()[-N_WEIGHT_GENES:])
        if raw_sum > 0:
            k = sum(canonical_genes(char.archetype)[-N_WEIGHT_GENES:]) / raw_sum
            print(f"    ~ pesos comparados reescalados por k={k:.3f} (soma canônica);"
                  f" só a razão afeta o combate")
        print(f"    desvio (deviation_i): {dev:.4f}")

    print("\n" + "═" * 72)
    print("  RESUMO — desvio por personagem")
    print("═" * 72 + "\n")
    for aid, dev in zip(ARCHETYPE_ORDER, deviations):
        print(f"  {ARCHETYPES[aid].name:14} [{_bar(dev)}] {dev:.4f}")
    mean_dev = sum(deviations) / len(deviations)
    print(f"\n  drift_penalty (média dos 5): {mean_dev:.4f}")

    # Diferenciação entre personagens (homogeneização) — distância par-a-par dos 5.
    diff = mean_pairwise_distance(ind)
    diff_canon = mean_pairwise_distance(Individual.from_canonical())
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
