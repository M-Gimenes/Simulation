# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Instrução permanente (docs)**: a referência técnica detalhada vive em `docs/reference/` (índice em `docs/reference/README.md`) — um arquivo por tema (combate, AG, NSGA-II, config, tools, reprodutibilidade, known-issues, revisão do combate). O material de redação da tese fica em `docs/thesis/`. **Sempre que o código mudar, atualize o(s) `docs/reference/*.md` do tema afetado antes de encerrar a tarefa**, mantendo-os fiéis ao estado atual. Este CLAUDE.md é o guia operacional + resumo de decisões; o detalhe completo é dos docs.

> **Convenção de idioma**: nomes de arquivos e pastas em **inglês**; o **texto** dos `.md` e dos comentários pode ser em português (incl. `docs/reference/` e `docs/thesis/`).

> **Instrução permanente**: sempre que qualquer decisão de design do sistema for alterada — comportamento do combate, semântica dos parâmetros, lógica do GA, ciclo de vantagens, constantes do fitness, protocolo experimental — atualize **três** lugares antes de encerrar a tarefa:
> 1. a seção **Key Design Decisions** neste arquivo e o `docs/reference/*.md` do tema — ambos descrevem o **estado atual** do código, não o histórico;
> 2. **`docs/thesis/04-design-decisions.md`** — o **porquê**, no formato *problema → mudança → resultado*, com os números que sustentam a decisão. Este é o destino obrigatório: mensagem de commit, `docs/status/REVIEW.md` e `docs/status/HANDOFF.md` são registros de trabalho e **não** são consultáveis na hora de redigir. Uma decisão que só existe em commit está perdida para a tese.
>
> Vale também para decisões que **mantiveram** o valor vigente: "manteve-se X porque Y" é resultado, e sem o registro a justificativa se perde igual.

> **Padrão de qualidade**: este é um TCC a ser apresentado para banca. O código deve ser o mais limpo possível — sem variáveis mortas, sem campos diagnósticos desnecessários, sem rastros de decisões anteriores. Prefira nomes explícitos que se auto-documentem. Quando algo for removido, remova completamente — não deixe comentários explicando que foi removido.

> **Foco no sistema, não na narrativa pra banca**: enquanto estamos refinando mecânicas, o objetivo é deixar o sistema o mais redondo possível. **Não** antecipar inline em respostas como o usuário deveria justificar X ou Y resultado para a banca — isso é prematuro enquanto há pontos a refinar. Pontos relevantes para a redação da tese vão para `docs/thesis/` (destrinchado por tema — ver `docs/thesis/README.md`), não para discussão inline. Discutir "defensibilidade na banca" só quando o usuário pedir explicitamente.

## Project Context

TCC (undergraduate thesis) — Genetic Algorithm for competitive game character balancing.  
**Research question:** Can a GA achieve competitive balance between 5 distinct archetypes without destroying their functional identities?

The canonical archetype values are *not* hardcoded constraints — they serve as the deviation measurement baseline and as the initial population seed of the scalar GA. The GA evolves freely; archetype deviation is penalized in the fitness via `LAMBDA_DRIFT` (and exposed as a Pareto objective in NSGA-II), but never hard-constrained.

**The line that keeps the question non-circular: the fitness may encode the *premise*, never the *answer*.**

| | what it is | where it lives |
|---|---|---|
| **premise** | what each archetype **is** — canonical values and `defining_genes`. Given by the FGC, prior to and independent of the balance question | **may** be in the fitness (`drift_penalty`) |
| **answer** | who beats whom (`beats`), whether balance and identity are compatible at all | **never** in the fitness — post-hoc metrics only |

"The Zoner is defined by range" is a premise; "the Zoner should beat the Grappler" is an answer. Encoding the latter would answer the research question with itself. Hence the asymmetry: identity *is* a fitness term, the advantage cycle is not.

A penalty is not a constraint, and the distinction is empirical here, not rhetorical: with `LAMBDA_DRIFT = 1.0` active the whole run, the scalar GA still trades identity away for balance — on the 2026-09-18 battery the evolved roster scores **13/23** on the validator, above every null roster (p < 0.03) but far from the canonical's 23/23. The term exists and can lose.

**Two rulers for identity, one on each side of the line:**
- **structural identity** (`drift_penalty`, in the fitness): are the genes still recognizable? Weighted toward each archetype's `defining_genes`. The validator's Layers 1-2 measure this same axis, so they are **partially endogenous** — a good score there partly reflects the penalty working.
- **functional identity** (validator **Layer 3** + the advantage cycle, post-hoc, never in the fitness): does the character still *play* like itself? Nothing in the fitness references behavior. The research question says "functional identities" — this is the ruler that answers it.

