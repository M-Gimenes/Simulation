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
  alcance e knockback, e o `knockback` tinha derivada negativa. → [04](04-design-decisions.md)
  "A reforma do combate"; [`11-combat-review`](../reference/11-combat-review.md).
- **Intenção sorteada proporcional aos pesos** (soft-policy), única fonte de sorte —
  **[medido]**. Dá gradiente contínuo aos pesos; a variância de dano e a ação aleatória
  uniforme foram removidas porque afogavam o sinal das mutações. → [04](04-design-decisions.md)
  "Estocasticidade do combate".
- **`ACTION_PERSISTENCE_SUBTICKS = 5`** — **[coerência] + [medido]**. 5 = 1 tick = o período
  do atacante mais rápido (`attack_cooldown = 1`), então quem sorteia GUARDA perde exatamente
  uma janela de ataque; a 10, perdia duas, e a razão sinal/ruído era pior em 8/8 genes. A
  coerência só passou a valer em 2026-09-18: até ali o período real era 6 sub-ticks. →
  [04](04-design-decisions.md) "A persistência da intenção" e "Os timers passaram a carregar o resto".
- **`TICK_SCALE = 5`** — **[coerência]**. Resolução sub-tick de movimento e timers. Com o
  resto acumulado, cooldown e stun agem de forma contínua em média em qualquer resolução;
  o valor ancora a persistência (1 tick = 5 sub-ticks = o período mínimo). →
  [04](04-design-decisions.md) "A persistência da intenção".
- **Timers com resto acumulado** (difusão de erro no período do cooldown e nos sub-ticks de
  stun) — **[medido]**. Sem ele o período era `round(5c) + 1` e o stun `ceil(stun_t)`: com
  cooldown 1, o stun tinha 4 efeitos em [0, 0,6], e o do Rushdown evoluído dava 5 WR
  distintas em 31 valores; com ele, 27 em 31, e período e stun exatos em média, sem
  segunda fonte de acaso. → [04](04-design-decisions.md) "Os timers passaram a carregar o resto".
- **Regra do impasse** (avanço imposto só quando ninguém alcança ninguém) — **[medido]**. Sem
  ela, Zoner × Turtle dava 100% de timeout; com ela, 0% nos 10 pares canônicos, sem tocar no
  kite. → [04](04-design-decisions.md) "A reforma do combate".
- **Colisão** — **[medido]**. Sem ela os corpos se cruzavam 134× por luta, anulando o alcance
  no clinch. → idem.
- **Empate como terceiro desfecho** — **[medido]**. Sem ele o desempate caía sempre para o
  lado A (índice menor): 54,90% no espelho do Rushdown. → idem.
- **`stun` como fração do cooldown, em [0, 0,6]** — **[coerência]**. O teto < 1 garante
  stun < cooldown (sempre há janela livre, sem perma-lockdown). → [04](04-design-decisions.md)
  "Calibração das mecânicas"; a continuidade do gene vem do resto acumulado (acima).
- **`DEFEND_DAMAGE_REDUCTION = 0,6`** (guarda reduz 40%) — **[projeto]**. Ajustado à mão
  durante o desenvolvimento (era 0,5), sem medição registrada. O que o modelo exige dele é
  qualitativo: guardar tem valor (reduz dano) e custo (abre mão do golpe, e o agarrão o
  pune). O ponto neutro do agarrão (0,4) deriva dele.
- **`grab_power` ∈ [0, 1], somado ao multiplicador contra quem guarda** — **[coerência]**. O
  intervalo vai de "guarda plena" (0) a "guarda punida" (1,6×); o ponto neutro 0,4 anula a
  guarda. Só o Grappler canônico (0,9) passa dele. → [04](04-design-decisions.md) "O agarrão".
- **Sem `defense` nem `recovery`** — **[medido]**. `recovery` era evolutivamente neutro (drifava
  para o piso); os dois adicionavam dimensões sem ganho de identidade. → [04](04-design-decisions.md)
  "Calibração das mecânicas"; [07](07-findings-and-limitations.md).
- **Campo 100, distância inicial 50** — **[coerência] + [projeto]**. A exigência é que
  todo alcance (≤ 20) seja menor que a distância inicial, para ninguém atacar no primeiro
  tick; a escala em si é de projeto. Os dois não foram calibrados — mas o equilíbrio
  evoluído é testado sob os dois perturbados (campo 80/120, distância 40/60) na validação
  externa, então a dependência do resultado em relação a eles é medida, não suposta.
