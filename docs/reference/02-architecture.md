# 02 — Arquitetura

## Layout do código

```
.
├── main.py                    # entry point (GA / NSGA-II)
├── src/                       # pacote raiz (importável como `src`)
│   ├── engine/                # o motor (importável como `src.engine`)
│   │   ├── paths.py           # PROJECT_ROOT + paths derivados — single source
│   │   ├── provenance.py      # carimbo de config/motor nos artefatos + aviso de obsoleto
│   │   ├── config.py          # todos os hiperparâmetros
│   │   ├── archetypes.py      # definições canônicas (frozen) + ciclo de vantagens
│   │   ├── character.py       # representação de genes (8 atributos + 3 pesos)
│   │   ├── individual.py      # 5 personagens por indivíduo
│   │   ├── combat.py          # simulação tick a tick (JIT)
│   │   ├── fitness.py         # avaliação round-robin
│   │   ├── operators.py       # seleção / crossover / mutação
│   │   ├── ga.py              # loop do AG escalar
│   │   ├── nsga2.py           # loop do NSGA-II
│   │   └── pareto_metrics.py  # hipervolume + spacing da fronteira
│   ├── tools/                 # ferramentas que consomem o motor
│   └── tests/                 # smoke tests
└── results/                   # saídas (results.json, nsga2_results.json, plots)
```

## Convenções

**Imports.** Dentro de `src/engine/` use relativos (`from .combat import ...`).
Fora dele (`main.py`, `src/tools/`, `src/tests/`) use absolutos a partir do
motor (`from src.engine.combat import ...`). Tools e tests referenciam umas às
outras também por caminho absoluto (`from src.tools.archetype_validator import ...`).

**Paths.** Nunca hardcode strings de caminho. Importe os constants de
`src.engine.paths` (`PROJECT_ROOT`, `RESULTS_DIR`, `GA_RESULTS_PATH`,
`NSGA2_RESULTS_PATH`, `NSGA2_PLOTS_DIR`). São derivados de
`Path(__file__).resolve().parent.parent.parent` — funcionam independente do cwd.

**Execução.** Tudo roda da raiz do projeto. Scripts em `src/tools/` e
`src/tests/` rodam como módulo (`py -m src.tools.<nome>`) para que `src` esteja
no path. Ver [08-tools.md](08-tools.md) e [09-reproducibility.md](09-reproducibility.md).

## Modelo de dados

Três níveis, do imutável ao mutável (`archetypes.py` → `character.py` →
`individual.py`):

```
ArchetypeDefinition (frozen)        Character (mutável)            Individual
  id, name, description               archetype: ArchetypeDefinition  characters: List[Character] (5)
  initial_attributes (8, frozen)      attributes: List[float] (8)     fitness, objectives, rank, crowding
  initial_weights    (3, frozen)      weights:    List[float] (3)
  defining_genes: Tuple[str, ...]
  beats: Tuple[ArchetypeID, ...]
```

- **`ArchetypeDefinition`** — valores canônicos congelados; baseline de drift e
  semente. `defining_genes` são os genes em que o arquétipo ocupa um extremo por
  design, e pesam mais no drift. Ver [03-archetypes.md](03-archetypes.md).
- **`Character`** — 11 genes mutáveis (8 atributos + 3 pesos), todos contínuos.
  `clip()` aplica os bounds.
- **`Individual`** — lista de 5 `Character` + caches de avaliação. Construtores:
  `from_canonical()` (semente), `random()`, `from_results()` (melhor do AG),
  `from_nsga2(representative=...)` (representante do Pareto).

**Total: 55 genes por indivíduo** (5 personagens × 11 genes).

## Orquestração das duas camadas

O AG (`ga.py` / `nsga2.py`) chama `fitness.py`, que roda o round-robin chamando
`combat.simulate_combat` para cada luta — semeada por `fitness.fight_seed` quando há
seed-base (ver [09-reproducibility.md](09-reproducibility.md)). Toda a lógica de combate
vive **exclusivamente** em duas funções `@njit`:

- `_simulate_combat_jit` — fast path sem rastreio, usado pelo fitness;
- `_simulate_combat_traced_jit` — grava estado tick a tick em arrays NumPy,
  consumido pelas tools de instrumentação (viewer, analyze_matchups, fingerprint,
  Layer 3 do validador).

As duas chamam os mesmos helpers `@njit` — `_decide_action` (postura),
`_apply_movement` (movimento e colisão) e `_decide_winner` (desfecho) —, então não há
cópias divergentes da lógica; um teste de paridade em `test_combat` garante isso. Não há
reimplementação Python do loop: tools que precisam visualizar a luta consomem
`CombatTrace` em vez de redobrar a lógica.

## Paralelismo

`fitness.evaluate_population` e `nsga2._evaluate_population` distribuem as
avaliações por `fitness.parallel_map`, sobre um `ProcessPoolExecutor` **persistente**:
sobe na primeira avaliação paralela e serve todas as gerações (e todas as sementes de um
`multi_run`), com `N_WORKERS = min(8, núcleos)` processos. O estado de processo do pai
(`RuntimeState`) viaja com cada tarefa, e não no `initializer`, porque muda depois que os
workers nascem — o seed-base a cada geração, os pesos a cada braço de sweep. Implicações de
reprodutibilidade em [09-reproducibility.md](09-reproducibility.md).
