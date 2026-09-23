"""hybrid_choice.py — aplica o critério pré-registrado que escolhe a configuração do
híbrido, sobre os braços do `run_hybrid_sweep.ps1`.

A escolha é uma decisão de projeto, e decisão de projeto tomada depois de ver os números
não é decisão, é ajuste. Por isso o critério mora aqui, em código, e grava a **trilha**
inteira no artefato: quem foi eliminado, por quê, e o que decidiu o desempate.

O CRITÉRIO, na ordem (registrado em 2026-09-22, antes do sweep rodar):

1. **Elimina quem é pior em equilíbrio.** A entrega é um elenco equilibrado; a pergunta
   de pesquisa pressupõe que o equilíbrio foi alcançado. Um braço que compra identidade
   com equilíbrio responde outra pergunta. Com n = 5 uma mediana por um fio é ruído, então
   a eliminação exige evidência **consistente**: perder `dominance_penalty` em ≥ 4 das 5
   sementes, **ou** ser pior nas duas medidas de equilíbrio ao mesmo tempo (mediana de
   `dominance_penalty` e média de `n_hard_counters`).
2. **Entre os sobreviventes, maximiza quantas das 4 réguas de identidade bate** — drift,
   validador estrutural (L1+L2), Layer 3 e concordância de ranking τ.
3. **Desempate por τ.** É a régua funcional contínua, e a pergunta de pesquisa fala em
   *"functional identities"*.
4. **Segundo desempate: a configuração mais simples** (split 0,5 carregando a fronteira
   inteira). Com n = 5 nada separa do ruído, e um braço escolhido por um fio é um braço
   escolhido por sorte.

ESTE TOOL ESCOLHE A CONFIGURAÇÃO, NÃO DECIDE A ADOÇÃO — correção de escopo feita em
2026-09-23, depois de medir a âncora e **antes** de ver os braços. A versão anterior do
critério deixava o sweep recusar o híbrido, e isso contraria a regra do próprio projeto:
*orçamento reduzido ordena configurações, nunca declara vencedor.*

O que forçou a correção foi a âncora. O AG escalar a 60 gerações tem **τ = 0,463**; a 150,
**0,281** (amostras diferentes, n = 5 contra 20, então é indício e não prova — mas a
direção é a do mecanismo). Ou seja: o escalar perde identidade *ao longo* da execução,
e a 60 gerações ele ainda não degradou. O sweep, portanto, compara o híbrido contra uma
âncora artificialmente forte, e tende a **subestimar** o braço. Deixar essa amostra vetar
a adoção seria decidir pelo artefato de orçamento.

Então: se nenhum braço sobreviver ao passo 1, a escolha cai na configuração mais simples
(0,5 / front) com `adoption_deferred = true`. A bateria mede o braço com n = 20 no
orçamento inteiro de qualquer forma — custa 104 min de uma bateria de 8h —, e é ela, com
o teste pareado, que decide se o híbrido entra como **contribuição de método** ou fica
como **braço descritivo** ao lado do achado do AG escalar.

O que o critério NÃO é: a soma `dominance + drift`. Os braços se comparam pelos termos e
pelas métricas post-hoc, nunca pelo composto, que os `LAMBDA_*` definem — ordenar por ele
embutiria a escolha de λ na decisão.

RESSALVA DECLARADA, e ela é mais forte aqui que num sweep comum. O projeto usa orçamento
reduzido para ORDENAR configurações porque ordenação costuma transferir de orçamento. No
híbrido isso é mais frágil: o mecanismo dele depende de a fase de Pareto ter gerações
suficientes para a fronteira se abrir, e a 60 gerações um split 0,25 dá só 15 gerações de
NSGA-II contra 75 no orçamento da bateria. A ordenação **entre splits** pode, portanto,
não transferir. É por isso que o passo 4 desempata pela configuração mais simples em vez
de pelo melhor número: com n = 5 e essa dependência de orçamento, escolher por um fio é
escolher por sorte. Quem avalia a configuração escolhida é a bateria, com n = 20 e o
orçamento inteiro.

Uso:
    py -m src.experiments.hybrid_choice
"""

from __future__ import annotations

