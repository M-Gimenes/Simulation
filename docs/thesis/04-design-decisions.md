# 04 — Caminhos e decisões de design

**Entra em**: Metodologia (justificativa das escolhas) e Discussão.

> A **trajetória** das decisões — que problema cada mudança resolveu. Não é a
> descrição do estado atual (isso é [`../reference/04-combat-model.md`](../reference/04-combat-model.md) e
> [`../reference/05`](../reference/05-genetic-algorithm.md)); é o **raciocínio** que levou até ele.
> As seções estão em ordem cronológica: quando uma decisão foi revista depois, a seção
> antiga aponta para a que a substituiu.
> Mostrar essa evolução evidencia que o sistema foi refinado para fechar problemas
> concretos, não montado arbitrariamente.

Cada item: **problema → mudança → resultado.**

## Estocasticidade do combate

- **Variância de dano e ação aleatória uniforme, removidas.** Problema: `DAMAGE_VARIANCE`
  (±20%/hit) e `ACTION_EPSILON` (ação uniforme aleatória/tick) eram **ruído operacional**
  — afogavam o sinal das mutações abaixo do piso de ruído binomial, e a ação uniforme
  ignorava os pesos (um Turtle "atacava à toa"). Mudança: removidas; a única fonte de
  estocasticidade passou a ser a **soft-policy** (escolha ponderada pelos pesos).
  Resultado: cada peso ganhou efeito contínuo e mensurável.
- **Princípio destilado:** estocasticidade só onde modela **incerteza estratégica**
  (a escolha do jogador), não ruído de execução.
- **Hesitação reintroduzida e depois removida.** Foi reintroduzida (variância de
  player ponderada pelos pesos, ε pequeno) e mais tarde (2026-06-27) **removida**:
  a revisão mostrou que o combate já tinha ruído de sobra (a soft-policy dispara
  muito) e que o determinismo estava no **desfecho**, não na falta de ruído. Manter
  uma 2ª fonte estocástica só adicionava um hiperparâmetro a calibrar sem retorno
  claro. **Estado atual:** a única fonte de estocasticidade é o **sorteio de
  intenção** (mantido por `ACTION_PERSISTENCE_SUBTICKS`).
- **Modelo de combate simplificado para intenção → execução (2026-06-27).**
  Problema: o modelo tinha 4 prioridades hierárquicas + hesitação, e genes
  (`defense`, `recovery`) cujo efeito era difícil de calibrar. Mudança: cada tick
  vira **(1) sorteio de uma intenção** (`FRENTE/RECUAR/GUARDA`, ponderada pelos
  pesos, quando em range) e **(2) execução** dela; `defense` e `recovery` removidos;
  `stun` virou **fração** do cooldown do atacante. Resultado: menos parâmetros,
  invariantes garantidas por bound (stun < cooldown) e identidade ainda expressa
  pelos pesos. (O "execução da intenção" foi revisto na reforma de 2026-09-10, abaixo: a
  intenção passou a governar só a postura, e o ataque virou regra de resolução.)

## Calibração das mecânicas (fechar exploits do AG)

- **Bounds apertados.** Problema: o AG explorava o espaço para vencer de formas
  degeneradas. Mudança: HP reduzido (eliminou "tanque absurdo"), knockback 5→3
  (zoning trivial por expulsão). Resultado: cada aperto fechou um modo de exploit.
  *(Os bounds de `defense` e `recovery` deixaram de existir quando esses genes foram
  removidos — abaixo.)*
- **`defense` e `recovery` removidos (2026-06-27).** Problema: dois genes cujo efeito
  era difícil de tornar visível à seleção sem platôs de arredondamento (recovery
  drifou pro piso — era evolutivamente neutro), e que adicionavam dimensões ao
  cromossomo sem ganho claro de identidade. Mudança: dano virou **flat** (só DEFEND
  reduz) e o stun bruto é aplicado direto. Resultado: modelo mais enxuto (7
  atributos), sem o gene neutro.
- **Stun: cap explícito → fração do cooldown.** Problema: stun ≈ cooldown gerava
  perma-lockdown (vencer por travar o oponente, não por dano). Solução inicial: um
  `STUN_CAP_MULTIPLIER = 0.6` capando o stun. Mudança final (2026-06-27): representar
  o `stun` **diretamente como fração** do cooldown do atacante (∈ [0, 0.6]) — a
  invariante "stun < cooldown" passa a ser garantida pelo **bound do gene**, sem
  constante de cap. Resultado: sempre há janela livre entre hits, com um parâmetro a
  menos.
- **`TICK_SCALE`.** Problema: timers discretos (cooldown ∈ {1..5}) criavam platôs no
  landscape de fitness. Mudança: resolução sub-tick. Resultado: landscape mais suave.

## Reprodutibilidade (achado de auditoria)

- **Problema:** o combate sorteia com `np.random` **dentro do JIT (Numba)**, cujo RNG é
  independente do `np.random` do Python — então semear no Python (como se fazia) **não
  reproduzia** nada, e o pareamento de seeds da análise de sensibilidade estava
  silenciosamente quebrado. Mudança: `seed_combat()` (`@njit`) + **reset ao seed-base
  (Common Random Numbers)** — toda avaliação reseta o RNG do combate ao mesmo seed-base.
  Resultado: experimentos com `--seed` reprodutíveis, e todo indivíduo avaliado sob o
  mesmo stream → a diferença de fitness reflete genes, não sorteio (paisagem mais lisa).
  *(Uma versão intermediária semeava por hash-dos-genes — reprodutível, mas dava a cada
  indivíduo um stream diferente, anulando o CRN; substituída.)* O CRN foi refinado duas
  vezes depois: o stream passou a rodar por geração ("O stream de avaliação") e a semente
  passou a ser por luta ("O CRN passou a semear cada luta"). Detalhe em
  [05](05-methodological-validation.md) e [`../reference/09`](../reference/09-reproducibility.md).

## A reformulação do objetivo (a decisão maior)

- **Problema:** com combate quase-determinístico, o WR é **bimodal** (0/1). Otimizar WR
  = otimizar um objetivo sem gradiente; além disso, "ganhar 55% sempre com 100% de
  vida" não é uma luta equilibrada — é um coin-flip entre dois blowouts.
- **Caminho A (margem):** trocar o objetivo de WR para **decisividade por-luta numa
  banda** — dá gradiente mesmo no determinismo e recompensa lutas *apertadas* (não
  blowout nem decididas no fio).
- **Caminho B (variância de player):** a hesitação, para que o desfecho deixe de ser
  determinístico.
- **Por que os dois (A habilita B):** a revisão mostrou que o ruído já existente não
  flipa desfechos porque as lutas são blowouts; quando o **A** aproxima as lutas, o
  ruído **passa** a flipar → WR graduado emerge. Então A é a alavanca; B é
  complemento/realismo. Interpretação completa em [03](03-fitness-formulation.md).
- **Correção (A sozinho não bastou — hipótese falsificada):** medindo o `best_dominance`
  do NSGA-II com o objetivo só-decisividade, ele dava `dominance_penalty = 0` e 10/10
  lutas na banda, mas **0/10 matchups equilibrados** (Grappler 92%, Turtle 8%). A
  decisividade é **cega à frequência de vitória** — um lado pode vencer sempre por
  margem fina. A hipótese "luta apertada ⟹ WR ~50%" foi **falsificada**. Mudança: a WR
  voltou como termo **primário** do `dominance_penalty` (`|WR−0.5|/0.5` contínuo), com a
  decisividade rebaixada a regularizador **secundário** (guarda contra blowout-coinflip).
  A objeção original ao WR (bimodal) deixou de valer: o sorteio de intenção o torna
  graduado.
- **Reformulação C2 — WR global em vez de por-matchup (2026-06-27, a correção mais
  recente):** Problema: o primário "WR por-matchup" tem como ótimo *todo par a 50%* —
  equilíbrio **plano**, que por construção é **incompatível com o ciclo de vantagens**
  (um ciclo exige que pares tenham vencedor). O objetivo, portanto, **forçava** a
  quebra do ciclo, e atribuí-la a "mecânicas omitidas" estaria errado para o indivíduo
  balanceado. Observação que originou a correção: a WR sempre quis medir o **global do
  boneco** (50% global é compatível com vencer 2 e perder 2). Mudança: o primário
  virou a **WR global por personagem** (`|WR_global − 0.5|`, RMS sobre os 5), mais um
  **teto de hard-counter** (`MATCHUP_WR_CAP`, mantém arestas como vantagens dentro de
  `[0.35, 0.65]`) e a decisividade inalterada. Resultado: o ciclo passa a ser
  **expressável**; "ele emerge das identidades preservadas?" vira o achado real, e C2
  é robusto ao próprio fracasso (se o plano dominar mesmo com espaço, é achado honesto,
  não artefato). Interpretação em [03](03-fitness-formulation.md) e
  [02](02-canonical-cycle.md). Pesos e cap ficaram provisórios até a agenda de calibração
  ("As constantes provisórias") e o sweep dos pesos ("Os pesos do dominance").

## Pesos do fitness

- **`LAMBDA_DRIFT` 6.0 → 1.0.** Problema: com 6.0, mover-se para equilibrar custava ~6×
  o ganho em dominância — o AG escalar ficava **preso ao canônico** (drift ≈ 0) e
  desbalanceado. Mudança: 1.0, igual ao dominance. Resultado: o AG é livre para usar o
  objetivo reformulado; e fica **simétrico ao NSGA-II** (que não pondera). A escolha só
  deixou de ser por eliminação com o sweep de λ ("O sweep de λ"), que a mediu como o
  joelho da curva.
- **`specialization_penalty` removido.** Problema: media spread *intra*-personagem, não
  diferenciação *entre* arquétipos (cinco builds idênticos passariam) — não fazia o que
  o nome diz, era redundante com o drift, e dava ao escalar um 3º termo que o NSGA-II
  não tem. Mudança: removido. Resultado: o AG escalar otimiza **os mesmos dois eixos do
  NSGA-II**; "os 5 ainda são distintos?" virou métrica **post-hoc** (diferenciação
  par-a-par), não termo forçado — coerente com a não-circularidade do ciclo.

## A reforma do combate (2026-09-10)

Quatro incongruências fechadas de uma vez. Todas mudaram número, e é daqui em diante
que os artefatos do projeto descrevem o motor atual.

- **Recuar era forfeit de dano (M1).** Problema: o ataque era uma *ação escolhida*
  concorrente com a postura, então recuar significava não atacar. Consequência medida: o
  `knockback` tinha derivada **negativa** — empurrar o oponente para longe só piorava — e
  o Zoner perdia 100% independentemente de `range` e `knockback`, ou seja, os dois genes
  que o **definem** eram inúteis. Mudança: **dois canais de ação** — a intenção sorteada
  governa só a *postura* (`FRENTE`/`RECUAR`/`GUARDA`), e o ataque virou **regra de
  resolução**: dispara sempre que o cooldown está pronto, o alvo está em alcance e a
  postura não é `GUARDA`. Resultado: avançar e recuar **ambos acertam**; só a guarda
  abdica do golpe. É isso que torna controle de espaço uma estratégia (zoning = atacar
  mantendo distância) e dá ao `knockback` inclinação positiva.
- **Os corpos se atravessavam (M2).** Problema: sem colisão, os personagens se cruzavam
  **134× por luta**, o que anulava `range` no clinch — um Zoner "preso" simplesmente
  atravessava para o outro lado. Mudança: `_apply_movement` desloca os dois a partir das
  posições do início do sub-tick (simultâneo, ninguém chega "primeiro") e os para no
  ponto de encontro. Resultado: A é sempre o lado esquerdo, o que elimina os casos de
  borda de direção em distância zero, e **encurralamento** passa a existir como
  consequência geométrica — `RECUAR` sem espaço cai para `DEFEND`.
- **O `stun` era categórico (M3).** Problema: o timer era arredondado para inteiro, o que
  deixava o gene com **4 níveis efetivos** para um atacante de `cooldown = 1` — um gene
  contínuo se comportando como categórico. Mudança: timer **contínuo** (float,
  decrementado de 1,0 por sub-tick). Resultado: a amplitude do gene a ±1σ de mutação
  passou de 6,8% para **17,4%**.
- **O empate não existia (D).** Problema: KO duplo ou timeout com HP idêntico caíam
  sempre para o lado A — e no round-robin o lado A é **sempre o arquétipo de índice
  menor**. Era viés sistemático na métrica exata que o fitness otimiza. Medido num
  espelho do Rushdown canônico: **54,90%** para o lado A, com 10,3% de KOs duplos.
  Mudança: `_decide_winner` devolve `-1` no empate, que o round-robin conta como meia
  vitória para cada lado. Resultado: o espelho volta a 50%.
- **A regra do impasse.** Problema colhido junto: com o ataque virando regra de
  resolução, dois personagens passivos recuavam para paredes opostas e o tempo esgotava
  sem um golpe. Mudança: quando `distância > alcance de ambos` — ninguém alcança ninguém
  — `ADVANCE` é **imposto**. Resultado: o impasse se resolve sem tornar a regra
  explorável, porque um personagem **sob ameaça** (o oponente alcança) segue livre para
  recuar; kiting fica intacto.

> O stun contínuo, revisto: o timer float ainda deixava o gene em degraus — ver «Os timers passaram a carregar o resto».

## A régua de identidade (2026-09-16)

O ponto de partida foi uma objeção do próprio autor, levantada no início do projeto e
retomada na auditoria: *"o AG não devia ter influência em preservar identidade, senão a
pergunta central fica ambígua — eu estaria forçando a preservação."*

- **Problema:** a objeção é válida como princípio, mas mirava o alvo errado. O projeto já
  tinha identidade no fitness por decisão explícita, e a não-circularidade estava
  garantida em outro lugar — no ciclo de vantagens, que nunca entrou em penalidade
  nenhuma. O que faltava era **nomear a linha**: o fitness pode codificar a **premissa**
  (o que cada arquétipo é), nunca a **resposta** (quem vence quem; se os dois objetivos
  são compatíveis). O argumento que fecha é empírico: com a penalidade ligada o run
  inteiro, o AG **mesmo assim** trocou identidade por equilíbrio (8/21 no validador) —
  penalidade não
  é restrição, e ter o termo não pré-determinou nada.
- **O defeito real:** os dois medidores de identidade do projeto discordavam. O
  `drift_penalty` dava 0,261 ("preservada") onde o validador dava 8/21 ("destruída"),
  porque distância euclidiana é cega a **ranking** — e o que aconteceu não foi
  homogeneização, foi **troca de papéis**.
- **Mudança:** duas réguas, uma de cada lado da linha. Identidade **estrutural** no
  fitness (drift normalizado pelo range do bound e ponderado pelos genes definidores de
  cada arquétipo); identidade **funcional** post-hoc (Layer 3 comportamental + ciclo),
  que nada no fitness referencia. Contrapartida declarada: as Layers 1-2 do validador
  ficaram **parcialmente endógenas**.
- **Resultado:** a ordenação por drift passou a bater com a do validador, e a margem
  entre indivíduos de identidade diferente dobrou. Medido nos quatro indivíduos de
  referência do diagnóstico, sob o validador de 21 asserções que precedeu o `grab_power`
  (critério: drift ascendente deve acompanhar validador descendente):

  | variante | knee (19/21) | ideal (16/21) | best_dom (11/21) | AG (8/21) | ordem bate? | gap AG−best_dom |
  |---|---|---|---|---|---|---|
  | `x/hi` uniforme (antiga) | 0,0885 | 0,1554 | 0,2709 | 0,2607 | **não** | −0,010 |
  | range, uniforme | 0,1302 | 0,2062 | 0,3245 | 0,3417 | sim | 0,017 |
  | range, ponderada (peso 3,0) | 0,1279 | 0,2054 | 0,3150 | 0,3579 | sim | **0,043** |

  A **normalização** conserta a ordenação; a **ponderação** alarga a margem. O peso
  satura (gap 0,055 em 5,0; 0,073 em 12,0), e pesos altos tornam os genes não-definidores
  quase gratuitos — 3,0 mantém os dois lados com preço. Mas a resposta em
  λ_drift = λ_dom = 1,0 **não mudou** — o AG continua trocando identidade por
  equilíbrio, com as falhas caindo exatamente sobre os genes definidores. Isso é o
  achado, não o bug: é o que empurra a resposta da tese para o **mapa do trade-off**
  (fronteira do NSGA-II) em vez de um ponto único.

> Revisto: a régua funcional ganhou uma medida contínua, e a leitura de identidade foi refeita — ver «A identidade funcional ganhou uma régua contínua».

## O piso de decisividade (2026-09-16)

- **Problema:** `MATCHUP_FLOOR = 0,10` punia lutas *apertadas demais*, empurrando na
  direção oposta ao termo primário — equilibrar aproxima as lutas. Pior, era ele quem
  decidia a comparação AG × NSGA-II: decomposto, o NSGA-II era **melhor no termo
  primário** e perdia no piso. "O AG vence em `dominance_penalty`" estava correto como
  número e errado como leitura.
- **Mudança:** piso para 0,02, virando guarda de **degenerescência**. A premissa original
  ("abaixo do piso é quase-empate, luta que não aconteceu") não vale no motor reformado:
  100% das lutas terminam em KO, então decisividade baixa é KO no fio — a melhor luta
  possível, não um defeito. O valor veio de medição: roster degenerado dá `D ≤ 0,008`,
  espelho puro dá 0,020–0,033, pares reais dão ≥ 0,045.
- **Resultado:** o piso deixou de morder (0/10 pares contra 5/10 antes) e a comparação
  entre algoritmos voltou para o termo primário. Em paralelo, os três termos do dominance
  passaram a ser reportados **separados** nos artefatos — o composto sozinho não
  distingue perder no primário de perder num secundário de metade do peso.

> Revisto: valor mantido, justificativa corrigida — ver «O piso de decisividade: mantido, com a justificativa corrigida».

## O critério de parada do AG (2026-09-16)

- **Problema:** o gate de convergência era `dominance_penalty <= 1e-9`, insatisfazível
  **por construção** — o termo primário é uma RMS sobre contagens discretas, cujo menor
  valor não-nulo é ~0,0015, então `1e-9` significava *exatamente zero*. `converged` era
  sempre `False` e todo o ramo de confirmação era código morto descrito na metodologia.
  Pior: a "reavaliação independente" rodava no **mesmo stream de RNG** do treino, então
  não podia discordar do gate. Medido no indivíduo que convergia:

  | stream | equilibrado? | bonecos em banda | counters duros |
  |---|---|---|---|
  | treino (42) — o que a confirmação usava | **sim** | 5/5 | 0 |
  | 9999 / 10000 / 10001 / 10002 | não | 5/5 | 1–2 |

  O que quebra é sempre o par-a-par, nunca a WR global: o ajuste ao stream se concentra
  ali.
