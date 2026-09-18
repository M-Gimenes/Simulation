"""
Smoke test da comparação estatística — a família de Holm e o que fica fora dela.

O ponto do teste: uma métrica sem variação não é um teste, e mantê-la na família
encarece as outras sem contrapartida. O critério de exclusão tem de ser objetivo
(decidido pelos dados, não pelos p-valores) e o `nan` tem de ser recusado em vez
de corromper a ordenação em silêncio. E trocar o representante do NSGA-II tem de
trocar o registro de cada semente, sem tocar no resto do artefato.

Rode com: py -m src.tests.test_compare_algorithms
"""

from src.tools.compare_algorithms import (
    ALPHA,
    METRICS,
    _holm,
    _is_degenerate,
    with_representative,
)


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# ── 1. Degenerescência é da amostra CONJUNTA ────────────────────────────────

separator("_is_degenerate: sem variação nas 2·n execuções")

assert _is_degenerate([5] * 10, [5] * 10)
print("  ✓ mesmo valor nos dois algoritmos → degenerada")

assert not _is_degenerate([5] * 10, [3] * 10), (
    "cada amostra é constante, mas a diferença entre elas é a mais forte possível"
)
print("  ✓ constantes em valores DIFERENTES → não é degenerada")

assert not _is_degenerate([5, 5, 5, 4], [5] * 4)
print("  ✓ uma única execução fora do valor comum já sustenta o teste")


# ── 2. Holm recusa `nan` em vez de ordenar errado em silêncio ───────────────

separator("_holm: contrato com o `nan`")

try:
    _holm([0.02, 0.3, float("nan")])
except ValueError as exc:
    assert "_is_degenerate" in str(exc), "a mensagem tem de apontar o conserto"
    print("  ✓ levanta ValueError apontando o filtro a aplicar antes")
else:
    raise AssertionError("_holm aceitou `nan` — a ordenação sai por sorte")


# ── 3. A família menor é uniformemente mais poderosa ────────────────────────

separator("_holm: o custo de cada métrica na família")

p_raw = [0.3074894566186813, 0.025748080821108063, 0.9682596548128651]

# Holm sobre k métricas multiplica o menor p por k.
four = _holm(p_raw + [0.5])
three = _holm(p_raw)
two = _holm(p_raw[:2])

assert abs(three[1] - 3 * p_raw[1]) < 1e-12
print(f"  ✓ o menor p é multiplicado pelo tamanho da família (3 × {p_raw[1]:.4f})")

assert four[1] > three[1] > two[1], "cada métrica a mais encarece as demais"
print(f"  ✓ o mesmo p bruto sai {four[1]:.4f} (k=4) · {three[1]:.4f} (k=3) · "
      f"{two[1]:.4f} (k=2)")

# Monotonicidade: lidos na ordem crescente do p bruto, os ajustados não decrescem.
ordered = [three[i] for i in sorted(range(3), key=lambda i: p_raw[i])]
assert ordered == sorted(ordered), "Holm força ajustados não-decrescentes"
print("  ✓ preserva a monotonicidade exigida pelo procedimento")

assert all(v <= 1.0 for v in four + three + two)
print("  ✓ nenhum p ajustado passa de 1.0")


# ── 4. Filtrar não fabrica significância ────────────────────────────────────

separator("O filtro corrige a família, não compra o resultado")

# p bruto real do `drift_penalty` na bateria de 2026-09-16.
assert p_raw[1] < ALPHA, "significativo antes de qualquer correção"
assert all(holm[1] > ALPHA for holm in (four, three, two)), (
    "nem a família mínima leva o drift abaixo de alfa — o conserto é de "
    "correção, não de resultado"
)
print(f"  ✓ p bruto {p_raw[1]:.4f} < {ALPHA}, mas nenhuma família o torna "
      f"significativo")
print("    (o que resolve isso é poder amostral — mais sementes — não a família)")


# ── 5. A tabela de métricas segue coerente ──────────────────────────────────

separator("METRICS: contrato da tabela")

assert len(METRICS) == len({key for key, _, _ in METRICS}), "chaves duplicadas"
assert all(direction in ("lower", "higher") for _, _, direction in METRICS)
print(f"  ✓ {len(METRICS)} métricas, chaves únicas, direções válidas")


# ── 6. Trocar de representante troca o registro, não o artefato ────────────

separator("with_representative: o NSGA-II visto por outro ponto")

def _roster(dominance: float) -> dict:
    return {"dominance_penalty": dominance, "drift_penalty": 0.3,
            "n_hard_counters": 0, "n_chars_balanced": 5}

nsga2 = {
    "seeds": [42, 43],
    "nsga2_representative": "best_dominance",
    "per_seed": [
        {"seed": seed, **_roster(0.01), "front_size": 50,
         "representatives": {"best_dominance": _roster(0.01),
                             "scalar_optimum": _roster(0.02 + i)}}
        for i, seed in enumerate((42, 43))
    ],
}

assert with_representative(nsga2, "best_dominance") is nsga2
print("  ✓ o representante registrado devolve o próprio artefato")

view = with_representative(nsga2, "scalar_optimum")
assert view["nsga2_representative"] == "scalar_optimum"
assert [r["seed"] for r in view["per_seed"]] == [42, 43], "a semente acompanha o registro"
assert [r["dominance_penalty"] for r in view["per_seed"]] == [0.02, 1.02]
assert view["seeds"] == nsga2["seeds"]
assert nsga2["nsga2_representative"] == "best_dominance", "o original não é alterado"
print("  ✓ outro ponto: cada semente contribui o registro dele, com a semente")

try:
    with_representative(nsga2, "knee_point")
except ValueError as exc:
    assert "scalar_optimum" in str(exc), "a mensagem lista os disponíveis"
    print("  ✓ nome desconhecido é recusado listando os disponíveis")
else:
    raise AssertionError("aceitou um representante que o artefato não tem")

legacy = {**nsga2, "per_seed": [{k: v for k, v in r.items() if k != "representatives"}
                                for r in nsga2["per_seed"]]}
try:
    with_representative(legacy, "scalar_optimum")
except ValueError as exc:
    assert "multi_run" in str(exc), "a mensagem aponta o conserto"
    print("  ✓ artefato anterior aos cinco representantes é recusado, apontando o multi_run")
else:
    raise AssertionError("inventou um representante que o artefato não gravou")

separator("Todos os testes de compare_algorithms passaram ✓")
