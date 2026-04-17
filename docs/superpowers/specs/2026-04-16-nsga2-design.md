# NSGA-II — Design Spec

**Data:** 2026-04-16
**Objetivo:** Implementar o NSGA-II como alternativa multi-objetivo ao AG clássico, otimizando simultaneamente equilíbrio competitivo, qualidade do pior matchup e preservação de arquétipos. Produz uma fronteira de Pareto — não um único "vencedor" escalarizado — e permite comparação futura com o AG escalarizado já existente.

**Escopo deste spec:** apenas a implementação do NSGA-II. A comparação experimental com o AG clássico (múltiplas seeds, tabelas comparativas, métricas estatísticas) será tratada em spec futuro, após o NSGA-II estar rodando e gerando dados concretos.

---

## Contexto

O AG atual (`ga.py`) escalariza quatro componentes num único fitness via pesos `LAMBDA`, `LAMBDA_DRIFT`, `LAMBDA_MATCHUP`. Esses pesos são escolhidos manualmente — o que introduz uma suposição arbitrária sobre importância relativa. O NSGA-II (Deb et al., 2002) elimina essa escolha: trata cada componente como um objetivo independente e devolve o conjunto de soluções não-dominadas (fronteira de Pareto).

Para o TCC, isso é significativo: a pergunta "é possível equilibrar sem destruir arquétipos?" vira naturalmente multi-objetivo. O NSGA-II expõe explicitamente o trade-off `balance × drift` como uma curva de soluções viáveis, não como um ponto único.

---

## Objetivos otimizados

Três objetivos, todos **minimizar**, todos já em `[0, 1]` (sem normalização adicional):

| Objetivo                    | Fonte (já calculado em `FitnessDetail`)      | Semântica                                      |
| --------------------------- | -------------------------------------------- | ---------------------------------------------- |
| `balance_error`             | `FitnessDetail.balance_error`                | Equilíbrio agregado — WR médio longe de 50%    |
| `matchup_dominance_penalty` | `FitnessDetail.matchup_dominance_penalty`    | Pior matchup direto — dominância 1v1           |
| `drift_penalty`             | `FitnessDetail.drift_penalty`                | Deriva média dos arquétipos em relação ao canônico |

**`attribute_cost` é deliberadamente excluído** — é correlato de `drift_penalty` (um arquétipo que se afasta do canônico tende também a homogeneizar atributos). Incluí-lo adicionaria redundância, dispersaria a fronteira em 4D (zona onde NSGA-II começa a degradar) e não traria informação ortogonal.

---

## Arquitetura e módulos afetados

### Módulos novos

- **`nsga2.py`** — loop principal do NSGA-II (análogo ao `ga.py`): inicialização, avaliação multi-objetivo, sort não-dominado, crowding distance, seleção (μ+λ), logging por geração. Expõe `run()` e `NSGAResult`.
- **`nsga2_plots.py`** — geração das 3 projeções 2D (sempre) e do plot 3D (opcional).
- **`test_nsga2.py`** — smoke tests focados em correção algorítmica (dominação, crowding, seleção dos 5 representantes, smoke run end-to-end).

### Módulos modificados (mudanças cirúrgicas, zero refactor do AG)

- **`fitness.py`** — adiciona `evaluate_objectives(ind) -> tuple[float, float, float]`. Reusa `evaluate_detail` internamente; retorna apenas os 3 objetivos na ordem fixa `(balance_error, matchup_dominance_penalty, drift_penalty)`.
- **`operators.py`** — adiciona `nsga2_binary_tournament(pop)` usando `rank` + `crowding`. Funções existentes (`tournament_selection`, `crossover`, `mutate`, `next_generation`) intocadas.
- **`individual.py`** — adiciona 2 campos `Optional` em `Individual`: `rank: Optional[int] = None`, `crowding: Optional[float] = None`. Ambos invisíveis para o AG clássico (que nunca os lê). Serialização JSON ignora campos `None`.
- **`main.py`** — adiciona flag `--algorithm {ga,nsga2}` (default `ga`) e `--plot-3d`. Dispacha para `ga.run()` ou `nsga2.run()` conforme o flag.
- **`config.py`** — adiciona aliases explícitos: `NSGA2_POP_SIZE = POPULATION_SIZE`, `NSGA2_GENERATIONS = MAX_GENERATIONS`, `NSGA2_OBJECTIVES = ["balance_error", "matchup_dominance_penalty", "drift_penalty"]`.

