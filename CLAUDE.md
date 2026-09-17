# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Instrução permanente (docs)**: a referência técnica detalhada vive em `docs/reference/` (índice em `docs/reference/README.md`) — um arquivo por tema (combate, AG, NSGA-II, config, tools, reprodutibilidade, known-issues, revisão do combate). O material de redação da tese fica em `docs/tcc/`. **Sempre que o código mudar, atualize o(s) `docs/reference/*.md` do tema afetado antes de encerrar a tarefa**, mantendo-os fiéis ao estado atual. Este CLAUDE.md é o guia operacional + resumo de decisões; o detalhe completo é dos docs.

> **Convenção de idioma**: nomes de arquivos e pastas em **inglês**; o **texto** dos `.md` e dos comentários pode ser em português (incl. `docs/reference/` e `docs/tcc/`).

> **Instrução permanente**: sempre que qualquer decisão de design do sistema for alterada — comportamento do combate, semântica dos parâmetros, lógica do GA, ciclo de vantagens, constantes do fitness, protocolo experimental — atualize **três** lugares antes de encerrar a tarefa:
> 1. a seção **Key Design Decisions** neste arquivo e o `docs/reference/*.md` do tema — ambos descrevem o **estado atual** do código, não o histórico;
> 2. **`docs/tcc/04-caminhos-e-decisoes.md`** — o **porquê**, no formato *problema → mudança → resultado*, com os números que sustentam a decisão. Este é o destino obrigatório: mensagem de commit, `REVIEW.md` e `HANDOFF.md` são registros de trabalho e **não** são consultáveis na hora de redigir. Uma decisão que só existe em commit está perdida para a tese.
>
> Vale também para decisões que **mantiveram** o valor vigente: "manteve-se X porque Y" é resultado, e sem o registro a justificativa se perde igual.

> **Padrão de qualidade**: este é um TCC a ser apresentado para banca. O código deve ser o mais limpo possível — sem variáveis mortas, sem campos diagnósticos desnecessários, sem rastros de decisões anteriores. Prefira nomes explícitos que se auto-documentem. Quando algo for removido, remova completamente — não deixe comentários explicando que foi removido.

> **Foco no sistema, não na narrativa pra banca**: enquanto estamos refinando mecânicas, o objetivo é deixar o sistema o mais redondo possível. **Não** antecipar inline em respostas como o usuário deveria justificar X ou Y resultado para a banca — isso é prematuro enquanto há pontos a refinar. Pontos relevantes para a redação da tese vão para `docs/tcc/` (destrinchado por tema — ver `docs/tcc/README.md`), não para discussão inline. Discutir "defensibilidade na banca" só quando o usuário pedir explicitamente.

## Project Context

TCC (undergraduate thesis) — Genetic Algorithm for competitive game character balancing.  
**Research question:** Can a GA achieve competitive balance between 5 distinct archetypes without destroying their functional identities?

The canonical archetype values are *not* hardcoded constraints — they serve as an initial population seed and as a deviation measurement baseline. The GA evolves freely; archetype deviation is penalized in the fitness via `LAMBDA_DRIFT` (and exposed as a Pareto objective in NSGA-II), but never hard-constrained.

**The line that keeps the question non-circular: the fitness may encode the *premise*, never the *answer*.**

| | what it is | where it lives |
|---|---|---|
| **premise** | what each archetype **is** — canonical values and `defining_genes`. Given by the FGC, prior to and independent of the balance question | **may** be in the fitness (`drift_penalty`) |
| **answer** | who beats whom (`beats`), whether balance and identity are compatible at all | **never** in the fitness — post-hoc metrics only |

"The Zoner is defined by range" is a premise; "the Zoner should beat the Grappler" is an answer. Encoding the latter would answer the research question with itself. Hence the asymmetry: identity *is* a fitness term, the advantage cycle is not.

A penalty is not a constraint, and the distinction is empirical here, not rhetorical: with `LAMBDA_DRIFT = 1.0` active the whole run, the scalar GA still traded identity away for balance (validator 8/21). The term exists and can lose.

**Two rulers for identity, one on each side of the line:**
- **structural identity** (`drift_penalty`, in the fitness): are the genes still recognizable? Weighted toward each archetype's `defining_genes`. The validator's Layers 1-2 measure this same axis, so they are **partially endogenous** — a good score there partly reflects the penalty working.
- **functional identity** (validator **Layer 3** + the advantage cycle, post-hoc, never in the fitness): does the character still *play* like itself? Nothing in the fitness references behavior. The research question says "functional identities" — this is the ruler that answers it.

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
│   │   ├── baselines.py       # modelos nulos: piso/teto de cada métrica post-hoc
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
py -m src.tools.report --evolved                 # dossiê completo do indivíduo, já com os modelos nulos (porta de entrada)
py -m src.tools.analyze_matchups                 # all matchups, canonical (default 1000 sims)
py -m src.tools.analyze_matchups rushdown zoner  # specific matchup
py -m src.tools.drift_table --evolved            # drift por gene + diferenciação
py -m src.tools.fingerprint --evolved            # assinatura comportamental
py -m src.tools.archetype_validator              # identity checks: structural (L1-2) + behavioral (L3)
py -m src.tools.baselines --evolved               # modelos nulos: posição de cada métrica entre piso e teto
py -m src.tools.sensitivity_analysis --evolved   # ±σ Δ-WR per gene, contra piso de ruído MEDIDO
py -m src.tools.multi_run --algorithm both       # N execuções + estatística agregada (metodologia 1.1)
py -m src.tools.compare_algorithms               # AG × NSGA-II: Mann-Whitney U + Â₁₂ + Holm
py -m src.tools.external_validation --nsga2 best_dominance  # robustez do equilíbrio fora do laço (metodologia 3.2)

