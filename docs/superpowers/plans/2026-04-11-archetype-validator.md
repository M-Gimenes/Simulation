# Archetype Validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `archetype_validator.py`, a standalone diagnostic tool that runs 28 archetype identity assertions on any `Individual` and prints a structured pass/fail report.

**Architecture:** Layer 1–2 check gene rankings statically (no simulation). Layers 3–4 run a detailed round-robin that tracks per-fighter action counts and outcome stats. A single `run_validation(individual)` function orchestrates all layers and returns a `ArchetypeValidationReport`.

**Tech Stack:** Python stdlib only. Reuses `combat.py`, `individual.py`, `archetypes.py`, `config.py`. Tests use plain `assert` statements, run with `py test_archetype_validator.py`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `combat.py` | Modify | Add `ActionLog` dataclass + `simulate_combat_detailed()` at the bottom |
| `archetype_validator.py` | Create | All validation logic: data structures, layer checks, report output, entry point |
| `test_archetype_validator.py` | Create | All tests, run as `py test_archetype_validator.py` |

---

## Task 1: `simulate_combat_detailed` in `combat.py`

**Files:**
- Modify: `combat.py` (append after line 363)
- Test: `test_archetype_validator.py` (create)

- [ ] **Step 1: Write the failing test**

Create `test_archetype_validator.py`:

```python
import sys, os
sys.path.insert(0, os.getcwd())

# ── Task 1 ────────────────────────────────────────────────────────────────────

def test_action_log_structure():
    from combat import simulate_combat_detailed, Action
    from individual import Individual

    canon = Individual.from_canonical()
    chars = canon.characters
    result, log = simulate_combat_detailed(chars[0], chars[1])

    # Both fighters logged
    assert len(log.action_counts) == 2
    assert len(log.active_ticks) == 2
    assert len(log.stun_applied) == 2

    # All four actions present as keys
    for counts in log.action_counts:
        assert set(counts.keys()) == {Action.ATTACK, Action.ADVANCE, Action.RETREAT, Action.DEFEND}

    # Sum of action counts equals active ticks for each fighter
    for i in range(2):
        assert sum(log.action_counts[i].values()) == log.active_ticks[i]

    # Active ticks positive (both fighters acted at some point)
    assert log.active_ticks[0] > 0
    assert log.active_ticks[1] > 0

    # Stun applied is non-negative
    assert log.stun_applied[0] >= 0
    assert log.stun_applied[1] >= 0

print("test_action_log_structure ...", end=" ", flush=True)
test_action_log_structure()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name 'simulate_combat_detailed' from 'combat'`

- [ ] **Step 3: Add `ActionLog` and `simulate_combat_detailed` to `combat.py`**

First, update the `typing` import line at the top of `combat.py` (line 1 of the imports block):

```python
# Before:
from typing import List, Optional, Tuple
# After:
from typing import Dict, List, Optional, Tuple
```

Then append the following **at the end** of `combat.py` (after the existing `simulate_combat` function):