import json
import statistics as st
from typing import Dict, List, Optional, Tuple

from src.engine.paths import EXPLORATORY_DIR, RESULTS_DIR
from src.engine.provenance import stamp

CHOICE_PATH = EXPLORATORY_DIR / "hybrid_choice.json"

ANCHOR_GLOB = "multi_run_ga_pop120_gen60_n5_seed1000.json"
ARM_GLOB = "multi_run_hybrid_pop120_gen60_n5_seed1000_split*.json"

# (campo, rótulo, "menor" ou "maior")
BALANCE = [("dominance_penalty", "dominance", "menor"),
           ("n_hard_counters", "counters", "menor")]
IDENTITY = [("drift_penalty", "drift", "menor"),
            ("validator_structural", "L1+L2", "maior"),
            ("validator_behavioral", "L3", "maior"),
            ("rank_agreement", "τ", "maior")]

SIMPLEST = (0.5, "front")


def _better(a: float, b: float, direction: str) -> bool:
    return a < b if direction == "menor" else a > b


def _by_seed(artifact: dict, field: str) -> Dict[int, float]:
    return {r["seed"]: r[field] for r in artifact["per_seed"]}


def paired_wins(arm: dict, anchor: dict, field: str, direction: str) -> Tuple[int, int]:
    """Em quantas sementes o braço bate a âncora. Pareado: a mesma semente fixa população
    inicial, operadores e streams nos dois lados, então a diferença é do algoritmo."""
    a, b = _by_seed(arm, field), _by_seed(anchor, field)
    common = sorted(set(a) & set(b))
    return sum(_better(a[s], b[s], direction) for s in common), len(common)


def _median(artifact: dict, field: str) -> float:
    return st.median(r[field] for r in artifact["per_seed"])


def _mean(artifact: dict, field: str) -> float:
    return st.mean(r[field] for r in artifact["per_seed"])


def evaluate_arm(arm: dict, anchor: dict) -> dict:
    """A ficha de um braço contra a âncora: passo 1 (eliminação) e passo 2 (contagem)."""
    dom_wins, n = paired_wins(arm, anchor, "dominance_penalty", "menor")
    worse_dominance_median = _median(arm, "dominance_penalty") > _median(anchor, "dominance_penalty")
    worse_counters = _mean(arm, "n_hard_counters") > _mean(anchor, "n_hard_counters")

    # Evidência consistente de custo em equilíbrio, e não uma mediana por um fio.
    loses_most_seeds = dom_wins <= n - 4
    worse_on_both = worse_dominance_median and worse_counters
    eliminated = loses_most_seeds or worse_on_both
    reasons = []
    if loses_most_seeds:
        reasons.append(f"perde dominance em {n - dom_wins}/{n} sementes")
    if worse_on_both:
        reasons.append("pior na mediana do dominance E na média de counters")

    identity_beaten = []
    for field, label, direction in IDENTITY:
        if _better(_median(arm, field), _median(anchor, field), direction):
            identity_beaten.append(label)

    return {
        "split": arm["hybrid_split"],
        "carry": arm["hybrid_carry"],
        "label": f"split {arm['hybrid_split']:g} / {arm['hybrid_carry']}",
        "dominance_median": _median(arm, "dominance_penalty"),
        "dominance_paired_wins": dom_wins,
        "counters_mean": _mean(arm, "n_hard_counters"),
        "balanced_rate": sum(r["roster_balanced"] for r in arm["per_seed"]) / len(arm["per_seed"]),
        "drift_median": _median(arm, "drift_penalty"),
        "validator_structural_median": _median(arm, "validator_structural"),
        "validator_behavioral_median": _median(arm, "validator_behavioral"),
        "rank_agreement_median": _median(arm, "rank_agreement"),
        "identity_beaten": identity_beaten,
        "n_identity_beaten": len(identity_beaten),
        "eliminated": eliminated,
        "elimination_reasons": reasons,
    }


