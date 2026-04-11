# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

TCC (undergraduate thesis) — Genetic Algorithm for competitive game character balancing.  
**Research question:** Can a GA achieve competitive balance between 5 distinct archetypes without destroying their functional identities?

The canonical archetype values are *not* hardcoded constraints — they serve as an initial population seed and as a deviation measurement baseline. The GA evolves freely; archetype preservation is measured post-hoc via `LAMBDA_DRIFT`.

## Running

```bash
# Full GA run
py main.py
py main.py --seed 42 --quiet --log-every 5

# Web viewer (opens browser at localhost:8080)
py web_viewer.py

# Smoke tests (run individually — no test runner configured)
py test_base.py
py test_combat.py
py test_fitness.py
py test_operators.py
```

> **Windows note:** Use `py` not `python` or `python3`. Output uses Unicode (box-drawing chars); redirect to a file or use `--quiet` if the terminal has encoding issues.

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`combat.py`):  
Tick-based 1v1 combat. Each tick: choose action via priority system → apply movement → resolve attacks simultaneously → decrement timers. Actions: ATTACK / ADVANCE / RETREAT / DEFEND. Key mechanics: `attack_cooldown` is deterministic (ticks), stun is capped at attacker's own cooldown (prevents infinite stun loops), knockback pushes the defender away after each hit. Timers are decremented **after** attacks — values freshly set by an attack are not decremented until the following tick, making `cooldown=1` and `stun=1` meaningful minimums. Two sources of stochasticity: `DAMAGE_VARIANCE=0.20` (±20% per hit) and `ACTION_EPSILON=0.10` (10% chance of random action per tick, modelling execution errors).