```python
# ─────────────────────────────────────────────────────────────────────────────
# Simulação detalhada — para diagnóstico de arquétipo
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ActionLog:
    """Contagem de ações e stun por lutador em um único combate."""
    action_counts: Tuple[Dict[int, int], Dict[int, int]]  # (fighter_0, fighter_1)
    active_ticks:  Tuple[int, int]                         # ticks não-stunados por lutador
    stun_applied:  Tuple[int, int]                         # stun total aplicado por lutador


def simulate_combat_detailed(
    char_a: Character, char_b: Character
) -> Tuple[CombatResult, ActionLog]:
    """
    Idêntico a simulate_combat mas registra distribuição de ações e stun aplicado.
    Usado exclusivamente pelo archetype_validator — não altera o pipeline de fitness.
    """
    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    pos = [
        (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,
        (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,
    ]
    end_tick = MAX_TICKS

    action_counts = [
        {Action.ATTACK: 0, Action.ADVANCE: 0, Action.RETREAT: 0, Action.DEFEND: 0},
        {Action.ATTACK: 0, Action.ADVANCE: 0, Action.RETREAT: 0, Action.DEFEND: 0},
    ]
    active_ticks = [0, 0]
    stun_applied = [0, 0]

    for tick in range(MAX_TICKS):
        distance = abs(pos[1] - pos[0])

        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            break

        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            elif _USE_EPSILON and random.random() < ACTION_EPSILON:
                a = random.randint(0, 3)
                actions.append(a)
                active_ticks[i] += 1
                action_counts[i][a] += 1
            else:
                a = _choose_action(fighters[i], fighters[1 - i], distance, pos[i])
                actions.append(a)
                active_ticks[i] += 1
                action_counts[i][a] += 1

        for i in range(2):
            if actions[i] not in (Action.ADVANCE, Action.RETREAT):
                continue
            speed = fighters[i].character.speed
            direction = 1.0 if pos[i] < pos[1 - i] else -1.0
            if actions[i] == Action.ADVANCE:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] + direction * speed))
            else:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] - direction * speed))

        distance = abs(pos[1] - pos[0])
        defending = [a == Action.DEFEND for a in actions]

        pre_stun_0 = fighters[0].stun_remaining
        pre_stun_1 = fighters[1].stun_remaining
        pre_cd_0   = fighters[0].cooldown_remaining
        pre_cd_1   = fighters[1].cooldown_remaining

        for attacker_idx in range(2):
            if actions[attacker_idx] != Action.ATTACK:
                continue
            if not fighters[attacker_idx].attack_ready:
                continue

            defender_idx = 1 - attacker_idx
            dmg, stun, kb = _resolve_attack(
                attacker=fighters[attacker_idx].character,
                defender_state=fighters[defender_idx],
                defender_is_defending=defending[defender_idx],
                distance=distance,
            )

            if dmg > 0:
                fighters[defender_idx].hp = max(0.0, fighters[defender_idx].hp - dmg)

                if stun > fighters[defender_idx].stun_remaining:
                    fighters[defender_idx].stun_remaining = stun
                stun_applied[attacker_idx] += stun

                kb_dir = 1.0 if pos[defender_idx] >= pos[attacker_idx] else -1.0
                pos[defender_idx] = max(0.0, min(FIELD_SIZE, pos[defender_idx] + kb_dir * kb))

                fighters[attacker_idx].cooldown_remaining = round(
                    fighters[attacker_idx].character.attack_cooldown
                )

        f0, f1 = fighters
        if f0.stun_remaining <= pre_stun_0:
            f0.stun_remaining = max(0, f0.stun_remaining - 1)
        if f0.cooldown_remaining <= pre_cd_0:
            f0.cooldown_remaining = max(0, f0.cooldown_remaining - 1)
        if f1.stun_remaining <= pre_stun_1:
            f1.stun_remaining = max(0, f1.stun_remaining - 1)
        if f1.cooldown_remaining <= pre_cd_1:
            f1.cooldown_remaining = max(0, f1.cooldown_remaining - 1)

    hp_a = max(0.0, fighters[0].hp)
    hp_b = max(0.0, fighters[1].hp)

    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
        result = CombatResult(winner=winner, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    elif not fighters[0].is_alive:
        result = CombatResult(winner=1, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    elif not fighters[1].is_alive:
        result = CombatResult(winner=0, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    else:
        winner = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
        result = CombatResult(winner=winner, ticks=MAX_TICKS, ko=False, hp_remaining=(hp_a, hp_b))

    log = ActionLog(
        action_counts=(action_counts[0], action_counts[1]),
        active_ticks=(active_ticks[0], active_ticks[1]),
        stun_applied=(stun_applied[0], stun_applied[1]),
    )
    return result, log
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: `test_action_log_structure ... OK`

- [ ] **Step 5: Commit**

```
git add combat.py test_archetype_validator.py
git commit -m "feat: add simulate_combat_detailed with action tracking"
```

---

## Task 2: Data structures in `archetype_validator.py`

**Files:**
- Create: `archetype_validator.py`
- Modify: `test_archetype_validator.py` (append tests)

- [ ] **Step 1: Append the failing test to `test_archetype_validator.py`**

```python
# ── Task 2 ────────────────────────────────────────────────────────────────────