- **Mudança:** o gate virou o próprio critério (`roster_balanced`, agora fonte única da
  definição de equilíbrio do projeto), e a confirmação passou a rodar num stream que o AG
  nunca viu (`seed + CONVERGENCE_SEED_OFFSET`).
- **Resultado:** convergir passou a significar *"o equilíbrio sobrevive a uma amostra que
  o AG não otimizou"*. Em 60 gerações o gate dispara 16× e a confirmação rejeita as 16 —
  o ajuste ao stream, quantificado; em 150 gerações o AG converge de fato. O headline "X%
  das execuções convergiram" cai, mas passa a significar alguma coisa.

## A população inicial do NSGA-II (2026-09-16)

- **Problema:** os dois algoritmos iniciavam com `[canônico] + aleatórios`. No NSGA-II
  isso é patológico, por uma assimetria entre os objetivos: `drift` tem piso 0 **e o piso
  é alcançável** (o canônico *é* a referência), enquanto o de `dominance` não é. Dominar
  o canônico exigiria `drift < 0` — impossível —, então ele é **imortal no rank 0** por
  pior que seja seu equilíbrio, e a vizinhança de drift ~0 herda quase a mesma imunidade.
  Medido: 40 dos 78 pontos da fronteira eram rosters tão desequilibrados quanto o canônico
  intocado, ocupando um terço da população e do esforço reprodutivo; o min `dominance`
  estagnava em 0,2233 e a fronteira nunca alcançava a região onde moram as soluções
  equilibradas.
- **Mudança:** NSGA-II inicia 100% aleatório. O AG escalar **mantém** o seed, porque lá
  ele ajuda: o fitness é um número só, o canônico é ruim nele e some depois de doar genes
  (com seed drift 0,2874, sem 0,3365, mesmo dominance). Assimetria deliberada, declarada.
- **Resultado:** min `dominance` 0,0896 em 60 gerações e 0,0346 em 150, sem nuvem
  (0/49 pontos com `dominance ≥ 1.0`). Com isso o **mapa do trade-off passou a existir**.
  No orçamento de produção (pop 300 × 150, os artefatos da bateria) os dois ficam
  **mutuamente não-dominados**: o escalar domina 0 dos 64 pontos da fronteira, nenhum o
  domina, e a `dominance` dele (0,0153) fica abaixo de toda a faixa dela ([0,0483; 1,1438]).
  Na função que o *escalar* otimiza, quem vence é o escalar — L1 0,2331 contra 0,2487.
  Não é que um domine o outro: cada um alcança uma parte diferente do trade-off.
  > **Nota de revisão (2026-09-22): a segunda frase se manteve, a primeira caiu.** Sobre a
  > bateria (n = 20, não uma semente), os dois seguem mutuamente não-dominados em 18/20 —
  > mas na soma `dominance + drift` a fronteira tem um ponto **melhor** em 20/20 sementes
  > (medianas 0,2658 contra 0,2052). O 0,2331 contra 0,2487 era de um run diagnóstico de
  > uma semente. Ser não-dominado não é ser ótimo em λ = 1/1: o escalar para num extremo
  > do trade-off porque `dominance` é amostrado e `drift` não. Ver
  > [07](07-findings-and-limitations.md) §«O AG escalar não é ótimo na própria função».
- **Ressalva de método que este item produziu:** o run diagnóstico rodou a pop **120**, e
  ali a leitura era a inversa (L1 0,2115 do NSGA-II contra 0,2945 do escalar). A conclusão
  sobre a **inicialização** transfere — é o mecanismo, e ele independe do orçamento; a
  conclusão sobre **qual algoritmo é melhor** não transferiu. Regra adotada: orçamento
  reduzido ordena *configurações*, nunca declara *vencedor* entre algoritmos.
- **Ponto de método associado:** `select_representatives` ganhou `scalar_optimum`, o
  mínimo da soma ponderada que o escalar otimiza. A comparação vinha usando
  `ideal_point`, que minimiza a norma L2 — outro ponto da mesma fronteira.

> Revisto: a assimetria de inicialização ganhou um braço de controle — ver «Os controles: λ_drift = 0 e AG sem semente canônica».

## O agarrão / quebra de guarda (2026-09-16)

- **Problema:** `DEFEND` reduzia 40% do dano e **não tinha custo** — sem chip damage,
  quebra de guarda ou stamina. Três sintomas que o projeto tratava como problemas
  separados eram a mesma lacuna: (i) o eixo de **recurso** sem contrapartida; (ii) a
  **Layer 3 do validador com 4 asserções para 5 arquétipos**, porque sem grab o Grappler
  não tinha comportamento distinto do corpo-a-corpo do Rushdown; (iii) a aresta
  **"Grappler vence Turtle"** do ciclo canônico, cuja justificativa é literalmente *"grab
  é o counter canônico ao bloqueio"*, sem mecanismo no motor. Some-se um quarto, vindo da
  decisão (A): o Grappler tinha um **único** gene definidor.
- **Mudança:** `grab_power` como 8º atributo, ∈ [0, 1], a **fração da guarda quebrada**.
  Contra alvo em `DEFEND` o multiplicador vira `defend_red + grab_power` — soma simples,
  então o teto **inverte** a vantagem de defender em vez de apenas anulá-la.
  Três escolhas de desenho, todas deliberadas: mesmo alcance e mesmo cooldown do ataque
  normal; **efeito nenhum contra quem não defende**; e nunca supera um golpe limpo. Nos
  canônicos o multiplicador contra quem guarda fica em Zoner 0,65× · Turtle 0,75× ·
  Rushdown 0,80× · Combo Master 0,90× · **Grappler 1,50×** — o único acima do ponto neutro
  (0,40 de `grab_power`, 1,00×).
- **Por que essas escolhas:** é o "efeito nenhum contra quem não defende" que faz do
  agarrão um **counter** em vez de um golpe superior — ele é uma leitura condicional, que
  vale contra quem bloqueia e é peso morto contra quem pressiona. E por ser uma
  condicional na *resolução* e não uma ação escolhida, o modelo de dois canais (postura
  escolhida, ataque por regra) fica intacto: nada de `w_grab` ou quarta postura, que
  teriam mexido de uma vez no espaço de política, na degenerescência de escala dos pesos
  e no drift dos pesos.
- **Resultado:** dano por golpe contra alvo em guarda vai de 16,2 (`grab = 0`, ou seja
  0,6×) a **43,2** (`grab = 1`, 1,6×), passando exatamente pelo golpe limpo de 27,0 no
  ponto neutro 0,40; diferença zero contra alvo que não defende. O
  validador canônico vai a **23/23**, com os cinco arquétipos tendo assinatura
  comportamental pela primeira vez. Ressalva honesta sobre o sintoma (iii): a aresta
  Grappler×Turtle sai em 100%, mas já saía antes — o Turtle canônico perde para todos
  (WR global 0%). O que mudou é que agora **existe o mecanismo** para ele vencer por
  mérito; se o ciclo emerge disso é pergunta para a bateria.

## Os modelos nulos: nenhuma métrica do projeto tinha piso (2026-09-16)

Este item entrou na pauta como *"recalibrar os canônicos para o ciclo existir"* e o
diagnóstico saiu **muito maior** que o item.

- **Problema:** todas as métricas de identidade estavam sendo lidas contra o **teto**,
  como se o piso fosse zero. Medido com 13 rosters nulos (5 espelhos + 8 aleatórios): o
  piso de acaso do validador é ~6,8/21 e um roster **aleatório** chegou a **12/21** — as
  asserções de ranking resolvem empate por ordem de índice, então algumas passam por
  acidente. O `drift_penalty` lê ~0,33 num **espelho** (cinco personagens idênticos,
  identidade zero por construção) e ~0,41 num aleatório: só **0,04** separam "identidade
  cuidadosamente preservada" de aniquilação total. E o ciclo canônico tem piso **5/10**,
  porque cada aresta é cara-ou-coroa. *(O piso 5/10 segue válido — os nulos aleatórios têm
  arestas decididas. O que não era válido era medir o ALVO na mesma resolução; ver «O ciclo
  saiu do `baselines`», 2026-09-22.)*
- **Por que isso importa:** ler `8/21` como "38% da identidade sobreviveu" é o mesmo erro
  que ler 20% numa prova de múltipla escolha de cinco opções como "sabe 20% da matéria".
- **Mudança:** `src/experiments/baselines.py` monta canônico + 5 espelhos + N aleatórios e
  reporta cada métrica como `posição = (valor − piso)/(teto − piso)`, com o **pior nulo**
  e um **p-valor empírico** — o piso é uma *distribuição*, não um ponto.
- **Resultado, e duas consequências que entram na tese.** Primeira: o **espelho é a
  solução trivial** de equilíbrio (equilíbrio perfeito, identidade zero) e é a resposta
  numérica à objeção óbvia *"por que não deixar os cinco iguais?"* — medido, o roster
  evoluído alcança 99% do equilíbrio do espelho ficando ~30% acima do piso de identidade.
  Segunda, e mais forte: **o ciclo autoral não pode ser resultado.** Ele é um torneio
  *regular* (cada arquétipo vence exatamente 2), e existem **24** torneios regulares
  rotulados em 5 vértices — acertar o rótulo específico é loteria de 1/24 enquanto o
  acaso já dá 5/10. *(O argumento do 1/24 foi depois corrigido neste mesmo arquivo: com
  arestas decididas, 10/10 teria p = 1/1024, informativo. O que desqualifica o ciclo como
  régua é o canônico realizar só 6/10.)* O que **é** resultado, e não depende de autoria, é a
  **não-transitividade em si**: equilíbrio global e pedra-papel-tesoura são a mesma
  estrutura, porque um roster estritamente transitivo teria WRs 100/75/50/25/0,
  incompatível com todos perto de 50%. Medida por `circular_triads` (Kendall & Babington
  Smith 1940), escala 0 (ordem estrita) · 2,5 (acaso) · 5 (máximo = equilíbrio perfeito).
  Coberto por teste: o ciclo **invertido** dá 0/10 arestas e ainda 5 tríades — a estrutura
  sobrevive à troca de rótulos, que é exatamente por que o rótulo não é o achado.
- **Resolução do p-valor:** a primeira medição (13 nulos) só afirmava p ≈ 0,08; com 35 nulos
  (5 espelhos + 30 aleatórios, o default do tool desde então) um valor que nenhum nulo
  iguala afirma p < 0,03. Com 35 nulos, o roster evoluído passou a superar todos nos três
  eixos de identidade.

> Revisto: o piso do validador estava inflado pelo desempate por índice, e três leituras feitas contra os nulos não se sustentavam — ver «O validador parou de dar asserções por empate» e «Leituras corrigidas».

## A família de testes estatísticos (2026-09-16)

- **Problema:** a comparação AG × NSGA-II aplicava Holm-Bonferroni sobre **4 métricas**,
  e uma delas — "bonecos em banda" — dava **5/5 nas 20 execuções**. Amostra conjunta
  constante: Mann-Whitney é indefinido ali (devolve `nan`, porque a correção de empates
  zera o denominador). Não é um teste que deu "sem diferença"; é a **ausência** de um
  teste. Mas entrava na família como se fosse um, e o multiplicador virava 4 em vez de 3.
  Cada métrica na família **encarece todas as outras**. Havia ainda um defeito silencioso:
  `_holm` ordenava com um `nan` dentro, e como toda comparação com `nan` é falsa, a
  ordenação saía certa por sorte do algoritmo de ordenação.
- **Mudança:** a família passou a ser montada por um critério **objetivo e declarável
  antes do teste** — variância da amostra **conjunta**. É a conjunta de propósito: `ga`
  constante em 5 contra `nsga2` constante em 3 é a diferença mais forte possível, não
  degenerescência. A métrica excluída segue reportada como **descritiva**, e `_holm`
  passou a recusar `nan` com exceção em vez de ordenar por acaso.
- **Por que o critério tinha de ser objetivo:** escolher a família *depois* de ver os
  p-valores é p-hacking, mesmo quando cada corte parece razoável isoladamente. Um
  critério que os dados decidem não tem esse problema.
- **Resultado:** o único achado da bateria — NSGA-II com drift menor, efeito **grande**
  (Â₁₂ = 0,80), p bruto 0,0257 — foi de p_Holm 0,1030 para **0,0772**. **Continua não
  significativo**, e é isso que torna a correção defensável: nem a família mínima
  concebível (2 métricas) o levaria abaixo de α, pois para em 0,0515. Não havia prêmio em
  escolher a família menor. A leitura honesta é *efeito grande, direção consistente, não
  significativo a n = 10* — e o gargalo é poder amostral, não correção. Explicação
  didática do aparato em
  [`../reference/12-statistical-testing.md`](../reference/12-statistical-testing.md).

> Revisto: a família passou a ser a mesma em toda comparação, com as métricas de identidade — ver «A manchete da comparação passou ao `scalar_optimum`».

## O stream de avaliação: CRN para seleção, rotação entre gerações (2026-09-16)

A decisão mais estrutural do bloco de calibração, e a que mais precisa aparecer na
Metodologia — ela muda **como o AG é avaliado**, não o que ele otimiza.

### O que é um stream, e por que o projeto usa um só

O combate tem um único nó aleatório: o **sorteio de intenção**. Mas o gerador é
pseudo-aleatório — uma semente determina toda a sequência de sorteios. Um *stream* é
essa sequência concreta: com a semente 42, a luta Zoner × Rushdown número 37 tem
sempre exatamente as mesmas decisões, na mesma ordem.

Avaliar todos os indivíduos de uma geração sob o **mesmo** stream é a técnica de
**Common Random Numbers**, e é a escolha certa para *seleção*: se cada indivíduo
enfrentasse sorteios diferentes, um poderia parecer melhor só por sorte, e a seleção
ficaria enganada. Com CRN, a diferença de fitness entre dois indivíduos só pode vir
dos **genes** — é dar a mesma prova a todos os candidatos, em vez de uma prova
diferente para cada um.

### O problema: era a mesma prova 150 vezes

- **Problema:** `set_seed_base(seed)` era chamado **uma única vez**, no início da
  execução. Toda avaliação, em **todas as gerações**, resetava o RNG para a mesma
  semente. Não era só "todos fazem a mesma prova" — era **a mesma prova repetida
  MAX_GENERATIONS vezes**, e a população tinha esse orçamento inteiro para decorá-la.
  O AG não precisava achar genes que equilibrassem o jogo; bastava achar genes que
  equilibrassem *aquela sequência de sorteios*. É a diferença entre estudar a matéria
  e decorar o gabarito de uma prova antiga.
- **Evidência de que acontecia:** o melhor indivíduo dava `dominance` medido no stream
  de treino muito melhor que em streams inéditos — razão média **4,14×** sobre 5
  sementes. O equilíbrio reportado era, em boa parte, sobre aquele gabarito.
- **Mudança:** `fitness.generation_seed(base, geração)` define o stream de **cada
  geração**. Dentro da geração, todo mundo continua sob o mesmo stream — **o CRN é
  preservado e a seleção segue justa**. Entre gerações o stream muda, então genes que
  só funcionavam contra uma sequência específica são punidos na geração seguinte.
  O protocolo é o **mesmo nos dois algoritmos**: se só um rotacionasse, a comparação
  AG × NSGA-II confundiria "algoritmo" com "forma de avaliar".
- **Resultado** (A/B com 5 sementes, 60 gerações, medido em 5 streams inéditos):

  | métrica | stream fixo | rotacionado | sementes que melhoram |
  |---|---|---|---|
  | razão dentro/fora do laço | 4,14 | **2,20** | **5/5** (Wilcoxon p = 0,0312) |
  | rosters equilibrados fora (de 5) | 2,6 | **4,8** | **5/5** (Wilcoxon p = 0,0312) |
  | `dominance` fora do laço | 0,0452 | 0,0373 | 3/5 (p = 0,31) |
  | `drift` | 0,2924 | 0,2968 | — (sem custo) |

  As duas métricas que melhoram em 5/5 são justamente a que mede o ajuste ao stream e
  a que corresponde ao *headline* da tese ("o roster está equilibrado?"). A
  **magnitude** do ganho em equilíbrio não está estabelecida (p = 0,31), e isso deve
  ser dito: o que a evidência sustenta é que o resultado passou a **sobreviver a
  streams inéditos**, não que o AG ficou 17% melhor. Bônus não previsto: sob stream
  fixo, 2 das 5 sementes **não convergiram**; sob rotação, 5/5 convergiram — mais
  tarde (19–36 contra 14–26), o que é o esperado de um critério mais exigente.

### O argumento de princípio, que não depende do tamanho do efeito

O projeto **já tinha tomado essa decisão um nível abaixo**: a *confirmação* de
convergência foi movida para um stream independente porque "CRN é certo para seleção e
errado para validação", e na época aceitou-se que isso tornasse a convergência muito
mais rara. A rotação é o mesmo princípio aplicado à busca: se não se pode **validar**
no stream de treino, também não se deveria deixar a busca inteira **fitar** um stream
só. Sem ela, "o AG nunca viu este stream" valia para a confirmação, mas não para a
otimização que produziu o indivíduo confirmado.

### O custo, e por que ele é assimétrico

Rotacionar obriga a reavaliar quem sobreviveu, porque a nota anterior veio de outra
prova. No **AG escalar** são os 30 elites (~1,8× medido). No **NSGA-II** é o dobro: a
ordenação por dominância compara pais e filhos dentro do mesmo conjunto combinado, e
objetivos medidos em streams diferentes **não são comparáveis** — os pais têm de ser
reavaliados junto, 2×pop por geração em vez de pop. Isso está comentado no código
porque é exatamente o tipo de reavaliação que alguém removeria como "redundante",
quebrando a validade da fronteira em silêncio.

### Por que não subir as simulações por par

A alternativa óbvia ao ajuste ao stream era subir `SIMS_PER_MATCHUP`, e ela ficou em 150
porque atacava o sintoma. O desvio binomial de um par a 150 lutas é ±4,1% (±2,9% a 300,
±2,0% a 600) — já folgado contra um cap de 15%. O que degradava o resultado fora do laço
não era a precisão da medida, e sim o protocolo: uma realização do RNG para a busca
inteira. Dobrar as lutas reduziria o ruído só por √2, dobraria o custo e deixaria a causa
intacta; a rotação custa ~1,8× no escalar e remove a causa.

