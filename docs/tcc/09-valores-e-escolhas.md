# 09 — Valores e escolhas: por que cada número

**Entra em**: Metodologia (parâmetros do sistema e do protocolo) e Limitações.

Catálogo de **todo valor e toda escolha** do sistema, com o porquê em uma ou duas frases e
o **tipo de sustentação** de cada um — para que a redação diga, número a número, o que foi
medido, o que foi argumentado e o que é simplesmente valor de projeto. O detalhe (a
trajetória, as tabelas) está onde o item aponta; aqui não se repete.

Os valores em si têm fonte única no código (`src/engine/config.py`, `src/engine/archetypes.py`)
e tabela em [`../reference/07-configuration.md`](../reference/07-configuration.md).

**Tipos de sustentação**

| marca | significa |
|---|---|
| **[medido]** | escolhido ou confirmado por experimento; o número que sustenta está no ponteiro |
| **[domínio]** | ancorado numa convenção externa ao sistema (a grade de matchup da FGC, a literatura) |
| **[coerência]** | derivado de outro valor ou de uma exigência do modelo — deixa de valer se aquele mudar |
| **[projeto]** | valor de projeto, **não calibrado**: nenhum experimento o escolheu nem o testou contra alternativas. Declarar como tal |

A honestidade da tabela é o ponto: um trabalho que chama todo número de "calibrado" é menos
defensável que um que separa os que foram medidos dos que são escolha.

---

## 1. Combate

- **Dois canais de ação** (postura sorteada, ataque por regra) — **[medido]**. Com o ataque
  como postura exclusiva, recuar era abrir mão do dano: o Zoner perdia 100% independente de
  alcance e knockback, e o `knockback` tinha derivada negativa. → [04](04-caminhos-e-decisoes.md)
  "A reforma do combate"; [`11-combat-review`](../reference/11-combat-review.md).
- **Intenção sorteada proporcional aos pesos** (soft-policy), única fonte de sorte —
  **[medido]**. Dá gradiente contínuo aos pesos; a variância de dano e a ação aleatória
  uniforme foram removidas porque afogavam o sinal das mutações. → [04](04-caminhos-e-decisoes.md)
  "Estocasticidade do combate".
- **`ACTION_PERSISTENCE_SUBTICKS = 5`** — **[coerência] + [medido]**. 5 = 1 tick = o cooldown
  mínimo, então quem tem `cooldown = 1` e sorteia GUARDA perde exatamente uma janela de
  ataque; a 10, perdia duas, e a razão sinal/ruído era pior em 8/8 genes. → [04](04-caminhos-e-decisoes.md)
  "A persistência da intenção".
- **`TICK_SCALE = 5`** — **[coerência]**. Resolução sub-tick para que o cooldown (1–5) não
  tenha só 5 valores e crie platôs no fitness. Com o stun contínuo, só o cooldown depende
  dele (`round(cd × 5)`), e é o que ancora a persistência; por isso ficou em 5. →
  [04](04-caminhos-e-decisoes.md) "A persistência da intenção".
- **Regra do impasse** (avanço imposto só quando ninguém alcança ninguém) — **[medido]**. Sem
  ela, Zoner × Turtle dava 100% de timeout; com ela, 0% nos 10 pares canônicos, sem tocar no
  kite. → [04](04-caminhos-e-decisoes.md) "A reforma do combate".
- **Colisão** — **[medido]**. Sem ela os corpos se cruzavam 134× por luta, anulando o alcance
  no clinch. → idem.
- **Empate como terceiro desfecho** — **[medido]**. Sem ele o desempate caía sempre para o
  lado A (índice menor): 54,90% no espelho do Rushdown. → idem.
- **`stun` como fração do cooldown, em [0, 0,6], timer contínuo** — **[coerência]**. O teto
  < 1 garante stun < cooldown (sempre há janela livre, sem perma-lockdown); o timer contínuo
  evita que o gene tenha só 4 níveis efetivos. → [04](04-caminhos-e-decisoes.md)
  "Calibração das mecânicas" e "A reforma do combate".