def test_datastructures():
    from archetype_validator import ArchetypeCheck, CharacterStats, ArchetypeValidationReport
    from archetypes import ArchetypeID
    from combat import Action

    check = ArchetypeCheck(
        archetype=ArchetypeID.RUSHDOWN,
        layer="structural_inter",
        description="speed = highest",
        passed=True,
        actual_rank=1,
        expected_rank=1,
    )
    assert check.passed

    stats = CharacterStats(
        action_counts={Action.ATTACK: 10, Action.ADVANCE: 20, Action.RETREAT: 5, Action.DEFEND: 15},
        active_ticks=50,
        wins=3,
        n_combats=4,
        ko_wins=2,
        hp_pct_on_wins=[0.8, 0.6, 0.7],
        ticks_on_wins=[100, 150, 120],
        stun_applied=8,
    )
    assert abs(stats.aggression_rate - 0.60) < 1e-9   # (10+20)/50
    assert abs(stats.defend_rate     - 0.30) < 1e-9   # 15/50
    assert abs(stats.retreat_rate    - 0.10) < 1e-9   # 5/50
    assert abs(stats.ko_rate         - 2/3)  < 1e-9   # 2/3
    assert abs(stats.avg_hp_pct_on_win - 0.7)          < 1e-9
    assert abs(stats.avg_ticks_on_win  - 370/3)        < 1e-9
    assert abs(stats.avg_stun_applied  - 2.0)          < 1e-9  # 8/4

    report = ArchetypeValidationReport(checks=[check], passed=1, total=1)
    assert report.score == 1.0
    assert report.failures() == []