### Consequência colateral a declarar

Sob rotação o fitness flutua entre gerações por troca de stream, então
`best_fitness_ever` é "melhorado" por ruído e o contador de estagnação reseta sozinho:
**`stagnated_at` fica menos confiável**. `converged_at` não sofre, porque o critério de
convergência é o predicado de equilíbrio (`roster_balanced`), não o valor do fitness.

## A persistência da intenção: 10 → 5 sub-ticks (2026-09-16)

- **Problema, em duas frentes que se encontraram.** Coerência: a persistência (10
  sub-ticks) era **maior que o cooldown mínimo** (5 = `attack_cooldown` 1 × `TICK_SCALE`),
  então quem tem cooldown 1 e sorteia GUARDA abria mão de **duas** janelas de ataque, não
  uma — um custo desenhado para uma janela virava dois por acidente de escala. Medição: na
  análise de sensibilidade, `speed` e `stun` ficavam **abaixo do piso de ruído**, ou seja,
  o AG não conseguia enxergar dois genes do modelo.
- **Mudança:** 5 sub-ticks = exatamente **1 tick** (`TICK_SCALE`) = exatamente o cooldown
  mínimo. A semântica fica limpa: a intenção é mantida por um tick.
- **Resultado.** A razão sinal/ruído melhora em **8/8 genes** (medido com 600 sims e piso
  medido em 12 repetições, no indivíduo evoluído):

  | gene | persist = 5 | persist = 10 | ganho |
  |---|---|---|---|
  | `range` | 8,86 | 5,82 | +52% |
  | `attack_cooldown` | 5,80 | 4,22 | +37% |
  | `damage` | 4,97 | 3,59 | +38% |
  | `hp` | 4,43 | 3,55 | +25% |
  | `grab_power` | 2,26 | 1,73 | +30% |
  | **`speed`** | **2,03** | **1,12** | **+81%** |
  | **`stun`** | **1,94** | **1,08** | **+80%** |
  | `knockback` | 0,74 | 0,57 | +30% |

- **Por que melhora tudo, e não só os dois genes visados:** persistência alta paga
  **duas vezes**. Menos decisões independentes por luta significa menos oportunidades de
  o gene se expressar (sinal menor) **e** mais variância no desfecho (piso de ruído
  maior — 3,5% a 5 contra 4,9% a 10). Baixá-la melhora numerador e denominador ao mesmo
  tempo. `knockback` continua abaixo do piso e segue como limitação declarada. (Remedido em
  2026-09-18 no indivíduo atual: no **limiar** do piso, junto com o `speed`, e não abaixo
  dele — ver "O carimbo retroativo por inferência falhou num artefato". Confirmado na
  bateria de 2026-09-21: `knockback` 4,3% e `speed` 3,5% contra um piso de 3,5% — no
  limiar; quem ficou **abaixo** foram `w_defend` 2,9% e `w_aggressiveness` 3,0%.)

- **E o `TICK_SCALE` ficou em 5.** A pergunta junto era se a própria resolução sub-tick
  devia mudar. Não: com o timer de stun contínuo, o único acoplamento que restou com ela é o
  cooldown, quantizado em `round(cd × TICK_SCALE)` — de 5 a 25 sub-ticks —, e é justamente
  o cooldown mínimo de 5 sub-ticks que ancora a persistência nova.

> Revisto: o cooldown mínimo real era 6 sub-ticks, não 5; com o período corrigido o argumento passou a valer — ver «Os timers passaram a carregar o resto».

## O drift deixou de cobrar pela escala dos pesos (2026-09-16)

- **Problema:** a intenção é sorteada **proporcionalmente** a `(w_retreat, w_defend,
  w_aggressiveness)`, então multiplicar os três por `k > 0` não muda **nada** no combate —
  é um grau de liberdade behaviouralmente nulo. Mas o `drift_penalty` media os valores
  **absolutos**, e portanto cobrava identidade por uma diferença que o simulador não
  consegue distinguir. Parte da régua central da tese media ruído.
- **Quanto, exatamente:** o número antes registrado ("55% do drift de pesos no Turtle")
  vinha de uma conta **confundida por escala**, que comparava distância no espaço bruto
  com distância no normalizado. A formulação exata — quanto do drift desaparece ao
  escolher o melhor `k` — dá **7,5%** do drift médio, pior caso Rushdown 15,1%. Os `k`
  ótimos entre 0,58 e 0,70 contam o que acontecia: o AG **inflava a escala dos pesos** e o
  drift cobrava pela inflação.
- **Mudança:** `fitness.drift_genes` — os 8 atributos passam intactos e os 3 pesos são
  comparados **reescalados para a soma canônica**. O `drift_table` consome o mesmo helper:
  ele calculava o total por uma via e a coluna por gene por outra, e as duas passariam a
  discordar nos pesos.
- **Sobre a escolha do representante:** tanto reescalar para a soma canônica quanto usar o
  `k` de mínimos quadrados produzem uma métrica **invariante à escala**, que é o
  requisito; elas apenas escolhem representantes diferentes da mesma classe de
  equivalência. A soma canônica foi preferida por ser explicável em uma frase
  ("normalizar para o mesmo total"). O resíduo entre as duas (0,2413 contra 0,2349) **não
  é desperdício remanescente** — é diferença genuína de forma medida sob outra convenção.
- **Resultado:** `drift_penalty` do indivíduo evoluído vai de 0,2539 para **0,2413**. O
  contrato ficou coberto por teste com três asserções, e a segunda é a que importa:
  escalar os três pesos não muda o drift, **trocar a razão entre eles muda** (a métrica
  não ficou cega aos pesos, que seria o jeito trivial de passar no primeiro teste), e os 8
  atributos passam intactos.

## As constantes provisórias, fechadas com evidência (2026-09-16)

A bateria completa deixou sete constantes rotuladas "provisório". Fechá-las exigiu
separar duas classes, e essa separação é ela própria uma decisão metodológica:

> Constantes que **definem** o que é equilíbrio (o cap, a banda, os pesos do objetivo)
> **não podem** ser escolhidas por desempenho — seria definir "counter duro" pelo que o
> motor produz, a mesma circularidade que mantém o ciclo de vantagens fora do fitness.
> Elas precisam de **âncora externa**. Constantes de **medição e motor** (sims,
> persistência, sementes) podem e devem ser escolhidas por desempenho, porque ali
> "melhor" é bem definido sem tocar na resposta.

- **`MATCHUP_WR_CAP = 0.15` — mantido, com âncora de domínio.** Problema: não havia
  justificativa escrita para 15 pontos percentuais, e o cap decide se uma execução conta
  como "roster equilibrado". Âncora: a grade de matchup da FGC é dita em inteiros —
  5-5, 6-4, 7-3, 8-2, ou seja `|WR − 0,5|` de 0,00 · 0,10 · 0,20 · 0,30 — e o consenso é
  que **6-4 é vantagem saudável** e **7-3 é counter**. Logo o cap deve permitir 0,10 e
  barrar 0,20. O que decide **entre** os candidatos é o ruído de medição: um limiar
  colado num ponto da grade vira cara-ou-coroa. Com σ ≈ 0,040, o cap a 0,10 reprova um
  6-4 legítimo em **50%** das vezes e o cap a 0,20 deixa passar **50%** dos 7-3; a 0,15 —
  ponto médio da única lacuna que importa — são 10,6% e 90,9%.
- **`DOMINANCE_DECIS_WEIGHT = 0.5` — mantido; a premissa do item estava errada.** O item
  dizia "o termo está morto" porque `decis_term` sai 0,0000 em 10/10 sementes. Mas isso é
  medido só nos indivíduos **finais**, e uma guarda que lê 0 no fim é uma guarda que
  **funcionou** — a busca saiu da região ruim. Medido em 18 rosters × 10 pares: o
  canônico, que *é* a geração 0 do AG escalar, dá **0,2834** com 5/10 pares acima do
  teto; 8 aleatórios dão 0,10–0,66; o espelho do Zoner — a solução trivial — dá 0,1282
  com **10/10 abaixo do piso**. 57/180 pares estouram o teto e o `D` observado chega a
  0,49 contra teto 0,20. As duas metades disparam e pegam coisas distintas: o teto pega
  blowout, o piso pega degenerescência.
- **Canônicos — declarados finais.** "Melhor valor" não existe aqui **por construção**:
  são a *premissa*, não variável a otimizar; ajustá-los para "ficarem melhores" seria
  mexer na premissa para obter a resposta. O que faltava era o **critério de aceitação**
  escrito: internamente coerentes (validador 23/23), distintos entre si (as 10 distâncias
  par-a-par ≥ 0,3221) e **desequilibrados** (`dominance` 1,2690 — o ponto de partida do
  problema, não defeito). E o que **não** se exige, com a razão: realizar o ciclo (o
  motivo registrado aqui, "loteria de 1/24", estava errado — ver «Leituras corrigidas»; o
  canônico realiza 6/10 dele, e é autoria, não premissa) e ser equilibrado (seria o
  problema resolvido de graça). Duas limitações
  declaradas junto: **5 dos 55 genes estão colados no bound e 4 deles são definidores**
  (Rushdown `attack_cooldown`/`speed`, Turtle `hp`/`attack_cooldown`/`damage`), então só
  podem driftar **para dentro** — a identidade desses dois é assimetricamente protegida
  num sentido e erodível no outro, e o `drift_penalty` não distingue os casos; e os
  canônicos **são** a referência do drift, logo mudá-los invalidaria todo número de drift
  já medido.
- **Escala dos pesos comportamentais — medido em 7,5%, não nos 55% registrados.** Só a
  **razão** entre `(w_agg, w_ret, w_def)` afeta o combate (a intenção é sorteada
  proporcionalmente), mas o drift mede valores absolutos. O número antes registrado vinha
  de uma conta **confundida por escala** — comparava distância no espaço bruto com
  distância no normalizado, dois espaços de escalas diferentes. Formulação exata: escalar
  os três pesos por `k > 0` não muda **nada** no combate, então o drift que some ao
  escolher o melhor `k` é cobrança por diferença indistinguível. Dá **7,5%** do drift
  médio (pior caso Rushdown 15,1%), e os `k` ótimos de 0,58–0,70 dizem o que houve: o AG
  **inflou a escala dos pesos** e o drift cobrou pela inflação. Atenua em parte que o
  artefato afeta também os modelos nulos, cancelando na leitura de *posição*; não cancela
  no drift absoluto.
- **`MULTI_RUN_N_SEEDS` 10 → 20.** Aqui "melhor valor" **é** bem definido, e foi medido
  por simulação de poder (4000 réplicas, dois normais separados por 1,190σ = Â₁₂ 0,80,
  critério `3 × p < 0,05`): **n=10 dá 44,4%** de poder, n=15 dá 73,1%, **n=20 dá 85,9%**,
  n=30 dá 97,3%. n = 20 é o menor que passa do patamar convencional de 80%. Com os 10
  atuais o experimento tem **menos de 50%** de chance de detectar um efeito grande que
  provavelmente existe — dizer "não significativo" a partir dali diz mais sobre a amostra
  que sobre os algoritmos.

## A regeneração parcial de artefato, e o número que ela escondia (2026-09-17)

**Problema.** A `external_validation` regenera **só o rótulo que recebe na linha de
comando**, e a bateria de 2026-09-17 rodou apenas `--nsga2 best_dominance`. Os outros três
rótulos (`_canonical`, `_evolved`, `_nsga2_knee_point`) ficaram no disco descrevendo o
motor anterior, e nada acusou: `git status` limpo (JSONs velhos seguem versionados) e mtime
recente (é do checkout, não da geração). O efeito não foi cosmético. A tabela que abre os
resultados — a degradação entre o `dominance` medido **durante** a busca e o medido **fora**
dela, que é o headline da rotação do stream — acabou comparando o **AG** de uma bateria com
o **NSGA-II** da outra, lendo "21× → 1,1×".

**Mudança.** Rodar os quatro rótulos no mesmo corte e refazer a tabela pareada, algoritmo
com algoritmo. Registrada como pendência de instrumentação a causa-raiz: **nenhum artefato
grava a config que o produziu**, então um JSON velho não se denuncia sozinho.

**Resultado — a correção deixa o achado mais forte, não mais fraco.** Pareado, os dois
algoritmos caem de degradação grande para ~1×:

| | AG escalar: dentro → fora | | NSGA-II `best_dominance`: dentro → fora | |
|---|---|---|---|---|
| bateria 2026-09-16 | 0,0039 → 0,0804 | **21×** | 0,0140 → 0,1148 | **8,2×** |
| bateria 2026-09-17 | 0,0153 → 0,0178 | **1,2×** | 0,0483 → 0,0545 | **1,1×** |

E o rótulo que estava velho carregava o resultado mais forte da bateria: o roster do **AG
escalar é o primeiro do projeto a sair ROBUSTO** da validação externa — 5/5 bonecos em
banda nas 10 condições independentes e **0/10** pares virando counter duro em qualquer uma
delas, com as WR por par em [42,0%, 57,8%]. Equilíbrio com arestas decididas, não
achatamento. Na bateria anterior o mesmo rótulo dava 3/10 counters.

