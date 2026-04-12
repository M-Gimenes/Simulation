# MAP-Elites — Design Spec

**Data:** 2026-04-10  
**Objetivo:** Analisar o espaço de soluções do problema de balanceamento de arquétipos, mapeando o trade-off empírico entre equilíbrio e preservação de identidade. Resultado usado para calibrar os lambdas do GA principal.

---

## Contexto

O GA atual usa uma função de fitness escalar com pesos (`LAMBDA_MATCHUP`, `LAMBDA_DRIFT`) escolhidos manualmente. O MAP-Elites é rodado uma única vez para revelar empiricamente quais combinações de (equilíbrio × deriva de identidade) são alcançáveis, e qual custo cada trade-off tem. O output direto é a calibração dos lambdas.

---

## Abordagem

Script standalone `map_elites.py`, executado com `py map_elites.py`. Nenhum arquivo existente é modificado. Reutiliza:
- `operators.mutate()` — mutação gaussiana
- `fitness.evaluate_detail()` — retorna `FitnessDetail` com todos os componentes
- `individual.Individual.random()` e `.from_canonical()` — inicialização
- `config.POPULATION_SIZE`, `config.SIMS_PER_MATCHUP`, `config.N_WORKERS`

Sem crossover — MAP-Elites padrão usa somente mutação.

---

## Grid

| Eixo | Métrica | Range | Buckets | Tamanho do bucket |
|---|---|---|---|---|
| X (colunas) | `balance_error` | 0.0 → 0.5 | 10 | 0.05 |
| Y (linhas) | `drift_penalty` | 0.0 → 0.6 | 8 | 0.075 |
| Qualidade | `matchup_dominance_penalty` | — | — | mínimo vence |

**Total:** 80 células. Archive: `Dict[Tuple[int,int], Tuple[Individual, FitnessDetail]]`.

Indivíduos fora dos bounds são descartados silenciosamente.

---

## Algoritmo

### Inicialização
Avaliar 200 indivíduos (1 canônico + 199 aleatórios) em paralelo via `evaluate_population()` (reutiliza `N_WORKERS`), depois colocar cada um no archive via `_place()`.

### Loop principal — 50.000 iterações
```
1. Sorteia célula ocupada aleatoriamente do archive
2. Clona o ocupante → aplica mutate()
3. Avalia → FitnessDetail
4. _place(): insere se célula vazia,
             substitui se matchup_dominance_penalty novo < atual
```

### Critério de parada
50.000 iterações atingidas. Sem critério de convergência — MAP-Elites é exploração, não otimização.

### `_place()` em detalhe
```python
bx = _bucket(detail.balance_error, 0.0, 0.5, 10)
by = _bucket(detail.drift_penalty,  0.0, 0.6,  8)

if (bx, by) not in archive:
    archive[(bx, by)] = (ind, detail)
elif detail.matchup_dominance_penalty < archive[(bx, by)][1].matchup_dominance_penalty:
    archive[(bx, by)] = (ind, detail)
```

---

## Output

### 1. Progresso durante a execução (a cada 1.000 iterações)
```
[  1000/50000]  células=47/80  melhor_bal=0.043  melhor_drift=0.12
[ 10000/50000]  células=63/80  melhor_bal=0.031  melhor_drift=0.09
```

### 2. Heatmap ASCII do grid
Cada célula exibe `matchup_dominance_penalty` do melhor indivíduo. `··` = vazia.
Eixo Y = drift (crescente para cima), eixo X = balance_error (crescente para direita).

### 3. Fronteira de trade-off
Para cada linha (drift bucket), a célula com menor `balance_error` preenchida:
```
Fronteira balance_error × drift_penalty:
  drift=0.07  →  melhor balance_error=0.15   matchup_pen=0.33
  drift=0.15  →  melhor balance_error=0.10   matchup_pen=0.17
  drift=0.22  →  melhor balance_error=0.05   matchup_pen=0.00  ← joelho
  ...
```

### 4. Recomendação de lambdas
O joelho da fronteira é identificado como o ponto de maior distância perpendicular à reta que conecta o primeiro e o último ponto da fronteira (método da distância máxima — implementável diretamente, sem derivadas). O slope da fronteira antes e depois do joelho fornece a taxa de troca empírica:

```
Slope empírico: Δbalance_error / Δdrift_penalty → LAMBDA_DRIFT sugerido
Range de matchup_pen nas células da fronteira → LAMBDA_MATCHUP sugerido
```

Formato do output:
```
=== Calibração sugerida de lambdas ===
  LAMBDA_DRIFT   = X.XX
  LAMBDA_MATCHUP = X.XX
  LAMBDA         = 0.2  (mantém — attribute_cost não afeta o trade-off central)
```

---

## Estrutura do arquivo `map_elites.py`

```
_bucket(val, lo, hi, n) → int
_place(archive, ind, detail) → None
_mutate_from(ind) → Individual
_evaluate(ind) → FitnessDetail
_find_knee(frontier) → int  (índice do joelho)
_suggest_lambdas(archive) → Dict[str, float]
_print_heatmap(archive) → None
_print_frontier(archive) → None
run_map_elites(seed, n_init, n_iterations, verbose) → archive
main() → None
```

---

## O que não muda

- `combat.py`, `fitness.py`, `operators.py`, `individual.py`, `archetypes.py`, `character.py` — sem modificações
- `ga.py`, `main.py` — sem modificações
- `config.py` — sem modificações (MAP-Elites usa os parâmetros existentes)

---

## Parâmetros do MAP-Elites (hardcoded em `map_elites.py`)

| Parâmetro | Valor | Razão |
|---|---|---|
| `N_INIT` | 200 | Igual ao `POPULATION_SIZE` atual |
| `N_ITERATIONS` | 50.000 | Budget de ~25-30 min, resultado publicável |
| `GRID_X_BINS` | 10 | balance_error: resolução de 5pp |
| `GRID_Y_BINS` | 8 | drift_penalty: resolução de 0.075 |
| `GRID_X_MAX` | 0.5 | Máximo teórico de balance_error |
| `GRID_Y_MAX` | 0.6 | Máximo observado de drift nos runs anteriores |
