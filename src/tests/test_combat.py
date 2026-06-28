"""
Smoke test do módulo de combate.
Rode com: py -m src.tests.test_combat
"""

from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER, ArchetypeID
from src.engine.character import Character
from src.engine.combat import simulate_combat, simulate_combat_detailed, simulate_combat_traced, seed_combat, CombatResult
from src.engine.config import MAX_TICKS
from src.engine.individual import Individual


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
assert 1 <= result.ticks <= MAX_TICKS
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
    n = 100
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


# ── 5. Caminho traced + reprodutibilidade do seed ────────────────────────────

separator("Trace tick-a-tick e reprodutibilidade (seed_combat)")
trace = simulate_combat_traced(grappler, rushdown)
assert trace.pos.shape[1] == 2
assert trace.end_tick == trace.pos.shape[0]
assert trace.winner in (0, 1)
print(f"  ✓ CombatTrace válido (end_tick={trace.end_tick}, arrays alinhados)")

cm = Character.random(ARCHETYPES[ArchetypeID.COMBO_MASTER])
tu = Character.random(ARCHETYPES[ArchetypeID.TURTLE])
seed_combat(123); a = [simulate_combat(cm, tu).hp_remaining[0] for _ in range(8)]
seed_combat(123); b = [simulate_combat(cm, tu).hp_remaining[0] for _ in range(8)]
assert a == b, "seed_combat não reproduziu a sequência de lutas"
print("  ✓ seed_combat reproduz o RNG do Numba")


# ── 6. Rusher majoritariamente agressivo (intenção→execução) ────────────────

separator("Rusher vs Zoner: majoritariamente FRENTE (atk+adv)")
ind = Individual.from_canonical()
rush = next(c for c in ind.characters if c.archetype_id == ArchetypeID.RUSHDOWN)
zon  = next(c for c in ind.characters if c.archetype_id == ArchetypeID.ZONER)
_, log = simulate_combat_detailed(rush, zon)
atk = log.action_counts[0][0]; adv = log.action_counts[0][1]
total = sum(log.action_counts[0].values())
assert total > 0
assert (atk + adv) / total > 0.5, f"Rusher deveria ser majoritariamente FRENTE (atk+adv), got {(atk+adv)/total:.2f}"
print("  ✓ rusher majoritariamente FRENTE")


# ── 7. Invariante: sem stun-lock ─────────────────────────────────────────────

separator("Invariante: stun aplicado nunca >= cooldown_subticks do atacante")
import numpy as np
ind = Individual.from_canonical()
rush = next(c for c in ind.characters if c.archetype_id == ArchetypeID.RUSHDOWN)
zon  = next(c for c in ind.characters if c.archetype_id == ArchetypeID.ZONER)
tr = simulate_combat_traced(rush, zon)
max_cd_subticks = round(max(rush.attack_cooldown, zon.attack_cooldown) * 5)
assert int(tr.stun.max()) < max_cd_subticks, "stun não pode atingir o cooldown (lock)"
print("  ✓ sem stun-lock")


separator("Todos os testes de combate passaram ✓")
