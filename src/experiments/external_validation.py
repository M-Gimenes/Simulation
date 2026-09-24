"""external_validation.py — Item 3.2 da metodologia: validação externa ao fitness.

Estilo Ludi (Browne & Maire 2010): não confiar num único número de fitness — validar o
artefato evoluído *fora* do laço de otimização. Fixa UM indivíduo (canônico, melhor do
AG, ou representante do NSGA-II) e o reavalia em duas perguntas diferentes:

  • **Replicação** — as mesmas regras do treino, sob sementes que o AG nunca viu
    (fora do range de treino e da seed de validação do `multi_run`), com uma amostra
    grande: o equilíbrio medido durante a busca se confirma com mais lutas?
  • **Robustez** — regras de combate que o AG nunca viu, uma constante por vez
    (`EXTERNAL_VALIDATION_RULE_PERTURBATIONS`: distância inicial, tamanho do campo,
    persistência da intenção, redução da guarda). Trocar a semente só repete a mesma
    pergunta com mais amostra; mudar a regra testa se o equilíbrio sobrevive fora das
    condições exatas em que foi otimizado.

Em cada condição, as `EXTERNAL_VALIDATION_N_SEEDS` sementes são somadas numa amostra só
(5000 lutas por par), e o veredito sai do **intervalo de confiança** (Wilson, 95%) de cada
WR contra a banda:

  • dentro — o IC inteiro dentro da banda;
  • fora — o IC inteiro fora da banda (a falha é estatisticamente clara);
  • inconclusivo — o IC atravessa a borda.

A condição é ROBUSTA se todo boneco e todo par estão dentro, FRÁGIL se algum está fora,
INCONCLUSIVA no resto. O veredito não depende de quantas sementes se usa: um quantificador
"falhou em alguma das K" ficaria mais severo a cada semente acrescentada, mesmo com o
roster intacto.

A bateria de identidade post-hoc (ciclo, drift_table, fingerprint, archetype_validator)
já é coberta pelo `report`; esta validação foca no eixo do **equilíbrio**, que é onde o
ajuste ao fitness se esconde.

Uso:
    py -m src.experiments.external_validation              # canônico
    py -m src.experiments.external_validation --evolved    # melhor do AG
    py -m src.experiments.external_validation --nsga2 scalar_optimum
    py -m src.experiments.external_validation --n-seeds 20 --sims 1000
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, List, Tuple

from src.engine.combat import CombatRules, TRAINING_RULES, set_rules
from src.engine.config import (
    EXTERNAL_VALIDATION_N_SEEDS,
    EXTERNAL_VALIDATION_RULE_PERTURBATIONS,
    EXTERNAL_VALIDATION_SEED_START,
    EXTERNAL_VALIDATION_SIMS,
    GLOBAL_CONVERGENCE_THRESHOLD,
    MATCHUP_WR_CAP,
)
from src.engine.fitness import evaluate_detail_n, set_seed_base
from src.engine.individual import Individual
from src.engine.paths import EXTERNAL_VALIDATION_DIR, PROJECT_ROOT
from src.engine.provenance import stamp
from src.experiments.multi_run import CHAR_NAMES, matchup_label, mean_std
from src.analysis.analyze_matchups import wilson_ci

REPLICATION = "replicação (regras do treino)"

# Bandas do critério de equilíbrio: WR global de cada boneco e WR de cada par.
CHARACTER_BAND = (0.5 - GLOBAL_CONVERGENCE_THRESHOLD, 0.5 + GLOBAL_CONVERGENCE_THRESHOLD)
PAIR_BAND      = (0.5 - MATCHUP_WR_CAP, 0.5 + MATCHUP_WR_CAP)


def _load_individual(args: argparse.Namespace):
    if args.nsga2:
        return (Individual.from_nsga2(representative=args.nsga2, require_current=True),
                f"nsga2_{args.nsga2}")
    if args.evolved:
        return Individual.from_results(require_current=True), "evolved"
    return Individual.from_canonical(), "canonical"


def conditions() -> List[Tuple[str, CombatRules]]:
    """(rótulo, regras): a replicação e uma condição por perturbação de regra."""
    perturbed = [
        (f"{name}={value:g}", TRAINING_RULES._replace(**{name.lower(): value}))
        for name, value in EXTERNAL_VALIDATION_RULE_PERTURBATIONS
    ]
    return [(REPLICATION, TRAINING_RULES)] + perturbed


def band_status(ci: Tuple[float, float], band: Tuple[float, float]) -> str:
    """"dentro" / "fora" / "inconclusivo" — o IC contra a banda."""
    lo, hi = ci
    if band[0] <= lo and hi <= band[1]:
        return "dentro"
    if hi < band[0] or lo > band[1]:
        return "fora"
    return "inconclusivo"


def verdict(statuses: List[str]) -> str:
    if "fora" in statuses:
        return "FRÁGIL"
    if "inconclusivo" in statuses:
        return "INCONCLUSIVO"
    return "ROBUSTO"


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação de uma condição
# ─────────────────────────────────────────────────────────────────────────────


def _evaluate_condition(individual: Individual, rules: CombatRules,
                        seeds: List[int], sims: int) -> dict:
    """Soma as sementes numa amostra só e classifica cada WR pelo IC contra a banda."""
    set_rules(rules)
    try:
        details = []
        for seed in seeds:
            set_seed_base(seed)
            details.append(evaluate_detail_n(individual, sims))
    finally:
        set_rules(TRAINING_RULES)

    fights_per_pair = sims * len(seeds)
    fights_per_char = fights_per_pair * (len(CHAR_NAMES) - 1)

    characters: Dict[str, dict] = {}
    for i, name in enumerate(CHAR_NAMES):
        wr = sum(d.winrates[i] for d in details) / len(details)
        ci = wilson_ci(wr * fights_per_char, fights_per_char)
        characters[name] = {"wr": wr, "ci": list(ci), "status": band_status(ci, CHARACTER_BAND)}

    matchups: Dict[str, dict] = {}
    for (i, j) in details[0].matchup_winrates:
        wr = sum(d.matchup_winrates[(i, j)] for d in details) / len(details)
        ci = wilson_ci(wr * fights_per_pair, fights_per_pair)
        matchups[matchup_label(i, j)] = {"wr": wr, "ci": list(ci),
                                         "status": band_status(ci, PAIR_BAND)}

    statuses = ([c["status"] for c in characters.values()]
                + [m["status"] for m in matchups.values()])
    return {
        "rules": rules._asdict(),
        "fights_per_pair": fights_per_pair,
        "dominance_penalty": mean_std([d.dominance_penalty for d in details]),
        "drift_penalty": details[0].drift_penalty,
        "characters": characters,
        "matchups": matchups,
        "verdict": verdict(statuses),
    }


def validate(individual: Individual, seeds: List[int], sims: int) -> dict:
    print(f"\n{'═' * 78}")
    print(f"  Validação externa — {len(seeds)} sementes × {sims} sims/matchup por condição "
          f"(seeds {seeds[0]}..{seeds[-1]})")
    print(f"{'═' * 78}")

    results: Dict[str, dict] = {}
    for label, rules in conditions():
        print(f"  {label:<36} ... ", end="", flush=True)
        results[label] = _evaluate_condition(individual, rules, seeds, sims)
        print(results[label]["verdict"])

    robustness = [results[label]["verdict"] for label, _ in conditions()[1:]]
    return {
        "seeds": seeds,
        "sims_per_matchup": sims,
        "character_band": list(CHARACTER_BAND),
        "pair_band": list(PAIR_BAND),
        "conditions": results,
        "replication_verdict": results[REPLICATION]["verdict"],
        "robustness_verdicts": {v: robustness.count(v)
                                for v in ("ROBUSTO", "INCONCLUSIVO", "FRÁGIL")},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Relatório
# ─────────────────────────────────────────────────────────────────────────────

_MARK = {"dentro": "✓", "inconclusivo": "~", "fora": "✗"}


def _print_condition(label: str, cond: dict) -> None:
    print(f"\n  ── {label} — {cond['verdict']}  "
          f"(dominance {cond['dominance_penalty']['mean']:.4f}, "
          f"{cond['fights_per_pair']} lutas por par)")
    for name, c in cond["characters"].items():
        lo, hi = c["ci"]
        print(f"      {_MARK[c['status']]} {name:<15s} {c['wr']:.1%}  IC [{lo:.1%}, {hi:.1%}]")
    off = {k: m for k, m in cond["matchups"].items() if m["status"] != "dentro"}
    if off:
        for k, m in off.items():
            lo, hi = m["ci"]
            print(f"      {_MARK[m['status']]} {k:<28s} {m['wr']:.1%}  IC [{lo:.1%}, {hi:.1%}]")
    else:
        print("      ✓ todos os pares dentro da banda de counter")


def _print_summary(result: dict, label: str) -> None:
    print(f"\n{'═' * 78}")
    print(f"  VALIDAÇÃO EXTERNA — {label}")
    print(f"  banda do boneco [{CHARACTER_BAND[0]:.0%}, {CHARACTER_BAND[1]:.0%}] · banda do par "
          f"[{PAIR_BAND[0]:.0%}, {PAIR_BAND[1]:.0%}] · ✓ IC dentro  ~ IC na borda  ✗ IC fora")
    print(f"{'═' * 78}")
    for cond_label, cond in result["conditions"].items():
        _print_condition(cond_label, cond)
    counts = result["robustness_verdicts"]
    n = sum(counts.values())
    print(f"\n  Replicação: {result['replication_verdict']}")
    print(f"  Robustez a regras: {counts['ROBUSTO']}/{n} robustas · "
          f"{counts['INCONCLUSIVO']}/{n} inconclusivas · {counts['FRÁGIL']}/{n} frágeis")


def _save(result: dict, label: str) -> None:
    EXTERNAL_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    path = EXTERNAL_VALIDATION_DIR / f"external_validation_{label}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(tool=__spec__.name), "individual": label, **result},
                  fh, indent=2, ensure_ascii=False)
    print(f"\n  Salvo em {path.relative_to(PROJECT_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validação externa ao fitness — replicação e robustez a regras (metodologia 3.2)"
    )
    parser.add_argument("--evolved", action="store_true", help="melhor do AG (single_run/ga.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="scalar_optimum",
                        help="representante do NSGA-II (scalar_optimum|best_dominance|knee_point|"
                             "best_drift|ideal_point)")
    parser.add_argument("--n-seeds", type=int, default=EXTERNAL_VALIDATION_N_SEEDS,
                        help=f"sementes por condição (default: {EXTERNAL_VALIDATION_N_SEEDS})")
    parser.add_argument("--seed-start", type=int, default=EXTERNAL_VALIDATION_SEED_START,
                        help=f"primeira semente (default: {EXTERNAL_VALIDATION_SEED_START})")
    parser.add_argument("--sims", type=int, default=EXTERNAL_VALIDATION_SIMS,
                        help=f"sims/matchup por semente (default: {EXTERNAL_VALIDATION_SIMS})")
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
