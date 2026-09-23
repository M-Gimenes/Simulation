"""
Smoke test da estrutura do torneio — o que separa ciclo de sorteio.

O contrato que este teste protege é o motivo de a métrica ter saído do `baselines`:
**aresta indecisa não conta**. Um roster cujos pares estão todos colados em 50% pode
marcar qualquer contagem de "arestas mantidas" por ruído, e foi exatamente o que
acontecia a 200 lutas por par.

Rode com: py -m src.tests.test_cycle_structure
"""

from itertools import combinations

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.fitness import FitnessDetail
from src.experiments.cycle_structure import (
    EDGES,
    _kept_rate,
    circular_triads,
    decided_threshold,
    edge_winrates,
    falsification_test,
    mirror_roster,
    summarize,
)


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def _detail(matchup_wr) -> FitnessDetail:
    return FitnessDetail(
        fitness=0.0,
        winrates=[0.5] * 5,
        matchup_winrates={
            pair: wr for pair, wr in zip(combinations(range(5), 2), matchup_wr)
        },
    )


# O ciclo canônico expresso como WR por par: 1.0 quando o lado A vence pelo `beats`.
CYCLE_WR = [
    1.0 if ARCHETYPE_ORDER[j] in ARCHETYPES[ARCHETYPE_ORDER[i]].beats else 0.0
    for i, j in combinations(range(5), 2)
]


# ── 1. As 10 arestas são as do `beats`, sem duplicata ───────────────────────

separator("EDGES: o ciclo autoral tem 10 arestas, uma por par")

assert len(EDGES) == 10, f"o ciclo deve ter 10 arestas, tem {len(EDGES)}"
pairs = {frozenset(edge) for edge in EDGES}
assert len(pairs) == 10, "cada par aparece uma vez só — senão uma aresta contaria dobrado"
print("  ✓ 10 arestas, uma por par dos 5 arquétipos (C(5,2) = 10)")


# ── 2. edge_winrates lê a WR do favorito canônico, não a do lado A ──────────

separator("edge_winrates: a WR é do favorito canônico do par")

assert edge_winrates(_detail(CYCLE_WR)) == [1.0] * 10, (
    "no ciclo perfeito toda aresta deve ler 1.0 — se lesse a WR do lado A, metade "
    "sairia 0.0"
)
assert edge_winrates(_detail([1.0 - wr for wr in CYCLE_WR])) == [0.0] * 10
print("  ✓ ciclo perfeito → 1.0 em todas; ciclo invertido → 0.0 em todas")


# ── 3. Tríades circulares — a escala 0 / 2.5 / 5 ────────────────────────────

separator("circular_triads: ordem estrita = 0, torneio regular = máximo")

# Ordem estrita 0>1>2>3>4: o de índice menor vence sempre.
assert circular_triads(_detail([1.0] * 10)) == 0.0, "torneio transitivo → 0 tríades"
print("  ✓ bicho-papão estrito (graus 4-3-2-1-0) → 0 tríades circulares")

# O ciclo canônico É um torneio regular — cada um vence 2 —, logo o MÁXIMO em 5 vértices.
assert circular_triads(_detail(CYCLE_WR)) == 5.0, "torneio regular → 5 tríades"
print("  ✓ o ciclo canônico é um torneio REGULAR → 5 tríades (máximo em 5 personagens)")
print("    (um roster estritamente transitivo não pode ter todos perto de 50%)")

assert circular_triads(_detail([1.0 - wr for wr in CYCLE_WR])) == 5.0
print("  ✓ o ciclo INVERTIDO ainda dá 5 tríades — a tríade mede a estrutura, cega ao")
print("    rótulo autoral; quem mede o rótulo são as arestas")


# ── 4. O contrato que motivou a extração: aresta indecisa não conta ─────────

separator("summarize: aresta dentro do limiar de ruído não é ciclo")

# Todas as arestas na direção autoral, mas por uma margem MENOR que o limiar.
narrow = summarize([0.502] * 10, triads=5.0, threshold=0.01)
assert narrow["kept"] == 10, "a contagem crua vê 10 — e é justamente o que engana"
assert narrow["decided"] == 0, "nenhuma passa do limiar"
assert narrow["kept_and_decided"] == 0, (
    "é o ponto do tool: 10 arestas 'mantidas' por 0,002 não são estrutura nenhuma"
)
print("  ✓ 10 arestas a 50,2% com limiar 1% → mantidas 10, decididas 0, válidas 0")

