# GA Character Balancer

> **Work in progress** — this project is still under active development.

An undergraduate thesis (TCC) exploring whether a Genetic Algorithm can achieve competitive balance between 5 distinct fighting game archetypes without destroying their functional identities.

## Overview

The system evolves a set of 5 characters (one per archetype) through a GA, evaluating fitness via full round-robin combat simulations. The core research question: can automated optimization produce balanced matchups while preserving each archetype's unique playstyle?

**Archetypes:** Rushdown, Zoner, Grappler, Turtle, Combo Master

## How it works

- **Simulation layer** — tick-based 1v1 combat with intention→execution action selection (Attack / Advance / Retreat / Defend), the intention sampled from the character's behavioral weights
- **GA layer** — each individual encodes 5 characters (50 genes total); fitness balances archetype drift against dominance (no single archetype dominates the roster, plus a hard-counter cap). NSGA-II variant optimizes the same two as Pareto objectives.

## Setup

Use the helper script to create the venv and install pinned dependencies:

```powershell
.\setup.ps1                 # cria .venv e instala requirements.txt
.\setup.ps1 -Recreate       # apaga .venv existente e refaz do zero
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

### Analysis tools

```powershell
py -m src.tools.analyze_matchups                # all matchups, canonical, 30 sims
py -m src.tools.analyze_matchups --evolved --n 50 # evolved individual, 50 sims
py -m src.tools.archetype_validator             # structural identity checks
py -m src.tools.sensitivity_analysis            # +/-sigma delta-WR per gene
py -m src.tools.web_viewer                      # browser viewer em localhost:8080
```

## Tests

Smoke tests rodam como módulo a partir da raiz:

```powershell
py -m src.tests.test_base
py -m src.tests.test_combat
py -m src.tests.test_fitness
py -m src.tests.test_operators
py -m src.tests.test_nsga2
py -m src.tests.test_archetype_validator
```
