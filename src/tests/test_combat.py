"""
Smoke test do módulo de combate.
Rode com: py -m src.tests.test_combat
"""

import numpy as np

from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER, ArchetypeID
from src.engine.character import Character
from src.engine.combat import Action, simulate_combat, simulate_combat_detailed, simulate_combat_traced, seed_combat
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
assert result.winner in (-1, 0, 1)
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
    assert r.winner in (-1, 0, 1)
    assert r.hp_remaining[0] >= 0
    assert r.hp_remaining[1] >= 0
print("  ✓ 50 combates com genes aleatórios sem crash")


# ── 5. Caminho traced + reprodutibilidade do seed ────────────────────────────

separator("Trace tick-a-tick e reprodutibilidade (seed_combat)")
trace = simulate_combat_traced(grappler, rushdown)
assert trace.pos.shape[1] == 2
assert trace.end_tick == trace.pos.shape[0]
assert trace.winner in (-1, 0, 1)
print(f"  ✓ CombatTrace válido (end_tick={trace.end_tick}, arrays alinhados)")

cm = Character.random(ARCHETYPES[ArchetypeID.COMBO_MASTER])
tu = Character.random(ARCHETYPES[ArchetypeID.TURTLE])
seed_combat(123); a = [simulate_combat(cm, tu).hp_remaining[0] for _ in range(8)]
seed_combat(123); b = [simulate_combat(cm, tu).hp_remaining[0] for _ in range(8)]
assert a == b, "seed_combat não reproduziu a sequência de lutas"
print("  ✓ seed_combat reproduz o RNG do Numba")


# ── 6. Rusher majoritariamente em avanço (intenção→postura) ─────────────────

separator("Rusher vs Zoner: postura majoritariamente ADVANCE")
ind = Individual.from_canonical()
rush = next(c for c in ind.characters if c.archetype_id == ArchetypeID.RUSHDOWN)
zon  = next(c for c in ind.characters if c.archetype_id == ArchetypeID.ZONER)
_, log = simulate_combat_detailed(rush, zon)
adv = log.stance_counts[0][int(Action.ADVANCE)]
total = sum(log.stance_counts[0].values())
assert total > 0
assert adv / total > 0.5, f"Rusher deveria avançar na maioria dos sub-ticks, got {adv/total:.2f}"
print("  ✓ rusher majoritariamente em avanço")


# ── 6b. Ataque é canal paralelo: recuar não impede bater ────────────────────

separator("Canal paralelo: um lutador que recua ainda ataca")
kiter = zon.clone()
kiter.weights = [1.0, 0.0, 0.0]      # só RECUAR
kiter.attributes[3] = 20.0            # range máximo
_, log_kite = simulate_combat_detailed(kiter, rush)
assert log_kite.stance_counts[0][int(Action.RETREAT)] > 0, "kiter deveria recuar"
assert log_kite.attacks[0] > 0, "kiter deveria atacar enquanto recua (canal paralelo)"
print("  ✓ recuar e atacar coexistem")


# ── 6c. GUARDA abre mão do golpe ────────────────────────────────────────────

separator("Invariante: nenhum ataque dispara na postura DEFEND")
mismatches = 0
for aid_a, aid_b in combinations(ARCHETYPE_ORDER, 2):
    ca = next(c for c in ind.characters if c.archetype_id == aid_a)
    cb = next(c for c in ind.characters if c.archetype_id == aid_b)
    seed_combat(7)
    tr = simulate_combat_traced(ca, cb)
    for i in (0, 1):
        defending = tr.stance[:, i] == int(Action.DEFEND)
        mismatches += int((defending & (tr.attacked[:, i] == 1)).sum())
assert mismatches == 0, f"{mismatches} ataques dispararam com a postura em DEFEND"
print("  ✓ guarda abre mão do golpe em todos os pares")


# ── 7. Invariante: sem stun-lock ─────────────────────────────────────────────

separator("Invariante: stun aplicado nunca >= cooldown_subticks do atacante")
ind = Individual.from_canonical()
rush = next(c for c in ind.characters if c.archetype_id == ArchetypeID.RUSHDOWN)
zon  = next(c for c in ind.characters if c.archetype_id == ArchetypeID.ZONER)
tr = simulate_combat_traced(rush, zon)
max_cd_subticks = max(rush.attack_cooldown, zon.attack_cooldown) * 5
assert float(tr.stun.max()) < max_cd_subticks, "stun não pode atingir o cooldown (lock)"
print("  ✓ sem stun-lock")


# ── 7b. Timers contínuos em média: cooldown e stun ─────────────────────────

