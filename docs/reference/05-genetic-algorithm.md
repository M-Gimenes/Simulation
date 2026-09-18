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
| `drift_penalty` | 1.0 | distância ponderada ao perfil canônico — identidade **estrutural** |
| `dominance_penalty` | 1.0 | balanço global por personagem (primário) + teto de hard-counter + decisividade fora da banda, RMS |

### `drift_penalty` — identidade estrutural ponderada

**RMS ponderada** dos desvios normalizados ao perfil canônico, sobre os 10 genes
(atributos e pesos juntos) (`fitness._archetype_deviation`):

```
d_g         = (gene_g − canon_g) / (hi_g − lo_g)                 # fração do RANGE do bound
w_g         = DRIFT_DEFINING_WEIGHT  se g ∈ defining_genes  senão  1.0
deviation_i = sqrt( Σ_g w_g · d_g²  /  Σ_g w_g )
drift_penalty = mean_i(deviation_i)
```

**Normalização pelo range, não pelo máximo.** `(x − lo)/(hi − lo)` em vez de `x/hi`:
dividir por `hi` subestima sistematicamente genes de `lo` alto — o HP vai de 250 a
450, então mover 162 é **81% do range** e apenas 36% do máximo. O efeito medido no
indivíduo evoluído é de 1,3× no `drift_penalty` (0,2607 → 0,3417) e de 1,6× no
personagem mais deslocado (Turtle 0,2894 → 0,4535). A mesma convenção vale na Layer 2
do validador e no `drift_table` — "normalizado" tem uma definição só no projeto.

**Ponderação pelos genes definidores.** `ArchetypeDefinition.defining_genes` (campo
congelado) lista os genes em que o arquétipo ocupa um extremo por design, espelhando
as asserções inter da Layer 1 do validador — Zoner: `range`/`knockback`/`w_retreat`;
Rushdown: `speed`/`attack_cooldown`/`w_aggressiveness`; Combo Master: `stun`;
Grappler: `damage`; Turtle: `hp`/`attack_cooldown`/`speed`/`w_defend`. Eles pesam
`DRIFT_DEFINING_WEIGHT = 3.0` contra 1.0 dos demais: mover o alcance do Zoner custa
mais que mover o stun dele.

É **declaração de premissa** (o que o arquétipo é), não de resposta (quem vence quem)
— ver a linha premissa/resposta no `CLAUDE.md`. Consequência de bookkeeping: as
Layers 1-2 do validador medem o mesmo eixo que o fitness otimiza e por isso são
**parcialmente endógenas**; quem sustenta a leitura post-hoc de identidade é a
**Layer 3** (comportamental) somada ao ciclo de vantagens, que nada no fitness toca.

**Medido nos quatro indivíduos de referência do diagnóstico de 2026-09-16**, sob o
validador de **21** asserções que precedeu o `grab_power` — é a evidência que decidiu a
convenção, não um número corrente (os atuais, de 23, estão em `results/baselines.json`).
O critério: drift ascendente deve bater com o validador descendente — `knee_point` 19/21 >
`ideal_point` 16/21 > `best_dominance` 11/21 > AG escalar 8/21; scores re-medidos após a
correção, já que a Layer 2 do validador usa a mesma normalização:

| variante | knee (19/21) | ideal (16/21) | best_dom (11/21) | AG (8/21) | ordem bate? | gap AG−best_dom |
|---|---|---|---|---|---|---|
| `x/hi` uniforme (antiga) | 0,0885 | 0,1554 | 0,2709 | 0,2607 | **não** (AG e best_dom invertidos) | −0,010 |
| range, uniforme | 0,1302 | 0,2062 | 0,3245 | 0,3417 | sim | 0,017 |
| range, ponderada (atual) | 0,1279 | 0,2054 | 0,3150 | 0,3579 | sim | **0,043** |

Ou seja: a **normalização** conserta a ordenação; a **ponderação** alarga a margem. O
peso satura (0,055 em 5,0; 0,073 em 12,0) e pesos altos tornam os genes não-definidores
quase gratuitos — 3,0 mantém os dois lados com preço.

