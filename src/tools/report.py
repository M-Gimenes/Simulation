"""
Dossiê de avaliação de um indivíduo — UM comando que compõe os tools de avaliação
num relatório único:

  • cabeçalho: fitness, drift_penalty, dominance_penalty
  • matchups: matriz de WR + WR global + ciclo (equilíbrio)
  • drift por gene + diferenciação (identidade de genes + homogeneização)
  • fingerprint (identidade comportamental)
  • validador estrutural (identidade de ranking)

Não duplica lógica — chama as funções dos tools existentes. Tools de propósito
diferente (sensitivity_analysis = validação do AG; viewer/web_viewer = visualização;
nsga2_plots = fronteira) ficam standalone, fora do dossiê.

Uso:
    py -m src.tools.report              # canônico
    py -m src.tools.report --evolved    # melhor do AG
    py -m src.tools.report --nsga2 [REP]
"""

from __future__ import annotations

import argparse
from typing import List, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER
from src.engine.combat import seed_combat
from src.engine.fitness import evaluate_detail, set_seed_base
from src.engine.individual import Individual
from src.tools.analyze_matchups import (
    MatchupRecord,
    analyze_combat_multi,
    build_record,
    print_aggregate_view,
    print_matchup_summary,
    print_matrix_view,
)
from src.tools.archetype_validator import print_report, run_validation
from src.tools.drift_table import print_drift_report
from src.tools.fingerprint import print_fingerprint_report

REPORT_SIMS = 200


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str, bool]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})", False
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (results.json)", False
    return Individual.from_canonical(), "CANÔNICO", True


def _print_header(ind: Individual, label: str, n: int, seed: int) -> None:
    set_seed_base(seed)
    d = evaluate_detail(ind)
    set_seed_base(None)
    print("\n" + "█" * 72)
    print(f"  DOSSIÊ DO INDIVÍDUO — {label}   (seed={seed}, n={n}/matchup)")
    print("█" * 72)
    print(f"  fitness = {d.fitness:+.4f}    drift_penalty = {d.drift_penalty:.4f}"
          f"    dominance_penalty = {d.dominance_penalty:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dossiê de avaliação de um indivíduo")
    parser.add_argument("--evolved", action="store_true", help="melhor do AG (results.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="representante do NSGA-II (knee_point|best_dominance|best_drift|ideal_point)")
    parser.add_argument("--n", type=int, default=REPORT_SIMS, help="sims por matchup")
    parser.add_argument("--seed", type=int, default=42, help="semente (reprodutibilidade)")
    args = parser.parse_args()

    ind, label, is_canon = _load_individual(args)
    seed_combat(args.seed)

    _print_header(ind, label, args.n, args.seed)

    # 1. Equilíbrio — round-robin de matchups
    chars = {c.archetype.id: c for c in ind.characters}
    records: List[MatchupRecord] = []
    for i in range(len(ARCHETYPE_ORDER)):
        for j in range(i + 1, len(ARCHETYPE_ORDER)):
            ia, ib = ARCHETYPE_ORDER[i], ARCHETYPE_ORDER[j]
            r = analyze_combat_multi(chars[ia], chars[ib], n=args.n)
            records.append(build_record(ia, ib, r))
    print_matrix_view(records, ARCHETYPE_ORDER)
    print_aggregate_view(records, ARCHETYPE_ORDER)
    print_matchup_summary(records, args.n)

    # 2. Identidade — genes + homogeneização
    print_drift_report(ind, label)

    # 3. Identidade — comportamento
    print_fingerprint_report(ind, label, is_canon, args.n, args.seed)

    # 4. Identidade — estrutura + comportamento (Layers 1-3)
    print()
    print_report(run_validation(ind, behavioral_n=args.n, seed=args.seed))


if __name__ == "__main__":
    main()
