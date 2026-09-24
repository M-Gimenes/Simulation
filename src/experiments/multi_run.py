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
  • fração de sementes que equilibram o ROSTER (5 bonecos em banda E 0 hard-counters);
  • identidade de cada roster: o validador (estrutural, Layers 1-2, e comportamental,
    Layer 3) e a concordância de ranking comportamental com o canônico (τ);
  • (secundário) WR média por matchup.

Cada execução do NSGA-II devolve uma fronteira, não um ponto: o ponto que representa
a execução (`--nsga2-representative`, default `scalar_optimum`, o comparável do escalar)
fica registrado no artefato, e os cinco representantes de cada semente ficam gravados e
reavaliados ao lado dele — a comparação pode ser refeita contra qualquer um sem re-rodar
o NSGA-II. Comparação estatística entre algoritmos e contra os controles:
`compare_algorithms`.

Uso:
    py -m src.experiments.multi_run                       # ambos os algoritmos, defaults do config
    py -m src.experiments.multi_run --algorithm nsga2     # só NSGA-II
    py -m src.experiments.multi_run --n-seeds 30          # escala o experimento
    py -m src.experiments.multi_run --nsga2-representative knee_point
    py -m src.experiments.multi_run --algorithm ga --pop 120 --generations 60 --n-seeds 5
    py -m src.experiments.multi_run --algorithm ga --lambda-drift 0   # controle: sem drift
    py -m src.experiments.multi_run --algorithm ga --no-canonical-seed  # controle: sem semente

Só a execução inteiramente no protocolo grava nos caminhos da bateria. Um desvio de
desenho com a amostra e o orçamento do protocolo é um CONTROLE (`results/controls/`); um
desvio de amostra ou de orçamento é EXPLORATÓRIO (`results/exploratory/`). O nome diz o
que desviou (ver `artifact_path`).
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
    ELITE_RATE,
    GA_CANONICAL_SEED,
    HYPERVOLUME_REFERENCE,
    IDENTITY_BEHAVIORAL_SIMS,
    LAMBDA_DOMINANCE,
    LAMBDA_DRIFT,
    MAX_GENERATIONS,
    MULTI_RUN_N_SEEDS,
    MULTI_RUN_SEED_START,
    MULTI_RUN_SIMS,
    MULTI_RUN_VALIDATION_SEED,
    POPULATION_SIZE,
    TOURNAMENT_SIZE,
)
from src.engine.fitness import (
    FitnessDetail,
    character_balanced,
    evaluate_detail_n,
    get_dominance_weights,
    get_lambdas,
    is_hard_counter,
    roster_balanced,
    set_dominance_weights_override,
    set_lambdas_override,
    set_seed_base,
)
from src.engine.ga import run as run_ga
from src.engine.hybrid import HYBRID_CARRY, HYBRID_SPLIT
from src.engine.hybrid import run as run_hybrid
from src.engine.individual import Individual
from src.engine.nsga2 import run as run_nsga2
from src.engine.operators import get_selection, set_selection_override
from src.engine.pareto_metrics import hypervolume_2d, spacing
from src.engine.paths import (
    CONTROLS_DIR,
    EXPLORATORY_DIR,
    MULTI_RUN_GA_PATH,
    MULTI_RUN_NSGA2_PATH,
    PROJECT_ROOT,
)
from src.engine.provenance import override, override_budget, stamp
from src.analysis.archetype_validator import run_validation

CHAR_NAMES: List[str] = [ARCHETYPES[aid].name for aid in ARCHETYPE_ORDER]

# O ponto da fronteira que representa cada execução do NSGA-II no agregado. Os cinco
# representantes são gravados e reavaliados de qualquer forma; este é só o de topo. É o
# `scalar_optimum` — o ponto que minimiza a própria função do AG escalar — porque é o
# único comparável a ele. O `best_dominance` é o extremo da fronteira e perde em drift
# por construção; como manchete, a comparação mediria a escolha do ponto, não o algoritmo.
HEADLINE_REPRESENTATIVE = "scalar_optimum"


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


