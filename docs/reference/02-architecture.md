# 02 — Arquitetura

## Layout do projeto

```
.
├── main.py                    # entry point: uma execução do AG escalar ou do NSGA-II
├── requirements.txt
├── scripts/                   # PowerShell: setup + sweeps + bateria + a noite desassistida
├── src/                       # pacote raiz (importável como `src`)
│   ├── engine/                # o modelo (importável como `src.engine`)
│   │   ├── paths.py           # PROJECT_ROOT + paths derivados — single source
│   │   ├── provenance.py      # carimbo de config/motor/medição nos artefatos + aviso e recusa de obsoleto
│   │   ├── config.py          # todos os hiperparâmetros
│   │   ├── archetypes.py      # definições canônicas (frozen) + ciclo de vantagens
│   │   ├── character.py       # representação de genes (8 atributos + 3 pesos)
│   │   ├── individual.py      # 5 personagens por indivíduo
│   │   ├── combat.py          # simulação tick a tick (JIT)
│   │   ├── fitness.py         # avaliação round-robin, CRN, pool de processos
│   │   ├── operators.py       # seleção / crossover / mutação
│   │   ├── ga.py              # loop do AG escalar
│   │   ├── nsga2.py           # loop do NSGA-II
│   │   └── pareto_metrics.py  # hipervolume + spacing da fronteira
│   ├── experiments/           # o protocolo: cada um grava um artefato em results/
│   ├── analysis/              # inspeciona um roster e imprime — não grava nada
│   ├── visualization/         # viewers e plots
│   └── tests/                 # smoke tests
├── docs/                      # reference/ (como funciona), thesis/ (o porquê), status/ (registros)
├── results/                   # artefatos, uma pasta por produtor
└── overleaf/                  # os textos redigidos
```

Os três pacotes fora do `engine/` se dividem pelo que fazem com um roster, e o critério
é verificável no código: só `experiments/` abre arquivo para escrita em `results/`;
`analysis/` só imprime; `visualization/` desenha (o `nsga2_plots` e o `ga_plots` gravam
os PNG que o `main.py` pede). É uma divisão por **saída**, não uma hierarquia — o dossiê do `analysis`
mostra os modelos nulos do `experiments/baselines`, e este pontua rosters com o validador
do `analysis`. Conteúdo de cada um: [08-tools.md](08-tools.md).

`results/` segue a mesma lógica — uma pasta por produtor:

| pasta | quem grava |
|---|---|
| `single_run/` | `main.py` — `ga.json`, `nsga2.json` e `plots/<timestamp>/` |
| `multi_run/` | `multi_run` (as 20 sementes da bateria) e `compare_algorithms` (AG × NSGA-II) |
| `controls/` | `multi_run` com a amostra e o orçamento da bateria e um fator de desenho trocado (λ_drift = 0, sem semente canônica), e o `compare_algorithms --control` de cada um |
| `exploratory/` | `multi_run` com amostra ou orçamento reduzidos — os braços de sweep |
| `external_validation/` | `external_validation`, um arquivo por roster |
| `sensitivity/` | `sensitivity_analysis` |
| `baselines/` | `baselines` |
| `logs/` | `run_overnight.ps1` — fora do git |

## Convenções

**Imports.** Dentro de `src/engine/` use relativos (`from .combat import ...`).
Fora dele (`main.py`, `src/experiments/`, `src/analysis/`, `src/visualization/`,
`src/tests/`) use absolutos a partir do pacote (`from src.engine.combat import ...`,
`from src.analysis.archetype_validator import ...`).

**Paths.** Nunca hardcode strings de caminho. Importe os constants de
`src.engine.paths` (`PROJECT_ROOT`, `RESULTS_DIR`, `GA_RESULTS_PATH`,
`NSGA2_RESULTS_PATH`, `NSGA2_PLOTS_DIR`, …). São derivados de
`Path(__file__).resolve().parent.parent.parent` — funcionam independente do cwd.

**Execução.** Tudo roda da raiz do projeto, como módulo
(`py -m src.experiments.<nome>`, `py -m src.analysis.<nome>`, …), para que `src` esteja
no path. Os scripts de `scripts/` fazem isso sozinhos: mudam para a raiz antes de rodar.
Ver [08-tools.md](08-tools.md) e [09-reproducibility.md](09-reproducibility.md).

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