- **`MAX_TICKS` = 500 ticks (2500 sub-ticks)** — **[projeto]**, de efeito mínimo: é uma
  trava de segurança. Com a regra do impasse, 100% das lutas medidas (70 pares, rosters
  aleatórios inclusive) terminam em KO, então o limite não decidiu nenhuma delas.

**Bounds dos genes** ([`07-configuration`](../reference/07-configuration.md)):
- HP 250–450 — **[projeto]**, apertado para eliminar o "tanque absurdo" que o AG explorava;
  comporta os canônicos (Turtle no teto). → [04](04-design-decisions.md) "Calibração das mecânicas".
- `knockback` ≤ 3 — **[projeto]**: teto acima do Zoner canônico (2), baixado de 5 para
  fechar o zoning trivial por expulsão de alcance. → idem.
- `range` 5–20 — **[coerência]** com a distância inicial (acima).
- `damage` 15–30, `speed` 1–5, `attack_cooldown` 1–5, pesos 0–1 — **[projeto]**: comportam os
  canônicos com folga dos dois lados (exceto os 5 genes canônicos colados no bound,
  declarados em [04](04-design-decisions.md) "As constantes provisórias").

## 2. Arquétipos

- **Cinco arquétipos** — **[domínio]** (autoria): categorias clássicas de FGC, numa escolha
  de operacionalização como qualquer outra. Com 5, o ciclo é um torneio regular — cada um
  vence 2 e perde 2. → [02](02-canonical-cycle.md).
- **Valores canônicos** — **[domínio]** (autoria): são a **premissa**, não variável a
  otimizar. Critério de aceitação escrito e medido: coerentes (validador 23/23), distintos
  entre si, desequilibrados de propósito. Declarados finais. → [04](04-design-decisions.md)
  "As constantes provisórias".
- **`defining_genes`** — **[domínio]**: os genes em que cada arquétipo ocupa um extremo por
  design, espelhando as asserções de ranking do validador. → [03](03-fitness-formulation.md).
- **Ciclo de vantagens** — **[domínio]** (autoria): uma operacionalização entre várias
  defensáveis, com justificativa FGC por aresta; nunca no fitness. → [02](02-canonical-cycle.md).

## 3. Fitness

- **Dois termos, identidade e equilíbrio** — **[coerência]** com a pergunta de pesquisa (é
  pergunta de trade-off) e com a linha premissa/resposta. → [03](03-fitness-formulation.md).
- **`LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1,0`** — **[medido]**. Só a razão importa; o sweep de λ
  mostrou 1,0 como o joelho da curva (dominance plano até ali, explosão depois). Re-rodado
  sobre o motor atual (2026-09-23), λ = 1,0 deixou de empatar com λ = 0,25 e 0,5 e passou a
  **dominá-los**: mesmo dominance, drift 0,10–0,13 melhor, τ dez vezes maior. →
  [04](04-design-decisions.md) "O sweep de λ" e "λ = 1,0 deixou de empatar com os λ menores".
- **Drift normalizado pelo range do bound** — **[medido]**: é o que faz a ordenação por drift
  concordar com a do validador. → [04](04-design-decisions.md) "A régua de identidade".
- **`DRIFT_DEFINING_WEIGHT = 3,0`** — **[medido]**: alarga a margem entre indivíduos de
  identidade diferente (gap 0,017 → 0,043); o ganho satura acima, e pesos altos tornariam os
  genes não-definidores quase gratuitos. → idem.
- **Pesos comportamentais reescalados antes do drift** — **[coerência] + [medido]**: só a razão
  entre eles afeta o combate; sem a reescala, 7,5% do drift médio era cobrança por diferença
  invisível. → [04](04-design-decisions.md) "O drift deixou de cobrar pela escala dos pesos".
- **RMS, não média** (nos dois termos) — **[coerência]**: extremos pesam mais, então o AG não
  esconde um boneco dominante ou um gene muito deslocado atrás de uma média. → [03](03-fitness-formulation.md).
- **Equilíbrio = WR global (C2), não WR por par** — **[coerência] + [medido]**: o ótimo "todo par
  a 50%" é incompatível com o ciclo por construção; e a decisividade sozinha foi falsificada
  como proxy de WR. → [04](04-design-decisions.md) "A reformulação do objetivo".