def choose(cards: List[dict]) -> Tuple[Optional[dict], List[str]]:
    """Passos 2–4 sobre os sobreviventes. Devolve o escolhido e a trilha da decisão."""
    trail: List[str] = []
    survivors = [c for c in cards if not c["eliminated"]]
    trail.append(f"passo 1: {len(survivors)} de {len(cards)} braços sobrevivem ao filtro "
                 f"de equilíbrio")
    if not survivors:
        trail.append("nenhum sobrevivente no orçamento reduzido — a ADOÇÃO fica para a "
                     "bateria (n = 20, orçamento inteiro), que é quem pode decidi-la")
        fallback = [c for c in cards if (c["split"], c["carry"]) == SIMPLEST]
        chosen = fallback[0] if fallback else cards[0]
        chosen = dict(chosen, adoption_deferred=True)
        trail.append(f"configuração a medir na bateria: a mais simples ({chosen['label']})")
        return chosen, trail

    best_count = max(c["n_identity_beaten"] for c in survivors)
    finalists = [c for c in survivors if c["n_identity_beaten"] == best_count]
    trail.append(f"passo 2: melhor contagem de identidade = {best_count}/4 "
                 f"({len(finalists)} braço(s): {', '.join(c['label'] for c in finalists)})")
    if len(finalists) == 1:
        return dict(finalists[0], adoption_deferred=False), trail

    best_tau = max(c["rank_agreement_median"] for c in finalists)
    tau_finalists = [c for c in finalists if c["rank_agreement_median"] == best_tau]
    trail.append(f"passo 3: desempate por τ — melhor mediana {best_tau:+.4f} "
                 f"({len(tau_finalists)} braço(s))")
    if len(tau_finalists) == 1:
        return dict(tau_finalists[0], adoption_deferred=False), trail

    simplest = [c for c in tau_finalists if (c["split"], c["carry"]) == SIMPLEST]
    if simplest:
        trail.append(f"passo 4: empate em τ — fica a configuração mais simples "
                     f"(split {SIMPLEST[0]:g} / {SIMPLEST[1]})")
        return dict(simplest[0], adoption_deferred=False), trail
    chosen = sorted(tau_finalists, key=lambda c: (abs(c["split"] - SIMPLEST[0]), c["carry"]))[0]
    trail.append(f"passo 4: empate em τ e a mais simples não está entre os finalistas — "
                 f"fica a mais próxima dela ({chosen['label']})")
    return dict(chosen, adoption_deferred=False), trail


def _load() -> Tuple[dict, List[dict]]:
    anchor_path = EXPLORATORY_DIR / ANCHOR_GLOB
    if not anchor_path.exists():
        raise SystemExit(f"Âncora não encontrada: {anchor_path}\n"
                         f"Rode `.\\scripts\\run_hybrid_sweep.ps1` primeiro.")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    arms = [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(EXPLORATORY_DIR.glob(ARM_GLOB))]
    if not arms:
        raise SystemExit("Nenhum braço de híbrido em results/exploratory/.")
    return anchor, arms