`LAMBDA_DRIFT = 1.0`, igual a `LAMBDA_DOMINANCE` — pesa equilíbrio e preservação de
identidade na mesma escala, reflexo do trade-off central da tese. O AG escalar dá
**um** ponto desse trade-off; o mapa completo vem do NSGA-II. (Era 6.0, que prendia o
AG no canônico — ver [10-known-issues.md](10-known-issues.md) V1.)

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
  arestas do ciclo como **vantagens** dentro de uma banda (`[0.35, 0.65]` com cap
  0.15), barrando counters esmagadores (ex.: 100×0). Dentro da banda o par não é
  penalizado.
- **Secundário — decisividade por-luta (`decis_term`):** score por-luta contínuo
  (`_fight_score`): em KO, `score = 0.5 + 0.5·(HP_frac do vencedor)` — esmaga →
  ~1.0, ganha no fio → ~0.5; em timeout, a fração de HP%. `D = média(|score_luta −
  0.5|) ∈ [0, 0.5]`, com excesso fora da **banda** `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]`.
  O **teto** (`MATCHUP_THRESHOLD = 0.20`) é o guarda que trabalha: pega
  **blowout-coinflip** — 55% A-esmaga / 45% B-esmaga ⇒ WR global ~50% mas toda luta
  é um massacre (todo blowout dá margem ~0.5). O **piso**
  (`MATCHUP_FLOOR = 0.02`) é só guarda de **degenerescência** e fica bem abaixo da
  faixa de operação — ver abaixo.

```
global_excess = |WR_global − 0.5| / 0.5
cap_excess    = max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP)
decis_excess  = max(0, D − MATCHUP_THRESHOLD)/(0.5 − MATCHUP_THRESHOLD)   # blowout
              + max(0, MATCHUP_FLOOR − D)/MATCHUP_FLOOR                    # fino demais
```

- **Por que o piso é tão baixo:** ele já foi `0.10`, e nessa altura empurrava
  **contra** o termo primário — equilibrar aproxima as lutas, e o piso punia
  exatamente isso. Medido, penalizava 5/10, 5/10 e 3/10 pares nos três indivíduos
  evoluídos, e era ele — um termo secundário de peso 0,5 — que decidia a comparação
  AG × NSGA-II. A premissa por trás dele ("abaixo do piso é quase-empate, luta que
  não aconteceu") **não vale no motor reformado**: toda luta termina em KO (100% em
  70 pares medidos, inclusive rosters aleatórios), então `D` baixo é KO no fio — a
  melhor luta possível. Faixas medidas: roster degenerado (dano mín / HP máx /
  GUARDA total, 0% de KO, timeout com HP idêntico) `D ≤ 0,008`; espelho puro dos 5
  canônicos `D ∈ [0,020, 0,033]`; pares reais `D ≥ 0,045`. O piso em **0,02** fica na
  base da faixa do espelho — abaixo do que dois personagens **idênticos** produzem —
  e por isso penaliza 0/10 pares em operação normal.
- **Os três termos são reportados separados:** `_dominance_penalty` devolve um
  `DominanceTerms` (`global_term`, `cap_term`, `decis_term`), guardado no
  `FitnessDetail`. O `multi_run` grava os três por semente e agregados; o
  `compare_algorithms` imprime a decomposição lado a lado, de forma **descritiva** —
  eles não entram na bateria de Mann-Whitney para não inflar a correção de Holm sobre
  as métricas que já estão lá. Perder no termo primário (peso 1,0) e perder num
  secundário (peso 0,5) são leituras opostas do mesmo composto.
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
  3 sorteados. (O NSGA-II **não** usa este operador: lá o torneio é binário e ordenado
  por rank de Pareto + crowding, `operators.nsga2_binary_tournament`.)
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
- **Elitismo:** top `operators.elite_count(pop_size)` clonados direto a cada geração —
  uma **fração** (`ELITE_RATE = 0.10`) do tamanho **real** da população, não uma contagem
  absoluta. `ELITE_SIZE = 30` é a derivação no orçamento default e existe só como
  referência; quem manda no laço é a taxa. A distinção importa porque uma execução de
  orçamento reduzido herdando 30 elites absolutos teria elitismo efetivo de 25% (pop 120)
  ou 100% (pop 30) — nesse último caso a geração seguinte é só clones e **o AG para de
  buscar**, sem erro e produzindo números plausíveis. Taxa 0 devolve 0 elites (é o braço
  "sem elitismo" do sweep); qualquer taxa positiva preserva no mínimo o melhor.

