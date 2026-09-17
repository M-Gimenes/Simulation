"""multi_run.py — Item 1.1 da metodologia: N execuções independentes + estatística agregada.

Um EA é estocástico, então uma seed é uma *amostra*, não um resultado (Eiben & Smith
2015; Deb 2001). Este tool roda o algoritmo escolhido sobre N sementes consecutivas,
reavalia o melhor indivíduo de cada execução sob um stream de RNG independente do
treino (Common Random Numbers entre execuções) e agrega (headline C2):

  • média ± desvio de `dominance_penalty` — **decomposto nos três termos**, porque o
    composto sozinho esconde de onde vem a diferença entre algoritmos — e de
    `drift_penalty`;
  • WR global média ± desvio por personagem + fração de sementes em que cada boneco
    fica equilibrado (WR global em [0.40, 0.60]);
  • número de hard-counters (pares fora de [0.35, 0.65]) por execução;
  • fração de sementes que equilibram o ROSTER (5 bonecos em banda E 0 hard-counters).
  • (secundário) WR média por matchup.

Cada execução do NSGA-II devolve uma fronteira, não um ponto: o ponto que representa
a execução (`--nsga2-representative`, default `best_dominance`) fica registrado no
artefato. Comparação estatística entre os dois algoritmos: `compare_algorithms`.

Uso:
    py -m src.tools.multi_run                       # ambos os algoritmos, defaults do config
    py -m src.tools.multi_run --algorithm nsga2     # só NSGA-II
    py -m src.tools.multi_run --n-seeds 30          # escala o experimento
    py -m src.tools.multi_run --nsga2-representative knee_point
"""

from __future__ import annotations

import argparse
import json
import statistics
from itertools import combinations
from pathlib import Path
from typing import Dict, List

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
    HYPERVOLUME_REFERENCE,
    LAMBDA_DOMINANCE,
    LAMBDA_DRIFT,
    MULTI_RUN_N_SEEDS,
    MULTI_RUN_SEED_START,
    MULTI_RUN_SIMS,
    MULTI_RUN_VALIDATION_SEED,
)
from src.engine.fitness import (
    FitnessDetail,
    character_balanced,
    evaluate_detail_n,
    get_lambdas,
    is_hard_counter,
    roster_balanced,
    set_lambdas_override,
    set_seed_base,
)
from src.engine.ga import run as run_ga
from src.engine.nsga2 import run as run_nsga2
from src.engine.pareto_metrics import hypervolume_2d, spacing
from src.engine.paths import (
    LAMBDA_SWEEP_DIR,
    MULTI_RUN_DIR,
    MULTI_RUN_GA_PATH,
    MULTI_RUN_NSGA2_PATH,
    PROJECT_ROOT,
)
from src.engine.provenance import stamp

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


