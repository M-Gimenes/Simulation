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

`numba` é usado para JIT-compilar o loop de combate (`src.engine.combat._simulate_combat_jit`) — speedup de ~150× sobre Python puro. Primeira chamada compila (~2.5s); depois fica em cache. Sem numba, o sistema não roda — `simulate_combat()` chama o JIT direto. `scipy` entra só no `src.tools.compare_algorithms` (Mann-Whitney U); o motor não depende dele.

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
│   │   ├── nsga2.py           # NSGA-II loop
│   │   └── pareto_metrics.py  # hipervolume + spacing da fronteira (metodologia 1.2)
│   ├── tools/                 # ferramentas que consomem o motor
│   │   ├── report.py          # dossiê do indivíduo (compõe os tools abaixo)
│   │   ├── analyze_matchups.py
│   │   ├── drift_table.py     # drift por gene + diferenciação
│   │   ├── fingerprint.py     # assinatura comportamental por personagem
│   │   ├── archetype_validator.py
│   │   ├── sensitivity_analysis.py
│   │   ├── multi_run.py       # N execuções + estatística agregada (metodologia 1.1)
│   │   ├── compare_algorithms.py   # AG × NSGA-II: Mann-Whitney U + Â₁₂ + Holm
│   │   ├── external_validation.py  # robustez do equilíbrio fora do laço (metodologia 3.2)
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
py -m src.tools.archetype_validator              # identity checks: structural (L1-2) + behavioral (L3)
py -m src.tools.sensitivity_analysis             # ±σ Δ-WR per gene
py -m src.tools.multi_run --algorithm both       # N execuções + estatística agregada (metodologia 1.1)
py -m src.tools.compare_algorithms               # AG × NSGA-II: Mann-Whitney U + Â₁₂ + Holm
py -m src.tools.external_validation --nsga2 best_dominance  # robustez do equilíbrio fora do laço (metodologia 3.2)

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
| `results/multi_run/multi_run_<algo>.json` | `py -m src.tools.multi_run` (estatística agregada de N execuções) |
| `results/multi_run/comparison_ga_vs_nsga2.json` | `py -m src.tools.compare_algorithms` (teste estatístico entre os dois algoritmos) |
| `results/external_validation/external_validation_<label>.json` | `py -m src.tools.external_validation` (robustez do equilíbrio fora do laço) |
| `results/sensitivity/sensitivity_analysis.json` | `py -m src.tools.sensitivity_analysis` (matriz Δ WR por gene) |

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`src/engine/combat.py`):  
Tick-based 1v1 combat. Each tick: choose **stance** via intention → apply simultaneous movement (with collision) → resolve attacks → decrement timers. **Two action channels:** the sampled intention governs only the *stance* (ADVANCE / RETREAT / DEFEND), while the *attack* is a resolution rule — it fires whenever cooldown is ready, the opponent is within range (post-movement) and the stance is not DEFEND. Advancing and retreating both hit; only GUARDA gives up the blow. That is what makes space control a strategy (zoning = attacking while holding distance) and what gives `knockback` a positive slope. **Intention:** sampled from `{FRENTE, RECUAR, GUARDA}` proportional to `(w_aggressiveness, w_retreat, w_defend)` and **held for `ACTION_PERSISTENCE_SUBTICKS` sub-ticks** (commitment/momentum); FRENTE → ADVANCE, RECUAR → RETREAT if there is room else DEFEND (cornered), GUARDA → DEFEND. The intention always applies, **except in an impasse** (`distance > own range` AND `distance > opponent's range`), where ADVANCE is imposed — without it two passive characters back off to opposite walls and time out without a blow. The intention sampling is the **single source of stochasticity**. Key mechanics: bodies **do not pass through each other** (`_apply_movement` moves both from the start-of-sub-tick positions and stops them at the meeting point; A is always the left side); `attack_cooldown` is deterministic; **stun = `stun × attack_cooldown × TICK_SCALE`**, a **continuous** timer — `stun` is a gene in `[0, 0.6]` expressing a **fraction of the attacker's own cooldown** (in sub-ticks); since the bound is `< 1.0`, applied stun is always strictly less than the cooldown, guaranteeing a free window for the defender (no explicit `STUN_CAP_MULTIPLIER`). Damage is **flat** (`damage`); the only modifier is the target's DEFEND, which multiplies incoming damage by `DEFEND_DAMAGE_REDUCTION` (0.6 = `1 − 0.4` → 40% reduction). There is **no `defense` gene** and **no `recovery` gene**. A fight ends in KO, timeout (higher HP%) or **draw** (`winner = -1`, identical HP% — double KO or a timeout with no difference), which counts as half a win for each side. Timers are decremented **after** attacks — values freshly set by an attack are not decremented until the following tick. Reproducibility: combat RNG is Numba-internal; seed it only via `seed_combat()` (`np.random.seed` from Python does nothing).

