# Remove balance_error from Fitness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remover `balance_error` completamente do sistema; reformular fitness como soma pura de penalidades; aplicar renomeações para consistência semântica; reduzir NSGA-II de 3 para 2 objetivos.

**Architecture:** A nova fórmula é `fitness = -(LAMBDA_SPECIALIZATION * specialization_penalty + LAMBDA_DRIFT * drift_penalty + LAMBDA_DOMINANCE * dominance_penalty)`. `balance_error` desaparece de todo o código — não é calculado, não é logado, não existe em nenhum dataclass. O NSGA-II passa a 2 objetivos: `(dominance_penalty, specialization_penalty)`.

**Tech Stack:** Python stdlib. Sem novas dependências.

---

## Mapa de renomeações

| Nome antigo | Nome novo | Arquivos afetados |
|---|---|---|
| `LAMBDA` | `LAMBDA_SPECIALIZATION` | `config.py`, `fitness.py` |
| `LAMBDA_MATCHUP` | `LAMBDA_DOMINANCE` | `config.py`, `fitness.py`, `test_map_elites.py` |
| `attribute_cost` | `specialization_penalty` | `fitness.py`, `ga.py`, `main.py`, `test_fitness.py`, `test_map_elites.py` |
| `matchup_dominance_penalty` | `dominance_penalty` | `fitness.py`, `ga.py`, `main.py`, `nsga2.py`, `nsga2_plots.py`, `test_nsga2.py`, `test_map_elites.py` |
| `_matchup_dominance()` | `_dominance_penalty()` | `fitness.py` |

## Mapa de remoções

| O que remover | De onde |
|---|---|
| `balance_error` (campo + cálculo) | `fitness.py` — `FitnessDetail`, `evaluate_detail_n`, `evaluate_objectives` |
| `BALANCE_MODE` | `config.py`, `fitness.py` (import + assert) |
| `CONVERGENCE_THRESHOLD` | `config.py`, `ga.py` (import + uso) |
| `GenerationStats.balance_error` | `ga.py` |
| `bal=...` no log por geração | `ga.py` |
| `Balance error` no log de resultado | `ga.py` |
| `balance_error` no resultado | `main.py` |
| Funções de knee 3D | `nsga2.py`: `_find_knee`, `_cross3`, `_distance_to_plane`, `_dist_to_line` |
| 3 projeções 2D + 3D opcional | `nsga2_plots.py` → substituir por 1 scatter 2D |
| `best_balance`, `best_drift` nos reps | `nsga2.py`, `nsga2_plots.py`, testes |
| Unpacking de 3 objetivos | `main.py` linha com `bal, mat, drf = ind.objectives` |

---

## Task 1 — `config.py`: renomear lambdas, remover parâmetros mortos

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Aplicar todas as mudanças no bloco de fitness**

Substituir o bloco completo da seção `# ── Função de fitness`:

```python
# ── Função de fitness ────────────────────────────────────────────────────────

SIMS_PER_MATCHUP       = 30    # simulações por matchup no round-robin
SIMS_CONVERGENCE_CHECK = 50    # simulações extras para confirmar convergência

LAMBDA_SPECIALIZATION  = 0.2   # peso da penalidade de homogeneização (specialization_penalty)
LAMBDA_DRIFT           = 0.0   # peso da penalidade de desvio arquetípico (drift_penalty)
                                # 0.0 = evolução livre  |  alto = âncora ao canônico
                                # trade-off central do TCC: equilíbrio vs preservação
LAMBDA_DOMINANCE       = 1.0   # peso da penalidade de dominância em matchups (dominance_penalty)

MATCHUP_THRESHOLD      = 0.10  # excesso acima de 50% que inicia penalização (60% WR = limiar)
```

E substituir a linha de `NSGA2_OBJECTIVES`:
```python
NSGA2_OBJECTIVES    = ["dominance_penalty", "specialization_penalty"]
```

- [ ] **Step 2: Remover `CONVERGENCE_THRESHOLD` e `BALANCE_MODE`**

Deletar a linha:
```python
CONVERGENCE_THRESHOLD = 0.02   # desvio máximo de balance_error para convergência (≈48–52%)
```

Deletar o bloco:
```python
BALANCE_MODE = "aggregate"     # como calcular balance_error:
                                # "matchup"   → mean(|wr_ij - 0.5|) sobre os 10 pares
                                # "aggregate" → mean(|wr_i  - 0.5|) sobre os 5 personagens
```