separator("Timers: período médio = cooldown × TICK_SCALE; stun médio = o do gene")
# Os dois timers contam sub-ticks inteiros, mas vêm de genes contínuos. Com o resto
# acumulado (`combat._carry_round`) a MÉDIA é exata: o gene age sem degraus. Antes, o
# período era `round(5c) + 1` (6 sub-ticks com cooldown 1) e o stun `ceil(stun_t)`, o
# que dava ao stun de um atacante de cooldown 1 só 4 efeitos distintos em [0, 0.6].
from src.engine.config import TICK_SCALE


def _duel(cooldown: float, stun: float):
    """Atacante que sempre avança contra alvo imortal que também avança."""
    attacker = Character.from_archetype(ARCHETYPES[ArchetypeID.RUSHDOWN])
    target   = Character.from_archetype(ARCHETYPES[ArchetypeID.TURTLE])
    attacker.attributes = [10000.0, 15.0, cooldown, 20.0, 5.0, stun, 0.0, 0.0]
    attacker.weights    = [0.0, 0.0, 1.0]
    target.attributes   = [10000.0, 15.0, 5.0, 5.0, 1.0, 0.0, 0.0, 0.0]
    target.weights      = [0.0, 0.0, 1.0]
    seed_combat(1)
    return simulate_combat_traced(attacker, target)


for cooldown in (1.0, 1.3, 2.5, 5.0):
    hits = np.nonzero(_duel(cooldown, 0.0).attacked[:, 0])[0]
    mean_period = float(np.diff(hits).mean())
    assert abs(mean_period - cooldown * TICK_SCALE) < 0.05, (cooldown, mean_period)
print("  ✓ período médio entre golpes = attack_cooldown × TICK_SCALE (1 · 1,3 · 2,5 · 5)")

previous = -1.0
for stun in (0.02, 0.07, 0.13, 0.21, 0.33, 0.47, 0.59):
    trace = _duel(1.0, stun)
    n_hits = int(trace.attacked[:, 0].sum())
    per_hit = float(trace.stun_applied[:, 0].sum()) / n_hits
    assert abs(per_hit - stun * TICK_SCALE) < 0.05, (stun, per_hit)
    assert per_hit > previous, "stun maior tem de travar mais — sem platô"
    previous = per_hit
print("  ✓ stun aplicado por golpe = stun × cooldown × TICK_SCALE em média, sem platô")


# ── 8. Paridade: JIT de fitness vs JIT traced ────────────────────────────────

separator("Paridade: _simulate_combat_jit vs _simulate_combat_traced_jit")
# As duas variantes DEVEM simular exatamente o mesmo combate (mesmo consumo de RNG):
# a credibilidade do fingerprint/validador comportamental depende disso. Este teste
# blinda contra divergência entre as cópias da lógica de decisão.
parity_pairs = [
    (ArchetypeID.RUSHDOWN, ArchetypeID.ZONER),
    (ArchetypeID.GRAPPLER, ArchetypeID.TURTLE),
    (ArchetypeID.COMBO_MASTER, ArchetypeID.ZONER),
]
canon = Individual.from_canonical()
def _canon_char(aid: ArchetypeID) -> Character:
    return next(c for c in canon.characters if c.archetype_id == aid)

mismatches = 0
for aid_a, aid_b in parity_pairs:
    ca, cb = _canon_char(aid_a), _canon_char(aid_b)
    for s in range(20):
        seed_combat(s); r = simulate_combat(ca, cb)
        seed_combat(s); t = simulate_combat_traced(ca, cb)
        hp_t = (float(t.hp[-1, 0]), float(t.hp[-1, 1])) if t.end_tick > 0 else r.hp_remaining
        ok = (
            r.winner == t.winner
            and r.ticks == t.end_tick
            and r.ko == t.ko
            and abs(r.hp_remaining[0] - hp_t[0]) < 1e-9
            and abs(r.hp_remaining[1] - hp_t[1]) < 1e-9
        )
        if not ok:
            mismatches += 1
assert mismatches == 0, f"{mismatches} divergências entre fitness-JIT e traced-JIT"
print("  ✓ as duas variantes do JIT produzem desfecho idêntico")


# ── Agarrão: counter à guarda, não golpe melhor ─────────────────────────────

separator("Agarrão — quebra de guarda proporcional a grab_power")

from src.engine.character import Attr, WIdx
from src.engine.config import DEFEND_DAMAGE_REDUCTION


def _fighter(aid: ArchetypeID, **genes) -> Character:
    """Cópia de um canônico com genes sobrescritos, para isolar a mecânica."""
    char = _canon_char(aid).clone()
    for name, value in genes.items():
        if name.startswith("w_"):
            char.weights[getattr(WIdx, name[2:].upper())] = value
        else:
            char.attributes[getattr(Attr, name.upper())] = value
    return char