- **Pesos 1,0 / 0,5 / 0,5 dos três termos** — **[medido]**: sem os secundários, 8,8 dos 10
  pares viram counter duro (2026-09-21; eram 10/10 no motor anterior), com o melhor
  `global_term` de todos os braços; a repartição 0,5/0,5 não se distingue das alternativas a
  n = 5 e ficou — as que sobem o peso do cap pagam em drift e em metade da concordância de
  ranking. → [04](04-design-decisions.md) "Os pesos do dominance" e "Os pesos do dominance:
  a falsificação se manteve".
- **`MATCHUP_WR_CAP = 0,15`** — **[domínio] + [medido]**: ponto médio entre 6-4 (vantagem
  saudável) e 7-3 (counter) na grade da FGC, onde o ruído binomial menos erra (10,6% de
  falso alarme num 6-4, 90,9% de captura num 7-3). → [04](04-design-decisions.md) "As constantes provisórias".
- **`MATCHUP_THRESHOLD = 0,20`** (teto da decisividade) — **[coerência] + [projeto]**. Numa
  vitória por KO, `|score − 0,5|` é metade da fração de HP do vencedor, então `D > 0,20`
  significa que o vencedor fecha, em média, com mais de 40% de HP — o limiar declarado de
  "massacre". O valor não foi varrido; foi verificado como ativo (dispara no canônico e nos
  aleatórios, 57/180 pares acima dele). → [04](04-design-decisions.md) "As constantes provisórias".
- **`MATCHUP_FLOOR = 0,02`** — **[medido]**: acima do roster degenerado (D ≤ 0,008, 0% de KO) e
  abaixo de todo par de personagens distintos; é guarda de degenerescência, não de qualidade.
  Dos cinco espelhos, pega só o do Zoner — a defesa contra a solução trivial é o drift, não
  o piso. → [04](04-design-decisions.md) "O piso de decisividade" e "O piso de decisividade:
  mantido, com a justificativa corrigida".
- **Cego à direção** (`|WR − 0,5|`) — **[coerência]** com a não-circularidade. → [03](03-fitness-formulation.md).

## 4. Algoritmo genético

- **Orçamento: população 300, 150 gerações** — **[projeto]**, com uma verificação: nas 20
  sementes da bateria a convergência sai entre as gerações 18 e 75, então 150 deixa o dobro
  de folga sobre a mais tardia. A população não foi variada. O orçamento importa para a
  comparação entre algoritmos — a ordem AG × NSGA-II inverte a pop 120 —, e por isso toda
  comparação de qualidade usa o de produção. → [`10-known-issues`](../reference/10-known-issues.md) §2.
- **Mutação: 5% por gene, σ de 10% do range (atributos) e 2,5% (pesos)** — **[projeto]**. Na
  média, ~2,75 dos 55 genes mudam por filho. O σ dos pesos é 4× menor por inércia deliberada
  (atributos = capacidade, pesos = estratégia). Nenhum dos três foi varrido; o σ de cada gene
  é também o passo usado na análise de sensibilidade, que mede se **um passo típico de
  mutação** move a WR. Custo medido dessa inércia (bateria de 2026-09-21): a esse passo os
  três pesos ocupam o fundo do ranking — `w_defend` 2,9% e `w_aggressiveness` 3,0% abaixo
  do piso de 3,5%, `w_retreat` 4,8% no limiar —, ou seja, o equilíbrio quase não dá
  gradiente à política. →
  [04](04-design-decisions.md) "A sensibilidade passou a cobrir os pesos".
- **Crossover por bloco de personagem** — **[coerência]**: preserva a coerência interna entre
  atributos e pesos de um arquétipo. Custo declarado: a recombinação dentro de um personagem
  depende só da mutação. → [`10-known-issues`](../reference/10-known-issues.md) §2.
- **Torneio 3, elitismo 10%** — **[medido]**: nenhum dos 7 braços do sweep os **domina**.
  Sobre o motor atual (2026-09-21) o default deixou de ter o menor `cap_term` e o menor
  número de counters; o que ele tem é o melhor drift (0,2448) e a melhor concordância de
  ranking (τ = 0,415) dos oito, e quem o supera em counters paga nos dois. "Testados, nada
  os domina", não "ótimos". → [04](04-design-decisions.md) "O elitismo e o torneio" e
  "Elitismo 10% / torneio 3: mantidos, por outra razão".