- **`DEFEND_DAMAGE_REDUCTION = 0,6`** (guarda reduz 40%) — **[projeto]**. Ajustado à mão
  durante o desenvolvimento (era 0,5), sem medição registrada. O que o modelo exige dele é
  qualitativo: guardar tem valor (reduz dano) e custo (abre mão do golpe, e o agarrão o
  pune). O ponto neutro do agarrão (0,4) deriva dele.
- **`grab_power` ∈ [0, 1], somado ao multiplicador contra quem guarda** — **[coerência]**. O
  intervalo vai de "guarda plena" (0) a "guarda punida" (1,6×); o ponto neutro 0,4 anula a
  guarda. Só o Grappler canônico (0,9) passa dele. → [04](04-caminhos-e-decisoes.md) "O agarrão".
- **Sem `defense` nem `recovery`** — **[medido]**. `recovery` era evolutivamente neutro (drifava
  para o piso); os dois adicionavam dimensões sem ganho de identidade. → [04](04-caminhos-e-decisoes.md)
  "Calibração das mecânicas"; [07](07-achados-e-limitacoes.md).
- **Campo 100, distância inicial 50** — **[coerência] + [projeto]**. A exigência é que
  todo alcance (≤ 20) seja menor que a distância inicial, para ninguém atacar no primeiro
  tick; a escala em si é de projeto, e o tamanho do campo — que decide quanto espaço de
  recuo existe antes do encurralamento — não foi variado no motor atual.
- **`MAX_TICKS` = 500 ticks (2500 sub-ticks)** — **[projeto]**, de efeito mínimo: é uma
  trava de segurança. Com a regra do impasse, 100% das lutas medidas (70 pares, rosters
  aleatórios inclusive) terminam em KO, então o limite não decidiu nenhuma delas.

**Bounds dos genes** ([`07-configuration`](../reference/07-configuration.md)):
- HP 250–450 — **[projeto]**, apertado para eliminar o "tanque absurdo" que o AG explorava;
  comporta os canônicos (Turtle no teto). → [04](04-caminhos-e-decisoes.md) "Calibração das mecânicas".
- `knockback` ≤ 3 — **[projeto]**: teto acima do Zoner canônico (2), baixado de 5 para
  fechar o zoning trivial por expulsão de alcance. → idem.
- `range` 5–20 — **[coerência]** com a distância inicial (acima).
- `damage` 15–30, `speed` 1–5, `attack_cooldown` 1–5, pesos 0–1 — **[projeto]**: comportam os
  canônicos com folga dos dois lados (exceto os 5 genes canônicos colados no bound,
  declarados em [04](04-caminhos-e-decisoes.md) "As constantes provisórias").

## 2. Arquétipos

- **Cinco arquétipos** — **[domínio]** (autoria): categorias clássicas de FGC, numa escolha
  de operacionalização como qualquer outra. Com 5, o ciclo é um torneio regular — cada um
  vence 2 e perde 2. → [02](02-ciclo-canonico.md).
- **Valores canônicos** — **[domínio]** (autoria): são a **premissa**, não variável a
  otimizar. Critério de aceitação escrito e medido: coerentes (validador 23/23), distintos
  entre si, desequilibrados de propósito. Declarados finais. → [04](04-caminhos-e-decisoes.md)
  "As constantes provisórias".
- **`defining_genes`** — **[domínio]**: os genes em que cada arquétipo ocupa um extremo por
  design, espelhando as asserções de ranking do validador. → [03](03-formulacao-do-fitness.md).
- **Ciclo de vantagens** — **[domínio]** (autoria): uma operacionalização entre várias
  defensáveis, com justificativa FGC por aresta; nunca no fitness. → [02](02-ciclo-canonico.md).

## 3. Fitness

- **Dois termos, identidade e equilíbrio** — **[coerência]** com a pergunta de pesquisa (é
  pergunta de trade-off) e com a linha premissa/resposta. → [03](03-formulacao-do-fitness.md).