# Web viewer (opens browser at localhost:8080)
py -m src.tools.web_viewer

# Smoke tests (run individually — no test runner configured)
py -m src.tests.test_base
py -m src.tests.test_baselines
py -m src.tests.test_combat
py -m src.tests.test_fitness
py -m src.tests.test_ga
py -m src.tests.test_operators
py -m src.tests.test_nsga2
py -m src.tests.test_archetype_validator
py -m src.tests.test_compare_algorithms
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
| `results/baselines.json` | `py -m src.tools.baselines` (rosters de referência + piso/teto/posição de cada métrica) |

## Architecture

The system has two independent layers that the GA orchestrates:

**Simulation layer** (`src/engine/combat.py`):  
Tick-based 1v1 combat. Each tick: choose **stance** via intention → apply simultaneous movement (with collision) → resolve attacks → decrement timers. **Two action channels:** the sampled intention governs only the *stance* (ADVANCE / RETREAT / DEFEND), while the *attack* is a resolution rule — it fires whenever cooldown is ready, the opponent is within range (post-movement) and the stance is not DEFEND. Advancing and retreating both hit; only GUARDA gives up the blow. That is what makes space control a strategy (zoning = attacking while holding distance) and what gives `knockback` a positive slope. **Intention:** sampled from `{FRENTE, RECUAR, GUARDA}` proportional to `(w_aggressiveness, w_retreat, w_defend)` and **held for `ACTION_PERSISTENCE_SUBTICKS` sub-ticks** (commitment/momentum); FRENTE → ADVANCE, RECUAR → RETREAT if there is room else DEFEND (cornered), GUARDA → DEFEND. The intention always applies, **except in an impasse** (`distance > own range` AND `distance > opponent's range`), where ADVANCE is imposed — without it two passive characters back off to opposite walls and time out without a blow. The intention sampling is the **single source of stochasticity**. Key mechanics: bodies **do not pass through each other** (`_apply_movement` moves both from the start-of-sub-tick positions and stops them at the meeting point; A is always the left side); `attack_cooldown` is deterministic; **stun = `stun × attack_cooldown × TICK_SCALE`**, a **continuous** timer — `stun` is a gene in `[0, 0.6]` expressing a **fraction of the attacker's own cooldown** (in sub-ticks); since the bound is `< 1.0`, applied stun is always strictly less than the cooldown, guaranteeing a free window for the defender (no explicit `STUN_CAP_MULTIPLIER`). Damage is **flat** (`damage`); the only modifier is the target's DEFEND, which multiplies incoming damage by `DEFEND_DAMAGE_REDUCTION` (0.6 = `1 − 0.4` → 40% reduction) — **less whatever the attacker's `grab_power` breaks through**: against a DEFENDING target the multiplier becomes `defend_red + grab_power` (`combat.py`, the grab block), so `grab_power = 0` leaves the full reduction (0.6×), the neutral point `1 − defend_red = 0.40` cancels it exactly (1.0×), and above that guarding becomes a liability — 1.6× at the cap. Against a target that is **not** defending, `grab_power` does nothing at all: that is what makes the grab a counter to guard rather than a better attack, and it means the grab never exceeds a clean hit. There is **no `defense` gene** and **no `recovery` gene**. A fight ends in KO, timeout (higher HP%) or **draw** (`winner = -1`, identical HP% — double KO or a timeout with no difference), which counts as half a win for each side. Timers are decremented **after** attacks — values freshly set by an attack are not decremented until the following tick. Reproducibility: combat RNG is Numba-internal; seed it only via `seed_combat()` (`np.random.seed` from Python does nothing).

