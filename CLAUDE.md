# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Instrução permanente**: sempre que qualquer decisão de design do sistema for alterada — comportamento do combate, semântica dos parâmetros, lógica do GA, ciclo de vantagens — atualize a seção **Key Design Decisions** neste arquivo antes de encerrar a tarefa. A seção deve refletir o estado atual do código, não o estado histórico.

> **Padrão de qualidade**: este é um TCC a ser apresentado para banca. O código deve ser o mais limpo possível — sem variáveis mortas, sem campos diagnósticos desnecessários, sem rastros de decisões anteriores. Prefira nomes explícitos que se auto-documentem. Quando algo for removido, remova completamente — não deixe comentários explicando que foi removido.

> **Foco no sistema, não na narrativa pra banca**: enquanto estamos refinando mecânicas, o objetivo é deixar o sistema o mais redondo possível. **Não** antecipar inline em respostas como o usuário deveria justificar X ou Y resultado para a banca — isso é prematuro enquanto há pontos a refinar. Pontos relevantes para a redação da tese vão para `docs/tcc/pontos_importantes.md`, não para discussão inline. Discutir "defensibilidade na banca" só quando o usuário pedir explicitamente.

## Project Context

TCC (undergraduate thesis) — Genetic Algorithm for competitive game character balancing.  
**Research question:** Can a GA achieve competitive balance between 5 distinct archetypes without destroying their functional identities?

