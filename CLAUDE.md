# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Instrução permanente**: sempre que qualquer decisão de design do sistema for alterada — comportamento do combate, semântica dos parâmetros, lógica do GA, ciclo de vantagens — atualize a seção **Key Design Decisions** neste arquivo antes de encerrar a tarefa. A seção deve refletir o estado atual do código, não o estado histórico.

## Project Context

TCC (undergraduate thesis) — Genetic Algorithm for competitive game character balancing.  
**Research question:** Can a GA achieve competitive balance between 5 distinct archetypes without destroying their functional identities?

The canonical archetype values are *not* hardcoded constraints — they serve as an initial population seed and as a deviation measurement baseline. The GA evolves freely; archetype preservation is measured post-hoc via `LAMBDA_DRIFT`.

## Dependencies

Only external package required: `pip install matplotlib`  
Everything else is Python stdlib + project modules.

## File Map

| File | Role |
|---|---|
| `config.py` | All hyperparameters — single source of truth |
| `combat.py` | Tick-based simulation engine |
| `archetypes.py` | Canonical archetype definitions (frozen) |
| `character.py` / `individual.py` | Gene representation |
| `fitness.py` | Round-robin evaluation + fitness formula |
| `operators.py` | Selection, crossover, mutation, NSGA-II tournament |
| `ga.py` | GA main loop |
| `nsga2.py` / `nsga2_plots.py` | NSGA-II algorithm + Pareto plots |
| `map_elites.py` | Maps balance×drift trade-off space, suggests LAMBDA values |
| `analyze_matchups.py` | Averaged matchup diagnostics (N sims, mean stats) |
| `archetype_validator.py` | 20 structural assertions on archetype identity |
| `web_viewer.py` / `viewer.py` | Browser and terminal combat visualizers |

## Running

```bash
# Full GA run
py main.py
py main.py --algorithm nsga2 --seed 42 --quiet

# Analysis tools
py analyze_matchups.py                    # all matchups, canonical, 30 sims each
py analyze_matchups.py rushdown zoner     # specific matchup
py analyze_matchups.py --evolved --n 50  # evolved individual, 50 sims
py archetype_validator.py                 # structural identity checks

# Web viewer (opens browser at localhost:8080)
py web_viewer.py

# Smoke tests (run individually — no test runner configured)
py test_base.py
py test_combat.py
py test_fitness.py
py test_operators.py
py test_nsga2.py
py test_archetype_validator.py
py test_map_elites.py
```

> **Windows note:** Use `py` not `python` or `python3`. Scripts output Unicode (box-drawing chars); if running through bash pipe use `PYTHONIOENCODING=utf-8` or pass `--quiet`.

## Output Files

All GA/NSGA-II outputs go to `results/` (created automatically on first run):

| File | Source |
|---|---|
| `results/results.json` | `py main.py` (GA) |
| `results/nsga2_results.json` | `py main.py --algorithm nsga2` |
| `results/plots/nsga2/<timestamp>/` | NSGA-II projection plots |

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`combat.py`):  
Tick-based 1v1 combat. Each tick: choose action via priority system → apply movement → resolve attacks simultaneously → decrement timers. Actions: ATTACK / ADVANCE / RETREAT / DEFEND. Key mechanics: `attack_cooldown` is deterministic, stun is capped at `STUN_CAP_MULTIPLIER × attacker_cooldown` (2× by default — allows 1 follow-up hit, enabling combo chaining). Timers are decremented **after** attacks — values freshly set by an attack are not decremented until the following tick, making `cooldown=1` and `stun=1` meaningful minimums. Two sources of stochasticity: `DAMAGE_VARIANCE=0.20` (±20% per hit) and `ACTION_EPSILON=0.20` (20% chance of random action per tick, modelling execution errors).