### Princípio de isolamento

O AG clássico não sabe que NSGA-II existe. Os dois algoritmos compartilham `combat.py`, `fitness.py`, `operators.py` e `individual.py`. Nada do código do AG clássico é refatorado — zero risco de regressão nos dados já coletados.

---

## Algoritmo NSGA-II

### Pseudocódigo do loop principal

```
P₀ ← [canônico] + [POPULATION_SIZE−1 aleatórios]   # mesma inicialização do AG clássico
avaliar P₀ → (f₁, f₂, f₃) por indivíduo
fast_non_dominated_sort(P₀) → atribui rank
crowding_distance_por_fronteira(P₀) → atribui crowding

para gen em 0..MAX_GENERATIONS−1:
    Q ← offspring_via(P) usando:
        nsga2_binary_tournament (2×) → crossover (reusado) → mutate (reusado)
        até |Q| = POPULATION_SIZE
    avaliar Q

    R ← P ∪ Q                                      # |R| = 2N
    fast_non_dominated_sort(R) → atribui rank
    crowding_distance_por_fronteira(R) → atribui crowding

    P_next ← []
    para cada fronteira F em ordem de rank:
        se |P_next| + |F| ≤ POPULATION_SIZE:
            P_next.extend(F)
        senão:
            F_sorted ← ordena F por crowding desc
            P_next.extend(F_sorted[: POPULATION_SIZE − |P_next|])
            break
    P ← P_next

    logar: tamanho de cada fronteira em R, melhores valores em cada objetivo, tempo acumulado

extrair fronteira_final (rank=0) de P
selecionar 5 representantes
salvar resultado em nsga2_results.json
gerar plots
```

### Componentes algorítmicos

Todos padrão de Deb et al. 2002.

**`fast_non_dominated_sort(population) -> list[list[Individual]]`**
Complexidade O(MN²), M=3 objetivos, N=tamanho da população. Retorna fronteiras ordenadas: `[[rank_0], [rank_1], ...]`. Atribui `ind.rank` in-place.

**`crowding_distance(front) -> None`**
Atribui `ind.crowding` in-place para cada indivíduo da fronteira:
- Para cada objetivo m: ordena a fronteira por f_m; extremos recebem `crowding += inf`; intermediários recebem `crowding += (f_m[i+1] − f_m[i−1]) / (f_m_max − f_m_min)`.
- Fronteira com 1 ou 2 indivíduos: todos recebem `crowding = inf`.

**`nsga2_binary_tournament(pop) -> Individual`**
Sorteia 2 indivíduos; vence o de menor `rank`. Empate de rank → vence o de maior `crowding`. Empate de ambos → sorteio aleatório.

**Dominação estrita (Pareto):**
`a` domina `b` sse `a.f_i ≤ b.f_i` para todos `i` E `a.f_j < b.f_j` para algum `j`.

---

## Seleção dos 5 representantes

Executada uma única vez ao final do loop, sobre a fronteira de Pareto (rank=0).

1. **Melhor em balance** — `argmin_i(ind[i].objectives[0])`
2. **Melhor em matchup** — `argmin_i(ind[i].objectives[1])`
3. **Melhor em drift** — `argmin_i(ind[i].objectives[2])`
4. **Knee point** — indivíduo com maior distância perpendicular ao plano definido pelos 3 extremos acima. Implementação: constrói o plano via produto vetorial `(p₂−p₁) × (p₃−p₁)`, calcula `dist(p, plano) = |(p−p₁) · n̂|` para cada `p` da fronteira, escolhe argmax.
5. **Ideal point** — `argmin_i(norma_euclidiana(ind[i].objectives))` (distância à origem `(0,0,0)`). Como os 3 objetivos já estão em `[0,1]`, não há normalização extra.

O **knee point é o representante oficial** em tabelas comparativas com o AG clássico (academicamente mais defensável — não embute suposição de pesos iguais, como o ideal point faz implicitamente). Os 5 são reportados no JSON e destacados nos plots.

---