## Dependencies

Versões pinadas em `requirements.txt`. Para subir o ambiente:

```powershell
.\scripts\setup.ps1                 # cria .venv e instala tudo
.\scripts\setup.ps1 -Recreate       # apaga .venv existente e refaz do zero
```

Ou manualmente:

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

`numba` é usado para JIT-compilar o loop de combate (`src.engine.combat._simulate_combat_jit`) — speedup de ~150× sobre Python puro. Primeira chamada compila (~2.5s); depois fica em cache. Sem numba, o sistema não roda — `simulate_combat()` chama o JIT direto. `scipy` entra só no `src.experiments.compare_algorithms` (Mann-Whitney U); o motor não depende dele.

## Layout

```
.
├── main.py                    # entry point: uma execução do AG escalar ou do NSGA-II
├── requirements.txt
├── scripts/                   # PowerShell; rodam a partir da raiz, de onde forem chamados
│   ├── setup.ps1              # cria o .venv
│   ├── run_sweeps.ps1         # os 16 braços exploratórios (orçamento reduzido)
│   ├── run_battery.ps1        # a bateria citável (n = 20), em passos retomáveis
│   └── run_overnight.ps1      # sweeps + bateria, desassistido
├── src/                       # pacote raiz (importável como `src`)
│   ├── engine/                # o modelo: combate, fitness e os dois algoritmos
│   │   ├── paths.py           # PROJECT_ROOT + paths derivados — single source
│   │   ├── provenance.py      # carimbo de config/motor nos artefatos + aviso de obsoleto
│   │   ├── config.py          # All hyperparameters
│   │   ├── archetypes.py      # canonical definitions (frozen)
│   │   ├── character.py       # gene representation
│   │   ├── individual.py      # 5 chars per individual
│   │   ├── combat.py          # tick-based simulation
│   │   ├── fitness.py         # round-robin evaluation, CRN seeding, persistent pool
│   │   ├── operators.py       # selection / crossover / mutation
│   │   ├── ga.py              # scalar GA loop
│   │   ├── nsga2.py           # NSGA-II loop
│   │   └── pareto_metrics.py  # hipervolume + spacing da fronteira (metodologia 1.2)
│   ├── experiments/           # o protocolo da tese — cada um GRAVA um artefato em results/
│   │   ├── multi_run.py       # N execuções + estatística agregada (metodologia 1.1)
│   │   ├── compare_algorithms.py   # AG × NSGA-II: Mann-Whitney U + Â₁₂ + Holm
│   │   ├── external_validation.py  # robustez do equilíbrio fora do laço (metodologia 3.2)
│   │   ├── sensitivity_analysis.py # Δ WR por gene contra o piso de ruído medido
│   │   └── baselines.py       # modelos nulos: piso/teto de cada métrica post-hoc
│   ├── analysis/              # inspeciona UM roster e imprime — não grava nada
│   │   ├── report.py          # dossiê do indivíduo (compõe os outros)
│   │   ├── analyze_matchups.py
│   │   ├── drift_table.py     # drift por gene + diferenciação
│   │   ├── fingerprint.py     # assinatura comportamental por personagem
│   │   └── archetype_validator.py
│   ├── visualization/         # viewers e plots
│   │   ├── viewer.py          # ASCII viewer
│   │   ├── web_viewer.py      # browser viewer
│   │   └── nsga2_plots.py     # Pareto plots
│   └── tests/                 # smoke tests
├── docs/
│   ├── reference/             # como o sistema funciona, um arquivo por tema
│   ├── thesis/                # material de redação: o porquê, o que apresentar
│   └── status/                # registros de trabalho: HANDOFF (estado + última bateria), REVIEW (auditoria)
├── results/                   # artefatos versionados, uma pasta por produtor — ver Output Files
└── overleaf/                  # os textos redigidos (monografia e artigos)
```

The three packages outside `engine/` are split by **what they do with a roster**: `experiments/` runs the protocol and writes the artifacts the thesis cites; `analysis/` inspects one roster and only prints; `visualization/` draws. `analysis/` may call into `experiments/` (the dossier shows the null models) and vice versa for shared measurements (`baselines` scores rosters with the validator) — the split is by output, not a layering.

> **Convenção de imports**: dentro de `src/engine/` use relativos (`from .combat import ...`); fora dele (em `main.py`, `src/experiments/`, `src/analysis/`, `src/visualization/`, `src/tests/`) use absolutos a partir do pacote (`from src.engine.combat import ...`, `from src.analysis.archetype_validator import ...`).
> **Convenção de paths**: nunca hardcode strings. Importe os constants de `src.engine.paths` (`PROJECT_ROOT`, `RESULTS_DIR`, `GA_RESULTS_PATH`, `NSGA2_RESULTS_PATH`, `NSGA2_PLOTS_DIR`, …). Eles são derivados de `Path(__file__).parent.parent.parent` — funcionam independente do cwd.