@dataclass
class SeedRun:
    """O que uma execução entrega ao agregador. `front_objectives`, `representatives` e
    `headline` (o nome do representante de topo) só existem no NSGA-II."""
    individual:       Individual
    milestones:       dict
    front_objectives: Optional[List[List[float]]] = None
    representatives:  Optional[Dict[str, Individual]] = None
    headline:         Optional[str] = None


def _run_algorithm(algorithm: str, seed: int, nsga2_representative: str,
                   pop_size: int, n_generations: int, canonical_seed: bool,
                   hybrid_split: float = HYBRID_SPLIT,
                   hybrid_carry: str = HYBRID_CARRY) -> SeedRun:
    """Roda o algoritmo (silencioso).
    AG escalar → o melhor indivíduo, sem fronteira. NSGA-II → o representante pedido, os
    cinco representantes e os objetivos `(dominance, drift)` de toda a fronteira
    (hipervolume/spacing). O NSGA-II devolve uma fronteira, não um ponto: qual ponto
    representa a execução é uma escolha, registrada no artefato (`nsga2_representative`).

    `milestones` traz a trajetória por geração e, no escalar, o eixo de **velocidade**:
    `converged_at` e os dois contadores do gate de convergência (disparos e recusas da
    confirmação fora do stream, que é o ajuste ao stream de RNG quantificado). A
    velocidade só existe no escalar, e a assimetria é estrutural, não
    omissão: "o roster está equilibrado?" não é pergunta que se faça a uma FRONTEIRA, que
    contém de propósito pontos desequilibrados-mas-fiéis. No NSGA-II essas chaves não
    existem e não aparecem no agregado dele — melhor que gravar zeros que alguém
    agregaria sem perceber.
    """
    if algorithm in ("ga", "hybrid"):
        # O híbrido entrega um PONTO, como o escalar — a fase 2 dele É um AG escalar —,
        # então ele passa pelo mesmo caminho e produz o mesmo registro. `converged_at`
        # já vem deslocado para a escala do orçamento inteiro (ver `hybrid.py`), senão o
        # eixo de velocidade compararia gerações da fase 2 com gerações do run inteiro.
        if algorithm == "hybrid":
            result = run_hybrid(seed=seed, verbose=False, pop_size=pop_size,
                                n_generations=n_generations, split=hybrid_split,
                                carry=hybrid_carry)
        else:
            result = run_ga(seed=seed, verbose=False, pop_size=pop_size,
                            n_generations=n_generations, canonical_seed=canonical_seed)
        return SeedRun(result.best, {
            "converged_at":           result.converged_at,
            "convergence_gate_fired": result.convergence_gate_fired,
            "convergence_rejected":   result.convergence_rejected,
            # `(dominance, drift)` do melhor indivíduo no stream da ÚLTIMA geração —
            # `generation_seed(seed, n_generations)`, o mesmo em que a fronteira do NSGA-II
            # da mesma semente é medida. É o que torna os dois pontos comparáveis sem
            # ruído de stream no teste de relação de Pareto do `compare_algorithms`.
            "in_loop_objectives": [result.best_detail.dominance_penalty,
                                   result.best_detail.drift_penalty],
            # A trajetória por geração, por semente. O `single_run/ga.json` já guarda a da
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
        })
    result = run_nsga2(seed=seed, verbose=False,
                       pop_size=pop_size, n_generations=n_generations)
    front_objectives = [list(ind.objectives) for ind in result.pareto_front]
    return SeedRun(result.representatives[nsga2_representative], {
        # A trajetória do NSGA-II é a da FRONTEIRA, não a de um fitness: amplitude de
        # dominance e drift no front 0 por geração. É o que mostra a fronteira se abrindo
        # (ou retraindo) ao longo da busca, e o análogo mais próximo da curva do escalar.
        "front_history": [
            {"gen": s.generation, "front0": s.front0_selected,
             "dom_range": list(s.front0_ranges[0]), "drift_range": list(s.front0_ranges[1])}
            for s in result.history
        ],
    }, front_objectives, result.representatives, nsga2_representative)


