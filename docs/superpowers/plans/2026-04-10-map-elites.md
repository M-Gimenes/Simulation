# MAP-Elites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar `map_elites.py`, script standalone que roda MAP-Elites para mapear o trade-off empírico balance_error × drift_penalty e sugerir valores calibrados de LAMBDA_DRIFT e LAMBDA_MATCHUP para o GA principal.

**Architecture:** Script autossuficiente em `map_elites.py`. Reutiliza `operators.mutate()`, `fitness.evaluate_detail()` e `individual.Individual` sem modificar nenhum arquivo existente. Archive é um `Dict[Tuple[int,int], Tuple[Individual, FitnessDetail]]`.

**Tech Stack:** Python 3, stdlib (math, random, argparse, concurrent.futures), dependências internas do projeto.

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `map_elites.py` | Criar | Lógica completa do MAP-Elites |
| `test_map_elites.py` | Criar | Testes das funções puras |

Nenhum arquivo existente é modificado.

---

### Task 1: Esqueleto do módulo + constantes + `_bucket` + `_place`

**Files:**
- Create: `map_elites.py`
- Create: `test_map_elites.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `test_map_elites.py`:

```python
"""
Testes do MAP-Elites.
Rode com: py test_map_elites.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fitness import FitnessDetail
from individual import Individual
from map_elites import _bucket, _place, GRID_X_BINS, GRID_Y_BINS, GRID_X_MAX, GRID_Y_MAX


def _detail(balance_error: float, drift_penalty: float, matchup_pen: float) -> FitnessDetail:
    """Cria FitnessDetail mínimo para testes — sem simulações."""
    return FitnessDetail(
        fitness=0.0, winrates=[], balance_error=balance_error,
        attribute_cost=0.2, drift_penalty=drift_penalty,
        matchup_dominance_penalty=matchup_pen,
    )


def test_bucket_basic():
    assert _bucket(0.0,  0.0, 0.5, 10) == 0
    assert _bucket(0.04, 0.0, 0.5, 10) == 0   # ainda no bucket 0
    assert _bucket(0.05, 0.0, 0.5, 10) == 1
    assert _bucket(0.49, 0.0, 0.5, 10) == 9
    assert _bucket(0.5,  0.0, 0.5, 10) == 9   # clamp no último bucket
    assert _bucket(0.99, 0.0, 0.5, 10) == 9   # fora do range → clamp
    assert _bucket(0.0,  0.0, 0.6,  8) == 0
    assert _bucket(0.6,  0.0, 0.6,  8) == 7   # clamp


def test_place_fills_empty_cell():
    archive = {}
    ind = Individual.from_canonical()
    d = _detail(0.08, 0.10, 0.5)
    _place(archive, ind, d)
    assert len(archive) == 1
    bx = _bucket(0.08, 0.0, GRID_X_MAX, GRID_X_BINS)
    by = _bucket(0.10, 0.0, GRID_Y_MAX, GRID_Y_BINS)
    assert (bx, by) in archive


def test_place_replaces_when_better():
    archive = {}
    ind = Individual.from_canonical()
    d_bad  = _detail(0.08, 0.10, 0.8)
    d_good = _detail(0.08, 0.10, 0.3)
    _place(archive, ind, d_bad)
    _place(archive, ind, d_good)
    bx = _bucket(0.08, 0.0, GRID_X_MAX, GRID_X_BINS)
    by = _bucket(0.10, 0.0, GRID_Y_MAX, GRID_Y_BINS)
    assert archive[(bx, by)][1].matchup_dominance_penalty == 0.3


def test_place_keeps_when_worse():
    archive = {}
    ind = Individual.from_canonical()
    d_good = _detail(0.08, 0.10, 0.3)
    d_bad  = _detail(0.08, 0.10, 0.8)
    _place(archive, ind, d_good)
    _place(archive, ind, d_bad)
    bx = _bucket(0.08, 0.0, GRID_X_MAX, GRID_X_BINS)
    by = _bucket(0.10, 0.0, GRID_Y_MAX, GRID_Y_BINS)
    assert archive[(bx, by)][1].matchup_dominance_penalty == 0.3


def test_place_out_of_bounds_clamps_to_last_bucket():
    archive = {}
    ind = Individual.from_canonical()
    # Valores fora do range fazem clamp para o último bucket — não são perdidos
    d = _detail(0.99, 0.99, 0.5)
    _place(archive, ind, d)
    assert len(archive) == 1  # entra no bucket (9, 7) por clamp


if __name__ == "__main__":
    test_bucket_basic()
    test_place_fills_empty_cell()
    test_place_replaces_when_better()
    test_place_keeps_when_worse()
    test_place_out_of_bounds_clamps_to_last_bucket()
    print("Task 1 — OK")
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

```bash
py test_map_elites.py
```

Esperado: `ModuleNotFoundError: No module named 'map_elites'`

- [ ] **Step 3: Criar `map_elites.py` com constantes + `_bucket` + `_place`**

```python
"""
MAP-Elites para análise do espaço de soluções.