## Running

Tudo roda a partir da raiz do projeto, como módulo (`-m`), para que `src` esteja no path.

```bash
# Uma execução de cada algoritmo
py main.py
py main.py --algorithm nsga2 --seed 42 --quiet

# src.analysis — inspecionar um roster (só imprime)
py -m src.analysis.report --evolved                 # dossiê completo do indivíduo, já com os modelos nulos (porta de entrada)
py -m src.analysis.analyze_matchups                 # all matchups, canonical (default 1000 sims)
py -m src.analysis.analyze_matchups rushdown zoner  # specific matchup
py -m src.analysis.drift_table --evolved            # drift por gene + diferenciação
py -m src.analysis.fingerprint --evolved            # assinatura comportamental
py -m src.analysis.archetype_validator              # identity checks: structural (L1-2) + behavioral (L3)

# src.experiments — o protocolo (cada um grava em results/)
py -m src.experiments.multi_run --algorithm both       # N execuções + estatística agregada (metodologia 1.1)
py -m src.experiments.multi_run --algorithm ga --lambda-drift 0.25   # braço de sweep (grava em results/exploratory/)
py -m src.experiments.compare_algorithms               # AG × NSGA-II: Mann-Whitney U + Â₁₂ + Holm
py -m src.experiments.compare_algorithms --nsga2-representative scalar_optimum   # o mesmo, contra o comparável do escalar
py -m src.experiments.external_validation --nsga2 best_dominance  # robustez do equilíbrio fora do laço (metodologia 3.2)
py -m src.experiments.sensitivity_analysis --evolved   # ±σ Δ-WR per gene, contra piso de ruído MEDIDO
py -m src.experiments.baselines --evolved              # modelos nulos: posição de cada métrica entre piso e teto

# src.visualization
py -m src.visualization.web_viewer                     # browser viewer em localhost:8080

# Smoke tests (run individually — no test runner configured)
py -m src.tests.test_base
py -m src.tests.test_baselines
py -m src.tests.test_combat
py -m src.tests.test_fitness
py -m src.tests.test_ga
py -m src.tests.test_operators
py -m src.tests.test_nsga2
py -m src.tests.test_provenance
py -m src.tests.test_archetype_validator
py -m src.tests.test_compare_algorithms
```

Experimentos completos (PowerShell): `.\scripts\run_sweeps.ps1` e `.\scripts\run_battery.ps1` são retomáveis com `-From N` e estimam o custo com `-WhatIf`; `.\scripts\run_overnight.ps1` encadeia os dois e **não** tem `-WhatIf` — chamado, ele roda. Os sweeps vêm **antes** da bateria.

> **Windows note:** Use `py` não `python`/`python3`. Scripts output Unicode (box-drawing); via bash pipe use `PYTHONIOENCODING=utf-8` ou passe `--quiet`.

## Output Files

All GA/NSGA-II outputs go to `results/` (created automatically on first run). **Every one of them opens with a `provenance` block** stamping the config, canonicals and engine that produced it, and loading a stale one prints a warning naming what changed — see Key Design Decisions and `docs/reference/09-reproducibility.md`.