**Efeito colateral metodológico:** isso recalibra a objeção ao veredito binário da
validação externa. Ele estava registrado como "binário **e sensível a ruído**"; a segunda
metade não se sustenta, porque o critério **discrimina** — o AG passa limpo e o
`best_dominance` reprova por um par que está fora em **9 das 10** condições (Grappler ×
Turtle, 63,6%–69,0%), não por um tropeço de amostragem. Um quantificador fracionário
reprovaria esse caso igual; o que ele mudaria é o *relato*, distinguindo um par
consistentemente fora de um que escapa uma vez por acaso. (Feito em 2026-09-18 — ver "O
veredito da validação externa ganhou a contagem", no fim deste documento.)

**A lição que vale para a redação:** um experimento cujos artefatos não carregam a
configuração que os gerou não tem como se auto-verificar, e a falha não aparece como erro —
aparece como um número plausível.

## Os artefatos passaram a carregar a própria proveniência (2026-09-17)

**Problema.** A causa-raiz do incidente acima: nenhum artefato de `results/` gravava a
configuração que o produziu. Sem isso, um JSON obsoleto é **indistinguível** de um atual —
`git status` limpo, mtime do checkout — e a falha não se manifesta como erro, e sim como um
número plausível dentro de uma tabela.

**Mudança.** `src/engine/provenance.py`: todo artefato passa a abrir com um bloco
`provenance` — timestamp, `fingerprint`, **toda** constante pública de `config.py` valor a
valor, digest dos canônicos (genes + `defining_genes` + `beats`) e digest do código de
`src/engine/`. A verificação é automática em `Individual.from_results` / `from_nsga2`, que
são o gargalo por onde toda ferramenta carrega um indivíduo evoluído.

Quatro decisões, cada uma contra um modo de falha específico — e as quatro são o conteúdo
metodológico do item, não detalhe de implementação:

1. **Enumerar as constantes, não listá-las à mão.** Uma lista curada apodrece em silêncio:
   a próxima constante adicionada ficaria invisível ao carimbo, que é exatamente o buraco
   que ele existe para fechar.
2. **Hashear o código do motor, não só as constantes.** O incidente não foi mudança de
   constante — `grab_power`, a colisão e a rotação do stream são *código*. Um carimbo só de
   constantes teria dito "atual" com o motor já diferente.
3. **Deixar `config.py` fora do digest de código,** porque seus valores vão gravados um a
   um. "`MATCHUP_WR_CAP` foi de 0,15 para 0,20" é acionável; "o hash mudou" não é.
4. **Não carimbar `N_WORKERS`.** A avaliação resemeia ao `_SEED_BASE` antes de cada
   round-robin, então o resultado independe de quantos workers avaliam — e um alarme que
   dispara à toa deixa de ser lido.

**Resultado.** Os artefatos da bateria de 2026-09-17 são anteriores ao módulo e receberam
carimbo **retroativo**, com o campo `backfilled` dizendo isso e como foi justificado: por
**reprodução bit-exata** sob o código atual — `single_run/ga.json` devolve
`fitness = −0,233101660623` sob `generation_seed(42, 150)`, e os 5 representantes do
`single_run/nsga2.json` devolvem os objetivos gravados. Os demais artefatos são função
determinística desses dois mais o motor, então re-rodar a bateria produziria números
idênticos mais um hash.

> ⚠️ **A inferência falhou num artefato.** O `sensitivity_analysis.json` não tinha sido
> regerado depois desses dois e era de 2026-09-16; a bateria de 2026-09-18 o pegou. Ver "O
> carimbo retroativo por inferência falhou num artefato", no fim deste documento.

**Um efeito colateral vale registrar:** a verificação por reprodução expôs que o
procedimento de checkup antigo (*"re-avaliar o melhor sob seed-base 42 devolve o gravado"*)
é anterior à rotação do stream e **não** vale mais. O número gravado é medido no stream da
**última geração**, `generation_seed(42, 150)`, não no seed-base — sob 42 o `dominance` sai
0,0665 contra 0,0153 gravado, enquanto o `drift`, determinístico, bate exato nos dois
casos. Quem for reproduzir um artefato precisa reproduzir também o *stream*.

> Revisto: a proveniência passou a recusar entrada velha e a cobrir o código de medição — ver a seção de mesmo tema em 2026-09-18.

## Os marcos de convergência viraram amostra, não anedota (2026-09-17)

**Problema.** Com os dois algoritmos em orçamento fixo, convergir virou evento registrado
(`converged_at` / `stagnated_at`) e "velocidade" passou a ser um segundo eixo de comparação,
além de "qualidade". Mas o `multi_run` não gravava esses campos: a única medida existente
era a da seed 42 — **n = 1**, anedota.

**Mudança.** `_run_algorithm` devolve os marcos junto do representante, `_seed_record` os
grava por semente e `_aggregate` produz `convergence`: taxa de convergência, geração média
entre as que convergiram, e o mesmo par para estagnação.

Duas escolhas de agregação que são o conteúdo do item:

- **A média sai só sobre quem convergiu.** Incluir as demais exigiria imputar um valor, e o
  único honesto — "não convergiu" — não é um número. A **taxa** carrega essa metade da
  informação, e as duas são lidas juntas: "converge em 70% das sementes, na geração 31 ± 8"
  diz o que nenhuma das duas sozinha diria.
- **O NSGA-II não recebe o campo, em vez de receber zero.** A assimetria é estrutural:
  *"o roster está equilibrado?"* não é pergunta que se faça a uma **fronteira**, que contém
  de propósito pontos desequilibrados-mas-fiéis. Gravar `0` ali produziria um número que
  alguém agregaria sem perceber; a ausência é a leitura correta e força a declaração.

**Resultado.** O eixo de velocidade passa a existir como amostra para o escalar — e fica
explícito no artefato que ele **não** é uma comparação pareada entre os dois algoritmos, e
sim uma caracterização do escalar. A medição sobre as 20 sementes saiu na bateria de
2026-09-18 — ver "A bateria com n = 20", no fim deste documento.

> Revisto: o `stagnated_at` foi removido — ver «O `stagnated_at` saiu».

## O sweep de lambda e o n = 20 viraram um experimento só (2026-09-17)

**Problema.** Os dois estavam na lista como pendências separadas: subir as sementes de 10
para 20 (poder estatístico) e varrer `LAMBDA_DRIFT` (demonstrar que o escalar é *um ponto*
do trade-off). Rodados em sequência, custariam duas regenerações — e a segunda compararia
seus braços contra uma bateria possivelmente produzida sob outro estado de código.

**Mudança.** Unificar, e a razão é estrutural, não de conveniência:

> **A fronteira do NSGA-II é λ-independente.** `nsga2.scalar_objective` é a única coisa no
> algoritmo que lê os `LAMBDA_*`, e é *reporting*, não busca: ela escolhe qual ponto da
> fronteira se chama `scalar_optimum`. A busca — dominância de Pareto e crowding — nunca
> olha os pesos. Logo **uma** execução do NSGA-II serve todos os braços do sweep: para cada
> λ, basta re-derivar aquele mínimo da fronteira já salva.

Some-se a isso que a célula λ=1,0 com 20 sementes **é** a bateria principal, e os dois
experimentos passam a compartilhar tudo o que é caro. Separados, o sweep teria de re-rodar
o NSGA-II (+4h42) ou aceitar comparar contra uma fronteira de outra proveniência.

O que a unificação exigiu de código: λ deixou de ser constante lida no import e virou
**estado de processo** (`fitness.set_lambdas` / `get_lambdas`), pelo mesmo motivo e com o
mesmo cuidado do `_SEED_BASE` — no Windows o pool nasce por *spawn* e re-importa o módulo,
então sem propagação explícita os workers avaliariam com o λ do `config.py` enquanto o pai
usa o do braço. Esse é o modo de falha mais caro possível aqui: um braço inteiro medindo o
λ errado, sem sintoma, saindo como resultado em vez de erro. Está coberto por teste que
compara o caminho paralelo com o serial sob dois λ.

**Uma consequência que valeu a pena:** o carimbo de proveniência da seção anterior assumia
`config.py` estático, e um sweep quebra isso — o artefato do braço λ=4,0 gravaria
`LAMBDA_DRIFT: 1.0`, mentindo sobre a própria origem. A solução foi registrar o override
**na mesma fonte que carimba** (`provenance.override`), de modo que `config_values()`
devolve o valor *em uso*. Daí sai de graça o que importa: cada braço tem `fingerprint`
próprio, e um braço lido sob a config padrão se identifica.

E uma distinção que precisou ser criada junto: um braço **não é** um artefato obsoleto.
`Divergence.is_experiment_arm` só vale quando a divergência é **inteiramente explicada**
pelos overrides que o artefato declarou — qualquer diferença fora disso (motor, canônicos,
outra constante) o devolve à condição de obsoleto. Sem a distinção o alarme dispararia nos
cinco braços e viraria ruído; com ela frouxa, o override seria salvo-conduto para esconder
mudança de motor. As duas falhas estão cobertas por teste.

**Resultado.** `run_battery.ps1`: passos retomáveis (`-From N`), ordenados para que
uma interrupção no meio ainda deixe a bateria principal completa e citável. Custo medido —
e aqui vai uma correção: a estimativa de ~180 min registrada para o n = 20 é **anterior à
rotação do stream**, que encareceu o escalar em ~1,8× e o NSGA-II em ~2×. Medido nos
artefatos: AG 7,2 min e NSGA-II 14,1 min por execução, o que põe o n = 20 em ~7h06 e a
bateria unificada inteira em **~10h17**.

## O sweep de λ: λ = 1,0 deixou de ser escolha por eliminação (2026-09-17)

**Problema.** `LAMBDA_DRIFT = 1.0` tinha só justificativa **negativa** — "6,0 prendia o AG
ao canônico, então baixamos". Nunca se mediu o que acontece nos valores intermediários, e
sem isso a afirmação central de que o escalar é *um ponto* de um trade-off era retórica: um
ponto só não faz curva.

**Mudança.** Sweep de 5 braços × 5 sementes, com o **orçamento reduzido** a pop 120 × 60
gerações (16% do custo) — 25 minutos em vez das 2h24 que o mesmo sweep custaria no
orçamento cheio. O que se pede dele é **ordenação**, não número citável.

> **Só a RAZÃO entre os dois λ importa**, e isso é o que faz um sweep de um parâmetro
> varrer a família inteira. A seleção é por torneio, que é ordinal: multiplicar `λ_drift` e
> `λ_dominance` pela mesma constante não muda decisão nenhuma. Então variar `λ_drift` com
> `λ_dominance` fixo em 1,0 percorre de "equilíbrio pesa 4× mais" (λ_drift = 0,25) a
> "identidade pesa 4× mais" (λ_drift = 4,0). *Ressalva:* a escala absoluta afeta uma coisa
> só — o limiar de estagnação, que é `> 0.001` absoluto; como estagnação virou evento
> registrado e não parada, isso mexe em `stagnated_at` e em mais nada.

**Resultado — a curva existe, e λ = 1,0 é o joelho dela.**

| λ_drift | peso relativo do dominance | dominance | drift | counters | convergiu |
|---|---|---|---|---|---|
| 0,25 | 4× | **0,0425** ± 0,0107 | 0,3681 | 0,4 | 100% |
| 0,5 | 2× | 0,0483 ± 0,0189 | 0,3740 | 0,6 | 100% |
| **1,0** | 1× | 0,0485 ± 0,0187 | 0,2982 | 0,6 | 80% |
| 2,0 | ½× | 0,1891 ± 0,1648 | 0,1763 | 4,0 | 40% |
| 4,0 | ¼× | 0,3365 ± 0,0803 | **0,0971** | 7,8 | 0% |

O trade-off é monotônico nas duas pontas: **drift cai 3,8×** e **dominance sobe 7,9×**. Mas
o formato é o achado, e ele não era óbvio: **`dominance` fica plano em ~0,048 até λ = 1,0 e
só então explode.** Entre 0,25 e 1,0 o equilíbrio custa praticamente nada enquanto o drift
já melhora de 0,37 para 0,30 — λ = 1,0 é o **último ponto onde identidade sai de graça**.
Depois dele o câmbio inverte: de 1,0 para 2,0 o drift melhora 0,12 e o dominance piora
0,14, com a variância triplicando e os counters duros indo de 0,6 para 4,0.

Dois modos de ler, e os dois apontam para o mesmo lugar:

- **Não existe "melhor λ"** no sentido de um ótimo — λ escolhe *onde se senta na curva*, e
  trocar identidade por equilíbrio é julgamento de valor, não algo que o dado decida.
- **Mas dentro da região plana, λ = 1,0 domina.** Contra λ = 0,25 ele entrega drift **0,070
  melhor** custando dominance **0,006 pior** — mais de 10× de retorno na troca.

E λ = 4,0 reproduz exatamente o sintoma que os docs atribuíam ao antigo λ = 6,0: drift
0,0971 (quase canônico) com **7,8 de 10 pares virando counter duro**. A patologia registrada
de memória agora tem medida.

**Consequência prática: nada mudou no `config.py`, e nada precisava mudar.** O sweep não foi
busca por um valor novo, foi **teste do valor vigente** — e ele passou. O ganho não é um
número diferente, é que λ = 1,0 passou de escolha por eliminação a joelho medido.

**Resultado de brinde — o ajuste ao stream, quantificado.** Os contadores do gate de
convergência (`convergence_gate_fired` / `convergence_rejected`) deram, sobre **62 disparos
em 25 execuções**, uma taxa de recusa de **67% a 83%** conforme o braço:

| λ_drift | gate disparou | confirmação recusou |
|---|---|---|
| 0,25 | 20× | 15× (75%) |
| 0,5 | 15× | 10× (67%) |
| 1,0 | 15× | 11× (73%) |
| 2,0 | 12× | 10× (83%) |

Ou seja: **~3 de cada 4 vezes em que o roster parece equilibrado sob o stream de treino, ele
não sobrevive a um stream inédito.** É exatamente o que a rotação do stream por geração
existe para combater, agora medido sobre uma amostra e não sobre a anedota de n = 1 que a
bateria de 2026-09-17 dava.

**Método que vale registrar junto:** este sweep só foi viável porque o orçamento virou
parâmetro de execução, e isso exigiu consertar um bug que ninguém tinha visto — `ELITE_SIZE`
era uma **contagem absoluta** (30) calculada uma vez no `config.py`, então reduzir a
população levava o elitismo efetivo de 10% para 25% (pop 120) ou 100% (pop 12, onde a
geração seguinte é só clones e o AG **para de buscar**), em silêncio e produzindo números
plausíveis. A consequência retroativa precisa aparecer no texto: os A/B da agenda de
calibração rodaram em pop 120, logo sob elitismo de **25%, não 10%**. Isso **não** invalida
aquelas decisões — o confundimento é constante nos dois braços de cada A/B —, mas significa
que "pop 120" nunca foi uma versão reduzida do AG de produção, e sim um AG com outra pressão
seletiva. Depois do conserto (`ELITE_RATE` fração, `elite_count` sobre o tamanho real), é.

**Um erro cometido no caminho, que virou regra.** Logo depois de rodar o sweep, um
re-carimbo **em massa** sobre `results/` apagou a proveniência dos cinco braços: `stamp()`
lê os overrides do processo que o chama, então aplicá-lo em lote reescreveu todos com a
configuração de quem rodava o lote, e os cinco passaram a afirmar `LAMBDA_DRIFT = 1.0`. Os
dados nunca foram tocados — só o registro de origem mentiu, que é precisamente a falha que o
módulo de proveniência existe para impedir. Duas consequências ficaram:

- **Regra:** re-carimbar é operação de **um artefato por vez**, sob os mesmos overrides que
  o produziram. Nunca em lote.
- **Conserto estrutural:** a configuração do experimento (`pop_size`, `n_generations`,
  `lambda_drift`, `lambda_dominance`) passou a ser gravada também no **corpo** do artefato,
  e não só no carimbo. O carimbo é um registro de *proveniência* e pode ser reescrito; a
  configuração do experimento é um *dado* e pertence ao artefato. Foi essa redundância que
  permitiu reconstruir os cinco — junto com o nome do arquivo, que já codificava o λ.

> Revisto: os sweeps passaram a rodar em sementes disjuntas das da bateria — ver «Os sweeps saíram das sementes da bateria».

## Os pesos do dominance: os termos secundários são carga estrutural (2026-09-17)

**Problema.** Os pesos `1,0 / 0,5 / 0,5` dos três termos do `dominance_penalty` nunca foram
variados. Pior: o `decis_term` lê **0,0000 no indivíduo final de toda execução saudável**, o
que a agenda de calibração chegou a levantar como suspeita de termo morto. A defesa era
argumentativa — "uma guarda que lê 0 no fim é uma guarda que funcionou" —, sustentada por
medições em rosters **não evoluídos** (canônico, aleatórios, espelhos). Faltava o teste
direto: desligar o termo e ver o que acontece.

**Mudança.** Sweep de 5 braços × 5 sementes em orçamento reduzido (pop 120 × 60, 25 min).

> **A comparação NÃO pode ser pelo `dominance_penalty`** — os pesos o *definem*, então o
> composto não é comparável entre braços. Ela é feita pelos **termos** (`global_term`,
> `cap_term`, `decis_term`, que são medições independentes dos pesos) e pelas métricas
> post-hoc (hard-counters, bonecos em banda, drift). Essa é a razão de a decomposição ser
> gravada separada desde a formulação C2.

**Resultado.**

| pesos g/cap/decis | global_term | cap_term | decis_term | drift | counters | convergiu |
|---|---|---|---|---|---|---|
| 1 / 2 / 0,5 | 0,0455 | **0,0000** | 0,0000 | 0,3372 | 0,2 | 100% |
| 1 / 1 / 1 | 0,0484 | 0,0108 | 0,0000 | 0,3470 | 0,2 | 100% |
| **1 / 0,5 / 0,5** | 0,0454 | 0,0063 | 0,0000 | 0,2982 | 0,6 | 80% |
| 1 / 0,5 / 0 | 0,0534 | 0,1440 | 0,0569 | 0,2454 | 3,2 | 40% |
| 1 / 0 / 0 | **0,0170** | **0,9030** | 0,3114 | 0,1548 | **10,0** | 0% |

**(1) O braço `1/0/0` falsifica de vez a hipótese "os secundários são decorativos".** Sem
eles o AG atinge o **melhor `global_term` de todos** — 0,0170, porque é a única coisa que
resta a otimizar — e ainda assim entrega **10 de 10 pares como counter duro, em 5 de 5
sementes**. Os cinco personagens ficam na banda global enquanto *toda* luta é massacre.

Isto é exatamente a patologia que a formulação C2 declarava como razão de existir do cap —
*blowout-coinflip*: 55% A-esmaga / 45% B-esmaga, WR global ~50% para todos, cada luta um
atropelo. A previsão existia como **raciocínio** desde a formulação; agora é **medida**, e
com a assinatura mais forte possível (10/10, desvio zero).

**(2) O `decis_term` não é inerte — ler 0 é ele funcionando.** Removê-lo sozinho (`1/0,5/0`)
leva os counters de 0,6 para **3,2 ± 2,5**, a convergência de 80% para 40%, e — o detalhe
que fecha o argumento — **piora o próprio `cap_term`**, de 0,0063 para 0,1440. Os dois
guardas são complementares: sem o piso de decisividade a busca torna as lutas decisivas, e
lutas decisivas empurram os pares para fora da banda de WR que o cap protege. O termo que
"lia zero" estava segurando o outro.

**(3) O que o sweep NÃO estabelece, e por isso o `config.py` não muda.** Subir o cap para
2,0 melhora counters (0,6 → 0,2) e convergência (80% → 100%) ao custo de drift (0,298 →
0,337). Mas a n = 5 isso é `0,6 ± 0,5` contra `0,2 ± 0,4` — bandas sobrepostas, 3 counters
totais contra 1. **Não é distinguível de ruído.** A leitura honesta: o experimento
estabelece que os termos são **indispensáveis** e não estabelece que a repartição 0,5/0,5
seja subótima. A direção sugere que mais peso no cap ajudaria; confirmar exigiria n maior, e
seria outro experimento.

**Para o texto, o ganho é de natureza diferente do sweep de λ.** Lá, a medida *confirmou* uma
escolha. Aqui ela **converte uma premissa de projeto em resultado experimental**: a
afirmação "equilíbrio global sozinho não é equilíbrio" deixa de ser argumento de desenho e
passa a ter contra-exemplo medido — um roster que o termo primário considera quase perfeito
(0,0170) e que é injogável (10/10 counters duros).

## O elitismo e o torneio: testados, e mantidos (2026-09-18)

**Problema.** `ELITE_RATE = 0.10` e `TOURNAMENT_SIZE = 3` eram os últimos parâmetros do AG
nunca variados. A justificativa era só "valores usuais da literatura" — a mesma posição em
que λ e os pesos do dominance estavam antes dos seus sweeps.

**Mudança.** Sweep de 7 braços × 5 sementes no orçamento reduzido (pop 120 × 60), contra o
braço default que os três sweeps compartilham. Os dois parâmetros só existem no AG escalar:
o NSGA-II seleciona por rank de Pareto e torneio binário, então rodá-lo por braço mediria o
mesmo número sete vezes.

**Resultado.**

| braço | global_term | cap_term | drift | counters | roster eq. | convergiu |
|---|---|---|---|---|---|---|
| elitismo 0 | 0,0593 | 0,0076 | 0,2746 | 1,4 ± 1,3 | 2/5 | 80% |
| elitismo 5% | **0,0391** | 0,0111 | 0,2723 | 1,0 ± 1,0 | 2/5 | 60% |
| **elitismo 10% · torneio 3** | 0,0454 | **0,0063** | 0,2982 | **0,6 ± 0,5** | 2/5 | 80% |
| elitismo 20% | 0,0473 | 0,0327 | 0,2736 | 1,6 ± 1,5 | 1/5 | 60% |
| elitismo 30% | 0,0516 | 0,0440 | 0,3136 | 1,8 ± 1,3 | 1/5 | 60% |
| torneio 2 | 0,0439 | 0,0884 | **0,2411** | 2,0 ± 2,9 | 2/5 | 40% |
| torneio 5 | 0,0528 | 0,1049 | 0,2575 | 2,2 ± 1,9 | 1/5 | 20% |
| torneio 7 | 0,0459 | 0,0886 | 0,2786 | 2,2 ± 3,3 | 1/5 | 60% |

**Nenhum braço domina o default.** Ele tem o menor número de counters e o menor `cap_term`
dos oito; as alternativas ganham um pouco de drift e pagam em counters. Como no sweep dos
pesos, a comparação é pelos termos e pelas métricas post-hoc, não pelo composto.

**O que o sweep NÃO estabelece, e por isso o `config.py` não muda.** A n = 5 nenhuma dessas
diferenças se separa do ruído — os desvios de counters chegam a 3,3 —, e o torneio dá um
padrão **não monotônico**: 3 sai melhor que 2 e que 5, e 5 empata com 7. Um ótimo real de
pressão seletiva produziria uma curva suave; um pico isolado no valor default tem mais a
cara de ruído. O braço sem elitismo, que devia ser o informativo (como o `1/0/0` foi nos
pesos), mostrou pouco: o `global_term` piora de 0,0454 para 0,0593, o pior dos oito, e o
resto fica dentro do ruído. A leitura honesta: 10% / 3 passam de "valores usuais" a
"testados neste problema, sem braço que os supere" — não a "ótimos".

**Consequência para o método:** os três sweeps exploratórios (λ, pesos, seleção) testaram
os valores vigentes e os três passaram. Nenhum parâmetro do AG ficou sem ter sido variado.

## A bateria com n = 20: o efeito se sustenta, e o de n = 10 estava inflado (2026-09-18)

**Problema.** A n = 10 o experimento tinha **44,4%** de poder para detectar um efeito grande
(simulação de poder, seção das constantes provisórias acima). As três métricas da família de
Holm saíram significativas na bateria de 2026-09-17, mas um resultado significativo numa
amostra subdimensionada tende a **superestimar** o efeito — a amostra que passa do limiar é,
em média, a que sorteou um efeito maior que o real.

**Mudança.** Rodar as 20 sementes (`run_battery.ps1`, 5h54). As sementes 42–51 reproduziram
**bit a bit** as 10 anteriores, nos dois algoritmos, o que confirma o "aditivo" que a decisão
pressupunha.

**Resultado — a conclusão se sustenta, e o tamanho do efeito encolhe.**

| métrica | mediana AG | mediana NSGA-II | p (Holm), n = 20 | Â₁₂, n = 20 | Â₁₂, n = 10 |
|---|---|---|---|---|---|
| `dominance_penalty` | 0,0387 | 0,0599 | **0,0123** | 0,27 | 0,20 |
| `drift_penalty` | 0,2526 | 0,1816 | **0,00007** | 0,89 | 0,94 |
| hard-counters/execução | 0 | 1 | **0,0018** | 0,21 | 0,14 |

Os p caíram, como se espera ao dobrar a amostra, e os três Â₁₂ **andaram na direção de 0,5**
— exatamente o que a preocupação previa. As 10 sementes novas foram mais favoráveis ao
NSGA-II (1,1 counter por execução contra 2,4 nas 42–51). O efeito continua **grande** nas
três métricas, e o de n = 20 é o que se cita.

**A decomposição ficou mais nítida, e muda a frase certa sobre o resultado.** O `global_term`
— o termo primário, que mede se alguém domina o roster — deu **0,0375 contra 0,0382**:
praticamente igual (a n = 10 eram 0,0375 contra 0,0470). O `cap_term` deu 0,0000 contra
0,0357. Então **toda** a vantagem do AG em `dominance` vem de counters duros: os dois
algoritmos equilibram o roster globalmente igual, e o NSGA-II perde porque deixa pares
passarem do teto. "O AG equilibra melhor" é impreciso; "o AG evita counters duros e o NSGA-II
não" é o que o dado diz. Em rosters: 14/20 do AG passam no critério completo, contra 4/20 do
`best_dominance`.

**O eixo de velocidade deixou de ser anedota.** O AG convergiu em **20/20 sementes**, sempre
confirmado num stream que nunca viu, na geração **34,8 ± 17,1** (18 a 75). E a amostra
corrigiu uma leitura feita a n = 1: a seed 42 não estagnava, e isso tinha sido tomado como
confirmação de que, sob rotação do stream, o contador de estagnação reseta por ruído e o
evento não dispara. Ele dispara em **10/20** sementes, tarde (geração 99,5 ± 21,2). O gate de
convergência disparou 70 vezes e a confirmação fora do stream recusou 50 (**71%**), dentro da
faixa de 67%–83% medida nos braços do sweep — agora no orçamento de produção.

> Revisto: quatro leituras desta bateria não se sustentavam — ver «Leituras corrigidas».
> E os números acima foram **substituídos** pela bateria de 2026-09-21, medida sobre o
> motor corrigido (timers com resto acumulado, CRN por luta) e com a família de 6: o
> empate no `global_term` não se repetiu (0,0397 contra 0,0490, o AG à frente), o NSGA-II
> passou a vencer as **quatro** réguas de identidade em vez de só o drift, e o
> `best_dominance` caiu de 4/20 para 2/20 rosters equilibrados (o `scalar_optimum`, a
> manchete nova, faz 0/20). Só a lição metodológica
> desta entrada — efeito de amostra pequena é inflado — segue valendo. Ver «O NSGA-II
> passou a vencer as quatro réguas de identidade».

## O carimbo retroativo por inferência falhou num artefato (2026-09-18)

**Problema.** O carimbo retroativo de 2026-09-17 reproduziu `single_run/ga.json` e
`single_run/nsga2.json` e **inferiu** o resto: *"os demais artefatos são função determinística
desses dois mais o motor"*. A inferência vale para um artefato gerado depois deles, e o
`sensitivity_analysis.json` não tinha sido: era do indivíduo de 2026-09-16, sob persistência
10 (piso de ruído 7,9%), e recebeu o carimbo de atual. A bateria o regerou — e re-rodar deu
resultado idêntico ao da bateria, então a ferramenta é determinística; o arquivo é que era
velho. Na mesma bateria apareceu uma segunda falha da mesma família: o `run_battery.ps1`
chamava `baselines --evolved` sem `--n-random`, o default do tool era 8, e o artefato saiu com
13 nulos em vez de 35 — a resolução do p caiu de < 0,03 para < 0,08 sem nenhum erro.

**O que as duas têm em comum:** nenhuma é detectável pelo carimbo. Na primeira, o carimbo
foi posto à mão sem reprodução; na segunda, a config do motor não mudou — mudou um argumento
de linha de comando, e o carimbo registra a config, não os argumentos.

**Mudança.** A sensibilidade foi regerada sobre o indivíduo atual. `N_RANDOM_DEFAULT` passou a
30, o valor do protocolo, para que a bateria e o dossiê (`report`) não dependam de um flag; o
`baselines.json` regerado saiu idêntico ao de 2026-09-17. Duas regras ficaram: **carimbo
retroativo só por reprodução do próprio artefato**, e **o default de uma ferramenta é o valor
do protocolo**, não um atalho mais barato. No `multi_run` a segunda regra esbarrava no
próprio carimbo: `MULTI_RUN_N_SEEDS` seguia 10 com a bateria passando `--n-seeds 20`, e
subir o default marcaria todos os artefatos como obsoletos, porque o carimbo grava toda
constante. A saída foi tirá-la do carimbo, com o mesmo argumento de `N_WORKERS`: ela só
define o tamanho da amostra, que o corpo do artefato do `multi_run` já grava (`n_seeds`,
`seeds`), e nenhum outro artefato depende dela. O default passou a 20, e o `compare` ignora
constantes excluídas também do lado gravado — sem isso, excluí-la invalidaria a bateria que
a exclusão existe para proteger.

**Resultado — a primeira medição de sensibilidade sobre o indivíduo atual.** Com 600 sims e 12
repetições do piso, para decidir o `knockback`:

| gene | \|Δ WR\| | sinal/ruído |
|---|---|---|
| `range` | 39,4% | 7,7 |
| `attack_cooldown` | 23,3% | 4,6 |
| `hp` | 20,0% | 3,9 |
| `damage` | 19,7% | 3,9 |
| `grab_power` | 9,8% | 1,9 |
| `stun` | 7,7% | 1,5 |
| `speed` | 5,9% | 1,2 |
| `knockback` | 5,5% | 1,1 |

(piso de ruído, máximo sobre 480 células sem perturbação: 5,1%)

A limitação registrada na seção da persistência — *"`knockback` continua abaixo do piso"* —
**muda de forma, não some**: no indivíduo atual nenhum gene fica abaixo do piso, mas
`knockback` e `speed` ficam no limiar, com sinal/ruído ~1,1. A diferença do `speed` (2,0 no
indivíduo em que se decidiu a persistência, 1,2 aqui) lembra que a análise é **local**: mede
a paisagem em volta de um indivíduo, e o que o AG enxerga depende de onde ele está.

## O veredito da validação externa ganhou a contagem (2026-09-18)

**Problema.** A validação externa declara um roster ROBUSTO só se nenhum boneco sair da
banda e nenhum par virar counter duro em **nenhuma** das 10 condições. O critério é
conservador e discrimina — o AG escalar passa limpo, o `best_dominance` reprova —, mas o
relato só dizia *se* um par falhou, nunca *quantas vezes*. Um par fora em 9 de 10 condições
e um que escapa uma vez por amostragem saíam idênticos na tabela.

**Mudança.** O veredito fica binário: um quantificador fracionário ("fora em mais de X% das
condições") não mudaria o veredito de nenhum roster da bateria, e trocaria uma regra sem
parâmetro por uma com um limiar a justificar. O que muda é o relato: a ferramenta grava e
imprime, por boneco, em quantas condições ele fica na banda e, por par, em quantas vira
counter duro.

**Resultado.** Os números antigos saíram idênticos, só com as contagens a mais, e a
distinção apareceu no primeiro uso. O `best_dominance` reprova por **um** par, Grappler ×
Turtle, fora em **9/10** condições — sistemático. O `knee_point` tem sete pares em 9–10/10 e
dois **esporádicos**, Zoner × Rushdown em 4/10 e Combo Master × Turtle em 6/10: ali o
veredito FRÁGIL é certo pelos sete, e os dois são o tipo de caso que a contagem existe para
não confundir com eles.

> Revisto: a validação externa separou replicação de robustez, com veredito por IC — ver a seção de mesmo tema.

## O pool de processos ficou persistente (2026-09-18)

**Problema.** A avaliação paralela criava um `ProcessPoolExecutor` novo a cada geração, e
cada worker novo re-importa o motor e recarrega o JIT. Numa geração de 300 indivíduos isso
custava mais que a própria avaliação: **3,87 s com pool novo contra 1,04 s com o pool
vivo**. A bateria de n = 20 levou 5h54 e os sweeps ~3h, grande parte gasta subindo
processos. Estava registrado por que não se fazia: com workers vivos, as mudanças de estado
do pai depois que eles nascem — o seed-base a cada geração (rotação do stream), os pesos a
cada braço de sweep — não chegariam a eles, e um worker avaliaria sob o estado velho sem
sintoma nenhum.

**Mudança.** Inverter onde o estado mora. O `RuntimeState` (seed-base, λ, pesos do
dominance) deixou de ir no `initializer` do pool e passou a viajar com **cada tarefa**; o
worker o aplica antes de toda avaliação (`fitness.parallel_map`). Com isso o pool pode viver
o processo inteiro — todas as gerações e todas as sementes de um `multi_run` — sem nenhum
worker jamais avaliar sob estado velho. `N_WORKERS` virou `min(8, os.cpu_count())`: o teto de
8 protege do `WinError 1455`, e com o pool vivo 8, 12 e 16 workers ficam dentro do ruído.

**Resultado.** Nenhum número muda, e isso foi verificado, não inferido. O teste de paridade
paralelo × serial passou a trocar seed-base e pesos entre avaliações servidas pelo mesmo pool
vivo. E a seed 42 de produção reproduziu **bit a bit** nos dois algoritmos: o AG no fitness,
no `converged_at` 39 e nas 150 gerações do histórico, em **3,0 min contra 6,7**; o NSGA-II na
fronteira inteira de 64 pontos e nos 5 representantes, em **5,8 min contra 9,7**. O ganho por
execução (2,2× e 1,7×) é menor que o por geração porque a avaliação de rosters evoluídos
pesa mais que a de aleatórios, e o spawn vira fração menor.

**Consequência declarada:** a mudança altera o código de `src/engine/`, logo o digest de
todo artefato, e `results/` passa a ler "obsoleto" mesmo com os números idênticos. A regra da
seção anterior vale aqui: re-carimbar exige reproduzir **cada** artefato, e reproduzir todos
é rodar a bateria. Com o pool novo ela custa ~3h45 estimadas, e os sweeps ~1h40. (Na
mesma noite o CRN passou a semear cada luta — seção seguinte —, e aí a bateria deixa de ser
re-carimbo e passa a substituir os resultados.)

## O CRN passou a semear cada luta (2026-09-18)

**Problema.** O CRN semeava o RNG **uma vez** por avaliação, e as 1500 lutas do round-robin
consumiam o mesmo stream em sequência. Cada luta gasta um número de sorteios proporcional à
própria duração, então a primeira luta que durasse diferente em dois indivíduos deslocava a
leitura de **todas** as seguintes — inclusive as de pares idênticos nos dois. Mudar um gene
do Zoner mexia, por sorteio, no resultado de Rushdown × Turtle.

**Mudança.** `fitness.fight_seed(seed_base, par, luta)`, misturado por SplitMix64, semeia
cada luta: a luta *k* do par *m* recebe os mesmos sorteios em todo indivíduo avaliado sob o
mesmo seed-base, não importa o que as anteriores consumiram. A rotação do stream por geração
fica igual — as sementes das lutas derivam do seed-base da geração. A `sensitivity_analysis`,
que semeava o combate direto, passou a usar o mesmo mecanismo.

**Resultado — o ganho é menor do que se esperava, e o registro precisa dizer isso.** A
proposta foi feita esperando um ganho possivelmente grande, sob a leitura de que, depois da
primeira luta divergente, os dois indivíduos ficavam como se tivessem sementes
independentes. A medição desmentiu as duas coisas. Roster evoluído contra ele mesmo com um
gene a +σ, 40 seed-bases:

| diferença pareada, mesma seed-base | stream único | uma semente por luta | ganho |
|---|---|---|---|
| f(X') − f(X), Zoner `range` +σ | DP 0,0328 | 0,0276 | 1,2× |
| f(X') − f(X), Turtle `stun` +σ | DP 0,0209 | 0,0213 | 1,0× |
| f(X') − f(X), Grappler `knockback` +σ | DP 0,0165 | 0,0127 | 1,3× |
| Rushdown × Turtle, com o Zoner alterado | DP 0,0190 | **0** | exato |

O stream único já preservava boa parte do pareamento: no par não afetado o DP da diferença
era 0,019, contra ~0,058 se as amostras fossem independentes. A semente por luta zera esse
resíduo, mas ele não era o ruído que pesa. O que sobra está **dentro** das lutas do
personagem alterado: quando o gene muda o que acontece numa luta, o resto dela se desenrola
diferente e os sorteios seguintes caem em estados diferentes. Semear por luta não alcança
isso; sincronizar por instante (sub-tick × lado) alcançaria, com ganho não medido. O custo é
+13% por avaliação.

**Por que ficou mesmo assim:** decisão do autor, com os números acima na mesa. O contrato
exato nos pares não alterados é uma propriedade limpa e testável (`test_fitness`: mudar um
gene do Zoner deixa os 6 pares sem ele bit a bit iguais), o ganho existe ainda que pequeno,
e a bateria já teria de rodar pelo pool persistente. **Consequência declarada:** todos os
sorteios mudam, logo todos os números da tese — a bateria seguinte substitui os resultados,
e as conclusões (incluindo as dos três sweeps) precisam ser relidas contra ela.

## Os cinco representantes do NSGA-II por semente (2026-09-18)

**Problema.** O teste entre algoritmos a n = 20 representava cada execução do NSGA-II pelo
`best_dominance`, escolha sem porquê registrado. O comparável que o próprio projeto declara
honesto — o `scalar_optimum`, mínimo da mesma função que o escalar otimiza — só era medido
na seed 42. O `multi_run` gravava os genes apenas do representante escolhido, então testar
contra outro ponto exigiria re-rodar o NSGA-II nas 20 sementes (~2h17).

**Mudança.** O `multi_run` grava os cinco representantes de cada semente, cada um
reavaliado sob a semente de validação exatamente como o de topo. O `compare_algorithms`
ganhou `--nsga2-representative`: troca o registro que cada semente contribui, sem re-rodar
nada, e grava em arquivo à parte (`comparison_ga_vs_nsga2_<REP>.json`). A bateria roda as
duas comparações: contra o `best_dominance` e contra o `scalar_optimum`.

**Resultado.** Custo de ~0,15 s por semente (cinco reavaliações de 0,03 s), contra minutos
de execução; o registro de topo sai idêntico ao do mesmo ponto em `representatives`
(conferido num ensaio de 2 sementes). O `best_dominance` **manteve-se** como representante
padrão, pela continuidade com as baterias anteriores: a escolha de qual comparação vira a
principal fica para depois da próxima bateria, com os dois resultados em mãos. O que a
comparação contra o `scalar_optimum` mostra é resultado dessa bateria.

> Revisto: a manchete foi decidida antes da bateria, pelo método — ver «A manchete da comparação passou ao `scalar_optimum`».

## A auditoria do zero: o que o sistema medido sustentava (2026-09-18)

Uma revisão feita **sem contexto prévio** — lendo o código e os artefatos como um leitor
externo leria, sem os docs como guia — achou três classes de problema, cada uma resolvida
numa seção abaixo:

1. **afirmações sobre o motor que o código não cumpria** — o período do cooldown e a
   continuidade do stun;
2. **leituras que os números não sustentavam** — sobre a régua de identidade funcional,
   o equilíbrio "melhor que o espelho", a não-transitividade e o ciclo autoral;
3. **buracos de protocolo e de instrumentação** — controles ausentes, representante de
   manchete, validação externa que só replicava, proveniência que podia ser lavada.

Todas as decisões abaixo foram tomadas **antes** da bateria que vai medi-las, com os
resultados anteriores já obsoletos (o CRN por luta troca todos os sorteios). Nenhuma foi
escolhida olhando o número que ela produziria.

## Os timers passaram a carregar o resto (2026-09-18)

**Problema — duas afirmações do motor eram falsas.** (i) O período entre golpes era
`round(5c) + 1` sub-ticks, não `round(5c)`: o timer recém-setado não decrementa no próprio
sub-tick, então quem tem `attack_cooldown = 1` batia a cada **6** sub-ticks. O argumento
de coerência da persistência — "5 sub-ticks = exatamente o cooldown mínimo" — estava
apoiado num número errado. (ii) O stun **continuava categórico**. A reforma de
2026-09-10 trocou o timer arredondado por um float decrementado de 1,0 e registrou que
isso tirava o gene dos "4 níveis efetivos"; mas um alvo com stun float `s` fica parado
exatamente `ceil(s)` sub-ticks — o mesmo degrau, só com os limiares deslocados (o ganho
de amplitude medido na época veio desse deslocamento de `round` para `ceil`, não de
continuidade). Medido no motor de então:

| | cooldown 1 | 1,3 | 2,5 | 5 |
|---|---|---|---|---|
| período esperado (sub-ticks) | 5 | 6,5 | 12,5 | 25 |
| período observado | **6** | **7** | **13** | **26** |

Com cooldown 1, stun de 0,02 a 0,20 travava 1 sub-tick, de 0,22 a 0,40 travava 2, de 0,42
a 0,60 travava 3: **4 efeitos** em todo o intervalo do gene. No indivíduo evoluído, variar
só o stun do Rushdown (cooldown 1,107) em 31 valores de 0 a 0,6 dava **5 WR distintas** — o
gene era um platô para o atacante mais rápido do roster.

**Mudança.** Os dois timers passaram a **carregar o resto** de uma aplicação para a
seguinte (difusão de erro, `combat._carry_round`): o período sorteado de cada golpe é o
inteiro da soma `5c + resto`, e o resto fica para o próximo; o mesmo para os sub-ticks de
stun. A média é exata e o combate segue determinístico — o sorteio de intenção continua a
única fonte de acaso. O sub-tick do próprio golpe passou a contar como o primeiro do
período. O stun virou inteiro no trace.

**Resultado.** Período observado 5,000 · 6,500 · 12,500 · 25,000 — exato nos quatro. Stun
aplicado por golpe, com cooldown 1: 0,250 · 0,500 · 0,748 · … · 2,994 para `stun` 0,05 ·
0,10 · 0,15 · … · 0,60 — linear no gene. O mesmo teste do Rushdown evoluído: **27 WR
distintas em 31**. O canônico segue passando nas 23 asserções do validador; as WR globais
se mexem pouco (Zoner 38,3% → 41,2%, Grappler 62,0% → 58,8%, os outros três iguais). Com o
período certo, o argumento da persistência passa a ser verdadeiro: 5 sub-ticks é
exatamente o período do atacante mais rápido. `test_combat` cobre os dois timers.

## O validador parou de dar asserções por empate (2026-09-18)

**Problema — dois defeitos no instrumento que mede identidade estrutural.** (i) O ranking
das asserções da Layer 1 resolvia empate pela **ordem do índice**: com cinco personagens
idênticos, o de índice 0 (o Zoner) era "o de maior alcance". Todo espelho passava em **4
das 13** asserções da Layer 1 sem ter identidade nenhuma — o piso dos modelos nulos estava
inflado por um detalhe de implementação. (ii) As asserções sobre os pesos comparavam o
valor **cru**, enquanto o projeto já tinha estabelecido que só a razão entre os pesos age
no combate (`fitness.drift_genes`). No indivíduo evoluído, o ranking cru e o da
probabilidade de intenção discordavam em 2 das 3 asserções de peso (Zoner, "quem mais
recua": 2º cru, 1º real; Turtle, "quem mais guarda": 3º cru, 4º real).

**Mudança.** Empate conta **contra** a asserção (`_rank_against`: um valor empatado ocupa
uma faixa de posições, e vale a ponta mais longe da esperada). As asserções de peso leem a
probabilidade de intenção (`Character.intention_probabilities`), a mesma forma em que o
peso age.

**Resultado.** Os espelhos passam em **0/13** da Layer 1 (antes 4/13) e em 1–4/18 das
estruturais (antes 5–8/18); o piso dos aleatórios não muda (valores contínuos não
empatam). A média nula do validador completo cai de 6,37 para 5,97/23, e o pior nulo segue
em 10/23. O canônico segue 23/23. `test_archetype_validator` cobre os dois: nenhum espelho
aprova asserção da Layer 1, e escalar os pesos não muda o veredito.

## A identidade funcional ganhou uma régua contínua (2026-09-18)

**Problema — a régua que responde à pergunta era a mais grossa do projeto, e estava no
piso.** A pergunta de pesquisa diz *identidades funcionais*, e o projeto designa a Layer 3
(comportamental) como a régua que a responde. Mas a Layer 3 são 5 bits — cada arquétipo
precisa ser o **1º** numa métrica, e ficar em 2º por um fio conta igual a ficar em 5º. E,
lida contra os nulos, ela não sustentava a leitura corrente: o indivíduo da bateria de
2026-09-18 passava em **1/5**, com **p = 0,74** contra os 35 nulos — indistinguível de um
roster aleatório. A frase "a identidade supera os 35 nulos nos três eixos (p < 0,03)" vinha
do drift (que está no fitness) e das Layers 1-2 (que o próprio projeto declara
endógenas). A política dele mostrava o mesmo por outro ângulo: o Rushdown evoluído guardava
mais do que avançava (pesos 0,39 / 0,71 / 0,52) e era o **menos** agressivo dos cinco; o
Zoner avançava mais do que recuava; o Turtle recuava mais do que guardava.

**Mudança.** Uma segunda régua funcional, contínua: a **concordância de ranking
comportamental** (`archetype_validator.rank_agreement`) — τ-b de Kendall entre a ordem dos
5 personagens no canônico e no roster, em cada uma das 10 métricas do perfil comportamental,
na média. 1 = a ordem do canônico em tudo, 0 = acaso, −1 = invertida. Usa as 5 posições
e todas as métricas, sem asserção escrita à mão, e é relativa ao roster nos dois lados (um
deslocamento que afeta todos igual não conta como perda). Entra no validador, nos modelos
nulos (com piso, teto e p), no dossiê e, por semente, no `multi_run`. A Layer 3 continua.

**Resultado.** Canônico: 1,000. Nos 35 nulos: média +0,001, desvio 0,173, máximo +0,338 —
o comportamento de uma régua de acaso bem calibrada. Re-teste (o mesmo roster sob 3
sementes): o canônico fica ≥ 0,97 com 120 ou 200 lutas por par; o evoluído varia 0,19–0,28
a 120 e 0,23–0,24 a 200 — daí `IDENTITY_BEHAVIORAL_SIMS = 200`. **Leitura preliminar**, a
confirmar na bateria: o evoluído da bateria anterior, reavaliado no motor atual, tira
τ = +0,19 com **p = 0,14** — também não se distingue do acaso. Se a bateria confirmar, a
resposta honesta é que o equilíbrio alcançado **não preserva a identidade funcional
medida**, e que o que o drift preserva é a identidade estrutural.

> Revisto: a bateria de 2026-09-21 **não** confirmou a leitura preliminar — τ = 0,314 e
> Layer 3 3/5 no indivíduo da seed 42, e separação com efeito grande contra o controle
> `λ_drift = 0` sobre 20 sementes. A régua que responde acabou sendo o controle, não os
> nulos: ver «A identidade funcional saiu do piso — e a régua que vale é o controle, não
> os nulos».

## Os controles: λ_drift = 0 e AG sem semente canônica (2026-09-18)

**Problema — nada isolava o efeito do método.** (i) Os modelos nulos não são otimizados:
um roster evoluído com penalidade de drift vencer rosters aleatórios em drift e nas
Layers 1-2 é garantido por construção, e não diz quanto da identidade o termo de drift
segura. O contrafactual da pergunta de pesquisa — *equilibrar sem o termo de identidade* —
não tinha sido medido; o sweep de λ foi de 0,25 a 4, sem o 0. (ii) O AG escalar começa com
o canônico na população e o NSGA-II começa aleatório — e o próprio projeto já tinha
registrado que um detalhe de inicialização **inverteu** a conclusão entre algoritmos. A
comparação AG × NSGA-II confundia algoritmo com inicialização.

**Mudança.** Dois braços de controle **na bateria**, com a amostra e o orçamento dela (n =
20, pop 300 × 150): AG com `λ_drift = 0`, e AG sem a semente canônica
(`GA_CANONICAL_SEED`, flag `--no-canonical-seed`). O `multi_run` passou a rotear
artefatos em três destinos: o protocolo (a bateria), `results/controls/` (desvio só de
desenho, amostra e orçamento do protocolo — citável) e `results/exploratory/` (desvio de
amostra ou orçamento — os sweeps). O `compare_algorithms --control` compara a bateria com
cada controle, com o mesmo aparato estatístico. O override `GA_CANONICAL_SEED` vai para o
carimbo como qualquer braço.

**Resultado.** Pendente da bateria. O que cada comparação responde, declarado antes dela:
AG × `λ_drift = 0` mede quanto de cada régua de identidade (drift, Layers 1-2, Layer 3, τ)
o termo de drift segura, e a que custo em equilíbrio; AG × sem semente mede quanto da
diferença entre AG e NSGA-II é inicialização.

## A manchete da comparação passou ao `scalar_optimum`, com a relação de Pareto (2026-09-18)

**Problema.** A comparação principal representava o NSGA-II pelo `best_dominance` — o
extremo de baixa dominância da fronteira, que perde em drift **por construção**. Como
manchete, "NSGA-II melhor em drift" media em boa parte a escolha do ponto. A seção "Os
cinco representantes" tinha deixado a escolha para depois da próxima bateria, com os dois
resultados em mãos — o que faria a manchete ser escolhida olhando o resultado.

**Mudança.** A escolha foi feita **antes** da bateria, pelo método: a manchete é o
`scalar_optimum`, o ponto que minimiza a própria função do AG escalar — o único comparável
a ele (`multi_run.HEADLINE_REPRESENTATIVE`). O `best_dominance` virou a leitura secundária.
Ao lado, descritiva e fora da família de Holm, a **relação de Pareto por semente**: o ponto
do AG contra a fronteira **inteira** do NSGA-II da mesma semente — domina algum ponto dela,
é dominado por algum, ou nenhum dos dois. Os dois lados são medidos no mesmo stream (o da
última geração da mesma semente), então a relação não carrega ruído de stream. E a família
de métricas testadas passou a ser a mesma em toda comparação — equilíbrio (`dominance`,
counters, bonecos em banda) e identidade (drift, Layers 1-2, Layer 3, τ): 7 métricas,
decididas antes de ver dados.

**Resultado.** Pendente da bateria. Custo: cada métrica a mais multiplica o menor p por um
fator maior no Holm; com n = 20 e os efeitos grandes da bateria anterior (p de 0,0018 a
0,00007 antes da correção), a família de 7 não muda o que é significativo nelas.

## A validação externa separou replicação de robustez (2026-09-18)

**Problema — ela só trocava a semente.** As 10 "condições" eram 10 sementes das mesmas
regras: replicação com mais amostra, não robustez a "condições que o AG nunca otimizou". E
o veredito binário ("counter duro em ALGUMA das K condições") ficava mais severo a cada
semente acrescentada, mesmo com o roster intacto — um par cuja WR real está em 64% reprova
com probabilidade crescente em K.

**Mudança.** Duas perguntas, cada uma com uma amostra de 5000 lutas por par (as 10
sementes somadas): **replicação** (regras do treino) e **robustez** (uma constante de regra
perturbada por vez — distância inicial 40/60, campo 80/120, persistência 4/6, redução da
guarda 0,55/0,65; `EXTERNAL_VALIDATION_RULE_PERTURBATIONS`). O veredito de cada WR sai do
IC de Wilson (95%) contra a banda: dentro, fora, ou inconclusivo — e a condição é ROBUSTA,
FRÁGIL ou INCONCLUSIVA. As regras do combate viraram estado de processo
(`combat.CombatRules`, `set_rules`), levadas aos workers no `RuntimeState` como os pesos.

**Resultado.** O veredito não depende mais do número de sementes. Pendente da bateria. O
dado anterior já indica por que a amostra somada importa: na bateria de 2026-09-18, com
5000 lutas por par, os 10 pares do roster do AG estavam todos **decididos** (|z| ≥ 3,6,
WR de 42,0% a 57,8%) — o que as 200 lutas do `baselines` não conseguiam mostrar.

## O `stagnated_at` saiu (2026-09-18)

**Problema.** A estagnação disparava quando o "melhor fitness histórico" não subia por 30
gerações. Com o stream rotacionando a cada geração, esse histórico é o máximo de valores
**ruidosos**: sobe por sorte, e depois raramente é batido. O evento media a catraca do
ruído, não a busca — "estagnou em 10/20, na geração 99,5" era um número sem objeto.

**Mudança.** `stagnated_at` e `STAGNATION_LIMIT` foram removidos. O eixo de velocidade
fica com `converged_at`, que testa o predicado `roster_balanced` em vez de um número
ruidoso.

**Resultado.** Um número frágil a menos em todo artefato do AG. O que `converged_at`
significa também foi escrito com mais cuidado: é o **primeiro** disparo do gate que
sobrevive à confirmação, num teste repetido a cada geração — na bateria anterior o gate
disparou 70 vezes e a confirmação recusou 50. Convergir não é ficar equilibrado: 20/20
sementes convergiram, mas 14/20 terminaram com o roster equilibrado na reavaliação.

## O hipervolume ganhou uma referência com significado (2026-09-18)

**Problema.** O ponto de referência era (2,0; 1,0) — os máximos teóricos dos dois
objetivos —, longe de qualquer fronteira real (máximos observados nas 20 fronteiras da
bateria: `dominance` 1,219, drift 0,260). O HV ocupava 90,4% da área de referência e
variava pouco entre sementes (coeficiente de variação 2,0%): "o hipervolume ficou igual"
era em parte o instrumento saturado.

**Mudança.** Referência (1,3; 0,4), ancorada nos modelos nulos: `dominance` ≈ a do
canônico (o equilíbrio de partida) e drift ≈ o do espelho (identidade zero). Um ponto com
equilíbrio pior que o de partida, ou identidade pior que a de cinco cópias, não conta.

**Resultado.** Nas mesmas 20 fronteiras: HV 76,7% da área (antes 90,4%), coeficiente de
variação 3,9% (antes 2,0%) — o dobro de resolução entre fronteiras, sem excluir nenhum
ponto real.

## O joelho e o ideal deixaram de depender da unidade (2026-09-18)

**Problema.** O `knee_point` (maior distância à reta entre os extremos) e o `ideal_point`
(menor norma L2 até a **origem**) eram calculados em unidades cruas. Com `dominance` indo
até 2,0 e drift em décimos, a escala de um eixo decidia a geometria; e a origem não é
alcançável por nenhum ponto.

**Mudança.** Os dois passaram a usar os objetivos normalizados pela amplitude da própria
fronteira, e o ideal passou a ser o mais próximo do **ponto utópico** (o melhor de cada
objetivo). `test_nsga2` cobre a invariância: mudar a unidade de um objetivo não muda o
ponto escolhido.

**Resultado.** Nas 20 fronteiras da bateria anterior, o `ideal_point` muda em **19/20**; o
`knee_point`, em 0/20. O ideal antigo era, na prática, o ponto de menor `dominance`
corrigido pelo drift — a escala escolhia por ele.

## A sensibilidade passou a cobrir os pesos, com janela inteira e o piso certo (2026-09-18)

**Problema — três defeitos.** (i) Só os 8 atributos eram medidos; os 3 pesos, que definem
a política (15 dos 55 genes), nunca. (ii) Perto do bound, o deslocamento era **cortado**:
num gene encostado no limite (no evoluído, o cooldown do Rushdown em 1,11, o stun do Combo
Master em 0,59, o dano do Turtle em 15,00) um lado da janela sumia e o gene parecia menos
visível só por estar na borda. (iii) O piso de ruído era o máximo de |Δ| de **uma célula**,
mas o número classificado é a **média de 5** |Δ| — estatísticas de variâncias diferentes.

**Mudança.** Os 11 genes, cada um com o σ que a mutação usa nele; janela de largura 2σ que
**desliza** para dentro do bound em vez de ser cortada; e o piso medido na mesma
estatística do ranking (média sobre os personagens de |Δ| sob janela zero).

**Resultado — preliminar**, no evoluído da bateria anterior com o motor atual. O piso cai
de 0,068 (máximo de uma célula) para 0,037 (máximo da estatística certa; média nula
0,019). `stun` (0,106) e `grab_power` (0,085) passam de borderline a visíveis; `speed` e
`knockback` (0,055) de neutros a borderline. E um achado novo: na escala da mutação,
`w_retreat` (0,026) e `w_defend` (0,024) ficam **abaixo do piso**, `w_aggressiveness`
(0,049) no limiar — o AG quase não enxerga a política pelo equilíbrio. O único gradiente
que a puxa de volta ao canônico é o do drift.

> Revisto na bateria de 2026-09-21, no indivíduo dela: piso 0,035, e os três pesos seguem
> no fundo do ranking, mas trocam de posição entre si — `w_defend` (0,029) e
> `w_aggressiveness` (0,030) abaixo do piso, `w_retreat` (0,048) no limiar, ao lado de
> `knockback` (0,043) e `speed` (0,035). A conclusão não muda, e o controle `λ_drift = 0`
> a confirma por outra via: sem o termo de drift, τ = +0,007.

## A proveniência passou a recusar entrada velha e a cobrir o código de medição (2026-09-18)

**Problema — três buracos por onde um número velho passava por atual.** (i) O
`compare_algorithms` checava os dois artefatos **um contra o outro** e carimbava o
resultado com a configuração vigente: dois `multi_run` obsoletos da mesma configuração
geravam uma comparação que se declarava atual. O mesmo nas ferramentas que carregam um
indivíduo salvo (`external_validation`, `baselines`, `sensitivity_analysis`): o
carregamento só **avisava**, e o artefato novo saía carimbado como atual. (ii) O digest de
código cobria só `src/engine/`: mudar as asserções do validador ou o cálculo de uma métrica
no `baselines` não tornava obsoleto nenhum artefato que dependesse delas. (iii) O
`multi_run` só olhava orçamento, λ, pesos e seleção para decidir o destino: um
`--n-seeds 3` no resto do protocolo gravava por cima da bateria de n = 20 — a falha
silenciosa que a própria função existia para impedir.

**Mudança.** (i) `provenance.refuse_if_stale`, o par estrito do `warn_if_stale`: quem
**grava** um artefato a partir de outro recusa entrada não-atual (um controle é aceito
quando a divergência é exatamente o override que ele declara). Quem só inspeciona segue
avisando. (ii) Digest de medição **por artefato**: cada ferramenta passa o próprio módulo
ao `stamp`, e o carimbo guarda o digest dele e de tudo de `src/` fora do motor que ele
importa, transitivamente — lista derivada das importações, não escrita à mão. Mudar o
validador invalida o `baselines.json` e o `multi_run`, e só eles. (iii) O destino do
`multi_run` passou a considerar todo desvio do protocolo, inclusive de amostra e de sims.

**Resultado.** `test_provenance` e `test_multi_run` cobrem os três. O custo declarado do
item (ii): uma mudança cosmética num módulo de medição também invalida os artefatos que
dependem dele — o mesmo preço já aceito para o motor, contra o silêncio do contrário.

## Os sweeps saíram das sementes da bateria (2026-09-18)

**Problema.** Os sweeps rodavam nas sementes 42–46, e a bateria em 42–61: um quarto da
amostra que **avalia** a configuração escolhida era a mesma que a **escolheu**.

**Mudança.** Os sweeps rodam nas sementes 1000–1004 (streams 1 000 000+, sem colisão com
nenhuma família do projeto).

**Resultado.** Seleção e avaliação em amostras disjuntas. Os 16 braços precisam rodar de
novo de qualquer forma (motor mudou); os nomes deles passam a levar `n5_seed1000`.

## O piso de decisividade: mantido, com a justificativa corrigida (2026-09-18)

**Problema.** O comentário do `MATCHUP_FLOOR` dizia que o piso "pega a solução trivial de
equilíbrio" (o espelho). Medido, ele pega **um** dos cinco espelhos — o do Zoner, o caso
menos decidido que o motor produz (D 0,016–0,019); os outros quatro (D 0,03–0,09) passam.

**Mudança.** Manteve-se 0,02, porque a função real do piso segue válida: ele fica acima do
roster degenerado (dano mínimo, HP máximo, só GUARDA: 0% de KO, D ≤ 0,008) e abaixo de todo
par de personagens distintos, e não morde nenhum roster evoluído. A justificativa passou a
dizer isso, e a dizer que a defesa contra a solução trivial é o `drift_penalty`, que cobra a
perda de identidade de qualquer espelho.

**Resultado.** Nenhum número muda; a afirmação passa a ser a que os dados sustentam.

## Leituras corrigidas (2026-09-18)

Quatro frases dos resultados de 2026-09-18 não se sustentavam nos próprios números. Ficam
registradas porque o erro é instrutivo, e porque a próxima bateria não pode repeti-lo.

- **"Mais equilibrado que o espelho (0,026 contra 0,025)".** 0,026 é *maior* que 0,025 —
  pior. Os "102% do equilíbrio trivial" eram contra a **média** dos espelhos, puxada pelo
  do Zoner (0,113, que o piso de decisividade penaliza); sem ele, a média é 0,030. E os
  0,026 do evoluído eram 100% `global_term`, no piso de ruído amostral de 200 lutas: a
  leitura correta é *tão equilibrado quanto a simetria perfeita, dentro do ruído*.
- **"Tríades circulares em 4,0, com pares em 43%–55%: arestas decididas."** A 200 lutas por
  par, 43%–55% é o espalhamento de puro ruído — os espelhos dão 44%–56% e chegam a 4,0
  tríades. A evidência boa estava em outro artefato: com 5000 lutas por par, os 10 pares
  estavam decididos e formavam um torneio **regular** (5 tríades, o máximo). Mesmo assim,
  equilíbrio global com pares decididos **força** intransitividade (um roster
  estritamente transitivo não pode ter todos perto de 50%), então ela é em boa parte
  consequência do objetivo, não achado independente. O que não é implicado — os pares
  seguirem decididos — é o que se reporta.
- **"Acertar o ciclo autoral é loteria de 1/24."** O argumento está errado: com arestas
  decididas, realizar as 10 arestas teria p = 1/1024 sob cara-ou-coroa, altamente
  informativo. O motivo real de o ciclo não servir de régua é outro: **o próprio canônico
  realiza só 6/10** dele no motor. E contra as direções que o canônico **realiza** —
  consequência da premissa, não da autoria —, o favorito de cada confronto não sobreviveu
  ao equilíbrio: 105 de 186 arestas decididas (56,5%, p = 0,091) contra 49,7% dos nulos,
  a 16.000 lutas por par. *(O número desta linha era "5/10 a 2000 lutas por par"; refeito
  em 2026-09-22 — ver «O ciclo saiu do `baselines`».)*
- **"A identidade supera os 35 nulos nos três eixos (p < 0,03)."** Os três eixos eram o
  drift (no fitness), as Layers 1-2 (endógenas) e o validador completo, dominado pelas
  estruturais. Na régua funcional isolada, o evoluído passava em 1/5 da Layer 3, com
  p = 0,74 — ver "A identidade funcional ganhou uma régua contínua".

## O controle `λ_drift = 0`: a identidade sai de graça (2026-09-21)

**Problema.** Com `LAMBDA_DRIFT = 1,0` ativo a corrida inteira, não havia como separar
"o equilíbrio preserva a identidade" de "o termo de drift segura a identidade, e o
equilíbrio nem a viu". Os modelos nulos não respondem isso: eles não são otimizados. O
contrafactual tinha que ser o mesmo AG, mesma amostra, mesmo orçamento, **sem** o termo.

**Mudança.** A bateria passou a rodar o braço `--lambda-drift 0` com n = 20 e pop 300 ×
150, em `results/controls/`, comparado por `compare_algorithms --control` na mesma família
de 6 métricas.

**Resultado (medianas sobre 20 execuções).** Tirar o termo **não compra equilíbrio nenhum
e zera a identidade**:

| | AG (λ = 1) | λ = 0 | p (Holm) | Â₁₂ |
|---|---|---|---|---|
| `dominance_penalty` | 0,0399 | 0,0534 | 0,063 | 0,30 |
| hard-counters | 0 | 0 | 0,553 | 0,54 |
| `drift_penalty` | 0,2473 | 0,4055 | 4,1 × 10⁻⁷ | 0,00 |
| validador L1+L2 | 11 | 6 | 1,1 × 10⁻⁶ | 0,98 |
| validador L3 | 3 | 1 | 0,00024 | 0,85 |
| concordância τ | 0,2811 | −0,0304 | 0,00022 | 0,87 |

As duas métricas de equilíbrio não se separam — e o braço sem drift é até ligeiramente
*pior* em `dominance`, que é o oposto do que "o drift atrapalha o equilíbrio" preveria.
As quatro de identidade se separam todas, com efeito grande. Na média das 20 execuções o
braço λ = 0 dá **τ = +0,007 ± 0,151**: o acaso com três casas decimais, contra
+0,259 ± 0,159 do AG.

O trade-off que o sweep de λ mede é real, mas o joelho está longe o bastante de λ = 1,0
para que o termo de identidade **não custe equilíbrio**. É o resultado mais forte da
bateria, e o único que responde à pergunta de pesquisa sem depender de régua endógena.

## O segundo controle: a semente canônica não explica a diferença entre os algoritmos (2026-09-21)

**Problema.** O AG escalar parte da semente canônica e o NSGA-II de população aleatória
(a semente é imortal no rank 0 — ver "A semente canônica saiu do NSGA-II"). A assimetria
é justificada, mas confunde algoritmo com inicialização.

**Mudança.** Braço `--no-canonical-seed` na amostra e no orçamento da bateria.

**Resultado.** Separa **só no drift** (0,2473 contra 0,2703, p_Holm 0,043) e em mais
nada: `dominance` 0,0399 contra 0,0403 (p = 0,964), L1+L2 11 contra 10,5 (p = 0,334),
L3 3 contra 2 (p = 0,366), τ 0,2811 contra 0,1931 (p = 0,310). A semente dá uma dianteira
estrutural modesta e nada mais. A diferença medida entre os dois algoritmos não é
inicialização.

## A identidade funcional saiu do piso — e a régua que vale é o controle, não os nulos (2026-09-21)

**Problema.** A leitura preliminar de 2026-09-18, feita sobre o indivíduo daquela bateria,
dava a identidade funcional no piso do acaso: Layer 3 **1/5** com p = 0,74 e τ = 0,19 com
p = 0,14. Se a bateria confirmasse, a resposta à pergunta de pesquisa seria "o equilíbrio
preserva a identidade estrutural e não a funcional".

**Mudança.** Nenhuma no código — a bateria mediu sobre o motor corrigido (timers com resto
acumulado, CRN por luta), que troca todos os sorteios.

**Resultado.** A leitura preliminar **não se confirmou**. No indivíduo da seed 42:
Layer 3 **3/5** (p = 0,03, empatando com o melhor nulo) e τ = **0,314** (p = 0,06, um fio
abaixo do melhor nulo, 0,316). Sobre as 20 sementes: L3 2,45 ± 1,00 e τ +0,259 ± 0,159.

O que a bateria ensina sobre **qual régua responde**: contra 35 nulos, um único roster não
dá resolução — 35 nulos dão p mínimo de 1/35, e o melhor deles chega perto do evoluído em
ambas as métricas funcionais por puro sorteio. Contra o controle `λ_drift = 0`, com 20
execuções de cada lado, as duas separam com efeito grande (p_Holm 0,00024 e 0,00022). **O
denominador certo da identidade funcional é o braço sem o termo, não o roster sem
projeto.** Os nulos continuam valendo para o que foram feitos: estabelecer que nenhuma
métrica tem piso zero.

## O NSGA-II passou a vencer as quatro réguas de identidade (2026-09-21)

**Problema.** Na bateria de 2026-09-18 (família de 3) o NSGA-II vencia só no
`drift_penalty`, e o resumo era "cada um ocupa um extremo do trade-off" com uma métrica de
cada lado. Com a família de 7 e a manchete no `scalar_optimum`, a bateria testa as duas
metades da pergunta com quatro réguas de identidade em vez de uma.

**Mudança.** Nenhuma no desenho — a família de 7 e a manchete no `scalar_optimum` foram
decididas antes da bateria, e o motor é o corrigido.

**Resultado.** **As seis métricas da família são significativas, todas com efeito
grande**, e a divisão é exatamente a das duas metades: o AG escalar vence as duas de
equilíbrio (`dominance` 0,0399 contra 0,0796, Â₁₂ = 0,10; hard-counters 0 contra 3,
Â₁₂ = 0,03) e o NSGA-II as quatro de identidade (drift Â₁₂ = 1,00 — separação **total**,
as duas amostras não se sobrepõem —, L1+L2 0,05, L3 0,24, τ 0,09).

O contraste mais duro está fora da família: **o AG termina com o roster equilibrado em
14/20 sementes e o NSGA-II em 0/20**, com 3,0 ± 1,5 hard-counters por execução contra
0,30 ± 0,47. A decomposição diz onde: `global_term` 0,0397 contra 0,0490 (perto),
`cap_term` 0,0030 contra 0,0807 (longe). Globalmente os dois equilibram parecido; o
NSGA-II deixa par passar do teto.

Relação de Pareto por semente: **18/20 mutuamente não-dominados**, o AG dominando um ponto
da fronteira numa semente e sendo dominado em outra. O ponto do escalar fica além da ponta
de baixa dominância da fronteira — compra equilíbrio com um drift que a fronteira não
oferece.

## `n_chars_balanced` deixou de discriminar qualquer coisa (2026-09-21)

**Problema.** A métrica "quantos dos 5 personagens ficam em banda" já saía da família de
Holm por degenerescência (`_is_degenerate`), mas isso era lido como uma peculiaridade da
comparação entre os dois algoritmos.

**Resultado.** Na bateria de 2026-09-21 ela dá **5/5 em 80 de 80 execuções** — AG,
NSGA-II e os **dois controles**, inclusive o braço sem termo de identidade nenhum.
Equilibrar os cinco personagens globalmente é fácil neste sistema: qualquer busca que olhe
o `global_term` chega lá. O que discrimina são os **pares** — hard-counters e `cap_term` —,
e é por isso que o `dominance_penalty` não pode ser só o termo primário. A exclusão da
família deixa de ser detalhe técnico e vira um resultado: a métrica é informativa sobre o
sistema e inútil como comparação.

## O ciclo autoral não sobrevive ao equilíbrio: 5/10, o piso (2026-09-21)

**Problema.** Registrar, no motor atual, o que acontece com o ciclo de vantagens — que
**nunca esteve no fitness**, por decisão (seria responder à pergunta com ela mesma).

**Resultado.** O evoluído mantém **5/10 arestas**, exatamente a média dos nulos (5,0),
posição 0% entre piso e teto, p = 0,63. O canônico, no mesmo motor, realiza 6/10. Não é
falha do método: o objetivo é cego à direção (`|WR − 0,5|`), então nada no fitness
distingue "o Zoner ganha do Grappler" de "o Grappler ganha do Zoner". O caso mais claro é
o Grappler × Turtle, aresta canônica forte (o agarrão é o counter do bloqueio, 100% no
canônico): o AG a **achata** para 51% ± 6% nas 20 sementes, hard-counter em nenhuma.

O ciclo segue como leitura post-hoc e **não** como régua de identidade — o canônico mesmo
não o realiza inteiro.

> **Nota de revisão (2026-09-22): a conclusão se manteve; a evidência era ruído e foi
> substituída.** Ver «O ciclo saiu do `baselines` e virou experimento próprio», abaixo.
> Em resumo: «5/10, posição 0%, p = 0,63» era **um** roster medido a 200 lutas por par, e
> a margem mediana das arestas de um roster equilibrado é 0,048 contra σ = 0,035 a 200
> lutas — o mesmo roster lê 5/10 a 200 lutas e 8/10 a 16.000. O número que vale, sobre as
> 20 sementes a 16.000 lutas por par e contando só arestas decididas: **105 de 186
> (56,5%), binomial p = 0,091**, contra 49,7% dos nulos. Não é "exatamente o piso" como o
> item dizia: é **indistinguível do acaso**, com inclinação fraca e não significativa na
> direção autoral.

## A validação externa: só o AG escalar replica (2026-09-21)

**Problema.** Medir se o equilíbrio encontrado é do roster ou do stream, e se depende das
regras exatas do treino.

**Resultado.** Com 10 sementes inéditas agrupadas em 5000 lutas por par e veredito pelo IC
de Wilson, a separação é total: o **AG escalar é o único dos quatro rótulos que replica**
(ROBUSTO, `dominance` 0,0373 fora do laço contra 0,0251 dentro — degradação de 1,5×,
contra 21× na bateria pré-rotação), e sobrevive a 4 das 8 regras perturbadas, com 2
inconclusivas e 2 frágeis. O canônico e os dois representantes do NSGA-II falham a
replicação e as 8 regras.

As duas regras que quebram o AG são `FIELD_SIZE = 80` (campo menor: Zoner × Turtle a
68,8%) e `ACTION_PERSISTENCE_SUBTICKS = 6` (Combo Master × Turtle a 69,4%, Turtle a 39,3%
global). As duas mexem em **quanto espaço e quanto compromisso a política tem** — coerente
com o limite declarado de a política ser fixa e cega ao estado, e a leitura honesta é que
o equilíbrio encontrado é condicionado a essas duas regras mais do que às outras seis.

## λ = 1,0 deixou de empatar com os λ menores e passou a dominá-los (2026-09-21)

**Problema.** O sweep de λ de 2026-09-17 estabeleceu λ = 1,0 como o joelho — `dominance`
plano até ele, explodindo depois —, mas contra λ = 0,25 a troca era "drift 0,070 melhor
por dominance 0,006 pior": um empate favorável, não uma dominância.

**Mudança.** Nenhuma no `config.py`. Os 16 braços foram re-rodados sobre o motor corrigido,
nas sementes 1000–1004.

**Resultado.** O formato da curva se manteve (`dominance` 0,060–0,065 em λ = 0,25, 0,5 e
1,0; 0,198 em λ = 2,0; 0,358 em λ = 4,0), mas λ = 1,0 **passou a dominar** os dois braços
mais baratos: mesmo `dominance`, drift 0,2448 contra 0,3462 e 0,3773, e τ = **+0,415**
contra +0,018 e −0,050. Abaixo de λ = 1,0 o AG paga identidade sem comprar equilíbrio —
não há razão nenhuma para ficar lá.

## Elitismo 10% / torneio 3: mantidos, por outra razão (2026-09-21)

**Problema.** A justificativa de 2026-09-18 era "o default tem o menor `cap_term` e o menor
número de counters dos oito braços". Sobre o motor corrigido, essa frase deixou de ser
verdadeira.

**Resultado.** O default **não tem nem um nem outro**: elitismo 0, elitismo 5% e torneio 2
fazem 0,6 counter por execução contra 0,8 dele, e três braços têm `cap_term` menor
(elitismo 0 em 0,0063, torneio 2 em 0,0083, torneio 7 em 0,0119, contra 0,0176). O que o
default tem é o **melhor drift (0,2448) e a melhor concordância de ranking (τ = 0,415)**
dos oito, e cada braço que o supera em counters paga nos dois.

**Manteve-se 10% / 3**, e a afirmação passa a ser "**nenhum braço os domina**" — mais
fraca que a anterior e mais fiel. A n = 5 nada disso se separa do ruído (os desvios de
counters vão a 1,3) e o torneio segue com padrão não monotônico (3 melhor que 2 e que 5, 5
igual a 7), que tem mais cara de ruído do que de ótimo de pressão seletiva. Registrar a
troca importa: o eixo em que o default ganha é justamente o da pergunta de pesquisa.

## Os pesos do dominance: a falsificação se manteve (2026-09-21)

**Problema.** Confirmar, sobre o motor corrigido, se os dois termos secundários do
`dominance_penalty` continuam sendo carga estrutural.

**Resultado.** `1 / 0 / 0` continua sendo a falsificação: sem os secundários o AG atinge o
**melhor `global_term` de todos os 16 braços** (0,0275 — é a única coisa que resta a
otimizar) e entrega **8,8 dos 10 pares como hard-counter**, com `cap_term` 0,7921 e
`decis_term` 0,2668. Os cinco na banda global, toda luta um massacre: o *blowout-coinflip*
que a formulação C2 previa.

E o `decis_term` não é inerte: removê-lo sozinho (`1 / 0,5 / 0`) leva os counters de 0,8 a
2,2 e **piora o próprio `cap_term`**, de 0,0176 para 0,1212. Ler 0,0000 no indivíduo final
é o termo tendo funcionado.

**`config.py` inalterado.** Os braços que dobram ou igualam o peso do cap (`1/2/0,5` e
`1/1/1`) entregam menos counters (0,2) e mais rosters equilibrados (80%), mas pagam
0,06–0,10 de drift e **mais da metade da concordância de ranking** (τ 0,159 e 0,113 contra
0,415). A n = 5 e em orçamento reduzido a troca não se distingue de ruído, e o eixo que
ela sacrifica é o da pergunta de pesquisa — manteve-se 1,0 / 0,5 / 0,5.

## As tabelas cruas do dossiê passaram a viver no artefato (2026-09-21)

**Problema — duas tabelas que a tese apresenta só existiam no terminal.** O
[`06-results-to-present`](06-results-to-present.md) §1 lista, no dossiê do indivíduo, a
**tabela de drift por gene**, a **diferenciação par-a-par** e o **fingerprint
comportamental**. Nenhuma das três era gravada: o `baselines.json` guardava o
`drift_penalty` (escalar) e o `per_character_drift` (5 valores), e do comportamento só o
resultado agregado — `validator_behavioral` (5 bits) e `rank_agreement` (um número). O
perfil de 10 métricas por personagem era calculado dentro do `run_validation`, usado para
a Layer 3 e o τ, e descartado. Redigir exigiria re-rodar uma ferramenta e ler a saída do
terminal, que é exatamente a fonte que o projeto não aceita para número citável.

Havia um segundo problema, pior: `fingerprint` e `archetype_validator`, rodados sozinhos,
tinham `--seed 42` chumbado, enquanto `report` e `baselines` usam
`MULTI_RUN_VALIDATION_SEED`. O mesmo indivíduo dava **τ = +0,334 pelo caminho standalone e
+0,314 pelo protocolo** — e o melhor nulo é 0,316, então a frase "acima ou abaixo do
melhor roster sem projeto" trocava conforme o caminho.

**Mudança.** (i) O `measure()` do `baselines` passou a gravar, por roster de referência e
para o alvo, `per_gene_drift`, `differentiation` e `behavioral_profile`. O perfil é
recomputado sob a **mesma semeadura** que o `run_validation` usa internamente, então é bit
a bit o que produziu a Layer 3 e o τ, não uma segunda medição. (ii) `fingerprint` passou a
usar o seed do protocolo como default e `FINGERPRINT_SIMS = IDENTITY_BEHAVIORAL_SIMS`, em
vez de um 200 repetido — duas constantes iguais por coincidência divergiriam no primeiro
ajuste. (iii) `mean_pairwise_distance` virou pública no `drift_table`, fonte única dos
dois consumidores.

**O que NÃO mudou, e por quê.** O `archetype_validator` continua com `--seed 42` no
standalone. O código dele está no digest de medição do `baselines`, do `multi_run` e da
`external_validation`: trocar esse default marcaria como obsoletos os 4 `multi_run` da
bateria e os 16 braços de sweep, e o `compare_algorithms` se recusaria a reescrever a
partir deles — **~7h de recomputação para uma mudança que não altera número nenhum**, já
que os três callers passam `seed=` explícito. O preço do digest cobrir código, e não
comportamento, é declarado desde que ele existe; aqui ele foi cobrado. A regra passou a
ser: **citar τ e o perfil comportamental do `baselines.json` ou do `report`, nunca do
validador standalone.**

**Resultado.** `baselines.json` reproduziu todos os agregados bit a bit (τ 0,314,
Layer 3 3/5, drift 0,236, ciclo 5/10, dominance 0,031, os mesmos p) com as três tabelas
novas junto — a extensão acrescentou dados sem tocar em medição. O `baselines` foi o único
artefato invalidado, e custa 28 s. A diferenciação do evoluído sai em 1,201 contra 1,353
do canônico: **89% da diferenciação preservada**, um número de homogeneização que antes
não existia em lugar nenhum.

## O histórico do AG escalar ganhou um plot (2026-09-21)

**Problema.** O [`06-results-to-present`](06-results-to-present.md) §2 pede a curva de
convergência do AG — e o `history` das 150 gerações estava no `single_run/ga.json` desde
sempre, sem nada que o desenhasse. O NSGA-II tinha `nsga2_plots`; o escalar, nada.

**Mudança.** `src/visualization/ga_plots.py`, com dois painéis: `best/mean/worst fitness`
e os dois termos (`dominance_penalty`, `drift_penalty`) do melhor, com `converged_at` como
linha vertical. Lê o **artefato**, não o objeto em memória, e é isso que o `main.py` chama
depois de salvar — uma serialização só, em vez de duas para manter em sincronia. Roda
sozinho (`py -m src.visualization.ga_plots`), sem re-executar o AG.

**Resultado.** Na seed 42 a curva mostra o que as tabelas afirmam: `dominance` despenca de
0,80 para ~0,03 nas primeiras 20 gerações, `drift` estabiliza em ~0,28 e cai devagar até
0,24, e a convergência na geração 31 cai onde as duas curvas já achataram. O plot também
torna visível a consequência declarada da rotação do stream — as curvas **flutuam** em vez
de serem monotônicas, que é a razão de não existir evento de estagnação.

## Os representantes da fronteira coincidem, e a figura precisava dizer isso (2026-09-21)

**Problema.** O plot da fronteira desenhava os 5 representantes com o mesmo tamanho de
marcador. Quando dois critérios escolhem **o mesmo ponto**, o segundo cobre o primeiro — e
a figura central do capítulo de Resultados passa a ter uma legenda citando um marcador que
não aparece nela. Na seed 42 é exatamente o caso: `scalar_optimum` cai sobre
`best_dominance`, e `ideal_point` sobre `knee_point`.

Não é acidente da seed 42. Medido sobre as 20 sementes da bateria: **`best_dominance` e
`scalar_optimum` são o mesmo ponto em 11/20**, e `knee_point` e `ideal_point` em 11/20
(`knee_point` = `scalar_optimum` em 2/20).

**Mudança.** Os marcadores passam a ser desenhados **aninhados** — agrupados por posição e
ordenados do maior ao menor —, e a caixa de anotação lista as coincidências
("Melhor dominância = Ótimo escalar"). O `nsga2_plots` também ganhou o caminho a partir do
artefato (`py -m src.visualization.nsga2_plots`), como o `ga_plots`: redesenhar a figura
não custa mais os 7 min de uma execução do NSGA-II.

**Resultado, e por que ele importa além da figura.** Que a manchete (`scalar_optimum`) e a
leitura secundária (`best_dominance`) sejam **o mesmo ponto em mais da metade das
sementes** é um dado sobre o formato da fronteira, não só sobre o desenho: na ponta de
baixa dominância a fronteira é íngreme o bastante para que minimizar a soma ponderada e
minimizar a dominância pura levem ao mesmo lugar. Reforça, por outro caminho, a decisão de
fixar a manchete **antes** da bateria: em 11 sementes a escolha nem teria efeito, e nas 9
restantes ela é a diferença entre comparar com o extremo da fronteira e comparar com o
ponto que otimiza a mesma função do AG escalar.

## O teste passou a ser o pareado (2026-09-21)

**Problema — o desenho é pareado e o teste era o de amostras independentes.** Uma
auditoria do zero notou a contradição dentro do próprio código: `compare_algorithms`
**exige** que os dois braços rodem as mesmas sementes (a constante se chama
`_PAIRED_FIELDS`, e `_check_comparable` aborta se divergirem), e a semente fixa tudo que
é aleatório dos dois lados — `random.seed(seed)` dá a mesma população inicial e a mesma
sequência de operadores, `generation_seed(seed, g)` dá o mesmo stream de avaliação na
geração `g`. A execução `i` de um braço e a execução `i` do outro são o mesmo bloco
experimental. Mann-Whitney U assume amostras **independentes**: aplicá-lo aqui joga fora
o poder que o CRN pagou. Nos controles a contradição é mais gritante ainda — é o mesmo
algoritmo, mesma semente, um único fator trocado: desenho casado de manual.

**Mudança.** O teste da família passou a ser o **Wilcoxon signed-rank pareado**
(`zero_method="wilcox"`, que descarta os pares sem diferença), e é sobre ele que o Holm
corrige. O **Mann-Whitney continua impresso ao lado**, cru, fora do Holm.

**Por que os dois aparecem.** Trocar de teste depois de já ter resultado é risco de
*p-hacking*, e a troca de fato mexe num resultado de fronteira. A defesa não é argumentar
que a intenção era boa — é não esconder nada: os dois p-valores saem na mesma tabela, em
todas as quatro comparações, e quem lê confere sozinho que as conclusões não dependem da
escolha. A justificativa da troca é do **desenho** (sementes idênticas exigidas em
código), não do p-valor, e ela foi aplicada à família inteira de uma vez, não à célula
que muda.

**Resultado.** Em 23 das 24 células das quatro comparações os dois testes dão o mesmo
veredito. A exceção é o controle `λ_drift = 0`, em `dominance_penalty`:

| | p bruto | p_Holm | veredito |
|---|---|---|---|
| Mann-Whitney (não-pareado) | 0,0315 | 0,0630 | sem diferença |
| **Wilcoxon (pareado)** | 0,0192 | **0,0385** | **AG melhor, efeito médio** |

A leitura do controle muda de "tirar o termo de identidade não compra equilíbrio" para
"**tirar o termo de identidade piora o equilíbrio**" — cinco das seis métricas passam a
separar a favor do braço com o termo, e só os hard-counters empatam. O achado central da
bateria fica mais forte, não mais fraco, e por um motivo metodológico que não depende
dele.

## O piso da sensibilidade depende de quantas nulas você roda (2026-09-21)

**Problema.** O piso de ruído é o **máximo** sobre `reps × 11` médias nulas. Máximo de
amostra cresce com o tamanho da amostra: com `--null-reps 3` são 33 nulas e o piso fica
perto do percentil 97; com 10 seriam 110, e o piso subiria — genes hoje no limiar
(`speed` 3,5%, `knockback` 4,3%, `w_retreat` 4,8% contra um piso de 3,5%) poderiam
mudar de classe. O número era reportado sem essa dependência.

**Mudança — e o que NÃO mudou.** Manteve-se o máximo. Um quantil fixo (p95) seria estável
em relação a `reps`, mas o máximo é o critério **conservador** e o mais fácil de
defender — "nem o ruído sozinho chegou até aqui" —, e trocá-lo mexeria num número já
medido para ganho marginal. O que passou a existir é a declaração: o docstring de
`_measure_noise_floor` e a saída do tool dizem que o piso depende de `--null-reps` e
qual valor o produziu, e o artefato grava `null_reps`. **Citar o piso sem o `reps` ao
lado é citar um número incompleto.**

**Resultado.** Nenhum número muda (o tool é determinístico e reproduziu idêntico); o que
muda é que a limitação do critério fica escrita onde quem cita o número vai olhar.

## O caminho sem semente ficou inalcançável, em vez de consertado (2026-09-21)

**Problema.** `Individual.clone()` copia o `fitness`, `evaluate_population` pula quem já
tem fitness, e a invalidação por geração está dentro de `if seed is not None`. Sem
semente, os elites **nunca são re-medidos**: um elite que tirou uma avaliação de sorte
fica com aquele número para sempre, não regride à média e se reclona geração após
geração. É a patologia que a rotação do stream existe para impedir — e `py main.py`, o
comando de entrada da documentação, rodava exatamente aí, porque `--seed` tinha default
`None`.

**Mudança — e por que não foi o conserto óbvio.** O conserto é mover duas linhas de
`invalidate_fitness()` para fora do `if`, em `ga.py` e `nsga2.py`. Mas os dois estão no
`engine_digest`: editar qualquer arquivo de `src/engine/` marca **todo** o `results/`
como obsoleto, e re-carimbar custa a noite inteira (sweeps + bateria) para produzir
números **bit a bit iguais** — o conserto é comprovadamente inerte em execuções com
semente, que são todas as da bateria.

Optou-se por fechar o caminho em vez de consertar o motor: `main.py --seed` passou a ter
default (`MULTI_RUN_SEED_START`), então nenhuma invocação pela CLI alcança o caminho
enviesado, e `py main.py` reproduz o passo 9 da bateria. O defeito latente em
`ga.run(seed=None)` está registrado no
[`10-known-issues`](../reference/10-known-issues.md) §1 para ser corrigido junto da
próxima mudança de motor que já exija re-rodar.

**Resultado, e a justificativa que vale além da economia.** Semear por default não é
contorno: uma execução sem semente grava um artefato que **ninguém consegue reproduzir**,
o oposto do que o carimbo de proveniência existe para garantir. O default explícito é o
comportamento coerente com o resto do projeto — a economia de uma noite é consequência,
não motivo. É a mesma decisão tomada duas vezes antes (o seed default do
`archetype_validator`, as tabelas cruas do dossiê): não pagar horas de recomputação por
números idênticos, desde que a ressalva fique escrita onde quem cita vai olhar.

## `MULTI_RUN_SIMS` saiu de `SIMS_CONVERGENCE_CHECK` (2026-09-22)

**Problema.** As duas constantes valiam 200 porque uma era definida como a outra
(`MULTI_RUN_SIMS = SIMS_CONVERGENCE_CHECK`), mas elas respondem a perguntas diferentes e
têm custos incomparáveis: a confirmação de convergência roda **dentro** do laço, a cada
disparo do gate, e subir o valor dela encarece a busca; a reavaliação do `multi_run` roda
**uma vez por execução**, sobre um indivíduo só, e custa 10 pares × sims lutas — 2.000
contra as 67.500.000 da execução que a produziu. Acopladas, a segunda não podia ganhar
resolução sem a primeira ficar mais cara.

E a resolução importava mais do que parecia. Medido em 30 streams, o desvio do
`dominance` de um mesmo roster a 150–200 lutas é **0,015–0,028** — da ordem do próprio
valor evoluído (~0,04). Nos agregados de n = 20 isso é inofensivo, porque o ruído é
simétrico entre os braços e a média o dilui; o teste pareado inclusive absorve o excesso
de variância como conservadorismo. Numa amostra pequena, não é: comparando dois braços em
5 sementes, o veredito **inverteu** entre a reavaliação a 200 sims (um stream) e a 1000
sims (quatro streams) — a 200, o braço novo parecia pagar equilíbrio pela identidade; a
1000, ele equilibra melhor *e* preserva mais identidade.

**Mudança.** `MULTI_RUN_SIMS` passou a ser um literal, com a evidência no comentário do
`config.py`, e a pendência do **valor** (200 → 1000) foi registrada em
[`10-known-issues`](../reference/10-known-issues.md) §1 para acompanhar a próxima
re-execução: a constante entra no carimbo de config, então trocá-la agora obsoletaria a
bateria de 2026-09-21 inteira sem nenhum número novo para pôr no lugar.

**Resultado.** O desacoplamento não muda valor gravado nenhum — a bateria segue *atual* —,
mas separa duas decisões que estavam presas uma na outra e deixa a regra de leitura
escrita onde quem cita vai olhar ([09](09-values-and-choices.md) §6): **nenhuma conclusão
por semente, nem comparação de braço em amostra pequena, a 200 sims.** É a terceira vez
que a resolução de uma medida muda uma leitura neste projeto — as outras duas foram
`IDENTITY_BEHAVIORAL_SIMS` (120 → 200, τ variando 0,19–0,28) e o piso da sensibilidade
medido na estatística errada. O padrão vale como lição de método: **antes de comparar dois
braços, medir o ruído da régua que vai decidir a comparação.**

## O ciclo saiu do `baselines` e virou experimento próprio (2026-09-22)

**Problema — em duas camadas.** A primeira: `cycle_edges_kept` e `circular_triads` viviam
no `baselines.py`, medidos a `MULTI_RUN_SIMS` = 200 lutas por par e reportados na tabela de
piso/teto ao lado de `drift_penalty`, do validador e de τ, com `piso`, `posição` e `p`.
Essa formatação afirma "isto é uma régua". Não é: o ciclo nunca esteve no fitness, o
próprio canônico não o realiza, e — a parte nova — **a resolução não dava para medi-lo**.
A margem mediana das arestas de um roster *equilibrado* é 0,048 contra um desvio binomial
de 0,035 a 200 lutas: a direção de cada aresta era cara-ou-coroa.

A segunda camada é o que provou isso: os **espelhos**. Cinco cópias do mesmo arquétipo têm
estrutura de torneio zero por construção, e marcavam **5,40/10 "mantidas" com 1,00/10
decididas**. Uma métrica que dá acima do piso num roster sem nenhuma estrutura está
medindo sorteio. O mesmo roster do dossiê lê **5/10 a 200 lutas e 8/10 a 16.000**.

**Mudança.** As duas funções saíram do `baselines` para
`src/experiments/cycle_structure.py`, que grava `results/cycle/cycle_structure.json` e é o
passo 17 da bateria. Três diferenças de desenho:

1. **Resolução própria:** 16 × 1000 = 16.000 lutas por par (σ = 0,0040), contra as 200 do
   resto do `baselines`. Não dava para subir a resolução de todas as métricas junto — o
   `baselines` mede 36 rosters com perfil comportamental —, e é o motivo de a métrica ter
   de sair em vez de ser consertada no lugar.
2. **Só arestas decididas contam** (`|WR − 0,5| > 2σ`). Aresta indecisa é sorteio, e
   contá-la mistura sinal com ruído nos dois sentidos.
3. **Grupos comparados pela taxa mantidas/decididas, não pela contagem.** Um roster
   aleatório decide 10/10 arestas e um equilibrado 9,3/10; comparar contagem crua puniria o
   equilibrado por ter uma aresta em cima do limiar. Coberto em
   `test_cycle_structure.py`, que é onde o contrato "aresta indecisa não conta" está
   protegido: 10 arestas a 50,2% com limiar de 1% dão `kept = 10` e
   `kept_and_decided = 0`.

O campo `beats` **fica** em `archetypes.py`. É premissa declarada, custa 5 tuplas, e é a
parte verificável do argumento de não-circularidade: a resposta está escrita no código e
nenhuma função de fitness a lê. Tirá-lo trocaria uma prova por uma promessa — e mudaria o
digest dos canônicos, obsoletando todo o `results/` por nada. A coluna `Ciclo` do
`analyze_matchups` também fica: é descritiva, é onde um humano *olha* um roster.

**Resultado.** O veredito não mudou de sinal, mudou de qualidade: passou de um número que
media ruído para um teste. Sobre as 20 sementes, o AG mantém **105 de 186 arestas
decididas — 56,5%, binomial p = 0,091**; os 30 nulos ficam em 49,7% (p = 0,128,
Â₁₂ = 0,63); o NSGA-II dá 4,90/10, o acaso com duas casas. **Indistinguível do acaso**, com
inclinação fraca e não significativa na direção autoral — nem "destruído" nem "preservado".

E apareceu um achado que a resolução antiga escondia: **o canônico também não tem um
ciclo.** Realiza 6/10, e as 4 arestas que quebra são inversões totais (0,000–0,006) — o
Rushdown ganha de todos, a Turtle perde para todos. Tríades circulares: canônico **1,00 de
5** (ordem quase estrita) contra 3,71 do AG e 0,40 dos aleatórios. A estrutura cíclica não
foi destruída pelo equilíbrio; **ela nunca existiu no motor**. Quem produz
não-transitividade é o AG — com a ressalva, já registrada, de que equilíbrio global com
pares decididos a força em boa parte.

Terceira lição de método na mesma direção das duas anteriores
(`IDENTITY_BEHAVIORAL_SIMS` 120 → 200; o piso da sensibilidade medido na estatística
errada): **antes de reportar uma métrica, medir o que ela marca quando não há nada para
marcar.** O espelho fez esse papel aqui, e é por isso que ele entrou no tool novo como
controle de ruído — não como piso de identidade, que é o papel dele no `baselines`.
