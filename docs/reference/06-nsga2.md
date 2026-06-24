# 06 — NSGA-II (multi-objetivo)

Variante multi-objetivo do AG (Deb et al., 2002), em `src/engine/nsga2.py`.
Ativada com `py main.py --algorithm nsga2`. Compartilha simulação, fitness por
componente e operadores com o AG escalar.

## Objetivos

Otimiza **2 objetivos** simultaneamente, ambos minimizados, sem ponderação:

| Objetivo | Significado |
|---|---|
| `dominance_penalty` | dominância de matchups (RMS sobre HP-weighted scores) |
| `drift_penalty` | preservação de arquétipo (distância euclidiana ao canônico) |

`evaluate_objectives` retorna `(dominance_penalty, drift_penalty)` em escala
bruta — os `LAMBDA_*` do fitness escalar são ignorados. O NSGA-II torna
**explícito** o trade-off que o AG escalar colapsa num peso fixo: exatamente a
tensão central do TCC entre equilíbrio e preservação de identidade.

## Algoritmo

Implementação padrão de Deb 2002:

1. **Dominância de Pareto** (`_dominates`): `a` domina `b` se não é pior em nenhum
   objetivo e é estritamente melhor em ao menos um.
2. **Fast non-dominated sort** (`fast_non_dominated_sort`): particiona a população
   em fronteiras por rank, trabalhando com índices (não `.index()` — clones do
   canônico têm conteúdo igual e quebrariam `.index()` silenciosamente).
3. **Crowding distance** (`crowding_distance_assignment`): densidade local por
   objetivo, normalizada pelo span; extremos recebem `inf` para serem sempre
   preservados.
4. **Seleção** (`nsga2_binary_tournament`): menor rank vence; empate decide por
   maior crowding.
5. **Geração (μ+λ)**: combina pais + filhos, re-ranqueia e seleciona os melhores
   `pop_size` por (rank, crowding). Essa combinação **é** o elitismo do NSGA-II.

Roda `NSGA2_GENERATIONS = 150` gerações fixas (fronteiras de Pareto não
"convergem" para um ponto — não há critério de parada antecipada).

## Representantes da fronteira

`select_representatives` extrai 4 pontos da Pareto front final:

- **`best_dominance`** — mínimo em `dominance_penalty` (mais equilibrado, pode ter
  drift alto).
- **`best_drift`** — mínimo em `drift_penalty` (mais fiel ao canônico, pode ser
  desbalanceado).
- **`knee_point`** — ponto de máxima curvatura: mais distante (perpendicular) da
  reta que liga os dois extremos. O "melhor compromisso".
- **`ideal_point`** — mais próximo da utopia `(0, 0)` em distância euclidiana.

## Saída

`save_results` grava `results/nsga2_results.json` (fronteira completa, os 4
representantes com genes e objetivos, e histórico por geração). Plots em
`results/plots/nsga2/<timestamp>/` via `nsga2_plots.save_plots` (ver
[08-tools.md](08-tools.md)). Representantes consumidos por tools via
`Individual.from_nsga2(representative=...)`.