def _evaluate_independent(individual, sims: int) -> FitnessDetail:
    """Reavalia o indivíduo sob a semente de validação — desacopla a métrica
    reportada da semente em que ele foi treinado e iguala o stream entre execuções."""
    set_seed_base(MULTI_RUN_VALIDATION_SEED)
    return evaluate_detail_n(individual, sims)


def _roster_record(individual: Individual, sims: int) -> dict:
    """As métricas de um roster, reavaliado sob a semente de validação — equilíbrio e
    identidade, esta medida pelas duas réguas post-hoc (validador e concordância de
    ranking comportamental), nas condições dos modelos nulos."""
    detail = _evaluate_independent(individual, sims)
    identity = run_validation(individual, behavioral_n=IDENTITY_BEHAVIORAL_SIMS,
                              seed=MULTI_RUN_VALIDATION_SEED)
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

    return {
        "dominance_penalty": detail.dominance_penalty,
        "dominance_terms": detail.dominance_terms.as_dict(),
        "drift_penalty": detail.drift_penalty,
        "characters": characters,
        "matchups": matchups,
        "n_chars_balanced": n_chars_balanced,
        "n_hard_counters": n_hard_counters,
        "roster_balanced": roster_balanced(detail),
        "validator_structural": identity.passed_in("structural_inter", "structural_intra"),
        "validator_behavioral": identity.passed_in("behavioral"),
        "rank_agreement": identity.rank_agreement,
        # Os genes, sempre. São 55 floats por roster — nada perto de uma execução de
        # 7 a 14 minutos —, e sem eles qualquer pergunta sobre o ROSTER de um braço
        # ("a λ=4 o AG ficou colado no canônico?") exige re-rodar o braço inteiro.
        "genes": [c.genes() for c in individual.characters],
    }


def _seed_record(run: SeedRun, seed: int, sims: int) -> dict:
    representatives = None
    if run.representatives is not None:
        # Os CINCO representantes, cada um reavaliado exatamente como o de topo — que é um
        # deles, lido pelo mesmo caminho. Com os cinco aqui, a comparação se refaz contra
        # outro ponto sem re-rodar o NSGA-II. Custa cinco reavaliações por semente, contra
        # uma execução de minutos.
        representatives = {name: _roster_record(individual, sims)
                           for name, individual in run.representatives.items()}
        record = {"seed": seed, **representatives[run.headline]}
    else:
        record = {"seed": seed, **_roster_record(run.individual, sims)}
    record.update(run.milestones)

    front_objectives = run.front_objectives
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

    if representatives is not None:
        record["representatives"] = representatives
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
        "identity": {
            metric: mean_std([r[metric] for r in records])
            for metric in ("validator_structural", "validator_behavioral", "rank_agreement")
        },
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
        fired    = sum(r["convergence_gate_fired"] for r in records)
        rejected = sum(r["convergence_rejected"] for r in records)
        agg["convergence"] = {
            "converged_rate":  len(gens) / n,
            "converged_at":    mean_std(gens) if gens else None,
            # O ajuste ao stream quantificado: de quantas vezes o roster PARECEU
            # equilibrado sob o stream de treino, quantas não sobreviveram a um inédito.
            "gate_fired":      fired,
            "gate_rejected":   rejected,
            "rejection_rate":  rejected / fired if fired else None,
        }
    return agg


