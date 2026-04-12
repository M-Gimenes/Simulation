# Archetype Validation — Design Spec
**Date:** 2026-04-11  
**Status:** Approved

---

## Problem

The GA evolves freely (`LAMBDA_DRIFT=0.0`). Without a formal definition of what makes each character *behave like* its archetype, there is no way to know whether:
1. The canonical values are functionally correct (does the canonical Rushdown actually rush down?).
2. Evolved individuals still represent their archetypes after convergence.

Adjusting canonical values empirically creates a circular dependency — values change, but there is no objective criterion to judge whether the change is correct.

---

## Goal

A **standalone diagnostic tool** (`archetype_validator.py`) that runs on any `Individual` (canonical or evolved) and produces a structured report showing which archetype identity assertions pass or fail.

**Primary use:** validate the canonical `Individual.from_canonical()` first. Fix canonical values until all assertions pass. Then use the same tool to evaluate evolved individuals post-convergence.

The tool does **not** feed into the fitness function — it is purely diagnostic and does not constrain the GA.

---

## Architecture

```
Individual
    └─ run_validation(individual, n_sims) → ArchetypeValidationReport
            ├─ structural_inter()   — gene rankings across the 5 characters (no simulation)
            ├─ structural_intra()   — normalized attribute ratios within each character (no simulation)
            └─ simulate_detailed()  — round-robin with action tracking → behavioral + outcome metrics
```

New file: `archetype_validator.py`  
New helper in `combat.py` (or `archetype_validator.py`): `simulate_combat_detailed()` — same as `simulate_combat()` but additionally returns per-fighter action counts.

Existing `_run_round_robin` logic is reused conceptually; the detailed version adds action count tracking without modifying the existing fitness pipeline.

---

## The 28 Assertions

All ranking assertions are **ordinal within a single Individual** (5 characters compared against each other).  
All intra-character assertions use **normalized values**: `norm(v) = (v - lo) / (hi - lo)` using `ATTRIBUTE_BOUNDS` from `config.py`.

### Layer 1 — Structural Inter-Character (14 assertions)

Gene values ranked across the 5 characters. Only rank-1 (highest) and rank-last (lowest) are asserted — intermediate positions are not constrained.

| # | Archetype | Attribute | Expected position | Rationale |
|---|-----------|-----------|------------------|-----------|
| 1 | Rushdown | `speed` | rank 1 (highest) | Closes distance first |
| 2 | Rushdown | `attack_cooldown` | rank 1 (lowest = fastest) | Constant pressure |
| 3 | Rushdown | `w_aggressiveness` | rank 1 (highest) | Never retreats |
| 4 | Zoner | `range_` | rank 1 (highest) | Controls space from afar |
| 5 | Zoner | `knockback` | rank 1 (highest) | Pushes enemies out of range |
| 6 | Zoner | `w_retreat` | rank 1 (highest) | Kites when threatened |
| 7 | Combo Master | `stun` | rank 1 (highest) | Lockdown — chains combos |
| 8 | Grappler | `damage` | rank 1 (highest) | Burst punish at close range |
| 9 | Turtle | `recovery` | rank 1 (highest) | Most resistant to being stunned |
| 10 | Turtle | `speed` | rank last (lowest) | Slowest — compensates with durability |
| 11 | Turtle | `attack_cooldown` | rank last (highest = slowest) | Patient — punishes mistakes, doesn't pressure |
| 12 | Turtle | `hp` | rank 1 (highest) | Living wall — wins by attrition |
| 13 | Turtle | `defense` | rank 1 (highest) | Absorbs maximum damage |
| 14 | Turtle | `w_defend` | rank 1 (highest) | Absorbs instead of retreating |

### Layer 2 — Structural Intra-Character (5 assertions)

Normalized attribute comparisons **within** the same character. Captures build profile: which dimension the character prioritizes over others.

| # | Archetype | Assertion | Rationale |
|---|-----------|-----------|-----------|
| 15 | Zoner | `norm(range_) > norm(speed)` | Space control matters more than mobility |
| 16 | Rushdown | `norm(speed) > norm(range_)` | Built to close gap, not to attack from afar |
| 17 | Grappler | `norm(hp) > norm(speed)` | Durability compensates for low mobility |
| 18 | Turtle | `norm(defense) > norm(damage)` | Lives off punishing errors, not pressuring |
| 19 | Combo Master | `norm(stun) > norm(knockback)` | Holds enemies in place, does not push them away |
| 20 | Combo Master | `norm(speed) > norm(range_)` | Built to close distance, sets up combos at contact |

### Layer 3 — Behavioral (3 assertions)

Action distribution across all round-robin matchups. Metric per character = `action_count / total_active_ticks` (stunned ticks excluded).

| # | Archetype | Metric | Expected position | Rationale |
|---|-----------|--------|------------------|-----------|
| 21 | Rushdown | `aggression_rate` = (ATTACK + ADVANCE) / active ticks | rank 1 (highest) | Always closing and attacking |
| 22 | Turtle | `defend_rate` = DEFEND / active ticks | rank 1 (highest) | Absorb-first strategy |
| 23 | Zoner | `retreat_rate` = RETREAT / active ticks | rank 1 (highest) | Kiting — creates and maintains distance |