**GA layer** (`src/engine/ga.py`, `src/engine/fitness.py`, `src/engine/operators.py`):  
Each individual = 5 characters (one per archetype) = 50 genes total (7 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula (scalar GA): `fitness = -(LAMBDA_DRIFT × drift_penalty + LAMBDA_DOMINANCE × dominance_penalty)` — the **same two terms the NSGA-II optimizes**, here as a weighted sum (scalar GA = one point of the trade-off NSGA-II maps). `drift_penalty` is the mean per-character normalized euclidean distance to the canonical profile (over the 10 genes; identity preservation, and the real anti-homogenization mechanism). `dominance_penalty` (**C2 formulation**) is `DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term` (max 2.0). **Primary term** `global_term = RMS over the 5 characters of |WR_global − 0.5| / 0.5` — *no archetype globally dominates the roster*. It does **not** force every pair to 50%: a character at 50% global can beat 2 and lose 2 — the space where the advantage cycle can live. (The old primary was per-matchup WR, whose optimum is *every pair at 50%* = flat balance, incompatible with a cycle by construction.) **Secondary `cap_term`** = RMS over the 10 pairs of the excess of `|WR_par − 0.5|` above `MATCHUP_WR_CAP` (hard-counter ceiling: keeps cycle edges as advantages within `[0.35, 0.65]`, bars crushing counters like 100×0). **Secondary `decis_term`** = RMS over the 10 pairs of per-fight decisiveness `D = mean(|score − 0.5|)` outside the healthy band `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]` = [0.10, 0.20] (winner closes ~20-40% HP); per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The decisiveness term guards against blowout-coinflip (55% A-crush / 45% B-crush, global WR ~50% but every fight a blowout). **NSGA-II** ignores all `LAMBDA_*` constants — `evaluate_objectives` returns `(dominance_penalty, drift_penalty)` raw; the Pareto front is computed in those two unweighted dimensions.

**Data model** (`src/engine/archetypes.py` → `src/engine/character.py` → `src/engine/individual.py`):  
`ArchetypeDefinition` (frozen, canonical values) → `Character` (mutable genes, 7 attrs + 3 weights) → `Individual` (list of 5 Characters + fitness cache). `Individual.from_canonical()` creates the canonical seed; `Individual.random()` creates a random individual.

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

**Two action channels: stance is chosen, attack is a rule.** Three shared `@njit` helpers — `_decide_action` (stance), `_apply_movement` (movement + collision) and `_decide_winner` (outcome) — are called by A and B in both JIT variants, so fitness and traced simulate exactly the same combat; covered by a parity test in `test_combat`. A stunned character loses the sub-tick (`stun_rem > 0` → stance = −1) and cannot attack.

- **Phase 1 — Intention.** With no active intention (`persist == 0`), **sample** one of `{FRENTE, RECUAR, GUARDA}` via `np.random.random()` weighted by `(w_aggressiveness, w_retreat, w_defend)` and hold it for `ACTION_PERSISTENCE_SUBTICKS` sub-ticks. Weights summing to 0 → GUARDA (fallback). The intention always applies **except in an impasse** — `distance > own range` AND `distance > opponent's range`, where nobody can reach anybody — which imposes ADVANCE and zeroes the counter. A character under threat (the opponent does reach) stays free to retreat, so kiting is untouched and the rule is not exploitable.
- **Phase 2 — Stance.** FRENTE → **ADVANCE**; RECUAR → **RETREAT** if there is room to back off else **DEFEND** (cornered); GUARDA → **DEFEND**.
- **Attack channel.** Fires at resolution when `stance ≥ 0 and stance ≠ DEFEND and cd_rem == 0 and distance ≤ range`, using the post-movement distance. There is no "whiff" and no wasted cooldown. Advancing and retreating both hit; only GUARDA abdicates the blow.

The intention sampling is the **only** stochastic node in the loop. Weights act continuously: a Δ in any weight produces a proportional Δ in intention probability, giving the GA a continuous gradient on these genes. Because sampling is proportional, only the **ratio** between the three weights affects behaviour — the drift term still measures their absolute values (open item in `REVIEW.md` §5).

**Intention persistence** (`ACTION_PERSISTENCE_SUBTICKS = 10`): once sampled, an intention is reused for the next 10 sub-ticks instead of resampling every sub-tick. This simulates commitment/momentum and prevents pathological flip-flopping. The intention is **never interrupted mid-window**, except by the impasse rule (which forces ADVANCE and zeroes the counter) or by being stunned.

**Collision and cornering.** Bodies do not pass through each other: `_apply_movement` displaces both from the start-of-sub-tick positions (simultaneous — neither side arrives "first") and, when two advances would cross, both stop at the meeting point. A is therefore always the left side (`pos_a ≤ pos_b`), which removes the direction edge cases at distance zero. Cornering exists as a consequence — RETREAT backs off to the wall and falls to DEFEND — and `CombatTrace.forced_defend` keeps that forced DEFEND separate from the chosen one (GUARDA), so geometry does not contaminate the defensive-identity metric.

**Timer decrement order**: Decrements happen at the END of each tick (after attacks), using pre-attack timer values to decide what to decrement. Timers freshly set by an attack (`current > pre`) are preserved until the next tick. This means `stun=1` blocks the target for exactly 1 tick, and `attack_cooldown=1` forces a 1-tick wait before the next attack.

**TICK_SCALE sub-tick resolution**: All timers and movement operate in sub-tick units (TICK_SCALE=5):
- Movement per sub-tick: `speed / TICK_SCALE`
- Cooldown on hit: `round(attack_cooldown * TICK_SCALE)` — integer
- Stun on hit: `stun * attack_cooldown * TICK_SCALE` — **continuous** (float timer, decremented by 1.0 per sub-tick). `stun ∈ [0, 0.6]` is a fraction of the attacker's own cooldown in sub-ticks; the bound `< 1.0` guarantees applied stun < cooldown (no explicit cap constant). Rounding it used to leave the gene with only 4 effective levels for a `cooldown = 1` attacker.

Toda a lógica de combate vive **exclusivamente** dentro do JIT (`_simulate_combat_jit` para o fitness, `_simulate_combat_traced_jit` para tools), com **postura, movimento e desfecho compartilhados** nos helpers `_decide_action`, `_apply_movement` e `_decide_winner` (chamados por A e B nas duas variantes — sem cópias divergentes). Não há reimplementação Python do loop — tools que precisam instrumentar consomem `CombatTrace` em vez de redobrar a lógica. O `CombatTrace` expõe `stance`, `attacked` (canal de ataque) e `forced_defend` (1 = DEFEND por encurralamento, distinto do GUARDA escolhido) para a separação de identidade defensiva.

**Two fitness terms** = the thesis's two axes: identity (`drift_penalty`) and balance (`dominance_penalty`). Scalar GA = weighted sum; NSGA-II = same two as unweighted Pareto objectives — the scalar GA is one point of the trade-off NSGA-II maps. (Homogenization — "are the 5 still distinct?" — is a post-hoc metric, not a fitness term, by the same non-circularity logic as the cycle.)
- `drift_penalty` (via `LAMBDA_DRIFT=1.0`, equal to dominance) penalizes deviation from canonical values — the central trade-off of the thesis, and the real anti-homogenization mechanism. (Was 6.0, which pinned the GA to canonical and prevented balancing — see `docs/reference/10-known-issues.md` V1.)
- `dominance_penalty` (via `LAMBDA_DOMINANCE=1.0`, **C2 formulation**) = `DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term` (weights 1.0 / 0.5 / 0.5; max 2.0). **Primary `global_term`** = RMS over the 5 characters of `|WR_global − 0.5| / 0.5` — *no archetype globally dominates the roster*. It does **not** force every pair to 50%: a character at 50% global can beat 2 and lose 2 — the space where the advantage cycle can live. (The old primary was per-matchup WR, whose optimum is *every pair at 50%* = flat balance, **incompatible with a cycle by construction** — see `docs/reference/11-combat-review.md` and `docs/tcc/02-ciclo-canonico.md`.) **Secondary `cap_term`** = RMS over the 10 pairs of the excess of `|WR_par − 0.5|` above `MATCHUP_WR_CAP` (hard-counter ceiling: cycle edges stay as advantages within `[0.35, 0.65]`, crushing counters like 100×0 are barred). **Secondary `decis_term`** = RMS over the 10 pairs of per-fight decisiveness `D = mean(|score − 0.5|)` outside the band `[MATCHUP_FLOOR, MATCHUP_THRESHOLD] = [0.10, 0.20]` (winner closes ~20-40% HP); per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). It guards against blowout-coinflip (55%/45% crush each way, global WR ~50% but every fight a blowout). The graded WR that makes this a usable gradient comes from the intention-sampling noise once fights are close.

