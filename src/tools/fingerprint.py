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
from typing import Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.combat import seed_combat
from src.engine.individual import Individual
from src.tools.analyze_matchups import behavioral_profile

FINGERPRINT_SIMS = 200

# Métricas do fingerprint: (chave, rótulo, tipo). "pct" = fração em [0,1];
# "count" = contagem por luta / distância média (formatada como valor absoluto).
# DEF vem dividido em guarda (escolhido) e parede (forçado por encurralamento).
_METRICS: Tuple[Tuple[str, str, str], ...] = (
    ("atk_landed",     "ATK conectado/luta", "count"),
    ("adv",            "ADV",                "pct"),
    ("ret",            "RET",                "pct"),
    ("def_chosen",     "DEF (guarda)",       "pct"),
    ("def_forced",     "DEF (parede)",       "pct"),
    ("oor",            "% fora range",       "pct"),
    ("stunned",        "% stunado",          "pct"),
    ("mean_dist",      "dist. média",        "count"),
    ("stun_inflicted", "stun aplic./luta",   "count"),
)


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO"
    return Individual.from_canonical(), "CANÔNICO"


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
    fp = behavioral_profile(ind, n)
    base = fp
    if not is_canon:
        seed_combat(seed); random.seed(seed)
        base = behavioral_profile(Individual.from_canonical(), n)

    print("\n" + "═" * 60)
    title = f"{label} vs CANÔNICO" if not is_canon else "CANÔNICO (baseline)"
    print(f"  FINGERPRINT COMPORTAMENTAL — {title}  (n={n})")
    print("═" * 60)

    for aid in ARCHETYPE_ORDER:
        print(f"\n  {ARCHETYPES[aid].name}")
        print(f"    {'métrica':20}{'canônico':>10}{'evoluído':>10}{'Δ':>9}")
        print(f"    {'─' * 49}")
        for key, lbl, kind in _METRICS:
            c = base[aid][key]
            e = fp[aid][key]
            if kind == "pct":
                print(f"    {lbl:20}{c:>9.0%}{'':1}{e:>9.0%}{'':1}{(e - c) * 100:>+7.0f}pp")
            else:
                print(f"    {lbl:20}{c:>10.1f}{e:>10.1f}{e - c:>+9.1f}")


if __name__ == "__main__":
    main()
