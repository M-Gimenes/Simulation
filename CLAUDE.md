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

A penalty is not a constraint, and the distinction is empirical here, not rhetorical: with `LAMBDA_DRIFT = 1.0` active the whole run, the scalar GA still trades identity away for balance — on the 2026-09-23 battery the evolved roster scores **17/23** on the validator, far from the canonical's 23/23, and its functional part (Layer 3) **3/5**. The term exists and can lose.

**Two rulers for identity, one on each side of the line:**
- **structural identity** (`drift_penalty`, in the fitness): are the genes still recognizable? Weighted toward each archetype's `defining_genes`. The validator's Layers 1-2 measure this same axis, so they are **partially endogenous** — a good score there partly reflects the penalty working, and beating unoptimized null rosters on them is nearly guaranteed.
- **functional identity** (validator **Layer 3** + the **behavioral rank agreement** τ, post-hoc, never in the fitness): does the character still *play* like itself? The research question says "functional identities" — this is the ruler that answers it. It is *held-out*, not independent: each Layer 3 assertion is a near-direct consequence of a defining gene. The advantage cycle is **not** an identity ruler — the canonical itself realizes only 6/10 of it.

**The control that isolates the method is `LAMBDA_DRIFT = 0`**, not the null rosters: the battery runs the scalar GA without the drift term (and without the canonical seed) at full sample and budget, and `compare_algorithms --control` compares every ruler against it.

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
├── README.md                  # porta de entrada curta: subir o ambiente e rodar
├── main.py                    # entry point: uma execução do AG escalar ou do NSGA-II
├── requirements.txt
├── scripts/                   # PowerShell; rodam a partir da raiz, de onde forem chamados
│   ├── setup.ps1              # cria o .venv
│   ├── run_sweeps.ps1         # os 16 braços exploratórios (orçamento reduzido)
│   ├── run_battery.ps1        # a bateria citável (n = 20), em passos retomáveis
│   ├── run_hybrid_sweep.ps1   # os 7 braços que escolhem a config do híbrido
│   └── run_overnight.ps1      # sweeps + bateria, desassistido
├── src/                       # pacote raiz (importável como `src`)
│   ├── engine/                # o modelo: combate, fitness e os dois algoritmos
│   │   ├── paths.py           # PROJECT_ROOT + paths derivados — single source
│   │   ├── provenance.py      # carimbo de config/motor/medição nos artefatos + aviso e recusa de obsoleto
│   │   ├── config.py          # All hyperparameters
│   │   ├── archetypes.py      # canonical definitions (frozen)
│   │   ├── character.py       # gene representation
│   │   ├── individual.py      # 5 chars per individual
│   │   ├── combat.py          # tick-based simulation
│   │   ├── fitness.py         # round-robin evaluation, CRN seeding, persistent pool
│   │   ├── operators.py       # selection / crossover / mutation
│   │   ├── ga.py              # scalar GA loop
│   │   ├── nsga2.py           # NSGA-II loop
│   │   ├── hybrid.py          # NSGA-II → AG escalar, orçamento repartido entre as fases
│   │   └── pareto_metrics.py  # hipervolume + spacing da fronteira (metodologia 1.2)
│   ├── experiments/           # o protocolo da tese — cada um GRAVA um artefato em results/
│   │   ├── multi_run.py       # N execuções + estatística agregada (metodologia 1.1)
│   │   ├── compare_algorithms.py   # AG × NSGA-II e AG × controles: Mann-Whitney U + Â₁₂ + Holm
│   │   ├── external_validation.py  # replicação e robustez a regras fora do laço (metodologia 3.2)
│   │   ├── sensitivity_analysis.py # Δ WR por gene contra o piso de ruído medido
│   │   ├── baselines.py       # modelos nulos: piso/teto de cada métrica post-hoc
│   │   ├── cycle_structure.py # o ciclo autoral falsificado uma vez, a 16.000 lutas/par
│   │   └── hybrid_choice.py   # o critério pré-registrado que escolhe a config do híbrido
│   ├── analysis/              # inspeciona UM roster e imprime — não grava nada
│   │   ├── report.py          # dossiê do indivíduo (compõe os outros)
│   │   ├── analyze_matchups.py
│   │   ├── drift_table.py     # drift por gene + diferenciação
│   │   ├── fingerprint.py     # assinatura comportamental por personagem
│   │   └── archetype_validator.py
│   ├── visualization/         # viewers e plots
│   │   ├── viewer.py          # ASCII viewer
│   │   ├── web_viewer.py      # browser viewer
│   │   ├── ga_plots.py        # curvas de convergência do AG (lê single_run/ga.json)
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
py -m src.experiments.multi_run --algorithm ga --lambda-drift 0      # controle: sem drift (grava em results/controls/)
py -m src.experiments.multi_run --algorithm ga --no-canonical-seed   # controle: sem semente canônica
py -m src.experiments.multi_run --algorithm hybrid                   # terceiro braço: NSGA-II → AG escalar
py -m src.experiments.hybrid_choice                    # aplica o critério que escolhe split/carry do híbrido
py -m src.experiments.multi_run --algorithm ga --lambda-drift 0.25 --n-seeds 5 --seed-start 1000 --pop 120 --generations 60   # braço de sweep (results/exploratory/)
py -m src.experiments.compare_algorithms               # AG × NSGA-II (scalar_optimum) + relação de Pareto
py -m src.experiments.compare_algorithms --nsga2-representative best_dominance   # o mesmo, contra o extremo da fronteira
py -m src.experiments.compare_algorithms --control results/controls/multi_run_ga_drift0_dom1.json   # AG × controle
py -m src.experiments.external_validation --nsga2 scalar_optimum  # replicação + robustez a regras (metodologia 3.2)
py -m src.experiments.sensitivity_analysis --evolved   # Δ-WR por gene (janela 2σ, 11 genes), contra piso de ruído MEDIDO
py -m src.experiments.baselines --evolved              # modelos nulos: posição de cada métrica entre piso e teto
py -m src.experiments.cycle_structure                  # o ciclo autoral na resolução que ele exige (16 × 1000 lutas/par)

