# 05 — Algoritmo genético (AG escalar)

Loop em `src/engine/ga.py`; fitness em `src/engine/fitness.py`; operadores em
`src/engine/operators.py`. O NSGA-II compartilha fitness e operadores — ver
[06-nsga2.md](06-nsga2.md).

## Indivíduo

Cada indivíduo = 5 personagens (um por arquétipo) = 55 genes. Por personagem: 8
atributos + 3 pesos. A população inicial é `[canônico] + [299 aleatórios]`
(`GA_CANONICAL_SEED = True`). Com `ga.run(canonical_seed=False)` — ou
`multi_run --no-canonical-seed` — ela nasce 100% aleatória, como a do NSGA-II: é o braço
de controle que separa o efeito do algoritmo do efeito da inicialização.

## Função de fitness

```
fitness = -(LAMBDA_DRIFT     × drift_penalty
          + LAMBDA_DOMINANCE × dominance_penalty)
```

Dois termos minimizados (o fitness é negativo; maior = melhor). `drift_penalty ∈
[0, 1]`; `dominance_penalty ∈ [0, DOMINANCE_GLOBAL_WEIGHT + DOMINANCE_CAP_WEIGHT +
DOMINANCE_DECIS_WEIGHT]` (hoje `[0, 2.0]`). São **os mesmos dois objetivos do
NSGA-II** — lá sem ponderação, aqui como soma ponderada. Avaliação por **round-robin
completo**: C(5,2) = 10 matchups × `SIMS_PER_MATCHUP = 150` lutas, cada luta semeada por
`fitness.fight_seed` (ver [09-reproducibility.md](09-reproducibility.md)).

| Termo | Peso | Penaliza |
|---|---|---|
| `drift_penalty` | 1.0 | distância ponderada ao perfil canônico — identidade **estrutural** |
| `dominance_penalty` | 1.0 | balanço global por personagem (primário) + teto de hard-counter + decisividade fora da banda, RMS |

`LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1.0` pesa equilíbrio e identidade na mesma escala.
Só a **razão** entre os dois importa (a seleção por torneio é ordinal), e o sweep de
`LAMBDA_DRIFT` mostrou 1,0 como o joelho da curva: o `dominance` fica plano até ali e só
então explode. O mapa completo do trade-off vem do NSGA-II. Trajetória em
[thesis/04](../thesis/04-design-decisions.md).

### `drift_penalty` — identidade estrutural ponderada

**RMS ponderada** dos desvios normalizados ao perfil canônico, sobre os 11 genes
(`fitness._archetype_deviation`), comparados na forma de `fitness.drift_genes`: os 8
atributos intactos e os 3 pesos **reescalados para a soma canônica** — como a intenção é
sorteada proporcionalmente aos pesos, multiplicar os três por `k > 0` não muda nada no
combate, e o drift não cobra por isso.

```
d_g         = (gene_g − canon_g) / (hi_g − lo_g)                 # fração do RANGE do bound
w_g         = DRIFT_DEFINING_WEIGHT  se g ∈ defining_genes  senão  1.0
deviation_i = sqrt( Σ_g w_g · d_g²  /  Σ_g w_g )
drift_penalty = mean_i(deviation_i)
```

**Normalização pelo range, não pelo máximo.** `(x − lo)/(hi − lo)` em vez de `x/hi`:
dividir por `hi` subestima sistematicamente genes de `lo` alto — o HP vai de 250 a
450, então mover 162 é **81% do range** e apenas 36% do máximo. A mesma convenção vale
na Layer 2 do validador e no `drift_table` — "normalizado" tem uma definição só.

**Ponderação pelos genes definidores.** `ArchetypeDefinition.defining_genes` lista os
genes em que o arquétipo ocupa um extremo por design, espelhando as asserções inter da
Layer 1 do validador — Zoner: `range`/`knockback`/`w_retreat`; Rushdown:
`speed`/`attack_cooldown`/`w_aggressiveness`; Combo Master: `stun`; Grappler:
`damage`/`grab_power`; Turtle: `hp`/`attack_cooldown`/`speed`/`w_defend`. Eles pesam
`DRIFT_DEFINING_WEIGHT = 3.0` contra 1.0 dos demais: mover o alcance do Zoner custa
mais que mover o stun dele. 3,0 mantém os genes não-definidores com preço; pesos altos
os tornariam quase gratuitos. A medição que decidiu normalização e peso está em
[thesis/04](../thesis/04-design-decisions.md) ("A régua de identidade").

É **declaração de premissa** (o que o arquétipo é), não de resposta (quem vence quem)
— ver a linha premissa/resposta no `CLAUDE.md`. Consequência: as Layers 1-2 do
validador medem o mesmo eixo que o fitness otimiza e por isso são **parcialmente
endógenas**; quem sustenta a leitura post-hoc de identidade é a **Layer 3**
(comportamental) somada ao ciclo de vantagens, que nada no fitness toca.

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
  exatamente o espaço em que o ciclo de vantagens pode existir. Um termo primário por
  matchup teria como ótimo todo par a 50%, incompatível com o ciclo por construção (ver
  [thesis/02-canonical-cycle.md](../thesis/02-canonical-cycle.md)).