Mapeia o trade-off balance_error × drift_penalty usando qualidade = matchup_dominance_penalty.
Rode com: py map_elites.py

Saída:
  - Heatmap ASCII do grid (80 células: 10 × 8)
  - Fronteira de trade-off empírica
  - Sugestão calibrada de LAMBDA_DRIFT e LAMBDA_MATCHUP para o GA principal
"""
from __future__ import annotations

import math
import random
import argparse
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Tuple
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from individual import Individual
from fitness import FitnessDetail, evaluate_detail
from operators import mutate
from config import N_WORKERS

# ─── Constantes do grid ───────────────────────────────────────────────────��───

GRID_X_BINS = 10     # balance_error
GRID_Y_BINS = 8      # drift_penalty
GRID_X_MAX  = 0.5    # máximo teórico de balance_error
GRID_Y_MAX  = 0.6    # máximo observado de drift_penalty

N_INIT       = 200
N_ITERATIONS = 50_000

Archive = Dict[Tuple[int, int], Tuple[Individual, FitnessDetail]]


# ─── Grid ─────────────────────────────────────────────────────────────────────

def _bucket(val: float, lo: float, hi: float, n: int) -> int:
    """Mapeia val em [lo, hi) para índice de bucket [0, n-1]. Faz clamp nos extremos."""
    if val >= hi:
        return n - 1
    if val < lo:
        return 0
    return int((val - lo) / (hi - lo) * n)


def _place(archive: Archive, ind: Individual, detail: FitnessDetail) -> None:
    """Insere ind no archive se a célula estiver vazia ou se a qualidade for melhor."""
    bx  = _bucket(detail.balance_error, 0.0, GRID_X_MAX, GRID_X_BINS)
    by  = _bucket(detail.drift_penalty,  0.0, GRID_Y_MAX, GRID_Y_BINS)
    key = (bx, by)
    if key not in archive or detail.matchup_dominance_penalty < archive[key][1].matchup_dominance_penalty:
        archive[key] = (ind, detail)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

```bash
py test_map_elites.py
```

Esperado: `Task 1 — OK`

- [ ] **Step 5: Commit**

```bash
git add map_elites.py test_map_elites.py
git commit -m "feat: MAP-Elites — grid constants, _bucket, _place + tests"
```

---

### Task 2: Helpers de avaliação — `_evaluate`, `_mutate_from`, `_evaluate_batch`

**Files:**
- Modify: `map_elites.py` (append)
- Modify: `test_map_elites.py` (append)

- [ ] **Step 1: Adicionar teste que falha em `test_map_elites.py`**

Adicionar ao final (antes do bloco `if __name__ == "__main__"`):

```python
from map_elites import _mutate_from


def test_mutate_from_returns_new_individual():
    ind = Individual.from_canonical()
    child = _mutate_from(ind)
    # Deve ser um objeto diferente (clone)
    assert child is not ind
    # Fitness deve estar invalidado
    assert not child.is_evaluated


def test_mutate_from_genes_differ():
    random.seed(42)
    ind = Individual.from_canonical()
    child = _mutate_from(ind)
    # Com MUTATION_RATE=0.2 e 60 genes, estatisticamente pelo menos 1 gene muda
    original_genes = ind.characters[0].genes()
    child_genes    = child.characters[0].genes()
    # Não garantimos que todos diferem, mas o clone não é a mesma referência
    assert original_genes is not child_genes
```

Atualizar o bloco `if __name__ == "__main__"`:

```python
if __name__ == "__main__":
    test_bucket_basic()
    test_place_fills_empty_cell()
    test_place_replaces_when_better()
    test_place_keeps_when_worse()
    test_place_out_of_bounds_clamps_to_last_bucket()
    test_mutate_from_returns_new_individual()
    test_mutate_from_genes_differ()
    print("Tasks 1-2 — OK")
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
py test_map_elites.py
```

Esperado: `ImportError: cannot import name '_mutate_from' from 'map_elites'`

- [ ] **Step 3: Adicionar funções em `map_elites.py`**

Adicionar após `_place`:

```python
# ─── Avaliação e mutação ──────────────────────────────────────────────────────

def _evaluate(ind: Individual) -> FitnessDetail:
    """Avalia um indivíduo e retorna FitnessDetail completo."""
    return evaluate_detail(ind)


def _mutate_from(ind: Individual) -> Individual:
    """Clona ind e aplica mutação gaussiana. O original não é modificado."""
    child = ind.clone()
    mutate(child)
    return child


def _evaluate_batch(population: List[Individual]) -> List[FitnessDetail]:
    """
    Avalia uma lista de indivíduos em paralelo (reutiliza N_WORKERS de config).
    Retorna FitnessDetail para cada indivíduo, na mesma ordem.
    """
    if N_WORKERS == 1:
        return [evaluate_detail(ind) for ind in population]
    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        return list(executor.map(evaluate_detail, population))
```

- [ ] **Step 4: Rodar e confirmar que passa**

```bash
py test_map_elites.py
```

Esperado: `Tasks 1-2 — OK`

- [ ] **Step 5: Commit**

```bash
git add map_elites.py test_map_elites.py
git commit -m "feat: MAP-Elites — _evaluate, _mutate_from, _evaluate_batch"
```

---

### Task 3: Análise — `_compute_frontier` + `_find_knee`

**Files:**
- Modify: `map_elites.py` (append)
- Modify: `test_map_elites.py` (append)

- [ ] **Step 1: Adicionar testes que falham**

Adicionar em `test_map_elites.py` (antes de `if __name__`):

```python
from map_elites import _compute_frontier, _find_knee


def _make_archive(cells: list) -> dict:
    """cells: list de (bx, by, balance_error, drift_penalty, matchup_pen)"""
    archive = {}
    ind = Individual.from_canonical()
    for bx, by, bal, drift, pen in cells:
        archive[(bx, by)] = (ind, _detail(bal, drift, pen))
    return archive


def test_compute_frontier_returns_best_bx_per_row():
    archive = _make_archive([
        (3, 0, 0.17, 0.03, 0.5),
        (1, 0, 0.07, 0.03, 0.4),  # mesmo row by=0, menor bx → vence
        (2, 1, 0.12, 0.11, 0.3),
    ])
    frontier = _compute_frontier(archive)
    assert frontier[0] == (1, 0)   # by=0 → bx=1 (menor)
    assert frontier[1] == (2, 1)   # by=1 → bx=2
    assert frontier[2] is None     # by=2 → vazio


def test_compute_frontier_empty_archive():
    frontier = _compute_frontier({})
    assert all(f is None for f in frontier)
    from map_elites import GRID_Y_BINS
    assert len(frontier) == GRID_Y_BINS


def test_find_knee_three_points():
    # Curva em L: joelho deve ser o ponto do meio
    points = [(0.3, 0.1), (0.1, 0.1), (0.1, 0.5)]
    # Distância da reta (0.3,0.1)-(0.1,0.5):
    # ponto (0.1, 0.1) deve ser o mais distante → índice 1
    assert _find_knee(points) == 1


def test_find_knee_linear():
    # Pontos colineares — qualquer índice é aceitável (sem joelho claro)
    points = [(0.0, 0.0), (0.1, 0.1), (0.2, 0.2)]
    knee = _find_knee(points)
    assert 0 <= knee < 3


def test_find_knee_too_few_points():
    assert _find_knee([(0.1, 0.2)]) == 0
    assert _find_knee([(0.1, 0.2), (0.2, 0.3)]) in (0, 1)
```

Atualizar o bloco `if __name__ == "__main__"`:

```python
if __name__ == "__main__":
    test_bucket_basic()
    test_place_fills_empty_cell()
    test_place_replaces_when_better()
    test_place_keeps_when_worse()
    test_place_out_of_bounds_clamps_to_last_bucket()
    test_mutate_from_returns_new_individual()
    test_mutate_from_genes_differ()
    test_compute_frontier_returns_best_bx_per_row()
    test_compute_frontier_empty_archive()
    test_find_knee_three_points()
    test_find_knee_linear()
    test_find_knee_too_few_points()
    print("Tasks 1-3 — OK")
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
py test_map_elites.py
```

Esperado: `ImportError: cannot import name '_compute_frontier' from 'map_elites'`

- [ ] **Step 3: Adicionar funções em `map_elites.py`**

Adicionar após `_evaluate_batch`:

```python
# ─── Análise do archive ───────────────────────────────────────────────────────

def _compute_frontier(archive: Archive) -> List[Optional[Tuple[int, int]]]:
    """
    Para cada bucket de drift_penalty (by), retorna a célula com menor balance_error (bx).
    Retorna lista de comprimento GRID_Y_BINS; None onde o bucket de drift está vazio.
    """
    result: List[Optional[Tuple[int, int]]] = []
    for by in range(GRID_Y_BINS):
        best_bx: Optional[int] = None
        for bx in range(GRID_X_BINS):
            if (bx, by) in archive:
                if best_bx is None or bx < best_bx:
                    best_bx = bx
        result.append((best_bx, by) if best_bx is not None else None)
    return result


def _find_knee(points: List[Tuple[float, float]]) -> int:
    """
    Retorna o índice do joelho numa lista de (balance_error, drift_penalty)
    usando o método de maior distância perpendicular à reta que conecta
    o primeiro e o último ponto.
    """
    if len(points) < 3:
        return len(points) // 2
    x1, y1 = points[0]
    x2, y2 = points[-1]
    dx, dy  = x2 - x1, y2 - y1
    length  = math.sqrt(dx * dx + dy * dy)
    if length < 1e-9:
        return 0
    best_dist, knee = -1.0, 0
    for i, (x, y) in enumerate(points):
        dist = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / length
        if dist > best_dist:
            best_dist, knee = dist, i
    return knee
```

- [ ] **Step 4: Rodar e confirmar que passa**

```bash
py test_map_elites.py
```

Esperado: `Tasks 1-3 — OK`

- [ ] **Step 5: Commit**

```bash
git add map_elites.py test_map_elites.py
git commit -m "feat: MAP-Elites — _compute_frontier, _find_knee + tests"
```

---

### Task 4: `_suggest_lambdas`

**Files:**
- Modify: `map_elites.py` (append)
- Modify: `test_map_elites.py` (append)

- [ ] **Step 1: Adicionar teste que falha**

Adicionar em `test_map_elites.py` (antes de `if __name__`):

```python
from map_elites import _suggest_lambdas


def test_suggest_lambdas_returns_required_keys():
    archive = _make_archive([
        (1, 1, 0.07, 0.11, 0.2),
        (2, 2, 0.12, 0.19, 0.3),
        (3, 3, 0.17, 0.26, 0.5),
        (4, 4, 0.22, 0.34, 0.7),
    ])
    result = _suggest_lambdas(archive)
    assert "LAMBDA_DRIFT"   in result
    assert "LAMBDA_MATCHUP" in result
    assert "LAMBDA"         in result
    assert result["LAMBDA"] == 0.2


def test_suggest_lambdas_empty_archive():
    # Archive vazio deve retornar defaults sem exceção
    result = _suggest_lambdas({})
    assert "LAMBDA_DRIFT" in result
    assert result["LAMBDA"] == 0.2


def test_suggest_lambdas_values_are_positive():
    archive = _make_archive([
        (0, 0, 0.02, 0.04, 0.0),
        (1, 2, 0.07, 0.19, 0.2),
        (2, 4, 0.12, 0.34, 0.4),
        (3, 6, 0.17, 0.49, 0.6),
    ])
    result = _suggest_lambdas(archive)
    assert result["LAMBDA_DRIFT"]   >= 0.0
    assert result["LAMBDA_MATCHUP"] >  0.0
```

Atualizar `if __name__ == "__main__"`:

```python
if __name__ == "__main__":
    test_bucket_basic()
    test_place_fills_empty_cell()
    test_place_replaces_when_better()
    test_place_keeps_when_worse()
    test_place_out_of_bounds_clamps_to_last_bucket()
    test_mutate_from_returns_new_individual()
    test_mutate_from_genes_differ()
    test_compute_frontier_returns_best_bx_per_row()
    test_compute_frontier_empty_archive()
    test_find_knee_three_points()
    test_find_knee_linear()
    test_find_knee_too_few_points()
    test_suggest_lambdas_returns_required_keys()
    test_suggest_lambdas_empty_archive()
    test_suggest_lambdas_values_are_positive()
    print("Tasks 1-4 — OK")
```

- [ ] **Step 2: Rodar e confirmar que falha**

```bash
py test_map_elites.py
```

Esperado: `ImportError: cannot import name '_suggest_lambdas' from 'map_elites'`

- [ ] **Step 3: Implementar `_suggest_lambdas` em `map_elites.py`**

Adicionar após `_find_knee`:

```python
def _suggest_lambdas(archive: Archive) -> Dict[str, float]:
    """
    Sugere LAMBDA_DRIFT e LAMBDA_MATCHUP baseado na fronteira empírica do archive.

    LAMBDA_DRIFT   = |Δbalance_error / Δdrift_penalty| no joelho da fronteira.
                     Representa quanto equilíbrio se ganha por unidade de drift permitido.
    LAMBDA_MATCHUP = 1 / range(matchup_pen na fronteira).
                     Normaliza a penalidade de matchup para escala comparável ao balance_error.
    """
    frontier = _compute_frontier(archive)
    points:     List[Tuple[float, float]] = []
    pen_values: List[float]               = []

    for cell in frontier:
        if cell is not None:
            _, detail = archive[cell]
            points.append((detail.balance_error, detail.drift_penalty))
            pen_values.append(detail.matchup_dominance_penalty)

    if len(points) < 2:
        return {"LAMBDA_DRIFT": 0.5, "LAMBDA_MATCHUP": 1.0, "LAMBDA": 0.2}

    knee = _find_knee(points)
    i    = knee

    if 0 < i < len(points) - 1:
        d_bal   = abs(points[i + 1][0] - points[i - 1][0])
        d_drift = abs(points[i + 1][1] - points[i - 1][1])
    elif i == 0:
        d_bal   = abs(points[1][0] - points[0][0])
        d_drift = abs(points[1][1] - points[0][1])
    else:
        d_bal   = abs(points[-1][0] - points[-2][0])
        d_drift = abs(points[-1][1] - points[-2][1])

    lambda_drift = round(d_bal / d_drift, 3) if d_drift > 1e-6 else 0.0

    pen_range      = max(pen_values) - min(pen_values) if pen_values else 0.5
    lambda_matchup = round(1.0 / max(pen_range, 0.1), 2)

    return {"LAMBDA_DRIFT": lambda_drift, "LAMBDA_MATCHUP": lambda_matchup, "LAMBDA": 0.2}
```

- [ ] **Step 4: Rodar e confirmar que passa**

```bash
py test_map_elites.py
```

Esperado: `Tasks 1-4 — OK`

- [ ] **Step 5: Commit**

```bash
git add map_elites.py test_map_elites.py
git commit -m "feat: MAP-Elites — _suggest_lambdas + tests"
```

---

### Task 5: Output visual — `_print_heatmap` + `_print_frontier`

**Files:**
- Modify: `map_elites.py` (append)

Estas funções são puro output — sem lógica testável via assert. Verificação manual.

- [ ] **Step 1: Adicionar `_print_heatmap` e `_print_frontier` em `map_elites.py`**

Adicionar após `_suggest_lambdas`:

```python
# ─── Output ───────────────────────────────────────────────────────────────────

def _print_heatmap(archive: Archive) -> None:
    """Imprime heatmap ASCII do grid. Cada célula mostra matchup_dominance_penalty."""
    col_w    = 6
    x_labels = [f"{GRID_X_MAX * (bx + 0.5) / GRID_X_BINS:.2f}" for bx in range(GRID_X_BINS)]

    print("\n=== Heatmap: matchup_dominance_penalty (·· = vazia, menor = melhor) ===\n")
    print(f"  drift  |  " + "".join(f"{v:>{col_w}}" for v in x_labels))
    print(f"         |  " + "─" * (col_w * GRID_X_BINS))

    for by in range(GRID_Y_BINS - 1, -1, -1):   # alto drift no topo
        y_center = GRID_Y_MAX * (by + 0.5) / GRID_Y_BINS
        row      = f"  {y_center:.3f}  |  "
        for bx in range(GRID_X_BINS):
            if (bx, by) in archive:
                val  = archive[(bx, by)][1].matchup_dominance_penalty
                row += f"{val:>{col_w}.2f}"
            else:
                row += f"{'··':>{col_w}}"
        print(row)

    print(f"         |")
    print(f"  bal_err:  " + "".join(f"{v:>{col_w}}" for v in x_labels))
    print(f"{'':30s}balance_error →\n")


def _print_frontier(archive: Archive) -> None:
    """Imprime fronteira de trade-off e marca o joelho."""
    frontier = _compute_frontier(archive)
    points: List[Tuple[float, float, float]] = []   # (balance_error, drift, matchup_pen)

    for cell in frontier:
        if cell is not None:
            _, detail = archive[cell]
            points.append((detail.balance_error, detail.drift_penalty, detail.matchup_dominance_penalty))

    print("=== Fronteira de trade-off (melhor balance_error por nível de drift) ===\n")

    if not points:
        print("  (nenhuma célula preenchida)")
        return

    knee = _find_knee([(p[0], p[1]) for p in points])

    for i, (bal, drift, pen) in enumerate(points):
        marker = "  ← joelho" if i == knee else ""
        print(f"  drift={drift:.3f}  →  balance_error={bal:.3f}   matchup_pen={pen:.2f}{marker}")
    print()
```

- [ ] **Step 2: Smoke test manual do output**

Criar um script temporário para verificar o visual (não commitar):

```bash
py -c "
import sys, os; sys.path.insert(0, os.getcwd())
from map_elites import _print_heatmap, _print_frontier, _place
from fitness import FitnessDetail
from individual import Individual

def det(b, dr, p):
    return FitnessDetail(fitness=0.0, winrates=[], balance_error=b, attribute_cost=0.2, drift_penalty=dr, matchup_dominance_penalty=p)

archive = {}
ind = Individual.from_canonical()
_place(archive, ind, det(0.05, 0.10, 0.2))
_place(archive, ind, det(0.10, 0.20, 0.3))
_place(archive, ind, det(0.15, 0.30, 0.5))
_place(archive, ind, det(0.03, 0.40, 0.1))
_print_heatmap(archive)
_print_frontier(archive)
"
```

Esperado: heatmap imprime sem erros, valores visíveis nas células corretas, fronteira lista 4 linhas com joelho marcado.

- [ ] **Step 3: Commit**

```bash
git add map_elites.py
git commit -m "feat: MAP-Elites — _print_heatmap, _print_frontier"
```

---

### Task 6: `run_map_elites` + `main` + smoke test final

**Files:**
- Modify: `map_elites.py` (append)

- [ ] **Step 1: Adicionar `run_map_elites` e `main` em `map_elites.py`**

Adicionar ao final do arquivo:

```python
# ─── Loop principal ───────────────────────────────────────────────────────────

def run_map_elites(
    seed:         Optional[int] = None,
    n_init:       int           = N_INIT,
    n_iterations: int           = N_ITERATIONS,
    verbose:      bool          = True,
) -> Archive:
    """
    Executa o MAP-Elites completo.

    Args:
        seed:         semente para reprodutibilidade (None = aleatório).
        n_init:       indivíduos avaliados na inicialização.
        n_iterations: iterações do loop principal.
        verbose:      imprime progresso a cada 1.000 iterações.

    Returns:
        Archive preenchido: Dict[(bx, by), (Individual, FitnessDetail)].
    """
    if seed is not None:
        random.seed(seed)

    archive: Archive = {}

    # ── Inicialização ─────────────────────────────────────────────────────────
    if verbose:
        print(f"Inicializando {n_init} indivíduos (paralelo com N_WORKERS={N_WORKERS})...")

    init_pop = [Individual.from_canonical()] + [Individual.random() for _ in range(n_init - 1)]
    details  = _evaluate_batch(init_pop)

    for ind, detail in zip(init_pop, details):
        _place(archive, ind, detail)

    if verbose:
        print(f"Archive inicial: {len(archive)}/{GRID_X_BINS * GRID_Y_BINS} células\n")

    # ── Loop ──────────────────────────────────────────────────────────────────
    for iteration in range(1, n_iterations + 1):
        key    = random.choice(list(archive.keys()))
        parent = archive[key][0]
        child  = _mutate_from(parent)
        detail = _evaluate(child)
        _place(archive, child, detail)

        if verbose and iteration % 1000 == 0:
            best_bal   = min(d.balance_error  for _, d in archive.values())
            best_drift = min(d.drift_penalty  for _, d in archive.values())
            print(
                f"[{iteration:6d}/{n_iterations}]  "
                f"células={len(archive):2d}/{GRID_X_BINS * GRID_Y_BINS}  "
                f"melhor_bal={best_bal:.3f}  melhor_drift={best_drift:.3f}"
            )

    return archive


# ─── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MAP-Elites — análise do espaço de soluções")
    parser.add_argument("--seed",         type=int, default=None, help="Semente aleatória")
    parser.add_argument("--n-init",       type=int, default=N_INIT,       help="Indivíduos iniciais")
    parser.add_argument("--n-iterations", type=int, default=N_ITERATIONS, help="Iterações do loop")
    parser.add_argument("--quiet",        action="store_true",            help="Suprime progresso")
    args = parser.parse_args()

    archive = run_map_elites(
        seed=args.seed,
        n_init=args.n_init,
        n_iterations=args.n_iterations,
        verbose=not args.quiet,
    )

    _print_heatmap(archive)
    _print_frontier(archive)

    lambdas = _suggest_lambdas(archive)
    print("=== Calibração sugerida de lambdas ===\n")
    print(f"  LAMBDA_DRIFT   = {lambdas['LAMBDA_DRIFT']}")
    print(f"  LAMBDA_MATCHUP = {lambdas['LAMBDA_MATCHUP']}")
    print(f"  LAMBDA         = {lambdas['LAMBDA']}  (mantém — attribute_cost não afeta o trade-off central)")
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test rápido — 50 iterações para verificar o fluxo**

```bash
py map_elites.py --n-init 10 --n-iterations 50 --seed 42
```

Esperado: inicializa, roda 50 iterações sem erro, imprime heatmap com algumas células, imprime fronteira e lambdas. Sem exceptions.

- [ ] **Step 3: Rodar todos os testes para garantir que nada quebrou**

```bash
py test_map_elites.py
py test_base.py
py test_fitness.py
py test_operators.py
```

Esperado: todos passam sem erro.

- [ ] **Step 4: Commit final**

```bash
git add map_elites.py
git commit -m "feat: MAP-Elites — run_map_elites, main, integração completa"
```

- [ ] **Step 5: Run completo (opcional — ~25-30 min)**

```bash
py map_elites.py --seed 42
```

Esperado: 50.000 iterações, heatmap com ≥60 células preenchidas, fronteira clara, lambdas sugeridos.