- [ ] **Step 3: Verificar**

```bash
py -c "import config; print(config.LAMBDA_SPECIALIZATION, config.LAMBDA_DOMINANCE, config.NSGA2_OBJECTIVES)"
```
Saída esperada: `0.2 1.0 ['dominance_penalty', 'specialization_penalty']`

---

## Task 2 — `fitness.py`: nova fórmula, renomeações, remoção de `balance_error`

**Files:**
- Modify: `fitness.py`

- [ ] **Step 1: Substituir o docstring do módulo**

```python
"""
Função de fitness para o AG.

Avaliação via round-robin completo:
  C(5,2) = 10 matchups × SIMS_PER_MATCHUP simulações por indivíduo.

Fórmula:
  fitness = -(LAMBDA_SPECIALIZATION * specialization_penalty
            + LAMBDA_DRIFT          * drift_penalty
            + LAMBDA_DOMINANCE      * dominance_penalty)

Componentes (todos em [0, 1], todos minimizados):
  specialization_penalty = 1 - mean(specialization_i)
  drift_penalty          = mean(archetype_deviation_i)
  dominance_penalty      = mean(excess_ij) sobre os 10 pares
"""
```

- [ ] **Step 2: Atualizar os imports de config**

```python
from config import (
    ATTRIBUTE_BOUNDS,
    LAMBDA_DOMINANCE,
    LAMBDA_DRIFT,
    LAMBDA_SPECIALIZATION,
    MATCHUP_THRESHOLD,
    N_WORKERS,
    SIMS_PER_MATCHUP,
)
```

- [ ] **Step 3: Renomear `_matchup_dominance` → `_dominance_penalty`**

Substituir a função:
```python
def _dominance_penalty(matchup_winrates: Dict[Tuple[int, int], float]) -> float:
    """
    Penalidade média dos excessos de dominância em todos os 10 pares, normalizada em [0, 1].

    Usa mean (não max): todos os matchups desbalanceados contribuem — o GA recebe
    sinal de melhora ao corrigir qualquer par ruim, não apenas o pior.
    Pares dentro de MATCHUP_THRESHOLD não penalizam (excess clampado em 0).
    """
    scale = 0.5 - MATCHUP_THRESHOLD
    return mean(
        max(0.0, (abs(wr - 0.5) - MATCHUP_THRESHOLD) / scale)
        for wr in matchup_winrates.values()
    )
```

- [ ] **Step 4: Substituir `FitnessDetail`**

```python
@dataclass
class FitnessDetail:
    """Resultado completo da avaliação de um indivíduo."""

    fitness:               float
    winrates:              List[float]                    # WR agregado por personagem (ordem ARCHETYPE_ORDER)
    specialization_penalty: float                         # 1 - mean(specialization_i)
    drift_penalty:          float = 0.0                  # mean(archetype_deviation_i)
    archetype_deviations:   List[float] = field(default_factory=list)
    matchup_winrates:       Dict[Tuple[int, int], float] = field(default_factory=dict)
    dominance_penalty:      float = 0.0                  # mean(excess_ij) normalizado em [0, 1]
```

- [ ] **Step 5: Substituir o corpo de `evaluate_detail_n`**

Substituir todo o bloco de cálculo e construção do `FitnessDetail`:

```python
    winrates         = [wins[i] / total_games[i] for i in range(n)]
    matchup_winrates = {key: v / sims for key, v in matchup_wins.items()}

    specialization_penalty = 1.0 - sum(_specialization(c) for c in chars) / n
    archetype_deviations   = [_archetype_deviation(c) for c in chars]
    drift_penalty          = sum(archetype_deviations) / n
    dominance_pen          = _dominance_penalty(matchup_winrates)

    fitness = -(
        LAMBDA_SPECIALIZATION * specialization_penalty
        + LAMBDA_DRIFT        * drift_penalty
        + LAMBDA_DOMINANCE    * dominance_pen
    )

    return FitnessDetail(
        fitness=fitness,
        winrates=winrates,
        specialization_penalty=specialization_penalty,
        drift_penalty=drift_penalty,
        archetype_deviations=archetype_deviations,
        matchup_winrates=matchup_winrates,
        dominance_penalty=dominance_pen,
    )
```

