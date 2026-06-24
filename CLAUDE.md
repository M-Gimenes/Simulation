# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Instrução permanente (docs)**: a referência técnica detalhada vive em `docs/reference/` (índice em `docs/reference/README.md`) — um arquivo por tema (combate, AG, NSGA-II, config, tools, reprodutibilidade, known-issues, revisão do combate). O material de redação da tese fica em `docs/tcc/`. **Sempre que o código mudar, atualize o(s) `docs/reference/*.md` do tema afetado antes de encerrar a tarefa**, mantendo-os fiéis ao estado atual. Este CLAUDE.md é o guia operacional + resumo de decisões; o detalhe completo é dos docs.

> **Convenção de idioma**: nomes de arquivos e pastas em **inglês**; o **texto** dos `.md` e dos comentários pode ser em português (incl. `docs/reference/` e `docs/tcc/`).

> **Instrução permanente**: sempre que qualquer decisão de design do sistema for alterada — comportamento do combate, semântica dos parâmetros, lógica do GA, ciclo de vantagens — atualize a seção **Key Design Decisions** neste arquivo E o `docs/*.md` correspondente antes de encerrar a tarefa. Devem refletir o estado atual do código, não o histórico.

> **Padrão de qualidade**: este é um TCC a ser apresentado para banca. O código deve ser o mais limpo possível — sem variáveis mortas, sem campos diagnósticos desnecessários, sem rastros de decisões anteriores. Prefira nomes explícitos que se auto-documentem. Quando algo for removido, remova completamente — não deixe comentários explicando que foi removido.

> **Foco no sistema, não na narrativa pra banca**: enquanto estamos refinando mecânicas, o objetivo é deixar o sistema o mais redondo possível. **Não** antecipar inline em respostas como o usuário deveria justificar X ou Y resultado para a banca — isso é prematuro enquanto há pontos a refinar. Pontos relevantes para a redação da tese vão para `docs/tcc/` (destrinchado por tema — ver `docs/tcc/README.md`), não para discussão inline. Discutir "defensibilidade na banca" só quando o usuário pedir explicitamente.

## Project Context

TCC (undergraduate thesis) — Genetic Algorithm for competitive game character balancing.  
**Research question:** Can a GA achieve competitive balance between 5 distinct archetypes without destroying their functional identities?

The canonical archetype values are *not* hardcoded constraints — they serve as an initial population seed and as a deviation measurement baseline. The GA evolves freely; archetype deviation is penalized in the fitness via `LAMBDA_DRIFT` (and exposed as a Pareto objective in NSGA-II), but never hard-constrained. The canonical *advantage cycle* (who beats whom) is **not** encoded in any penalty — it is reported post-hoc as an evaluation metric. Forcing it would make the research question circular.

## Dependencies

Versões pinadas em `requirements.txt`. Para subir o ambiente:

```powershell
.\setup.ps1                 # cria .venv e instala tudo
.\setup.ps1 -Recreate       # apaga .venv existente e refaz do zero
```

Ou manualmente:

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

`numba` é usado para JIT-compilar o loop de combate (`src.engine.combat._simulate_combat_jit`) — speedup de ~150× sobre Python puro. Primeira chamada compila (~2.5s); depois fica em cache. Sem numba, o sistema não roda — `simulate_combat()` chama o JIT direto.

## Layout