The canonical archetype values are *not* hardcoded constraints — they serve as an initial population seed and as a deviation measurement baseline. The GA evolves freely; archetype deviation is penalized in the fitness via `LAMBDA_DRIFT` (and exposed as a Pareto objective in NSGA-II), but never hard-constrained. The canonical *advantage cycle* (who beats whom) is **not** encoded in any penalty — it is reported post-hoc as an evaluation metric. Forcing it would make the research question circular.

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
Tick-based 1v1 combat. Each tick: choose action via priority system → apply movement → resolve attacks simultaneously → decrement timers. Actions: ATTACK / ADVANCE / RETREAT / DEFEND. Key mechanics: `attack_cooldown` is deterministic, stun is computed as `round(attacker.stun × TICK_SCALE) − defender.recovery` (recovery is an integer in sub-ticks, subtractive — see Key Design Decisions), then capped at `STUN_CAP_MULTIPLIER × attacker_cooldown` (1× by default — stun never exceeds the attacker's own cooldown, so combo chaining is impossible). Defending reduces incoming damage by `1 - DEFEND_DAMAGE_REDUCTION` (60% reduction at 0.4). Damage is deterministic: `damage × (1 − defense)`; no per-hit variance. Timers are decremented **after** attacks — values freshly set by an attack are not decremented until the following tick, making `cooldown=1` and `stun=1` meaningful minimums. Single source of stochasticity: **soft-policy threat response** — when the enemy can hit the character (distance ≤ enemy range, enemy ready, not stunned), the action is sampled from `{ADVANCE, RETREAT, DEFEND}` with probabilities proportional to `(w_aggressiveness, w_retreat, w_defend)`. All other priority branches are deterministic.

**GA layer** (`ga.py`, `fitness.py`, `operators.py`):  
Each individual = 5 characters (one per archetype) = 60 genes total (9 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula (scalar GA): `fitness = -(LAMBDA_SPECIALIZATION × specialization_penalty + LAMBDA_DRIFT × drift_penalty + LAMBDA_DOMINANCE × dominance_penalty)`. The `specialization_penalty` uses a *specialization* metric (max−min of normalized attributes) — rewards archetype differentiation and prevents homogenization. `dominance_penalty` uses `sqrt(mean(excess_ij²))` (RMS) over the 10 pairs computed on **HP-weighted scores** rather than binary WR — KO matches contribute 1.0/0.0 like a WR, but timeout matches contribute the loser's HP-share fraction (a 55%/45% timeout enters as score≈0.55, not 1.0). The square gives extreme matchups (100/0) ~16× the weight of moderate ones (70/30). **NSGA-II** ignores all `LAMBDA_*` constants — `evaluate_objectives` returns `(dominance_penalty, drift_penalty)` raw; the Pareto front is computed in those two unweighted dimensions.

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

**Priority-based action selection** (see `_choose_action` in `combat.py`). Priorities (highest to lowest):
1. **ATTACK** — if in own range and `attack_ready`.
2. **THREAT RESPONSE** — if the enemy can hit the character now (`distance ≤ enemy.range_` AND `enemy.attack_ready` AND not stunned), choose ADVANCE/RETREAT/DEFEND probabilistically via `_threat_response` — `random.choices` weighted by `(w_aggressiveness, w_retreat, w_defend)`. This is the **soft-policy** branch: weights act continuously (a Δ in any weight produces a proportional Δ in action probability), giving the GA a continuous gradient on these genes. The previous hard-comparison form (`w_aggressiveness > w_retreat and w_aggressiveness > w_defend`) was replaced because it made weights *categorical* — only the order mattered, magnitudes were invisible to selection.
3. **ADVANCE** — if out of own range or cornered against a wall.
4. **DEFEND** — default while waiting for cooldown.

**Critical**: threat detection requires `distance ≤ enemy.range_` — a character that never successfully attacks keeps `cooldown=0` forever and would otherwise create a false perpetual-threat loop (ghost fight).

**Timer decrement order**: Decrements happen at the END of each tick (after attacks), using pre-attack timer values to decide what to decrement. Timers freshly set by an attack (`current > pre`) are preserved until the next tick. This means `stun=1` blocks the target for exactly 1 tick, and `attack_cooldown=1` forces a 1-tick wait before the next attack.

**TICK_SCALE sub-tick resolution**: All timers and movement operate in sub-tick units (TICK_SCALE=5). Any script that re-implements the combat loop **must** apply this:
- Movement per sub-tick: `speed / TICK_SCALE`
- Cooldown on hit: `round(attack_cooldown * TICK_SCALE)`
- `_resolve_attack` already returns stun in sub-tick units (handles TICK_SCALE internally)

**Three orthogonal fitness terms** (scalar GA — NSGA-II uses only the latter two, unweighted):
- `specialization_penalty` (via `LAMBDA_SPECIALIZATION=0.2`) penalizes homogeneous builds
- `drift_penalty` (via `LAMBDA_DRIFT=6.0`) penalizes deviation from canonical values — the central trade-off of the thesis. High weight to keep evolved characters near canonical baselines without hard-constraining them
- `dominance_penalty` (via `LAMBDA_DOMINANCE=1.0`) penalizes per-matchup score excess beyond `MATCHUP_THRESHOLD=0.10` (60%) using **RMS** (root mean square): `sqrt(mean(excess²))`. The square gives extreme matchups (100/0) ~16× the weight of moderate ones (70/30), preventing the GA from "hiding" a single destroyed matchup behind a balanced average. Computed over HP-weighted scores, not binary WR — stalemate timeout matches contribute their HP-share fraction so the AG sees a soft signal instead of binary noise

**Direction-blind dominance is intentional**: the penalty uses `|score − 0.5|` — it does not encode which archetype "should" win each matchup. Encoding the canonical advantage cycle into the fitness would force the GA to preserve identity, making the central research question circular. The cycle is tracked as a post-hoc evaluation metric only.

**Convergence criteria**: Two conditions must both hold (confirmed with `SIMS_CONVERGENCE_CHECK` extra simulations):
1. Each character's aggregate WR within `CONVERGENCE_THRESHOLD` of 50%
2. Every direct matchup WR within `MATCHUP_CONVERGENCE_THRESHOLD` (10%) of 50%

**Canonical calibration rules**:
- HP range: 300–500; Damage range: 10–20 — minimum ~15 hits to KO (300 HP / 20 dmg)
- All `range` values ≤ 20 < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- `attack_cooldown` ∈ [1, 5]: Rushdown=1 (fastest), Turtle=5 (slowest), Grappler=4
- `recovery` ∈ [0, 15] (integer sub-ticks): Zoner=2, Rushdown=3, CM=3, Grappler=4, Turtle=7
- Behaviors expressed via `w_*` weights (3 per character: `w_retreat`, `w_defend`, `w_aggressiveness`)
- `w_aggressiveness >= 0.7` → aggressive archetypes (Rushdown, Grappler, Combo Master) push through threats
- `w_retreat > w_defend` → reactive archetypes (Zoner) kite; `w_defend >= w_retreat` → absorbers (Turtle) hold ground

**Cooldown only on hit**: `_resolve_attack` returns `(0, 0, 0)` if `distance > attacker.range_`. The cooldown is set only inside the `if dmg > 0` block — a whiffed attack (chosen before movement changed distance) does not waste the attacker's cooldown.

**Recovery as integer subtraction**: `recovery` is stored as an integer in sub-tick units, with bounds `[0, 15]`. Each unit shaves exactly 1 sub-tick from any incoming stun: `effective_stun = max(0, raw_stun_subticks − defender.recovery)`. The previous multiplicative form `stun × (1 − recovery_float)` produced rounding plateaus in which small mutations were invisible to the AG; the additive integer form gives a visible behavior change per gene unit. Mutation operates on the float internal value; `Character.clip()` rounds genes listed in `INTEGER_ATTRIBUTES` to int after each clamp, keeping representation and combat semantics aligned.

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
| `LAMBDA_SPECIALIZATION` | 0.2 | Weight of specialization penalty (scalar GA only) |
| `LAMBDA_DRIFT` | 6.0 | Weight of archetype deviation penalty (scalar GA only — NSGA-II uses raw value) |
| `LAMBDA_DOMINANCE` | 1.0 | Weight of dominance penalty (scalar GA only) |
| `MATCHUP_THRESHOLD` | 0.10 | Score excess above 50% that starts penalizing (60% = trigger) |
| `MATCHUP_CONVERGENCE_THRESHOLD` | 0.10 | Max WR deviation per matchup to declare convergence |
| `SIMS_PER_MATCHUP` | 100 | Simulations per matchup (more = stable WR, slower; 100 → ~5% binomial std at 50% WR) |
| `SIMS_CONVERGENCE_CHECK` | 200 | Extra sims used only for convergence confirmation (high enough that ±10% per-matchup band is statistically reachable across all 10 pairs) |
| `MAX_GENERATIONS` | 100 | GA termination limit |
| `STAGNATION_LIMIT` | 50 | Generations without improvement before stopping |
| `TICK_SCALE` | 5 | Sub-tick resolution multiplier for cooldown/stun/movement |
| `STUN_CAP_MULTIPLIER` | 1.0 | Max stun = multiplier × attacker cooldown (1.0 = no combo chaining) |
| `DEFEND_DAMAGE_REDUCTION` | 0.4 | Multiplier on incoming damage when defending (40% taken = 60% reduction) |