| File | Source |
|---|---|
| `results/single_run/ga.json` | `py main.py` (GA) |
| `results/single_run/nsga2.json` | `py main.py --algorithm nsga2` |
| `results/single_run/plots/<timestamp>/` | NSGA-II projection plots |
| `results/multi_run/multi_run_<algo>.json` | `py -m src.experiments.multi_run` (estatística agregada de N execuções) |
| `results/multi_run/comparison_ga_vs_nsga2.json` | `py -m src.experiments.compare_algorithms` (teste estatístico entre os dois algoritmos) |
| `results/multi_run/comparison_ga_vs_nsga2_<rep>.json` | `py -m src.experiments.compare_algorithms --nsga2-representative <rep>` (a mesma comparação contra outro ponto da fronteira — a bateria roda `scalar_optimum`) |
| `results/external_validation/external_validation_<label>.json` | `py -m src.experiments.external_validation` (robustez do equilíbrio fora do laço) |
| `results/sensitivity/sensitivity_analysis.json` | `py -m src.experiments.sensitivity_analysis` (matriz Δ WR por gene) |
| `results/baselines/baselines.json` | `py -m src.experiments.baselines` (rosters de referência + piso/teto/posição de cada métrica) |
| `results/exploratory/multi_run_ga_<desvios>.json` | braços de sweep — `run_sweeps.ps1`. O nome é montado pelos desvios **reais** do default (orçamento, λ, pesos do dominance, elitismo/torneio), então dois braços nunca se sobrescrevem e uma execução barata nunca cai no caminho da bateria |
| `results/logs/` | logs do `run_overnight.ps1` — diagnóstico da noite, fora do git |

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`src/engine/combat.py`):  
Tick-based 1v1 combat. Each sub-tick: choose **stance** via intention → apply simultaneous movement (with collision) → resolve attacks → decrement timers. **Two action channels:** the sampled intention governs only the *stance* (ADVANCE / RETREAT / DEFEND), while the *attack* is a resolution rule — it fires whenever cooldown is ready, the opponent is within range (post-movement) and the stance is not DEFEND. Advancing and retreating both hit; only GUARDA gives up the blow. That is what makes space control a strategy (zoning = attacking while holding distance) and what gives `knockback` a positive slope. **Intention:** sampled from `{FRENTE, RECUAR, GUARDA}` proportional to `(w_aggressiveness, w_retreat, w_defend)` and held for `ACTION_PERSISTENCE_SUBTICKS` sub-ticks; FRENTE → ADVANCE, RECUAR → RETREAT if there is room else DEFEND (cornered), GUARDA → DEFEND. The intention always applies, **except in an impasse** (`distance > own range` AND `distance > opponent's range`), where ADVANCE is imposed. The intention sampling is the **single source of stochasticity**. Bodies **do not pass through each other**; `attack_cooldown` is deterministic; **stun** is a continuous timer `stun × attack_cooldown × TICK_SCALE`, with the gene in `[0, 0.6]` as a fraction of the attacker's own cooldown, so applied stun is always strictly less than the cooldown. Damage is **flat**; the only modifier is the target's DEFEND (`DEFEND_DAMAGE_REDUCTION = 0.6`, i.e. 40% reduction), **less whatever the attacker's `grab_power` breaks through** (see Key Design Decisions). There is **no `defense` gene** and **no `recovery` gene**. A fight ends in KO, timeout (higher HP%) or **draw** (`winner = -1`), which counts as half a win for each side. Timers freshly set by an attack are not decremented until the following tick. Reproducibility: combat RNG is Numba-internal; seed it only via `seed_combat()` (`np.random.seed` from Python does nothing). Under a seed base, the round-robin reseeds before **every fight** (`fitness.fight_seed`).