- **`LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1,0`** — **[medido]**. Só a razão importa; o sweep de λ
  mostrou 1,0 como o joelho da curva (dominance plano até ali, explosão depois). →
  [04](04-caminhos-e-decisoes.md) "O sweep de λ".
- **Drift normalizado pelo range do bound** — **[medido]**: é o que faz a ordenação por drift
  concordar com a do validador. → [04](04-caminhos-e-decisoes.md) "A régua de identidade".
- **`DRIFT_DEFINING_WEIGHT = 3,0`** — **[medido]**: alarga a margem entre indivíduos de
  identidade diferente (gap 0,017 → 0,043); o ganho satura acima, e pesos altos tornariam os
  genes não-definidores quase gratuitos. → idem.
- **Pesos comportamentais reescalados antes do drift** — **[coerência] + [medido]**: só a razão
  entre eles afeta o combate; sem a reescala, 7,5% do drift médio era cobrança por diferença
  invisível. → [04](04-caminhos-e-decisoes.md) "O drift deixou de cobrar pela escala dos pesos".
- **RMS, não média** (nos dois termos) — **[coerência]**: extremos pesam mais, então o AG não
  esconde um boneco dominante ou um gene muito deslocado atrás de uma média. → [03](03-formulacao-do-fitness.md).
- **Equilíbrio = WR global (C2), não WR por par** — **[coerência] + [medido]**: o ótimo "todo par
  a 50%" é incompatível com o ciclo por construção; e a decisividade sozinha foi falsificada
  como proxy de WR. → [04](04-caminhos-e-decisoes.md) "A reformulação do objetivo".
- **Pesos 1,0 / 0,5 / 0,5 dos três termos** — **[medido]**: sem os secundários, 10/10 pares
  viram counter duro; a repartição 0,5/0,5 não se distingue das alternativas a n = 5 e ficou.
  → [04](04-caminhos-e-decisoes.md) "Os pesos do dominance".
- **`MATCHUP_WR_CAP = 0,15`** — **[domínio] + [medido]**: ponto médio entre 6-4 (vantagem
  saudável) e 7-3 (counter) na grade da FGC, onde o ruído binomial menos erra (10,6% de
  falso alarme num 6-4, 90,9% de captura num 7-3). → [04](04-caminhos-e-decisoes.md) "As constantes provisórias".
- **`MATCHUP_THRESHOLD = 0,20`** (teto da decisividade) — **[coerência] + [projeto]**. Numa
  vitória por KO, `|score − 0,5|` é metade da fração de HP do vencedor, então `D > 0,20`
  significa que o vencedor fecha, em média, com mais de 40% de HP — o limiar declarado de
  "massacre". O valor não foi varrido; foi verificado como ativo (dispara no canônico e nos
  aleatórios, 57/180 pares acima dele). → [04](04-caminhos-e-decisoes.md) "As constantes provisórias".
- **`MATCHUP_FLOOR = 0,02`** — **[medido]**: base da faixa dos espelhos, abaixo de todo par de
  personagens distintos; é guarda de degenerescência, não de qualidade. → [04](04-caminhos-e-decisoes.md)
  "O piso de decisividade".
- **Cego à direção** (`|WR − 0,5|`) — **[coerência]** com a não-circularidade. → [03](03-formulacao-do-fitness.md).

## 4. Algoritmo genético

- **Orçamento: população 300, 150 gerações** — **[projeto]**, com uma verificação: nas 20
  sementes da bateria a convergência sai entre as gerações 18 e 75, então 150 deixa o dobro
  de folga sobre a mais tardia. A população não foi variada. O orçamento importa para a
  comparação entre algoritmos — a ordem AG × NSGA-II inverte a pop 120 —, e por isso toda
  comparação de qualidade usa o de produção. → [`10-known-issues`](../reference/10-known-issues.md) §2.
- **Mutação: 5% por gene, σ de 10% do range (atributos) e 2,5% (pesos)** — **[projeto]**. Na
  média, ~2,75 dos 55 genes mudam por filho. O σ dos pesos é 4× menor por inércia deliberada
  (atributos = capacidade, pesos = estratégia). Nenhum dos três foi varrido; o σ dos atributos
  é também o passo usado na análise de sensibilidade, que mede se **um passo típico de
  mutação** move a WR.