def aggregate_algorithm(algorithm: str, seeds: List[int], sims: int,
                        nsga2_representative: str,
                        pop_size: int = POPULATION_SIZE,
                        n_generations: int = MAX_GENERATIONS,
                        canonical_seed: bool = GA_CANONICAL_SEED,
                        hybrid_split: float = HYBRID_SPLIT,
                        hybrid_carry: str = HYBRID_CARRY) -> dict:
    records: List[dict] = []
    rep_label = f", representante {nsga2_representative}" if algorithm == "nsga2" else ""
    print(f"\n{'═' * 70}")
    print(f"  {algorithm.upper()} — {len(seeds)} execuções (seeds {seeds[0]}..{seeds[-1]}), "
          f"validação com {sims} sims/matchup{rep_label}")
    print(f"{'═' * 70}")

    for idx, seed in enumerate(seeds, start=1):
        print(f"  [{idx:>2}/{len(seeds)}] seed={seed} ... ", end="", flush=True)
        run = _run_algorithm(algorithm, seed, nsga2_representative, pop_size, n_generations,
                             canonical_seed, hybrid_split, hybrid_carry)
        record = _seed_record(run, seed, sims)
        records.append(record)
        hv_part = f"  hv={record['hypervolume']:.4f}" if "hypervolume" in record else ""
        conv = record.get("converged_at")
        conv_part = f"  conv={'—' if conv is None else f'g{conv}'}" if "converged_at" in record else ""
        print(f"dom={record['dominance_penalty']:.4f}  drift={record['drift_penalty']:.4f}  "
              f"bonecos eq={record['n_chars_balanced']}/{len(CHAR_NAMES)}  "
              f"counters={record['n_hard_counters']}  L3={record['validator_behavioral']}  "
              f"τ={record['rank_agreement']:+.2f}{hv_part}{conv_part}")

    lambda_drift, lambda_dominance = get_lambdas()
    result = {
        "algorithm": algorithm,
        # Orçamento e λ no CORPO do artefato, não só no carimbo. São a configuração do
        # experimento, e o carimbo é um registro de proveniência que pode ser reescrito
        # (foi, por um re-carimbo em massa descuidado em 2026-09-17, que apagou o λ dos
        # braços do sweep). Configuração do experimento pertence ao artefato.
        "pop_size": pop_size,
        "n_generations": n_generations,
        "lambda_drift": lambda_drift,
        "lambda_dominance": lambda_dominance,
        "dominance_weights": dict(zip(("global", "cap", "decis"), get_dominance_weights())),
        "selection": dict(zip(("elite_rate", "tournament_size"), get_selection())),
        "n_seeds": len(seeds),
        "seeds": seeds,
        "validation_seed": MULTI_RUN_VALIDATION_SEED,
        "sims_per_matchup": sims,
        "per_seed": records,
        "aggregate": _aggregate(records),
    }
    if algorithm == "ga":
        result["canonical_seed"] = canonical_seed
    elif algorithm == "hybrid":
        # A repartição do orçamento é configuração do experimento, como λ e o orçamento:
        # vai no CORPO, e é o que `artifact_path` usa para nomear o braço.
        result["hybrid_split"] = hybrid_split
        result["hybrid_carry"] = hybrid_carry
    else:
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

    ident = agg["identity"]
    print(f"\n    Identidade — validador estrutural (L1+L2): "
          f"{ident['validator_structural']['mean']:.1f} ± {ident['validator_structural']['std']:.1f}"
          f"   comportamental (L3): "
          f"{ident['validator_behavioral']['mean']:.1f} ± {ident['validator_behavioral']['std']:.1f}")
    print(f"    Identidade — concordância de ranking comportamental (τ, 0 = acaso): "
          f"{ident['rank_agreement']['mean']:+.3f} ± {ident['rank_agreement']['std']:.3f}")

    conv = agg.get("convergence")
    if conv is not None:
        c_rate, c_at = conv["converged_rate"], conv["converged_at"]
        at = f", na geração {c_at['mean']:.1f} ± {c_at['std']:.1f}" if c_at else ""
        print(f"\n    Velocidade — convergiu (equilíbrio confirmado FORA do stream de treino): "
              f"{c_rate:.0%}  ({int(round(c_rate * n))}/{n}){at}")

    print(f"\n    (secundário) Hard-counter rate por matchup (fração de sementes em que o par vira counter duro):")
    for label, rate_hc in agg["hard_counter_rate"].items():
        wr = agg["matchup_wr"][label]
        flag = "  ⚠" if rate_hc > 0 else ""
        print(f"      {label:<28s} WR {wr['mean']:.0%}±{wr['std']:.0%}   counter em {rate_hc:.0%}{flag}")


