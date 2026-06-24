# 05 — Algoritmo genético (AG escalar)

Loop em `src/engine/ga.py`; fitness em `src/engine/fitness.py`; operadores em
`src/engine/operators.py`. O NSGA-II compartilha fitness e operadores — ver
[06-nsga2.md](06-nsga2.md).

## Indivíduo

Cada indivíduo = 5 personagens (um por arquétipo) = 60 genes. Por personagem: 9
atributos + 3 pesos. A população inicial é `[canônico] + [299 aleatórios]`.

## Função de fitness

```
fitness = -(LAMBDA_DRIFT     × drift_penalty
          + LAMBDA_DOMINANCE × dominance_penalty)
```

Dois termos, ambos em `[0, 1]` e minimizados (o fitness é negativo; maior =
melhor). São **os mesmos dois objetivos do NSGA-II** — lá sem ponderação, aqui
como soma ponderada; o escalar é um ponto do trade-off que o NSGA-II mapeia.
Avaliação por **round-robin completo**: C(5,2) = 10 matchups ×
`SIMS_PER_MATCHUP = 150` simulações.

| Termo | Peso | Penaliza |
|---|---|---|
| `drift_penalty` | 1.0 | distância ao perfil canônico — preservação de identidade |
| `dominance_penalty` | 1.0 | decisividade por-luta fora da banda saudável (RMS) |

### `drift_penalty`

Distância euclidiana normalizada ao perfil canônico, sobre atributos e pesos
juntos (`fitness._archetype_deviation`):

```
deviation_i = sqrt( ( Σ ((attr−canon)/attr_max)²  +  Σ (w−w_canon)² ) / 12 )
drift_penalty = mean_i(deviation_i)
```

Atributos são normalizados pelo **máximo do bound** (`/hi`); pesos entram crus
(já em `[0,1]`). `LAMBDA_DRIFT = 1.0`, igual a `LAMBDA_DOMINANCE` — pesa equilíbrio
e preservação de identidade na mesma escala, reflexo do trade-off central da tese.
O AG escalar dá **um** ponto desse trade-off; o mapa completo vem do NSGA-II. (Era
6.0, que prendia o AG no canônico — ver [10-known-issues.md](10-known-issues.md) V1.)

### `dominance_penalty` — decisividade por-luta numa banda

O sinal é a **decisividade**: a margem média **por luta**, não o desvio da WR
média. Score por-luta contínuo (`_fight_score`): em KO, `score = 0.5 + 0.5 ·
(HP_frac do vencedor)` — esmaga → ~1.0, ganha no fio → ~0.5; em timeout, a fração
de HP%. A decisividade de um matchup é `D = média(|score_luta − 0.5|) ∈ [0, 0.5]`.

```
excess_ij = max(0, D_ij − MATCHUP_THRESHOLD)/(0.5 − MATCHUP_THRESHOLD)   # blowout
          + max(0, MATCHUP_FLOOR − D_ij)/MATCHUP_FLOOR                    # fino demais
dominance_penalty = sqrt( mean_ij( excess_ij² ) )
```

- **Banda saudável `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]` = [0.05, 0.10]:** o
  vencedor fecha com ~10-20% de HP de folga. Penaliza os dois lados: blowout
  (decisiva demais) **e** quase-empate decidido no fio (fina demais — instável,
  parece coin-flip).
- **Por-luta, não da média:** `média(|score−0.5|)`, não `|média(score)−0.5|`. A
  diferença é crucial — a média da WR zera quando blowouts se cancelam (55%
  A-esmaga / 45% B-esmaga ⇒ WR ~50% mas toda luta é blowout). A média **por-luta**
  pega isso (todo blowout dá margem ~0.5 → penalidade alta).
- **Dá gradiente em combate determinístico:** mesmo sem variância, a margem do KO
  varia continuamente — o AG tem uma rampa para aproximar as lutas, não só um
  penhasco 0/1. Quando as lutas ficam apertadas, o ruído da soft-policy/hesitação
  passa a flipar desfechos → WR graduado emerge. Ver
  [11-combat-review.md](11-combat-review.md).
- **Direcionalmente cego:** usa `|score − 0.5|`, não codifica quem deveria vencer.
  O ciclo continua métrica post-hoc.
- **RMS, não média:** extremos pesam ~16× mais que moderados, impedindo o AG de
  esconder um matchup destruído atrás de uma média balanceada.

### NSGA-II ignora os λ

`evaluate_objectives` retorna apenas `(dominance_penalty, drift_penalty)` em
escala bruta. Mudar qualquer `LAMBDA_*` não afeta o NSGA-II.

## Operadores

- **Seleção:** torneio com `TOURNAMENT_SIZE = 3` — pega o de maior fitness entre
  3 sorteados.
- **Crossover por bloco de personagem:** cada um dos 5 personagens do filho é
  clonado integralmente de um dos pais (50/50). Preserva a coerência interna
  entre atributos e pesos de um mesmo arquétipo. *Consequência:* a recombinação
  de genes **dentro** de um personagem depende inteiramente da mutação — não há
  crossover gene a gene.
- **Mutação gaussiana** por gene com `MUTATION_RATE = 0.05`:
  - Atributos: `sigma = ATTRIBUTE_MUTATION_SIGMA × (hi − lo)` = 10% do range.
  - Pesos: `sigma = WEIGHT_MUTATION_SIGMA × (hi − lo)` = 2.5% do range.
  - Pesos têm sigma 4× menor (inércia evolutiva): atributos = capacidade, pesos =
    estratégia; explora-se mais capacidade do que estratégia.
  - `clip()` aplica bounds após cada mutação; atributos em `INTEGER_ATTRIBUTES`
    (só `recovery`, índice 8) são arredondados para int. A mutação opera no float
    interno (gradiente contínuo), o valor armazenado/usado no combate é inteiro.
- **Elitismo:** top `ELITE_SIZE = 30` (10% de 300) clonados direto a cada geração.

## Critérios de convergência e parada

O AG escalar para por **convergência** quando ambos valem, confirmados com
`SIMS_CONVERGENCE_CHECK = 200` simulações extras:

1. `dominance_penalty ≈ 0` no melhor indivíduo (nenhum matchup acima de 60% em
   score HP-weighted);
2. cada matchup direto: `|wr_ij − 0.5| ≤ MATCHUP_CONVERGENCE_THRESHOLD (0.10)`.

Outras paradas: `STAGNATION_LIMIT = 30` gerações sem melhoria > 0.001, ou
`MAX_GENERATIONS = 150`.

> Nota: o melhor indivíduo é re-avaliado estocasticamente a cada geração, então o
> `best_fitness` reportado e o contador de estagnação operam sobre fitness
> re-amostrado (ruidoso), não sobre o valor cacheado. Ver
> [10-known-issues.md](10-known-issues.md).

## Saída

`py main.py` salva o melhor indivíduo em `results/results.json` como lista de
genes por personagem. Consumido por tools via `Individual.from_results()`.
