"""
Smoke test do módulo de combate.
Rode com: python test_combat.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from archetypes import ARCHETYPES, ArchetypeID
from character import Character
from combat import simulate_combat, CombatResult


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# ── 1. Combate simples (canônico) ────────────────────────────────────────────

separator("Combate canônico: Grappler vs Rushdown")
grappler = Character.from_archetype(ARCHETYPES[ArchetypeID.GRAPPLER])
rushdown = Character.from_archetype(ARCHETYPES[ArchetypeID.RUSHDOWN])
result = simulate_combat(grappler, rushdown)
print(f"  Vencedor: {'Grappler' if result.winner == 0 else 'Rushdown'}")
print(f"  KO: {result.ko} | Ticks: {result.ticks}")
print(f"  HP final: Grappler={result.hp_remaining[0]:.1f} | Rushdown={result.hp_remaining[1]:.1f}")
assert result.winner in (0, 1)
assert 1 <= result.ticks <= 500
assert isinstance(result.ko, bool)
print("  ✓ Estrutura do resultado válida")


# ── 2. Todos os matchups canônicos ───────────────────────────────────────────

separator("Round-robin canônico (10 matchups × 10 partidas cada)")
archetype_ids = list(ARCHETYPES.keys())
from itertools import combinations

for aid_a, aid_b in combinations(archetype_ids, 2):
    char_a = Character.from_archetype(ARCHETYPES[aid_a])
    char_b = Character.from_archetype(ARCHETYPES[aid_b])

    wins_a = 0
    n = 10
    for _ in range(n):
        r = simulate_combat(char_a, char_b)
        if r.winner == 0:
            wins_a += 1

    name_a = ARCHETYPES[aid_a].name
    name_b = ARCHETYPES[aid_b].name
    wr_a = wins_a / n
    print(f"  {name_a:15s} vs {name_b:15s} → {name_a} WR={wr_a:.1%}")

print("  ✓ Todos os matchups executaram sem erro")


# ── 3. Verificação de HP ─────────────────────────────────────────────────────

separator("Verificação de HP final")
zoner  = Character.from_archetype(ARCHETYPES[ArchetypeID.ZONER])
turtle = Character.from_archetype(ARCHETYPES[ArchetypeID.TURTLE])
for _ in range(5):
    r = simulate_combat(zoner, turtle)
    assert r.hp_remaining[0] >= 0, "HP negativo detectado (Zoner)"
    assert r.hp_remaining[1] >= 0, "HP negativo detectado (Turtle)"
    assert r.hp_remaining[r.winner] > 0 or not r.ko, "Vencedor com HP 0 em combate não-KO"
print("  ✓ HP sempre >= 0 e consistente com resultado")


# ── 4. Personagens aleatórios ────────────────────────────────────────────────

separator("Personagens aleatórios (stress: 50 combates)")
import random
random.seed(42)
for _ in range(50):
    a = Character.random(ARCHETYPES[ArchetypeID.COMBO_MASTER])
    b = Character.random(ARCHETYPES[ArchetypeID.TURTLE])
    r = simulate_combat(a, b)
    assert r.winner in (0, 1)
    assert r.hp_remaining[0] >= 0
    assert r.hp_remaining[1] >= 0
print("  ✓ 50 combates com genes aleatórios sem crash")


separator("Todos os testes de combate passaram ✓")
