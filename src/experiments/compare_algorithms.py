"""compare_algorithms.py — comparação estatística entre dois conjuntos de execuções.

O `multi_run` agrega média ± desvio de cada configuração, mas média ± desvio não decide
se a diferença entre duas é real ou ruído de amostragem. Dois usos, o mesmo aparato:

  • **AG escalar × NSGA-II** (default) — a comparação entre algoritmos;
  • **AG escalar × controle** (`--control`) — a bateria contra um braço que difere dela
    num único fator de desenho, com a mesma amostra e o mesmo orçamento: `λ_drift = 0`
    (quanto da identidade o termo de drift segura) ou sem a semente canônica (quanto da
    diferença entre os algoritmos é só inicialização).

Como recomendado para comparação de algoritmos estocásticos (Derrac et al. 2011; Arcuri
& Briand 2011), sobre as amostras já gravadas:

  • **Mann-Whitney U** bicaudal — teste não-paramétrico para duas amostras
    independentes (não assume normalidade; as amostras são pequenas e limitadas
    por baixo em 0). Com `method="auto"` o SciPy usa a aproximação assintótica com
    correção de empates nesses tamanhos de amostra — conservadora (p maior que o
    exato), e a única válida para as métricas inteiras, que empatam muito;
  • **Â₁₂ de Vargha-Delaney** — tamanho de efeito: probabilidade de uma execução da
    primeira configuração produzir valor maior que uma da segunda (0.5 = sem efeito);
  • **correção de Holm-Bonferroni** sobre a família de métricas testadas — sem
    ela, testar k métricas a α=0.05 infla a chance de um falso positivo. A
    família exclui métricas **degeneradas** (amostra conjunta sem variação): elas
    não são teste, e deixá-las dentro encareceria as demais de graça.

A família é a mesma nos dois usos — equilíbrio e identidade, as duas metades da pergunta
de pesquisa —, então nenhuma comparação escolhe as métricas depois de ver os dados.

Não roda nada: lê os artefatos do `multi_run`. Se algum deles não descreve o sistema
atual (um controle pode divergir só pelo override que declara), ou se eles não
compartilham sementes, semente de validação, sims/matchup e orçamento, o tool aborta.

O NSGA-II entra pelo representante registrado no artefato (`scalar_optimum` na bateria,
o comparável do escalar). Como o `multi_run` grava os cinco representantes de cada
semente, já reavaliados, `--nsga2-representative` refaz a comparação contra outro ponto
e grava num arquivo à parte, sem sobrescrever a da bateria. E, descritivamente, a
**relação de Pareto por semente**: o ponto do AG contra a fronteira inteira do NSGA-II da
mesma semente — que não depende de escolher representante nenhum.

Uso:
    py -m src.experiments.multi_run --algorithm both   # gera os artefatos
    py -m src.experiments.compare_algorithms           # AG × NSGA-II
    py -m src.experiments.compare_algorithms --nsga2-representative best_dominance
    py -m src.experiments.compare_algorithms --control results/controls/multi_run_ga_drift0_dom1.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

from scipy.stats import mannwhitneyu, wilcoxon

from src.engine.config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
)
from src.engine.paths import (
    CONTROLS_DIR,
    MULTI_RUN_COMPARISON_PATH,
    MULTI_RUN_GA_PATH,
    MULTI_RUN_NSGA2_PATH,
    PROJECT_ROOT,
)
from src.engine.provenance import refuse_if_stale, stamp

ALPHA = 0.05

# (chave no registro por semente, rótulo, direção — "lower" ou "higher" é melhor)
METRICS: List[Tuple[str, str, str]] = [
    ("dominance_penalty",    "dominance_penalty",              "lower"),
    ("n_hard_counters",      "hard-counters por execução",     "lower"),
    ("n_chars_balanced",     "bonecos em banda por execução",  "higher"),
    ("drift_penalty",        "drift_penalty",                  "lower"),
    ("validator_structural", "validador estrutural (L1+L2)",   "higher"),
    ("validator_behavioral", "validador comportamental (L3)",  "higher"),
    ("rank_agreement",       "concordância de ranking (τ)",    "higher"),
]

# Os campos que tornam dois artefatos comparáveis: mesma amostra e mesmo orçamento.
_PAIRED_FIELDS = ("seeds", "validation_seed", "sims_per_matchup", "pop_size", "n_generations")


def _load(path: Path, allow_experiment_arm: bool = False) -> dict:
    """Lê um artefato do `multi_run` e recusa se ele não descreve o sistema atual.

    A comparação grava o carimbo da configuração VIGENTE, então aceitar entrada de outra
    configuração produziria um resultado que se declara atual sobre números de outro
    sistema. E como os dois artefatos vêm de invocações separadas — na bateria, horas de
    NSGA-II e horas de AG —, exigir que os dois sejam atuais é também o que garante que
    são comparáveis entre si: uma mudança de código entre as duas execuções reprova uma
    delas aqui. Um controle diverge de propósito, e só pelo override que declara."""
    if not path.exists():
        raise FileNotFoundError(
            f"'{path.relative_to(PROJECT_ROOT)}' não encontrado — "
            f"rode o `multi_run` correspondente primeiro."
        )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    refuse_if_stale(data.get("provenance"), f"{path.parent.name}/{path.name}",
                    allow_experiment_arm=allow_experiment_arm)
    return data


def with_representative(nsga2: dict, name: str) -> dict:
    """O artefato do NSGA-II visto por outro representante: cada semente contribui o
    registro daquele ponto em vez do de topo. Não re-roda nada — o `multi_run` grava os
    cinco já reavaliados sob a mesma semente de validação."""
    if name == nsga2["nsga2_representative"]:
        return nsga2
    first = nsga2["per_seed"][0]
    if "representatives" not in first:
        raise ValueError(
            f"O multi_run do NSGA-II grava só o representante "
            f"'{nsga2['nsga2_representative']}' — foi gerado antes de o multi_run "
            f"guardar os cinco. Rode `py -m src.experiments.multi_run --algorithm nsga2` de novo."
        )
    if name not in first["representatives"]:
        raise ValueError(
            f"Representante '{name}' desconhecido — disponíveis: "
            f"{', '.join(first['representatives'])}."
        )
    per_seed = [{"seed": record["seed"], **record["representatives"][name]}
                for record in nsga2["per_seed"]]
    return {**nsga2, "per_seed": per_seed, "nsga2_representative": name}


def _check_comparable(a: dict, b: dict) -> None:
    for field in _PAIRED_FIELDS:
        if a[field] != b[field]:
            raise ValueError(
                f"Os dois multi_run divergem em '{field}' "
                f"({a[field]} vs {b[field]}) — não são comparáveis. "
                f"Regenere ambos com os mesmos parâmetros."
            )
    for run in (a, b):
        missing = [key for key, _, _ in METRICS if key not in run["per_seed"][0]]
        if missing:
            raise ValueError(
                f"O multi_run de '{run['algorithm']}' não traz {', '.join(missing)} — "
                f"foi gerado por uma versão anterior do multi_run. Rode de novo."
            )


def _samples(run: dict, key: str) -> List[float]:
    return [record[key] for record in run["per_seed"]]


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _a12(a: List[float], b: List[float]) -> float:
    """Vargha-Delaney Â₁₂ = P(a > b) + 0.5·P(a = b)."""
    greater = sum(x > y for x in a for y in b)
    equal = sum(x == y for x in a for y in b)
    return (greater + 0.5 * equal) / (len(a) * len(b))


def _effect_magnitude(a12: float) -> str:
    """Limiares de Vargha & Delaney (2000), em |Â₁₂ − 0.5|."""
    delta = abs(a12 - 0.5)
    if delta < 0.06:
        return "desprezível"
    if delta < 0.14:
        return "pequeno"
    if delta < 0.21:
        return "médio"
    return "grande"


def _is_degenerate(sample_a: List[float], sample_b: List[float]) -> bool:
    """Amostra **conjunta** sem variação alguma — as 2·n execuções deram o mesmo
    valor. Mann-Whitney é indefinido aí (devolve `nan`, porque a correção de
    empates zera o denominador): não existe teste a corrigir, e manter a métrica
    na família de Holm encareceria as outras sem contrapartida.

    O critério é a amostra conjunta, não cada uma: `a` constante em 5 contra
    `b` constante em 3 é a diferença mais forte possível, não degenerescência.
    Sendo objetivo e decidido pelos dados, vale como regra declarada antes do
    teste — não é escolha de família feita depois de ver os p-valores."""
    return len(set(sample_a + sample_b)) == 1


def _holm(p_values: List[float]) -> List[float]:
    """p ajustado por Holm-Bonferroni, preservando a ordem de entrada.

    Exige p-valores válidos: um `nan` aqui corrompe a ordenação **em silêncio**,
    porque toda comparação com `nan` é falsa e a posição dele passa a depender do
    algoritmo de ordenação. Métricas degeneradas têm de ser filtradas antes."""
    if any(p != p for p in p_values):
        raise ValueError(
            "_holm recebeu `nan` — filtre as métricas degeneradas com "
            "`_is_degenerate` antes de montar a família."
        )
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    running_max = 0.0
    for rank, idx in enumerate(order):
        value = min(1.0, (n - rank) * p_values[idx])
        running_max = max(running_max, value)
        adjusted[idx] = running_max
    return adjusted


def compare(a: dict, b: dict, label_a: str, label_b: str) -> dict:
    """Wilcoxon pareado + Â₁₂ + Holm de `a` contra `b` sobre a família `METRICS`,
    com o Mann-Whitney não-pareado reportado ao lado.

    **Por que o pareado é o teste do desenho.** `_check_comparable` exige que os dois
    braços rodem as MESMAS sementes, e a semente controla tudo que é aleatório nos dois
    lados: `random.seed(seed)` dá a mesma população inicial e a mesma sequência de
    operadores, e `generation_seed(seed, g)` dá o mesmo stream de avaliação na geração
    `g`. Execução `i` de `a` e execução `i` de `b` são o mesmo bloco experimental, não
    duas amostras independentes — o que Mann-Whitney assume. Ignorar o bloco é
    conservador (joga fora o poder que o CRN pagou), não inválido.

    **E por que os dois aparecem.** Trocar de teste depois de ver resultado é risco de
    p-hacking, e a troca nasceu de uma auditoria do desenho, não de um p-valor. A defesa
    é não esconder nada: a família de Holm é montada sobre o pareado, o não-pareado vem
    na mesma tabela, e quem lê confere que as conclusões não dependem da escolha."""
    _check_comparable(a, b)

    tests: List[dict] = []
    for key, label, direction in METRICS:
        sample_a, sample_b = _samples(a, key), _samples(b, key)
        degenerate = _is_degenerate(sample_a, sample_b)
        if degenerate:
            statistic = p_value = p_unpaired = None
        else:
            # `zero_method="wilcox"` descarta os pares sem diferença: são os empates,
            # que não informam direção nenhuma.
            diffs = [x - y for x, y in zip(sample_a, sample_b)]
            if all(d == 0 for d in diffs):
                # Amostras diferentes par a par não podem cair aqui — só se `a` e `b`
                # derem exatamente o mesmo valor em toda semente, o que `_is_degenerate`
                # não pega quando os dois são constantes em valores distintos.
                statistic, p_value = None, 1.0
            else:
                statistic, p_value = wilcoxon(
                    sample_a, sample_b, alternative="two-sided", zero_method="wilcox"
                )
            _, p_unpaired = mannwhitneyu(
                sample_a, sample_b, alternative="two-sided", method="auto"
            )
        median_a, median_b = _median(sample_a), _median(sample_b)

        if median_a == median_b:
            better = "empate"
        elif (median_a < median_b) == (direction == "lower"):
            better = "a"
        else:
            better = "b"

        tests.append({
            "metric": key,
            "label": label,
            "better_is": direction,
            "median_a": median_a,
            "median_b": median_b,
            "w_statistic": None if (degenerate or statistic is None) else float(statistic),
            "p_value": None if degenerate else float(p_value),
            "p_value_unpaired": None if degenerate else float(p_unpaired),
            "a12_a_vs_b": _a12(sample_a, sample_b),
            "better": better,
            "degenerate": degenerate,
        })

    family = [t for t in tests if not t["degenerate"]]
    for test, p_adjusted in zip(family, _holm([t["p_value"] for t in family])):
        test["p_holm"] = p_adjusted
        test["significant"] = p_adjusted < ALPHA
    for test in tests:
        test["effect_magnitude"] = _effect_magnitude(test["a12_a_vs_b"])
        if test["degenerate"]:
            test["p_holm"] = None
            test["significant"] = False

    return {
        "a": label_a,
        "b": label_b,
        "test": "Wilcoxon signed-rank pareado (bicaudal)",
        "test_secondary": "Mann-Whitney U (bicaudal, não-pareado) — reportado como robustez",
        "effect_size": "Vargha-Delaney A12 (a vs b)",
        "correction": "Holm-Bonferroni",
        "alpha": ALPHA,
        "n_seeds": len(a["seeds"]),
        "seeds": a["seeds"],
        "validation_seed": a["validation_seed"],
        "sims_per_matchup": a["sims_per_matchup"],
        "family_size": len(family),
        "excluded_from_family": [t["metric"] for t in tests if t["degenerate"]],
        "metrics": tests,
        "dominance_decomposition": _decomposition(a, b),
    }


def _decomposition(a: dict, b: dict) -> dict:
    """Medianas dos três termos do `dominance_penalty` lado a lado. É DESCRITIVO,
    não entra na bateria de testes: somar métricas ao Mann-Whitney infla a correção
    de Holm sobre as que já estão lá. Serve para ler de ONDE vem a diferença no
    composto — perder no termo primário (peso 1.0) e perder num secundário (peso
    0.5) são leituras opostas do mesmo número total."""
    return {
        term: {
            "median_a": _median([r["dominance_terms"][term] for r in a["per_seed"]]),
            "median_b": _median([r["dominance_terms"][term] for r in b["per_seed"]]),
            "weight":   weight,
        }
        for term, weight in (("global_term", DOMINANCE_GLOBAL_WEIGHT),
                             ("cap_term", DOMINANCE_CAP_WEIGHT),
                             ("decis_term", DOMINANCE_DECIS_WEIGHT))
    }


# ─────────────────────────────────────────────────────────────────────────────
# Relação de Pareto por semente (AG × NSGA-II)
# ─────────────────────────────────────────────────────────────────────────────


def _dominates(p: Sequence[float], q: Sequence[float]) -> bool:
    return all(x <= y for x, y in zip(p, q)) and any(x < y for x, y in zip(p, q))


def pareto_relation(ga: dict, nsga2: dict) -> dict:
    """O ponto do AG escalar contra a FRONTEIRA inteira do NSGA-II da mesma semente.

    Comparar o AG com UM representante mede, em parte, a escolha do representante.
    Contra a fronteira não há escolha: ou algum ponto dela domina o do AG (o NSGA-II
    achou algo melhor nos dois objetivos), ou o do AG domina algum ponto dela (o AG
    achou algo melhor), ou nenhum dos dois — os dois alcançam partes diferentes do
    trade-off. As três leituras são exclusivas: um ponto dominado por um membro da
    fronteira e dominando outro faria o primeiro dominar o segundo, e os membros da
    fronteira são mutuamente não-dominados.

    Os dois lados estão no MESMO stream — o da última geração da mesma semente, em que
    o AG mediu seu melhor e o NSGA-II a fronteira final —, então a relação não carrega
    ruído de stream. É descritiva: fica fora da família de Holm."""
    fronts = {record["seed"]: record["front_objectives"] for record in nsga2["per_seed"]}
    per_seed = []
    for record in ga["per_seed"]:
        point, front = record["in_loop_objectives"], fronts[record["seed"]]
        dominated = any(_dominates(member, point) for member in front)
        dominates = sum(_dominates(point, member) for member in front)
        per_seed.append({
            "seed": record["seed"],
            "relation": ("dominado" if dominated
                         else "domina" if dominates else "não-dominado"),
            "front_points_dominated": dominates,
            "front_size": len(front),
        })
    return {
        "per_seed": per_seed,
        "counts": {relation: sum(r["relation"] == relation for r in per_seed)
                   for relation in ("domina", "não-dominado", "dominado")},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Relatório
# ─────────────────────────────────────────────────────────────────────────────


def print_report(result: dict) -> None:
    n = result["n_seeds"]
    a, b = result["a"], result["b"]
    print("=" * 84)
    print(f"  {a} vs {b} — {n} execuções cada (seeds "
          f"{result['seeds'][0]}..{result['seeds'][-1]}), reavaliadas sob a seed "
          f"{result['validation_seed']} com {result['sims_per_matchup']} sims/matchup")
    print(f"  {result['test']} + {result['effect_size']} + {result['correction']} "
          f"(alfa={result['alpha']}, família de {result['family_size']})")
    print(f"  ao lado, como robustez: {result['test_secondary']}")
    print("=" * 84)
    print(f"  {'métrica':<34}{'mediana ' + a[:10]:>18}{'mediana ' + b[:10]:>18}"
          f"{'p (Holm)':>9}{'A12':>6}{'p n-pareado':>13}")
    print("  " + "-" * 95)
    for test in result["metrics"]:
        p_holm = "—" if test["degenerate"] else f"{test['p_holm']:.4f}"
        p_unp  = "—" if test["degenerate"] else f"{test['p_value_unpaired']:.4f}"
        print(f"  {test['label']:<34}{test['median_a']:>18.4f}{test['median_b']:>18.4f}"
              f"{p_holm:>9}{test['a12_a_vs_b']:>6.2f}{p_unp:>13}")
    print("  " + "-" * 95)
    print("")
    for test in result["metrics"]:
        if test["degenerate"]:
            verdict = ("amostra conjunta constante — nenhum teste é definido aí; "
                       "fora da família")
        elif test["significant"]:
            winner = a if test["better"] == "a" else b
            verdict = (f"diferença significativa — {winner} melhor "
                       f"(efeito {test['effect_magnitude']})")
        else:
            verdict = (f"sem diferença significativa (p_Holm="
                       f"{test['p_holm']:.3f}, efeito {test['effect_magnitude']})")
        print(f"    {test['label']:<34} {verdict}")
    print("")
    print(f"    A12 = P(uma execução de {a} dar valor MAIOR que uma de {b}); 0.5 = sem efeito.")
    print("    `p (Holm)` corrige o WILCOXON PAREADO — o teste do desenho: os dois braços")
    print("    rodam as mesmas sementes, e a semente fixa população inicial, operadores e")
    print("    stream de avaliação nos dois. `p n-pareado` é o Mann-Whitney BRUTO (sem")
    print("    Holm), só para conferir que a conclusão não depende do teste escolhido.")
    excluded = result["excluded_from_family"]
    if excluded:
        plural = "s" if len(excluded) > 1 else ""
        print(f"    Fora da família de Holm (sem variação nas 2×{n} execuções, logo "
              f"sem teste a corrigir):")
        print(f"      {', '.join(excluded)} — segue{plural} acima "
              f"como descritiva{plural}.")
    print("")
    print("  Decomposição do dominance_penalty (descritiva — não entra na bateria "
          "de testes):")
    print(f"    {'termo':<14}{'peso':>6}{'mediana ' + a[:10]:>20}{'mediana ' + b[:10]:>20}  melhor")
    print("    " + "-" * 70)
    for term, d in result["dominance_decomposition"].items():
        better = (a if d["median_a"] < d["median_b"]
                  else b if d["median_b"] < d["median_a"] else "empate")
        print(f"    {term:<14}{d['weight']:>6.1f}{d['median_a']:>20.4f}"
              f"{d['median_b']:>20.4f}  {better}")
    print("    O termo primário é `global_term` — é ele que diz quem equilibra o "
          "roster melhor.")

    relation = result.get("pareto_relation")
    if relation is not None:
        counts = relation["counts"]
        print("")
        print("  Relação de Pareto por semente — ponto do AG contra a fronteira inteira do "
              "NSGA-II")
        print(f"    AG domina algum ponto da fronteira: {counts['domina']}/{n}   "
              f"mutuamente não-dominados: {counts['não-dominado']}/{n}   "
              f"AG dominado pela fronteira: {counts['dominado']}/{n}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(description="Mann-Whitney U + Â₁₂ + Holm sobre os "
                                                 "artefatos do multi_run: AG × NSGA-II, "
                                                 "ou AG × um controle")
    parser.add_argument("--nsga2-representative", metavar="REP", default=None,
                        help="Ponto da fronteira que representa o NSGA-II (default: o "
                             "registrado no artefato). Outro ponto grava em "
                             "comparison_ga_vs_nsga2_<REP>.json")
    parser.add_argument("--control", metavar="PATH", type=Path, default=None,
                        help="Compara a bateria do AG com este artefato de controle (de "
                             "results/controls/) em vez de com o NSGA-II")
    return parser.parse_args()


def _save(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(tool=__spec__.name), **result}, fh, indent=2, ensure_ascii=False)
    print("")
    print(f"  Salvo em {path.relative_to(PROJECT_ROOT)}")


def main() -> None:
    args = parse_args()
    ga = _load(MULTI_RUN_GA_PATH)

    if args.control is not None:
        control_path = args.control.resolve()
        control = _load(control_path, allow_experiment_arm=True)
        arm = control_path.stem.removeprefix("multi_run_")
        result = compare(ga, control, "AG", arm)
        print_report(result)
        _save(result, CONTROLS_DIR / f"comparison_ga_vs_{arm}.json")
        return

    nsga2 = _load(MULTI_RUN_NSGA2_PATH)
    recorded = nsga2["nsga2_representative"]
    representative = args.nsga2_representative or recorded
    result = compare(ga, with_representative(nsga2, representative),
                     "AG", f"NSGA-II ({representative})")
    result["nsga2_representative"] = representative
    result["pareto_relation"] = pareto_relation(ga, nsga2)
    print_report(result)

    path = MULTI_RUN_COMPARISON_PATH
    if representative != recorded:
        path = path.with_name(f"{path.stem}_{representative}{path.suffix}")
    _save(result, path)


if __name__ == "__main__":
    main()
