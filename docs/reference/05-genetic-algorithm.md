# 05 — Algoritmo genético (AG escalar)

Loop em `src/engine/ga.py`; fitness em `src/engine/fitness.py`; operadores em
`src/engine/operators.py`. O NSGA-II compartilha fitness e operadores — ver
[06-nsga2.md](06-nsga2.md).

## Indivíduo

Cada indivíduo = 5 personagens (um por arquétipo) = 50 genes. Por personagem: 7
atributos + 3 pesos. A população inicial é `[canônico] + [299 aleatórios]`.

## Função de fitness

```
fitness = -(LAMBDA_DRIFT     × drift_penalty
          + LAMBDA_DOMINANCE × dominance_penalty)
```

Dois termos minimizados (o fitness é negativo; maior = melhor). `drift_penalty ∈
[0, 1]`; `dominance_penalty ∈ [0, DOMINANCE_GLOBAL_WEIGHT + DOMINANCE_CAP_WEIGHT +
DOMINANCE_DECIS_WEIGHT]` (hoje `[0, 2.0]`). São **os mesmos dois objetivos do
NSGA-II** — lá sem ponderação, aqui como soma ponderada; o escalar é um ponto do
trade-off que o NSGA-II mapeia. Avaliação por **round-robin completo**:
C(5,2) = 10 matchups × `SIMS_PER_MATCHUP = 150` simulações.

| Termo | Peso | Penaliza |
|---|---|---|
| `drift_penalty` | 1.0 | distância ao perfil canônico — preservação de identidade |
| `dominance_penalty` | 1.0 | balanço global por personagem (primário) + teto de hard-counter + decisividade fora da banda, RMS |

### `drift_penalty`

Distância euclidiana normalizada ao perfil canônico, sobre os 10 genes
(atributos e pesos juntos) (`fitness._archetype_deviation`):

```
deviation_i = sqrt( ( Σ ((attr−canon)/attr_max)²  +  Σ (w−w_canon)² ) / 10 )
drift_penalty = mean_i(deviation_i)
```

Atributos são normalizados pelo **máximo do bound** (`/hi`); pesos entram crus
(já em `[0,1]`). `LAMBDA_DRIFT = 1.0`, igual a `LAMBDA_DOMINANCE` — pesa equilíbrio
e preservação de identidade na mesma escala, reflexo do trade-off central da tese.
O AG escalar dá **um** ponto desse trade-off; o mapa completo vem do NSGA-II. (Era
6.0, que prendia o AG no canônico — ver [10-known-issues.md](10-known-issues.md) V1.)

### `dominance_penalty` — balanço global primário + teto de hard-counter + decisividade (formulação C2)

Equilíbrio **não** é "cada par a 50%" (equilíbrio plano, que destruiria o ciclo
por construção) e sim "**nenhum personagem domina o roster**". A penalidade soma
**três sinais cegos à direção**:

```
global_term = RMS_{i=1..5}  ( |WR_global_i − 0.5| / 0.5 )                          # PRIMÁRIO
cap_term    = RMS_{pares=1..10} ( max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP) )   # teto hard-counter
decis_term  = RMS_{pares=1..10} ( decisividade fora de [MATCHUP_FLOOR, MATCHUP_THRESHOLD] )            # qualidade de luta

dominance_penalty = DOMINANCE_GLOBAL_WEIGHT · global_term
                  + DOMINANCE_CAP_WEIGHT    · cap_term
                  + DOMINANCE_DECIS_WEIGHT  · decis_term
```

Com `DOMINANCE_GLOBAL_WEIGHT = 1.0`, `DOMINANCE_CAP_WEIGHT = 0.5`,
`DOMINANCE_DECIS_WEIGHT = 0.5` (máximo teórico `2.0`).

- **Primário — balanço global por personagem (`global_term`):** `|WR_global − 0.5| / 0.5`
  por boneco (RMS sobre os 5), onde `WR_global` é o win rate agregado do
  personagem sobre seus 4 oponentes. O ótimo é "ninguém domina o roster", mas
  **não** força cada par a 50%: um boneco a 50% global pode vencer 2 e perder 2 —
  exatamente o espaço em que o ciclo de vantagens pode existir. (Antes o termo
  primário era a WR **por-matchup**, cujo ótimo é todo par a 50% — equilíbrio plano,
  incompatível com o ciclo.)
- **Secundário — teto de hard-counter (`cap_term`):** penaliza só o excesso de
  `|WR_par − 0.5|` **acima** de `MATCHUP_WR_CAP` (RMS sobre os 10 pares). Mantém as
  arestas do ciclo como **vantagens** dentro de uma banda (`[0.30, 0.70]` com cap
  0.20), barrando counters esmagadores (ex.: 100×0). Dentro da banda o par não é
  penalizado.