- [ ] **Step 6: Substituir `evaluate_objectives`**

```python
def evaluate_objectives(individual: Individual) -> Tuple[float, float]:
    """
    Avalia o indivíduo e retorna (dominance_penalty, specialization_penalty).

    Minimizados pelo NSGA-II. Cacheia em `individual.objectives`; não reavalia se já cacheado.
    Escalas: dominance_penalty ∈ [0, 1]; specialization_penalty ∈ [0, 1].
    """
    if individual.objectives is not None:
        return individual.objectives
    detail = evaluate_detail(individual)
    objs = (detail.dominance_penalty, detail.specialization_penalty)
    individual.objectives = objs
    return objs
```

- [ ] **Step 7: Verificar**

```bash
py -c "from fitness import evaluate_detail; from individual import Individual; d = evaluate_detail(Individual.from_canonical()); print(f'fit={d.fitness:.4f}  spec={d.specialization_penalty:.4f}  dom={d.dominance_penalty:.4f}')"
```

Saída esperada: `fit=` valor ≤ 0.0, demais valores em [0, 1].

---

## Task 3 — `ga.py`: renomear campos, remover `balance_error`, novo critério de convergência

**Files:**
- Modify: `ga.py`

- [ ] **Step 1: Atualizar imports — remover `CONVERGENCE_THRESHOLD`**

Substituir o bloco de imports de config:
```python
from config import (
    ELITE_SIZE,
    MATCHUP_CONVERGENCE_THRESHOLD,
    MAX_GENERATIONS,
    POPULATION_SIZE,
    SIMS_CONVERGENCE_CHECK,
    STAGNATION_LIMIT,
)
```

- [ ] **Step 2: Substituir `GenerationStats`**

```python
@dataclass
class GenerationStats:
    generation:            int
    best_fitness:          float
    mean_fitness:          float
    worst_fitness:         float
    specialization_penalty: float
    drift_penalty:         float
    dominance_penalty:     float
    winrates:              List[float]
    archetype_deviations:  List[float]
    elapsed_s:             float
```

- [ ] **Step 3: Atualizar `_log` (log por geração)**

```python
def _log(stats: GenerationStats, verbose: bool) -> None:
    if not verbose:
        return
    print(
        f"Gen {stats.generation:4d} | "
        f"fit={stats.best_fitness:+.4f}  "
        f"mean={stats.mean_fitness:+.4f}  "
        f"dom={stats.dominance_penalty:.4f}  "
        f"spec={stats.specialization_penalty:.4f}  "
        f"drift={stats.drift_penalty:.3f}  "
        f"({stats.elapsed_s:.1f}s)"
    )
```

- [ ] **Step 4: Atualizar `_log_result`**

Substituir as linhas de impressão dos componentes do fitness:
```python
    print(f"  {'Fitness':22s} {result.best.fitness:+.4f}")
    print(f"  {'Dominance penalty':22s} {d.dominance_penalty:.4f}")
    print(f"  {'Specialization penalty':22s} {d.specialization_penalty:.4f}")
    print(f"  {'Drift penalty':22s} {d.drift_penalty:.4f}")
```

- [ ] **Step 5: Atualizar a construção de `GenerationStats` no loop**

```python
        stats = GenerationStats(
            generation=gen,
            best_fitness=best_detail.fitness,
            mean_fitness=sum(fitnesses) / len(fitnesses),
            worst_fitness=min(fitnesses),
            specialization_penalty=best_detail.specialization_penalty,
            drift_penalty=best_detail.drift_penalty,
            dominance_penalty=best_detail.dominance_penalty,
            winrates=best_detail.winrates,
            archetype_deviations=best_detail.archetype_deviations,
            elapsed_s=time.time() - t_start,
        )
```

- [ ] **Step 6: Substituir o critério de convergência**

```python
        if best_detail.dominance_penalty <= 1e-9:
            confirmed   = evaluate_detail_n(best_ind, SIMS_CONVERGENCE_CHECK)
            matchups_ok = all(
                abs(wr - 0.5) <= MATCHUP_CONVERGENCE_THRESHOLD
                for wr in confirmed.matchup_winrates.values()
            )
            if matchups_ok:
                best_ind.fitness = confirmed.fitness
                _log_result(GAResult(best_ind, confirmed, gen, True, False, history), verbose)
                return GAResult(
                    best=best_ind,
                    best_detail=confirmed,
                    generation=gen,
                    converged=True,
                    stagnated=False,
                    history=history,
                )
```