> **Elitismo e torneio são estado de processo** (`operators.set_selection` /
> `set_selection_override`), pela mesma razão dos λ e dos pesos do dominance: um sweep os
> varia entre execuções e `from .config import X` congelaria o valor no import. **Sem** a
> plumbing de `RuntimeState`, porém — os dois são lidos só por `next_generation` e
> `tournament_selection`, que rodam exclusivamente no processo pai (os workers avaliam
> fitness, nunca reproduzem), então não atravessam o spawn. `set_selection_override`
> recalcula também `ELITE_SIZE` no carimbo, senão o artefato de um braço afirmaria a taxa
> do braço ao lado da contagem do arquivo.

**Os dois valores foram testados** (2026-09-18, 7 braços × 5 sementes em orçamento
reduzido: elitismo 0 · 5% · 20% · 30%, torneio 2 · 5 · 7). Nenhum braço supera 10% / 3,
que têm o menor número de counters duros e o menor `cap_term` dos oito; a n = 5 as
diferenças não se separam do ruído. Tabela e leitura em
[tcc/04](../tcc/04-caminhos-e-decisoes.md).

## Critérios de convergência e parada

O AG escalar **roda sempre `MAX_GENERATIONS` gerações**. Convergência e estagnação são
**eventos registrados** (`converged_at`, `stagnated_at`), não paradas.

> **Por que orçamento fixo nos dois algoritmos.** O NSGA-II não tem como parar pelo
> critério do escalar: *"o roster está equilibrado?"* não se pergunta a uma **fronteira**,
> que de propósito contém pontos desequilibrados e fiéis — e perguntar a um representante
> faz a resposta depender de uma escolha arbitrária. Parar o escalar mais cedo tornaria a
> comparação ambígua: "melhor" ficaria indistinguível de "usou menos orçamento". Com os
> dois em orçamento fixo, a comparação é de **qualidade sob orçamento igual**, e
> `converged_at` vira um segundo eixo — **velocidade** — que antes não existia.

Convergência é o mesmo predicado valendo duas vezes: no laço (gate) e numa reavaliação
independente com `SIMS_CONVERGENCE_CHECK = 200` simulações extras (confirmação). Sob C2 o
critério é o equilíbrio **global**, não "todo par a 50%":

```
roster_balanced(detail) =
      todo personagem com WR global dentro de GLOBAL_CONVERGENCE_THRESHOLD (0.10) de 50%
  E   nenhum par com |WR_par − 0.5| > MATCHUP_WR_CAP (0.15)
```

1. **Gate:** `roster_balanced(best_detail)` — sobre a avaliação do laço, que já está
   em mãos; custo zero.
2. **Confirmação:** `roster_balanced(confirmed)` — 200 sims/matchup num stream de RNG
   **que o AG nunca viu** (`seed + CONVERGENCE_SEED_OFFSET`, via
   `ga._confirm_convergence`, que restaura o base do treino ao sair).

`roster_balanced` vive em `fitness.py`, ao lado de `character_balanced` e
`is_hard_counter`, e é a **fonte única** consumida pela convergência do AG, pelo
veredito por semente do `multi_run` e pelas tools de reporting. **Não** exige cada par
a 50% — arestas de ciclo são permitidas, e é esse o espaço em que o ciclo vive.

### Por que o gate não é um limiar escalar

O gate era `dominance_penalty ≤ 1e-9`, e isso era insatisfazível **por construção**,
não só na prática. `global_term` é uma RMS sobre **contagens discretas**: com
4 × `SIMS_PER_MATCHUP` = 600 lutas por personagem, o menor valor não-nulo possível é
`(1/600)/0.5/√5 ≈ 0.0015`. Não existe continuum entre 0 e 0.0015, então `1e-9`
significava **exatamente zero** — os 5 personagens com WR exatamente 300/600 na mesma
avaliação. `converged` era `False` sempre, e todo o ramo de confirmação era **código
morto** descrito na metodologia.