- **Secundário — teto de hard-counter (`cap_term`):** penaliza só o excesso de
  `|WR_par − 0.5|` **acima** de `MATCHUP_WR_CAP` (RMS sobre os 10 pares). Mantém as
  arestas do ciclo como **vantagens** dentro de uma banda (`[0.35, 0.65]` com cap
  0.15), barrando counters esmagadores (ex.: 100×0). Dentro da banda o par não é
  penalizado. O 0,15 é ancorado na grade de matchup da FGC — ver
  [07-configuration.md](07-configuration.md).
- **Secundário — decisividade por-luta (`decis_term`):** score por-luta contínuo
  (`_fight_score`): em KO, `score = 0.5 + 0.5·(HP_frac do vencedor)` — esmaga →
  ~1.0, ganha no fio → ~0.5; em timeout, a fração de HP%. `D = média(|score_luta −
  0.5|) ∈ [0, 0.5]`, com excesso fora da **banda** `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]`.
  O **teto** (`MATCHUP_THRESHOLD = 0.20`) é o guarda que trabalha: pega
  **blowout-coinflip** — 55% A-esmaga / 45% B-esmaga ⇒ WR global ~50% mas toda luta
  é um massacre. O **piso** (`MATCHUP_FLOOR = 0.02`) é só guarda de
  **degenerescência**: toda luta do motor termina em KO, então `D` baixo é KO no fio, a
  melhor luta possível, e o piso fica na base da faixa dos espelhos — abaixo do que dois
  personagens **idênticos** produzem.

```
global_excess = |WR_global − 0.5| / 0.5
cap_excess    = max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP)
decis_excess  = max(0, D − MATCHUP_THRESHOLD)/(0.5 − MATCHUP_THRESHOLD)   # blowout
              + max(0, MATCHUP_FLOOR − D)/MATCHUP_FLOOR                    # fino demais
```

- **Os secundários são carga estrutural**, e isso é medido: sem eles o AG alcança o
  melhor `global_term` e entrega todos os pares como counter duro — o blowout-coinflip
  que o cap existe para barrar. Sweep dos pesos em [thesis/04](../thesis/04-design-decisions.md).
- **Os três termos são reportados separados:** `_dominance_penalty` devolve um
  `DominanceTerms` (`global_term`, `cap_term`, `decis_term`), guardado no
  `FitnessDetail`. O `multi_run` grava os três por semente e agregados; o
  `compare_algorithms` imprime a decomposição lado a lado, de forma **descritiva** —
  eles não entram na bateria de Mann-Whitney para não inflar a correção de Holm sobre
  as métricas que já estão lá. Perder no termo primário (peso 1,0) e perder num
  secundário (peso 0,5) são leituras opostas do mesmo composto.
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
  - `clip()` aplica os bounds após cada mutação. Todos os genes são contínuos.
- **Elitismo:** top `operators.elite_count(pop_size)` clonados direto a cada geração —
  uma **fração** (`ELITE_RATE = 0.10`) do tamanho **real** da população, não uma contagem
  absoluta: uma execução de orçamento reduzido herdando 30 elites absolutos teria
  elitismo efetivo de 25% (pop 120) ou 100% (pop 30), e no último caso o AG pararia de
  buscar sem dar sinal. Taxa 0 devolve 0 elites; qualquer taxa positiva preserva no
  mínimo o melhor.

> **Elitismo e torneio são estado de processo** (`operators.set_selection` /
> `set_selection_override`), pela mesma razão dos λ e dos pesos do dominance: um sweep os
> varia entre execuções e `from .config import X` congelaria o valor no import. **Sem** a
> plumbing de `RuntimeState`, porém — os dois são lidos só por `next_generation` e
> `tournament_selection`, que rodam exclusivamente no processo pai (os workers avaliam
> fitness, nunca reproduzem).

**Os dois valores foram testados** (sweep de 7 braços: elitismo 0 · 5% · 20% · 30%,
torneio 2 · 5 · 7) e nenhum braço supera 10% / 3. Tabela e leitura em
[thesis/04](../thesis/04-design-decisions.md).

## Critérios de convergência e parada

O AG escalar **roda sempre `MAX_GENERATIONS` gerações**. Convergência é **evento
registrado** (`converged_at`), não parada. Não há evento de estagnação: com o stream
rotacionando a cada geração, o "melhor fitness histórico" seria o máximo de valores
ruidosos — sobe por sorte e raramente é batido —, e o evento mediria a catraca do ruído,
não a busca.