- **Seed canônico no AG escalar (`GA_CANONICAL_SEED`), população aleatória no NSGA-II** —
  **[medido]**. No NSGA-II o canônico é imortal no rank 0 (drift 0 é alcançável) e comia
  metade da fronteira; no escalar ele ajuda. Como a assimetria confunde algoritmo com
  inicialização, o AG sem semente é um braço de controle da bateria. →
  [04](04-design-decisions.md) "A população inicial do NSGA-II" e "Os controles".
- **Orçamento fixo nos dois algoritmos** — **[coerência]**: o NSGA-II não pode parar pelo
  critério do escalar, e parar o escalar cedo confundiria "melhor" com "usou menos
  orçamento". → [04](04-design-decisions.md) "O critério de parada".
- **Convergência = `roster_balanced` duas vezes, a segunda num stream inédito** —
  **[medido]**: o gate antigo era inalcançável por construção, e confirmar no stream do
  treino não confirmava nada. → idem.
- **`GLOBAL_CONVERGENCE_THRESHOLD = 0,10`** (WR global em [40%, 60%]) — **[projeto]**, com
  correspondência de domínio: 0,10 é, na média contra o roster, o 6-4 que a grade da FGC trata
  como vantagem saudável. Não foi varrido. É também a banda "boneco equilibrado" do reporting.
- **Sem evento de estagnação** — **[coerência]**: com o stream rotacionando, o "melhor fitness
  histórico" é o máximo de valores ruidosos, e o evento mediria a catraca do ruído. O eixo
  de velocidade é só `converged_at`. → [04](04-design-decisions.md) "O `stagnated_at` saiu".

## 5. NSGA-II

- **Por que NSGA-II** — **[domínio]**: é o algoritmo multiobjetivo de referência para 2–3
  objetivos (Deb 2002), elitista, sem pesos a calibrar, com o crowding para espalhar a
  fronteira — e a pergunta da tese é de trade-off, que uma fronteira de Pareto mostra
  inteira. Alternativas (SPEA2, MOEA/D) não foram avaliadas; declarar.
- **Representantes**: `best_dominance` e `best_drift` (os extremos), `knee_point` (maior
  distância à reta entre os extremos) e `ideal_point` (mais próximo do ponto utópico), os
  dois com os objetivos normalizados pela amplitude da fronteira, e `scalar_optimum`
  (mínimo da soma que o AG escalar otimiza — o comparável honesto dele) — **[coerência]**.
  Em unidades cruas a escala de um objetivo decidia a geometria: o ideal mudou em 19/20
  fronteiras com a normalização. → [`06-nsga2`](../reference/06-nsga2.md); [04](04-design-decisions.md)
  "O joelho e o ideal deixaram de depender da unidade".
- **Ponto de referência do hipervolume (1,3; 0,4)** — **[coerência] + [medido]**: ancorado nos
  modelos nulos — `dominance` do canônico (o equilíbrio de partida) e drift do espelho
  (identidade zero) —, fixo para que o HV seja comparável entre execuções. Com (2,0; 1,0) o
  HV saturava em 90% da área (CV 2,0%); com este, 76% (CV 2,9% — 0,3954 ± 0,0114 na bateria
  de 2026-09-21). → [04](04-design-decisions.md)
  "O hipervolume ganhou uma referência com significado".

## 6. Protocolo experimental

- **`SIMS_PER_MATCHUP = 150`** — **[medido]**. O desvio binomial de um par a 150 lutas é
  ±4,1%, folgado contra o cap de 15%. O que degradava o resultado fora do laço não era a
  precisão da medida, e sim o protocolo (uma realização do RNG para a busca inteira): dobrar
  as lutas reduziria o ruído só por √2, custaria 2× e deixaria a causa intacta; a rotação do
  stream resolveu a causa. → [04](04-design-decisions.md) "O stream de avaliação".
- **Rotação do stream por geração** — **[medido]**: razão dentro/fora do laço 4,14 → 2,20 em
  5/5 sementes. → idem.
- **CRN com uma semente por luta** — **[medido]**, ganho pequeno: pares sem o personagem
  alterado saem idênticos, mas o sinal de seleção melhora só 1,0–1,3×; mantido por decisão
  do autor. → [04](04-design-decisions.md) "O CRN passou a semear cada luta".