**GA layer** (`src/engine/ga.py`, `src/engine/fitness.py`, `src/engine/operators.py`):  
Each individual = 5 characters (one per archetype) = 55 genes total (8 attrs + 3 weights per character). Fitness is evaluated via full round-robin (C(5,2)=10 matchups × `SIMS_PER_MATCHUP` simulations). Fitness formula (scalar GA): `fitness = -(LAMBDA_DRIFT × drift_penalty + LAMBDA_DOMINANCE × dominance_penalty)` — the **same two terms the NSGA-II optimizes**, here as a weighted sum (scalar GA = one point of the trade-off NSGA-II maps — a claim that is **measured, not assumed**: see Key Design Decisions). `drift_penalty` is the mean per-character **weighted** RMS of normalized gene deviations from the canonical profile (structural identity, and the real anti-homogenization mechanism). It compares `fitness.drift_genes(char)`, not the raw genes: the 8 attributes pass through untouched while the 3 behavioural weights are **rescaled to the canonical sum**, because intention is sampled *proportionally* to them — scaling all three by `k > 0` changes nothing in combat, so charging identity for it measured noise (7.5% of mean drift, worst case Rushdown 15.1%; the optimal `k` of 0.58–0.70 shows the GA was inflating the weight scale and drift was billing the inflation). Three further things make it sharper than a plain euclidean distance: normalization is by the **bound's range** `(x − lo) / (hi − lo)`, not by `hi` (dividing by `hi` underestimates genes with a high `lo` — HP runs 250→450, so moving 162 is 81% of the range, not 36% of the max); and each archetype's `defining_genes` weigh `DRIFT_DEFINING_WEIGHT` (3.0) against 1.0 for the rest, so moving the Zoner's range costs more than moving its stun. `dominance_penalty` (**C2 formulation**) is `DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term` (max 2.0). **Primary term** `global_term = RMS over the 5 characters of |WR_global − 0.5| / 0.5` — *no archetype globally dominates the roster*. It does **not** force every pair to 50%: a character at 50% global can beat 2 and lose 2 — the space where the advantage cycle can live. (The old primary was per-matchup WR, whose optimum is *every pair at 50%* = flat balance, incompatible with a cycle by construction.) **Secondary `cap_term`** = RMS over the 10 pairs of the excess of `|WR_par − 0.5|` above `MATCHUP_WR_CAP` (hard-counter ceiling: keeps cycle edges as advantages within `[0.35, 0.65]`, bars crushing counters like 100×0). **Secondary `decis_term`** = RMS over the 10 pairs of per-fight decisiveness `D = mean(|score − 0.5|)` outside the band `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]` = [0.02, 0.20]; per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The **ceiling** is the working guard: it bars blowout-coinflip (55% A-crush / 45% B-crush — global WR ~50%, every fight a massacre). The **floor** is only a degeneracy guard and sits far below the operating range (see Key Design Decisions). **NSGA-II** ignores all `LAMBDA_*` constants — `evaluate_objectives` returns `(dominance_penalty, drift_penalty)` raw; the Pareto front is computed in those two unweighted dimensions.

**Data model** (`src/engine/archetypes.py` → `src/engine/character.py` → `src/engine/individual.py`):  
`ArchetypeDefinition` (frozen, canonical values) → `Character` (mutable genes, 8 attrs + 3 weights) → `Individual` (list of 5 Characters + fitness cache). `Individual.from_canonical()` creates the canonical seed; `Individual.random()` creates a random individual.

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

**Intention persistence** (`ACTION_PERSISTENCE_SUBTICKS = 5`): once sampled, an intention is reused for the next 5 sub-ticks instead of resampling every sub-tick. This simulates commitment/momentum and prevents pathological flip-flopping. The intention is **never interrupted mid-window**, except by the impasse rule (which forces ADVANCE and zeroes the counter) or by being stunned. **5 is exactly one tick (`TICK_SCALE`) and exactly the minimum cooldown**, so a `attack_cooldown = 1` character that draws GUARDA gives up exactly one attack window. It was 10, which made that cost two windows by an accident of scale — and the measurement agreed with the coherence argument: dropping to 5 raises the signal-to-noise ratio on **8/8 genes**, `speed` +81% and `stun` +80% (both were below the measured noise floor at 10). High persistence pays twice: fewer independent decisions per fight means less room for a gene to express itself **and** more variance in the outcome (noise floor 3.5% at 5 versus 4.9% at 10).

**Collision and cornering.** Bodies do not pass through each other: `_apply_movement` displaces both from the start-of-sub-tick positions (simultaneous — neither side arrives "first") and, when two advances would cross, both stop at the meeting point. A is therefore always the left side (`pos_a ≤ pos_b`), which removes the direction edge cases at distance zero. Cornering exists as a consequence — RETREAT backs off to the wall and falls to DEFEND — and `CombatTrace.forced_defend` keeps that forced DEFEND separate from the chosen one (GUARDA), so geometry does not contaminate the defensive-identity metric.

**Timer decrement order**: Decrements happen at the END of each tick (after attacks), using pre-attack timer values to decide what to decrement. Timers freshly set by an attack (`current > pre`) are preserved until the next tick. This means `stun=1` blocks the target for exactly 1 tick, and `attack_cooldown=1` forces a 1-tick wait before the next attack.

**TICK_SCALE sub-tick resolution**: All timers and movement operate in sub-tick units (TICK_SCALE=5):
- Movement per sub-tick: `speed / TICK_SCALE`
- Cooldown on hit: `round(attack_cooldown * TICK_SCALE)` — integer
- Stun on hit: `stun * attack_cooldown * TICK_SCALE` — **continuous** (float timer, decremented by 1.0 per sub-tick). `stun ∈ [0, 0.6]` is a fraction of the attacker's own cooldown in sub-ticks; the bound `< 1.0` guarantees applied stun < cooldown (no explicit cap constant). Rounding it used to leave the gene with only 4 effective levels for a `cooldown = 1` attacker.

Toda a lógica de combate vive **exclusivamente** dentro do JIT (`_simulate_combat_jit` para o fitness, `_simulate_combat_traced_jit` para tools), com **postura, movimento e desfecho compartilhados** nos helpers `_decide_action`, `_apply_movement` e `_decide_winner` (chamados por A e B nas duas variantes — sem cópias divergentes). Não há reimplementação Python do loop — tools que precisam instrumentar consomem `CombatTrace` em vez de redobrar a lógica. O `CombatTrace` expõe `stance`, `attacked` (canal de ataque) e `forced_defend` (1 = DEFEND por encurralamento, distinto do GUARDA escolhido) para a separação de identidade defensiva.