def _run_algorithm(algorithm: str, seed: int, nsga2_representative: str):
    """Roda o algoritmo (silencioso) e devolve `(representante, objetivos_da_fronteira,
    marcos)`.
    AG escalar → o melhor indivíduo, sem fronteira (`None`). NSGA-II → o representante
    pedido e os objetivos `(dominance, drift)` de toda a fronteira (hipervolume/spacing).
    O NSGA-II devolve uma fronteira, não um ponto: qual ponto representa a execução é
    uma escolha, registrada no artefato (`nsga2_representative`).

    `marcos` é o dict do eixo de **velocidade**: `converged_at`, `stagnated_at` e os dois
    contadores do gate de convergência (disparos e recusas da confirmação fora do stream,
    que é o ajuste ao stream de RNG quantificado). Só existe no escalar, e a assimetria é
    estrutural, não omissão: "o roster está equilibrado?" não é pergunta que se faça a uma
    FRONTEIRA, que contém de propósito pontos desequilibrados-mas-fiéis. O NSGA-II devolve
    dict **vazio** e as chaves não aparecem no agregado dele — melhor que gravar zeros que
    alguém agregaria sem perceber.
    """
    if algorithm == "ga":
        result = run_ga(seed=seed, verbose=False)
        return result.best, None, {
            "converged_at":           result.converged_at,
            "stagnated_at":           result.stagnated_at,
            "convergence_gate_fired": result.convergence_gate_fired,
            "convergence_rejected":   result.convergence_rejected,
            # A trajetória por geração, por semente. O `results.json` já guarda a da
            # semente 42, mas uma curva de convergência de UMA semente contradiz a
            # premissa deste tool — "uma seed é amostra, não resultado". Com o histórico
            # das N sementes a figura vira média ± banda. São ~30 KB por semente contra
            # 7 min de execução: não guardar é que seria caro.
            "history": [
                {"gen": s.generation, "best_fitness": s.best_fitness,
                 "mean_fitness": s.mean_fitness, "worst_fitness": s.worst_fitness,
                 "dominance_penalty": s.dominance_penalty, "drift_penalty": s.drift_penalty}
                for s in result.history
            ],
        }
    result = run_nsga2(seed=seed, verbose=False)
    front_objectives = [list(ind.objectives) for ind in result.pareto_front]
    return result.representatives[nsga2_representative], front_objectives, {
        # A trajetória do NSGA-II é a da FRONTEIRA, não a de um fitness: amplitude de
        # dominance e drift no front 0 por geração. É o que mostra a fronteira se abrindo
        # (ou retraindo) ao longo da busca, e o análogo mais próximo da curva do escalar.
        "front_history": [
            {"gen": s.generation, "front0": s.front0_selected,
             "dom_range": list(s.front0_ranges[0]), "drift_range": list(s.front0_ranges[1])}
            for s in result.history
        ],
    }


def _evaluate_independent(individual, sims: int) -> FitnessDetail:
    """Reavalia o indivíduo sob a semente de validação — desacopla a métrica
    reportada da semente em que ele foi treinado e iguala o stream entre execuções."""
    set_seed_base(MULTI_RUN_VALIDATION_SEED)
    return evaluate_detail_n(individual, sims)


def _seed_record(detail: FitnessDetail, individual, seed: int,
                 front_objectives, milestones: dict) -> dict:
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
        "dominance_terms": detail.dominance_terms.as_dict(),
        "drift_penalty": detail.drift_penalty,
        "characters": characters,
        "matchups": matchups,
        "n_chars_balanced": n_chars_balanced,
        "n_hard_counters": n_hard_counters,
        "roster_balanced": roster_balanced(detail),
    }
    record.update(milestones)

    # Os genes do representante, sempre. São 55 floats por semente — nada perto de uma
    # execução de 7 a 14 minutos —, e sem eles qualquer pergunta sobre o ROSTER de um
    # braço ("a λ=4 o AG ficou colado no canônico?") exige re-rodar o braço inteiro.
    record["genes"] = [c.genes() for c in individual.characters]

    if front_objectives is not None:
        record["front_size"] = len(front_objectives)
        record["hypervolume"] = hypervolume_2d(front_objectives, HYPERVOLUME_REFERENCE)
        record["spacing"] = spacing(front_objectives)
        # A FRONTEIRA INTEIRA, e não só as métricas dela. É o que torna o sweep de λ um
        # experimento só: a fronteira é λ-independente (`nsga2.scalar_objective` lê os
        # LAMBDA_* apenas para ESCOLHER o `scalar_optimum`, nunca para buscar), então
        # guardá-la permite re-derivar o comparável do escalar em qualquer λ sem re-rodar
        # o NSGA-II. Guardando só `front_size`/`hypervolume`/`spacing`, como antes, cada
        # λ novo custaria uma execução completa do NSGA-II.
        record["front_objectives"] = front_objectives
    return record


# ─────────────────────────────────────────────────────────────────────────────
# Agregação
# ─────────────────────────────────────────────────────────────────────────────