**Nota**: `dominance_penalty <= 1e-9` equivale a `== 0` de forma segura — a função retorna exatamente 0.0 quando todos os matchups estão dentro de `MATCHUP_THRESHOLD`.

- [ ] **Step 7: Atualizar o docstring do módulo**

Substituir a linha:
```
       b. Verifica convergência  → para se balance_error ≤ CONVERGENCE_THRESHOLD.
```
Por:
```
       b. Verifica convergência  → para se dominance_penalty == 0 (todos matchups ≤ 60% WR).
```

- [ ] **Step 8: Verificar**

```bash
py -c "import ga; print('OK')"
```

---

## Task 4 — `nsga2.py`: 2 objetivos; remover funções 3D; simplificar representantes

**Files:**
- Modify: `nsga2.py`

- [ ] **Step 1: Substituir o docstring do módulo**

```python
"""
NSGA-II — Algoritmo genético multi-objetivo (Deb et al., 2002).

Otimiza 2 objetivos simultaneamente:
  f1 = dominance_penalty      (dominância em matchups diretos)
  f2 = specialization_penalty (homogeneização de atributos)

Todos minimizados, todos em [0, 1].
"""
```

- [ ] **Step 2: Remover as funções auxiliares de knee/plano 3D**

Deletar completamente:
- `_distance_to_plane`
- `_cross3`
- `_dist_to_line`
- `_find_knee`

- [ ] **Step 3: Substituir `select_representatives`**

```python
def select_representatives(front: List[Individual]) -> dict:
    """
    Retorna 4 representantes da fronteira de Pareto 2D:
      - best_dominance    — menor dominance_penalty (objetivo 0)
      - best_cost         — menor specialization_penalty (objetivo 1)
      - knee_point        — mais distante da reta entre os dois extremos
      - ideal_point       — mais próximo da utopia (0, 0)

    Ordem dos objetivos: (dominance_penalty, specialization_penalty).
    """
    best_dominance = _best_in(front, 0)
    best_cost      = _best_in(front, 1)
    ideal          = min(front, key=lambda ind: _euclidean_norm(ind.objectives))

    p1        = best_dominance.objectives
    p2        = best_cost.objectives
    line      = (p2[0] - p1[0], p2[1] - p1[1])
    line_norm = math.sqrt(line[0] ** 2 + line[1] ** 2)

    if line_norm == 0.0 or len(front) <= 2:
        knee = front[0]
    else:
        def _dist(ind):
            d     = (ind.objectives[0] - p1[0], ind.objectives[1] - p1[1])
            proj  = (d[0] * line[0] + d[1] * line[1]) / line_norm
            perp2 = d[0] ** 2 + d[1] ** 2 - proj ** 2
            return math.sqrt(max(0.0, perp2))
        knee = max(front, key=_dist)

    return {
        "best_dominance": best_dominance,
        "best_cost":      best_cost,
        "knee_point":     knee,
        "ideal_point":    ideal,
    }
```

- [ ] **Step 4: Atualizar `_log_generation`**

```python
def _log_generation(stats: GenerationStats, verbose: bool) -> None:
    if not verbose:
        return
    dom, cost = stats.best_per_objective
    print(
        f"Gen {stats.generation:4d} | "
        f"front0={stats.front_sizes[0]:3d}  "
        f"dom={dom:.4f}  cost={cost:.4f}  "
        f"({stats.elapsed_s:.1f}s)"
    )
```

- [ ] **Step 5: Atualizar `range(3)` → `range(2)` no loop principal**

```python
        best_per_obj = [min(ind.objectives[m] for ind in population) for m in range(2)]
```

- [ ] **Step 6: Verificar**

```bash
py -c "import nsga2; print('OK')"
```

---

## Task 5 — `nsga2_plots.py`: substituir por 1 scatter 2D limpo

**Files:**
- Modify: `nsga2_plots.py`

- [ ] **Step 1: Reescrever o arquivo**