**Direction-blind dominance is intentional**: the penalty uses `|WR − 0.5|` and `|score − 0.5|` — it does not encode which archetype "should" win each matchup. Encoding the canonical advantage cycle into the fitness would force the GA to preserve identity, making the central research question circular. The cycle is tracked as a post-hoc evaluation metric only.

**Convergence criteria** (C2): a gate plus confirmation (with `SIMS_CONVERGENCE_CHECK` extra simulations):
1. **Gate:** `dominance_penalty ≤ 1e-9` on the best individual;
2. **(a)** each character's **global** WR within `GLOBAL_CONVERGENCE_THRESHOLD` (0.10) of 50% — no one dominates the roster;
3. **(b)** no pair is a hard-counter — every `|wr_par − 0.5| ≤ MATCHUP_WR_CAP` (0.15). It does **not** require each pair at 50% (cycle edges are allowed). Both predicates live in `fitness.py` (`character_balanced`, `is_hard_counter`) as the single source consumed by GA convergence and the reporting tools.

**Canonical calibration rules** (bounds e canônicos re-tunados ao novo modelo — **provisórios, a calibrar**):
- HP range: 250–450; Damage range: 15–30. Canônicos HP: Zoner=300, Rush=320, CM=350, Grap=400, Turtle=450 (Turtle no teto do bound); dano: Zoner=20, Rush=16, CM=18, Grap=27, Turtle=15
- All `range` values ≤ 20 < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- `attack_cooldown` ∈ [1, 5]: Rushdown=1 (fastest), Turtle=5 (slowest), Grappler=4
- `stun` ∈ [0, 0.6] — **fração** do cooldown do atacante (não valor absoluto), aplicada como timer contínuo; bound `< 1.0` garante stun < cooldown. Canônicos: Zoner=0.10, Rush=0.10, CM=0.55, Grap=0.30, Turtle=0.20
- `knockback` ∈ [0, 3]: teto razoável acima do Zoner (2), evita zoning trivial via expulsão de range
- **Não há mais `defense` nem `recovery`** — dano é flat (só DEFEND reduz) e o stun bruto é aplicado direto. 7 atributos por personagem
- Behaviors expressed via `w_*` weights (3 per character: `w_retreat`, `w_defend`, `w_aggressiveness`)
- `w_aggressiveness >= 0.7` → aggressive archetypes (Rushdown, Grappler, Combo Master) push through threats
- `w_retreat > w_defend` → reactive archetypes (Zoner) kite; `w_defend >= w_retreat` → absorbers (Turtle) hold ground

