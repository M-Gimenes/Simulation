"""
Smoke test dos modelos nulos — a matemática que sustenta "posição entre piso e teto".

Rode com: py -m src.tests.test_baselines
"""

from itertools import combinations

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.fitness import FitnessDetail
from src.experiments.baselines import (
    circular_triads,
    cycle_edges_kept,
    empirical_p,
    mirror_roster,
    position,
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


# ── 1. Espelho: identidade zero por construção ──────────────────────────────

separator("mirror_roster: cinco personagens idênticos")

for aid in ARCHETYPE_ORDER:
    roster = mirror_roster(aid)
    first = roster.characters[0]
    assert all(c.attributes == first.attributes for c in roster.characters)
    assert all(c.weights == first.weights for c in roster.characters)
    # Continua sendo um roster de 5 arquétipos — só os genes é que são iguais.
    assert [c.archetype.id for c in roster.characters] == ARCHETYPE_ORDER
print("  ✓ os 5 personagens compartilham genes, preservando os rótulos de arquétipo")

proto = mirror_roster(ARCHETYPE_ORDER[0]).characters[0]
canon = ARCHETYPES[ARCHETYPE_ORDER[0]]
assert proto.attributes == list(canon.initial_attributes)
print(f"  ✓ o protótipo é o canônico do arquétipo espelhado ({canon.name})")


# ── 2. Tríades circulares — a escala 0 / 2.5 / 5 ────────────────────────────

separator("circular_triads: ordem estrita = 0, torneio regular = máximo")

# Ordem estrita 0>1>2>3>4: o de índice menor vence sempre (wr do par (i,j) > 0.5).
transitive = _detail([1.0] * 10)
assert circular_triads(transitive) == 0.0, "torneio transitivo deve ter 0 tríades"
print("  ✓ bicho-papão estrito (graus 4-3-2-1-0) → 0 tríades circulares")

# Torneio regular: cada personagem vence exatamente 2. Usa o próprio ciclo canônico,
# que É um torneio regular — e por isso o MÁXIMO de tríades em 5 vértices.
regular_wr = []
for i, j in combinations(range(5), 2):
    id_a, id_b = ARCHETYPE_ORDER[i], ARCHETYPE_ORDER[j]
    regular_wr.append(1.0 if id_b in ARCHETYPES[id_a].beats else 0.0)
regular = _detail(regular_wr)
assert circular_triads(regular) == 5.0, (
    f"torneio regular deve ter 5 tríades, deu {circular_triads(regular)}"
)
print("  ✓ o ciclo canônico é um torneio REGULAR → 5 tríades (máximo em 5 personagens)")
print("    (um roster estritamente transitivo não pode ter todos perto de 50%)")

assert cycle_edges_kept(regular) == 10, "o próprio ciclo canônico deve dar 10/10"
print("  ✓ cycle_edges_kept reconhece o ciclo canônico perfeito (10/10)")

inverted = _detail([1.0 - wr for wr in regular_wr])
assert cycle_edges_kept(inverted) == 0, "o ciclo invertido deve dar 0/10"
assert circular_triads(inverted) == 5.0, "invertido ainda é regular → 5 tríades"
print("  ✓ ciclo INVERTIDO dá 0/10 arestas mas ainda 5 tríades — as tríades medem a")
print("    estrutura, independentes do rótulo; as arestas medem o rótulo autoral")


# ── 3. Posição entre piso e teto ────────────────────────────────────────────

separator("position: o valor cru não diz nada sem o piso")

# Métrica "maior é melhor": piso 8, teto 21. O valor 8 é ZERO, não 38%.
assert position(8, 8, 21) == 0.0
assert abs(position(12, 8, 21) - 4 / 13) < 1e-9
print("  ✓ valor 8 com piso 8 → 0% (e não os 38% que 8/21 sugere)")

# Métrica "menor é melhor": drift, piso 0.33 (espelho), teto 0.0.
assert abs(position(0.287, 0.326, 0.0) - (0.326 - 0.287) / 0.326) < 1e-9
print("  ✓ funciona com eixo invertido (drift: teto 0, piso ~0.33)")

assert position(5, 5, 5) is None
print("  ✓ piso == teto devolve None em vez de dividir por zero")


# ── 4. p-valor empírico ─────────────────────────────────────────────────────

separator("empirical_p: quantos rosters sem estrutura alcançam isso?")

nulls = [6, 7, 8, 8, 9, 12]
assert empirical_p(12, nulls, "maior") == 1 / 6, "só o nulo de 12 iguala"
assert empirical_p(13, nulls, "maior") == 0.0, "nenhum nulo alcança 13"
assert empirical_p(6, nulls, "maior") == 1.0, "todos os nulos alcançam 6"
print("  ✓ conta os nulos que igualam ou superam (eixo 'maior é melhor')")

assert empirical_p(0.30, [0.33, 0.40, 0.45], "menor") == 0.0
assert empirical_p(0.45, [0.33, 0.40, 0.45], "menor") == 1.0
print("  ✓ inverte corretamente no eixo 'menor é melhor'")

assert empirical_p(1.0, [], "maior") is None
print("  ✓ sem nulos devolve None — não inventa significância")

separator("Todos os testes de baselines passaram ✓")
