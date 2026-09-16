# 04 — Caminhos e decisões de design

**Entra em**: Metodologia (justificativa das escolhas) e Discussão.

> A **trajetória** das decisões — que problema cada mudança resolveu. Não é a
> descrição do estado atual (isso é [`../04-combat-model.md`](../reference/04-combat-model.md) e
> [`../05`](../reference/05-genetic-algorithm.md)); é o **raciocínio** que levou até ele.
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
  pelos pesos. Estado atual em [`../reference/04-combat-model.md`](../reference/04-combat-model.md).

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
  indivíduo um stream diferente, anulando o CRN; substituída.)* Detalhe em
  [05](05-validacao-metodologica.md) e [`../09`](../reference/09-reproducibility.md).

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
  complemento/realismo. Interpretação completa em [03](03-formulacao-do-fitness.md).
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
  não artefato). Interpretação em [03](03-formulacao-do-fitness.md) e
  [02](02-ciclo-canonico.md). **Pesos/cap provisórios — a calibrar.**

## Pesos do fitness

- **`LAMBDA_DRIFT` 6.0 → 1.0.** Problema: com 6.0, mover-se para equilibrar custava ~6×
  o ganho em dominância — o AG escalar ficava **preso ao canônico** (drift ≈ 0) e
  desbalanceado (achado V1). Mudança: 1.0, igual ao dominance. Resultado: o AG é livre
  para usar o objetivo reformulado; e fica **simétrico ao NSGA-II** (que não pondera).
- **`specialization_penalty` removido.** Problema: media spread *intra*-personagem, não
  diferenciação *entre* arquétipos (cinco builds idênticos passariam) — não fazia o que
  o nome diz, era redundante com o drift, e dava ao escalar um 3º termo que o NSGA-II
  não tem. Mudança: removido. Resultado: o AG escalar otimiza **os mesmos dois eixos do
  NSGA-II**; "os 5 ainda são distintos?" virou métrica **post-hoc** (diferenciação
  par-a-par), não termo forçado — coerente com a não-circularidade do ciclo.

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
  entre indivíduos de identidade diferente dobrou. Mas a resposta em
  λ_drift = λ_dom = 1,0 **não mudou** — o AG continua trocando identidade por
  equilíbrio, com as falhas caindo exatamente sobre os genes definidores. Isso é o
  achado, não o bug: é o que empurra a resposta da tese para o **mapa do trade-off**
  (fronteira do NSGA-II) em vez de um ponto único.

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

## O critério de parada do AG (2026-09-16)

- **Problema:** o gate de convergência era `dominance_penalty <= 1e-9`, insatisfazível
  **por construção** — o termo primário é uma RMS sobre contagens discretas, cujo menor
  valor não-nulo é ~0,0015, então `1e-9` significava *exatamente zero*. `converged` era
  sempre `False` e todo o ramo de confirmação era código morto descrito na metodologia.
  Pior: a "reavaliação independente" rodava no **mesmo stream de RNG** do treino, então
  não podia discordar do gate.
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
  (0/49 pontos com `dominance ≥ 1.0`). Com isso o **mapa do trade-off passou a existir**
  — e a leitura da comparação inverteu: o NSGA-II agora vence o AG escalar na função que
  o *escalar* otimiza (L1 0,2115 contra 0,2945), enquanto o escalar alcança um extremo de
  `dominance` (0,0088) abaixo de toda a faixa da fronteira. Não é que um domine o outro:
  cada um alcança uma parte diferente do trade-off.
- **Ponto de método associado:** `select_representatives` ganhou `scalar_optimum`, o
  mínimo da soma ponderada que o escalar otimiza. A comparação vinha usando
  `ideal_point`, que minimiza a norma L2 — outro ponto da mesma fronteira.

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
  Contra alvo em `DEFEND` o multiplicador vira `defend_red + grab_power·(1 − defend_red)`.
  Três escolhas de desenho, todas deliberadas: mesmo alcance e mesmo cooldown do ataque
  normal; **efeito nenhum contra quem não defende**; e nunca supera um golpe limpo.
- **Por que essas escolhas:** é o "efeito nenhum contra quem não defende" que faz do
  agarrão um **counter** em vez de um golpe superior — ele é uma leitura condicional, que
  vale contra quem bloqueia e é peso morto contra quem pressiona. E por ser uma
  condicional na *resolução* e não uma ação escolhida, o modelo de dois canais (postura
  escolhida, ataque por regra) fica intacto: nada de `w_grab` ou quarta postura, que
  teriam mexido de uma vez no espaço de política, na degenerescência de escala dos pesos
  e no drift dos pesos.
- **Resultado:** dano por golpe contra alvo em guarda vai de 16,2 (`grab=0`) a 27,0
  (`grab=1`), exatamente 1,67× = `1/0.6`; diferença zero contra alvo que não defende. O
  validador canônico vai a **23/23**, com os cinco arquétipos tendo assinatura
  comportamental pela primeira vez. Ressalva honesta sobre o sintoma (iii): a aresta
  Grappler×Turtle sai em 100%, mas já saía antes — o Turtle canônico perde para todos
  (WR global 0%). O que mudou é que agora **existe o mecanismo** para ele vencer por
  mérito; se o ciclo emerge disso é pergunta para a bateria.