print("test_datastructures ...", end=" ", flush=True)
test_datastructures()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: No module named 'archetype_validator'`

- [ ] **Step 3: Create `archetype_validator.py` with data structures only**

```python
"""
Diagnóstico de identidade de arquétipo.

Executa 28 asserções em 4 camadas sobre qualquer Individual
(canônico ou evoluído) e imprime relatório pass/fail.

Uso standalone:
    py archetype_validator.py            # valida o canônico
    py archetype_validator.py --evolved  # requer individual salvo (futuro)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Tuple

from archetypes import ARCHETYPE_ORDER, ArchetypeID
from combat import Action, ActionLog, CombatResult, simulate_combat_detailed
from config import ATTRIBUTE_BOUNDS, SIMS_PER_MATCHUP
from individual import Individual


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArchetypeCheck:
    archetype:     ArchetypeID
    layer:         str   # "structural_inter" | "structural_intra" | "behavioral" | "outcome"
    description:   str
    passed:        bool
    actual_rank:   int   # 1 = highest value; 0 = N/A (intra assertions)
    expected_rank: int   # 1 = should be highest; 5 = should be lowest; 0 = N/A


@dataclass
class CharacterStats:
    """Stats agregados de um personagem sobre todos os combates do round-robin."""
    action_counts:   Dict[int, int]  # Action → total de ticks nessa ação
    active_ticks:    int             # total de ticks não-stunados
    wins:            int
    n_combats:       int
    ko_wins:         int
    hp_pct_on_wins:  List[float]     # HP% restante em cada vitória
    ticks_on_wins:   List[int]       # duração do combate em cada vitória
    stun_applied:    int             # total de ticks de stun aplicados

    @property
    def aggression_rate(self) -> float:
        atk = self.action_counts.get(Action.ATTACK, 0) + self.action_counts.get(Action.ADVANCE, 0)
        return atk / self.active_ticks if self.active_ticks > 0 else 0.0

    @property
    def defend_rate(self) -> float:
        return self.action_counts.get(Action.DEFEND, 0) / self.active_ticks if self.active_ticks > 0 else 0.0

    @property
    def retreat_rate(self) -> float:
        return self.action_counts.get(Action.RETREAT, 0) / self.active_ticks if self.active_ticks > 0 else 0.0

    @property
    def ko_rate(self) -> float:
        return self.ko_wins / self.wins if self.wins > 0 else 0.0

    @property
    def avg_hp_pct_on_win(self) -> float:
        return sum(self.hp_pct_on_wins) / len(self.hp_pct_on_wins) if self.hp_pct_on_wins else 0.0

    @property
    def avg_ticks_on_win(self) -> float:
        return sum(self.ticks_on_wins) / len(self.ticks_on_wins) if self.ticks_on_wins else 0.0

    @property
    def avg_stun_applied(self) -> float:
        return self.stun_applied / self.n_combats if self.n_combats > 0 else 0.0


@dataclass
class ArchetypeValidationReport:
    checks: List[ArchetypeCheck]
    passed: int
    total:  int

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    def failures(self) -> List[ArchetypeCheck]:
        return [c for c in self.checks if not c.passed]
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: both tests print `OK`

- [ ] **Step 5: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: archetype_validator data structures + CharacterStats properties"
```

---

## Task 3: Layer 1 — structural inter-character checks

**Files:**
- Modify: `archetype_validator.py` (append after data structures)
- Modify: `test_archetype_validator.py` (append test)

- [ ] **Step 1: Append the failing test**

```python
# ── Task 3 ────────────────────────────────────────────────────────────────────

def test_structural_inter_canonical():
    from archetype_validator import _check_structural_inter
    from archetypes import ArchetypeID
    from individual import Individual

    canon = Individual.from_canonical()
    checks = _check_structural_inter(canon.characters)

    assert len(checks) == 14

    # All layers are "structural_inter"
    assert all(c.layer == "structural_inter" for c in checks)

    # Known canonical bugs — these two must FAIL
    failing = {(c.archetype, c.description[:15]) for c in checks if not c.passed}
    turtle_recovery_fails = any(
        c.archetype == ArchetypeID.TURTLE and "recovery" in c.description and not c.passed
        for c in checks
    )
    turtle_cooldown_fails = any(
        c.archetype == ArchetypeID.TURTLE and "attack_cooldown" in c.description and not c.passed
        for c in checks
    )
    assert turtle_recovery_fails,  "Turtle recovery should fail (Grappler leads in canonical)"
    assert turtle_cooldown_fails,  "Turtle attack_cooldown should fail (Grappler leads in canonical)"

    # All other 12 must pass
    assert sum(1 for c in checks if c.passed) == 12

print("test_structural_inter_canonical ...", end=" ", flush=True)
test_structural_inter_canonical()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name '_check_structural_inter' from 'archetype_validator'`

- [ ] **Step 3: Append `_rank_desc` and `_check_structural_inter` to `archetype_validator.py`**

```python
# ─────────────────────────────────────────────────────────────────────────────
# Helpers de ranking
# ─────────────────────────────────────────────────────────────────────────────

def _rank_desc(values: List[float]) -> List[int]:
    """
    Retorna rank para cada valor (1 = maior). Empates recebem ranks consecutivos
    pela posição original (sort estável).
    """
    n = len(values)
    ranks = [0] * n
    for rank_pos, orig_idx in enumerate(
        sorted(range(n), key=lambda i: values[i], reverse=True)
    ):
        ranks[orig_idx] = rank_pos + 1
    return ranks


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Structural inter-character
# ─────────────────────────────────────────────────────────────────────────────

# (archetype_id, attr_name, expected_rank, description)
# expected_rank=1 → deve ter o maior valor entre os 5 personagens
# expected_rank=5 → deve ter o menor valor entre os 5 personagens
_INTER_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.RUSHDOWN,     "speed",             1, "speed = highest (closes distance first)"),
    (ArchetypeID.RUSHDOWN,     "attack_cooldown",   5, "attack_cooldown = lowest (fastest attacker)"),
    (ArchetypeID.RUSHDOWN,     "w_aggressiveness",  1, "w_aggressiveness = highest (never retreats)"),
    (ArchetypeID.ZONER,        "range_",            1, "range = highest (controls space from afar)"),
    (ArchetypeID.ZONER,        "knockback",         1, "knockback = highest (pushes enemies out of range)"),
    (ArchetypeID.ZONER,        "w_retreat",         1, "w_retreat = highest (kites when threatened)"),
    (ArchetypeID.COMBO_MASTER, "stun",              1, "stun = highest (lockdown — chains combos)"),
    (ArchetypeID.GRAPPLER,     "damage",            1, "damage = highest (burst punish at close range)"),
    (ArchetypeID.TURTLE,       "recovery",          1, "recovery = highest (most resistant to stun)"),
    (ArchetypeID.TURTLE,       "speed",             5, "speed = lowest (slowest — compensates with durability)"),
    (ArchetypeID.TURTLE,       "attack_cooldown",   1, "attack_cooldown = highest (patient, punishes mistakes)"),
    (ArchetypeID.TURTLE,       "hp",                1, "hp = highest (living wall)"),
    (ArchetypeID.TURTLE,       "defense",           1, "defense = highest (absorbs maximum damage)"),
    (ArchetypeID.TURTLE,       "w_defend",          1, "w_defend = highest (absorbs instead of retreating)"),
]


def _check_structural_inter(chars) -> List[ArchetypeCheck]:
    arch_to_idx = {c.archetype.id: i for i, c in enumerate(chars)}
    checks = []
    for arch_id, attr_name, expected_rank, description in _INTER_ASSERTIONS:
        values = [getattr(c, attr_name) for c in chars]
        ranks  = _rank_desc(values)
        idx    = arch_to_idx[arch_id]
        actual = ranks[idx]
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="structural_inter",
            description=description,
            passed=(actual == expected_rank),
            actual_rank=actual,
            expected_rank=expected_rank,
        ))
    return checks
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: all three tests print `OK`

- [ ] **Step 5: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: layer 1 structural inter-character rank assertions (14 checks)"
```

---

## Task 4: Layer 2 — structural intra-character checks

**Files:**
- Modify: `archetype_validator.py` (append)
- Modify: `test_archetype_validator.py` (append)

- [ ] **Step 1: Append the failing test**

```python
# ── Task 4 ────────────────────────────────────────────────────────────────────

def test_structural_intra_canonical():
    from archetype_validator import _check_structural_intra
    from individual import Individual

    canon = Individual.from_canonical()
    checks = _check_structural_intra(canon.characters)

    assert len(checks) == 6
    assert all(c.layer == "structural_intra" for c in checks)

    # All 6 pass on canonical values (verified analytically in design spec)
    failed = [c for c in checks if not c.passed]
    assert failed == [], f"Unexpected failures: {[c.description for c in failed]}"

print("test_structural_intra_canonical ...", end=" ", flush=True)
test_structural_intra_canonical()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name '_check_structural_intra'`

- [ ] **Step 3: Append `_check_structural_intra` to `archetype_validator.py`**

```python
# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Structural intra-character (normalized comparisons)
# ─────────────────────────────────────────────────────────────────────────────

# Mapa de nome de propriedade → (lo, hi) dos ATTRIBUTE_BOUNDS
_ATTR_BOUNDS: Dict[str, Tuple[float, float]] = dict(zip(
    ["hp", "damage", "attack_cooldown", "range_", "speed", "defense", "stun", "knockback", "recovery"],
    ATTRIBUTE_BOUNDS,
))


def _norm(char, attr_name: str) -> float:
    """Normaliza o atributo para [0, 1] usando os bounds globais."""
    lo, hi = _ATTR_BOUNDS[attr_name]
    return (getattr(char, attr_name) - lo) / (hi - lo)


# (archetype_id, attr_a, attr_b, description)
# Asserção: norm(attr_a) > norm(attr_b) para o personagem do arquétipo dado
_INTRA_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.ZONER,        "range_",  "speed",    "norm(range) > norm(speed) — space control over mobility"),
    (ArchetypeID.RUSHDOWN,     "speed",   "range_",   "norm(speed) > norm(range) — closes gap, not ranged"),
    (ArchetypeID.GRAPPLER,     "hp",      "speed",    "norm(hp) > norm(speed) — durability over mobility"),
    (ArchetypeID.TURTLE,       "defense", "damage",   "norm(defense) > norm(damage) — punishes errors, not pressures"),
    (ArchetypeID.COMBO_MASTER, "stun",    "knockback","norm(stun) > norm(knockback) — holds, doesn't push"),
    (ArchetypeID.COMBO_MASTER, "speed",   "range_",   "norm(speed) > norm(range) — closes distance for combos"),
]


def _check_structural_intra(chars) -> List[ArchetypeCheck]:
    arch_to_char = {c.archetype.id: c for c in chars}
    checks = []
    for arch_id, attr_a, attr_b, description in _INTRA_ASSERTIONS:
        char   = arch_to_char[arch_id]
        norm_a = _norm(char, attr_a)
        norm_b = _norm(char, attr_b)
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="structural_intra",
            description=description,
            passed=(norm_a > norm_b),
            actual_rank=0,
            expected_rank=0,
        ))
    return checks
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: all tests print `OK`

- [ ] **Step 5: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: layer 2 structural intra-character normalized assertions (6 checks)"
```

---

## Task 5: `_collect_stats` — round-robin with action tracking

**Files:**
- Modify: `archetype_validator.py` (append)
- Modify: `test_archetype_validator.py` (append)

- [ ] **Step 1: Append the failing test**

```python
# ── Task 5 ────────────────────────────────────────────────────────────────────

def test_collect_stats_structure():
    from archetype_validator import _collect_stats, CharacterStats
    from combat import Action
    from individual import Individual

    canon = Individual.from_canonical()
    stats = _collect_stats(canon, n_sims=5)

    assert len(stats) == 5  # one per character

    for s in stats:
        assert isinstance(s, CharacterStats)
        # Each character fights 4 others × 5 sims = 20 combats
        assert s.n_combats == 20
        # Action counts cover all four actions
        assert set(s.action_counts.keys()) == {Action.ATTACK, Action.ADVANCE, Action.RETREAT, Action.DEFEND}
        # Active ticks = sum of action counts
        assert sum(s.action_counts.values()) == s.active_ticks
        assert s.active_ticks > 0
        # Wins within valid range
        assert 0 <= s.wins <= s.n_combats
        assert 0 <= s.ko_wins <= s.wins
        # hp_pct_on_wins entries in [0, 1]
        assert all(0.0 <= hp <= 1.0 for hp in s.hp_pct_on_wins)

print("test_collect_stats_structure ...", end=" ", flush=True)
test_collect_stats_structure()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name '_collect_stats'`

- [ ] **Step 3: Append `_collect_stats` to `archetype_validator.py`**

```python
# ─────────────────────────────────────────────────────────────────────────────
# Coleta de stats simulados
# ─────────────────────────────────────────────────────────────────────────────

def _collect_stats(individual: Individual, n_sims: int) -> List[CharacterStats]:
    """
    Executa round-robin completo com simulate_combat_detailed.
    Retorna uma lista de CharacterStats na ordem de individual.characters.
    """
    chars = individual.characters
    n     = len(chars)

    stats = [
        CharacterStats(
            action_counts={Action.ATTACK: 0, Action.ADVANCE: 0, Action.RETREAT: 0, Action.DEFEND: 0},
            active_ticks=0,
            wins=0,
            n_combats=0,
            ko_wins=0,
            hp_pct_on_wins=[],
            ticks_on_wins=[],
            stun_applied=0,
        )
        for _ in range(n)
    ]

    for i, j in combinations(range(n), 2):
        for _ in range(n_sims):
            result, log = simulate_combat_detailed(chars[i], chars[j])

            # Atualiza stats de ação para ambos os lutadores
            for fighter_pos, char_idx in ((0, i), (1, j)):
                s = stats[char_idx]
                for action, count in log.action_counts[fighter_pos].items():
                    s.action_counts[action] += count
                s.active_ticks += log.active_ticks[fighter_pos]
                s.stun_applied += log.stun_applied[fighter_pos]
                s.n_combats    += 1

            # Atualiza stats de resultado para o vencedor
            winner_char_idx = i if result.winner == 0 else j
            winner_hp = result.hp_remaining[result.winner]
            winner_hp_pct = winner_hp / chars[winner_char_idx].hp

            sw = stats[winner_char_idx]
            sw.wins += 1
            if result.ko:
                sw.ko_wins += 1
            sw.hp_pct_on_wins.append(winner_hp_pct)
            sw.ticks_on_wins.append(result.ticks)

    return stats
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: all tests print `OK`

- [ ] **Step 5: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: _collect_stats round-robin with action and outcome tracking"
```

---

## Task 6: Layer 3 — behavioral checks

**Files:**
- Modify: `archetype_validator.py` (append)
- Modify: `test_archetype_validator.py` (append)

- [ ] **Step 1: Append the failing test**

```python
# ── Task 6 ────────────────────────────────────────────────────────────────────

def test_behavioral_checks_structure():
    from archetype_validator import _check_behavioral, _collect_stats
    from individual import Individual

    canon  = Individual.from_canonical()
    stats  = _collect_stats(canon, n_sims=5)
    checks = _check_behavioral(stats)

    assert len(checks) == 3
    assert all(c.layer == "behavioral" for c in checks)
    # Each check has a valid actual_rank (1–5)
    assert all(1 <= c.actual_rank <= 5 for c in checks)

print("test_behavioral_checks_structure ...", end=" ", flush=True)
test_behavioral_checks_structure()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name '_check_behavioral'`

- [ ] **Step 3: Append `_check_behavioral` to `archetype_validator.py`**

```python
# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Behavioral
# ─────────────────────────────────────────────────────────────────────────────

# (archetype_id, metric_name, expected_rank, description)
_BEHAVIORAL_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.RUSHDOWN, "aggression_rate", 1, "aggression_rate = highest (always closing/attacking)"),
    (ArchetypeID.TURTLE,   "defend_rate",     1, "defend_rate = highest (absorb-first strategy)"),
    (ArchetypeID.ZONER,    "retreat_rate",    1, "retreat_rate = highest (kiting — creates distance)"),
]


def _check_behavioral(stats: List[CharacterStats]) -> List[ArchetypeCheck]:
    arch_to_idx = {arch_id: i for i, arch_id in enumerate(ARCHETYPE_ORDER)}
    checks = []
    for arch_id, metric, expected_rank, description in _BEHAVIORAL_ASSERTIONS:
        values = [getattr(s, metric) for s in stats]
        ranks  = _rank_desc(values)
        idx    = arch_to_idx[arch_id]
        actual = ranks[idx]
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="behavioral",
            description=description,
            passed=(actual == expected_rank),
            actual_rank=actual,
            expected_rank=expected_rank,
        ))
    return checks
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: all tests print `OK`

- [ ] **Step 5: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: layer 3 behavioral rank assertions (3 checks)"
```

---

## Task 7: Layer 4 — outcome checks

**Files:**
- Modify: `archetype_validator.py` (append)
- Modify: `test_archetype_validator.py` (append)

- [ ] **Step 1: Append the failing test**

```python
# ── Task 7 ────────────────────────────────────────────────────────────────────

def test_outcome_checks_structure():
    from archetype_validator import _check_outcome, _collect_stats
    from individual import Individual

    canon  = Individual.from_canonical()
    stats  = _collect_stats(canon, n_sims=5)
    checks = _check_outcome(stats)

    assert len(checks) == 5
    assert all(c.layer == "outcome" for c in checks)
    assert all(1 <= c.actual_rank <= 5 for c in checks)

print("test_outcome_checks_structure ...", end=" ", flush=True)
test_outcome_checks_structure()
print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name '_check_outcome'`

- [ ] **Step 3: Append `_check_outcome` to `archetype_validator.py`**

```python
# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Outcome
# ─────────────────────────────────────────────────────────────────────────────

# (archetype_id, metric_name, expected_rank, description)
_OUTCOME_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.GRAPPLER,     "ko_rate",            1, "ko_rate = highest (burst damage — finishes enemies)"),
    (ArchetypeID.TURTLE,       "avg_hp_pct_on_win",  1, "avg_hp_pct_on_win = highest (absorbs damage cleanly)"),
    (ArchetypeID.RUSHDOWN,     "avg_ticks_on_win",   5, "avg_ticks_on_win = lowest (overwhelms fast)"),
    (ArchetypeID.TURTLE,       "avg_ticks_on_win",   1, "avg_ticks_on_win = highest (wins by attrition)"),
    (ArchetypeID.COMBO_MASTER, "avg_stun_applied",   1, "avg_stun_applied = highest (lockdown identity)"),
]


def _check_outcome(stats: List[CharacterStats]) -> List[ArchetypeCheck]:
    arch_to_idx = {arch_id: i for i, arch_id in enumerate(ARCHETYPE_ORDER)}
    checks = []
    for arch_id, metric, expected_rank, description in _OUTCOME_ASSERTIONS:
        values = [getattr(s, metric) for s in stats]
        ranks  = _rank_desc(values)
        idx    = arch_to_idx[arch_id]
        actual = ranks[idx]
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="outcome",
            description=description,
            passed=(actual == expected_rank),
            actual_rank=actual,
            expected_rank=expected_rank,
        ))
    return checks
```

- [ ] **Step 4: Run test to verify it passes**

```
py test_archetype_validator.py
```

Expected: all tests print `OK`

- [ ] **Step 5: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: layer 4 outcome rank assertions (5 checks)"
```

---

## Task 8: `run_validation`, `print_report`, entry point

**Files:**
- Modify: `archetype_validator.py` (append)
- Modify: `test_archetype_validator.py` (append)

- [ ] **Step 1: Append the failing test**

```python
# ── Task 8 ────────────────────────────────────────────────────────────────────

def test_run_validation_canonical():
    from archetype_validator import run_validation
    from individual import Individual

    canon  = Individual.from_canonical()
    report = run_validation(canon, n_sims=10)

    assert report.total == 28
    # Known: 2 structural inter failures; behavioral/outcome may vary
    assert report.passed <= 28
    assert report.passed >= 12  # at minimum all other structural checks pass
    assert 0.0 <= report.score <= 1.0
    assert len(report.failures()) == report.total - report.passed

print("test_run_validation_canonical ...", end=" ", flush=True)
test_run_validation_canonical()
print("OK")
print("\nAll tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

```
py test_archetype_validator.py
```

Expected: `ImportError: cannot import name 'run_validation'`

- [ ] **Step 3: Append `run_validation`, `print_report`, and entry point to `archetype_validator.py`**

```python
# ─────────────────────────────────────────────────────────────────────────────
# Orquestração
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(
    individual: Individual,
    n_sims: int = SIMS_PER_MATCHUP,
) -> ArchetypeValidationReport:
    """Executa as 28 asserções e retorna o relatório completo."""
    chars  = individual.characters
    checks: List[ArchetypeCheck] = []

    # Camadas 1–2: apenas genes, sem simulação
    checks.extend(_check_structural_inter(chars))
    checks.extend(_check_structural_intra(chars))

    # Camadas 3–4: requerem simulação
    stats = _collect_stats(individual, n_sims)
    checks.extend(_check_behavioral(stats))
    checks.extend(_check_outcome(stats))

    passed = sum(1 for c in checks if c.passed)
    return ArchetypeValidationReport(checks=checks, passed=passed, total=len(checks))


# ─────────────────────────────────────────────────────────────────────────────
# Formatação do relatório
# ─────────────────────────────────────────────────────────────────────────────

_LAYER_LABELS = {
    "structural_inter": "LAYER 1 — Structural (inter-character)",
    "structural_intra": "LAYER 2 — Structural (intra-character, normalized)",
    "behavioral":       "LAYER 3 — Behavioral",
    "outcome":          "LAYER 4 — Outcome",
}
_ARCH_NAMES = {a: a.name.replace("_", " ").title() for a in ArchetypeID}
_LINE = "═" * 66


def print_report(report: ArchetypeValidationReport) -> None:
    print("ARCHETYPE VALIDATION REPORT")
    print(_LINE)

    current_layer = None
    current_arch  = None

    for check in report.checks:
        if check.layer != current_layer:
            current_layer = check.layer
            current_arch  = None
            print(f"\n{_LAYER_LABELS[current_layer]}")

        prefix = f"  {_ARCH_NAMES[check.archetype]:<14}" if check.archetype != current_arch else " " * 16
        current_arch = check.archetype

        symbol   = "✓" if check.passed else "✗"
        rank_str = ""
        if check.actual_rank != 0 and not check.passed:
            rank_str = f" (actual rank {check.actual_rank})"

        print(f"{prefix} {symbol} {check.description}{rank_str}")

    print()
    failures  = report.failures()
    score_pct = report.score * 100

    if not failures:
        print(f"SCORE: {report.passed}/{report.total} ({score_pct:.1f}%) — all assertions passed ✓")
    else:
        print(f"SCORE: {report.passed}/{report.total} ({score_pct:.1f}%) — {len(failures)} failure(s)")
        for f in failures:
            rank_str = f" (actual rank {f.actual_rank})" if f.actual_rank != 0 else ""
            print(f"  ✗ {_ARCH_NAMES[f.archetype]}: {f.description}{rank_str}")

    print(_LINE)


# ─────────────────────────────────────────────────────────────────────────────
# Entrada standalone
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    canon = Individual.from_canonical()
    print("Validating canonical individual...\n")
    report = run_validation(canon)
    print_report(report)
```

- [ ] **Step 4: Run tests to verify all pass**

```
py test_archetype_validator.py
```

Expected:
```
test_action_log_structure ... OK
test_datastructures ... OK
test_structural_inter_canonical ... OK
test_structural_intra_canonical ... OK
test_collect_stats_structure ... OK
test_behavioral_checks_structure ... OK
test_outcome_checks_structure ... OK
test_run_validation_canonical ... OK

All tests passed.
```

- [ ] **Step 5: Run the standalone validator against canonical**

```
py archetype_validator.py
```

Expected: report showing 2 known failures (Turtle recovery and Turtle attack_cooldown) and all other assertions.

- [ ] **Step 6: Commit**

```
git add archetype_validator.py test_archetype_validator.py
git commit -m "feat: run_validation, print_report, standalone entry point — archetype validator complete"
```
