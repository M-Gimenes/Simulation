"""multi_run.py — Item 1.1 da metodologia: N execuções independentes + estatística agregada.

Um EA é estocástico, então uma seed é uma *amostra*, não um resultado (Eiben & Smith
2015; Deb 2001). Este tool roda o algoritmo escolhido sobre N sementes consecutivas,
reavalia o melhor indivíduo de cada execução sob um stream de RNG independente do
treino (Common Random Numbers entre execuções) e agrega (headline C2):

  • média ± desvio de `dominance_penalty` / `drift_penalty`;
  • WR global média ± desvio por personagem + fração de sementes em que cada boneco
    fica equilibrado (WR global em [0.40, 0.60]);
  • número de hard-counters (pares fora de [0.30, 0.70]) por execução;
  • fração de sementes que equilibram o ROSTER (5 bonecos em banda E 0 hard-counters).
  • (secundário) WR média por matchup.

Uso:
    py -m src.tools.multi_run                       # ambos os algoritmos, defaults do config
    py -m src.tools.multi_run --algorithm nsga2     # só NSGA-II
    py -m src.tools.multi_run --n-seeds 30          # escala o experimento
"""

from __future__ import annotations

import argparse
import json
import statistics
from itertools import combinations
from typing import Dict, List, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import (
    HYPERVOLUME_REFERENCE,
    MULTI_RUN_N_SEEDS,
    MULTI_RUN_SEED_START,
    MULTI_RUN_SIMS,
    MULTI_RUN_VALIDATION_SEED,
)
from src.engine.fitness import (
    FitnessDetail,
    character_balanced,
    evaluate_detail_n,
    is_hard_counter,
    set_seed_base,
)
from src.engine.ga import run as run_ga
from src.engine.nsga2 import run as run_nsga2
from src.engine.pareto_metrics import hypervolume_2d, spacing
from src.engine.paths import (
    MULTI_RUN_DIR,
    MULTI_RUN_GA_PATH,
    MULTI_RUN_NSGA2_PATH,
    PROJECT_ROOT,
)

CHAR_NAMES: List[str] = [ARCHETYPES[aid].name for aid in ARCHETYPE_ORDER]


def matchup_label(i: int, j: int) -> str:
    return f"{CHAR_NAMES[i]} vs {CHAR_NAMES[j]}"


def mean_std(values: List[float]) -> Dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Execução de uma semente
# ─────────────────────────────────────────────────────────────────────────────


def _run_algorithm(algorithm: str, seed: int):
    """Roda o algoritmo (silencioso) e devolve `(representante, objetivos_da_fronteira)`.
    AG escalar → o melhor indivíduo, sem fronteira (`None`). NSGA-II → o `best_dominance`
    e os objetivos `(dominance, drift)` de toda a fronteira (para hipervolume/spacing)."""
    if algorithm == "ga":
        return run_ga(seed=seed, verbose=False).best, None
    result = run_nsga2(seed=seed, verbose=False)
    front_objectives = [ind.objectives for ind in result.pareto_front]
    return result.representatives["best_dominance"], front_objectives


def _evaluate_independent(individual, sims: int) -> FitnessDetail:
    """Reavalia o indivíduo sob a semente de validação — desacopla a métrica
    reportada da semente em que ele foi treinado e iguala o stream entre execuções."""
    set_seed_base(MULTI_RUN_VALIDATION_SEED)
    return evaluate_detail_n(individual, sims)


def _seed_record(detail: FitnessDetail, seed: int, front_objectives) -> dict:
    characters: Dict[str, dict] = {}
    n_chars_balanced = 0
    for i, name in enumerate(CHAR_NAMES):
        wr = detail.winrates[i]
        balanced = character_balanced(wr)
        n_chars_balanced += balanced
        characters[name] = {"wr": wr, "balanced": balanced}

    matchups: Dict[str, dict] = {}
    n_hard_counters = 0
    for (i, j), wr in detail.matchup_winrates.items():
        hard_counter = is_hard_counter(wr)
        n_hard_counters += hard_counter
        matchups[matchup_label(i, j)] = {"wr": wr, "hard_counter": hard_counter}

    record = {
        "seed": seed,
        "dominance_penalty": detail.dominance_penalty,
        "drift_penalty": detail.drift_penalty,
        "characters": characters,
        "matchups": matchups,
        "n_chars_balanced": n_chars_balanced,
        "n_hard_counters": n_hard_counters,
        "roster_balanced": n_chars_balanced == len(CHAR_NAMES) and n_hard_counters == 0,
    }
    if front_objectives is not None:
        record["front_size"] = len(front_objectives)
        record["hypervolume"] = hypervolume_2d(front_objectives, HYPERVOLUME_REFERENCE)
        record["spacing"] = spacing(front_objectives)
    return record


# ─────────────────────────────────────────────────────────────────────────────
# Agregação
# ─────────────────────────────────────────────────────────────────────────────


def _aggregate(records: List[dict]) -> dict:
    n = len(records)
    matchup_labels = [matchup_label(i, j) for i, j in combinations(range(len(CHAR_NAMES)), 2)]

    agg = {
        "dominance_penalty": mean_std([r["dominance_penalty"] for r in records]),
        "drift_penalty": mean_std([r["drift_penalty"] for r in records]),
        "characters": {
            name: {
                **mean_std([r["characters"][name]["wr"] for r in records]),
                "balanced_rate": sum(r["characters"][name]["balanced"] for r in records) / n,
            }
            for name in CHAR_NAMES
        },
        "matchup_wr": {
            label: mean_std([r["matchups"][label]["wr"] for r in records])
            for label in matchup_labels
        },
        "hard_counter_rate": {
            label: sum(r["matchups"][label]["hard_counter"] for r in records) / n
            for label in matchup_labels
        },
        "hard_counters_per_seed": mean_std([r["n_hard_counters"] for r in records]),
        "roster_balanced_rate": sum(r["roster_balanced"] for r in records) / n,
    }
    if all("hypervolume" in r for r in records):
        agg["hypervolume"] = mean_std([r["hypervolume"] for r in records])
        agg["spacing"] = mean_std([r["spacing"] for r in records])
    return agg