**The evaluation stream rotates per generation; CRN holds within one.** The combat RNG is reseeded before every evaluation, and `fitness.generation_seed(base, generation)` is the single definition of *which* stream a generation uses — consumed by **both** loops, because if only one rotated the GA × NSGA-II comparison would confound "algorithm" with "way of evaluating". Within a generation every individual faces the identical stream (Common Random Numbers), so a fitness difference reflects genes rather than luck — correct for *selection*. Between generations the stream changes. Without that change `set_seed_base(seed)` ran **once** and the whole budget of generations optimized against a single RNG realization: the population had `MAX_GENERATIONS` attempts to fit one specific sequence of draws rather than the game. Measured (5 seeds, 60 generations, scored on 5 unseen streams): the ratio between in-loop and out-of-loop `dominance` falls from **4.14 to 2.20**, improving in **5/5** seeds (paired Wilcoxon p = 0.0312), and rosters that stay balanced out-of-loop go from 2.6 to **4.8** of 5, also 5/5 (p = 0.0312). The **magnitude** of the balance gain is *not* established (out-of-loop `dominance` improves in 3/5, p = 0.31) and drift costs nothing (0.2924 → 0.2968) — what the evidence supports is that the result now *survives unseen streams*, not that the GA got 17% better. It also converges more reliably: under a fixed stream 2 of 5 seeds never converged, under rotation 5/5 did, later (19–36 vs 14–26). The principle is one the project already adopted one level down — the convergence *confirmation* runs out-of-stream because "CRN is right for selection and wrong for validation"; rotation applies the same rule to the search that produced the individual being confirmed. Cost: ~1.8× in the scalar GA (the 30 elites arrive measured on the previous stream) and **~2× in NSGA-II**, where non-dominated sorting compares parents and offspring inside one `combined` set and objectives from different streams are not comparable — the parents must be re-evaluated too. Declared consequence: fitness now fluctuates between generations from the stream change, so the stagnation counter resets on noise and **`stagnated_at` is less reliable**; `converged_at` is unaffected because convergence tests the `roster_balanced` predicate, not the fitness value.

**Two fitness terms** = the thesis's two axes: identity (`drift_penalty`) and balance (`dominance_penalty`). Scalar GA = weighted sum; NSGA-II = same two as unweighted Pareto objectives. "The scalar GA is one point of the trade-off NSGA-II maps" is the claim this pairing is meant to support — measured at matched budgets (pop 120, 150 generations, 80 sims, seed 42) it is **still not literally true, but no longer for the old reason**: the scalar's point reaches `dominance` 0.0088, below the front's entire range [0.0346, 0.9585], so it sits *past* the front's low-dominance end rather than on it (it dominates 3 of 49 front points; none dominate it). Meanwhile NSGA-II now wins on the scalar's **own** objective — `scalar_optimum` L1 0.2115 vs the scalar's 0.2945. Each algorithm reaches a different part of the trade-off and neither is sub-converged; that is the honest statement, and it replaces the earlier finding that the scalar's point dominated a sub-converged front. (Homogenization — "are the 5 still distinct?" — is a post-hoc metric, not a fitness term, by the same non-circularity logic as the cycle.)
- `drift_penalty` (via `LAMBDA_DRIFT=1.0`, equal to dominance) penalizes deviation from canonical values — the central trade-off of the thesis, and the real anti-homogenization mechanism. (Was 6.0, which pinned the GA to canonical and prevented balancing — see `docs/reference/10-known-issues.md` V1.) It measures **structural** identity only; functional identity stays post-hoc (see Project Context).
- `dominance_penalty` (via `LAMBDA_DOMINANCE=1.0`, **C2 formulation**) = `DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term` (weights 1.0 / 0.5 / 0.5; max 2.0). **Primary `global_term`** = RMS over the 5 characters of `|WR_global − 0.5| / 0.5` — *no archetype globally dominates the roster*. It does **not** force every pair to 50%: a character at 50% global can beat 2 and lose 2 — the space where the advantage cycle can live. (The old primary was per-matchup WR, whose optimum is *every pair at 50%* = flat balance, **incompatible with a cycle by construction** — see `docs/reference/11-combat-review.md` and `docs/tcc/02-ciclo-canonico.md`.) **Secondary `cap_term`** = RMS over the 10 pairs of the excess of `|WR_par − 0.5|` above `MATCHUP_WR_CAP` (hard-counter ceiling: cycle edges stay as advantages within `[0.35, 0.65]`, crushing counters like 100×0 are barred). **Secondary `decis_term`** = RMS over the 10 pairs of per-fight decisiveness `D = mean(|score − 0.5|)` outside the band `[MATCHUP_FLOOR, MATCHUP_THRESHOLD] = [0.02, 0.20]`; per-fight score is continuous (KO: `0.5 + 0.5·winner_HP_frac`; timeout: HP-share). The ceiling guards against blowout-coinflip (55%/45% crush each way, global WR ~50% but every fight a blowout); the floor only guards against degeneracy. The graded WR that makes this a usable gradient comes from the intention-sampling noise once fights are close. The three terms are kept **separate** in `DominanceTerms` and reported decomposed by `multi_run` / `compare_algorithms` — the composite alone hides whether a difference came from the primary term or from a secondary one at half the weight.

