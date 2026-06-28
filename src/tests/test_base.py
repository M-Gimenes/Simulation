"""
Smoke test da estrutura base.
Rode com: py -m src.tests.test_base
"""

from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER, ArchetypeID
from src.engine.character import Character, Attr, WIdx
from src.engine.individual import Individual


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# ── 1. Arquétipos ─────────────────────────────────────────────────────────────

separator("Arquétipos carregados")
for aid in ARCHETYPE_ORDER:
    arch = ARCHETYPES[aid]
    beats = [ARCHETYPES[b].name for b in arch.beats]
    print(f"  {arch.name:15s} → vence {beats}")


# ── 2. Personagem canônico ────────────────────────────────────────────────────

separator("Personagem canônico (Grappler)")
g = Character.from_archetype(ARCHETYPES[ArchetypeID.GRAPPLER])
print(f"  HP={g.hp} | Damage={g.damage} | Speed={g.speed} | Stun={g.stun}")
print(f"  Weights: ret={g.w_retreat} | def={g.w_defend} | agg={g.w_aggressiveness}")
print(f"  Genes totais: {len(g.genes())} ({'OK' if len(g.genes()) == 10 else 'ERRO'})")


# ── 3. Personagem aleatório ───────────────────────────────────────────────────

separator("Personagem aleatório (Rushdown)")
r = Character.random(ARCHETYPES[ArchetypeID.RUSHDOWN])
print(f"  {r}")
from src.engine.config import ATTRIBUTE_BOUNDS, WEIGHT_BOUNDS
assert all(lo <= v <= hi for v, (lo, hi) in zip(r.attributes, ATTRIBUTE_BOUNDS)), "Atributo fora do bound!"
assert all(lo <= v <= hi for v, (lo, hi) in zip(r.weights,    WEIGHT_BOUNDS)),    "Peso fora do bound!"
print("  ✓ Todos os genes dentro dos bounds")


# ── 4. Clone e load_genes ─────────────────────────────────────────────────────

separator("Clone e carga de genes")
clone = r.clone()
genes = clone.genes()
clone.attributes[Attr.HP] = 9999
clone.clip()
hp_max = ATTRIBUTE_BOUNDS[Attr.HP][1]
assert clone.hp == hp_max, f"Clip falhou: {clone.hp} (esperado {hp_max})"
assert r.hp != 999, "Clone afetou o original!"
print("  ✓ Clone isolado + clip funcionando")


# ── 5. Indivíduo canônico ─────────────────────────────────────────────────────

separator("Indivíduo canônico (5 personagens)")
ind = Individual.from_canonical()
assert len(ind) == 5
assert len(ind.characters[0].genes()) == 10, "char deve ter 10 genes"
total_genes = sum(len(c.genes()) for c in ind.characters)
assert total_genes == 50, f"Esperado 50 genes, got {total_genes}"
print(f"  Personagens: {[c.name for c in ind.characters]}")
print(f"  Total de genes: {total_genes} ({'OK' if total_genes == 50 else 'ERRO'})")


# ── 6. Indivíduo aleatório ───────────────────────────────────────────────────

separator("Indivíduo aleatório")
rand_ind = Individual.random()
rand_ind.clip()
print(f"  {rand_ind}")
print(f"  {rand_ind.summary()}")


# ── 7. Acesso por arquétipo ───────────────────────────────────────────────────

separator("Acesso por ArchetypeID")
turtle      = ind.get(ArchetypeID.TURTLE)
turtle_arch = ARCHETYPES[ArchetypeID.TURTLE]
print(f"  Turtle HP={turtle.hp} | Stun={turtle.stun}")
assert turtle.hp   == turtle_arch.initial_attributes.hp
assert turtle.stun == turtle_arch.initial_attributes.stun
print("  ✓ Acesso por ID correto")


separator("Todos os testes passaram ✓")