def artifact_path(result: dict) -> Path:
    """Onde o artefato desta execução é gravado — função só do que o corpo dele registra.

    Só a execução **inteiramente no protocolo** grava nos caminhos principais: ela É a
    bateria, e é dela que o `compare_algorithms` lê. Os desvios são de dois tipos:

    - de AMOSTRA ou ORÇAMENTO (população, gerações, nº e início das sementes, sims da
      reavaliação) → `exploratory/`: o número não é citável;
    - só de DESENHO (λ, pesos do dominance, seleção, semente canônica, representante de
      topo), com amostra e orçamento do protocolo → `controls/`: é um braço de controle,
      citável e comparável à bateria.

    O sufixo é montado a partir das diferenças reais, e não de um rótulo passado à mão,
    porque o risco aqui é silencioso nos dois sentidos: um nome fixo faria dois braços
    diferentes se sobrescreverem, e cair no caminho principal faria uma execução barata
    **apagar** horas de bateria sem aviso."""
    algorithm = result["algorithm"]
    partes = []
    if (result["pop_size"], result["n_generations"]) != (POPULATION_SIZE, MAX_GENERATIONS):
        partes.append(f"pop{result['pop_size']}_gen{result['n_generations']}")
    seeds = result["seeds"]
    if len(seeds) != MULTI_RUN_N_SEEDS:
        partes.append(f"n{len(seeds)}")
    if seeds[0] != MULTI_RUN_SEED_START:
        partes.append(f"seed{seeds[0]}")
    if result["sims_per_matchup"] != MULTI_RUN_SIMS:
        partes.append(f"sims{result['sims_per_matchup']}")
    sample_deviates = bool(partes)

    lambdas = (result["lambda_drift"], result["lambda_dominance"])
    if lambdas != (LAMBDA_DRIFT, LAMBDA_DOMINANCE):
        partes.append(f"drift{lambdas[0]:g}_dom{lambdas[1]:g}")
    dom_weights = tuple(result["dominance_weights"].values())
    if dom_weights != (DOMINANCE_GLOBAL_WEIGHT, DOMINANCE_CAP_WEIGHT, DOMINANCE_DECIS_WEIGHT):
        g, c, d = dom_weights
        partes.append(f"domw{g:g}-{c:g}-{d:g}")
    selection = result["selection"]
    if selection["elite_rate"] != ELITE_RATE:
        partes.append(f"elite{selection['elite_rate']:g}")
    if selection["tournament_size"] != TOURNAMENT_SIZE:
        partes.append(f"tour{selection['tournament_size']:g}")
    if algorithm == "ga" and result["canonical_seed"] != GA_CANONICAL_SEED:
        partes.append("unseeded")
    if algorithm == "nsga2" and result["nsga2_representative"] != HEADLINE_REPRESENTATIVE:
        partes.append(f"rep-{result['nsga2_representative']}")
    if algorithm == "hybrid":
        # O híbrido NUNCA cai no caminho principal: `multi_run_ga.json` e
        # `multi_run_nsga2.json` são os dois algoritmos que a pergunta de pesquisa compara,
        # e o híbrido é um terceiro braço. Split e carry entram sempre no nome, mesmo nos
        # valores default, porque é deles que a comparação entre braços trata.
        partes.append(f"split{result['hybrid_split']:g}_{result['hybrid_carry']}")
    if not partes:
        return MULTI_RUN_GA_PATH if algorithm == "ga" else MULTI_RUN_NSGA2_PATH
    folder = EXPLORATORY_DIR if sample_deviates else CONTROLS_DIR
    return folder / f"multi_run_{algorithm}_{'_'.join(partes)}.json"