```python
"""
Visualização da fronteira de Pareto do NSGA-II (2 objetivos).

Gera 1 scatter 2D: dominance_penalty × specialization_penalty.
Os 4 representantes são destacados.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nsga2 import NSGAResult

_AXIS_LABEL = {0: "dominance_penalty", 1: "specialization_penalty"}

_REP_STYLE = {
    "best_dominance": {"marker": "o", "color": "tab:red",    "label": "Melhor dominância"},
    "best_cost":      {"marker": "o", "color": "tab:blue",   "label": "Melhor custo"},
    "knee_point":     {"marker": "^", "color": "black",      "label": "Knee point"},
    "ideal_point":    {"marker": "*", "color": "tab:orange", "label": "Ideal point"},
}


def save_plots(result: NSGAResult, outdir: str, plot_3d: bool = False) -> None:
    """Gera o scatter 2D da fronteira de Pareto em `outdir`. `plot_3d` é ignorado."""
    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6))

    xs = [ind.objectives[0] for ind in result.pareto_front]
    ys = [ind.objectives[1] for ind in result.pareto_front]
    ax.scatter(xs, ys, alpha=0.4, s=30, color="tab:blue", label="Fronteira de Pareto")

    for name, ind in result.representatives.items():
        style = _REP_STYLE[name]
        ax.scatter(
            ind.objectives[0], ind.objectives[1],
            marker=style["marker"], color=style["color"],
            s=140, edgecolors="black", linewidths=1.2, label=style["label"], zorder=10,
        )

    ax.set_xlabel(_AXIS_LABEL[0])
    ax.set_ylabel(_AXIS_LABEL[1])
    ax.set_title("Fronteira de Pareto — dominância vs custo de especialização")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "pareto_front.png"), dpi=120)
    plt.close(fig)
```

- [ ] **Step 2: Verificar**

```bash
py -c "import nsga2_plots; print('OK')"
```

---

## Task 6 — `main.py`: remover `balance_error`, corrigir unpacking de objetivos NSGA-II

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Remover a linha de `balance_error` e renomear a de dominância**

Localizar:
```python
    print(f"Balance error:             {result.best_detail.balance_error:.4f}")
    print(f"Matchup dominance penalty: {result.best_detail.matchup_dominance_penalty:.4f}")
```
Substituir por:
```python
    print(f"Dominance penalty:     {result.best_detail.dominance_penalty:.4f}")
    print(f"Specialization penalty: {result.best_detail.specialization_penalty:.4f}")
```

- [ ] **Step 2: Corrigir o unpacking de objetivos no loop NSGA-II**

Localizar:
```python
        bal, mat, drf = ind.objectives
        print(f"  {name:15s}  bal={bal:.4f}  mat={mat:.4f}  drift={drf:.4f}")
```
Substituir por:
```python
        dom, cost = ind.objectives
        print(f"  {name:15s}  dom={dom:.4f}  cost={cost:.4f}")
```

- [ ] **Step 3: Verificar**

```bash
py -c "import main; print('OK')"
```

---

## Task 7 — `test_fitness.py`: atualizar nomes e assertion de range

**Files:**
- Modify: `test_fitness.py`

- [ ] **Step 1: Atualizar os prints e a assertion**

Substituir:
```python
print(f"\n  balance_error  = {detail.balance_error:.4f}")
print(f"  attribute_cost = {detail.attribute_cost:.4f}")
print(f"  fitness        = {detail.fitness:.4f}")
assert -1.0 < detail.fitness <= 1.0, f"Fitness fora do range: {detail.fitness}"
print("  ✓ Fitness dentro do range esperado")
```
Por:
```python
print(f"\n  specialization_penalty = {detail.specialization_penalty:.4f}")
print(f"  dominance_penalty      = {detail.dominance_penalty:.4f}")
print(f"  fitness                = {detail.fitness:.4f}")
# Nova fórmula: fitness = -(LAMBDA_SPECIALIZATION*spec + LAMBDA_DRIFT*drift + LAMBDA_DOMINANCE*dom)
# Máxima penalidade com lambdas padrão (0.2 + 0.0 + 1.0): fitness >= -1.2
assert -2.0 < detail.fitness <= 0.0, f"Fitness fora do range: {detail.fitness}"
print("  ✓ Fitness dentro do range esperado")
```

- [ ] **Step 2: Rodar o teste**

```bash
py test_fitness.py
```
Saída esperada: `Todos os testes de fitness passaram ✓`

---

## Task 8 — `test_nsga2.py`: atualizar para 2 objetivos e novos nomes

**Files:**
- Modify: `test_nsga2.py`