def _aggregate(records: List[dict]) -> dict:
    n = len(records)
    matchup_labels = [matchup_label(i, j) for i, j in combinations(range(len(CHAR_NAMES)), 2)]

    agg = {
        "dominance_penalty": mean_std([r["dominance_penalty"] for r in records]),
        "dominance_terms": {
            term: mean_std([r["dominance_terms"][term] for r in records])
            for term in ("global_term", "cap_term", "decis_term")
        },
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

    # Velocidade — só o escalar tem (ver `_run_algorithm`). A média é sobre as sementes
    # que CONVERGIRAM: incluir as que não convergiram exigiria imputar um valor, e o
    # único honesto seria "não convergiu", que não é um número. A taxa carrega essa
    # informação separada, e as duas juntas é que são lidas.
    if all("converged_at" in r for r in records):
        gens = [r["converged_at"] for r in records if r["converged_at"] is not None]
        stag = [r["stagnated_at"] for r in records if r["stagnated_at"] is not None]
        fired    = sum(r["convergence_gate_fired"] for r in records)
        rejected = sum(r["convergence_rejected"] for r in records)
        agg["convergence"] = {
            "converged_rate":  len(gens) / n,
            "converged_at":    mean_std(gens) if gens else None,
            "stagnated_rate":  len(stag) / n,
            "stagnated_at":    mean_std(stag) if stag else None,
            # O ajuste ao stream quantificado: de quantas vezes o roster PARECEU
            # equilibrado sob o stream de treino, quantas não sobreviveram a um inédito.
            "gate_fired":      fired,
            "gate_rejected":   rejected,
            "rejection_rate":  rejected / fired if fired else None,
        }
    return agg


def aggregate_algorithm(algorithm: str, seeds: List[int], sims: int,
                        nsga2_representative: str) -> dict:
    records: List[dict] = []
    rep_label = f", representante {nsga2_representative}" if algorithm == "nsga2" else ""
    print(f"\n{'═' * 70}")
    print(f"  {algorithm.upper()} — {len(seeds)} execuções (seeds {seeds[0]}..{seeds[-1]}), "
          f"validação com {sims} sims/matchup{rep_label}")
    print(f"{'═' * 70}")

    for idx, seed in enumerate(seeds, start=1):
        print(f"  [{idx:>2}/{len(seeds)}] seed={seed} ... ", end="", flush=True)
        individual, front_objectives, milestones = _run_algorithm(
            algorithm, seed, nsga2_representative
        )
        detail = _evaluate_independent(individual, sims)
        record = _seed_record(detail, individual, seed, front_objectives, milestones)
        records.append(record)
        hv_part = f"  hv={record['hypervolume']:.4f}" if "hypervolume" in record else ""
        conv = record.get("converged_at")
        conv_part = f"  conv={'—' if conv is None else f'g{conv}'}" if "converged_at" in record else ""
        print(f"dom={record['dominance_penalty']:.4f}  drift={record['drift_penalty']:.4f}  "
              f"bonecos eq={record['n_chars_balanced']}/{len(CHAR_NAMES)}  "
              f"counters={record['n_hard_counters']}{hv_part}{conv_part}")

    result = {
        "algorithm": algorithm,
        "n_seeds": len(seeds),
        "seeds": seeds,
        "validation_seed": MULTI_RUN_VALIDATION_SEED,
        "sims_per_matchup": sims,
        "per_seed": records,
        "aggregate": _aggregate(records),
    }
    if algorithm == "nsga2":
        result["nsga2_representative"] = nsga2_representative
    return result


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
    for term, weight in (("global_term", DOMINANCE_GLOBAL_WEIGHT),
                         ("cap_term", DOMINANCE_CAP_WEIGHT),
                         ("decis_term", DOMINANCE_DECIS_WEIGHT)):
        t = agg["dominance_terms"][term]
        print(f"      └ {term:<12} {t['mean']:.4f} ± {t['std']:.4f}   (peso {weight})")
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
    print(f"\n    Hard-counters por execução (pares fora de [35%, 65%]): "
          f"{hc['mean']:.1f} ± {hc['std']:.1f}")

    rate = agg["roster_balanced_rate"]
    print(f"\n    Sementes que equilibram o ROSTER (5 bonecos em banda E 0 hard-counters): "
          f"{rate:.0%}  ({int(round(rate * n))}/{n})")

    conv = agg.get("convergence")
    if conv is not None:
        c_rate, c_at = conv["converged_rate"], conv["converged_at"]
        at = f", na geração {c_at['mean']:.1f} ± {c_at['std']:.1f}" if c_at else ""
        print(f"\n    Velocidade — convergiu (equilíbrio confirmado FORA do stream de treino): "
              f"{c_rate:.0%}  ({int(round(c_rate * n))}/{n}){at}")
        s_rate, s_at = conv["stagnated_rate"], conv["stagnated_at"]
        at = f", na geração {s_at['mean']:.1f} ± {s_at['std']:.1f}" if s_at else ""
        print(f"    Velocidade — estagnou: {s_rate:.0%}  ({int(round(s_rate * n))}/{n}){at}")

    print(f"\n    (secundário) Hard-counter rate por matchup (fração de sementes em que o par vira counter duro):")
    for label, rate_hc in agg["hard_counter_rate"].items():
        wr = agg["matchup_wr"][label]
        flag = "  ⚠" if rate_hc > 0 else ""
        print(f"      {label:<28s} WR {wr['mean']:.0%}±{wr['std']:.0%}   counter em {rate_hc:.0%}{flag}")


def _artifact_path(algorithm: str, lambdas) -> Path:
    """Onde o artefato deste braço é gravado.

    O braço do λ DEFAULT grava nos caminhos principais — ele É a bateria, e é dele que o
    `compare_algorithms` lê. Os demais vão para `lambda_sweep/`, nomeados pelo λ, porque
    são pontos de uma curva e não repetições da mesma configuração: juntá-los ao principal
    convidaria o próximo leitor a agregar λ diferentes como se fossem a mesma coisa."""
    if lambdas == (LAMBDA_DRIFT, LAMBDA_DOMINANCE):
        return MULTI_RUN_GA_PATH if algorithm == "ga" else MULTI_RUN_NSGA2_PATH
    drift, dominance = lambdas
    return LAMBDA_SWEEP_DIR / f"multi_run_{algorithm}_drift{drift:g}_dom{dominance:g}.json"


def _save(result: dict, algorithm: str) -> None:
    path = _artifact_path(algorithm, get_lambdas())
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(), **result}, fh, indent=2, ensure_ascii=False)
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
    parser.add_argument("--lambda-drift", type=float, default=LAMBDA_DRIFT,
                        help=f"Peso do drift no fitness escalar (default: {LAMBDA_DRIFT}). "
                             f"Braço do sweep de λ — grava em results/multi_run/lambda_sweep/ "
                             f"quando difere do default")
    parser.add_argument("--lambda-dominance", type=float, default=LAMBDA_DOMINANCE,
                        help=f"Peso do dominance no fitness escalar (default: {LAMBDA_DOMINANCE})")
    parser.add_argument("--nsga2-representative", default="best_dominance",
                        choices=["best_dominance", "best_drift", "knee_point", "ideal_point",
                                 "scalar_optimum"],
                        help="Ponto da fronteira que representa cada execução do NSGA-II "
                             "(default: best_dominance)")
    return parser.parse_args()


def main():
    args = parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.n_seeds))
    algorithms = ["ga", "nsga2"] if args.algorithm == "both" else [args.algorithm]

    # Antes de qualquer execução: o λ vale para o processo inteiro (e é propagado aos
    # workers), e fica registrado no carimbo de proveniência do artefato.
    set_lambdas_override(args.lambda_drift, args.lambda_dominance)
    if (args.lambda_drift, args.lambda_dominance) != (LAMBDA_DRIFT, LAMBDA_DOMINANCE):
        print(f"\n  BRAÇO DO SWEEP — λ_drift={args.lambda_drift:g} "
              f"λ_dominance={args.lambda_dominance:g} "
              f"(config: {LAMBDA_DRIFT:g} / {LAMBDA_DOMINANCE:g})")
        if "nsga2" in algorithms:
            print("  ⚠ A FRONTEIRA do NSGA-II é λ-independente: rodá-la por braço é "
                  "desperdício.\n    Rode o NSGA-II uma vez no λ default e re-derive o "
                  "`scalar_optimum` por λ.")

    for algorithm in algorithms:
        result = aggregate_algorithm(algorithm, seeds, args.sims, args.nsga2_representative)
        _print_summary(result)
        _save(result, algorithm)


if __name__ == "__main__":
    main()
