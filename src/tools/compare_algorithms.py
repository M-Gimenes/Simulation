"""compare_algorithms.py — comparação estatística entre AG escalar e NSGA-II.

O `multi_run` agrega média ± desvio de cada algoritmo, mas média ± desvio não
decide se a diferença entre eles é real ou ruído de amostragem. Como recomendado
para comparação de algoritmos estocásticos (Derrac et al. 2011; Arcuri & Briand
2011), este tool aplica sobre as amostras já gravadas:

  • **Mann-Whitney U** bicaudal — teste não-paramétrico para duas amostras
    independentes (não assume normalidade; as amostras são pequenas e limitadas
    por baixo em 0). Com `method="auto"` o SciPy usa a aproximação assintótica com
    correção de empates nesses tamanhos de amostra — conservadora (p maior que o
    exato), e a única válida para as métricas inteiras, que empatam muito;
  • **Â₁₂ de Vargha-Delaney** — tamanho de efeito: probabilidade de uma execução
    do AG produzir valor maior que uma execução do NSGA-II (0.5 = sem efeito);
  • **correção de Holm-Bonferroni** sobre a família de métricas testadas — sem
    ela, testar k métricas a α=0.05 infla a chance de um falso positivo. A
    família exclui métricas **degeneradas** (amostra conjunta sem variação): elas
    não são teste, e deixá-las dentro encareceria as demais de graça.

Não roda nada: lê os dois artefatos do `multi_run`. Se eles não compartilham
sementes, semente de validação e sims/matchup, a comparação não é pareada em
condição e o tool aborta.

Uso:
    py -m src.tools.multi_run --algorithm both   # gera os artefatos
    py -m src.tools.compare_algorithms           # compara
"""

from __future__ import annotations

import json
from typing import List, Tuple

from scipy.stats import mannwhitneyu

from src.engine.config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
)
from src.engine.paths import (
    MULTI_RUN_COMPARISON_PATH,
    MULTI_RUN_GA_PATH,
    MULTI_RUN_NSGA2_PATH,
    PROJECT_ROOT,
)

ALPHA = 0.05

# (chave no registro por semente, rótulo, direção — "lower" ou "higher" é melhor)
METRICS: List[Tuple[str, str, str]] = [
    ("dominance_penalty", "dominance_penalty", "lower"),
    ("drift_penalty",     "drift_penalty",     "lower"),
    ("n_hard_counters",   "hard-counters por execução", "lower"),
    ("n_chars_balanced",  "bonecos em banda por execução", "higher"),
]