**GA layer** (`src/engine/ga.py`, `src/engine/fitness.py`, `src/engine/operators.py`):  
Each individual = 5 characters (one per archetype) = 55 genes total (8 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` fights). Scalar GA: `fitness = -(LAMBDA_DRIFT × drift_penalty + LAMBDA_DOMINANCE × dominance_penalty)` — the **same two terms NSGA-II optimizes** as unweighted Pareto objectives (`evaluate_objectives` returns `(dominance_penalty, drift_penalty)` raw and ignores every `LAMBDA_*`). `drift_penalty` is the mean per-character weighted RMS of normalized gene deviations from the canonical profile (structural identity, and the real anti-homogenization mechanism). `dominance_penalty` (**C2 formulation**) is `DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term` (max 2.0): no archetype globally dominates the roster, no pair is a hard counter, and fights are neither blowouts nor degenerate. Both terms in detail below.

**Data model** (`src/engine/archetypes.py` → `src/engine/character.py` → `src/engine/individual.py`):  
`ArchetypeDefinition` (frozen: canonical values, `defining_genes`, `beats`) → `Character` (mutable genes, 8 attrs + 3 weights) → `Individual` (list of 5 Characters + fitness cache). `Individual.from_canonical()` creates the canonical seed; `Individual.random()` a random individual; `from_results()` / `from_nsga2()` load evolved ones and check provenance.

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

Current state only; the *why* behind each decision, with the numbers, is in `docs/thesis/04-design-decisions.md`. Every value and choice, tagged with the kind of evidence behind it (`[medido]` / `[domínio]` / `[coerência]` / `[projeto]`), is catalogued in `docs/thesis/09-values-and-choices.md` — when a value or its evidence changes, update its entry there too.

> **Numbers quoted below that come from a battery are from the 2026-09-18 one, measured before per-fight CRN seeding.** That change replaces every draw, so the next battery (`run_overnight.ps1`) replaces them — reread each against it before relying on it.

### Combat

**Two action channels: stance is chosen, attack is a rule.** Three shared `@njit` helpers — `_decide_action` (stance), `_apply_movement` (movement + collision) and `_decide_winner` (outcome) — are called by A and B in both JIT variants (`_simulate_combat_jit` for fitness, `_simulate_combat_traced_jit` for tools), so both simulate exactly the same combat; covered by a parity test in `test_combat`. There is no Python reimplementation of the loop: tools consume `CombatTrace` (`stance`, `attacked`, `forced_defend`, `guard_broken`). A stunned character loses the sub-tick (`stun_rem > 0` → stance = −1) and cannot attack. The attack fires at resolution when `stance ≥ 0 and stance ≠ DEFEND and cd_rem == 0 and distance ≤ range` (post-movement distance); the cooldown is set only when it lands, so there is no "whiff". Weights act continuously on the intention probabilities, and only their **ratio** affects behaviour.

**Intention persistence = 5 sub-ticks**: exactly one tick (`TICK_SCALE`) and exactly the minimum cooldown, so an `attack_cooldown = 1` character that draws GUARDA gives up exactly one attack window. Never interrupted mid-window, except by the impasse rule (forces ADVANCE, zeroes the counter) or by being stunned. At 10 the same choice cost two windows by an accident of scale, and signal-to-noise was worse on 8/8 genes.

**Collision and cornering.** `_apply_movement` moves both fighters from the start-of-sub-tick positions and stops them at the meeting point, so A is always the left side (`pos_a ≤ pos_b`). Cornering follows — RETREAT with no room falls to DEFEND — and `CombatTrace.forced_defend` keeps that forced DEFEND apart from the chosen one, so geometry does not contaminate the defensive-identity metric.

**Timers and resolution.** All timers and movement run in sub-ticks (`TICK_SCALE = 5`): movement `speed / TICK_SCALE` per sub-tick, cooldown `round(attack_cooldown × TICK_SCALE)`, stun `stun × attack_cooldown × TICK_SCALE` as a float timer decremented by 1.0 (rounding it would leave the gene 4 effective levels for a fast attacker). Decrements happen at the end of the sub-tick, from pre-attack values: a timer freshly set by an attack is not decremented until the next one.

**The grab is a conditional on attack resolution, not a fourth action.** Against a **guarding** target the damage multiplier is `defend_red + grab_power`: 0.6× at `grab_power = 0`, exactly 1.0× at the neutral point `1 − defend_red = 0.40`, 1.6× at the cap. Against a target that is **not** defending it does nothing at all — a counter to guard, not a better attack. Canonically only the Grappler (0.90 → 1.50×) is above the neutral point. Same range and cooldown as the normal attack; no `w_grab`, no fourth stance, so the policy space is untouched. Measured in `test_combat` against an always-guarding target: 16.2 per hit at `grab_power = 0`, 43.2 at `1.0`, exactly zero difference against a non-defending target. `guard_broken` is the Grappler's Layer 3 signature. Caveat: the Grappler beats the Turtle 100% canonically, but the canonical Turtle loses to everyone; whether the GA realizes that edge *on merit* is a question for the battery.

**Draw as a third outcome**: `_decide_winner` returns `-1` on identical HP fraction (double KO, or a timeout with no difference) — half a win for each side, per-fight score 0.5. Without it the tie fell to side A, always the lower-index archetype in `_run_round_robin`: a systematic bias on the metric the fitness optimizes (canonical Rushdown mirror: 54.90% to side A).

**Canonical calibration** — bounds and canonicals are **final** (declared 2026-09-16: they are the premise, not a variable to optimize). Bounds: HP 250–450, damage 15–30, `attack_cooldown` 1–5, `range` 5–20 (all < `INITIAL_DISTANCE` 50, so nobody attacks at tick 1), speed 1–5, `stun` 0–0.6, `knockback` 0–3 (a ceiling above the Zoner's 2 that avoids trivial zoning by ejection), `grab_power` 0–1, weights 0–1. Canonical values live in `archetypes.py` (single source; tables in `docs/reference/03-archetypes.md`). Behaviour is expressed by the three `w_*` weights: `w_aggressiveness ≥ 0.7` for the aggressive archetypes (Rushdown, Grappler, Combo Master), `w_retreat > w_defend` for the kiter (Zoner), `w_defend ≥ w_retreat` for the absorber (Turtle).

### Fitness

**Structural identity: weighted drift, normalized by the bound's range.** `_archetype_deviation` is a weighted RMS over the 11 genes, `sqrt(Σ wᵢ·dᵢ² / Σ wᵢ)`, with `dᵢ = (gene − canonical) / (hi − lo)` and `wᵢ = DRIFT_DEFINING_WEIGHT` (3.0) for the archetype's `defining_genes`, 1.0 otherwise. It compares `fitness.drift_genes(char)`: the 8 attributes as they are, the 3 weights **rescaled to the canonical sum** — intention is sampled proportionally to them, so scaling all three changes nothing in combat and must not be charged as identity loss. `defining_genes` (frozen field of `ArchetypeDefinition`) mirrors the validator's Layer 1 inter assertions — Zoner: range/knockback/w_retreat; Rushdown: speed/attack_cooldown/w_aggressiveness; Combo Master: stun; Grappler: damage/grab_power; Turtle: hp/attack_cooldown/speed/w_defend. Range normalization is what makes the drift ordering of individuals agree with the validator's (dividing by `hi` underestimates genes with a high `lo`); the weighting widens the margin, and 3.0 keeps non-defining genes priced. Same convention in the validator's Layer 2 and in `drift_table`. `LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1.0`: only their ratio matters (tournament selection is ordinal), and the λ sweep measured 1.0 as the knee of the curve — `dominance` stays flat up to it and blows up past it.

**Dominance, C2 formulation** — balance is "no archetype dominates the roster", not "every pair at 50%" (flat balance, incompatible with a cycle by construction):
- **Primary `global_term`** = RMS over the 5 characters of `|WR_global − 0.5| / 0.5`. A character at 50% global can beat 2 and lose 2 — the space where the advantage cycle can live.
- **Secondary `cap_term`** = RMS over the 10 pairs of the excess of `|WR_pair − 0.5|` above `MATCHUP_WR_CAP` — cycle edges stay advantages within `[0.35, 0.65]`, crushing counters are barred.
- **Secondary `decis_term`** = RMS over the 10 pairs of per-fight decisiveness `D = mean(|score − 0.5|)` outside `[MATCHUP_FLOOR, MATCHUP_THRESHOLD] = [0.02, 0.20]`; per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The **ceiling** bars blowout-coinflip (55% A-crush / 45% B-crush: global WR ~50%, every fight a massacre). The **floor** only bars degeneracy: every fight in the engine ends in KO, so a low `D` is a KO at the wire, the best fight; 0.02 sits below every pair of distinct characters and catches the trivial solution (the Zoner mirror reads `D` ≈ 0.016–0.019).
- Weights 1.0 / 0.5 / 0.5 (max 2.0). **The secondaries are load-bearing, and that is measured**: with both at zero the GA reaches the best `global_term` of every sweep arm and still delivers all 10 pairs as hard counters; `decis_term` reads 0.0000 on healthy final individuals because it works — removing it alone multiplies hard counters and worsens `cap_term` itself. Arms are compared by the terms and post-hoc metrics, never by the composite, which the weights define.
- **Direction-blind** (`|WR − 0.5|`, `|score − 0.5|`): nothing encodes which archetype "should" win. The cycle is post-hoc only.
- **Reported decomposed**: `_dominance_penalty` returns `DominanceTerms`, carried in `FitnessDetail`, written per seed by `multi_run` and printed side by side by `compare_algorithms` — descriptively, outside the Mann-Whitney family, so it does not inflate Holm. Losing on the primary term and losing on a secondary one are opposite readings of the same composite: on the 2026-09-18 battery the two algorithms tie on `global_term` and the scalar GA's whole advantage comes from `cap_term`.

**`MATCHUP_WR_CAP = 0.15` is anchored to the FGC matchup grid.** Charts are stated as 5-5, 6-4, 7-3, 8-2 — `|WR − 0.5|` of 0.00, 0.10, 0.20, 0.30; 6-4 is a healthy advantage, 7-3 a counter. The cap must permit 0.10, bar 0.20, and not sit on a grid point (a flush threshold is a coin flip under binomial noise, σ ≈ 0.040): at 0.15 a true 6-4 trips 10.6% of the time and a true 7-3 is caught 90.9%.

### Search and evaluation protocol

**CRN within a generation, one seed per fight; the stream rotates between generations.** `fitness.generation_seed(base, generation)` is the single definition of which stream a generation uses, consumed by **both** loops (if only one rotated, the comparison would confound "algorithm" with "way of evaluating"). Within the generation, `fitness.fight_seed(seed_base, pair, fight)` seeds every fight, so fight *k* of pair *m* gets the same draws in every individual however many draws the earlier fights consumed — a fitness difference reflects genes rather than luck, correct for *selection*. Between generations the stream changes, so the search cannot fit one realization of the RNG — the same rule that keeps the convergence confirmation out-of-stream, applied to the search itself. Costs: re-evaluating survivors on the new stream (~1.8× in the scalar GA, **~2× in NSGA-II**, whose sort compares parents and offspring in one set), and +13% for per-fight seeding. Per-fight seeding makes unaltered pairs identical between two individuals, but the paired fitness difference improves only 1.0–1.3×: the noise left is *inside* the altered character's fights. Declared consequence of rotation: fitness fluctuates between generations, so **`stagnated_at` is less reliable**; `converged_at` is not, since it tests the `roster_balanced` predicate.

**Fixed budget in both algorithms; convergence is a recorded event.** `ga.run` always completes `MAX_GENERATIONS`, recording `converged_at` / `stagnated_at`. NSGA-II cannot stop by the scalar criterion — "is the roster balanced?" is not a question one asks of a front — and stopping the scalar early would make "better" indistinguishable from "used less budget". The comparison is quality at equal budget, and `converged_at` is a second axis, **speed**. `multi_run` aggregates it into `convergence` (rate + mean generation over the seeds that converged, no imputed value); NSGA-II gets no field rather than a zero.

**Convergence = the same predicate, twice, on different samples.** `roster_balanced(detail)`: every character's global WR within `GLOBAL_CONVERGENCE_THRESHOLD` (0.10) of 50% **and** no pair beyond `MATCHUP_WR_CAP` — it does not require each pair at 50%. It must hold on the in-loop evaluation (the gate) **and** on a re-evaluation with `SIMS_CONVERGENCE_CHECK` sims on a stream the GA never saw (`seed + CONVERGENCE_SEED_OFFSET`, 100000, colliding with no other seed family). Re-evaluating on the training stream would confirm nothing: the fitting to the stream concentrates in the pairwise term. The gate is the predicate itself, not a threshold on the composite: `global_term` is quantized (smallest non-zero ≈ 0.0015), and the composite includes `decis_term`, which is not part of convergence. `roster_balanced`, `character_balanced` and `is_hard_counter` in `fitness.py` are the single source for GA convergence, `multi_run`'s per-seed verdict and the reporting tools.

**NSGA-II starts from a fully random population; the scalar GA keeps the canonical seed.** `drift` has a reachable floor of 0 (the canonical *is* the reference) while `dominance` does not, so a seeded canonical is **immortal in rank 0** however unbalanced, and crowding only prunes an overflowing front — with the seed, half the front was rosters as unbalanced as the untouched canonical. In the scalar GA the seed helps and stays: the canonical is bad on the single fitness number and disappears after donating genes.

**`scalar_optimum` is the comparable for the scalar GA.** The fifth representative minimizes `LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift` — the scalar GA's own function — and is the only place NSGA-II reads `LAMBDA_*` (reporting, never search; the front itself is λ-independent, so a λ comparison against it needs no NSGA-II re-run, only `front_objectives`). Measured at the production budget, the scalar GA's point lies *past* the front's low-dominance end and the two are mutually non-dominated; on its own objective the scalar wins. A claim about relative quality is only made from the battery: at a reduced budget the ordering reverses. `multi_run` records all five representatives per seed, each re-evaluated like the headline one, so `compare_algorithms --nsga2-representative scalar_optimum` tests the scalar GA against its comparable at n = 20 without re-running NSGA-II; the battery runs both comparisons, and the headline stays `best_dominance`.

**Elitism 10% and tournament 3 are tested values.** Swept against elitism 0 / 5% / 20% / 30% and tournament 2 / 5 / 7: no arm beats the default, which has the fewest hard counters; at n = 5 the differences do not separate from noise, so the claim is "tested, nothing beats them", not "optimal". Both are read only by `operators.py` in the parent process. `ELITE_RATE` is a **fraction** of the actual population size — an absolute count would silently turn a reduced-budget run into a clone machine.

**Process state for anything a sweep varies, and a persistent pool.** λ, the dominance weights, elitism and tournament are process state (`set_*` / `set_*_override`), because `from .config import X` freezes the value at import. What the workers read travels in a `RuntimeState` with **every task** to the persistent pool (`fitness.parallel_map`) — so a live worker never evaluates under a stale seed base or weight; covered by a parallel-vs-serial test that changes both between evaluations. The pool lives the whole process (3.87 s → 1.04 s per generation of 300), `N_WORKERS = min(8, os.cpu_count())` (the cap guards against `WinError 1455`). Sweep overrides register in the provenance stamp (`provenance.override`), and `multi_run` routes any run that deviates from the defaults in budget, λ, dominance weights or selection to `results/exploratory/`, with the deviation in the name.

### Measurement

**Every artifact carries the configuration that produced it, and checks itself on load.** `src/engine/provenance.py` stamps every JSON in `results/`: timestamp, `fingerprint`, every public constant of `config.py` value by value, a digest of the canonicals (genes + `defining_genes` + `beats`) and a digest of `src/engine/`'s source. `Individual.from_results` / `from_nsga2` call `warn_if_stale` — the chokepoint every tool goes through — and the warning names what changed. Constants are **enumerated**, not hand-listed; the engine **source** is hashed, not only its constants; `config.py` is out of the source digest because its values are recorded one by one. `N_WORKERS` and `MULTI_RUN_N_SEEDS` are out of the stamp — neither changes a number in any artifact (the sample size is recorded in the `multi_run` body), and `compare` ignores excluded constants on the recorded side too. `Divergence.is_experiment_arm` separates a sweep arm from a stale artifact, strictly. Operating rules: re-stamp one artifact at a time, under its own overrides; a retroactive stamp is valid only by reproducing **that** artifact; the stamp does not cover command-line arguments, so each tool's default is the protocol value (`baselines` 30 null rosters, `multi_run` 20 seeds). A recorded number is measured on the **last generation's** stream (`generation_seed(seed, MAX_GENERATIONS)`) — reproducing it means reproducing that stream.

**Every post-hoc metric is read against a measured floor, never against the ceiling.** None of the identity metrics has a floor of zero: `src/experiments/baselines.py` measures them on 35 null rosters (5 mirrors + 30 random) — the validator's chance floor is ~6.4/23 with a null reaching 10/23 (rank assertions resolve ties by index), drift reads ~0.38 for a mirror (identity zero by construction) against ~0.42 for a random roster, and the cycle's floor is 5/10 (every edge a coin flip). Every metric is reported as `position = (value − floor) / (ceiling − floor)` plus an empirical p-value (resolution 1/N). The **mirror roster is the trivial solution** to balance — the numeric answer to "why not make all five identical?". **The authored cycle cannot be a result**: it is one of 24 labelled regular tournaments on 5 vertices; what is a result, without authorship, is **intransitivity itself** — a strictly transitive roster has WRs 100/75/50/25/0, incompatible with everyone near 50% — measured by `circular_triads` (0 strict order / 2.5 random / 5 maximum), meaningful only when the pair WRs are decided.

**External validation keeps a binary verdict, with counts.** A roster is ROBUST only if no character leaves the band and no pair becomes a hard counter in **any** of 10 unseen conditions; the report also counts in how many conditions each pair and character fails, which separates a systematic failure from a sporadic one.

**The comparison between algorithms** is Mann-Whitney U + Vargha-Delaney Â₁₂ + Holm over a family built by the variance of the joint sample (a metric constant across both algorithms is not a test and stays out, reported descriptively). n = 20 seeds is the smallest with ≥ 80% power for a large effect. On the 2026-09-18 battery all three family metrics are significant with a large effect — scalar GA better on `dominance` and hard counters, NSGA-II on drift — and the Â₁₂ moved toward 0.5 from n = 10, which was inflated.

## Quick Matchup Check

```bash
py -m src.analysis.report --evolved              # dossiê completo do indivíduo (porta de entrada)
py -m src.analysis.analyze_matchups --evolved    # só os matchups
py -m src.analysis.drift_table --evolved         # só o drift por gene + diferenciação
py -m src.analysis.fingerprint --evolved         # só o comportamento
py -m src.experiments.baselines --evolved           # só os modelos nulos (piso/teto/posição)
py -m src.analysis.analyze_matchups rushdown zoner --n 100   # par específico
```

## Hyperparameters

Todos em `src/engine/config.py`. **Tabela completa e comentada em
[`docs/reference/07-configuration.md`](docs/reference/07-configuration.md)** — manter lá, não duplicar
aqui. Os mais ajustados ao refinar: `LAMBDA_DRIFT` / `LAMBDA_DOMINANCE` (trade-off
do escalar — hoje 1.0 / 1.0, o joelho medido), `DOMINANCE_GLOBAL_WEIGHT` / `DOMINANCE_CAP_WEIGHT` /
`DOMINANCE_DECIS_WEIGHT` (pesos dos 3 termos do dominance C2 — hoje 1.0 / 0.5 / 0.5),
`MATCHUP_WR_CAP` (banda de hard-counter — 0.15, **fechado**: ponto médio entre 6-4 e
7-3 na grade da FGC, ver o comentário no `config.py`),
`MATCHUP_THRESHOLD` / `MATCHUP_FLOOR` (banda de decisividade — hoje 0.20 / 0.02,
o piso como guarda de degenerescência), `DRIFT_DEFINING_WEIGHT` (peso dos genes
definidores no drift — hoje 3.0; 1.0 volta ao drift uniforme),
`ACTION_PERSISTENCE_SUBTICKS` (comprometimento da intenção — 5, **fechado**: 1 tick
= cooldown mínimo), `SIMS_PER_MATCHUP`,
`MAX_GENERATIONS` / `STAGNATION_LIMIT`, `ELITE_RATE` / `TOURNAMENT_SIZE` (0.10 / 3,
**testados**: nenhum dos 7 braços do sweep os supera).