def _save(result: dict) -> None:
    path = artifact_path(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(tool=__spec__.name), **result}, fh, indent=2, ensure_ascii=False)
    print(f"\n  Salvo em {path.relative_to(PROJECT_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="N execuções independentes + estatística agregada (metodologia 1.1)"
    )
    parser.add_argument("--hybrid-split", type=float, default=HYBRID_SPLIT,
                        help=f"fração do orçamento na fase NSGA-II do híbrido "
                             f"(default: {HYBRID_SPLIT})")
    parser.add_argument("--hybrid-carry", default=HYBRID_CARRY,
                        help=f"o que a fase 1 entrega à fase 2: 'front' (a fronteira "
                             f"inteira) ou o nome de um representante (default: {HYBRID_CARRY})")
    parser.add_argument("--algorithm", choices=["ga", "nsga2", "hybrid", "both"], default="both",
                        help="Algoritmo(s) a agregar (default: both)")
    parser.add_argument("--n-seeds", type=int, default=MULTI_RUN_N_SEEDS,
                        help=f"Número de execuções (default: {MULTI_RUN_N_SEEDS})")
    parser.add_argument("--seed-start", type=int, default=MULTI_RUN_SEED_START,
                        help=f"Primeira semente (default: {MULTI_RUN_SEED_START})")
    parser.add_argument("--sims", type=int, default=MULTI_RUN_SIMS,
                        help=f"Sims/matchup na reavaliação independente (default: {MULTI_RUN_SIMS})")
    parser.add_argument("--pop", type=int, default=POPULATION_SIZE,
                        help=f"Tamanho da população (default: {POPULATION_SIZE}). "
                             f"Reduzir barateia a execução para experimentos exploratórios; "
                             f"o elitismo continua sendo 10%% do tamanho real")
    parser.add_argument("--generations", type=int, default=MAX_GENERATIONS,
                        help=f"Gerações por execução (default: {MAX_GENERATIONS})")
    parser.add_argument("--lambda-drift", type=float, default=LAMBDA_DRIFT,
                        help=f"Peso do drift no fitness escalar (default: {LAMBDA_DRIFT}). "
                             f"Braço do sweep de λ")
    parser.add_argument("--lambda-dominance", type=float, default=LAMBDA_DOMINANCE,
                        help=f"Peso do dominance no fitness escalar (default: {LAMBDA_DOMINANCE})")
    parser.add_argument("--dom-global", type=float, default=DOMINANCE_GLOBAL_WEIGHT,
                        help=f"Peso do global_term no dominance (default: {DOMINANCE_GLOBAL_WEIGHT})")
    parser.add_argument("--dom-cap", type=float, default=DOMINANCE_CAP_WEIGHT,
                        help=f"Peso do cap_term (default: {DOMINANCE_CAP_WEIGHT})")
    parser.add_argument("--dom-decis", type=float, default=DOMINANCE_DECIS_WEIGHT,
                        help=f"Peso do decis_term (default: {DOMINANCE_DECIS_WEIGHT})")
    parser.add_argument("--elite-rate", type=float, default=ELITE_RATE,
                        help=f"Fração da população preservada por elitismo "
                             f"(default: {ELITE_RATE}). Só o AG escalar; 0 desliga")
    parser.add_argument("--tournament-size", type=int, default=TOURNAMENT_SIZE,
                        help=f"Candidatos por torneio (default: {TOURNAMENT_SIZE}). Só o AG "
                             f"escalar — o NSGA-II usa torneio binário por dominância")
    parser.add_argument("--nsga2-representative", default=HEADLINE_REPRESENTATIVE,
                        choices=["best_dominance", "best_drift", "knee_point", "ideal_point",
                                 "scalar_optimum"],
                        help="Ponto da fronteira que representa cada execução do NSGA-II "
                             f"(default: {HEADLINE_REPRESENTATIVE})")
    parser.add_argument("--no-canonical-seed", dest="canonical_seed", action="store_false",
                        help="AG escalar com população inicial 100%% aleatória, como a do "
                             "NSGA-II — o controle que separa algoritmo de inicialização")
    return parser.parse_args()