**GA layer** (`ga.py`, `fitness.py`, `operators.py`):  
Each individual = 5 characters (one per archetype) = 60 genes total (9 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula: `(1 - balance_error) - LAMBDA * attribute_cost - LAMBDA_DRIFT * drift_penalty - LAMBDA_MATCHUP * matchup_dominance_penalty`. The `attribute_cost` term uses a *specialization* metric (max−min of normalized attributes) — rewards archetype differentiation and prevents homogenization. `matchup_dominance_penalty` uses `max(excess_ij)` over the 10 pairs — the single worst matchup drives the penalty, without mean dilution.

**Data model** (`archetypes.py` → `character.py` → `individual.py`):  
`ArchetypeDefinition` (frozen, canonical values) → `Character` (mutable genes, 9 attrs + 3 weights) → `Individual` (list of 5 Characters + fitness cache). `Individual.from_canonical()` creates the canonical seed; `Individual.random()` creates a random individual.

## Key Design Decisions

**Priority-based action selection**: Deterministic strategy modelling an experienced player. Priorities (highest to lowest): (1) ATTACK if in range and ready; (2) respond to threat — if enemy is ready and within `RETREAT_ZONE_FACTOR * enemy.range_`: the three behavioral weights compete directly — if `w_aggressiveness > w_retreat and w_aggressiveness > w_defend` → ADVANCE; else if `w_retreat > w_defend` → RETREAT; else → DEFEND; (3) ADVANCE if out of range or cornered; (4) DEFEND (default while waiting for cooldown). The `w_*` weights compete symmetrically — no hardcoded thresholds, giving the GA a continuous fitness landscape.

**Timer decrement order**: Decrements happen at the END of each tick (after attacks), using pre-attack timer values to decide what to decrement. Timers freshly set by an attack (`current > pre`) are preserved until the next tick. This means `stun=1` blocks the target for exactly 1 tick, and `attack_cooldown=1` forces a 1-tick wait before the next attack.

**Attribute cost vs. drift penalty vs. matchup penalty**: Three orthogonal fitness terms:
- `attribute_cost` (via `LAMBDA=0.2`) penalizes homogeneous builds
- `drift_penalty` (via `LAMBDA_DRIFT=0.0`) penalizes deviation from canonical values — the central trade-off of the thesis
- `matchup_dominance_penalty` (via `LAMBDA_MATCHUP=1`) penalizes the worst single-matchup WR excess beyond `MATCHUP_THRESHOLD=0.15` (65%)

**Convergence criteria**: Two conditions must both hold (confirmed with `SIMS_CONVERGENCE_CHECK` extra simulations):
1. Each character's aggregate WR within `CONVERGENCE_THRESHOLD` of 50%
2. Every direct matchup WR within `MATCHUP_CONVERGENCE_THRESHOLD` (20%) of 50%

**Canonical calibration rules**:
- HP range: 300–500; Damage range: 10–20 — minimum ~15 hits to KO (300 HP / 20 dmg)
- All `range` values ≤ 20 < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- `attack_cooldown` ∈ [1, 5]: Rushdown=2 (fastest), Grappler=5 (slowest)
- Behaviors expressed via `w_*` weights (3 per character: `w_retreat`, `w_defend`, `w_aggressiveness`)
- `w_aggressiveness >= 0.7` → aggressive archetypes (Rushdown, Grappler, Combo Master) push through threats
- `w_retreat > w_defend` → reactive archetypes (Zoner) kite; `w_defend >= w_retreat` → absorbers (Turtle) hold ground

**Cooldown only on hit**: `_resolve_attack` returns `(0, 0, 0)` if `distance > attacker.range_`. The cooldown is set only inside the `if dmg > 0` block — a whiffed attack (chosen before movement changed distance) does not waste the attacker's cooldown.

## Matchup Verification Script

```bash
py -c "
import sys, os; sys.path.insert(0, os.getcwd())
from archetypes import ArchetypeID
from individual import Individual
from combat import simulate_combat
from config import SIMS_PER_MATCHUP
canon = Individual.from_canonical()
chars = {c.archetype.id: c for c in canon.characters}
matchups = [
    (ArchetypeID.RUSHDOWN,     ArchetypeID.ZONER,        'RD > Zoner'),
    (ArchetypeID.ZONER,        ArchetypeID.GRAPPLER,     'Zoner > Grappler'),
    (ArchetypeID.ZONER,        ArchetypeID.TURTLE,       'Zoner > Turtle'),
    (ArchetypeID.GRAPPLER,     ArchetypeID.RUSHDOWN,     'Grappler > RD'),
    (ArchetypeID.GRAPPLER,     ArchetypeID.COMBO_MASTER, 'Grappler > CM'),
    (ArchetypeID.TURTLE,       ArchetypeID.RUSHDOWN,     'Turtle > RD'),
    (ArchetypeID.TURTLE,       ArchetypeID.GRAPPLER,     'Turtle > Grappler'),
    (ArchetypeID.COMBO_MASTER, ArchetypeID.TURTLE,       'CM > Turtle'),
    (ArchetypeID.COMBO_MASTER, ArchetypeID.ZONER,        'CM > Zoner'),
    (ArchetypeID.RUSHDOWN,     ArchetypeID.COMBO_MASTER, 'RD > CM'),
]
N = SIMS_PER_MATCHUP
for w, l, label in matchups:
    wins = sum(simulate_combat(chars[w], chars[l]).winner == 0 for _ in range(N))
    status = 'OK   ' if wins/N >= 0.55 else 'FALHOU'
    print(f'{status}  {label:<28} winrate={wins/N:.0%}')
"
```

## All Hyperparameters

Located in `config.py`. Commonly adjusted:

| Parameter | Value | Effect |
|---|---|---|
| `LAMBDA` | 0.2 | Weight of specialization penalty in fitness |
| `LAMBDA_DRIFT` | 0.0 | Weight of archetype deviation penalty (0 = free evolution) |
| `LAMBDA_MATCHUP` | 1.0 | Weight of worst-matchup dominance penalty |
| `MATCHUP_THRESHOLD` | 0.15 | WR excess above 50% that starts penalizing (65% = trigger) |
| `MATCHUP_CONVERGENCE_THRESHOLD` | 0.20 | Max WR deviation per matchup to declare convergence (70%) |
| `SIMS_PER_MATCHUP` | 15 | Simulations per matchup (more = stable WR, slower) |
| `SIMS_CONVERGENCE_CHECK` | 50 | Extra sims used only for convergence confirmation |
| `MAX_GENERATIONS` | 20 | GA termination limit |
| `DAMAGE_VARIANCE` | 0.20 | ±20% per-hit damage roll — execution variance |
| `ACTION_EPSILON` | 0.10 | Probability of random action per tick — decision error |
