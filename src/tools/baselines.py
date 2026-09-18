"""baselines.py — modelos nulos: o que cada métrica marca SEM estrutura nenhuma.

Toda métrica de identidade do projeto vinha sendo lida contra o **teto** (o canônico),
como se o piso fosse zero. Nenhuma tem piso zero:

  • validador  — cinco personagens IDÊNTICOS (identidade zero por construção) tiram
    6–9/23, e rosters aleatórios chegam a 10/23, porque asserção de ranking com empate
    se resolve por ordem de índice e algumas acertam por acidente;
  • drift      — o espelho dá ~0.38 e um roster aleatório ~0.42, então entre
    "identidade preservada" e "aniquilação total" cabem ~0.04;
  • ciclo      — cada aresta é cara-ou-coroa, então o acaso já entrega 5/10.

Os valores exatos dependem da semente de avaliação: por isso o piso é reportado como
**distribuição** (média, pior nulo, p-valor empírico) e recalculado junto do alvo, nunca
fixado como constante.

Ler `13/23` como "57% da identidade sobreviveu" é o mesmo erro de ler 20% numa prova de
cinco alternativas como "sabe 20% da matéria". Este tool mede o piso e reporta cada
métrica como **posição entre piso e teto**.

Rosters de referência:
  canônico   identidade intacta, equilíbrio terrível  → o TETO de identidade
  espelho    5 cópias do mesmo arquétipo: equilíbrio perfeito, identidade zero
             → o PISO de identidade, e a resposta à objeção "por que não deixar
               todos iguais?", que precisa ser numérica e não retórica
  aleatório  sem projeto nenhum → o chão absoluto

Uso:
    py -m src.tools.baselines                    # só os baselines
    py -m src.tools.baselines --evolved          # + posiciona o melhor do AG
    py -m src.tools.baselines --nsga2 scalar_optimum
    py -m src.tools.baselines --n-random 60 --sims 400   # mais resolução no p
"""

from __future__ import annotations

import argparse
import json
import random
from itertools import combinations
from math import comb
from typing import Dict, List, Optional, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from src.engine.combat import seed_combat
from src.engine.config import MULTI_RUN_SIMS, MULTI_RUN_VALIDATION_SEED
from src.engine.fitness import (
    FitnessDetail,
    _archetype_deviation,
    evaluate_detail_n,
    get_seed_base,
    set_seed_base,
)
from src.engine.individual import Individual
from src.engine.paths import BASELINES_PATH, PROJECT_ROOT
from src.engine.provenance import stamp
from src.tools.analyze_matchups import expected_winner
from src.tools.archetype_validator import run_validation

# A resolução do p-valor empírico é 1/N: com 5 espelhos + 30 aleatórios, nenhum nulo
# igualando o observado afirma p < 0,03. O default é o valor do protocolo, porque a
# bateria (`run_battery.ps1`) e o dossiê (`report`) o usam sem flag.
N_RANDOM_DEFAULT = 30
BEHAVIORAL_SIMS = 120


# ─────────────────────────────────────────────────────────────────────────────
# Rosters de referência
# ─────────────────────────────────────────────────────────────────────────────


def mirror_roster(archetype_id: ArchetypeID) -> Individual:
    """Cinco cópias do mesmo arquétipo. Equilíbrio perfeito por simetria (todo par
    é um espelho), identidade zero por construção — não existe "o de maior alcance"
    quando os cinco têm o mesmo alcance. É a solução TRIVIAL do problema de
    equilíbrio, e o piso contra o qual o roster evoluído tem de se justificar."""
    ind   = Individual.from_canonical()
    proto = ind.get(archetype_id)
    for char in ind.characters:
        char.attributes = list(proto.attributes)
        char.weights    = list(proto.weights)
    return ind


def reference_rosters(n_random: int, seed: int) -> List[Tuple[str, str, Individual]]:
    """(rótulo, papel, roster). O papel diz qual extremo cada um ancora."""
    rosters: List[Tuple[str, str, Individual]] = [
        ("canônico", "teto_identidade", Individual.from_canonical()),
    ]
    rosters += [
        (f"espelho {ARCHETYPES[aid].name}", "piso_identidade", mirror_roster(aid))
        for aid in ARCHETYPE_ORDER
    ]
    rng_state = random.getstate()
    random.seed(seed)
    rosters += [
        (f"aleatório {k + 1}", "chao_absoluto", Individual.random())
        for k in range(n_random)
    ]
    random.setstate(rng_state)
    return rosters


# ─────────────────────────────────────────────────────────────────────────────
# Métricas
# ─────────────────────────────────────────────────────────────────────────────