```
.
├── main.py                    # entry point (GA / NSGA-II)
├── src/                       # pacote raiz (importável como `src`)
│   ├── engine/                # motor (importável como pacote `src.engine`)
│   │   ├── paths.py           # PROJECT_ROOT + paths derivados — single source
│   │   ├── config.py          # All hyperparameters
│   │   ├── archetypes.py      # canonical definitions (frozen)
│   │   ├── character.py       # gene representation
│   │   ├── individual.py      # 5 chars per individual
│   │   ├── combat.py          # tick-based simulation
│   │   ├── fitness.py         # round-robin evaluation
│   │   ├── operators.py       # selection / crossover / mutation
│   │   ├── ga.py              # scalar GA loop
│   │   └── nsga2.py           # NSGA-II loop
│   ├── tools/                 # ferramentas que consomem o motor
│   │   ├── report.py          # dossiê do indivíduo (compõe os tools abaixo)
│   │   ├── analyze_matchups.py
│   │   ├── drift_table.py     # drift por gene + diferenciação
│   │   ├── fingerprint.py     # assinatura comportamental por personagem
│   │   ├── archetype_validator.py
│   │   ├── sensitivity_analysis.py
│   │   ├── viewer.py          # ASCII viewer
│   │   ├── web_viewer.py      # browser viewer
│   │   └── nsga2_plots.py     # Pareto plots
│   └── tests/                 # smoke tests
└── results/                   # outputs (gitignored content é o que importa)
```

> **Convenção de imports**: dentro de `src/engine/` use relativos (`from .combat import ...`); fora dele (em `main.py`, `src/tools/`, `src/tests/`) use absolutos a partir do motor (`from src.engine.combat import ...`). Tools/tests referenciam umas às outras também por caminho absoluto (`from src.tools.archetype_validator import ...`).
> **Convenção de paths**: nunca hardcode strings. Importe os constants de `src.engine.paths` (`PROJECT_ROOT`, `RESULTS_DIR`, `GA_RESULTS_PATH`, `NSGA2_RESULTS_PATH`, `NSGA2_PLOTS_DIR`). Eles são derivados de `Path(__file__).parent.parent.parent` — funcionam independente do cwd.

## Running

Tudo roda a partir da raiz do projeto. Scripts em `src/tools/` e `src/tests/` são executados como módulo (`-m`) para que `src` esteja no path.

```bash
# Full GA run
py main.py
py main.py --algorithm nsga2 --seed 42 --quiet

# Analysis tools
py -m src.tools.report --evolved                 # dossiê completo do indivíduo (porta de entrada)
py -m src.tools.analyze_matchups                 # all matchups, canonical (default 1000 sims)
py -m src.tools.analyze_matchups rushdown zoner  # specific matchup
py -m src.tools.drift_table --evolved            # drift por gene + diferenciação
py -m src.tools.fingerprint --evolved            # assinatura comportamental
py -m src.tools.archetype_validator              # structural identity checks
py -m src.tools.sensitivity_analysis             # ±σ Δ-WR per gene

# Web viewer (opens browser at localhost:8080)
py -m src.tools.web_viewer

# Smoke tests (run individually — no test runner configured)
py -m src.tests.test_base
py -m src.tests.test_combat
py -m src.tests.test_fitness
py -m src.tests.test_operators
py -m src.tests.test_nsga2
py -m src.tests.test_archetype_validator
```

> **Windows note:** Use `py` não `python`/`python3`. Scripts output Unicode (box-drawing); via bash pipe use `PYTHONIOENCODING=utf-8` ou passe `--quiet`.

## Output Files

All GA/NSGA-II outputs go to `results/` (created automatically on first run):

| File | Source |
|---|---|
| `results/results.json` | `py main.py` (GA) |
| `results/nsga2_results.json` | `py main.py --algorithm nsga2` |
| `results/plots/nsga2/<timestamp>/` | NSGA-II projection plots |

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`src/engine/combat.py`):  
Tick-based 1v1 combat. Each tick: choose action via priority system → apply movement → resolve attacks simultaneously → decrement timers. Actions: ATTACK / ADVANCE / RETREAT / DEFEND. Key mechanics: `attack_cooldown` is deterministic, stun is computed as `round(attacker.stun × TICK_SCALE) − defender.recovery` (recovery is an integer in sub-ticks, subtractive — see Key Design Decisions), then capped at `STUN_CAP_MULTIPLIER × attacker_cooldown` (0.6 by default — stun é estritamente menor que o cooldown do atacante, garantindo uma janela livre entre hits para o defensor agir). Defending reduces incoming damage by `1 - DEFEND_DAMAGE_REDUCTION` (60% reduction at 0.4). Damage is deterministic: `damage × (1 − defense)`; no per-hit variance. Timers are decremented **after** attacks — values freshly set by an attack are not decremented until the following tick, making `cooldown=1` and `stun=1` meaningful minimums. Stochasticity has two sources: (1) **soft-policy commitment** — when the character is within its own range but the cooldown is not ready, the action is sampled from `{ADVANCE, RETREAT, DEFEND}` with probabilities proportional to `(w_aggressiveness, w_retreat, w_defend)` and **held for `ACTION_PERSISTENCE_SUBTICKS` sub-ticks** before re-rolling (commitment/momentum). (2) **hesitation** (`HESITATION_RATE`) — each tick, with that probability, even a deterministic ATTACK/ADVANCE branch instead samples the same weighted distribution, modeling player execution variance (weighted, not uniform, so it respects archetype identity). `HESITATION_RATE=0` reproduces the no-hesitation combat. Reproducibility: combat RNG is Numba-internal; seed it only via `seed_combat()` (`np.random.seed` from Python does nothing).