Subir o limiar para um escalar calibrado manteria uma versão mais branda do mesmo
defeito: o composto inclui o `decis_term`, que **não faz parte da definição de
convergência**. Um roster genuinamente convergido (todos em banda, zero counters
duros) mas com lutas decisivas teria dominance alto e seria barrado pelo gate. Testar
o predicado direto não tem essa lacuna.

### O stream de avaliação roda por geração

`ga.run` define o stream de cada geração com `fitness.generation_seed(seed, g)` —
mesma função que o NSGA-II usa, para que o protocolo de avaliação seja idêntico nos
dois e a comparação não confunda "algoritmo" com "forma de avaliar".

**Dentro** da geração todo indivíduo enfrenta o mesmo stream (CRN); **entre** gerações
o stream muda. Antes, `set_seed_base(seed)` era chamado uma vez e as
`MAX_GENERATIONS` inteiras corriam sobre uma realização só do RNG — a população tinha
o orçamento completo para se ajustar àquela sequência de sorteios em vez de ao jogo.
Medido (5 sementes, 60 gerações, 5 streams inéditos): a razão entre o `dominance` de
dentro e o de fora do laço cai de **4,14 para 2,20**, melhorando em **5/5** sementes
(Wilcoxon pareado p = 0,0312), e rosters que continuam equilibrados fora do laço vão
de 2,6 para **4,8** de 5 (também 5/5, p = 0,0312). A **magnitude** do ganho em
equilíbrio não está estabelecida (3/5, p = 0,31): o que a evidência sustenta é que o
resultado passou a sobreviver a streams inéditos.

Como os elites chegam medidos no stream anterior, a geração inteira é reavaliada —
custo ~1,8× (no NSGA-II é ~2×, ver [06](06-nsga2.md)). E o fitness passa a flutuar
entre gerações por troca de stream, então **`stagnated_at` fica menos confiável**;
`converged_at` não sofre, porque testa o predicado `roster_balanced` e não o fitness.
Medido na bateria de n = 20 (2026-09-18): a estagnação dispara em **10/20** sementes, tarde
(geração 99,5 ± 21,2), enquanto a convergência sai em 20/20, na geração 34,8 ± 17,1.

### Por que a confirmação roda fora do stream do treino

O laço avalia todo indivíduo de uma geração sob o mesmo stream (Common Random
Numbers) — correto para **seleção**, porque a diferença de fitness passa a refletir
genes e não sorteio. Mas
reavaliar nesse mesmo stream não confirma nada: mede a mesma realização do RNG com mais
amostras, e a confirmação **não pode discordar do gate**. Medido num indivíduo que
passou: equilibrado sob a semente de treino (5/5 em banda, 0 counters duros) e **não
equilibrado sob quatro streams independentes** (5/5 em banda, mas 1-2 counters duros em
cada). O que quebra é sempre o par-a-par, nunca a WR global — o ajuste ao stream se
concentra ali.

Por isso a confirmação resseta para `seed + CONVERGENCE_SEED_OFFSET` (100000, escolhido
para não colidir com treino 42+, `MULTI_RUN_VALIDATION_SEED` 9999 nem
`EXTERNAL_VALIDATION_SEED_START` 10000+) e devolve o base do treino ao sair. Convergir
passa a significar **"o equilíbrio sobrevive a um stream que o AG nunca viu"**, e o
`best_detail` devolvido pelo AG vira uma medição fora da amostra. Consequência esperada
e aceita: convergência fica bem mais rara — medido num run curto (pop 120, 60 gerações,
seed 42), o gate disparou **16 vezes** e a confirmação fora do stream rejeitou **as 16**.
É o ajuste ao stream quantificado. No orçamento de produção, sobre as 20 sementes da
bateria, o gate disparou 70 vezes e a confirmação recusou 50 (**71%**) — e ainda assim
todas as 20 convergiram: a confirmação atrasa a convergência, não a impede.

A confirmação é testada **só até o primeiro sucesso**: o que interessa é *quando*
convergiu, e cada disparo custa `SIMS_CONVERGENCE_CHECK` simulações extras.
`STAGNATION_LIMIT = 30` gerações sem melhoria > 0.001 também vira evento registrado.

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