def _print(anchor: dict, cards: List[dict], chosen: Optional[dict], trail: List[str]) -> None:
    line = "═" * 96
    print(line)
    print("  ESCOLHA DA CONFIGURAÇÃO DO HÍBRIDO — critério pré-registrado")
    print(line)
    print(f"  sementes {anchor['seeds'][0]}–{anchor['seeds'][-1]}, "
          f"pop {anchor['pop_size']} × {anchor['n_generations']} gerações, "
          f"reavaliação com {anchor['sims_per_matchup']} sims/matchup")
    print()
    print(f"  {'braço':<26}{'dominance':>11}{'venc.':>7}{'counters':>10}{'eq.':>6}"
          f"{'drift':>9}{'L1+2':>7}{'L3':>5}{'τ':>8}{'ident.':>8}")
    print("  " + "─" * 94)
    print(f"  {'ÂNCORA — AG escalar':<26}{_median(anchor, 'dominance_penalty'):>11.4f}"
          f"{'—':>7}{_mean(anchor, 'n_hard_counters'):>10.2f}"
          f"{sum(r['roster_balanced'] for r in anchor['per_seed']):>3}/{len(anchor['per_seed']):<2}"
          f"{_median(anchor, 'drift_penalty'):>9.4f}"
          f"{_median(anchor, 'validator_structural'):>7.1f}"
          f"{_median(anchor, 'validator_behavioral'):>5.1f}"
          f"{_median(anchor, 'rank_agreement'):>+8.3f}{'—':>8}")
    for c in sorted(cards, key=lambda c: (c["carry"], c["split"])):
        mark = " ✗" if c["eliminated"] else ("  ★" if chosen and c["label"] == chosen["label"] else "")
        print(f"  {c['label'] + mark:<26}{c['dominance_median']:>11.4f}"
              f"{c['dominance_paired_wins']:>5}/5{c['counters_mean']:>10.2f}"
              f"{c['balanced_rate'] * len(anchor['per_seed']):>3.0f}/{len(anchor['per_seed']):<2}"
              f"{c['drift_median']:>9.4f}{c['validator_structural_median']:>7.1f}"
              f"{c['validator_behavioral_median']:>5.1f}{c['rank_agreement_median']:>+8.3f}"
              f"{c['n_identity_beaten']:>6}/4")
    print("  " + "─" * 94)
    print("  'venc.' = sementes em que o braço bate a âncora em dominance (pareado).")
    print("  'ident.' = quantas das 4 réguas de identidade a mediana do braço bate.")
    print("  ✗ = eliminado no passo 1 (custo em equilíbrio).   ★ = escolhido.")
    print()
    for c in cards:
        if c["eliminated"]:
            print(f"    ✗ {c['label']}: {'; '.join(c['elimination_reasons'])}")
    print()
    print(line)
    print("  TRILHA DA DECISÃO")
    print(line)
    for step in trail:
        print(f"  • {step}")
    print()
    print(f"  CONFIGURAÇÃO ESCOLHIDA: split {chosen['split']:g}, carry {chosen['carry']}")
    print(f"  Identidade batida: {', '.join(chosen['identity_beaten']) or '(nenhuma)'}")
    if chosen.get("adoption_deferred"):
        print()
        print("  ADOÇÃO ADIADA para a bateria: nenhum braço passou no filtro de equilíbrio")
        print("  em orçamento reduzido — onde a âncora ainda não degradou (τ 0,46 a 60")
        print("  gerações contra 0,28 a 150) e o híbrido tem menos a consertar. Quem")
        print("  decide é o teste pareado com n = 20 no orçamento inteiro.")
    print(line)


def main() -> None:
    anchor, arms = _load()
    cards = [evaluate_arm(arm, anchor) for arm in arms]
    chosen, trail = choose(cards)
    _print(anchor, cards, chosen, trail)

    CHOICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHOICE_PATH.open("w", encoding="utf-8") as fh:
        json.dump({
            "provenance": stamp(tool=__spec__.name),
            "anchor": {
                "seeds": anchor["seeds"], "pop_size": anchor["pop_size"],
                "n_generations": anchor["n_generations"],
                "sims_per_matchup": anchor["sims_per_matchup"],
                "dominance_median": _median(anchor, "dominance_penalty"),
                "counters_mean": _mean(anchor, "n_hard_counters"),
                "drift_median": _median(anchor, "drift_penalty"),
                "validator_structural_median": _median(anchor, "validator_structural"),
                "validator_behavioral_median": _median(anchor, "validator_behavioral"),
                "rank_agreement_median": _median(anchor, "rank_agreement"),
            },
            "arms": cards,
            "decision_trail": trail,
            "chosen": chosen,
            # A ressalva viaja no artefato, não só no docstring: quem citar a escolha
            # precisa citar o que ela pressupõe.
            "caveat": (
                "Ordenação medida em orçamento reduzido (pop 120 × 60). O mecanismo do "
                "híbrido depende de a fase de Pareto ter gerações para a fronteira se "
                "abrir — a 60 gerações um split 0,25 dá 15 gerações de NSGA-II contra 75 "
                "no orçamento da bateria —, então a ordenação ENTRE SPLITS pode não "
                "transferir. O desempate pela configuração mais simples é a proteção "
                "contra isso. Quem avalia a configuração escolhida é a bateria."
            ),
        }, fh, indent=2, ensure_ascii=False)
    print(f"\n  → {CHOICE_PATH.relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