# src.visualization
py -m src.visualization.web_viewer                     # browser viewer em localhost:8080
py -m src.visualization.ga_plots                       # curvas de convergência do AG, a partir do artefato
py -m src.visualization.nsga2_plots                    # fronteira de Pareto, a partir do artefato

# Smoke tests (run individually — no test runner configured)
py -m src.tests.test_base
py -m src.tests.test_baselines
py -m src.tests.test_cycle_structure
py -m src.tests.test_hybrid
py -m src.tests.test_hybrid_choice
py -m src.tests.test_combat
py -m src.tests.test_fitness
py -m src.tests.test_ga
py -m src.tests.test_operators
py -m src.tests.test_nsga2
py -m src.tests.test_provenance
py -m src.tests.test_archetype_validator
py -m src.tests.test_compare_algorithms
py -m src.tests.test_multi_run
```

Experimentos completos (PowerShell): `.\scripts\run_sweeps.ps1` e `.\scripts\run_battery.ps1` são retomáveis com `-From N` e estimam o custo com `-WhatIf`; `.\scripts\run_overnight.ps1` encadeia os dois e **não** tem `-WhatIf` — chamado, ele roda. Os sweeps vêm **antes** da bateria.

> **Windows note:** Use `py` não `python`/`python3`. Scripts output Unicode (box-drawing); via bash pipe use `PYTHONIOENCODING=utf-8` ou passe `--quiet`.

## Output Files

All GA/NSGA-II outputs go to `results/` (created automatically on first run). **Every one of them opens with a `provenance` block** stamping the config, canonicals, engine and (for experiment tools) measurement code that produced it; loading a stale one prints a warning naming what changed, and a tool that writes a new artifact from a stale one refuses — see Key Design Decisions and `docs/reference/09-reproducibility.md`.

| File | Source |
|---|---|
| `results/single_run/ga.json` | `py main.py` (GA) |
| `results/single_run/nsga2.json` | `py main.py --algorithm nsga2` |
| `results/single_run/plots/<timestamp>/` | NSGA-II Pareto plot — `py main.py --algorithm nsga2`, ou `py -m src.visualization.nsga2_plots` a partir do artefato |
| `results/single_run/plots/ga_convergence.png` | `py main.py` (GA) ou `py -m src.visualization.ga_plots` — best/mean/worst fitness e os dois termos por geração, com `converged_at` marcado |
| `results/multi_run/multi_run_<algo>.json` | `py -m src.experiments.multi_run` (estatística agregada de N execuções) |
| `results/multi_run/comparison_ga_vs_nsga2.json` | `py -m src.experiments.compare_algorithms` (teste estatístico entre os dois algoritmos, NSGA-II pelo `scalar_optimum`, + relação de Pareto por semente) |
| `results/multi_run/comparison_ga_vs_nsga2_<rep>.json` | `py -m src.experiments.compare_algorithms --nsga2-representative <rep>` (a mesma comparação contra outro ponto da fronteira — a bateria roda `best_dominance`) |
| `results/controls/multi_run_ga_<desvio>.json` | braços de controle — amostra e orçamento da bateria, um fator de desenho trocado (`drift0_dom1`, `unseeded`) |
| `results/controls/multi_run_hybrid_split<s>_<carry>.json` | `py -m src.experiments.multi_run --algorithm hybrid` — o terceiro braço, com amostra e orçamento do protocolo. Split e carry entram **sempre** no nome: o híbrido nunca cai no caminho principal, que é dos dois algoritmos que a pergunta compara |
| `results/exploratory/hybrid_choice.json` | `py -m src.experiments.hybrid_choice` (a escolha da configuração, com a trilha da decisão e a ressalva de orçamento reduzido) |
| `results/controls/comparison_ga_vs_<braço>.json` | `py -m src.experiments.compare_algorithms --control <artefato>` |
| `results/external_validation/external_validation_<label>.json` | `py -m src.experiments.external_validation` (replicação e robustez a regras perturbadas) |
| `results/sensitivity/sensitivity_analysis.json` | `py -m src.experiments.sensitivity_analysis` (matriz Δ WR por gene) |
| `results/cycle/cycle_structure.json` | `py -m src.experiments.cycle_structure` (o ciclo autoral falsificado: arestas mantidas **e decididas** do canônico, dos dois algoritmos e dos nulos, a 16.000 lutas por par) |
| `results/baselines/baselines.json` | `py -m src.experiments.baselines` (rosters de referência + piso/teto/posição de cada métrica, e — por roster — as três tabelas cruas que sustentam elas: `per_gene_drift`, `differentiation` e `behavioral_profile`) |
| `results/exploratory/multi_run_ga_<desvios>.json` | braços de sweep — `run_sweeps.ps1` (sementes 1000–1004, disjuntas da bateria). O nome é montado pelos desvios **reais** do protocolo (orçamento, amostra, sims, λ, pesos do dominance, seleção, semente canônica), então dois braços nunca se sobrescrevem e uma execução barata nunca cai no caminho da bateria |
| `results/logs/` | logs do `run_overnight.ps1` — diagnóstico da noite, fora do git |

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`src/engine/combat.py`):  
Tick-based 1v1 combat. Each sub-tick: choose **stance** via intention → apply simultaneous movement (with collision) → resolve attacks → decrement timers. **Two action channels:** the sampled intention governs only the *stance* (ADVANCE / RETREAT / DEFEND), while the *attack* is a resolution rule — it fires whenever cooldown is ready, the opponent is within range (post-movement) and the stance is not DEFEND. Advancing and retreating both hit; only GUARDA gives up the blow. That is what makes space control a strategy (zoning = attacking while holding distance) and what gives `knockback` a positive slope. **Intention:** sampled from `{FRENTE, RECUAR, GUARDA}` proportional to `(w_aggressiveness, w_retreat, w_defend)` and held for `ACTION_PERSISTENCE_SUBTICKS` sub-ticks; FRENTE → ADVANCE, RECUAR → RETREAT if there is room else DEFEND (cornered), GUARDA → DEFEND. The intention always applies, **except in an impasse** (`distance > own range` AND `distance > opponent's range`), where ADVANCE is imposed. The intention sampling is the **single source of stochasticity**. Bodies **do not pass through each other**; the attack period is `attack_cooldown × TICK_SCALE` sub-ticks and the **stun** `stun × attack_cooldown × TICK_SCALE`, both **exact on average** — each hit rounds to whole sub-ticks carrying the remainder to the next (`_carry_round`, deterministic error diffusion) —, with the stun gene in `[0, 0.6]` as a fraction of the attacker's own cooldown, so applied stun is always strictly less than the period. Damage is **flat**; the only modifier is the target's DEFEND (`DEFEND_DAMAGE_REDUCTION = 0.6`, i.e. 40% reduction), **less whatever the attacker's `grab_power` breaks through** (see Key Design Decisions). There is **no `defense` gene** and **no `recovery` gene**. A fight ends in KO, timeout (higher HP%) or **draw** (`winner = -1`), which counts as half a win for each side. Timers freshly set by an attack are not decremented until the following tick. The combat rules (field, initial distance, persistence, guard reduction, …) are process state (`combat.CombatRules`, default `TRAINING_RULES` = the `config.py` values), changed only by the external validation. Reproducibility: combat RNG is Numba-internal; seed it only via `seed_combat()` (`np.random.seed` from Python does nothing). Under a seed base, the round-robin reseeds before **every fight** (`fitness.fight_seed`).

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