**Direction-blind dominance is intentional**: the penalty uses `|WR − 0.5|` and `|score − 0.5|` — it does not encode which archetype "should" win each matchup. Encoding the canonical advantage cycle into the fitness would force the GA to preserve identity, making the central research question circular. The cycle is tracked as a post-hoc evaluation metric only.

**Convergence is a recorded event, not a stop — both algorithms run a fixed budget.** `ga.run` always completes `MAX_GENERATIONS`; convergence and stagnation are recorded as `converged_at` / `stagnated_at`. The reason is the comparison: NSGA-II *cannot* stop by the scalar GA's criterion — "is the roster balanced?" is not a question one asks of a **front**, which deliberately contains unbalanced-but-faithful points, and asking it of a representative makes the answer depend on an arbitrary choice. Stopping the scalar early would make "better" indistinguishable from "used less budget". With both on a fixed budget the comparison is **quality at equal budget**, and `converged_at` becomes a second axis — **speed** — that did not exist before.

**Convergence criteria** (C2) — **the same predicate, twice, on different samples**: `roster_balanced(detail)` must hold on the in-loop evaluation (the cheap gate, on numbers already in hand) **and** survive re-evaluation with `SIMS_CONVERGENCE_CHECK` extra simulations **on an RNG stream the GA never saw** (`seed + CONVERGENCE_SEED_OFFSET`, via `_confirm_convergence`). `roster_balanced` is **(a)** every character's **global** WR within `GLOBAL_CONVERGENCE_THRESHOLD` (0.10) of 50% — no one dominates the roster — **and (b)** no pair is a hard-counter, every `|wr_par − 0.5| ≤ MATCHUP_WR_CAP` (0.15). It does **not** require each pair at 50% (cycle edges are allowed). It lives in `fitness.py` alongside `character_balanced` and `is_hard_counter`, as the single source consumed by GA convergence, `multi_run`'s per-seed verdict and the reporting tools.

Using the criterion itself as the gate is what makes convergence **reachable at all**. The old gate was a scalar threshold on the composite, `dominance_penalty ≤ 1e-9`, and it was unsatisfiable *by construction*: `global_term` is an RMS over discrete counts, so with 4 × `SIMS_PER_MATCHUP` fights per character its smallest non-zero value is `(1/600)/0.5/√5 ≈ 0.0015` — there is no continuum between 0 and that, so `1e-9` meant *exactly zero*, i.e. all 5 characters at exactly 300/600 in the same evaluation. `converged` was always `False` and the whole confirmation branch was dead code described in the methodology. Raising it to some calibrated scalar would have kept a milder version of the same bug: the composite includes `decis_term`, which is **not** part of the convergence definition, so a genuinely converged roster with decisive fights would still be blocked. Testing the predicate directly has no such gap.

**The confirmation runs out-of-stream, and that is the point.** The loop evaluates every individual under the same stream (Common Random Numbers) — correct for *selection*, since fitness differences then reflect genes rather than draws. But re-evaluating on that same stream confirms nothing: it measures the same RNG realization with more samples, and the confirmation cannot disagree with the gate. Measured on an individual that passed: balanced under the training seed (5/5 in band, 0 hard counters) and **not balanced under four independent streams** (5/5 in band but 1-2 hard counters each) — the fitting to the stream concentrates in the pairwise term, never in global WR. So the confirmation reseeds to `seed + CONVERGENCE_SEED_OFFSET` (100000, chosen to collide with no other seed family: training 42+, `MULTI_RUN_VALIDATION_SEED` 9999, `EXTERNAL_VALIDATION_SEED_START` 10000+) and restores the training base afterwards. Converging now means *the balance survives a stream the GA never saw*, and the `best_detail` the GA returns is an out-of-sample measurement. Expected and accepted consequence: convergence becomes much rarer — measured on a short run (pop 120, 60 generations, seed 42), the gate fired **16 times** and the out-of-stream confirmation rejected **all 16**, which is that over-fitting quantified.