- [ ] **Step 1: Atualizar `test_individual_clone_copies_nsga2_fields`**

```python
def test_individual_clone_copies_nsga2_fields():
    ind = Individual.from_canonical()
    ind.objectives = (0.1, 0.2)
    ind.rank = 2
    ind.crowding = 1.5
    clone = ind.clone()
    assert clone.objectives == (0.1, 0.2)
    assert clone.rank == 2
    assert clone.crowding == 1.5
    clone.rank = 99
    assert ind.rank == 2
```

- [ ] **Step 2: Atualizar `test_config_constants_exist`**

```python
def test_config_constants_exist():
    from config import POPULATION_SIZE, MAX_GENERATIONS
    assert NSGA2_POP_SIZE == POPULATION_SIZE
    assert NSGA2_GENERATIONS == MAX_GENERATIONS
    assert NSGA2_OBJECTIVES == ["dominance_penalty", "specialization_penalty"]
```

- [ ] **Step 3: Renomear e atualizar `test_evaluate_objectives_returns_3tuple` → 2-tupla**

```python
def test_evaluate_objectives_returns_2tuple():
    random.seed(0)
    ind = Individual.from_canonical()
    objs = evaluate_objectives(ind)
    assert isinstance(objs, tuple), "deve retornar tupla"
    assert len(objs) == 2,          "deve ter 2 objetivos"
    for o in objs:
        assert isinstance(o, float), f"objetivo deve ser float, recebeu {type(o)}"
        assert 0.0 <= o <= 1.0,       f"objetivo fora de [0,1]: {o}"
```

- [ ] **Step 4: Atualizar todos os testes de dominância para 2 elementos**

```python
def test_dominates_strict():
    a = _ind_with_obj([0.1, 0.1])
    b = _ind_with_obj([0.2, 0.2])
    assert _dominates(a, b)
    assert not _dominates(b, a)

def test_dominates_requires_strict_in_at_least_one():
    a = _ind_with_obj([0.1, 0.1])
    b = _ind_with_obj([0.1, 0.1])
    assert not _dominates(a, b)
    assert not _dominates(b, a)

def test_dominates_fails_if_any_worse():
    a = _ind_with_obj([0.1, 0.3])
    b = _ind_with_obj([0.2, 0.2])
    assert not _dominates(a, b)
    assert not _dominates(b, a)
```

- [ ] **Step 5: Atualizar testes de sorting**

```python
def test_sort_single_pareto_layer():
    pop = [
        _ind_with_obj([0.1, 0.9]),
        _ind_with_obj([0.5, 0.5]),
        _ind_with_obj([0.9, 0.1]),
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 1
    assert all(ind.rank == 0 for ind in pop)

def test_sort_multiple_layers():
    pop = [
        _ind_with_obj([0.1, 0.9]),
        _ind_with_obj([0.9, 0.1]),
        _ind_with_obj([0.95, 0.95]),
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 2
    assert len(fronts[0]) == 2
    assert len(fronts[1]) == 1
    assert pop[2].rank == 1

def test_sort_divergent_dominated_sets():
    pop = [
        _ind_with_obj([0.1, 0.9]),
        _ind_with_obj([0.9, 0.1]),
        _ind_with_obj([0.5, 0.5]),
        _ind_with_obj([0.2, 0.95]),
        _ind_with_obj([0.95, 0.2]),
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 2
    assert len(fronts[0]) == 3
    assert len(fronts[1]) == 2
    assert pop[3].rank == 1
    assert pop[4].rank == 1
```

- [ ] **Step 6: Atualizar testes de crowding**

```python
def test_crowding_assigns_inf_to_extremes():
    front = [
        _ind_with_obj([0.1, 0.9]),
        _ind_with_obj([0.5, 0.5]),
        _ind_with_obj([0.9, 0.1]),
    ]
    crowding_distance_assignment(front)
    inf_count = sum(1 for ind in front if math.isinf(ind.crowding))
    assert inf_count >= 2, "extremos em cada objetivo recebem +inf"

def test_crowding_small_front_all_inf():
    front = [
        _ind_with_obj([0.1, 0.1]),
        _ind_with_obj([0.9, 0.9]),
    ]
    crowding_distance_assignment(front)
    assert math.isinf(front[0].crowding)
    assert math.isinf(front[1].crowding)

def test_crowding_middle_has_finite_value():
    front = [
        _ind_with_obj([0.0, 0.5]),
        _ind_with_obj([0.5, 0.5]),
        _ind_with_obj([1.0, 0.5]),
    ]
    crowding_distance_assignment(front)
    assert math.isinf(front[0].crowding)
    assert math.isinf(front[2].crowding)
    assert not math.isinf(front[1].crowding)
    assert front[1].crowding > 0
```

