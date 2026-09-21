# GA Character Balancer

> **Work in progress** — this project is still under active development.

An undergraduate thesis (TCC) exploring whether a Genetic Algorithm can achieve competitive balance between 5 distinct fighting game archetypes without destroying their functional identities.

## Overview

The system evolves a set of 5 characters (one per archetype) through a GA, evaluating fitness via full round-robin combat simulations. The core research question: can automated optimization produce balanced matchups while preserving each archetype's unique playstyle?

**Archetypes:** Rushdown, Zoner, Grappler, Turtle, Combo Master

## How it works

- **Simulation layer** — tick-based 1v1 combat on **two action channels**: the sampled intention governs only the *stance* (Advance / Retreat / Defend), while the *attack* is a resolution rule that fires whenever cooldown is ready and the opponent is in range and the stance is not Defend. Advancing and retreating both hit; only guarding gives up the blow. The intention is sampled from the character's behavioral weights and held for a few sub-ticks (commitment).
- **GA layer** — each individual encodes 5 characters (8 attributes + 3 behavioral weights each = **55 genes**); fitness balances archetype drift against dominance (no single archetype dominates the roster, plus a hard-counter cap and a decisiveness band). NSGA-II variant optimizes the same two as unweighted Pareto objectives.

## Setup

Use the helper script to create the venv and install pinned dependencies:

```powershell
.\scripts\setup.ps1                 # cria .venv e instala requirements.txt
.\scripts\setup.ps1 -Recreate       # apaga .venv existente e refaz do zero
```

Ative o ambiente antes de rodar qualquer comando (necessário em cada nova sessão do terminal):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Alternativamente, invoque o Python do venv diretamente sem ativar:

```powershell
.\.venv\Scripts\python.exe main.py
```

> Requer Python 3. No Windows use `py` (não `python`/`python3`). `numba` JIT-compila o loop de combate na primeira chamada (~2.5s) — sem ele o sistema não roda.

## Running

Com o venv ativo, rode tudo a partir da raiz do projeto:

```powershell
py main.py                                      # GA escalar
py main.py --algorithm nsga2 --seed 42 --quiet  # NSGA-II
```

### Ferramentas

Três pacotes, divididos pelo que fazem com um roster:

```powershell
# src.analysis — inspeciona um roster e imprime (nao grava nada)
py -m src.analysis.report --evolved                   # dossie completo do individuo (porta de entrada)
py -m src.analysis.analyze_matchups                   # all matchups, canonical
py -m src.analysis.analyze_matchups --evolved --n 50  # evolved individual, 50 sims
py -m src.analysis.archetype_validator                # structural + behavioral identity checks

# src.experiments — o protocolo da tese (cada um grava um artefato em results/)
py -m src.experiments.multi_run --algorithm both      # N execucoes independentes + estatistica agregada
py -m src.experiments.multi_run --algorithm ga --lambda-drift 0   # controle: equilibrar sem o termo de identidade
py -m src.experiments.compare_algorithms              # GA x NSGA-II (scalar_optimum) + relacao de Pareto
py -m src.experiments.compare_algorithms --control results/controls/multi_run_ga_drift0_dom1.json   # GA x controle
py -m src.experiments.external_validation --nsga2 knee_point  # replicacao + robustez a regras perturbadas
py -m src.experiments.sensitivity_analysis --evolved  # delta-WR por gene, janela 2sigma (no canonico satura)
py -m src.experiments.baselines --evolved             # modelos nulos: piso/teto de cada metrica

# src.visualization
py -m src.visualization.web_viewer                    # browser viewer em localhost:8080
py -m src.visualization.ga_plots                      # curvas de convergencia do AG (do artefato)
py -m src.visualization.nsga2_plots                   # fronteira de Pareto (do artefato)
```

### Experimentos completos

Em `scripts/`. Os dois primeiros são retomáveis (`-From N` retoma de um passo; `-WhatIf`
só lista e estima o custo); o `run_overnight.ps1` não tem `-WhatIf` — chamado, ele roda:

```powershell
.\scripts\run_sweeps.ps1     # 16 bracos exploratorios em orcamento reduzido (~1h40)
.\scripts\run_battery.ps1    # a bateria citavel, n = 20 sementes, com os dois controles (~6h12)
.\scripts\run_overnight.ps1  # encadeia os dois e roda desassistido
```

> **Nesta ordem.** Implementar um braço de sweep mexe no motor, e mexer no motor depois da
> bateria faria horas de artefato nascerem carimbados como obsoletos. A bateria é sempre a
> última coisa a rodar.

`run_overnight.ps1` é para deixar rodando sozinho. Ele roda os sweeps, ou espera terminarem
se já estiverem rodando (os dois ao mesmo tempo dobram o tempo de ambos e arriscam estourar
o limite de commit do Windows), e emenda a bateria com **uma** retomada automática se um
passo falhar. Enquanto roda, declara ao Windows que há trabalho em andamento via
`SetThreadExecutionState`, que impede suspensão/hibernação e **solta sozinho no fim**, em
vez de mexer no plano de energia global que ninguém lembra de desfazer. Tudo com carimbo de
hora em `results/logs/overnight.log`.

## Onde fica o quê

```
main.py        uma execução do AG ou do NSGA-II
scripts/       setup do ambiente, sweeps, bateria, a noite desassistida
src/engine/    o modelo: combate, fitness, os dois algoritmos
src/experiments/  analysis/  visualization/  tests/
docs/          reference/ (como funciona) · thesis/ (o porquê) · status/ (estado atual)
results/       artefatos, uma pasta por produtor
overleaf/      monografia e artigos
```

## Documentação

- [`docs/reference/`](docs/reference/README.md) — como o sistema funciona, um arquivo por tema.
- [`docs/thesis/`](docs/thesis/README.md) — material de redação: o porquê de cada decisão, o que apresentar.
- [`docs/status/HANDOFF.md`](docs/status/HANDOFF.md) — o estado atual e os resultados da última bateria.
- [`docs/status/REVIEW.md`](docs/status/REVIEW.md) — a auditoria de coerência do sistema e o que dela segue aberto.
- [`CLAUDE.md`](CLAUDE.md) — guia de trabalho no repositório e resumo das decisões de design.

## Tests

Smoke tests rodam como módulo a partir da raiz:

```powershell
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
py -m src.tests.test_multi_run
```
