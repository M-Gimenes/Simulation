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
Tick-based 1v1 combat. Each tick: decrement timers → choose action via softmax scoring → apply movement → resolve attacks simultaneously. Actions: ATTACK / ADVANCE / RETREAT / DEFEND. Key mechanics: cooldown is deterministic (ticks), stun is capped at attacker's own cooldown ticks (prevents infinite stun loops), knockback pushes the defender away after each hit.

**GA layer** (`ga.py`, `fitness.py`, `operators.py`):  
Each individual = 5 characters (one per archetype) = 70 genes total. Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula: `(1 - balance_error) - LAMBDA * attribute_cost - LAMBDA_DRIFT * drift_penalty`. The `attribute_cost` term uses a *specialization* metric (max−min of normalized attributes) — this rewards archetype differentiation and prevents the degenerate optimum where all stats drift toward zero.

**Data model** (`archetypes.py` → `character.py` → `individual.py`):  
`ArchetypeDefinition` (frozen, canonical values) → `Character` (mutable genes, 9 attrs + 5 weights) → `Individual` (list of 5 Characters + fitness cache). `Individual.from_canonical()` creates the canonical seed; `Individual.random()` creates a random individual.

## Key Design Decisions

**Softmax action selection** (`SCORE_TEMPERATURE = 0.1`): Low temperature makes behavior closely follow the `w_*` weights. The `score_attack` is forced to `-1e9` when the character is in cooldown — this prevents wasted attack attempts.

**Attribute cost vs. drift penalty**: `attribute_cost` (via `LAMBDA=0.3`) penalizes homogeneous builds; `drift_penalty` (via `LAMBDA_DRIFT`, currently `0.0`) penalizes deviation from canonical values. These are the central trade-off variables of the thesis — changing `LAMBDA_DRIFT` from 0 to a positive value adds an evolutionary "anchor" to archetypes.

**Canonical calibration rules** (documented in `tcc_design_decisions.md`):
- Damage range: 6–15 (low); HP range: 60–95 (relatively high) — ensures ≥5 hits to KO in any matchup
- All `range` values < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- Behaviors expressed via `w_*` weights, not hardcoded decision trees

**Known matchup limitation**: Zoner > Grappler is mechanically weak (~35–40% WR) because `score_retreat` only fires when the enemy is *already in range* — Zoner cannot proactively kite. Fixing this requires changes to the scoring formula in `_choose_action`.

**Open issue — CM > Turtle = 0% WR**: Turtle KOs CM despite w_defend=0.5 fix. Root cause: `score_attack` at temperature=0.1 competes with `score_advance=0` and `score_defend≈0`, giving CM only ~41% attack probability when in range. Additionally, choosing ATTACK while out of range whiffs (returns 0 dmg) but still triggers cooldown (phase 4 of `simulate_combat`). Fix candidates: raise `SCORE_TEMPERATURE`, add a proximity bonus to `score_advance` when already in range, or gate ATTACK on `in_range`.

## Matchup Verification Script

```bash
py -c "
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
| `LAMBDA` | 0.3 | Weight of specialization penalty in fitness |
| `LAMBDA_DRIFT` | 0.0 | Weight of archetype deviation penalty (0 = free evolution) |
| `SIMS_PER_MATCHUP` | 30 | Simulations per matchup (more = stable WR, slower) |
| `MAX_GENERATIONS` | 20 | GA termination limit |
| `SCORE_TEMPERATURE` | 0.1 | Softmax sharpness for action selection |