- **200 lutas na confirmação e na reavaliação do `multi_run`; 10 × 500 na validação externa**
  — **[projeto]**, com a razão escrita: mais lutas que o treino onde se **mede** em vez de
  **selecionar** — ±3,5% por par a 200; na validação externa as 10 sementes são somadas
  numa amostra de 5000 lutas por par (IC de ±1,4%).
- **`MULTI_RUN_SIMS` (1000) não é `SIMS_CONVERGENCE_CHECK` (200)** —
  **[coerência]**. A confirmação roda *dentro* do laço, a cada disparo do gate; a
  reavaliação, uma vez por execução, sobre um indivíduo só. Custos e restrições diferentes,
  então constantes diferentes.
- **A resolução de 200 sims é suficiente para os agregados e insuficiente para ranquear
  rosters** — **[medido]** (2026-09-22). O desvio do `dominance` de um mesmo roster em 30
  streams é 0,015–0,028, da ordem do valor evoluído (~0,04). Nos agregados de n = 20 isso é
  inofensivo: o ruído é simétrico entre braços e a média o dilui. **Numa amostra pequena
  não é** — comparando dois braços em 5 sementes, o veredito a 200 sims inverteu contra a
  reavaliação a 1000 sims em 4 sorteios. Regra de leitura: nenhuma conclusão por semente,
  nem comparação de braço em amostra pequena, a 200. **Subiu para 1000 em 2026-09-23**,
  junto da re-execução que o híbrido exigiu: custa 10.000 lutas por semente contra
  67.500.000 da execução, e a constante entra no carimbo, então só podia acompanhar uma
  bateria nova. **Efeito medido**, com os mesmos indivíduos: identidade inalterada,
  `dominance` mediano do AG 0,0399 → 0,0355 e rosters equilibrados 14/20 → 16/20 — a régua
  antiga subestimava o equilíbrio —, e uma afirmação da tese caiu (o controle λ = 0 deixou
  de separar em equilíbrio). → [04](04-design-decisions.md), "`MULTI_RUN_SIMS` saiu de
  `SIMS_CONVERGENCE_CHECK`" e [07](07-findings-and-limitations.md).
- **Validação externa: veredito pelo IC, replicação e regras perturbadas** — **[coerência] +
  [projeto]**. O IC contra a banda não fica mais severo com o número de sementes, como o
  quantificador "em alguma das K" ficava. As perturbações de regra (distância 40/60, campo
  80/120, persistência 4/6, redução da guarda 0,55/0,65) são de projeto: ± uma escala
  razoável, uma constante por vez, dentro do que o modelo sustenta. → [04](04-design-decisions.md)
  "A validação externa separou replicação de robustez".
- **Famílias de sementes separadas** (bateria 42+ → streams 42 000+, sweeps 1000+ → streams
  1 000 000+, validação 9999, externa 10 000+, confirmação +100 000) — **[coerência]**:
  nenhuma avaliação reusa o stream de outra, e a amostra que escolhe uma configuração
  (sweeps) é disjunta da que a avalia (bateria). → [04](04-design-decisions.md) "Os sweeps
  saíram das sementes da bateria".
- **Uma semente de validação comum a todas as execuções** (9999) — **[coerência]**: as 20
  execuções são reavaliadas sob os mesmos sorteios, então a diferença entre elas reflete o
  indivíduo evoluído, não a avaliação.
- **n = 20 sementes** — **[medido]**: o menor n com poder ≥ 80% para um efeito grande (44,4% a
  n = 10). → [04](04-design-decisions.md) "As constantes provisórias".
- **Mann-Whitney U + Â₁₂ + Holm, família de 7** — **[domínio]** (Derrac et al. 2011; Arcuri &
  Briand 2011; Vargha & Delaney 2000; Holm 1979): não-paramétrico, tamanho de efeito ao lado do
  p, e a família — equilíbrio e identidade, as duas metades da pergunta — é a mesma em toda
  comparação, com as métricas degeneradas excluídas pela variância da amostra conjunta:
  critério declarável antes do teste. → [`12-statistical-testing`](../reference/12-statistical-testing.md).