> **Por que orçamento fixo nos dois algoritmos.** O NSGA-II não tem como parar pelo
> critério do escalar: *"o roster está equilibrado?"* não se pergunta a uma **fronteira**,
> que de propósito contém pontos desequilibrados e fiéis — e perguntar a um representante
> faz a resposta depender de uma escolha arbitrária. Parar o escalar mais cedo tornaria a
> comparação ambígua: "melhor" ficaria indistinguível de "usou menos orçamento". Com os
> dois em orçamento fixo, a comparação é de **qualidade sob orçamento igual**, e
> `converged_at` vira um segundo eixo — **velocidade**.

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

**Por que o gate é o predicado, e não um limiar no composto.** `global_term` é uma RMS
sobre contagens discretas — com 600 lutas por personagem, o menor valor não-nulo é
≈ 0,0015 —, então um limiar como `1e-9` exigiria os 5 personagens exatamente a 50%, e
nunca dispararia. E qualquer limiar no composto barraria um roster convergido de lutas
decisivas, porque o `decis_term` não faz parte da definição de convergência.

### O stream de avaliação roda por geração

`ga.run` define o stream de cada geração com `fitness.generation_seed(seed, g)` —
mesma função que o NSGA-II usa, para que o protocolo de avaliação seja idêntico nos
dois e a comparação não confunda "algoritmo" com "forma de avaliar".

**Dentro** da geração todo indivíduo recebe os mesmos sorteios (CRN, uma semente por
luta); **entre** gerações o stream muda. Sem a troca, as `MAX_GENERATIONS` inteiras
correriam sobre uma realização só do RNG, e a população teria o orçamento completo para
se ajustar àquela sequência de sorteios em vez de ao jogo. Medições em
[thesis/04](../thesis/04-design-decisions.md).

Como os elites chegam medidos no stream anterior, a geração inteira é reavaliada —
custo ~1,8× (no NSGA-II é ~2×, ver [06](06-nsga2.md)). O fitness passa a flutuar entre
gerações por troca de stream; `converged_at` não sofre, porque testa o predicado
`roster_balanced` e não o fitness.

> **Orçamento igual = descendentes iguais.** Os dois algoritmos geram 300 filhos novos por
> geração. O NSGA-II faz o dobro de avaliações (reavalia os pais junto dos filhos, porque
> a ordenação por dominância os compara no mesmo conjunto); o escalar reavalia só a
> população nova. A comparação é de qualidade sob o mesmo número de candidatos
> gerados, não sob o mesmo número de avaliações — declarar.

### Por que a confirmação roda fora do stream do treino

O laço avalia todo indivíduo de uma geração sob os mesmos sorteios (Common Random
Numbers) — correto para **seleção**, porque a diferença de fitness passa a refletir
genes e não sorteio. Mas reavaliar nesses mesmos sorteios não confirma nada: mede a mesma
realização do RNG com mais amostras, e a confirmação **não pode discordar do gate**. O
ajuste ao stream se concentra no par-a-par, nunca na WR global.

Por isso a confirmação ressemeia no stream da geração somado a `CONVERGENCE_SEED_OFFSET`
(100000, escolhido para não colidir com os streams de treino, `MULTI_RUN_VALIDATION_SEED`
9999 nem `EXTERNAL_VALIDATION_SEED_START` 10000+) e devolve o base do treino ao sair. Convergir
passa a significar **"o equilíbrio sobrevive a um stream que o AG nunca viu"**, e o
`best_detail` devolvido pelo AG vira uma medição fora da amostra. A contagem de
disparos e recusas sai em `convergence_gate_fired` / `convergence_rejected`.

A confirmação é testada **só até o primeiro sucesso**: o que interessa é *quando*
convergiu, e cada disparo custa `SIMS_CONVERGENCE_CHECK` simulações extras. Daí o que
`converged_at` significa: o **primeiro** disparo do gate que sobrevive à confirmação, num
teste repetido a cada geração — não que o roster fique equilibrado dali em diante. A
fração de sementes que **terminam** equilibradas é outra métrica do `multi_run`, e as duas
se leem juntas.

## Saída

`py main.py` evolui, salva o melhor indivíduo em `results/single_run/ga.json` (lista de
genes por personagem, consumida por tools via `Individual.from_results()`) e imprime
apenas um **headline curto** — motivo de parada, geração, `fitness/dom/drift` — e o
ponteiro `→ py -m src.analysis.report --evolved`. A avaliação completa (matchups, drift
por gene, fingerprint, validador) vive **só** no dossiê do `report`, não no `main`.

`run()` ainda acumula `history` (lista de `GenerationStats`: `best/mean/worst
fitness`, `drift_penalty`, `dominance_penalty`, `elapsed_s` por geração) para a curva
de convergência da tese — ver [thesis/06-results-to-present.md](../thesis/06-results-to-present.md).