def cycle_edges_kept(detail: FitnessDetail) -> int:
    """Arestas do ciclo canônico realizadas. **Piso de acaso = 5/10**: cada aresta é
    cara-ou-coroa. E acertar o rótulo específico é 1 em 24 — o ciclo canônico é um
    torneio REGULAR (cada arquétipo vence 2 e perde 2) e existem 24 torneios regulares
    rotulados em 5 vértices. Por isso o número cru não distingue preservação de sorte."""
    kept = 0
    for (i, j), wr in detail.matchup_winrates.items():
        id_a, id_b = ARCHETYPE_ORDER[i], ARCHETYPE_ORDER[j]
        expected = expected_winner(id_a, id_b)
        observed = id_a if wr > 0.5 else id_b if wr < 0.5 else None
        kept += observed == expected
    return kept


def circular_triads(detail: FitnessDetail) -> float:
    """Tríades circulares do torneio de matchups (Kendall & Babington Smith 1940):
    `C(n,3) − Σ C(d_i, 2)`, com `d_i` = vitórias do personagem i.

    Mede estrutura **sem depender de autoria**: 0 = ordem estrita (bicho-papão),
    2.5 = torneio aleatório, 5 = máximo em 5 personagens — que é exatamente o torneio
    REGULAR, isto é, equilíbrio global perfeito. Equilíbrio global e pedra-papel-tesoura
    são a mesma coisa: um roster estritamente transitivo tem WRs 100/75/50/25/0, o que
    é incompatível com todo mundo perto de 50%.

    **Só significa algo com arestas decididas.** Num espelho os pares ficam em 44%–58%
    (ruído binomial puro) e a direção de cada aresta é sorteio, então a contagem vira
    lixo — por isso o relatório sempre traz o espalhamento das WR ao lado."""
    wins = [0.0] * len(ARCHETYPE_ORDER)
    for (i, j), wr in detail.matchup_winrates.items():
        if wr > 0.5:
            wins[i] += 1
        elif wr < 0.5:
            wins[j] += 1
        else:
            wins[i] += 0.5
            wins[j] += 0.5
    n = len(wins)
    # Empates dão meia-vitória; C(d,2) = d(d−1)/2 estende para d fracionário.
    return comb(n, 3) - sum(d * (d - 1) / 2 for d in wins)