## Visualizações (`nsga2_plots.py`)

**3 projeções 2D (sempre geradas):**
- `balance × drift` — o trade-off principal da pergunta de pesquisa do TCC
- `balance × matchup` — equilíbrio médio vs pior caso
- `drift × matchup` — preservação vs dominância

Cada projeção: scatter de toda a fronteira (rank=0) em azul; 5 representantes destacados com marcadores e cores distintas:
- Círculo azul = extremo de balance
- Círculo verde = extremo de drift
- Círculo vermelho = extremo de matchup
- Triângulo preto = knee point
- Estrela amarela = ideal point

**1 plot 3D (opcional, flag `--plot-3d`):** scatter 3D com os 3 objetivos, mesma legenda dos representantes. Salvo como PNG (matplotlib). Se `plotly` estiver disponível, também salva versão interativa em HTML.

**Saída:** `plots/nsga2/<timestamp>/` (não sobrescreve runs anteriores). Arquivos: `proj_balance_drift.png`, `proj_balance_matchup.png`, `proj_drift_matchup.png`, opcionalmente `front_3d.png` e `front_3d.html`.

---

## Output (`nsga2_results.json`)

```json
{
  "algorithm": "nsga2",
  "seed": 42,
  "generations_run": 100,
  "pareto_front": [
    {"genes": [[...5 chars genes...]], "objectives": [0.12, 0.08, 0.05]}
  ],
  "representatives": {
    "best_balance":   {"genes": [...], "objectives": [...]},
    "best_drift":     {"genes": [...], "objectives": [...]},
    "best_matchup":   {"genes": [...], "objectives": [...]},
    "knee_point":     {"genes": [...], "objectives": [...]},
    "ideal_point":    {"genes": [...], "objectives": [...]}
  },
  "history": [
    {"gen": 0, "front_sizes": [23, 18, 12, ...], "best_per_objective": [0.18, 0.22, 0.15], "elapsed_s": 12.4}
  ]
}
```

Nota: `genes` segue o mesmo formato já usado em `results.json` do AG clássico (lista de 5 listas de 12 genes cada), permitindo reaproveitar `Individual.from_results()` com caminho parametrizável se necessário no futuro.

---

## Testes (`test_nsga2.py`)

Smoke tests no padrão do projeto (sem framework; rodados individualmente com `py test_nsga2.py`):

- **`test_non_dominated_sort`** — população artificial de 6 pontos com ranking conhecido → verifica rank atribuído a cada indivíduo.
- **`test_crowding_distance`** — fronteira de 5 pontos equidistantes em linha reta → verifica que extremos recebem inf e intermediários recebem valor ordenado esperado.
- **`test_binary_tournament`** — 2 indivíduos com `rank` diferente → vence menor rank; mesmo rank com crowding diferente → vence maior crowding.
- **`test_representatives`** — fronteira sintética 3D com extremos claros → verifica que os 3 extremos, knee e ideal são os pontos esperados.
- **`test_run_smoke`** — roda NSGA-II com `pop=20, gen=3` e valida que: fronteira final é não-vazia, 5 representantes existem e são distintos, JSON de saída é válido.

---

## Uso

```bash
py main.py                              # AG clássico (inalterado)
py main.py --algorithm nsga2            # NSGA-II, plots 2D
py main.py --algorithm nsga2 --plot-3d  # adiciona plot 3D
py main.py --algorithm nsga2 --seed 42 --quiet
```

---

## Nota de implementação — clean code

Durante a implementação (em cada tarefa do plano), invocar a skill **`clean-code`** antes de commitar. O sort não-dominado e o cálculo de crowding são trechos onde é fácil escrever versão densa e difícil de ler — a skill orienta a separação em funções curtas e nomeadas, com intenção explícita.

---

## Decisões e Justificativas

Material de referência para a escrita dos capítulos de Metodologia e Decisões de Design do TCC. Cada item abaixo documenta *por que* a escolha foi feita dessa forma e quais alternativas foram descartadas.

### Por que 3 objetivos e não 4

Os 4 componentes originais do fitness escalar (`balance_error`, `attribute_cost`, `drift_penalty`, `matchup_dominance_penalty`) foram reduzidos a 3 pela remoção de `attribute_cost`. Motivos:

1. **Correlação com drift:** um personagem que se afasta do canônico tende a homogeneizar atributos; os dois objetivos capturam dimensões quase paralelas. Manter ambos adiciona redundância sem ortogonalidade real.
2. **Degradação do NSGA-II em 4D:** a partir de 4 objetivos, a fração de indivíduos não-dominados aumenta drasticamente, fazendo crowding distance perder poder discriminativo. Em 3D, NSGA-II opera na sua zona canônica (caso ótimo do paper original de Deb).
3. **Narrativa do TCC:** 3 objetivos mapeiam diretamente a pergunta de pesquisa — equilíbrio agregado, equilíbrio por matchup, preservação de identidade.

**Alternativa descartada:** fundir `balance_error + matchup_dominance_penalty` em um único objetivo (reduzindo a 2 objetivos). Isso reintroduziria um peso escalarizado — exatamente o que o NSGA-II deveria evitar — enfraquecendo o argumento metodológico do TCC.

### Por que knee point + ideal point (não um só)

Os dois critérios capturam conceitos diferentes e podem apontar para soluções diferentes:

- **Knee point** é geométrico: maximiza curvatura da fronteira — o ponto onde ganhar +1% num objetivo passa a custar muito nos outros.
- **Ideal point** é de compromisso: minimiza distância Euclidiana à utopia `(0, 0, 0)` — assume implicitamente que os 3 objetivos pesam igual.

Quando os dois coincidem, a fronteira é bem-comportada. Quando divergem, a divergência é dado empírico do TCC (indica assimetria na fronteira). O **knee point é o oficial** para comparações 1-pra-1 com o AG clássico porque não embute suposição de pesos iguais — é uma escolha mais defensável academicamente.

### Por que manter o AG clássico intacto

O AG clássico já produziu dados válidos e foi validado. Refatorá-lo para um loop genérico pluggable ("seleção como estratégia") teria custo (risco de regressão) sem benefício direto para o TCC. O ganho pedagógico de separação limpa entre os dois algoritmos supera o ganho estético de DRY.

### Por que mesmo orçamento de avaliações

Comparação justa entre AG clássico e NSGA-II exige que ambos tenham acesso ao mesmo número de avaliações de fitness (a operação cara do sistema: cada avaliação = C(5,2) × SIMS_PER_MATCHUP simulações de combate). Manter `POPULATION_SIZE` e `MAX_GENERATIONS` iguais garante orçamento equivalente. Os aliases `NSGA2_POP_SIZE` e `NSGA2_GENERATIONS` em `config.py` permitem tunar depois sem tocar código.

### Posicionamento do MAP-Elites no TCC

MAP-Elites (já implementado) revela a **região alcançável** do espaço de soluções (interior), enquanto NSGA-II revela a **borda ótima** (fronteira). Os dois são complementares, não redundantes. Para o TCC:

- **Capítulo central:** AG clássico + NSGA-II (comparação principal)
- **Capítulo de análise de espaço (opcional, secundário):** MAP-Elites como "topografia" do espaço, contextualizando a fronteira
- **Apêndice técnico:** implementação e calibração do MAP-Elites (seu output já foi usado pra definir os lambdas do AG)

### Critério de parada: gerações fixas

NSGA-II não tem "convergência" análoga ao AG clássico (não existe um fitness escalar para comparar com threshold). A literatura majoritariamente usa número fixo de gerações. Alternativas consideradas:

- **Estagnação de hipervolume:** métrica correta para "fronteira parou de melhorar", mas computar hipervolume em 3D é caro (+100 linhas, overhead por geração). Fica como métrica de análise pós-execução, não como critério de parada.
- **Estagnação de fronteira:** fuzzy demais (quantos % de indivíduos novos definem "parou"?).

Decisão: parada por `MAX_GENERATIONS` fixo. Hipervolume pode ser calculado na análise comparativa futura.

---

## Referências

- Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). **A fast and elitist multiobjective genetic algorithm: NSGA-II.** IEEE Transactions on Evolutionary Computation, 6(2), 182–197.
- Branke, J., Deb, K., Dierolf, H., & Osswald, M. (2004). **Finding Knees in Multi-objective Optimization.** Parallel Problem Solving from Nature — PPSN VIII.