> **Numbers quoted below that come from a battery are from the 2026-09-23 one** — n = 20, 19 steps, the two control arms plus the hybrid arm, the headline on `scalar_optimum`. It is the citable battery; nothing older is.
>
> It re-runs the 2026-09-21 battery on the engine with the five deferred fixes applied and with `MULTI_RUN_SIMS` = 1000 (was 200). **The individuals are the same**: compared gene by gene, 40 of 40 seeded runs came out bit-identical, so the fixes are inert as `10-known-issues` claimed and now measures. **No identity number moved** (drift, validator, τ). What moved is everything the ruler measures — anything derived from `dominance` — and two readings flipped because of it: the λ = 0 arm's effect on balance (now not significant) and the evolved roster's position against the mirrors (now 99%, not 102%). Both are flagged ⚠ below.

### Combat

**Two action channels: stance is chosen, attack is a rule.** Four shared `@njit` helpers — `_decide_action` (stance), `_apply_movement` (movement + collision), `_carry_round` (timer rounding) and `_decide_winner` (outcome) — are called by A and B in both JIT variants (`_simulate_combat_jit` for fitness, `_simulate_combat_traced_jit` for tools), so both simulate exactly the same combat; covered by a parity test in `test_combat`. There is no Python reimplementation of the loop: tools consume `CombatTrace` (`stance`, `attacked`, `forced_defend`, `guard_broken`). A stunned character loses the sub-tick (`stun_rem > 0` → stance = −1) and cannot attack. The attack fires at resolution when `stance ≥ 0 and stance ≠ DEFEND and cd_rem == 0 and distance ≤ range` (post-movement distance); the cooldown is set only when it lands, so there is no "whiff". Weights act continuously on the intention probabilities, and only their **ratio** affects behaviour.

**Intention persistence = 5 sub-ticks**: exactly one tick (`TICK_SCALE`) and exactly the attack period of the fastest attacker (`attack_cooldown = 1`), so one that draws GUARDA gives up exactly one attack window — true only since the timer fix; the period used to be 6. Never interrupted mid-window, except by the impasse rule (forces ADVANCE, zeroes the counter) or by being stunned. At 10 the same choice cost two windows by an accident of scale, and signal-to-noise was worse on 8/8 genes.

**Collision and cornering.** `_apply_movement` moves both fighters from the start-of-sub-tick positions and stops them at the meeting point, so A is always the left side (`pos_a ≤ pos_b`). Cornering follows — RETREAT with no room falls to DEFEND — and `CombatTrace.forced_defend` keeps that forced DEFEND apart from the chosen one, so geometry does not contaminate the defensive-identity metric.

**Timers carry the remainder.** All timers and movement run in sub-ticks (`TICK_SCALE = 5`): movement `speed / TICK_SCALE` per sub-tick; each hit converts the continuous period `attack_cooldown × TICK_SCALE` and stun `stun × attack_cooldown × TICK_SCALE` into whole sub-ticks by **error diffusion** (`_carry_round`: add the remainder of the previous hit, keep the integer part, carry the new remainder; it starts at 0.5). Both are exact on average, the combat stays deterministic, and the genes act without plateaus. The cooldown is set to `period − 1` because the hit's own sub-tick counts as the first of the period. Before: the period was `round(5c) + 1` and a float stun stunned exactly `ceil(s)` sub-ticks — 4 effects across [0, 0.6] for `cooldown = 1`; the evolved Rushdown's stun gave 5 distinct WRs over 31 values, now 27. Decrements happen at the end of the sub-tick, from pre-attack values: a timer freshly set by an attack is not decremented until the next one.

**The grab is a conditional on attack resolution, not a fourth action.** Against a **guarding** target the damage multiplier is `defend_red + grab_power`: 0.6× at `grab_power = 0`, exactly 1.0× at the neutral point `1 − defend_red = 0.40`, 1.6× at the cap. Against a target that is **not** defending it does nothing at all — a counter to guard, not a better attack. Canonically only the Grappler (0.90 → 1.50×) is above the neutral point. Same range and cooldown as the normal attack; no `w_grab`, no fourth stance, so the policy space is untouched. Measured in `test_combat` against an always-guarding target: 16.2 per hit at `grab_power = 0`, 43.2 at `1.0`, exactly zero difference against a non-defending target. `guard_broken` is the Grappler's Layer 3 signature. Caveat: the Grappler beats the Turtle 100% canonically, but the canonical Turtle loses to everyone. The 2026-09-23 battery answers what the GA does with that edge: it flattens it — Grappler × Turtle lands at 51% ± 6% across the 20 seeds, a hard counter on none of them.

**Draw as a third outcome**: `_decide_winner` returns `-1` on identical HP fraction (double KO, or a timeout with no difference) — half a win for each side, per-fight score 0.5. Without it the tie fell to side A, always the lower-index archetype in `_run_round_robin`: a systematic bias on the metric the fitness optimizes (canonical Rushdown mirror: 54.90% to side A).

