"""
Dossiê de avaliação de um indivíduo — UM comando que compõe os tools de avaliação
num relatório único:

  • cabeçalho: fitness, drift_penalty, dominance_penalty
  • matchups: matriz de WR + WR global + ciclo (equilíbrio)
  • drift por gene + diferenciação (identidade de genes + homogeneização)
  • fingerprint (identidade comportamental)
  • validador estrutural (identidade de ranking)
  • modelos nulos: a posição de cada métrica entre piso e teto

A última seção é o que dá sentido às anteriores: nenhuma métrica de identidade do
projeto tem piso zero — rosters SEM estrutura nenhuma pontuam bem acima de zero no
validador e no drift —, então valor cru não diz nada sozinho. Os modelos nulos são
recalculados a cada execução (~2s), nunca lidos de cache. Ver [`baselines`](baselines.py).

Não duplica lógica — chama as funções dos tools existentes. Tools de propósito
diferente (sensitivity_analysis = validação do AG; viewer/web_viewer = visualização;
nsga2_plots = fronteira) ficam standalone, fora do dossiê.

Uso:
    py -m src.analysis.report              # canônico
    py -m src.analysis.report --evolved    # melhor do AG
    py -m src.analysis.report --nsga2 [REP]
"""

from __future__ import annotations

import argparse
from typing import List, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER
from src.engine.combat import seed_combat
from src.engine.config import IDENTITY_BEHAVIORAL_SIMS, MULTI_RUN_SIMS, MULTI_RUN_VALIDATION_SEED
from src.engine.fitness import evaluate_detail_n, set_seed_base
from src.engine.individual import Individual
from src.analysis.analyze_matchups import (
    MatchupRecord,
    analyze_combat_multi,
    build_record,
    print_aggregate_view,
    print_matchup_summary,
    print_matrix_view,
)
from src.analysis.archetype_validator import print_report, run_validation
from src.experiments.baselines import (
    N_RANDOM_DEFAULT,
    floors_and_ceilings,
    measure,
    print_position_table,
    print_reference_table,
    reference_rosters,
)
from src.analysis.drift_table import print_drift_report
from src.analysis.fingerprint import print_fingerprint_report


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str, bool]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})", False
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (single_run/ga.json)", False
    return Individual.from_canonical(), "CANÔNICO", True


def _print_header(ind: Individual, label: str, n: int, seed: int) -> None:
    # `evaluate_detail_n(ind, n)`, não `evaluate_detail`: esta última usa
    # SIMS_PER_MATCHUP e o cabeçalho anunciaria um `n` que não foi o usado.
    set_seed_base(seed)
    seed_combat(seed)
    d = evaluate_detail_n(ind, n)
    set_seed_base(None)
    print("\n" + "█" * 72)
    print(f"  DOSSIÊ DO INDIVÍDUO — {label}   (seed={seed}, n={n}/matchup)")
    print("█" * 72)
    print(f"  fitness = {d.fitness:+.4f}    drift_penalty = {d.drift_penalty:.4f}"
          f"    dominance_penalty = {d.dominance_penalty:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dossiê de avaliação de um indivíduo")
    parser.add_argument("--evolved", action="store_true", help="melhor do AG (single_run/ga.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="representante do NSGA-II (knee_point|best_dominance|best_drift|ideal_point|scalar_optimum)")
    # Os defaults são os do `baselines`: assim a tabela de nulos do dossiê é a mesma do
    # `baselines.json`, e não um segundo piso em circulação.
    parser.add_argument("--n", type=int, default=MULTI_RUN_SIMS,
                        help=f"sims por matchup (default: {MULTI_RUN_SIMS})")
    parser.add_argument("--seed", type=int, default=MULTI_RUN_VALIDATION_SEED,
                        help=f"semente de avaliação (default: {MULTI_RUN_VALIDATION_SEED})")
    parser.add_argument("--n-random", type=int, default=N_RANDOM_DEFAULT,
                        help="rosters aleatórios nos modelos nulos (mais = mais "
                             f"resolução no p-valor; default: {N_RANDOM_DEFAULT})")
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

    # 4. Identidade — estrutura + comportamento (Layers 1-3). Mesma medição que o
    # `baselines.measure` faz, para que o placar aqui seja o `valor` da tabela de posição.
    print()
    print_report(run_validation(ind, behavioral_n=IDENTITY_BEHAVIORAL_SIMS, seed=args.seed))

    # 5. Modelos nulos — o que os números acima valem contra um roster SEM estrutura.
    # Recalculado a cada execução (custa ~2s): baseline em cache silenciosamente
    # obsoleto é exatamente o erro que este dossiê existe para evitar.
    print()
    references = [
        (rlabel, role, measure(roster, args.n, args.seed))
        for rlabel, role, roster in reference_rosters(args.n_random, args.seed)
    ]
    print_reference_table(references)
    print_position_table(label, measure(ind, args.n, args.seed),
                         floors_and_ceilings(references))


if __name__ == "__main__":
    main()
