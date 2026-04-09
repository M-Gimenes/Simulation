"""
Smoke test da estrutura base.
Rode com: python test_base.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from archetypes import ARCHETYPES, ARCHETYPE_ORDER, ArchetypeID
from character import Character, Attr, WIdx
from individual import Individual


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
print(f"  HP={g.hp} | Damage={g.damage} | Speed={g.speed} | Defense={g.defense}")
print(f"  Weights: atk={g.w_attack} | adv={g.w_advance} | agg={g.w_aggressiveness}")
print(f"  Genes totais: {len(g.genes())} ({'OK' if len(g.genes()) == 14 else 'ERRO'})")


# ── 3. Personagem aleatório ───────────────────────────────────────────────────

separator("Personagem aleatório (Rushdown)")
r = Character.random(ARCHETYPES[ArchetypeID.RUSHDOWN])
print(f"  {r}")
from config import ATTRIBUTE_BOUNDS, WEIGHT_BOUNDS
assert all(lo <= v <= hi for v, (lo, hi) in zip(r.attributes, ATTRIBUTE_BOUNDS)), "Atributo fora do bound!"
assert all(lo <= v <= hi for v, (lo, hi) in zip(r.weights,    WEIGHT_BOUNDS)),    "Peso fora do bound!"
print("  ✓ Todos os genes dentro dos bounds")


# ── 4. Clone e load_genes ─────────────────────────────────────────────────────

separator("Clone e carga de genes")
clone = r.clone()
genes = clone.genes()
clone.attributes[Attr.HP] = 9999         # modifica o clone
clone.clip()                              # deve voltar para o bound máximo (500)
assert clone.hp == 500.0, f"Clip falhou: {clone.hp}"
assert r.hp != 999, "Clone afetou o original!"
print("  ✓ Clone isolado + clip funcionando")


# ── 5. Indivíduo canônico ─────────────────────────────────────────────────────

separator("Indivíduo canônico (5 personagens)")
ind = Individual.from_canonical()
assert len(ind) == 5
total_genes = sum(len(c.genes()) for c in ind.characters)
assert total_genes == 70, f"Esperado 70 genes, got {total_genes}"
print(f"  Personagens: {[c.name for c in ind.characters]}")
print(f"  Total de genes: {total_genes} ({'OK' if total_genes == 70 else 'ERRO'})")


# ── 6. Indivíduo aleatório ───────────────────────────────────────────────────

separator("Indivíduo aleatório")
rand_ind = Individual.random()
rand_ind.clip()
print(f"  {rand_ind}")
print(f"  {rand_ind.summary()}")


# ── 7. Acesso por arquétipo ───────────────────────────────────────────────────

separator("Acesso por ArchetypeID")
turtle = ind.get(ArchetypeID.TURTLE)
print(f"  Turtle HP={turtle.hp} | Defense={turtle.defense} (esperado HP=500, def=0.9)")
assert turtle.hp       == 500.0
assert turtle.defense  == 0.90
print("  ✓ Acesso por ID correto")


separator("Todos os testes passaram ✓")