- **O NSGA-II entra no teste pelo `scalar_optimum`, com a relação de Pareto ao lado** —
  **[coerência]**: é o ponto que minimiza a função do próprio escalar, o único comparável a
  ele; o `best_dominance` é o extremo da fronteira e perde em drift por construção, e fica
  como leitura secundária. Decidido antes da bateria, pelo método. A relação de Pareto por
  semente (o ponto do AG contra a fronteira inteira, no mesmo stream) não depende de escolher
  representante. → [04](04-design-decisions.md) "A manchete da comparação passou ao `scalar_optimum`".
- **Controles na bateria: AG com `λ_drift = 0` e AG sem semente canônica** — **[coerência]**:
  os nulos não são otimizados, então vencê-los em drift é garantido por construção; o
  contrafactual da pergunta é equilibrar sem o termo de identidade. E sem semente, a
  comparação AG × NSGA-II deixa de confundir algoritmo com inicialização. Mesma amostra e
  orçamento da bateria. → [04](04-design-decisions.md) "Os controles".
- **Sweeps em orçamento reduzido (pop 120 × 60, 5 sementes)** — **[medido]** como limite: ordenam
  configurações, não declaram vencedor entre algoritmos (há contraexemplo medido), e a n = 5
  diferenças pequenas não se separam do ruído. → [`10-known-issues`](../reference/10-known-issues.md) §2.

## 7. Medição

- **Validador de 23 asserções de ranking** (13 estruturais entre personagens, 5 dentro do
  personagem, 5 comportamentais) — **[coerência]**: identidade, operacionalmente, é ranking
  (quem é o de maior alcance), e distância euclidiana é cega a ranking. Empate conta
  **contra** a asserção, e os pesos são comparados como probabilidade de intenção — sem
  isso, cinco cópias do mesmo personagem passavam em 4/13 da Layer 1, e a escala dos pesos,
  que não age no combate, mudava o veredito. → [03](03-fitness-formulation.md);
  [04](04-design-decisions.md) "O validador parou de dar asserções por empate".
- **Concordância de ranking comportamental (τ de Kendall)** — **[coerência] + [medido]**: a
  régua funcional contínua ao lado dos 5 bits da Layer 3; 0 = acaso (média dos 35 nulos
  −0,039 na bateria de 2026-09-21, e +0,007 no braço de controle sem o termo de drift — o
  acaso por duas vias independentes), 1 = a ordem do canônico. **`IDENTITY_BEHAVIORAL_SIMS = 200`** — **[medido]**: em
  re-teste, a 120 lutas o τ do evoluído variava 0,19–0,28; a 200, 0,23–0,24. →
  [04](04-design-decisions.md) "A identidade funcional ganhou uma régua contínua".
- **Modelos nulos: 5 espelhos + 30 aleatórios** — **[coerência]**: o espelho é a solução
  trivial do equilíbrio, o aleatório o chão absoluto; 30 dá resolução p < 0,03. →
  [04](04-design-decisions.md) "Os modelos nulos".
- **Tríades circulares ao lado das arestas do ciclo** — **[coerência]**: as tríades medem
  estrutura sem depender de autoria, mas só com arestas decididas (a 200 lutas, um espelho
  chega a 4,0 por ruído) e são em boa parte consequência do objetivo — equilíbrio global com
  pares decididos força intransitividade. O ciclo autoral não serve de régua porque o próprio
  canônico só realiza 6/10 dele, não por ser "loteria". → [04](04-design-decisions.md)
  "Leituras corrigidas".
- **Sensibilidade: janela de 2σ de mutação nos 11 genes, 200 lutas, piso em 3 repetições** —
  **[coerência]** + **[projeto]**: o σ é o passo de mutação de cada gene (a pergunta é se o AG
  enxerga um passo típico); a janela desliza para dentro do bound em vez de ser cortada; o piso
  é medido sob hipótese nula, **na mesma estatística** que a tabela classifica (média de 5
  |Δ|); as contagens são de projeto. → [05](05-methodological-validation.md); [04](04-design-decisions.md)
  "A sensibilidade passou a cobrir os pesos".
- **Proveniência com digest do código de medição por artefato e recusa de entrada velha** —
  **[coerência]**: todo número post-hoc sai de código fora do motor; cobrir só o motor deixava
  uma mudança no validador invisível. A lista de módulos é derivada das importações. →
  [04](04-design-decisions.md) "A proveniência passou a recusar entrada velha".