def measure(individual: Individual, sims: int, seed: int) -> dict:
    """Mede um roster sob `seed`, devolvendo o seed-base do processo como estava.
    Restaurar importa porque o `report` compõe esta função com outros tools."""
    previous_base = get_seed_base()
    set_seed_base(seed)
    seed_combat(seed)
    try:
        detail     = evaluate_detail_n(individual, sims)
        structural = run_validation(individual, behavioral_n=0)
        full       = run_validation(individual, behavioral_n=BEHAVIORAL_SIMS, seed=seed)
    finally:
        set_seed_base(previous_base)

    pair_wrs = sorted(detail.matchup_winrates.values())
    return {
        "dominance_penalty": detail.dominance_penalty,
        "dominance_terms":   detail.dominance_terms.as_dict(),
        "drift_penalty":     detail.drift_penalty,
        "per_character_drift": [
            _archetype_deviation(individual.get(aid)) for aid in ARCHETYPE_ORDER
        ],
        "validator_structural": structural.passed,
        "validator_structural_total": structural.total,
        "validator_full":      full.passed,
        "validator_full_total": full.total,
        "cycle_edges_kept":    cycle_edges_kept(detail),
        "circular_triads":     circular_triads(detail),
        "pair_wr_min":         pair_wrs[0],
        "pair_wr_max":         pair_wrs[-1],
        "global_wr":           list(detail.winrates),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Piso, teto e posição
# ─────────────────────────────────────────────────────────────────────────────


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _null_stats(values: List[float], better: str) -> dict:
    """O piso não é um ponto, é uma **distribuição**. Medido, um roster aleatório
    chegou a 12/21 no validador — então comparar contra a média do nulo não basta:
    um resultado só é distinguível do acaso se supera o que o acaso alcança."""
    if not values:
        return {"media": 0.0, "desvio": 0.0, "extremo": 0.0, "n": 0}
    media  = _mean(values)
    desvio = (sum((v - media) ** 2 for v in values) / len(values)) ** 0.5
    return {
        "media":   media,
        "desvio":  desvio,
        "extremo": max(values) if better == "maior" else min(values),
        "n":       len(values),
    }


def empirical_p(value: float, nulls: List[float], better: str) -> Optional[float]:
    """Fração dos rosters nulos que igualam ou superam o valor observado — um
    p-valor empírico no espírito de teste de permutação. `p = 0` com N nulos
    significa apenas `p < 1/N`: com poucos nulos não há resolução para afirmar mais."""
    if not nulls:
        return None
    if better == "maior":
        at_least = sum(1 for v in nulls if v >= value)
    else:
        at_least = sum(1 for v in nulls if v <= value)
    return at_least / len(nulls)


def floors_and_ceilings(measured: List[Tuple[str, str, dict]]) -> dict:
    """Piso = média dos rosters SEM estrutura; teto = o canônico (ou o ótimo teórico).

    Para identidade o piso vem dos espelhos: eles são o pior caso *construído*
    (identidade zero com equilíbrio perfeito), enquanto os aleatórios são o pior caso
    *não construído*. Os dois são reportados — dizem coisas diferentes."""
    by_role: Dict[str, List[dict]] = {}
    for _, role, m in measured:
        by_role.setdefault(role, []).append(m)

    mirrors = by_role.get("piso_identidade", [])
    randoms = by_role.get("chao_absoluto", [])
    canon   = by_role["teto_identidade"][0]

    n_pairs = len(list(combinations(ARCHETYPE_ORDER, 2)))
    spec = [
        ("validator_full",       "validator_full",       "maior", canon["validator_full_total"]),
        ("validator_structural", "validator_structural", "maior", canon["validator_structural_total"]),
        ("drift_penalty",        "drift_penalty",        "menor", 0.0),
        ("cycle_edges_kept",     "cycle_edges_kept",     "maior", n_pairs),
        ("dominance_penalty",    "dominance_penalty",    "menor", _mean([m["dominance_penalty"] for m in mirrors])),
    ]

    refs = {}
    for key, field, better, teto in spec:
        nulls = [m[field] for m in mirrors + randoms]
        refs[key] = {
            "melhor":         better,
            "teto":           teto,
            "nulos":          nulls,
            "espelho":        _null_stats([m[field] for m in mirrors], better),
            "aleatorio":      _null_stats([m[field] for m in randoms], better),
            "piso":           _mean(nulls),
            "piso_extremo":   max(nulls) if better == "maior" else min(nulls),
        }
    # O ciclo tem piso ANALÍTICO, não empírico: cada aresta é cara-ou-coroa, então o
    # acaso entrega n_pairs/2 — e acertar o rótulo específico é 1 em 24 (o ciclo
    # canônico é um dos 24 torneios regulares rotulados em 5 vértices).
    refs["cycle_edges_kept"]["piso"] = n_pairs / 2
    return refs


def position(value: float, floor: float, ceiling: float) -> Optional[float]:
    """Fração do caminho do piso até o teto. `None` quando piso e teto coincidem."""
    span = ceiling - floor
    if abs(span) < 1e-12:
        return None
    return (value - floor) / span


# ─────────────────────────────────────────────────────────────────────────────
# Relatório
# ─────────────────────────────────────────────────────────────────────────────

_LINE = "═" * 78


def print_reference_table(measured: List[Tuple[str, str, dict]]) -> None:
    print(_LINE)
    print("  ROSTERS DE REFERÊNCIA")
    print(_LINE)
    print(f"  {'roster':<24}{'dominance':>10}{'drift':>8}{'L1+L2':>8}{'L1-L3':>8}"
          f"{'ciclo':>7}{'tríades':>9}{'WR par':>13}")
    print("  " + "─" * 74)
    current_role = None
    for label, role, m in measured:
        if role != current_role:
            current_role = role
            print(f"  {_ROLE_LABEL[role]}")
        print(f"    {label:<22}{m['dominance_penalty']:>10.4f}{m['drift_penalty']:>8.4f}"
              f"{m['validator_structural']:>5}/{m['validator_structural_total']:<2}"
              f"{m['validator_full']:>5}/{m['validator_full_total']:<2}"
              f"{m['cycle_edges_kept']:>4}/10{m['circular_triads']:>9.1f}"
              f"{m['pair_wr_min']:>8.0%}–{m['pair_wr_max']:.0%}")


_ROLE_LABEL = {
    "teto_identidade": "  ── teto de identidade (intacta, equilíbrio terrível) ──",
    "piso_identidade": "  ── piso de identidade: espelhos, 5 idênticos "
                       "(equilíbrio perfeito, identidade zero) ──",
    "chao_absoluto":   "  ── chão absoluto: sem projeto nenhum ──",
}

_METRIC_LABEL = {
    "validator_full":       "validador (L1-L3)",
    "validator_structural": "validador (L1+L2)",
    "drift_penalty":        "drift_penalty",
    "cycle_edges_kept":     "arestas do ciclo",
    "dominance_penalty":    "dominance_penalty",
}


def print_position_table(label: str, measured: dict, refs: dict) -> None:
    print()
    print(_LINE)
    print(f"  POSIÇÃO ENTRE PISO E TETO — {label}")
    print(_LINE)
    print(f"  {'métrica':<22}{'valor':>9}{'piso méd':>10}{'pior nulo':>11}"
          f"{'teto':>9}{'posição':>9}{'p':>7}")
    print("  " + "─" * 74)
    for key, ref in refs.items():
        value = measured[key]
        pos   = position(value, ref["piso"], ref["teto"])
        p     = empirical_p(value, ref["nulos"], ref["melhor"])
        pos_s = "—" if pos is None else f"{pos:.0%}"
        p_s   = "—" if p is None else (f"<{1 / len(ref['nulos']):.2f}" if p == 0 else f"{p:.2f}")
        print(f"  {_METRIC_LABEL[key]:<22}{value:>9.3f}{ref['piso']:>10.3f}"
              f"{ref['piso_extremo']:>11.3f}{ref['teto']:>9.3f}{pos_s:>9}{p_s:>7}")
    print("  " + "─" * 74)
    print("  posição = (valor − piso méd) / (teto − piso méd): 0% = na média dos rosters")
    print("           sem estrutura;  100% = no extremo de referência daquele eixo.")
    print("  pior nulo = o melhor resultado que um roster SEM estrutura alcançou aqui.")
    print("           Não superá-lo significa não ser distinguível do acaso.")
    print("  p = fração dos rosters nulos que igualam ou superam o valor (p-valor")
    print("           empírico). Com poucos nulos, `p = 0` só afirma `p < 1/N`.")
    print()
    print(f"  Espalhamento das WR por par: "
          f"{measured['pair_wr_min']:.0%}–{measured['pair_wr_max']:.0%}   "
          f"tríades circulares: {measured['circular_triads']:.1f}")
    print("  (tríades: 0 = ordem estrita · 2.5 = acaso · 5 = máximo = equilíbrio global")
    print("   perfeito. Só significam algo com arestas DECIDIDAS — se as WR por par")
    print("   estão coladas em 50%, a direção de cada aresta é sorteio.)")
    print(_LINE)


# ─────────────────────────────────────────────────────────────────────────────
# Entrada
# ─────────────────────────────────────────────────────────────────────────────


def _load_individual(args: argparse.Namespace) -> Optional[Tuple[Individual, str]]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (results.json)"
    return None


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Modelos nulos: piso, teto e posição de cada métrica post-hoc"
    )
    parser.add_argument("--evolved", action="store_true",
                        help="Posiciona o melhor indivíduo do AG (results.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="scalar_optimum",
                        help="Posiciona um representante do NSGA-II (knee_point|"
                             "best_dominance|best_drift|ideal_point|scalar_optimum)")
    parser.add_argument("--n-random", type=int, default=N_RANDOM_DEFAULT,
                        help=f"Rosters aleatórios no chão absoluto (default: {N_RANDOM_DEFAULT})")
    parser.add_argument("--sims", type=int, default=MULTI_RUN_SIMS,
                        help=f"Simulações por matchup (default: {MULTI_RUN_SIMS})")
    parser.add_argument("--seed", type=int, default=MULTI_RUN_VALIDATION_SEED,
                        help=f"Semente de avaliação (default: {MULTI_RUN_VALIDATION_SEED})")
    return parser


def main() -> None:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    args = _build_argparser().parse_args()

    print(f"\nMedindo rosters de referência ({args.sims} sims/matchup, "
          f"seed {args.seed})...\n")
    measured = [
        (label, role, measure(ind, args.sims, args.seed))
        for label, role, ind in reference_rosters(args.n_random, args.seed)
    ]
    print_reference_table(measured)

    refs = floors_and_ceilings(measured)
    artifact = {
        "sims_per_matchup": args.sims,
        "seed": args.seed,
        "n_random": args.n_random,
        "references": [
            {"label": label, "role": role, **m} for label, role, m in measured
        ],
        "floors_and_ceilings": refs,
    }

    target = _load_individual(args)
    if target is not None:
        individual, label = target
        target_measured = measure(individual, args.sims, args.seed)
        print_position_table(label, target_measured, refs)
        artifact["target"] = {"label": label, **target_measured}

    BASELINES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINES_PATH, "w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(), **artifact}, fh, indent=2, ensure_ascii=False)
    print(f"\n  Salvo em {BASELINES_PATH.relative_to(PROJECT_ROOT)}\n")


if __name__ == "__main__":
    main()