def _load(path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"'{path.relative_to(PROJECT_ROOT)}' não encontrado — "
            f"rode `py -m src.tools.multi_run --algorithm both` primeiro."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _check_comparable(ga: dict, nsga2: dict) -> None:
    for field in ("seeds", "validation_seed", "sims_per_matchup"):
        if ga[field] != nsga2[field]:
            raise ValueError(
                f"Os dois multi_run divergem em '{field}' "
                f"({ga[field]} vs {nsga2[field]}) — não são comparáveis. "
                f"Regenere ambos com os mesmos parâmetros."
            )
    for label, run in (("ga", ga), ("nsga2", nsga2)):
        if "dominance_terms" not in run["per_seed"][0]:
            raise ValueError(
                f"O multi_run de '{label}' não traz `dominance_terms` — foi gerado "
                f"antes da decomposição do dominance. Rode "
                f"`py -m src.tools.multi_run --algorithm both` de novo."
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


def _is_degenerate(sample_ga: List[float], sample_nsga2: List[float]) -> bool:
    """Amostra **conjunta** sem variação alguma — as 2·n execuções deram o mesmo
    valor. Mann-Whitney é indefinido aí (devolve `nan`, porque a correção de
    empates zera o denominador): não existe teste a corrigir, e manter a métrica
    na família de Holm encareceria as outras sem contrapartida.

    O critério é a amostra conjunta, não cada uma: `ga` constante em 5 contra
    `nsga2` constante em 3 é a diferença mais forte possível, não degenerescência.
    Sendo objetivo e decidido pelos dados, vale como regra declarada antes do
    teste — não é escolha de família feita depois de ver os p-valores."""
    return len(set(sample_ga + sample_nsga2)) == 1


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


def compare(ga: dict, nsga2: dict) -> dict:
    _check_comparable(ga, nsga2)

    tests: List[dict] = []
    for key, label, direction in METRICS:
        sample_ga = _samples(ga, key)
        sample_nsga2 = _samples(nsga2, key)
        degenerate = _is_degenerate(sample_ga, sample_nsga2)
        if degenerate:
            statistic = p_value = None
        else:
            statistic, p_value = mannwhitneyu(
                sample_ga, sample_nsga2, alternative="two-sided", method="auto"
            )
        median_ga, median_nsga2 = _median(sample_ga), _median(sample_nsga2)

        if median_ga == median_nsga2:
            better = "empate"
        elif (median_ga < median_nsga2) == (direction == "lower"):
            better = "ga"
        else:
            better = "nsga2"

        tests.append({
            "metric": key,
            "label": label,
            "better_is": direction,
            "median_ga": median_ga,
            "median_nsga2": median_nsga2,
            "u_statistic": None if degenerate else float(statistic),
            "p_value": None if degenerate else float(p_value),
            "a12_ga_vs_nsga2": _a12(sample_ga, sample_nsga2),
            "better": better,
            "degenerate": degenerate,
        })

    family = [t for t in tests if not t["degenerate"]]
    for test, p_adjusted in zip(family, _holm([t["p_value"] for t in family])):
        test["p_holm"] = p_adjusted
        test["significant"] = p_adjusted < ALPHA
    for test in tests:
        test["effect_magnitude"] = _effect_magnitude(test["a12_ga_vs_nsga2"])
        if test["degenerate"]:
            test["p_holm"] = None
            test["significant"] = False

    return {
        "test": "Mann-Whitney U (bicaudal)",
        "effect_size": "Vargha-Delaney A12 (ga vs nsga2)",
        "correction": "Holm-Bonferroni",
        "alpha": ALPHA,
        "n_seeds": len(ga["seeds"]),
        "seeds": ga["seeds"],
        "validation_seed": ga["validation_seed"],
        "sims_per_matchup": ga["sims_per_matchup"],
        "nsga2_representative": nsga2.get("nsga2_representative"),
        "family_size": len(family),
        "excluded_from_family": [t["metric"] for t in tests if t["degenerate"]],
        "metrics": tests,
        "dominance_decomposition": _decomposition(ga, nsga2),
    }


def _decomposition(ga: dict, nsga2: dict) -> dict:
    """Medianas dos três termos do `dominance_penalty` lado a lado. É DESCRITIVO,
    não entra na bateria de testes: somar métricas ao Mann-Whitney infla a correção
    de Holm sobre as que já estão lá. Serve para ler de ONDE vem a diferença no
    composto — perder no termo primário (peso 1.0) e perder num secundário (peso
    0.5) são leituras opostas do mesmo número total."""
    return {
        term: {
            "median_ga":    _median([r["dominance_terms"][term] for r in ga["per_seed"]]),
            "median_nsga2": _median([r["dominance_terms"][term] for r in nsga2["per_seed"]]),
            "weight":       weight,
        }
        for term, weight in (("global_term", DOMINANCE_GLOBAL_WEIGHT),
                             ("cap_term", DOMINANCE_CAP_WEIGHT),
                             ("decis_term", DOMINANCE_DECIS_WEIGHT))
    }


def print_report(result: dict) -> None:
    n = result["n_seeds"]
    print("=" * 78)
    print(f"  AG escalar vs NSGA-II — {n} execuções por algoritmo (seeds "
          f"{result['seeds'][0]}..{result['seeds'][-1]}), reavaliadas sob a seed "
          f"{result['validation_seed']} com {result['sims_per_matchup']} sims/matchup")
    print(f"  NSGA-II representado por: {result['nsga2_representative']}")
    print(f"  {result['test']} + {result['effect_size']} + {result['correction']} "
          f"(alfa={result['alpha']}, família de {result['family_size']})")
    print("=" * 78)
    print(f"  {'métrica':<32}{'mediana AG':>12}{'mediana NSGA2':>15}"
          f"{'p (Holm)':>11}{'A12':>8}")
    print("  " + "-" * 76)
    for test in result["metrics"]:
        p_holm = "—" if test["degenerate"] else f"{test['p_holm']:.4f}"
        print(f"  {test['label']:<32}{test['median_ga']:>12.4f}"
              f"{test['median_nsga2']:>15.4f}{p_holm:>11}"
              f"{test['a12_ga_vs_nsga2']:>8.2f}")
    print("  " + "-" * 76)
    print("")
    for test in result["metrics"]:
        if test["degenerate"]:
            verdict = ("amostra conjunta constante — Mann-Whitney indefinido; "
                       "fora da família")
        elif test["significant"]:
            winner = "AG escalar" if test["better"] == "ga" else "NSGA-II"
            verdict = (f"diferença significativa — {winner} melhor "
                       f"(efeito {test['effect_magnitude']})")
        else:
            verdict = (f"sem diferença significativa (p_Holm="
                       f"{test['p_holm']:.3f}, efeito {test['effect_magnitude']})")
        print(f"    {test['label']:<32} {verdict}")
    print("")
    print("    A12 = P(uma execução do AG dar valor MAIOR que uma do NSGA-II); "
          "0.5 = sem efeito.")
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
    print(f"    {'termo':<14}{'peso':>6}{'mediana AG':>13}{'mediana NSGA2':>15}  melhor")
    print("    " + "-" * 60)
    for term, d in result["dominance_decomposition"].items():
        better = ("AG" if d["median_ga"] < d["median_nsga2"]
                  else "NSGA-II" if d["median_nsga2"] < d["median_ga"] else "empate")
        print(f"    {term:<14}{d['weight']:>6.1f}{d['median_ga']:>13.4f}"
              f"{d['median_nsga2']:>15.4f}  {better}")
    print("    O termo primário é `global_term` — é ele que diz quem equilibra o "
          "roster melhor.")


def main() -> None:
    ga = _load(MULTI_RUN_GA_PATH)
    nsga2 = _load(MULTI_RUN_NSGA2_PATH)
    result = compare(ga, nsga2)
    print_report(result)

    MULTI_RUN_COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MULTI_RUN_COMPARISON_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print("")
    print(f"  Salvo em {MULTI_RUN_COMPARISON_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