**Canonical calibration** — bounds and canonicals are **final** (declared 2026-09-16: they are the premise, not a variable to optimize). Bounds: HP 250–450, damage 15–30, `attack_cooldown` 1–5, `range` 5–20 (all < `INITIAL_DISTANCE` 50, so nobody attacks at tick 1), speed 1–5, `stun` 0–0.6, `knockback` 0–3 (a ceiling above the Zoner's 2 that avoids trivial zoning by ejection), `grab_power` 0–1, weights 0–1. Canonical values live in `archetypes.py` (single source; tables in `docs/reference/03-archetypes.md`). Behaviour is expressed by the three `w_*` weights: `w_aggressiveness ≥ 0.7` for the aggressive archetypes (Rushdown, Grappler, Combo Master), `w_retreat > w_defend` for the kiter (Zoner), `w_defend ≥ w_retreat` for the absorber (Turtle).

### Fitness

**Structural identity: weighted drift, normalized by the bound's range.** `_archetype_deviation` is a weighted RMS over the 11 genes, `sqrt(Σ wᵢ·dᵢ² / Σ wᵢ)`, with `dᵢ = (gene − canonical) / (hi − lo)` and `wᵢ = DRIFT_DEFINING_WEIGHT` (3.0) for the archetype's `defining_genes`, 1.0 otherwise. It compares `fitness.drift_genes(char)`: the 8 attributes as they are, the 3 weights **rescaled to the canonical sum** — intention is sampled proportionally to them, so scaling all three changes nothing in combat and must not be charged as identity loss. `defining_genes` (frozen field of `ArchetypeDefinition`) mirrors the validator's Layer 1 inter assertions — Zoner: range/knockback/w_retreat; Rushdown: speed/attack_cooldown/w_aggressiveness; Combo Master: stun; Grappler: damage/grab_power; Turtle: hp/attack_cooldown/speed/w_defend. Range normalization is what makes the drift ordering of individuals agree with the validator's (dividing by `hi` underestimates genes with a high `lo`); the weighting widens the margin, and 3.0 keeps non-defining genes priced. Same convention in the validator's Layer 2 and in `drift_table`. `LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1.0`: only their ratio matters (tournament selection is ordinal), and the λ sweep measured 1.0 as the knee of the curve — `dominance` stays flat up to it (0.060–0.065 at λ = 0.25, 0.5 and 1.0) and blows up past it (0.198 at λ = 2.0, 0.358 at 4.0). On the 2026-09-21 λ sweep λ = 1.0 does not merely tie the cheaper arms, it **dominates them**: same `dominance`, drift 0.2448 against 0.3462 and 0.3773, and τ = 0.415 against 0.018 and −0.050.

**Dominance, C2 formulation** — balance is "no archetype dominates the roster", not "every pair at 50%" (flat balance, incompatible with a cycle by construction):
- **Primary `global_term`** = RMS over the 5 characters of `|WR_global − 0.5| / 0.5`. A character at 50% global can beat 2 and lose 2 — the space where the advantage cycle can live.
- **Secondary `cap_term`** = RMS over the 10 pairs of the excess of `|WR_pair − 0.5|` above `MATCHUP_WR_CAP` — cycle edges stay advantages within `[0.35, 0.65]`, crushing counters are barred.
- **Secondary `decis_term`** = RMS over the 10 pairs of per-fight decisiveness `D = mean(|score − 0.5|)` outside `[MATCHUP_FLOOR, MATCHUP_THRESHOLD] = [0.02, 0.20]`; per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The **ceiling** bars blowout-coinflip (55% A-crush / 45% B-crush: global WR ~50%, every fight a massacre). The **floor** only bars degeneracy: every fight in the engine ends in KO, so a low `D` is a KO at the wire, the best fight; 0.02 sits above the degenerate roster (0% KO, `D` ≤ 0.008) and below every pair of distinct characters. Of the five mirrors it catches only the Zoner one (`D` ≈ 0.016–0.019) — the defense against the trivial solution is `drift_penalty`, not the floor.
- Weights 1.0 / 0.5 / 0.5 (max 2.0). **The secondaries are load-bearing, and that is measured**: with both at zero the GA reaches the best `global_term` of every sweep arm (0.0275) and still turns 8.8 of the 10 pairs into hard counters; `decis_term` reads 0.0000 on healthy final individuals because it works — removing it alone takes hard counters from 0.8 to 2.2 and `cap_term` from 0.0176 to 0.1212. Arms are compared by the terms and post-hoc metrics, never by the composite, which the weights define.
- **Direction-blind** (`|WR − 0.5|`, `|score − 0.5|`): nothing encodes which archetype "should" win. The cycle is post-hoc only.
- **Reported decomposed**: `_dominance_penalty` returns `DominanceTerms`, carried in `FitnessDetail`, written per seed by `multi_run` and printed side by side by `compare_algorithms` — descriptively, outside the Mann-Whitney family, so it does not inflate Holm. Losing on the primary term and losing on a secondary one are opposite readings of the same composite: on the 2026-09-23 battery the scalar GA wins both, but by very different margins — `global_term` 0.0318 against 0.0401, `cap_term` 0.0032 against 0.0736. The composite alone would hide that most of the gap is crushing counters, not roster-level imbalance.

**`MATCHUP_WR_CAP = 0.15` is anchored to the FGC matchup grid.** Charts are stated as 5-5, 6-4, 7-3, 8-2 — `|WR − 0.5|` of 0.00, 0.10, 0.20, 0.30; 6-4 is a healthy advantage, 7-3 a counter. The cap must permit 0.10, bar 0.20, and not sit on a grid point (a flush threshold is a coin flip under binomial noise, σ ≈ 0.040): at 0.15 a true 6-4 trips 10.6% of the time and a true 7-3 is caught 90.9%.

### Search and evaluation protocol

**CRN within a generation, one seed per fight; the stream rotates between generations.** `fitness.generation_seed(base, generation)` is the single definition of which stream a generation uses, consumed by **both** loops (if only one rotated, the comparison would confound "algorithm" with "way of evaluating"). Within the generation, `fitness.fight_seed(seed_base, pair, fight)` seeds every fight, so fight *k* of pair *m* gets the same draws in every individual however many draws the earlier fights consumed — a fitness difference reflects genes rather than luck, correct for *selection*. Between generations the stream changes, so the search cannot fit one realization of the RNG — the same rule that keeps the convergence confirmation out-of-stream, applied to the search itself. Costs: re-evaluating survivors on the new stream (~1.8× in the scalar GA, **~2× in NSGA-II**, whose sort compares parents and offspring in one set), and +13% for per-fight seeding. Per-fight seeding makes unaltered pairs identical between two individuals, but the paired fitness difference improves only 1.0–1.3×: the noise left is *inside* the altered character's fights. Declared consequence of rotation: fitness fluctuates between generations, which is why there is **no stagnation event** (the "best fitness ever" would be a running max of noisy values — it rises by luck and is rarely beaten again); `converged_at` is unaffected, since it tests the `roster_balanced` predicate.

**Fixed budget in both algorithms; convergence is a recorded event.** `ga.run` always completes `MAX_GENERATIONS`, recording `converged_at`. NSGA-II cannot stop by the scalar criterion — "is the roster balanced?" is not a question one asks of a front — and stopping the scalar early would make "better" indistinguishable from "used less budget". The comparison is quality at equal budget — equal number of **offspring**: NSGA-II does twice the evaluations, re-evaluating parents with offspring —, and `converged_at` is a second axis, **speed**. `multi_run` aggregates it into `convergence` (rate + mean generation over the seeds that converged, no imputed value); NSGA-II gets no field rather than a zero. `converged_at` is the **first** gate firing that survives confirmation in a test repeated every generation, not stable balance: read it next to the share of seeds that **end** balanced (20/20 converged vs 16/20 balanced at the end on the 2026-09-23 battery; it read 14/20 at 200 fights per pair, and two of those were the ruler's noise).

**Convergence = the same predicate, twice, on different samples.** `roster_balanced(detail)`: every character's global WR within `GLOBAL_CONVERGENCE_THRESHOLD` (0.10) of 50% **and** no pair beyond `MATCHUP_WR_CAP` — it does not require each pair at 50%. It must hold on the in-loop evaluation (the gate) **and** on a re-evaluation with `SIMS_CONVERGENCE_CHECK` sims on a stream the GA never saw (`generation_seed(seed, gen) + CONVERGENCE_SEED_OFFSET`, 100000 — so the confirmation stream is **different every generation**, and collides with no other seed family while training seeds stay under 100 apart). Re-evaluating on the training stream would confirm nothing: the fitting to the stream concentrates in the pairwise term. The gate is the predicate itself, not a threshold on the composite: `global_term` is quantized (smallest non-zero ≈ 0.0015), and the composite includes `decis_term`, which is not part of convergence. `roster_balanced`, `character_balanced` and `is_hard_counter` in `fitness.py` are the single source for GA convergence, `multi_run`'s per-seed verdict and the reporting tools.

**NSGA-II starts from a fully random population; the scalar GA keeps the canonical seed (`GA_CANONICAL_SEED`).** `drift` has a reachable floor of 0 (the canonical *is* the reference) while `dominance` does not, so a seeded canonical is **immortal in rank 0** however unbalanced, and crowding only prunes an overflowing front — with the seed, half the front was rosters as unbalanced as the untouched canonical. In the scalar GA the seed helps and stays: the canonical is bad on the single fitness number and disappears after donating genes. Because the asymmetry confounds algorithm with initialization, the battery runs the **scalar GA without the seed** as a control arm.

**A third arm: the hybrid NSGA-II → scalar GA** (`src/engine/hybrid.py`, `multi_run --algorithm hybrid`, battery steps 18–19). It splits **one** budget — `HYBRID_SPLIT = 0.5` of the generations to NSGA-II, the rest to `ga.run` seeded with the final front (`HYBRID_CARRY = "front"`). Phase 2 continues the stream rotation via `gen_offset`, and `converged_at` is shifted to the whole-run scale. Motivation: the scalar fitness sums a **sampled** term (`dominance`) with an **exact** one (`drift`), so past convergence the selection spends its pressure on noise and the low-drift lineage dies at generation 7; in NSGA-II `drift` is a separate noise-free objective whose extreme is immortal in rank 0. **Measured on the 2026-09-23 battery, it trades large identity for no balance at all**: drift 0.1663 against 0.2473 (Â₁₂ = 0.97), τ +0.5215 against +0.2811, L1+2 15 against 11, L3 4 against 3 — all large effects, p_Holm ≤ 0.0058 — while `dominance` (Â₁₂ = 0.51, p_Holm = 1.00) and hard counters (Â₁₂ = 0.49) do not move, with 16/20 rosters balanced in both arms. Against NSGA-II it keeps that identity with **0.25 hard counters against 2.80** and 16/20 balanced against 0/20. The price is **speed**: it converges at generation 98.3 ± 20.2 against 31.3 ± 13.2, because the first 75 generations are Pareto and do not chase the balance predicate. The research question is still compared between the scalar GA and NSGA-II — the two algorithms from the literature; the hybrid is reported as a **method contribution**. Caveat: the split came from the choice criterion's simplicity tie-break, not from evidence — at reduced budget no arm passed the balance filter and the ordering between splits did not transfer, so "0.5 is the best split" is not measured.

**Two control arms at battery sample and budget** (n = 20, pop 300 × 150): the scalar GA with `LAMBDA_DRIFT = 0` (the counterfactual of the research question: balance without the identity term) and without the canonical seed. The λ = 0 arm is also the noisiest: its in-loop `dominance` inflates **2.33×** on re-evaluation against 1.80× for the full GA and 1.25× for NSGA-II — the more the selection leans on the noisy term, the more the run buys luck. **Both were measured on the 2026-09-23 battery, and the λ = 0 arm is the strongest single result in it — on identity only.** Dropping the drift term destroys identity on all four rulers: drift 0.4089 against 0.2495, validator L1+2 5.7 against 11.5, Layer 3 0.90 against 2.45, τ +0.007 against +0.259, each at p_Holm ≤ 0.0045 with a large effect. τ = +0.007 is chance to three decimals. **On balance it does not separate**: `dominance` 0.0432 against 0.0355 in medians, same direction and the same medium effect (Â₁₂ = 0.30), but p_Holm = 0.059 — raw p is 0.030, so it dies on the Holm correction over the family of 6. ⚠ **This is a correction**: at `MULTI_RUN_SIMS` = 200 the same line read 0.0534 against 0.0399 at p_Holm = 0.038, and the docs claimed dropping identity *costs* balance. The individuals are bit-identical; only the ruler changed. The λ = 0 arm is the noisier of the two (in-loop → out-of-loop inflation 3.21× against 2.58× on the old measurement), so the coarse ruler penalized it more, and part of what looked like an effect was the measurement erring against the noisier arm. The defensible claim is now *"identity does not cost balance"*, never *"it improves balance"*. Hard counters does not separate either (p_Holm = 0.180). The unseeded arm separates on **drift only** (0.2703 against 0.2473 in medians, p_Holm = 0.0073) and on nothing else, so initialization is not what the algorithm comparison is measuring. `multi_run` routes a run by what its body records: fully protocol → the battery paths; a **design**-only deviation (λ, dominance weights, selection, canonical seed, headline representative) with protocol sample and budget → `results/controls/` (citable); a **sample or budget** deviation (population, generations, number or start of seeds, sims) → `results/exploratory/`. `compare_algorithms --control` compares the battery with each control.

**`scalar_optimum` is the comparable for the scalar GA — and the headline.** The fifth representative minimizes `LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift` — the scalar GA's own function — and is the only place NSGA-II reads `LAMBDA_*` (reporting, never search; the front itself is λ-independent, so a λ comparison against it needs no NSGA-II re-run, only `front_objectives`). It is the headline representative (`multi_run.HEADLINE_REPRESENTATIVE`), decided before the battery on method: `best_dominance` is the front's extreme and loses on drift by construction, so as a headline it would measure the choice of point. `best_dominance` is the secondary comparison. Alongside, descriptive and outside the Holm family, the **per-seed Pareto relation**: the GA point (`in_loop_objectives`) against the **whole** NSGA-II front of the same seed, on the same last-generation stream — dominates a front point, is dominated, or neither. On the 2026-09-23 battery the two are **mutually non-dominated on 18/20 seeds**, with one seed each way: the scalar GA's point lies *past* the front's low-dominance end on **19/20** (0.017 against 0.05), buying balance with drift the front never offers. A claim about relative quality is only made from the battery: at a reduced budget the ordering reverses. **But being non-dominated is not being optimal at λ = 1/1: on the sum `dominance + drift` the front holds a better point on 20/20 seeds in-loop** (medians 0.2658 against 0.2052), 18/20 re-evaluated, 5/5 at 1000 fights — the scalar GA sits at an extreme of the trade-off rather than at its own optimum, because `dominance` is sampled and `drift` is not. Open finding, mechanism and the equal-budget hybrid that nearly dominates it: `docs/thesis/07-findings-and-limitations.md` §"O AG escalar não é ótimo na própria função" and `docs/reference/10-known-issues.md` §1. The geometric representatives (`knee_point`, `ideal_point`) use objectives **normalized by the front's range**, and the ideal is the point closest to the front's **utopia point**, not the origin — in raw units the scale of `dominance` decided the geometry (normalizing changed the ideal on 19/20 fronts, the knee on 0/20).

**Elitism 10% and tournament 3 are tested values.** Swept against elitism 0 / 5% / 20% / 30% and tournament 2 / 5 / 7: **no arm dominates the default**, which holds the best drift (0.2448) and the best rank agreement (τ = 0.415) of the eight. It is not best on every axis — elitism 0, elitism 5% and tournament 2 each land fewer hard counters (0.6 against 0.8) and a smaller `cap_term`, and each pays for it in drift and in τ. At n = 5 none of it separates from noise, so the claim is "tested, nothing beats them", not "optimal". Both are read only by `operators.py` in the parent process. `ELITE_RATE` is a **fraction** of the actual population size — an absolute count would silently turn a reduced-budget run into a clone machine. The sweeps run on seeds **1000–1004**, disjoint from the battery's 42–61: the sample that chooses a configuration is not the one that evaluates it.

**Process state for anything a run varies, and a persistent pool.** λ, the dominance weights, elitism, tournament and the combat rules are process state (`set_*` / `set_*_override`, `combat.set_rules`), because `from .config import X` freezes the value at import. What the workers read (seed base, λ, dominance weights, combat rules) travels in a `RuntimeState` with **every task** to the persistent pool (`fitness.parallel_map`) — so a live worker never evaluates under a stale seed base, weight or rule; covered by a parallel-vs-serial test that changes all of them between evaluations. The pool lives the whole process (3.87 s → 1.04 s per generation of 300), `N_WORKERS = min(8, os.cpu_count())` (the cap guards against `WinError 1455`). Overrides register in the provenance stamp (`provenance.override`), and `multi_run` routes every deviation from the protocol by the three-destination rule above, with the deviation in the name.

### Measurement

**Every artifact carries the configuration that produced it, and checks itself on load.** `src/engine/provenance.py` stamps every JSON in `results/`: timestamp, `fingerprint`, every public constant of `config.py` value by value, a digest of the canonicals (genes + `defining_genes` + `beats`), a digest of `src/engine/`'s source and — in the artifacts of `src/experiments/` tools — a **measurement digest**: the tool's own module plus every `src.` module outside the engine it imports, transitively (`provenance.measurement_modules`, derived from the imports), so changing the validator stales `baselines.json` and `multi_run` and nothing else. `Individual.from_results` / `from_nsga2` call `warn_if_stale` — the chokepoint every tool goes through — and the warning names what changed. **Reading warns; writing refuses:** a tool that writes an artifact from another (`compare_algorithms` from the `multi_run`s; `external_validation`, `baselines`, `sensitivity_analysis` from `single_run/*.json`) calls `refuse_if_stale` (`require_current=True`), because the new artifact is stamped with the *current* configuration and would otherwise launder an old number; a control arm is accepted when its divergence is exactly its declared override. Constants are **enumerated**, not hand-listed; the engine **source** is hashed, not only its constants; `config.py` is out of the source digest because its values are recorded one by one. `N_WORKERS` and `MULTI_RUN_N_SEEDS` are out of the stamp — neither changes a number in any artifact (the sample size is recorded in the `multi_run` body), and `compare` ignores excluded constants on the recorded side too. `Divergence.is_experiment_arm` separates a sweep arm from a stale artifact, strictly. Operating rules: re-stamp one artifact at a time, under its own overrides; a retroactive stamp is valid only by reproducing **that** artifact; the stamp does not cover command-line arguments, so each tool's default is the protocol value (`baselines` 30 null rosters, `multi_run` 20 seeds). A recorded number is measured on the **last generation's** stream (`generation_seed(seed, MAX_GENERATIONS)`) — reproducing it means reproducing that stream. **The digest is per module, not per symbol, and `src/analysis/analyze_matchups.py` mixes measurement (`behavioral_profile`, `wilson_ci`, `expected_winner`) with the CLI's printing, so editing a legend there stales `multi_run`, `baselines` and the external validation at once** — measured 2026-09-22; splitting the two is pending fix 4 in `docs/reference/10-known-issues.md`.

**`MULTI_RUN_SIMS` is its own constant, not `SIMS_CONVERGENCE_CHECK`** (both 200): the convergence confirmation runs *inside* the loop on every gate firing, the `multi_run` re-evaluation once per run on one individual. 200 sims resolves the n = 20 aggregates (measurement noise is symmetric across arms and the mean dilutes it) but **not a single roster**: the same roster's `dominance` varies 0.015–0.028 across streams, the order of its own evolved value (~0.04), and a two-arm verdict on 5 seeds **inverted** between 200 sims and a 1000-sim re-measurement on four streams. So: no per-seed conclusion and no small-sample arm comparison at 200. Raising it to 1000 costs 10k fights against the run's 67.5M but enters the config stamp, so it travels with the next battery — pending fix 5 in `docs/reference/10-known-issues.md`.

**Every post-hoc metric is read against a measured floor, never against the ceiling.** None of the identity metrics has a floor of zero: `src/experiments/baselines.py` measures them on 35 null rosters (5 mirrors + 30 random) — the validator's chance floor is ~6/23 with a null reaching 10/23, drift reads ~0.38 for a mirror (identity zero by construction) against ~0.41 for a random roster, the rank agreement τ reads ~0 (a null reaching 0.32), and the cycle's floor is 5/10 (every edge a coin flip). Every metric is reported as `position = (value − floor) / (ceiling − floor)` plus an empirical p-value (resolution 1/N). The **mirror roster is the trivial solution** to balance — the numeric answer to "why not make all five identical?" — and an evolved `dominance` level with the mirrors' is "as balanced as perfect symmetry, within noise", never "more balanced". The null rosters are **not** a control for the method (they are unoptimized); `LAMBDA_DRIFT = 0` is. **The authored cycle left `baselines` and became its own one-shot experiment** (`src/experiments/cycle_structure.py` → `results/cycle/cycle_structure.json`). It is a **declared premise, not a ruler**: it was never in the fitness (direction-blind by construction), and the canonical itself realizes only 6/10 of it. Measuring it per run at `MULTI_RUN_SIMS` could not work — a balanced roster's edges have a median margin of **0.048** against σ = 0.035 at 200 fights, so the count was noise (the same roster reads 5/10 at 200 fights and 8/10 at 16 000, and the mirrors, zero structure by construction, score 5.40/10 "kept" with 1.00/10 decided). The tool therefore runs 16 × 1000 fights per pair (σ = 0.0040) and counts only **decided** edges (`|WR − 0.5| > 2σ`), because an undecided edge is a coin toss in both directions. Groups are compared by the *rate* kept/decided, never the raw count: a random roster decides 10/10 edges and a balanced one 9.3/10, so the raw count would penalize the balanced roster for one edge sitting on the threshold.

**Reading (2026-09-22 measurement over the battery's 20 seeds): the cycle is not realized, with a weak non-significant lean in the authored direction.** The scalar GA keeps **105 of 186 decided edges (56.5%), binomial p = 0.091**; the 30 random nulls sit at 49.7% (p = 0.128, Â₁₂ = 0.63). NSGA-II is at 4.90/10 — chance to two decimals. Not "destroyed", not "preserved": *not distinguishable from chance*. Of the four edges the canonical breaks, all are total inversions (0.000–0.006): the Rushdown beats everyone and the Turtle loses to everyone, which makes the canonical a **pecking order (1.00 of 5 circular triads), not a cycle**. The GA is the one producing non-transitivity — 3.71 triads with 9.3/10 decided edges, against 0.40 for random rosters — though global balance with decided pairs largely *forces* that, so it is not independent evidence. `circular_triads` moved into the same tool for the same reason: the mirrors score 2.59 from pure noise. **Intransitivity** (`circular_triads`: 0 strict order / 2.5 random / 5 maximum) is largely *implied* by the objective — global balance with decided pairs forces it — and is meaningful only with decided pair WRs: at 200 fights a mirror reaches 4 triads by noise; the evidence of decided pairs comes from the 5000-fight external validation.

**The raw tables behind the post-hoc metrics live in `baselines.json`, not only on the terminal.** Every reference roster and the target carry, besides the aggregates, the three tables the aggregates are computed from: `per_gene_drift` (the normalized deviation gene by gene, via `drift_genes` — the same form `_archetype_deviation` compares, so the rows sum to the character's deviation), `differentiation` (mean pairwise distance between the 5, the homogenization reading) and `behavioral_profile` (the 10 behavioral metrics per character, recomputed under the seeding `run_validation` uses internally, so it is bit for bit the profile that produced Layer 3 and τ — not a second measurement). Without them the thesis would have to re-run a tool and read a terminal for two of the tables it presents. `src/analysis/` still writes nothing: it prints these same numbers, and `fingerprint` and `report` default to the protocol seed (`MULTI_RUN_VALIDATION_SEED`) and to `IDENTITY_BEHAVIORAL_SIMS`, so every path reports what the artifact records. The standalone `archetype_validator` still defaults to seed 42 and therefore prints a τ of its own (0.334 against the artifact's 0.314) — its source is inside the measurement digest of `baselines`, `multi_run` and `external_validation`, so changing that default would stale the whole battery without changing a single recorded number. Cite τ from `baselines.json` or `report`, never from the standalone validator.

**The identity instruments.** The validator (`archetype_validator`) counts a **tie against** the assertion (`_rank_against`: five identical characters no longer pass 4/13 Layer 1 assertions for free) and reads the behavior weights as **intention probabilities** (`Character.intention_probabilities`), so the weight scale — which does nothing in combat — cannot change the verdict. Layer 3 is 5 bits; the **behavioral rank agreement** (`rank_agreement`: Kendall τ-b between the canonical's and the roster's ordering of the 5 characters on each of the 10 behavioral metrics, averaged; 1 = canonical order, 0 = chance) is the continuous functional ruler, measured at `IDENTITY_BEHAVIORAL_SIMS = 200` (retest: 0.19–0.28 at 120 fights, 0.23–0.24 at 200) in the null models, the dossier and, per seed, the `multi_run`. Reading on the 2026-09-23 battery: functional identity is **above chance but only just, and its evidence is the control, not the nulls**. On one individual the resolution is too coarse to conclude — Layer 3 3/5 ties the best null (p = 0.03) and τ = 0.314 sits a hair under it (0.316, p = 0.06). Over 20 seeds against the `LAMBDA_DRIFT = 0` arm it separates cleanly: Layer 3 2.45 against 0.90 and τ +0.259 against +0.007, both p_Holm = 0.0002 with a large effect.

**External validation separates replication from robustness.** Each of two questions uses the 10 unseen seeds pooled into 5000 fights per pair: **replication** (training rules) and **robustness** (one combat rule perturbed at a time — `EXTERNAL_VALIDATION_RULE_PERTURBATIONS`: initial distance 40/60, field 80/120, persistence 4/6, guard reduction 0.55/0.65). Every WR is classified by its Wilson 95% CI against the band — inside, outside, inconclusive — and each condition is ROBUST / FRAGILE / INCONCLUSIVE. The verdict no longer grows stricter with the number of seeds, as "failed in *any* of K conditions" did, and seeds alone only tested sampling noise. On the 2026-09-23 battery the split is total: the **scalar GA is the only one of the four labels that replicates** (ROBUST, `dominance` 0.0373 out of loop against 0.0251 in it) and it survives 4/8 perturbed rules, 2 inconclusive, 2 fragile (`FIELD_SIZE = 80`, `ACTION_PERSISTENCE_SUBTICKS = 6`). The canonical and both NSGA-II representatives fail replication and all 8 rules.

**The comparison between two sets of runs** — GA × NSGA-II, or GA × a control — is the **paired Wilcoxon signed-rank** + Vargha-Delaney Â₁₂ + Holm over a **fixed family of 7 metrics**, the same in every comparison: balance (`dominance`, hard counters, characters in band) and identity (drift, structural validator, Layer 3, rank agreement); only a metric constant across the joint sample leaves it (not a test), reported descriptively. n = 20 seeds is the smallest with ≥ 80% power for a large effect.

**The test is paired because the design is.** `_check_comparable` requires both arms to run the *same* seeds, and a seed fixes everything random on both sides: `random.seed(seed)` gives the same initial population and the same operator draws, `generation_seed(seed, g)` the same evaluation stream at generation `g`. Run *i* of one arm and run *i* of the other are the same experimental block, not independent samples — which is what Mann-Whitney assumes. The unpaired test is *conservative*, not invalid, and it is still printed next to the paired one (raw, outside Holm) so a reader can check that no conclusion depends on the choice. ⚠ **The cell where the two used to disagree no longer supports a conclusion.** On the 2026-09-21 data the `LAMBDA_DRIFT = 0` control's `dominance_penalty` read p_Holm 0.063 unpaired against 0.038 paired, and the docs used the paired test to claim that dropping identity makes balance *worse*. On the 2026-09-23 battery, same individuals, finer ruler: 0.030 raw paired → **p_Holm = 0.059**, and the unpaired raw is 0.034. Neither survives Holm, and the claim is retired — see the control-arm paragraph above. The lesson about pairing stands on its own (the design *is* paired); what does not stand is a conclusion that lived inside the ruler's noise. On the 2026-09-23 battery `n_chars_balanced` is the constant metric in all four comparisons — every arm puts 5/5 characters in band on every seed — so the family is 6. GA × NSGA-II (`scalar_optimum`): **all six significant, all with a large effect** (p_Holm from 1.1 × 10⁻⁵ to 0.0027), and the split is clean — the scalar GA wins both balance metrics (`dominance` 0.0355 against 0.0759, Â₁₂ = 0.07; hard counters 0 against 3, Â₁₂ = 0.03) and NSGA-II wins all four identity metrics (drift Â₁₂ = 1.00, L1+2 0.05, Layer 3 0.24, τ 0.09). Against `best_dominance` the same six, same directions, slightly weaker (`dominance` 0.0355 against 0.0551).

**Sensitivity covers the 11 genes against the right floor.** Each gene is shifted over a 2σ window (σ = its own mutation step) that **slides inside** the bound instead of being clipped, and the noise floor is measured on the **same statistic** that is classified (mean over the 5 characters of |Δ WR|), not on single cells: 0.037 vs 0.068 on the same individual. On the 2026-09-23 individual the measured floor is 0.035 and the three policy weights sit at the bottom of the ranking — `w_defend` (0.029) and `w_aggressiveness` (0.030) below it, `w_retreat` (0.048) borderline, against `range` 0.308 at the top. The GA barely sees the policy through balance; the only gradient pulling it back toward canonical is the drift term's.

**Hypervolume reference `(1.3, 0.4)`**, anchored on the null models (the canonical's `dominance`, the mirror's drift): with the theoretical maxima (2.0, 1.0) the HV saturated at 90% of the area (CV 2.0% across seeds, now 2.9% — 0.3954 ± 0.0114 on the 2026-09-23 battery, unchanged from the previous one).

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
= o período do atacante mais rápido), `SIMS_PER_MATCHUP`,
`MAX_GENERATIONS`, `ELITE_RATE` / `TOURNAMENT_SIZE` (0.10 / 3, **testados**: nenhum dos
7 braços do sweep os domina), `GA_CANONICAL_SEED` (o controle sem semente),
`IDENTITY_BEHAVIORAL_SIMS` (200, medido em re-teste), `HYPERVOLUME_REFERENCE` ((1.3, 0.4),
ancorado nos nulos) e `EXTERNAL_VALIDATION_RULE_PERTURBATIONS` (as regras que a validação
externa perturba).