**GA layer** (`src/engine/ga.py`, `src/engine/fitness.py`, `src/engine/operators.py`):  
Each individual = 5 characters (one per archetype) = 60 genes total (9 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula (scalar GA): `fitness = -(LAMBDA_DRIFT × drift_penalty + LAMBDA_DOMINANCE × dominance_penalty)` — the **same two terms the NSGA-II optimizes**, here as a weighted sum (scalar GA = one point of the trade-off NSGA-II maps). `drift_penalty` is the mean per-character normalized euclidean distance to the canonical profile (identity preservation, and the real anti-homogenization mechanism). `dominance_penalty` is the RMS over the 10 pairs of `e = DOMINANCE_WR_WEIGHT·wr_excess + DOMINANCE_DECIS_WEIGHT·decis_excess`. **Primary term** `wr_excess = |WR − 0.5| / 0.5` (continuous WR imbalance, no dead band) — the real balancing objective. **Secondary term** `decis_excess` = per-fight decisiveness `D = mean(|score − 0.5|)` outside the healthy band `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]` = [0.05, 0.10] (winner closes ~10-20% HP); per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The secondary term guards against blowout-coinflip (55% A-crush / 45% B-crush, WR ~50% but every fight a blowout — which the WR term alone misses). The WR term exists because decisiveness alone is **blind to win frequency**: a 100%×0% matchup closing each fight at ~15% HP gives `D ≈ 0.075` (in-band) → zero penalty despite 100% WR (the "tight fight ⟹ WR ~50%" hypothesis, falsified — see `docs/reference/11-combat-review.md`). **NSGA-II** ignores all `LAMBDA_*` constants — `evaluate_objectives` returns `(dominance_penalty, drift_penalty)` raw; the Pareto front is computed in those two unweighted dimensions.

**Data model** (`src/engine/archetypes.py` → `src/engine/character.py` → `src/engine/individual.py`):  
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

**Priority-based action selection** (definido inline em `_simulate_combat_jit` / `_simulate_combat_traced_jit`). Priorities (highest to lowest):
1. **ATTACK** — if in own range and `attack_ready`. Clears any pending soft-policy commitment.
2. **ADVANCE** — if out of own range OR cornered against a wall. Clears any pending soft-policy commitment.
3. **HELD COMMITMENT** — if a previous soft-policy choice is still within its persistence window (`commitment_remaining > 0`), repeat it and decrement the counter.
4. **NEW SOFT POLICY** — sample one of `{ADVANCE, RETREAT, DEFEND}` via `random.choices` weighted by `(w_aggressiveness, w_retreat, w_defend)`, store it as the committed action, and reset the counter to `ACTION_PERSISTENCE_SUBTICKS`.

The soft-policy branch (3 + 4) is the only stochastic node in the loop. Weights act continuously: a Δ in any weight produces a proportional Δ in action probability, giving the GA a continuous gradient on these genes. The previous hard-comparison form (`w_aggressiveness > w_retreat and w_aggressiveness > w_defend`) made weights *categorical* — only the order mattered, magnitudes were invisible to selection.

**Action persistence** (`ACTION_PERSISTENCE_SUBTICKS = 10`): once a soft-policy action is sampled, it is reused for the next 10 sub-ticks instead of resampling every sub-tick. This simulates commitment/momentum and prevents pathological flip-flopping — without it, the character would re-roll RETREAT/DEFEND/ADVANCE 5× per logical tick. The commitment is broken whenever a higher-priority branch fires (in own range + ready → ATTACK, or out of range / cornered → ADVANCE).

**Timer decrement order**: Decrements happen at the END of each tick (after attacks), using pre-attack timer values to decide what to decrement. Timers freshly set by an attack (`current > pre`) are preserved until the next tick. This means `stun=1` blocks the target for exactly 1 tick, and `attack_cooldown=1` forces a 1-tick wait before the next attack.

**TICK_SCALE sub-tick resolution**: All timers and movement operate in sub-tick units (TICK_SCALE=5):
- Movement per sub-tick: `speed / TICK_SCALE`
- Cooldown on hit: `round(attack_cooldown * TICK_SCALE)`
- Stun on hit: `round(attacker.stun * TICK_SCALE) − defender.recovery`, capped at `STUN_CAP_MULTIPLIER × attack_cooldown × TICK_SCALE`

Toda a lógica de combate vive **exclusivamente** dentro do JIT (`_simulate_combat_jit` para o fitness, `_simulate_combat_traced_jit` para tools). Não há reimplementação Python do loop — tools que precisam instrumentar consomem `CombatTrace` em vez de redobrar a lógica.

**Two fitness terms** = the thesis's two axes: identity (`drift_penalty`) and balance (`dominance_penalty`). Scalar GA = weighted sum; NSGA-II = same two as unweighted Pareto objectives — the scalar GA is one point of the trade-off NSGA-II maps. (Homogenization — "are the 5 still distinct?" — is a post-hoc metric, not a fitness term, by the same non-circularity logic as the cycle.)
- `drift_penalty` (via `LAMBDA_DRIFT=1.0`, equal to dominance) penalizes deviation from canonical values — the central trade-off of the thesis, and the real anti-homogenization mechanism. (Was 6.0, which pinned the GA to canonical and prevented balancing — see `docs/reference/10-known-issues.md` V1.)
- `dominance_penalty` (via `LAMBDA_DOMINANCE=1.0`) is the **RMS** over the 10 pairs of `e = DOMINANCE_WR_WEIGHT·wr_excess + DOMINANCE_DECIS_WEIGHT·decis_excess`. **Primary** `wr_excess = |WR − 0.5| / 0.5` (continuous WR imbalance, no dead band) — the real balancing objective, with a smooth gradient down to 50%. **Secondary** `decis_excess` = per-fight decisiveness `D = mean(|score − 0.5|)` outside the band `[MATCHUP_FLOOR, MATCHUP_THRESHOLD] = [0.05, 0.10]` (winner closes ~10-20% HP); per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The decisiveness term guards against blowout-coinflip (55%/45% crush each way, WR ~50% but every fight a blowout — the WR term alone misses this) and keeps fight *quality* in scope. The WR term is primary because decisiveness alone is **blind to win frequency**: a 100%×0% matchup closing each fight at ~15% HP gives `D ≈ 0.075` (in-band) → zero penalty despite 100% WR. The "tight fight ⟹ WR ~50%" hypothesis was **falsified** empirically (old `best_dominance`: 10/10 fights in-band but 0/10 matchups balanced); WR was brought back as primary. The graded WR that makes this a usable gradient comes from soft-policy/hesitation noise once fights are close (see `docs/reference/11-combat-review.md`).

**Direction-blind dominance is intentional**: the penalty uses `|WR − 0.5|` and `|score − 0.5|` — it does not encode which archetype "should" win each matchup. Encoding the canonical advantage cycle into the fitness would force the GA to preserve identity, making the central research question circular. The cycle is tracked as a post-hoc evaluation metric only.

**Convergence criteria**: Two conditions must both hold (confirmed with `SIMS_CONVERGENCE_CHECK` extra simulations):
1. Each character's aggregate WR within `CONVERGENCE_THRESHOLD` of 50%
2. Every direct matchup WR within `MATCHUP_CONVERGENCE_THRESHOLD` (10%) of 50%

**Canonical calibration rules**:
- HP range: 300–400; Damage range: 10–20 — minimum ~15 hits to KO (300 HP / 20 dmg). Bounds apertados (era 500) eliminam "tanque acima do Turtle" como espaço de exploit do AG; canônicos: Zoner=300, Rush=320, CM=350, Grap=380, Turtle=400
- All `range` values ≤ 20 < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- `attack_cooldown` ∈ [1, 5]: Rushdown=1 (fastest), Turtle=5 (slowest), Grappler=4
- `defense` ∈ [0, 0.30] (era 0.5): teto colado em Turtle (0.25) + headroom mínimo, evita evolução de defesa absurda
- `knockback` ∈ [0, 3] (era 5): teto razoável acima do Zoner (2), evita zoning trivial via expulsão de range
- `recovery` ∈ [0, 10] (era 15, integer sub-ticks): Zoner=2, Rushdown=3, CM=3, Grappler=4, Turtle=7. Teto reduzido evita "stun-immunity" via recovery alta
- Behaviors expressed via `w_*` weights (3 per character: `w_retreat`, `w_defend`, `w_aggressiveness`)
- `w_aggressiveness >= 0.7` → aggressive archetypes (Rushdown, Grappler, Combo Master) push through threats
- `w_retreat > w_defend` → reactive archetypes (Zoner) kite; `w_defend >= w_retreat` → absorbers (Turtle) hold ground

**Cooldown only on hit**: o JIT só seta o cooldown do atacante dentro do bloco `if dmg > 0.0` (i.e. quando há dano efetivo). Um ataque que sai mas sai fora de range (a distância pode ter mudado depois do movimento daquele tick) não desperdiça cooldown.

**Recovery as integer subtraction**: `recovery` is stored as an integer in sub-tick units, with bounds `[0, 10]`. Each unit shaves exactly 1 sub-tick from any incoming stun: `effective_stun = max(0, raw_stun_subticks − defender.recovery)`. The previous multiplicative form `stun × (1 − recovery_float)` produced rounding plateaus in which small mutations were invisible to the AG; the additive integer form gives a visible behavior change per gene unit. Mutation operates on the float internal value; `Character.clip()` rounds genes listed in `INTEGER_ATTRIBUTES` to int after each clamp, keeping representation and combat semantics aligned.

## Quick Matchup Check

```bash
py -m src.tools.report --evolved              # dossiê completo do indivíduo (porta de entrada)
py -m src.tools.analyze_matchups --evolved    # só os matchups
py -m src.tools.drift_table --evolved         # só o drift por gene + diferenciação
py -m src.tools.fingerprint --evolved         # só o comportamento
py -m src.tools.analyze_matchups rushdown zoner --n 100   # par específico
```

## Hyperparameters

Todos em `src/engine/config.py`. **Tabela completa e comentada em
[`docs/reference/07-configuration.md`](docs/reference/07-configuration.md)** — manter lá, não duplicar
aqui. Os mais ajustados ao refinar: `LAMBDA_DRIFT` / `LAMBDA_DOMINANCE` (trade-off
do escalar — hoje 1.0 / 1.0), `DOMINANCE_WR_WEIGHT` / `DOMINANCE_DECIS_WEIGHT`
(peso WR-primário vs decisividade-secundária dentro do dominance — hoje 1.0 / 0.5),
`MATCHUP_THRESHOLD` / `MATCHUP_FLOOR` (banda de decisividade), `HESITATION_RATE`
(variância de player — provisória, a calibrar), `SIMS_PER_MATCHUP`,
`MAX_GENERATIONS` / `STAGNATION_LIMIT`.