wide = summarize([0.6] * 10, triads=5.0, threshold=0.01)
assert (wide["kept"], wide["decided"], wide["kept_and_decided"]) == (10, 10, 10)
print("  ✓ as mesmas 10 a 60% → 10 válidas")

mixed = summarize([0.6] * 3 + [0.502] * 4 + [0.4] * 3, triads=5.0, threshold=0.01)
assert mixed["kept"] == 7 and mixed["decided"] == 6 and mixed["kept_and_decided"] == 3
print("  ✓ 3 largas a favor + 4 indecisas + 3 largas contra → 7 / 6 / 3")


# ── 5. O limiar cai com a raiz do número de lutas ───────────────────────────

separator("decided_threshold: 2σ binomial, cai com √n")

coarse = decided_threshold(streams=1, sims=200)
fine   = decided_threshold(streams=16, sims=1000)
assert abs(coarse - 2 * (0.25 / 200) ** 0.5) < 1e-12
assert fine < coarse, "mais lutas têm de baixar o limiar"
assert abs(coarse / fine - (16000 / 200) ** 0.5) < 1e-9, "a razão tem de ser √(n₂/n₁)"
print(f"  ✓ 200 lutas → {coarse:.4f};  16.000 lutas → {fine:.4f}  (razão √80)")
print("    A margem mediana de um roster equilibrado é ~0,03: indecisa a 200, decidida")
print("    a 16.000 — é a diferença entre medir ruído e medir o ciclo.")


# ── 6. A taxa, não a contagem, é o que compara dois grupos ──────────────────

separator("_kept_rate: grupos com decidibilidade diferente não têm contagem comparável")

assert _kept_rate(summarize([0.6] * 10, 5.0, 0.01)) == 1.0
assert _kept_rate(summarize([0.502] * 10, 5.0, 0.01)) is None, (
    "sem aresta decidida não existe taxa — devolver 0 afirmaria 'errou todas'"
)
half = summarize([0.6] * 5 + [0.4] * 5, 5.0, 0.01)
assert _kept_rate(half) == 0.5
print("  ✓ todas a favor → 1,0;  metade → 0,5;  nenhuma decidida → None")


# ── 7. O teste de falsificação ───────────────────────────────────────────────

separator("falsification_test: o ciclo perfeito é detectado, o acaso não")

perfect = falsification_test([summarize([0.6] * 10, 5.0, 0.01)],
                             [half, half])
assert perfect["kept_rate"] == 1.0
assert perfect["binomial_p"] < 0.01, "10 de 10 arestas decididas tem p = 1/512"
print(f"  ✓ ciclo perfeito: taxa 100%, binomial p = {perfect['binomial_p']:.4f}")

chance = falsification_test([half] * 4, [half, half])
assert chance["kept_rate"] == 0.5 and chance["binomial_p"] > 0.5
print(f"  ✓ direção ao acaso: taxa 50%, binomial p = {chance['binomial_p']:.2f}")

empty = falsification_test([summarize([0.502] * 10, 5.0, 0.01)], [half])
assert empty["binomial_p"] is None and empty["kept_rate"] is None, (
    "sem aresta decidida o tool não pode afirmar nada — nem a favor nem contra"
)
print("  ✓ sem aresta decidida devolve None em vez de fabricar um p-valor")


# ── 8. O espelho é o controle de ruído ──────────────────────────────────────

separator("mirror_roster: estrutura de torneio zero por construção")

roster = mirror_roster(ARCHETYPE_ORDER[0])
first = roster.characters[0]
assert all(c.attributes == first.attributes for c in roster.characters)
assert all(c.weights == first.weights for c in roster.characters)
assert [c.archetype.id for c in roster.characters] == ARCHETYPE_ORDER
print("  ✓ os 5 compartilham genes e preservam os rótulos — toda aresta é um espelho,")
print("    então o que a métrica marcar nele é o que ela marca sem estrutura nenhuma")


print(f"\n{'─'*60}")
print("  Todos os testes de cycle_structure passaram ✓")
print('─'*60)