**Canonical calibration rules** (bounds e canônicos re-tunados ao novo modelo — **provisórios, a calibrar**):
- HP range: 250–450; Damage range: 15–30. Canônicos HP: Zoner=300, Rush=320, CM=350, Grap=400, Turtle=450 (Turtle no teto do bound); dano: Zoner=20, Rush=16, CM=18, Grap=27, Turtle=15
- All `range` values ≤ 20 < `INITIAL_DISTANCE` (50) — no character can attack from tick 1
- `attack_cooldown` ∈ [1, 5]: Rushdown=1 (fastest), Turtle=5 (slowest), Grappler=4
- `stun` ∈ [0, 0.6] — **fração** do cooldown do atacante (não valor absoluto), aplicada como timer contínuo; bound `< 1.0` garante stun < cooldown. Canônicos: Zoner=0.10, Rush=0.10, CM=0.55, Grap=0.30, Turtle=0.20
- `knockback` ∈ [0, 3]: teto razoável acima do Zoner (2), evita zoning trivial via expulsão de range
- `grab_power` ∈ [0, 1] — **fração da guarda quebrada**; só tem efeito contra alvo em DEFEND. Canônicos: Grappler=0.90 (o especialista, e o 2º gene definidor dele), CM=0.30, Rush=0.20, Turtle=0.15, Zoner=0.05
- **Não há mais `defense` nem `recovery`** — dano é flat (só DEFEND e o agarrão o modificam) e o stun bruto é aplicado direto. 8 atributos por personagem
- Behaviors expressed via `w_*` weights (3 per character: `w_retreat`, `w_defend`, `w_aggressiveness`)
- `w_aggressiveness >= 0.7` → aggressive archetypes (Rushdown, Grappler, Combo Master) push through threats
- `w_retreat > w_defend` → reactive archetypes (Zoner) kite; `w_defend >= w_retreat` → absorbers (Turtle) hold ground

**Cooldown only on hit**: o cooldown do atacante só é setado dentro do bloco de resolução, que só executa quando o golpe conecta (`cd_rem == 0 and distance ≤ range` com a distância **pós-movimento**, e postura fora da guarda). Como o ataque virou regra de resolução e não ação escolhida, não existe mais o conceito de "whiff": um golpe fora de alcance simplesmente não acontece e o cooldown segue intacto.

**Stun as a continuous fraction (no `recovery`, no explicit cap)**: `stun ∈ [0, 0.6]` is a fraction of the attacker's own cooldown; applied stun `= stun × attack_cooldown × TICK_SCALE` is always strictly less than the cooldown (bound `< 1.0`), so the defender always gets a free window — this replaces the old `STUN_CAP_MULTIPLIER`. The timer is a float, decremented by 1.0 per sub-tick: the previous `round()` collapsed the gene to 4 effective levels for a fast attacker, and its amplitude at ±1σ of mutation went from 6.8% to 17.4% when the rounding came out. There is no longer a `recovery` gene subtracting from incoming stun, nor a `defense` gene reducing damage; all genes are continuous floats (no `INTEGER_ATTRIBUTES`).

**Structural identity: weighted drift, normalized by the bound's range.** `_archetype_deviation` is a **weighted RMS** over the 10 genes, `sqrt(Σ wᵢ·dᵢ² / Σ wᵢ)`, where `dᵢ = (gene − canonical) / (hi − lo)` and `wᵢ = DRIFT_DEFINING_WEIGHT` (3.0) for the archetype's `defining_genes`, 1.0 otherwise. `defining_genes` is a frozen field of `ArchetypeDefinition` mirroring the validator's Layer 1 inter assertions — the genes in which the archetype holds an extreme rank by design (Zoner: range/knockback/w_retreat; Rushdown: speed/attack_cooldown/w_aggressiveness; Combo Master: stun; Grappler: damage; Turtle: hp/attack_cooldown/speed/w_defend). Measured on the four reference individuals: the **range normalization** is what fixes the *ordering* — under the old `x / hi` the scalar GA (validator 8/21) read as less drifted than NSGA-II's `best_dominance` (11/21), inverting the identity ranking; with `(x − lo)/(hi − lo)` the drift ordering matches the validator's at every weight. (The validator's own Layer 2 uses the same normalization, so its scores were re-measured after the fix: knee 19/21, ideal 16/21, best_dominance 11/21, scalar GA 8/21 — the 2026-09-10 audit recorded 20/16/13/7 under the old convention.) The **weighting** then widens the margin: the AG−best_dominance gap goes 0.017 (uniform) → 0.043 (weight 3.0) → 0.073 (weight 12, saturating). 3.0 keeps non-defining genes meaningfully priced instead of nearly free. Same convention in the validator's Layer 2 and in `drift_table` — one definition of "normalized" across the project.

**The decisiveness term is a guard on both ends, and both ends are live.** The ceiling (`MATCHUP_THRESHOLD = 0.20`) bars blowouts; the floor (`MATCHUP_FLOOR = 0.02`) bars degeneracy. The floor was `0.10` and pushed **against** the primary term — balancing makes fights closer, and the floor punished exactly that; measured, it penalized 5/10, 5/10 and 3/10 pairs on the three evolved individuals, which is what decided the GA × NSGA-II comparison rather than the primary term. The premise behind it does not hold in the reformed engine: **every fight ends in KO** (100% over 70 pairs, random rosters included), so a low `D` is never "the fight did not happen" — it is a KO at the wire, the best possible fight.