- **Crossover por bloco de personagem** — **[coerência]**: preserva a coerência interna entre
  atributos e pesos de um arquétipo. Custo declarado: a recombinação dentro de um personagem
  depende só da mutação. → [`10-known-issues`](../reference/10-known-issues.md) §2.
- **Torneio 3, elitismo 10%** — **[medido]**: nenhum dos 7 braços do sweep os supera;
  "testados, nada os supera", não "ótimos". → [04](04-caminhos-e-decisoes.md) "O elitismo e o torneio".
- **Seed canônico no AG escalar, população aleatória no NSGA-II** — **[medido]**. No NSGA-II o
  canônico é imortal no rank 0 (drift 0 é alcançável) e comia metade da fronteira; no
  escalar ele ajuda. → [04](04-caminhos-e-decisoes.md) "A população inicial do NSGA-II".
- **Orçamento fixo nos dois algoritmos** — **[coerência]**: o NSGA-II não pode parar pelo
  critério do escalar, e parar o escalar cedo confundiria "melhor" com "usou menos
  orçamento". → [04](04-caminhos-e-decisoes.md) "O critério de parada".
- **Convergência = `roster_balanced` duas vezes, a segunda num stream inédito** —
  **[medido]**: o gate antigo era inalcançável por construção, e confirmar no stream do
  treino não confirmava nada. → idem.
- **`GLOBAL_CONVERGENCE_THRESHOLD = 0,10`** (WR global em [40%, 60%]) — **[projeto]**, com
  correspondência de domínio: 0,10 é, na média contra o roster, o 6-4 que a grade da FGC trata
  como vantagem saudável. Não foi varrido. É também a banda "boneco equilibrado" do reporting.
- **`STAGNATION_LIMIT = 30`** — **[projeto]**, de efeito só descritivo: 20% do orçamento sem
  melhoria > 0,001 registra `stagnated_at`, que não para nada — e que a rotação do stream
  torna pouco confiável.

## 5. NSGA-II

- **Por que NSGA-II** — **[domínio]**: é o algoritmo multiobjetivo de referência para 2–3
  objetivos (Deb 2002), elitista, sem pesos a calibrar, com o crowding para espalhar a
  fronteira — e a pergunta da tese é de trade-off, que uma fronteira de Pareto mostra
  inteira. Alternativas (SPEA2, MOEA/D) não foram avaliadas; declarar.
- **Representantes**: `best_dominance` e `best_drift` (os extremos), `knee_point` (maior
  distância à reta entre os extremos), `ideal_point` (menor norma L2) e `scalar_optimum`
  (mínimo da soma que o AG escalar otimiza — o comparável honesto dele) — **[coerência]**.
  → [`06-nsga2`](../reference/06-nsga2.md).
- **Ponto de referência do hipervolume (2,0; 1,0)** — **[coerência]**: os piores valores
  possíveis dos dois objetivos, fixo para que o HV seja comparável entre execuções.

## 6. Protocolo experimental

- **`SIMS_PER_MATCHUP = 150`** — **[medido]**. O desvio binomial de um par a 150 lutas é
  ±4,1%, folgado contra o cap de 15%. O que degradava o resultado fora do laço não era a
  precisão da medida, e sim o protocolo (uma realização do RNG para a busca inteira): dobrar
  as lutas reduziria o ruído só por √2, custaria 2× e deixaria a causa intacta; a rotação do
  stream resolveu a causa. → [04](04-caminhos-e-decisoes.md) "O stream de avaliação".
- **Rotação do stream por geração** — **[medido]**: razão dentro/fora do laço 4,14 → 2,20 em
  5/5 sementes. → idem.
- **CRN com uma semente por luta** — **[medido]**, ganho pequeno: pares sem o personagem
  alterado saem idênticos, mas o sinal de seleção melhora só 1,0–1,3×; mantido por decisão
  do autor. → [04](04-caminhos-e-decisoes.md) "O CRN passou a semear cada luta".