- [ ] **Step 7: Atualizar testes de tournament**

```python
def test_tournament_picks_lower_rank():
    a = _ind_with_obj([0.1, 0.1]); a.rank = 0; a.crowding = 1.0
    b = _ind_with_obj([0.5, 0.5]); b.rank = 2; b.crowding = 10.0
    random.seed(0)
    assert nsga2_binary_tournament([a, b]) is a

def test_tournament_breaks_tie_by_crowding():
    a = _ind_with_obj([0.1, 0.1]); a.rank = 1; a.crowding = 5.0
    b = _ind_with_obj([0.2, 0.2]); b.rank = 1; b.crowding = 1.0
    random.seed(0)
    assert nsga2_binary_tournament([a, b]) is a

def test_tournament_stochastic_on_full_tie():
    a = _ind_with_obj([0.1, 0.1]); a.rank = 1; a.crowding = 5.0
    b = _ind_with_obj([0.2, 0.2]); b.rank = 1; b.crowding = 5.0
    wins_a = sum(
        1 for s in range(200)
        if (random.seed(s) or True) and nsga2_binary_tournament([a, b]) is a
    )
    assert 60 < wins_a < 140
```

- [ ] **Step 8: Substituir todos os testes de `select_representatives`**

```python
def test_representatives_identifies_extremes():
    front = [
        _ind_with_obj([0.05, 0.90]),
        _ind_with_obj([0.90, 0.05]),
        _ind_with_obj([0.50, 0.50]),
    ]
    reps = select_representatives(front)
    assert reps["best_dominance"] is front[0]
    assert reps["best_cost"]      is front[1]

def test_representatives_ideal_closest_to_origin():
    front = [
        _ind_with_obj([0.05, 0.90]),
        _ind_with_obj([0.20, 0.20]),
        _ind_with_obj([0.90, 0.05]),
    ]
    reps = select_representatives(front)
    assert reps["ideal_point"] is front[1]

def test_representatives_knee_is_interior():
    front = [
        _ind_with_obj([0.05, 0.95]),
        _ind_with_obj([0.15, 0.15]),
        _ind_with_obj([0.95, 0.05]),
    ]
    reps = select_representatives(front)
    assert reps["knee_point"] is front[1]

def test_representatives_all_four_keys():
    front = [_ind_with_obj([0.1 * i, 0.9 - 0.1 * i]) for i in range(5)]
    reps = select_representatives(front)
    assert set(reps.keys()) == {"best_dominance", "best_cost", "knee_point", "ideal_point"}
```

- [ ] **Step 9: Atualizar testes de integração**

```python
def test_run_smoke_small_config():
    result = run(seed=42, pop_size=20, n_generations=3, verbose=False)
    assert len(result.pareto_front) > 0
    assert all(ind.rank == 0 for ind in result.pareto_front)
    assert all(ind.objectives is not None for ind in result.pareto_front)
    assert set(result.representatives.keys()) == {"best_dominance", "best_cost", "knee_point", "ideal_point"}
    assert len(result.history) == 3

def test_save_results_produces_valid_json():
    result = run(seed=42, pop_size=10, n_generations=2, verbose=False)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        path = fh.name
    save_results(result, path)
    with open(path) as fh:
        data = json.load(fh)
    assert data["algorithm"] == "nsga2"
    assert data["seed"] == 42
    assert data["generations_run"] == 2
    first = data["pareto_front"][0]
    assert len(first["genes"]) == 5
    assert len(first["objectives"]) == 2
    for key in ("best_dominance", "best_cost", "knee_point", "ideal_point"):
        assert key in data["representatives"]
    os.unlink(path)

def test_save_plots_creates_pareto_png():
    result = run(seed=42, pop_size=10, n_generations=2, verbose=False)
    with tempfile.TemporaryDirectory() as outdir:
        save_plots(result, outdir)
        path = os.path.join(outdir, "pareto_front.png")
        assert os.path.exists(path), "pareto_front.png não existe"
        assert os.path.getsize(path) > 1000
```