`decis_term` reads **exactly 0.0000 on the final individual of all 10 seeds in both algorithms**, and that is the guard *working*, not a dead term — measured over 18 rosters / 180 pairs (2026-09-16): the **canonical** (which *is* the scalar GA's generation 0) reads 0.2834 with 5/10 pairs over the ceiling; 8 random rosters read 0.10–0.66 with 3–9/10 over it; 57/180 pairs breach the ceiling overall and observed `D` reaches 0.49 against a ceiling of 0.20. The search leaves that region; the term is what makes it leave. The two halves catch different things: the ceiling catches blowout (canonical, randoms), the **floor catches the trivial solution** — the Zoner mirror reads `D ∈ [0.016, 0.019]`, 10/10 pairs under the floor. Measured mirror bands are wider than previously recorded (Zoner 0.016–0.019 · Turtle 0.027–0.032 · Rushdown 0.030–0.035 · Combo Master 0.045–0.052 · Grappler 0.074–0.088), so the floor is **not** below every mirror — it is below every pair of *distinct* characters, and it fires 0/10 on all four evolved rosters.

**`MATCHUP_WR_CAP = 0.15` is anchored to the FGC matchup grid, not chosen round.** Matchup charts are stated in whole numbers — 5-5, 6-4, 7-3, 8-2 — which in `|WR − 0.5|` are 0.00, 0.10, 0.20, 0.30. Domain consensus: 6-4 is a healthy advantage present in every game, 7-3 is a counter. So the cap must **permit** 0.10 and **bar** 0.20. It must not land *on* a grid point, because a threshold flush against a legitimate value is a coin flip under binomial noise (σ ≈ 0.040 at `SIMS_PER_MATCHUP`): at cap 0.10 a true 6-4 trips **50%** of the time; at cap 0.20 a true 7-3 is caught **50%** of the time. At 0.15 — the midpoint of the only gap that matters — a true 6-4 trips 10.6% and a true 7-3 is caught 90.9%. Raising sims narrows both tails without moving the cap.

**Dominance is reported decomposed.** `_dominance_penalty` returns a `DominanceTerms` (`global_term`, `cap_term`, `decis_term`) and `FitnessDetail` carries it; `multi_run` writes the three per seed and aggregated, and `compare_algorithms` prints them side by side as a **descriptive** table. They are deliberately **not** added to the Mann-Whitney battery — extra metrics would inflate the Holm correction on the ones already there (open item F). Losing on the primary term (weight 1.0) and losing on a secondary one (weight 0.5) are opposite readings of the same composite, and the composite alone cannot tell them apart.

**NSGA-II starts from a fully random population; the scalar GA keeps the canonical seed.** A deliberate asymmetry, forced by an asymmetry between the two objectives: **`drift` has a floor of 0 and the floor is reachable** — the canonical *is* the reference, drift exactly 0.0000 — while `dominance`'s floor is not. Dominating `(1.2418, 0.0000)` would require `drift < 0`, which cannot exist, so the canonical is **immortal in rank 0** however unbalanced it is, and the same protection extends to its low-drift neighbourhood. Crowding does not clean it up: it only prunes when a front **overflows** the population, and `front0` (78) never exceeded 120. Measured (pop 120, 60 generations, seed 42 — initialization the only difference): min `dominance` on the front 0.2233 (stalled: −0.3970 over the first 30 generations, −0.0338 over the last 30) vs **0.0896** without the seed (still falling at gen 50); points with `dominance ≥ 1.0` — as unbalanced as the untouched canonical — 40/78 vs **1/44**; front drift coverage [0, 0.161] vs [0.124, 0.300], i.e. with the seed the front never reached the region where balanced rosters actually live. Half the front was consuming a third of the population *and a third of the reproductive effort*. In the **scalar GA the same seed helps** and stays: fitness is a single number (`−(drift + dominance) = −1.2418`), so the canonical loses and disappears after donating genes through crossover — measured, the scalar ends at drift 0.2874 with the seed and 0.3365 without, at the same dominance. This removes the acute cause (drift = 0 for free at generation 0), not the structural asymmetry — NSGA-II selects for low drift, so the population marches there on its own; see `docs/reference/06-nsga2.md` for the remedy shortlist if the cloud returns.

**`scalar_optimum` is the honest comparable for the scalar GA.** `select_representatives` returns five points; the fifth minimizes `LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift` — the **same function the scalar GA optimizes** — and is the only place in NSGA-II that reads the `LAMBDA_*` constants (reporting, never search). The claim "the scalar GA is one point of the trade-off NSGA-II maps" is only testable against that point; `ideal_point` minimizes the **L2** norm, which is a different point, and it was what the comparison had been using.

**Every post-hoc metric is read against a measured floor, never against the ceiling.** None of the project's identity metrics has a floor of zero, and all three were being read as if they did. Measured (`src/tools/baselines.py`, 13 null rosters — 5 mirrors + 8 random): the **validator**'s chance floor is ~6.8/21 and a *random* roster reached **12/21**, because rank assertions resolve ties by index and some pass by accident; **drift** reads ~0.33 for a mirror (five identical characters — identity zero by construction) and ~0.41 for a random roster, so only ~0.04 separates "identity carefully preserved" from total annihilation; the **canonical cycle** floor is 5/10, since every edge is a coin flip. Reading `8/21` as "38% of identity survived" is the same error as reading 20% on a five-option multiple-choice test as "knows 20% of the material". So every metric is reported as `position = (value − floor) / (ceiling − floor)` plus an **empirical p-value** (what fraction of null rosters match or beat it) — the floor is a *distribution*, not a point.

Two consequences worth stating plainly. First, the **mirror roster is the trivial solution** to balance (perfect balance, zero identity) and it is the numeric answer to the obvious objection "why not just make all five identical?" — measured, the evolved roster reaches 99% of mirror-level balance while sitting ~30% above the identity floor (p ≈ 0.08 with 13 nulls: suggestive, not established). Second, **the authored cycle cannot be a result**: it is a *regular tournament* (each archetype beats exactly 2), and there are **24** labelled regular tournaments on 5 vertices, so hitting the specific one is a 1-in-24 lottery while the chance score is 5/10. What *is* a result, and needs no authorship, is **intransitivity itself** — global WR balance and rock-paper-scissors are the same structure, since a strictly transitive roster has WRs 100/75/50/25/0, incompatible with everyone near 50%. `circular_triads` measures it on a 0 (strict pecking order) / 2.5 (random) / 5 (maximum = perfectly balanced) scale, and is only meaningful when the pair WRs are decided rather than noise.

**The grab is a conditional on attack resolution, not a fourth action.** `grab_power ∈ [0, 1]` (8th attribute) is what the grab **adds to the damage multiplier against a guarding target**: that multiplier is `defend_red + grab_power`. At `0` the guard gives its full 40% reduction (0.6×); at the **neutral point** `1 − defend_red = 0.40` the guard is exactly cancelled (1.0×); above it the guard becomes a **liability**, up to 1.6× at the cap. Canonically **only the Grappler (0.90 → 1.50×) is above the neutral point** — against the other four, guarding still pays. That is the mechanism that differentiates the Grappler and that realizes the cycle edge's stated justification. Two further deliberate properties make it a **counter to guard** rather than a better attack: it uses the same range and cooldown as the normal attack, and it does **nothing at all** against a target that is not defending (a conditional read — valuable against blockers, dead weight against pressure). Being a resolution conditional rather than a chosen action keeps the two-channel model intact — no `w_grab`, no fourth stance, so the policy space, the weight scale degeneracy and the weight drift are all untouched. Measured in `test_combat` against an always-guarding target: per-hit damage 16.2 at `grab_power = 0` (0.60×) versus 43.2 at `1.0` (1.60×), exactly a clean hit at the neutral 0.40, and **exactly zero** difference against a target that is not defending. `CombatTrace` exposes `guard_broken` (damage torn through the guard), which is the Grappler's Layer 3 signature.

One gene closed four gaps that had been treated as separate problems: the Recurso axis had no counter (DEFEND was free); Layer 3 had 4 assertions for 5 archetypes because the Grappler had no distinct behaviour; the cycle edge "Grappler beats Turtle" — justified in the table below as literally *"grab é o counter canônico ao bloqueio"* — had no mechanism; and the Grappler had a single defining gene. The validator now scores **23/23** on the canonical, with all five archetypes carrying a behavioural signature for the first time. Honest caveat on the cycle edge: the Grappler beats the Turtle 100% canonically, but it already did before the grab — the canonical Turtle loses to everyone (0% global WR). The mechanism now exists for the GA to realize that edge *on merit*; whether it does is a question for the battery.

**Draw as a third outcome**: `_decide_winner` returns `-1` when both fighters end on the same HP fraction (double KO, or a timeout with no difference); the round-robin scores it as half a win for each side and the per-fight score is `0.5`. Without it the tie always fell to side A — which in `_run_round_robin` is always the lower-index archetype, a systematic bias on the very metric the fitness optimises (measured in a mirror: canonical Rushdown gave 54.90% to side A, with 10.3% double KOs).

## Quick Matchup Check

```bash
py -m src.tools.report --evolved              # dossiê completo do indivíduo (porta de entrada)
py -m src.tools.analyze_matchups --evolved    # só os matchups
py -m src.tools.drift_table --evolved         # só o drift por gene + diferenciação
py -m src.tools.fingerprint --evolved         # só o comportamento
py -m src.tools.baselines --evolved           # só os modelos nulos (piso/teto/posição)
py -m src.tools.analyze_matchups rushdown zoner --n 100   # par específico
```

## Hyperparameters

Todos em `src/engine/config.py`. **Tabela completa e comentada em
[`docs/reference/07-configuration.md`](docs/reference/07-configuration.md)** — manter lá, não duplicar
aqui. Os mais ajustados ao refinar: `LAMBDA_DRIFT` / `LAMBDA_DOMINANCE` (trade-off
do escalar — hoje 1.0 / 1.0), `DOMINANCE_GLOBAL_WEIGHT` / `DOMINANCE_CAP_WEIGHT` /
`DOMINANCE_DECIS_WEIGHT` (pesos dos 3 termos do dominance C2 — hoje 1.0 / 0.5 / 0.5),
`MATCHUP_WR_CAP` (banda de hard-counter — 0.15, **fechado**: ponto médio entre 6-4 e
7-3 na grade da FGC, ver o comentário no `config.py`),
`MATCHUP_THRESHOLD` / `MATCHUP_FLOOR` (banda de decisividade — hoje 0.20 / 0.02,
o piso como guarda de degenerescência), `DRIFT_DEFINING_WEIGHT` (peso dos genes
definidores no drift — hoje 3.0; 1.0 volta ao drift uniforme),
`ACTION_PERSISTENCE_SUBTICKS` (comprometimento da intenção — 5, **fechado**: 1 tick
= cooldown mínimo, e SNR melhor em 8/8 genes), `SIMS_PER_MATCHUP`,
`MAX_GENERATIONS` / `STAGNATION_LIMIT`.
