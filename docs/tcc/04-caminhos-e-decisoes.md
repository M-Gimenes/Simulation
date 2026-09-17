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
  Contra alvo em `DEFEND` o multiplicador vira `defend_red + grab_power` — soma simples,
  então o teto **inverte** a vantagem de defender em vez de apenas anulá-la.
  Três escolhas de desenho, todas deliberadas: mesmo alcance e mesmo cooldown do ataque
  normal; **efeito nenhum contra quem não defende**; e nunca supera um golpe limpo.
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
  porque cada aresta é cara-ou-coroa.
- **Por que isso importa:** ler `8/21` como "38% da identidade sobreviveu" é o mesmo erro
  que ler 20% numa prova de múltipla escolha de cinco opções como "sabe 20% da matéria".
- **Mudança:** `src/tools/baselines.py` monta canônico + 5 espelhos + N aleatórios e
  reporta cada métrica como `posição = (valor − piso)/(teto − piso)`, com o **pior nulo**
  e um **p-valor empírico** — o piso é uma *distribuição*, não um ponto.
- **Resultado, e duas consequências que entram na tese.** Primeira: o **espelho é a
  solução trivial** de equilíbrio (equilíbrio perfeito, identidade zero) e é a resposta
  numérica à objeção óbvia *"por que não deixar os cinco iguais?"* — medido, o roster
  evoluído alcança 99% do equilíbrio do espelho ficando ~30% acima do piso de identidade.
  Segunda, e mais forte: **o ciclo autoral não pode ser resultado.** Ele é um torneio
  *regular* (cada arquétipo vence exatamente 2), e existem **24** torneios regulares
  rotulados em 5 vértices — acertar o rótulo específico é loteria de 1/24 enquanto o
  acaso já dá 5/10. O que **é** resultado, e não depende de autoria, é a
  **não-transitividade em si**: equilíbrio global e pedra-papel-tesoura são a mesma
  estrutura, porque um roster estritamente transitivo teria WRs 100/75/50/25/0,
  incompatível com todos perto de 50%. Medida por `circular_triads` (Kendall & Babington
  Smith 1940), escala 0 (ordem estrita) · 2,5 (acaso) · 5 (máximo = equilíbrio perfeito).

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
  tempo. `knockback` continua abaixo do piso e segue como limitação declarada.

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
  problema, não defeito). E o que **não** se exige, com a razão: realizar o ciclo (loteria
  de 1/24) e ser equilibrado (seria o problema resolvido de graça). Duas limitações
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
consistentemente fora de um que escapa uma vez por acaso.

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
**reprodução bit-exata** sob o código atual — `results.json` devolve
`fitness = −0,233101660623` sob `generation_seed(42, 150)`, e os 5 representantes do
`nsga2_results.json` devolvem os objetivos gravados. Os demais artefatos são função
determinística desses dois mais o motor, então re-rodar a bateria produziria números
idênticos mais um hash.

**Um efeito colateral vale registrar:** a verificação por reprodução expôs que o
procedimento de checkup antigo (*"re-avaliar o melhor sob seed-base 42 devolve o gravado"*)
é anterior à rotação do stream e **não** vale mais. O número gravado é medido no stream da
**última geração**, `generation_seed(42, 150)`, não no seed-base — sob 42 o `dominance` sai
0,0665 contra 0,0153 gravado, enquanto o `drift`, determinístico, bate exato nos dois
casos. Quem for reproduzir um artefato precisa reproduzir também o *stream*.

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
sim uma caracterização do escalar. A medição sobre as N sementes ainda não foi feita: ela
entra na próxima regeneração da bateria.

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