- [ ] **Step 10: Atualizar o bloco `__main__`**

```python
if __name__ == "__main__":
    test_individual_has_nsga2_fields()
    test_individual_clone_copies_nsga2_fields()
    test_config_constants_exist()
    test_evaluate_objectives_returns_2tuple()
    test_evaluate_objectives_caches_on_individual()
    test_dominates_strict()
    test_dominates_requires_strict_in_at_least_one()
    test_dominates_fails_if_any_worse()
    test_sort_single_pareto_layer()
    test_sort_multiple_layers()
    test_sort_divergent_dominated_sets()
    test_crowding_assigns_inf_to_extremes()
    test_crowding_small_front_all_inf()
    test_crowding_middle_has_finite_value()
    test_tournament_picks_lower_rank()
    test_tournament_breaks_tie_by_crowding()
    test_tournament_stochastic_on_full_tie()
    test_representatives_identifies_extremes()
    test_representatives_ideal_closest_to_origin()
    test_representatives_knee_is_interior()
    test_representatives_all_four_keys()
    test_run_smoke_small_config()
    test_save_results_produces_valid_json()
    test_save_results_roundtrip_genes()
    test_save_plots_creates_pareto_png()
    print("Todos os testes NSGA-II passaram ✓")
```

- [ ] **Step 11: Rodar**

```bash
py test_nsga2.py
```
Saída esperada: `Todos os testes NSGA-II passaram ✓`

---

## Task 9 — `test_map_elites.py`: atualizar nomes (map_elites.py não existe ainda)

**Files:**
- Modify: `test_map_elites.py`

**Nota**: `map_elites.py` ainda não existe — estes testes falham por `ModuleNotFoundError`. Atualizar apenas os nomes para que o arquivo esteja pronto quando o módulo for implementado.

- [ ] **Step 1: Atualizar `_detail` e suas chamadas**

```python
def _detail(dominance_penalty: float, drift_penalty: float, specialization_penalty: float = 0.2) -> FitnessDetail:
    """Cria FitnessDetail mínimo para testes — sem simulações."""
    return FitnessDetail(
        fitness=0.0, winrates=[],
        specialization_penalty=specialization_penalty,
        drift_penalty=drift_penalty,
        dominance_penalty=dominance_penalty,
    )
```

- [ ] **Step 2: Atualizar todas as chamadas de `_detail` no arquivo**

Substituir `_detail(balance_error, drift, matchup_pen)` por `_detail(dominance_penalty, drift, specialization_penalty)` em cada chamada. Verificar também os acessos a `.matchup_dominance_penalty` → `.dominance_penalty` e `.attribute_cost` → `.specialization_penalty`.

- [ ] **Step 3: Substituir referências a `LAMBDA_MATCHUP`**

```python
assert "LAMBDA_DOMINANCE" in result
...
assert result["LAMBDA_DOMINANCE"] > 0.0
```

---

## Task 10 — Verificação final integrada

- [ ] **Step 1: Rodar todos os testes**

```bash
py test_fitness.py && py test_nsga2.py
```
Ambos devem terminar sem erro.

- [ ] **Step 2: Smoke test do GA (5 gerações)**

```bash
py main.py --algorithm ga --seed 42
```

Verificar: log mostra `dom=` e `spec=` (não `bal=`); fitness ≤ 0.

- [ ] **Step 3: Smoke test do NSGA-II**

```bash
py main.py --algorithm nsga2 --seed 42 --quiet
```

Verificar: termina sem erro; output mostra `dom=` e `cost=`.

- [ ] **Step 4: Verificar JSON**

```bash
py -c "import json; d=json.load(open('results/nsga2_results.json')); print('obj len:', len(d['pareto_front'][0]['objectives'])); print('reps:', list(d['representatives'].keys()))"
```

Saída esperada:
```
obj len: 2
reps: ['best_dominance', 'best_cost', 'knee_point', 'ideal_point']
```

- [ ] **Step 5: Commit**

```bash
git add fitness.py config.py ga.py nsga2.py nsga2_plots.py main.py test_fitness.py test_nsga2.py test_map_elites.py CLAUDE.md
git commit -m "refactor(fitness): remove balance_error; rename lambdas; NSGA-II to 2 objectives"
```