**Cooldown only on hit**: o cooldown do atacante só é setado dentro do bloco de resolução, que só executa quando o golpe conecta (`cd_rem == 0 and distance ≤ range` com a distância **pós-movimento**, e postura fora da guarda). Como o ataque virou regra de resolução e não ação escolhida, não existe mais o conceito de "whiff": um golpe fora de alcance simplesmente não acontece e o cooldown segue intacto.

**Stun as a continuous fraction (no `recovery`, no explicit cap)**: `stun ∈ [0, 0.6]` is a fraction of the attacker's own cooldown; applied stun `= stun × attack_cooldown × TICK_SCALE` is always strictly less than the cooldown (bound `< 1.0`), so the defender always gets a free window — this replaces the old `STUN_CAP_MULTIPLIER`. The timer is a float, decremented by 1.0 per sub-tick: the previous `round()` collapsed the gene to 4 effective levels for a fast attacker, and its amplitude at ±1σ of mutation went from 6.8% to 17.4% when the rounding came out. There is no longer a `recovery` gene subtracting from incoming stun, nor a `defense` gene reducing damage; all genes are continuous floats (no `INTEGER_ATTRIBUTES`).

**Draw as a third outcome**: `_decide_winner` returns `-1` when both fighters end on the same HP fraction (double KO, or a timeout with no difference); the round-robin scores it as half a win for each side and the per-fight score is `0.5`. Without it the tie always fell to side A — which in `_run_round_robin` is always the lower-index archetype, a systematic bias on the very metric the fitness optimises (measured in a mirror: canonical Rushdown gave 54.90% to side A, with 10.3% double KOs).

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
do escalar — hoje 1.0 / 1.0), `DOMINANCE_GLOBAL_WEIGHT` / `DOMINANCE_CAP_WEIGHT` /
`DOMINANCE_DECIS_WEIGHT` (pesos dos 3 termos do dominance C2 — hoje 1.0 / 0.5 / 0.5),
`MATCHUP_WR_CAP` (banda de hard-counter — hoje 0.15, **provisório, a calibrar**),
`MATCHUP_THRESHOLD` / `MATCHUP_FLOOR` (banda de decisividade — hoje 0.20 / 0.10),
`ACTION_PERSISTENCE_SUBTICKS` (comprometimento da intenção), `SIMS_PER_MATCHUP`,
`MAX_GENERATIONS` / `STAGNATION_LIMIT`.
