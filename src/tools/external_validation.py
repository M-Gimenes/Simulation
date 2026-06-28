"""external_validation.py — Item 3.2 da metodologia: validação externa ao fitness.

Estilo Ludi (Browne & Maire 2010): não confiar num único número de fitness — validar
o artefato evoluído *fora* do laço de otimização, contra uma bateria de indicadores
sob condições que o AG nunca otimizou.

Aqui: fixa UM indivíduo (canônico, melhor do AG, ou representante do NSGA-II) e o
reavalia sob K sementes de avaliação **totalmente novas** (fora do range de treino e
da seed de validação do multi_run), cada uma com mais sims. Se o equilíbrio é robusto,
ele sobrevive ao ruído fora do laço; se é overfit às condições exatas do treino, os
matchups balanceados se desfazem entre as sementes.

A bateria de identidade post-hoc (ciclo, drift_table, fingerprint, archetype_validator)
é determinística nos genes e já coberta pelo `report`; esta validação foca no eixo
**estocástico** (equilíbrio), que é onde o overfitting ao fitness se esconde.

Uso:
    py -m src.tools.external_validation              # canônico
    py -m src.tools.external_validation --evolved    # melhor do AG
    py -m src.tools.external_validation --nsga2 best_dominance
    py -m src.tools.external_validation --n-seeds 30 --sims 1000
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from typing import Dict, List

from src.engine.config import (
    EXTERNAL_VALIDATION_N_SEEDS,
    EXTERNAL_VALIDATION_SEED_START,
    EXTERNAL_VALIDATION_SIMS,
)
from src.engine.fitness import (
    FitnessDetail,
    character_balanced,
    evaluate_detail_n,
    is_hard_counter,
    set_seed_base,
)
from src.engine.individual import Individual
from src.engine.paths import EXTERNAL_VALIDATION_DIR, PROJECT_ROOT
from src.tools.multi_run import CHAR_NAMES, matchup_label, mean_std


def _load_individual(args: argparse.Namespace):
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"nsga2_{args.nsga2}"
    if args.evolved:
        return Individual.from_results(), "evolved"
    return Individual.from_canonical(), "canonical"


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação por condição (semente) e agregação
# ─────────────────────────────────────────────────────────────────────────────


def _condition_record(detail: FitnessDetail, seed: int) -> dict:
    characters: Dict[str, dict] = {}
    for i, name in enumerate(CHAR_NAMES):
        wr = detail.winrates[i]
        characters[name] = {"wr": wr, "balanced": character_balanced(wr)}
    matchups: Dict[str, dict] = {}
    for (i, j), wr in detail.matchup_winrates.items():
        matchups[matchup_label(i, j)] = {"wr": wr, "hard_counter": is_hard_counter(wr)}
    return {
        "seed": seed,
        "dominance_penalty": detail.dominance_penalty,
        "drift_penalty": detail.drift_penalty,
        "characters": characters,
        "matchups": matchups,
    }


def _aggregate(records: List[dict]) -> dict:
    labels = [matchup_label(i, j) for i, j in combinations(range(len(CHAR_NAMES)), 2)]

    char_stats = {}
    n_chars_robust = 0
    for name in CHAR_NAMES:
        wrs = [r["characters"][name]["wr"] for r in records]
        robust = all(r["characters"][name]["balanced"] for r in records)
        n_chars_robust += robust
        stats = mean_std(wrs)
        stats["robust"] = robust  # WR global em banda em TODAS as condições
        char_stats[name] = stats

    matchup_stats = {}
    n_hard_counter_matchups = 0
    for label in labels:
        wrs = [r["matchups"][label]["wr"] for r in records]
        ever_hard_counter = any(r["matchups"][label]["hard_counter"] for r in records)
        n_hard_counter_matchups += ever_hard_counter
        stats = mean_std(wrs)
        stats["hard_counter"] = ever_hard_counter  # counter duro em ALGUMA condição
        matchup_stats[label] = stats

    return {
        "dominance_penalty": mean_std([r["dominance_penalty"] for r in records]),
        "drift_penalty": mean_std([r["drift_penalty"] for r in records]),
        "characters": char_stats,
        "matchups": matchup_stats,
        "n_chars_robust": n_chars_robust,
        "n_chars": len(CHAR_NAMES),
        "n_hard_counter_matchups": n_hard_counter_matchups,
        "n_matchups": len(labels),
        # Roster robusto: todos os bonecos em banda em todas as condições E
        # nenhum par vira counter duro em condição alguma.
        "roster_robust": n_chars_robust == len(CHAR_NAMES) and n_hard_counter_matchups == 0,
    }


def validate(individual, seeds: List[int], sims: int) -> dict:
    records: List[dict] = []
    print(f"\n{'═' * 70}")
    print(f"  Validação externa — {len(seeds)} condições independentes "
          f"(seeds {seeds[0]}..{seeds[-1]}), {sims} sims/matchup")
    print(f"{'═' * 70}")

    for idx, seed in enumerate(seeds, start=1):
        print(f"  [{idx:>2}/{len(seeds)}] seed={seed} ... ", end="", flush=True)
        set_seed_base(seed)
        detail = evaluate_detail_n(individual, sims)
        record = _condition_record(detail, seed)
        records.append(record)
        n_bal = sum(c["balanced"] for c in record["characters"].values())
        n_hc = sum(m["hard_counter"] for m in record["matchups"].values())
        print(f"dom={record['dominance_penalty']:.4f}  "
              f"bonecos eq={n_bal}/{len(record['characters'])}  counters={n_hc}")

    return {
        "seeds": seeds,
        "sims_per_matchup": sims,
        "per_condition": records,
        "aggregate": _aggregate(records),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Relatório
# ─────────────────────────────────────────────────────────────────────────────


def _print_summary(result: dict, label: str) -> None:
    agg = result["aggregate"]
    n = len(result["seeds"])
    print(f"\n  ── Robustez do equilíbrio ({label}, {n} condições) ──")

    dom = agg["dominance_penalty"]
    drift = agg["drift_penalty"]
    print(f"    dominance_penalty:  {dom['mean']:.4f} ± {dom['std']:.4f}")
    print(f"    drift_penalty:      {drift['mean']:.4f} ± {drift['std']:.4f}")

    print(f"\n    WR global por personagem (alvo 50%; ✓ = em [40%, 60%] em TODAS as condições):")
    for name in CHAR_NAMES:
        stats = agg["characters"][name]
        mark = "✓" if stats["robust"] else "✗"
        print(f"      {mark} {name:<15s} {stats['mean']:.1%} ± {stats['std']:.1%}")

    print(f"\n    Matchups (WR média ± desvio através das condições; "
          f"⚠ = counter duro em ALGUMA condição):")
    for label_m, stats in agg["matchups"].items():
        mark = "⚠" if stats["hard_counter"] else " "
        print(f"      {mark} {label_m:<28s} {stats['mean']:.1%} ± {stats['std']:.1%}")

    print(f"\n    Bonecos robustos (WR global em banda em todas as {n} condições): "
          f"{agg['n_chars_robust']}/{agg['n_chars']}")
    print(f"    Matchups que viram counter duro em alguma condição: "
          f"{agg['n_hard_counter_matchups']}/{agg['n_matchups']}")
    verdict = "ROBUSTO" if agg["roster_robust"] else "FRÁGIL (sensível à condição de avaliação)"
    print(f"    Veredito do roster: {verdict}")


def _save(result: dict, label: str) -> None:
    EXTERNAL_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    path = EXTERNAL_VALIDATION_DIR / f"external_validation_{label}.json"
    with open(path, "w") as fh:
        json.dump({"individual": label, **result}, fh, indent=2)
    print(f"\n  Salvo em {path.relative_to(PROJECT_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validação externa ao fitness — robustez do equilíbrio (metodologia 3.2)"
    )
    parser.add_argument("--evolved", action="store_true", help="melhor do AG (results.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="best_dominance",
                        help="representante do NSGA-II (best_dominance|knee_point|best_drift|ideal_point)")
    parser.add_argument("--n-seeds", type=int, default=EXTERNAL_VALIDATION_N_SEEDS,
                        help=f"nº de condições de avaliação (default: {EXTERNAL_VALIDATION_N_SEEDS})")
    parser.add_argument("--seed-start", type=int, default=EXTERNAL_VALIDATION_SEED_START,
                        help=f"primeira semente (default: {EXTERNAL_VALIDATION_SEED_START})")
    parser.add_argument("--sims", type=int, default=EXTERNAL_VALIDATION_SIMS,
                        help=f"sims/matchup por condição (default: {EXTERNAL_VALIDATION_SIMS})")
    return parser.parse_args()


def main():
    args = parse_args()
    individual, label = _load_individual(args)
    seeds = list(range(args.seed_start, args.seed_start + args.n_seeds))

    result = validate(individual, seeds, args.sims)
    _print_summary(result, label)
    _save(result, label)


if __name__ == "__main__":
    main()