**GA layer** (`ga.py`, `fitness.py`, `operators.py`):  
Each individual = 5 characters (one per archetype) = 60 genes total (9 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula: `(1 - balance_error) - LAMBDA * attribute_cost - LAMBDA_DRIFT * drift_penalty - LAMBDA_MATCHUP * matchup_dominance_penalty`. The `attribute_cost` term uses a *specialization* metric (max−min of normalized attributes) — rewards archetype differentiation and prevents homogenization. `matchup_dominance_penalty` uses `mean(excess_ij)` over the 10 pairs — all unbalanced matchups contribute, giving the GA gradient signal to fix any bad pair.

**Data model** (`archetypes.py` → `character.py` → `individual.py`):  
`ArchetypeDefinition` (frozen, canonical values) → `Character` (mutable genes, 9 attrs + 3 weights) → `Individual` (list of 5 Characters + fitness cache). `Individual.from_canonical()` creates the canonical seed; `Individual.random()` creates a random individual.

## Canonical Advantage Cycle

| Vencedor | Perdedor | Motivo FGC |
|---|---|---|
| Rushdown | Zoner | pressão não deixa iniciar setup |
| Rushdown | Combo Master | pressão antes do setup de combo |
| Zoner | Grappler | controla espaço, fica fora da zona de punição |
| Zoner | Turtle | fica fora da zona de punição da Turtle |
| Grappler | Rushdown | grab/burst pune fuga e combos rápidos |
| Grappler | Turtle | grab é o counter canônico ao bloqueio |
| Combo Master | Grappler | Grappler lento morre pra combo |
| Combo Master | Zoner | burst converte um acerto em match |
| Turtle | Rushdown | bloqueio absorve pressão agressiva |
| Turtle | Combo Master | bloqueio quebra setup de combo |

## Key Design Decisions

**Priority-based action selection**: Deterministic strategy modelling an experienced player. Priorities (highest to lowest): (1) ATTACK if in range and ready; (2) respond to threat — enemy must be **within their own attack range** (`distance ≤ enemy.range_`) AND ready: if `w_aggressiveness > w_retreat and w_aggressiveness > w_defend` → ADVANCE; else if `w_retreat > w_defend` → RETREAT; else → DEFEND; (3) ADVANCE if out of range or cornered; (4) DEFEND (default while waiting for cooldown). The `w_*` weights compete symmetrically — no hardcoded thresholds, giving the GA a continuous fitness landscape. **Critical**: threat detection requires `distance ≤ enemy.range_` — a character that never successfully attacks keeps `cooldown=0` forever and would otherwise create a false perpetual-threat loop (ghost fight).

**Timer decrement order**: Decrements happen at the END of each tick (after attacks), using pre-attack timer values to decide what to decrement. Timers freshly set by an attack (`current > pre`) are preserved until the next tick. This means `stun=1` blocks the target for exactly 1 tick, and `attack_cooldown=1` forces a 1-tick wait before the next attack.

**TICK_SCALE sub-tick resolution**: All timers and movement operate in sub-tick units (TICK_SCALE=5). Any script that re-implements the combat loop **must** apply this:
- Movement per sub-tick: `speed / TICK_SCALE`
- Cooldown on hit: `round(attack_cooldown * TICK_SCALE)`
- `_resolve_attack` already returns stun in sub-tick units (handles TICK_SCALE internally)

**Attribute cost vs. drift penalty vs. matchup penalty**: Three orthogonal fitness terms:
- `attribute_cost` (via `LAMBDA=0.2`) penalizes homogeneous builds
- `drift_penalty` (via `LAMBDA_DRIFT=0.0`) penalizes deviation from canonical values — the central trade-off of the thesis
- `matchup_dominance_penalty` (via `LAMBDA_MATCHUP=1`) penalizes mean WR excess across all pairs beyond `MATCHUP_THRESHOLD=0.10` (60%)

**Convergence criteria**: Two conditions must both hold (confirmed with `SIMS_CONVERGENCE_CHECK` extra simulations):
1. Each character's aggregate WR within `CONVERGENCE_THRESHOLD` of 50%
2. Every direct matchup WR within `MATCHUP_CONVERGENCE_THRESHOLD` (10%) of 50%

**Canonical calibration rules**:
- HP range: 300–500; Damage range: 10–20 — minimum ~15 hits to KO (300 HP / 20 dmg)
- All `range` values ≤ 20 < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- `attack_cooldown` ∈ [1, 5]: Rushdown=1 (fastest), Turtle=5 (slowest), Grappler=4
- Behaviors expressed via `w_*` weights (3 per character: `w_retreat`, `w_defend`, `w_aggressiveness`)
- `w_aggressiveness >= 0.7` → aggressive archetypes (Rushdown, Grappler, Combo Master) push through threats
- `w_retreat > w_defend` → reactive archetypes (Zoner) kite; `w_defend >= w_retreat` → absorbers (Turtle) hold ground

**Cooldown only on hit**: `_resolve_attack` returns `(0, 0, 0)` if `distance > attacker.range_`. The cooldown is set only inside the `if dmg > 0` block — a whiffed attack (chosen before movement changed distance) does not waste the attacker's cooldown.

## Quick Matchup Check

```bash
py analyze_matchups.py              # all 10 matchups, canonical, 30 sims
py analyze_matchups.py --evolved    # evolved individual
py analyze_matchups.py rushdown zoner --n 100   # specific pair, high precision
```

## All Hyperparameters

Located in `config.py`. Commonly adjusted:

| Parameter | Value | Effect |
|---|---|---|
| `LAMBDA` | 0.2 | Weight of specialization penalty in fitness |
| `LAMBDA_DRIFT` | 0.0 | Weight of archetype deviation penalty (0 = free evolution) |
| `LAMBDA_MATCHUP` | 1.0 | Weight of mean matchup dominance penalty |
| `MATCHUP_THRESHOLD` | 0.10 | WR excess above 50% that starts penalizing (60% = trigger) |
| `MATCHUP_CONVERGENCE_THRESHOLD` | 0.10 | Max WR deviation per matchup to declare convergence (60%) |
| `SIMS_PER_MATCHUP` | 30 | Simulations per matchup (more = stable WR, slower) |
| `SIMS_CONVERGENCE_CHECK` | 50 | Extra sims used only for convergence confirmation |
| `MAX_GENERATIONS` | 100 | GA termination limit |
| `STAGNATION_LIMIT` | 50 | Generations without improvement before stopping |
| `TICK_SCALE` | 5 | Sub-tick resolution multiplier for cooldown/stun/movement |
| `STUN_CAP_MULTIPLIER` | 2.0 | Max stun = multiplier × attacker cooldown |
| `DAMAGE_VARIANCE` | 0.20 | ±20% per-hit damage roll — execution variance |
| `ACTION_EPSILON` | 0.20 | Probability of random action per tick — decision error |
