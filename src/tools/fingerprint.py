"""
Fingerprint comportamental — retrato de COMO cada personagem joga, agregado sobre
os 4 matchups dele. Mede identidade *comportamental* (o Zoner evoluído ainda kita?),
complementando o `archetype_validator` (identidade estrutural/ranking) e a
`drift_table` (identidade de genes/distância).

Mostra, por personagem, o canônico vs o evoluído + Δ (em pontos percentuais) das
métricas: mix de ações (ATK/ADV/RET/DEF), % do tempo fora de range (espaçamento) e
% stunado. Rodado no canônico, os Δ ficam ~0 (sanity).

Uso:
    py -m src.tools.fingerprint              # canônico (baseline)
    py -m src.tools.fingerprint --evolved    # evoluído vs canônico
    py -m src.tools.fingerprint --nsga2 [REP]
"""

from __future__ import annotations

import argparse
import random
from typing import Dict, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from src.engine.combat import Action, seed_combat
from src.engine.individual import Individual
from src.tools.analyze_matchups import analyze_combat_multi

FINGERPRINT_SIMS = 200

# Métricas do fingerprint: (chave, rótulo). Frações em [0, 1].
_METRICS: Tuple[Tuple[str, str], ...] = (
    ("atk", "ATK"),
    ("adv", "ADV"),
    ("ret", "RET"),
    ("def", "DEF"),
    ("oor", "% fora range"),
    ("stun", "% stunado"),
)


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO"
    return Individual.from_canonical(), "CANÔNICO"


def _fingerprint(ind: Individual, n: int) -> Dict[ArchetypeID, Dict[str, float]]:
    """Métricas comportamentais médias por personagem (sobre seus 4 matchups)."""
    chars = {c.archetype.id: c for c in ind.characters}
    ids = ARCHETYPE_ORDER
    agg = {aid: {k: 0.0 for k, _ in _METRICS} | {"_n": 0} for aid in ids}

    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            r = analyze_combat_multi(chars[ids[a]], chars[ids[b]], n=n)
            total = max(r.avg_ticks, 1.0)
            for idx, aid in ((0, ids[a]), (1, ids[b])):
                s = r.stats[idx]
                act = sum(s.action_counts.values()) or 1.0
                m = agg[aid]
                m["atk"] += s.action_counts[int(Action.ATTACK)] / act
                m["adv"] += s.action_counts[int(Action.ADVANCE)] / act
                m["ret"] += s.action_counts[int(Action.RETREAT)] / act
                m["def"] += s.action_counts[int(Action.DEFEND)] / act
                m["oor"] += s.ticks_out_of_range / total
                m["stun"] += s.ticks_stunned / total
                m["_n"] += 1

    for aid in ids:
        n_m = agg[aid].pop("_n") or 1
        for k, _ in _METRICS:
            agg[aid][k] /= n_m
    return agg


def main() -> None:
    parser = argparse.ArgumentParser(description="Fingerprint comportamental por personagem")
    parser.add_argument("--evolved", action="store_true",
                        help="Melhor indivíduo do AG (results.json) vs canônico")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="Representante do NSGA-II vs canônico")
    parser.add_argument("--n", type=int, default=FINGERPRINT_SIMS, help="Sims por matchup")
    parser.add_argument("--seed", type=int, default=42,
                        help="Semente (mesma p/ canônico e evoluído — comparação justa)")
    args = parser.parse_args()
    ind, label = _load_individual(args)
    is_canon = not (args.evolved or args.nsga2)
    print_fingerprint_report(ind, label, is_canon, args.n, args.seed)


def print_fingerprint_report(
    ind: Individual, label: str, is_canon: bool, n: int = FINGERPRINT_SIMS, seed: int = 42
) -> None:
    seed_combat(seed); random.seed(seed)
    fp = _fingerprint(ind, n)
    base = fp
    if not is_canon:
        seed_combat(seed); random.seed(seed)
        base = _fingerprint(Individual.from_canonical(), n)

    print("\n" + "═" * 60)
    title = f"{label} vs CANÔNICO" if not is_canon else "CANÔNICO (baseline)"
    print(f"  FINGERPRINT COMPORTAMENTAL — {title}  (n={n})")
    print("═" * 60)

    for aid in ARCHETYPE_ORDER:
        print(f"\n  {ARCHETYPES[aid].name}")
        print(f"    {'métrica':14}{'canônico':>10}{'evoluído':>10}{'Δ':>8}")
        print(f"    {'─' * 42}")
        for k, lbl in _METRICS:
            c = base[aid][k]
            e = fp[aid][k]
            print(f"    {lbl:14}{c:>9.0%}{'':1}{e:>9.0%}{'':1}{(e - c) * 100:>+7.0f}pp")


if __name__ == "__main__":
    main()