def _hit_profile(attacker: Character, defender: Character, seed: int = 7):
    """(dano médio POR GOLPE, dano total arrancado pela guarda).

    Por golpe, não total: a luta termina em KO, então o dano total fica limitado
    pelo HP do alvo e esconde o efeito da mecânica."""
    seed_combat(seed)
    trace = simulate_combat_traced(attacker, defender)
    dealt = trace.damage_dealt[:, 0]
    hits  = dealt[dealt > 0]
    assert hits.size > 0, "o atacante precisa conectar ao menos um golpe"
    return float(hits.mean()), float(trace.guard_broken[:, 0].sum())


# Alvo que SEMPRE defende; atacante que sempre avança. Isola o efeito da guarda.
GUARDING = dict(w_retreat=0.0, w_defend=1.0, w_aggressiveness=0.0)
PRESSING = dict(w_retreat=0.0, w_defend=0.0, w_aggressiveness=1.0)

blocker  = _fighter(ArchetypeID.TURTLE,   **GUARDING)
no_grab  = _fighter(ArchetypeID.GRAPPLER, grab_power=0.0, **PRESSING)
max_grab = _fighter(ArchetypeID.GRAPPLER, grab_power=1.0, **PRESSING)

hit_none, broke_none = _hit_profile(no_grab,  blocker)
hit_full, broke_full = _hit_profile(max_grab, blocker)

assert broke_none == 0.0, "sem grab_power não se arranca nada pela guarda"
assert broke_full > 0.0, "com grab_power máximo a guarda tem de ser quebrada"

expected_none = no_grab.damage * DEFEND_DAMAGE_REDUCTION
expected_full = max_grab.damage * (DEFEND_DAMAGE_REDUCTION + 1.0)
assert abs(hit_none - expected_none) < 1e-6, f"grab 0 deve dar {expected_none:.2f}"
assert abs(hit_full - expected_full) < 1e-6, f"grab 1 deve dar {expected_full:.2f}"
print(f"  contra alvo em GUARDA, dano por golpe: grab 0.0 → {hit_none:.1f} "
      f"({DEFEND_DAMAGE_REDUCTION:.2f}×), grab 1.0 → {hit_full:.1f} "
      f"({DEFEND_DAMAGE_REDUCTION + 1.0:.2f}×)")

# O ponto NEUTRO — onde a guarda deixa de compensar — é `1 − defend_red`. Abaixo dele
# defender ainda vale; acima, defender é pior que não defender. É a régua que separa
# o Grappler (0.90) dos outros quatro arquétipos (todos abaixo de 0.40).
neutral = 1.0 - DEFEND_DAMAGE_REDUCTION
hit_neutral, _ = _hit_profile(_fighter(ArchetypeID.GRAPPLER, grab_power=neutral, **PRESSING), blocker)
assert abs(hit_neutral - max_grab.damage) < 1e-6, (
    f"em grab={neutral:.2f} a guarda deve ser exatamente anulada "
    f"({max_grab.damage}), deu {hit_neutral:.2f}"
)
print(f"  ✓ ponto neutro em grab={neutral:.2f}: guarda anulada (dano = golpe limpo)")
assert hit_full > max_grab.damage, "acima do neutro, a guarda tem de virar desvantagem"
print(f"  ✓ acima do neutro a guarda PUNE: {hit_full:.1f} > {max_grab.damage:.0f} do golpe limpo")

# O invariante que faz do agarrão um COUNTER: contra quem não defende, ele não existe.
aggressive = _fighter(ArchetypeID.TURTLE, **PRESSING)
hit_a, broke_a = _hit_profile(_fighter(ArchetypeID.GRAPPLER, grab_power=0.0, **PRESSING), aggressive)
hit_b, broke_b = _hit_profile(_fighter(ArchetypeID.GRAPPLER, grab_power=1.0, **PRESSING), aggressive)
assert broke_a == 0.0 and broke_b == 0.0, "sem guarda não há o que quebrar"
assert abs(hit_a - hit_b) < 1e-9, (
    f"grab_power não pode mudar nada contra quem não defende: {hit_a:.4f} vs {hit_b:.4f}"
)
print("  ✓ contra quem NÃO defende, grab_power não muda nada — é counter, não golpe melhor")

# Só o Grappler canônico passa do ponto neutro: é isso que o diferencia dos outros.
_canon_ind = Individual.from_canonical()
above = [c.name for c in _canon_ind.characters if c.grab_power > neutral]
assert above == ["Grappler"], f"só o Grappler deve punir a guarda, mas {above} passam do neutro"
print(f"  ✓ nos canônicos, só o Grappler passa do ponto neutro — os outros 4 ficam abaixo")


separator("Todos os testes de combate passaram ✓")