def aggregate_algorithm(algorithm: str, seeds: List[int], sims: int) -> dict:
    records: List[dict] = []
    print(f"\n{'═' * 70}")
    print(f"  {algorithm.upper()} — {len(seeds)} execuções (seeds {seeds[0]}..{seeds[-1]}), "
          f"validação com {sims} sims/matchup")
    print(f"{'═' * 70}")

    for idx, seed in enumerate(seeds, start=1):
        print(f"  [{idx:>2}/{len(seeds)}] seed={seed} ... ", end="", flush=True)
        individual, front_objectives = _run_algorithm(algorithm, seed)
        detail = _evaluate_independent(individual, sims)
        record = _seed_record(detail, seed, front_objectives)
        records.append(record)
        hv_part = f"  hv={record['hypervolume']:.4f}" if "hypervolume" in record else ""
        print(f"dom={record['dominance_penalty']:.4f}  drift={record['drift_penalty']:.4f}  "
              f"bonecos eq={record['n_chars_balanced']}/{len(CHAR_NAMES)}  "
              f"counters={record['n_hard_counters']}{hv_part}")

    return {
        "algorithm": algorithm,
        "n_seeds": len(seeds),
        "seeds": seeds,
        "validation_seed": MULTI_RUN_VALIDATION_SEED,
        "sims_per_matchup": sims,
        "per_seed": records,
        "aggregate": _aggregate(records),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Relatório
# ─────────────────────────────────────────────────────────────────────────────


def _print_summary(result: dict) -> None:
    agg = result["aggregate"]
    n = result["n_seeds"]
    print(f"\n  ── Resumo agregado ({n} execuções) ──")

    dom = agg["dominance_penalty"]
    drift = agg["drift_penalty"]
    print(f"    dominance_penalty:  {dom['mean']:.4f} ± {dom['std']:.4f}")
    print(f"    drift_penalty:      {drift['mean']:.4f} ± {drift['std']:.4f}")

    if "hypervolume" in agg:
        hv = agg["hypervolume"]
        sp = agg["spacing"]
        print(f"    hipervolume:        {hv['mean']:.4f} ± {hv['std']:.4f}  (ref={HYPERVOLUME_REFERENCE}, maior=melhor)")
        print(f"    spacing:            {sp['mean']:.4f} ± {sp['std']:.4f}  (menor=mais uniforme)")

    print(f"\n    WR global por personagem (alvo 50%; eq = WR global em [40%, 60%]):")
    for name in CHAR_NAMES:
        c = agg["characters"][name]
        print(f"      {name:<15s} {c['mean']:.1%} ± {c['std']:.1%}   eq em {c['balanced_rate']:.0%} das sementes")

    hc = agg["hard_counters_per_seed"]
    print(f"\n    Hard-counters por execução (pares fora de [30%, 70%]): "
          f"{hc['mean']:.1f} ± {hc['std']:.1f}")

    rate = agg["roster_balanced_rate"]
    print(f"\n    Sementes que equilibram o ROSTER (5 bonecos em banda E 0 hard-counters): "
          f"{rate:.0%}  ({int(round(rate * n))}/{n})")

    print(f"\n    (secundário) Hard-counter rate por matchup (fração de sementes em que o par vira counter duro):")
    for label, rate_hc in agg["hard_counter_rate"].items():
        wr = agg["matchup_wr"][label]
        flag = "  ⚠" if rate_hc > 0 else ""
        print(f"      {label:<28s} WR {wr['mean']:.0%}±{wr['std']:.0%}   counter em {rate_hc:.0%}{flag}")


def _save(result: dict, algorithm: str) -> None:
    MULTI_RUN_DIR.mkdir(parents=True, exist_ok=True)
    path = MULTI_RUN_GA_PATH if algorithm == "ga" else MULTI_RUN_NSGA2_PATH
    with open(path, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\n  Salvo em {path.relative_to(PROJECT_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="N execuções independentes + estatística agregada (metodologia 1.1)"
    )
    parser.add_argument("--algorithm", choices=["ga", "nsga2", "both"], default="both",
                        help="Algoritmo(s) a agregar (default: both)")
    parser.add_argument("--n-seeds", type=int, default=MULTI_RUN_N_SEEDS,
                        help=f"Número de execuções (default: {MULTI_RUN_N_SEEDS})")
    parser.add_argument("--seed-start", type=int, default=MULTI_RUN_SEED_START,
                        help=f"Primeira semente (default: {MULTI_RUN_SEED_START})")
    parser.add_argument("--sims", type=int, default=MULTI_RUN_SIMS,
                        help=f"Sims/matchup na reavaliação independente (default: {MULTI_RUN_SIMS})")
    return parser.parse_args()


def main():
    args = parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.n_seeds))
    algorithms = ["ga", "nsga2"] if args.algorithm == "both" else [args.algorithm]

    for algorithm in algorithms:
        result = aggregate_algorithm(algorithm, seeds, args.sims)
        _print_summary(result)
        _save(result, algorithm)


if __name__ == "__main__":
    main()