### Layer 4 — Outcome (5 assertions)

Combat result patterns across all round-robin matchups.

| # | Archetype | Metric | Expected position | Rationale |
|---|-----------|--------|------------------|-----------|
| 24 | Grappler | `ko_rate` = wins by KO / total wins | rank 1 (highest) | Burst damage — finishes enemies |
| 25 | Turtle | `avg_hp_pct_on_win` = avg HP% remaining when winning | rank 1 (highest) | Absorbs damage cleanly |
| 26 | Rushdown | `avg_ticks_on_win` = avg combat duration in won fights | rank last (shortest) | Overwhelms fast |
| 27 | Turtle | `avg_ticks_on_win` | rank 1 (longest) | Wins by attrition |
| 28 | Combo Master | `avg_stun_applied` = avg stun ticks dealt per combat | rank 1 (highest) | Lockdown identity |

---

## Known Canonical Bugs (detected by this design)

Before the tool is implemented, design analysis already reveals one inconsistency in the current canonical values:

| Bug | Current canonical | Required by assertion |
|-----|------------------|-----------------------|
| Turtle `attack_cooldown` should exceed Grappler's | Grappler=5.0, Turtle=4.0 | Turtle > Grappler (assertion #11) |
| Turtle `recovery` should exceed Grappler's | Grappler=0.4, Turtle=0.3 | Turtle > Grappler (assertion #9) |

Fixes: set Turtle `attack_cooldown` > Grappler (e.g., Turtle=5.0, Grappler≈3.5); set Turtle `recovery` > Grappler (e.g., Turtle≈0.45, Grappler≈0.35).

---

## Output Format

```
ARCHETYPE VALIDATION REPORT
══════════════════════════════════════════════════════════════════
LAYER 1 — Structural (inter-character)
  Rushdown     ✓ speed=rank1   ✓ cooldown=rank1   ✓ w_aggressiveness=rank1
  Zoner        ✓ range=rank1   ✓ knockback=rank1  ✓ w_retreat=rank1
  Combo Master ✓ stun=rank1
  Grappler     ✓ damage=rank1
  Turtle       ✓ speed=rankL   ✗ cooldown=rankL (Grappler leads)  ✓ hp=rank1  ✓ defense=rank1  ✓ w_defend=rank1  ✗ recovery=rank1 (Grappler leads)

LAYER 2 — Structural (intra-character, normalized)
  Zoner        ✓ norm(range) > norm(speed)
  Rushdown     ✓ norm(speed) > norm(range)
  Grappler     ✓ norm(hp) > norm(speed)
  Turtle       ✓ norm(defense) > norm(damage)
  Combo Master ✓ norm(stun) > norm(knockback)   ✓ norm(speed) > norm(range)

LAYER 3 — Behavioral (n=30 sims per matchup)
  Rushdown     ✓ aggression_rate=rank1
  Turtle       ✓ defend_rate=rank1
  Zoner        ✓ retreat_rate=rank1

LAYER 4 — Outcome
  Grappler     ✓ ko_rate=rank1
  Turtle       ✓ avg_hp_pct_on_win=rank1   ✓ avg_ticks_on_win=rank1
  Rushdown     ✓ avg_ticks_on_win=rankL
  Combo Master ✓ avg_stun_applied=rank1

SCORE: 26/28 (92.9%) — 2 failures
  ✗ Turtle attack_cooldown should be rank-last (highest); currently Grappler leads
  ✗ Turtle recovery should be rank-1 (highest); currently Grappler leads
══════════════════════════════════════════════════════════════════
```

---

## Data Structures

```python
@dataclass
class ArchetypeCheck:
    archetype: ArchetypeID
    layer: str          # "structural_inter", "structural_intra", "behavioral", "outcome"
    description: str    # human-readable assertion
    passed: bool
    actual_rank: int    # observed rank (1 = highest)
    expected_rank: int  # 1 or n (last)

@dataclass
class CharacterStats:
    """Aggregated simulation stats per character."""
    action_counts: Dict[int, int]   # Action → tick count
    active_ticks: int               # non-stunned ticks
    wins: int
    ko_wins: int
    hp_pct_on_wins: List[float]
    ticks_on_wins: List[int]
    stun_applied: List[int]         # stun ticks dealt per combat

@dataclass
class ArchetypeValidationReport:
    checks: List[ArchetypeCheck]
    passed: int
    total: int

    @property
    def score(self) -> float:
        return self.passed / self.total

    def failures(self) -> List[ArchetypeCheck]:
        return [c for c in self.checks if not c.passed]
```

---

## Integration Points

- **Standalone script:** `py archetype_validator.py` — validates canonical by default, prints report.
- **After GA run:** `main.py` calls `run_validation(best_individual)` and prints report alongside fitness summary.
- **No changes to fitness pipeline** — zero coupling with `fitness.py`, `ga.py`, or `operators.py`.
- **Simulation budget:** reuses `SIMS_PER_MATCHUP` from `config.py` for behavioral/outcome layers. No new config parameters needed.