- **Secundário — decisividade por-luta (`decis_term`):** score por-luta contínuo
  (`_fight_score`): em KO, `score = 0.5 + 0.5·(HP_frac do vencedor)` — esmaga →
  ~1.0, ganha no fio → ~0.5; em timeout, a fração de HP%. `D = média(|score_luta −
  0.5|) ∈ [0, 0.5]`, com excesso fora da **banda** `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]`.
  Guarda contra **blowout-coinflip** — 55% A-esmaga / 45% B-esmaga ⇒ WR global
  ~50% mas toda luta é um massacre; a decisividade por-luta pega isso (todo blowout
  dá margem ~0.5). Banda saudável `[0.10, 0.20]`: vencedor fecha com ~20-40% de HP.

```
global_excess = |WR_global − 0.5| / 0.5
cap_excess    = max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP)
decis_excess  = max(0, D − MATCHUP_THRESHOLD)/(0.5 − MATCHUP_THRESHOLD)   # blowout
              + max(0, MATCHUP_FLOOR − D)/MATCHUP_FLOOR                    # fino demais
```

- **Por que global, e não por-matchup:** o termo primário antigo (WR por-matchup)
  tinha como ótimo *todo par a 50%* — equilíbrio plano, que por construção é
  **incompatível com o ciclo** (um ciclo exige que pares tenham vencedor). Sob C2 o
  plano não força mais a quebra do ciclo; "o ciclo emerge das identidades
  preservadas?" passa a ser o achado real, não um artefato do objetivo. Ver
  [tcc/02-ciclo-canonico.md](../tcc/02-ciclo-canonico.md).
- **Gradiente em combate quase-determinístico:** a margem do KO varia
  continuamente, e quando as lutas ficam apertadas o ruído da soft-policy flipa
  desfechos → WR graduado emerge (logo os termos de WR têm gradiente). Ver
  [11-combat-review.md](11-combat-review.md).
- **Direcionalmente cego:** usa `|WR − 0.5|` e `|score − 0.5|` — não codifica quem
  deveria vencer. O ciclo continua métrica post-hoc.
- **RMS, não média:** extremos pesam mais que moderados, impedindo o AG de
  esconder um boneco dominante ou um counter duro atrás de uma média balanceada.

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
  - `clip()` aplica os bounds após cada mutação. Todos os genes são contínuos
    (não há mais atributo inteiro — `recovery`, o único, foi removido do modelo).
- **Elitismo:** top `ELITE_SIZE = 30` (10% de 300) clonados direto a cada geração.

## Critérios de convergência e parada

O AG escalar para por **convergência** quando o gate dispara e a confirmação
(com `SIMS_CONVERGENCE_CHECK = 200` simulações extras) vale. Sob C2 o critério é o
equilíbrio **global**, não "todo par a 50%":

1. **Gate:** `dominance_penalty ≤ 1e-9` no melhor indivíduo;
2. **Confirmação (a):** cada personagem com WR **global** dentro de
   `GLOBAL_CONVERGENCE_THRESHOLD (0.10)` de 50% — ninguém domina o roster;
3. **Confirmação (b):** nenhum par é counter duro — todo `|wr_par − 0.5| ≤
   MATCHUP_WR_CAP (0.20)`. **Não** exige cada par a 50% (arestas de ciclo são ok).

Os predicados `(a)` e `(b)` vivem em `fitness.py` (`character_balanced` e
`is_hard_counter`) e são a **fonte única** consumida tanto pela convergência do AG
quanto pelas tools de reporting.

Outras paradas: `STAGNATION_LIMIT = 30` gerações sem melhoria > 0.001, ou
`MAX_GENERATIONS = 150`.

> Nota: o melhor indivíduo é re-avaliado estocasticamente a cada geração, então o
> `best_fitness` reportado e o contador de estagnação operam sobre fitness
> re-amostrado (ruidoso), não sobre o valor cacheado. Ver
> [10-known-issues.md](10-known-issues.md).

## Saída

`py main.py` evolui, salva o melhor indivíduo em `results/results.json` (lista de
genes por personagem, consumida por tools via `Individual.from_results()`) e imprime
apenas um **headline curto** — motivo de parada, geração, `fitness/dom/drift` — e o
ponteiro `→ py -m src.tools.report --evolved`. A avaliação completa (matchups, drift
por gene, fingerprint, validador) vive **só** no dossiê do `report`, não no `main`.

`run()` ainda acumula `history` (lista de `GenerationStats`: `best/mean/worst
fitness`, `drift_penalty`, `dominance_penalty`, `elapsed_s` por geração) para a curva
de convergência da tese — ver [tcc/06-resultados-a-apresentar.md](../tcc/06-resultados-a-apresentar.md).