def main():
    args = parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.n_seeds))
    algorithms = ["ga", "nsga2"] if args.algorithm == "both" else [args.algorithm]

    # Antes de qualquer execução: o λ vale para o processo inteiro (e é propagado aos
    # workers), e fica registrado no carimbo de proveniência do artefato.
    set_lambdas_override(args.lambda_drift, args.lambda_dominance)
    set_dominance_weights_override(args.dom_global, args.dom_cap, args.dom_decis)
    set_selection_override(args.elite_rate, args.tournament_size)
    selecao = (args.elite_rate, args.tournament_size)
    if selecao != (ELITE_RATE, TOURNAMENT_SIZE):
        print(f"\n  SELEÇÃO — elitismo={args.elite_rate:g} torneio={args.tournament_size:g} "
              f"(config: {ELITE_RATE:g} / {TOURNAMENT_SIZE:g})")
        if "nsga2" in algorithms:
            print("  ⚠ Os dois valem SÓ para o AG escalar. O NSGA-II não tem elitismo por "
                  "fitness\n    (a elite dele é o rank de Pareto) nem torneio de tamanho k "
                  "— rodá-lo por\n    braço mede o mesmo número N vezes.")
    pesos = (args.dom_global, args.dom_cap, args.dom_decis)
    if pesos != (DOMINANCE_GLOBAL_WEIGHT, DOMINANCE_CAP_WEIGHT, DOMINANCE_DECIS_WEIGHT):
        print(f"\n  PESOS DO DOMINANCE — global={args.dom_global:g} cap={args.dom_cap:g} "
              f"decis={args.dom_decis:g} "
              f"(config: {DOMINANCE_GLOBAL_WEIGHT:g}/{DOMINANCE_CAP_WEIGHT:g}/{DOMINANCE_DECIS_WEIGHT:g})")
        print("  ⚠ `dominance_penalty` NÃO é comparável entre braços — os pesos o DEFINEM."
              "\n    Compare pelos TERMOS (global/cap/decis) e pelas métricas post-hoc"
              "\n    (hard-counters, bonecos em banda, drift), que não dependem dos pesos.")
    if (args.lambda_drift, args.lambda_dominance) != (LAMBDA_DRIFT, LAMBDA_DOMINANCE):
        print(f"\n  BRAÇO DO SWEEP — λ_drift={args.lambda_drift:g} "
              f"λ_dominance={args.lambda_dominance:g} "
              f"(config: {LAMBDA_DRIFT:g} / {LAMBDA_DOMINANCE:g})")
        if "nsga2" in algorithms:
            print("  ⚠ A FRONTEIRA do NSGA-II é λ-independente: rodá-la por braço é "
                  "desperdício.\n    Rode o NSGA-II uma vez no λ default e re-derive o "
                  "`scalar_optimum` por λ.")

    override("GA_CANONICAL_SEED", args.canonical_seed)
    if args.canonical_seed != GA_CANONICAL_SEED:
        print("\n  CONTROLE — AG escalar SEM a semente canônica (população inicial aleatória)")
        if "nsga2" in algorithms:
            print("  ⚠ Vale só para o AG escalar: o NSGA-II já nasce 100% aleatório.")

    reduzido = (args.pop, args.generations) != (POPULATION_SIZE, MAX_GENERATIONS)
    if reduzido:
        print(f"\n  ORÇAMENTO REDUZIDO — pop={args.pop} × {args.generations} gerações "
              f"(config: {POPULATION_SIZE} × {MAX_GENERATIONS}), "
              f"~{args.pop * args.generations / (POPULATION_SIZE * MAX_GENERATIONS):.0%} do custo.")
        print("  Serve para ORDENAR configurações, não para número citável: a convergência"
              "\n  não transfere (60 gerações não dizem nada sobre convergir na 39 de 150).")

    for algorithm in algorithms:
        # O orçamento vale por algoritmo — as constantes que cada um lê são distintas.
        override_budget(args.pop, args.generations, algorithm)
        result = aggregate_algorithm(algorithm, seeds, args.sims, args.nsga2_representative,
                                     pop_size=args.pop, n_generations=args.generations,
                                     canonical_seed=args.canonical_seed,
                                     hybrid_split=args.hybrid_split,
                                     hybrid_carry=args.hybrid_carry)
        _print_summary(result)
        _save(result)


if __name__ == "__main__":
    main()