- **200 lutas na confirmação e na reavaliação do `multi_run`; 500 na validação externa** —
  **[projeto]**, com a razão escrita: mais lutas que o treino onde se **mede** em vez de
  **selecionar** — ±3,5% por par a 200, ±2,2% a 500.
- **10 condições na validação externa** — **[projeto]**: 100 oportunidades par × condição de
  falhar, o que torna o veredito binário conservador; a contagem por par distingue o
  sistemático do esporádico. → [04](04-caminhos-e-decisoes.md) "O veredito da validação externa".
- **Famílias de sementes separadas** (treino 42+ → streams 42 000+, validação 9999, externa
  10 000+, confirmação +100 000) — **[coerência]**: nenhuma avaliação reusa o stream de outra.
- **Uma semente de validação comum a todas as execuções** (9999) — **[coerência]**: as 20
  execuções são reavaliadas sob os mesmos sorteios, então a diferença entre elas reflete o
  indivíduo evoluído, não a avaliação.
- **n = 20 sementes** — **[medido]**: o menor n com poder ≥ 80% para um efeito grande (44,4% a
  n = 10). → [04](04-caminhos-e-decisoes.md) "As constantes provisórias".
- **Mann-Whitney U + Â₁₂ + Holm, família de 3** — **[domínio]** (Derrac et al. 2011; Arcuri &
  Briand 2011; Vargha & Delaney 2000; Holm 1979): não-paramétrico, tamanho de efeito ao lado do
  p, e a família montada pela variância da amostra conjunta, critério declarável antes do
  teste. → [`12-statistical-testing`](../reference/12-statistical-testing.md).
- **O NSGA-II entra no teste pelo `best_dominance`** — **[projeto]**, sem registro de porquê. A
  leitura que o desenho permite: é o ponto mais equilibrado de cada fronteira, logo o melhor
  caso do NSGA-II em `dominance` e o pior em drift. O AG vencer em `dominance` contra ele, e o
  NSGA-II vencer em drift mesmo nele, são por isso resultados fortes nas duas direções. A
  comparação contra o `scalar_optimum`, o comparável do escalar, sai da mesma bateria: o
  `multi_run` grava e reavalia os cinco representantes de cada semente. Resultado pendente
  da próxima bateria. → [04](04-caminhos-e-decisoes.md) "Os cinco representantes".
- **Sweeps em orçamento reduzido (pop 120 × 60, 5 sementes)** — **[medido]** como limite: ordenam
  configurações, não declaram vencedor entre algoritmos (há contraexemplo medido), e a n = 5
  diferenças pequenas não se separam do ruído. → [`10-known-issues`](../reference/10-known-issues.md) §2.

## 7. Medição

- **Validador de 23 asserções de ranking** (13 estruturais entre personagens, 5 dentro do
  personagem, 5 comportamentais) — **[coerência]**: identidade, operacionalmente, é ranking
  (quem é o de maior alcance), e distância euclidiana é cega a ranking. → [03](03-formulacao-do-fitness.md).
- **Modelos nulos: 5 espelhos + 30 aleatórios** — **[coerência]**: o espelho é a solução
  trivial do equilíbrio, o aleatório o chão absoluto; 30 dá resolução p < 0,03. →
  [04](04-caminhos-e-decisoes.md) "Os modelos nulos".
- **Tríades circulares no lugar das arestas do ciclo** — **[medido]**: acertar o ciclo autoral é
  loteria de 1/24; a não-transitividade é o que dispensa autoria. → idem.
- **Sensibilidade: ±1σ de mutação, 200 lutas, piso medido em 3 repetições** — **[coerência]** +
  **[projeto]**: o σ é o passo de mutação (a pergunta é se o AG enxerga um passo típico); o piso
  é medido sob hipótese nula, na mesma grandeza que a tabela classifica; as contagens são de
  projeto (600 lutas e 12 repetições dão um piso mais fino, usado para decidir o `knockback`).
  → [05](05-validacao-metodologica.md).
