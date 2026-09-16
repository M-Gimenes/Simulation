# Revisão de coerência do sistema — pauta

Roteiro da revisão passo a passo de cada etapa do sistema, para verificar se as
escolhas são coerentes entre si e com a pergunta de pesquisa. Aberto em 2026-09-10,
depois de fechar as correções do `HANDOFF.md`. **Auditoria executada em 2026-09-10** —
cada item ganhou uma linha `**Verificado:**` com a medição que sustenta (ou derruba) o
que estava só afirmado.

Não é lista de bugs — é **lista de escolhas a auditar**. Cada item traz o que já foi
observado (fato) separado do que ainda precisa ser decidido (pergunta). Pontos que já
sabemos estar em aberto no sistema seguem em
[`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md); aqui fica o
percurso da auditoria.

**Como usar:** percorrer as etapas na ordem (o de baixo depende do de cima). Ao fechar
um item, registrar a decisão no doc de referência do tema e marcar aqui.

---

## 0. Sumário da auditoria — incongruências por gravidade

Achados que **não** estavam na pauta original ou que a contradizem. Cada um remete à
etapa onde está detalhado.

| # | Incongruência | Etapa | Estado |
|---|---|---|---|
| **M1** | Recuar era forfeit de dano: o `knockback` tinha derivada **negativa** e o Zoner perdia 100% independentemente de range e knockback | §2 | ✅ resolvido |
| **M2** | Sem colisão: os corpos se atravessavam 134× por luta, anulando `range` no clinch | §2 | ✅ resolvido |
| **M3** | `stun` arredondado tinha 4 níveis efetivos para atacante rápido — gene categórico | §2 | ✅ resolvido |
| **D** | KO duplo/timeout empatado premiava sempre o lado A, e o round-robin fixa o índice menor como A | §2 | ✅ resolvido |
| **A** | O AG escalar equilibra **destruindo a identidade** (validador 8/21) e nenhum dos dois medidores de identidade do sistema acusa | §3 | ✅ instrumento corrigido 2026-09-16 (o fenômeno permanece — é o achado) |
| **B** | "O AG vence em `dominance_penalty`" não é "o AG equilibra melhor" — a diferença está no **piso de decisividade**, e o NSGA-II é melhor no termo primário | §4 | ✅ resolvido 2026-09-16 (piso rebaixado + decomposição reportada) |
| **C** | O ponto do AG escalar **não está** na fronteira do NSGA-II: ele a **domina**, justamente no representante usado em toda a comparação | §5 | ✅ resolvido 2026-09-16 (causa: seed canônico imortal no NSGA-II; a dominância some ao removê-lo) |
| **E** | O gate de convergência é inalcançável **por construção** (o termo é quantizado), não só na prática | §4 | ✅ resolvido 2026-09-16 (gate = o próprio critério; confirmação em stream independente) |
| **F** | Holm roda sobre 4 métricas, uma delas degenerada (`p = nan`) — infla a correção nas outras três | §6 | ✅ resolvido 2026-09-16 (família por variância da amostra conjunta; `_holm` recusa `nan`) |
| **G** | A sensibilidade usa dois critérios de corte incompatíveis na mesma saída, e o piso de ruído está subdimensionado | §4 | ✅ resolvido 2026-09-16 (piso medido, critério único, `--evolved`) |
| **H** | O ciclo canônico não é realizado nem pelo próprio canônico (5/10 = nível de acaso) — o baseline não distingue preservação de sorte | §3 | ✅ resolvido 2026-09-16 (o problema era geral: **nenhuma** métrica tinha piso) |
| **R** | **Eixo Recurso sem counter:** DEFEND não tem custo nem quebra de guarda, e o grab ausente é ao mesmo tempo a identidade do Grappler e uma aresta do ciclo | §2 | ✅ resolvido 2026-09-16 (`grab_power`, 8º atributo) |

Menores (sem impacto em resultado, mas sujeira para banca) em §7.

> ⚠️ **`results/` está obsoleto desde 2026-09-10.** As correções M1–M3 e D mudaram o
> motor de combate; todo artefato em `results/` descreve o modelo anterior. A bateria
> completa só deve ser rodada depois de fechar A, B, E e a calibração (H) — ver a
> ordem em §8.

---

## 1. Ambiente e execução

- [ ] **Pool de processos recriado a cada geração.** *Fato:* `fitness.evaluate_population`
  (e o equivalente em `nsga2.py`) cria um `ProcessPoolExecutor` novo por geração, então
  o custo de spawn escala com o nº de workers. Medido nesta máquina, uma geração de 300
  indivíduos: 1w 4,56s | 4w 1,66s | **8w 1,28s** | 12w 1,41s | 16w 1,62s | 20w 1,91s |
  28w 2,77s. Com o default (`None` → 28 núcleos) os processos carregando llvmlite
  estouravam o limite de commit do Windows (`WinError 1455`). Mitigado fixando
  `N_WORKERS = 8`. *Pergunta:* vale trocar por um pool persistente? Ganho provável
  grande, mas exige propagar mudanças de `_SEED_BASE` para workers vivos — plumbing de
  reprodutibilidade.
- [ ] **`N_WORKERS = 8` é específico desta máquina.** *Pergunta:* deixar fixo e
  documentado (hoje), ou derivar de `os.cpu_count()` com teto?
  **Verificado:** a decisão não é respeitada em toda parte — `sensitivity_analysis` tem
  `--workers` com default `None`, que resolve para todos os núcleos e reabre exatamente
  o cenário do `WinError 1455`. Ver §7.
- [ ] **Alinhamento CRN imperfeito depois do 1º matchup.** *Fato:* cada luta consome um
  nº variável de sorteios, então a posição do stream diverge entre indivíduos nos
  matchups seguintes. *Pergunta:* aceitar (documentado) ou semear por
  `(base, matchup_idx, sim_idx)`?
- [x] **O ambiente não sobe sozinho.** *Verificado:* `.venv/` não existia no repositório
  e o Python do sistema (3.14) não tem `numpy`/`numba`/`scipy` — nenhuma tool roda até
  `.\setup.ps1`. Recriado nesta sessão; `requirements.txt` instala limpo em 3.14 e os
  **6 smoke tests passam** (`test_base`, `test_combat`, `test_fitness`, `test_operators`,
  `test_nsga2`, `test_archetype_validator`). Nada a decidir — só não presumir ambiente
  pronto ao retomar.

## 2. Simulação de combate

Auditoria de integridade rodada em 2026-09-10 (varredura de resposta de cada gene em
corpo neutro e nos contextos de projeto, instrumentação por `CombatTrace`,
encurralamento, estagnação e viés posicional). Quatro defeitos encontrados e
corrigidos; o quadro macro do modelo ficou registrado abaixo.

### Corrigido

- [x] **M1 — a intenção sorteada agora vale sempre (fim do ADVANCE incondicional).**
  *Fato:* `_decide_action` impunha ADVANCE sempre que `distance > range`, sobrescrevendo
  a política do personagem. Consequências medidas: um zoner (range 20, speed 2) perdia
  **100%** para um rusher (range 6, speed 5) em **toda** a varredura do próprio `range`
  (5→20: 0,0% em todos os passos) e do próprio `knockback` (0→3: 0,0%); o `knockback`
  tinha derivada **negativa** no corpo neutro (−8,4%), porque empurrar o alvo para fora
  do próprio alcance obrigava o atacante a persegui-lo; e o campo não era o mecanismo
  (`FIELD_SIZE` de 100 a 800 dava 0,0% igual). *Correção:* a intenção governa sempre,
  com a exceção do impasse (abaixo). *Depois:* `range` no corpo neutro subiu de Δ=46,8%
  para **Δ=90,5%** (amplitude a ±1σ de mutação: 36,9% → 49,6%).
- [x] **M1b — ataque virou canal paralelo à postura.** *Fato:* com FRENTE e RECUAR
  mutuamente exclusivos por 10 sub-ticks, recuar era **puro forfeit de dano** — zonear,
  que é atacar segurando espaço, não existia como jogada. *Correção:* a intenção governa
  só a postura (ADVANCE/RETREAT/DEFEND) e o ataque dispara por regra na resolução
  (cooldown pronto + em alcance + postura ≠ DEFEND). *Depois:* zoner×rusher passou de
  0,0% a **49,0%**; a varredura de `knockback` nesse contexto passou de Δ=0,1% (plana)
  a **Δ=44,3% monótona ↑** (27,4% → 71,6%); a de `range`, de Δ=0,0% a Δ=45,0%. O
  conceito de "whiff" deixou de existir.
- [x] **M2 — os corpos não se atravessam mais.** *Fato:* **134 atravessamentos de
  posição por luta** no roster canônico (80.520 em 600 lutas); a distância colapsava
  para ~0 e oscilava, anulando o `range` no clinch. *Correção:* `_apply_movement`
  (helper compartilhado pelos dois JITs) desloca os dois a partir das posições do início
  do sub-tick e os para no ponto de encontro; A é sempre o lado esquerdo. *Ressalva
  levantada na revisão:* o atravessamento era a válvula de escape do encurralamento.
  Medido depois da correção, o canto **não** virou armadilha automática — quem é
  encurralado perde entre 55% e 100% das lutas conforme o par (Zoner×Grappler: preso em
  52% das lutas, perdeu 55% delas), e o knockback de quem está preso empurra o agressor
  para longe. Manter sob observação ao recalibrar os canônicos.
- [x] **M3 — timer de stun contínuo.** *Fato:* `round(stun × round(cd × TICK_SCALE))`
  deixava o gene com **4 níveis efetivos** para `cooldown = 1` (10 para `cd = 3`, 16 para
  `cd = 5`) — categórico, não contínuo; amplitude a ±1σ de apenas 6,8%, e resposta
  não-monótona. *Correção:* `stun_t = stun × attack_cooldown × TICK_SCALE` em float, com
  decremento de 1,0 por sub-tick. *Depois:* Δ no bound inteiro de 17,2% → **53,5%**,
  amplitude a ±1σ de 6,8% → **17,4%**. A invariante "stun < cooldown" continua garantida
  pelo bound `< 1.0` e coberta por teste.
- [x] **D — empate como terceiro desfecho.** *Fato:* HP% igual (KO duplo ou timeout sem
  dano) entregava a vitória ao lado A, e `_run_round_robin` fixa o índice menor como A.
  Medido em espelho (4000 lutas): Rushdown canônico dava **54,90%** para o lado A com
  10,3% de KO duplo (previsto 55,15%); depois de M1, o espelho do Zoner chegou a
  **99,75%** porque a estagnação levava 100% das lutas ao desempate. *Correção:*
  `_decide_winner` devolve `-1`; no round-robin vale meia vitória para cada lado e o
  score por-luta é `0,5`. *Depois:* todos os espelhos voltam a ~50% (neutro 50,3%,
  Rushdown 50,6%, Turtle 50,9%).
- [x] **Anti-estagnação — avanço imposto só no impasse.** *Fato:* com M1 sozinho, dois
  passivos recuavam para paredes opostas e nunca se encontravam: Zoner×Turtle deu
  **100% de timeout** com distância média 87,7. *Correção:* o ADVANCE é imposto apenas
  quando `distance > range_próprio` **e** `distance > range_do_oponente` — impasse puro,
  ninguém alcança ninguém. Quem está sob ameaça segue livre para recuar, então o kite
  não é afetado e a regra não é explorável. *Depois:* **0% de timeout** nos 10 pares
  canônicos.

### Aberto

- [ ] **Hipersensibilidade dos genes de recurso.** *Fato novo:* com o ataque automático,
  a luta virou uma corrida de DPS quase determinística e a resposta ficou muito íngreme
  em espelho — amplitude a ±1σ de mutação: `range` **92,5%**, `attack_cooldown` 65,1%,
  `damage` 55,5%, `hp` 43,6%. Em contrapartida, 71% dos matchups de indivíduos aleatórios
  ficam saturados (WR fora de [5%, 95%]). *Contraponto medido:* o AG lida bem — um AG
  curto (pop 120, 25 gerações, 80 sims) leva o `dominance_penalty` de 1,236 a 0,250, com
  os 5 bonecos em WR global [48,7%, 52,0%] e, o que é novo, **espalhamento real por par**
  (22% · 34% · 36% · 48% · 50% · 50% · 58% · 64% · 70% · 71%) — no motor antigo o evoluído
  ficava achatado em [43,5%, 58%]. *Pergunta:* a inclinação é aceitável (gradiente forte,
  solução frágil) ou precisa de amortecimento — por exemplo variância no dano, ou
  `SIMS_PER_MATCHUP` maior para o cap significar o que diz?
- [x] ~~**Decisividade caiu abaixo do piso.**~~ **Resolvido em 2026-09-16 pelo item (B):**
  era o piso que estava descalibrado, e a premissa dele não valia no motor reformado
  (100% das lutas terminam em KO, então `D` baixo é KO no fio, não luta que não
  aconteceu). `MATCHUP_FLOOR` foi de 0,10 para 0,02 — guarda de degenerescência, não
  banda de qualidade. Ver §4, item (B).
- [ ] **`TICK_SCALE = 5` e `ACTION_PERSISTENCE_SUBTICKS = 10` seguem provisórios.**
  *Pergunta:* qual evidência justifica esses valores? Note a incoerência de escala: a
  persistência (10 sub-ticks) é **maior que o cooldown mínimo** (5 sub-ticks), então um
  personagem de `cooldown = 1` que sorteia GUARDA abre mão de duas janelas de ataque
  inteiras. Com M3 o acoplamento `stun × TICK_SCALE` deixou de ser crítico (o timer é
  contínuo), mas o cooldown segue quantizado em `round(cd × TICK_SCALE)`.
- [ ] **A política é cega ao estado.** A intenção não depende de HP, distância, cooldown
  do oponente nem de o oponente estar stunado: um personagem em GUARDA continua em GUARDA
  enquanto o oponente está indefeso. É o commitment pretendido, mas significa que
  "estratégia" no modelo é uma mistura fixa de três posturas — nenhum arquétipo tem plano.
  *Pergunta:* declarar como escopo (posição atual) ou é o próximo eixo a abrir?
- [x] **(R) O eixo Recurso não tem counter — e o grab ausente é o mesmo problema em três
  lugares.** *Fato:* DEFEND reduz 40% do dano e **não tem custo**: não há chip damage,
  quebra de guarda nem stamina; o único preço é o golpe abdicado. O counter canônico ao
  bloqueio, em qualquer jogo de luta, é o grab — que é exatamente a mecânica ausente do
  Grappler. A mesma lacuna produz três sintomas que hoje são tratados como problemas
  separados:

  1. o **eixo Recurso sem contrapartida** — defender indefinidamente não é punível;
  2. a **Layer 3 do validador com 4 asserções para 5 arquétipos**, porque o Grappler não
     tem assinatura comportamental distinta do corpo-a-corpo do Rushdown
     ([03-archetypes.md](docs/reference/03-archetypes.md), `_BEHAVIORAL_NO_ASSERTION`);
  3. a aresta **"Grappler vence Turtle"** do ciclo canônico — cuja justificativa na
     própria tabela do `CLAUDE.md` é literalmente *"grab é o counter canônico ao
     bloqueio"* — sem realização nenhuma no motor.

  **Decisão registrada (2026-09-10):** entra no escopo, mas **só depois de fechar A, B e
  C** — o eixo pode ficar aceitável sem ele, e mexer no motor de novo antes de a régua de
  fitness estar definida obriga a medir duas vezes.

  *Esboços a avaliar quando chegar a vez (nenhum decidido):*
  - **`grab_power` como gene novo (8º atributo).** Um golpe que ignora o
    `DEFEND_DAMAGE_REDUCTION` — ou o inverte, causando dano **maior** contra quem
    defende. Mais direto e mais fiel à FGC; custo: um gene novo em todos os canônicos,
    nos bounds, no drift, no validador e na recalibração inteira.
  - **Reinterpretar `knockback` como agarrão.** Contra um alvo em DEFEND, o hit ignora a
    redução em vez de empurrar. Sem gene novo, mas sobrecarrega um gene que acabou de
    ganhar função como ferramenta de espaço (§2, M1b) — provavelmente uma má troca.
  - **Custo de guarda sem gene (chip damage).** DEFEND passa a sofrer uma fração pequena
    do dano mesmo bloqueando. Fecha o eixo Recurso com uma constante em `config.py` e
    zero genes novos, mas **não** resolve os sintomas (2) e (3) — o Grappler continua sem
    assinatura própria.
  - **Terceira postura ofensiva.** A intenção FRENTE se divide em "golpe" e "agarrão",
    exigindo um quarto peso `w_grab`. É o desenho mais expressivo e o mais caro: muda o
    espaço de política, a degenerescência de escala e o drift dos pesos de uma vez.

  **✅ Resolvido em 2026-09-16 — `grab_power` como 8º atributo, esboço 1.**

  *Respostas às três perguntas:* **mesmo alcance** e **mesmo cooldown** do ataque normal,
  e **efeito nenhum contra quem não está defendendo**. É a última que faz o desenho: o
  agarrão vira uma **condicional na resolução do ataque**, não uma ação escolhida — então
  o modelo de dois canais (postura escolhida, ataque por regra) fica intacto, sem `w_grab`
  nem quarta postura.

  *Mecânica:* contra alvo em `DEFEND`, o multiplicador do dano vira
  `defend_red + grab_power × (1 − defend_red)`. `grab_power ∈ [0, 1]` é a **fração da
  guarda quebrada**: 0 deixa a redução cheia, 1 a anula. No teto o agarrão **iguala** o
  dano de um golpe limpo — anula a vantagem de defender, não a inverte.

  *Medido* (`test_combat`, alvo sempre em guarda): dano por golpe **16,2 → 27,0**
  (1,67× = `1/0.6`) ao varrer `grab_power` de 0 a 1; e diferença **exatamente zero**
  contra alvo que não defende. O `CombatTrace` ganhou o canal `guard_broken`.

  *Canônicos:* Grappler **0,90** (o especialista), CM 0,30, Rushdown 0,20, Turtle 0,15,
  Zoner 0,05.

  *Os três sintomas:*
  1. **Eixo Recurso** — fechado: defender deixou de ser grátis contra quem tem agarrão.
  2. **Layer 3 com 4 asserções para 5 arquétipos** — fechado: o Grappler ganhou
     `guard_break = maior`, e o validador vai a **23/23** no canônico. Isso importa mais
     do que parecia em 2026-09-10, porque a Layer 3 virou **a régua independente de
     identidade** do projeto na decisão (A).
  3. **Aresta "Grappler vence Turtle"** — *parcialmente*, e vale ser honesto: o Grappler
     vence o Turtle em 100% no canônico, mas isso já era verdade antes do agarrão, porque
     o Turtle canônico perde para todo mundo (WR global 0%). A mecânica agora existe e dá
     ao AG uma alavanca para realizá-la **por mérito**; que o ciclo emerja disso é
     pergunta para a bateria, não coisa fechada aqui. O contador de arestas segue em 5/10
     no canônico — que é o piso do acaso, ver (H).

  *Bônus não previsto:* o Grappler saiu de **um** gene definidor para dois
  (`damage`, `grab_power`), corrigindo a assimetria mais gritante da tabela de premissa.

  *Custo pago:* 8º atributo propagado por bounds, canônicos, drift, validador, viewers e
  testes. Os testes que repetiam a aridade (`== 10 genes`, `== 12 asserções`) passaram a
  **derivar das tabelas**, então o próximo gene não os quebra.
- [ ] **`forced_defend` é suficiente?** RETREAT sem espaço vira DEFEND e o trace separa o
  forçado do escolhido. *Pergunta:* isso basta para as métricas de identidade defensiva,
  agora que o encurralamento passou a ser permanente (sem atravessamento)?

## 3. Representação: genes, arquétipos, canônicos

- [ ] **Canônicos re-tunados são provisórios.** HP, dano e stun dos 5 foram reajustados
  ao novo modelo e nunca calibrados. *Pergunta:* qual o critério para dizer que um
  conjunto canônico está bom? Ele é simultaneamente semente inicial e régua do
  `drift_penalty` — mudá-lo move as duas coisas ao mesmo tempo.
- [ ] **Turtle no teto do bound de HP (450).** *Pergunta:* um canônico colado no bound
  limita a exploração do AG num lado só; é intencional?
  **Verificado:** na prática o AG foi para o **outro** lado — o Turtle evoluído tem
  HP 287,6 (o mínimo do bound é 250). O teto não foi o que restringiu.
- [x] **Normalização do drift usa `x / hi`** (fração do máximo do bound), não
  `(x − lo) / (hi − lo)`. *Pergunta:* a escolha é deliberada? Ela faz genes com `lo`
  alto (ex.: HP, mín 250) parecerem menos deslocados do que estão.
  **Verificado:** o efeito é de **1,3×** no indivíduo evoluído — `drift_penalty` 0,2607
  com a normalização atual contra 0,3417 com `(x − lo)/(hi − lo)`. O maior desvio
  individual é o do Turtle: 0,2894 → 0,4535 (o HP 450→288 conta como −0,36 hoje e −0,81
  na normalização por range). A convenção atual **subestima sistematicamente** o desvio
  dos genes de `lo` alto — e é justamente neles que o AG se moveu mais.
  **✅ Corrigido em 2026-09-16:** `(x − lo)/(hi − lo)` em `fitness.gene_drift`, na Layer 2
  do validador e no `drift_table` — uma definição só de "normalizado" no projeto. Não é
  cosmético: é essa troca que conserta a **ordenação** entre indivíduos por identidade
  (ver item (A) logo abaixo), independentemente da ponderação. Efeito colateral medido: a
  diferenciação par-a-par do indivíduo evoluído cai de `ratio` 0,92 para 0,82 — o medidor
  de homogeneização também estava subestimando.
- [x] **🔴 (A) O AG equilibra destruindo a identidade — e nenhum medidor do sistema
  acusa.** *Fato novo.* Validador de identidade (21 asserções de ranking) contra a
  `dominance_penalty` fora do laço:

  | indivíduo | dominance (fora do laço) | validador | drift | diferenciação |
  |---|---|---|---|---|
  | canônico | 1,4162 | **21/21** | 0,000 | 1,00 |
  | melhor do AG escalar | 0,0279 | **7/21** | 0,261 | 0,92 |
  | NSGA-II `knee_point` | 0,3443 | **20/21** | 0,089 | 0,96 |
  | NSGA-II `best_dominance` | 0,1148 | **13/21** | 0,271 | 0,96 |
  | NSGA-II `ideal_point` | — | 16/21 | 0,155 | — |

  > **Números desta tabela são a medição de 2026-09-10**, sob a normalização `x/hi`, que
  > foi corrigida em 2026-09-16 — as colunas `validador` (a Layer 2 usa a mesma
  > convenção), `drift` e `diferenciação` mudaram de valor. Re-medidos: validador
  > `knee_point` 19/21, `ideal_point` 16/21, `best_dominance` 11/21, AG escalar 8/21;
  > drift 0,1279 / 0,2054 / 0,3150 / 0,3579; diferenciação do AG 0,92 → 0,82. A
  > **ordenação** entre os indivíduos não muda em nenhuma das colunas; os números, sim.

  O que o AG fez com os genes: Turtle HP 450→288 e dano 15→28 (a "muralha viva" virou o
  boneco de **menor** HP e **maior** dano); Rushdown speed 5,0→2,7 e `w_aggressiveness`
  0,90→0,10 (o agressivo virou defensivo); Zoner range 18→9 (o de maior alcance virou o
  de **menor**); Combo Master perdeu o rank 1 de stun. Quatro dos cinco convergiram para
  dano 24–28 (topo do bound) e HP 284–291 (fundo do bound).

  **O problema não é o resultado — é que os dois instrumentos de identidade do projeto
  não o detectam:**
  - `drift_penalty` dá **0,261 para o AG e 0,271 para o `best_dominance`** — praticamente
    empatados, enquanto o validador dá 8/21 contra 11/21. Drift é distância euclidiana
    média sobre 10 genes: dilui um Turtle que perdeu 162 HP em sete genes que quase não
    mexeram. É cego à **estrutura de ranking**, que é o que "identidade" significa
    operacionalmente aqui (o Zoner deixar de ser o de maior range é uma asserção perdida
    e ~0,44 de desvio normalizado num gene só).
  - a **diferenciação** do `drift_table` dá **0,92** ("~1 = diferenciação preservada").
    Ela mede distância média par-a-par entre os 5 — e os 5 continuam espalhados. O que
    aconteceu não foi homogeneização: foi **troca de papéis**. A métrica mede
    espalhamento, não correspondência, e por isso não vê.

  *Consequência direta para a pergunta de pesquisa:* no ponto λ_drift = λ_dom = 1,0 a
  resposta a "dá pra equilibrar sem destruir as identidades?" é **não** — e o termo
  descrito no CLAUDE.md e em `docs/tcc/03` como "o real mecanismo anti-homogeneização"
  não é sensível ao fenômeno que deveria conter.
  **✅ Decidido em 2026-09-16 — duas réguas, uma de cada lado da linha premissa/resposta.**
  A discussão de origem era "o AG não devia ter influência em preservar identidade, senão
  a pergunta fica circular". A preocupação é válida como princípio, mas mira o alvo
  errado: o projeto **já** tinha identidade no fitness por decisão explícita
  (`LAMBDA_DRIFT = 1.0`, "penalized but never hard-constrained"), e a linha de
  não-circularidade separa **premissa** (o que cada arquétipo É — canônicos e genes
  definidores; pode entrar no fitness) de **resposta** (quem vence quem; se equilíbrio e
  identidade são compatíveis — nunca entra). "O Zoner é definido por alcance" é premissa;
  "o Zoner deve vencer o Grappler" é resposta. Some-se o argumento empírico: com a
  penalidade ligada o run inteiro, o AG **mesmo assim** destruiu a identidade (8/21) —
  penalidade não é restrição, o termo existe e pode perder. E tirar drift do fitness
  mataria o braço NSGA-II inteiro (uma fronteira de Pareto precisa de dois objetivos).

  O problema real não era "identidade no fitness", era **os dois instrumentos discordarem
  sobre o que a palavra significa**. Arquitetura adotada:
  - **identidade estrutural** — `drift_penalty`, **no fitness**: normalizado pelo range do
    bound e ponderado pelos `defining_genes` (campo congelado novo em
    `ArchetypeDefinition`, espelhando as asserções inter da Layer 1).
    `DRIFT_DEFINING_WEIGHT = 3.0`.
  - **identidade funcional** — Layer 3 do validador + ciclo de vantagens, **post-hoc,
    nunca no fitness**. Nada no fitness referencia comportamento. A pergunta da tese diz
    literalmente *"functional identities"* — é essa a régua que a responde.
  - bookkeeping honesto: as Layers 1-2 passam a ser **parcialmente endógenas** (medem o
    eixo que o fitness otimiza) e estão marcadas como tal no tool e nos docs. A Layer 3 é
    held-out, não insulada — comportamento é downstream dos genes que o fitness move.

  **Verificado (o instrumento).** A ordenação por drift agora bate com a do validador em
  todos os pesos testados. Quem conserta isso é a **normalização**: com `x/hi` o AG dava
  0,2607, *abaixo* do `best_dominance` (0,2709), invertendo 8/21 contra 11/21. A
  **ponderação** alarga a margem (gap AG−best_dom 0,017 uniforme → 0,043 em peso 3,0 →
  0,073 em peso 12, saturando). Tabela completa em
  [`docs/reference/05-genetic-algorithm.md`](docs/reference/05-genetic-algorithm.md).

  **Verificado (o fenômeno permanece).** AG curto sob o fitness novo (pop 120, 25
  gerações, 80 sims/par, seed 42): dominance 0,0896 (global 0,0816 | cap 0,0160 | decis
  0,0000), drift 0,2973, WR global em [43,7%, 56,1%], WR por par de 34% a 66% — e
  validador **estrutural 7/17, completo 10/21**, com as falhas caindo exatamente sobre os
  genes definidores (os 3 do Rushdown, os 3 do Zoner, 3 dos 4 do Turtle). A régua ficou
  afiada; a resposta em λ_drift = λ_dom = 1,0 **não mudou**. É o achado, não o bug — e
  reforça que o mapa do trade-off (fronteira do NSGA-II, e possivelmente um sweep de
  `LAMBDA_DRIFT`) é onde a resposta da tese vive. *Atualização de (C):* com o seed
  canônico fora do NSGA-II a fronteira passou a cobrir a faixa de drift [0,080, 0,301]
  com dominance de 0,0346 a 0,9585 — ou seja, o mapa do trade-off agora existe de fato,
  e é nele que essa pergunta deve ser respondida.

  *Segue aberto (redação):* `\valAg = 7` já
  está no `values.tex`: a redação assume esse número como resultado, enquanto o
  `drift_penalty` do mesmo indivíduo é lido como "identidade preservada a 0,26" — as
  duas leituras não podem coexistir no texto. Com as duas réguas nomeadas
  (estrutural vs funcional) a contradição some, mas o texto precisa ser reescrito
  (§6 / passo 9 da ordem).
- [ ] **🟡 (H) O canônico não realiza o próprio ciclo de vantagens.** *Fato novo:*
  medido sob a semente 9999 com 200 sims, o roster canônico dá WR global Rushdown
  **100%**, Turtle **0%**, Zoner 25%, Grappler 73%, CM 52%; 10/10 pares são
  hard-counter; e o ciclo canônico é mantido em **5 de 10 arestas** (Zoner×Grappler,
  Rushdown×Grappler, Rushdown×Turtle, CM×Grappler e CM×Turtle saem invertidos).
  Arestas mantidas: canônico 5/10, AG 5/10, `knee_point` 5/10, `best_dominance` 6/10 —
  todos no nível do acaso.
  **✅ Resolvido em 2026-09-16 — e o item era maior do que parecia: o problema não é do
  ciclo, é de TODAS as métricas post-hoc.**

  **(1) Por que calibrar o ciclo é perseguir uma loteria.** O ciclo canônico é um torneio
  **regular** — cada arquétipo vence exatamente 2 e perde 2 (verificado em
  `test_baselines`). Existem **24** torneios regulares rotulados em 5 vértices, então
  acertar o rótulo específico é 1/24 ≈ 4,2%; e como cada aresta é cara-ou-coroa, o acaso
  já entrega 5/10. O sucesso da calibração não distinguiria preservação de sorte — o
  alvo é inatingível como *evidência*, independentemente de ser atingível como *valor*.

  **(2) O achado maior: nenhuma métrica tinha piso.** Medido com 13 rosters nulos
  (5 espelhos + 8 aleatórios), seed 9999, 150 sims:

  | métrica | piso médio | pior nulo | teto |
  |---|---|---|---|
  | validador (L1-L3) | ~6,8/21 | **12/21** | 21/21 |
  | validador (L1+L2) | ~5,8/17 | 10/17 | 17/17 |
  | `drift_penalty` | 0,408 (aleatório) · 0,326 (espelho) | 0,326 | 0,000 |
  | arestas do ciclo | 5/10 (analítico) | 8/10 | 10/10 |

  Um roster **aleatório** tirou 12/21 no validador; cinco personagens **idênticos**
  (identidade zero por construção) tiram 7–10/21, porque asserção de ranking com empate
  se resolve por ordem de índice e algumas acertam por acidente. Ler `8/21` como "38% da
  identidade sobreviveu" é o erro de ler 20% numa prova de cinco alternativas como
  "sabe 20% da matéria". Pior: entre drift 0,287 (evoluído) e 0,326 (todos idênticos) há
  **0,04** — a régua central da tese quase não distingue preservação de aniquilação.

  *Correção:* `src/tools/baselines.py` monta canônico + 5 espelhos + N aleatórios e
  reporta cada métrica como `posição = (valor − piso)/(teto − piso)`, com o **pior nulo**
  e um **p-valor empírico** (fração dos nulos que igualam ou superam). O piso é
  distribuição, não ponto.

  *Veredito sobre os indivíduos existentes:* o do `results.json` está **no piso** em todos
  os eixos de identidade (p = 0,46 / 0,38 / 0,23) — indistinguível de um roster aleatório
  — e **abaixo** do acaso no ciclo (4/10, p = 0,85). O AG sob o motor/fitness novos fica
  em 99% do equilíbrio trivialmente alcançável e ~30% acima do piso de identidade
  (p ≈ 0,08 com 13 nulos: sugestivo, não estabelecido).

  **(3) O espelho responde a objeção que estava em aberto.** Cinco personagens idênticos
  são a solução **trivial** do problema de equilíbrio, e eles equilibram *melhor* que o
  roster evoluído (dominance 0,02–0,05 contra 0,049). A pergunta "por que não deixar
  todos iguais?" agora tem resposta numérica em vez de retórica, e os cantos degenerados
  podem ser marcados no gráfico da fronteira de Pareto.

  **(4) O que substitui o ciclo como métrica de estrutura.** Tríades circulares
  (Kendall & Babington Smith 1940), escala 0 (ordem estrita) · 2,5 (acaso) · 5 (máximo).
  O máximo **é** o torneio regular, que **é** equilíbrio global perfeito: um roster
  estritamente transitivo tem WRs 100/75/50/25/0, incompatível com todos perto de 50%.
  Ou seja **equilíbrio global não é achatamento — ele força não-transitividade**. Isso é
  demonstrável e não depende de autoria. O AG novo dá 3,0 tríades com pares em 34%–66%
  (arestas decididas, contagem válida). Ressalva coberta por teste: o ciclo **invertido**
  dá 0/10 arestas e ainda 5 tríades — a estrutura sobrevive à troca de rótulos, que é
  exatamente por que o rótulo não é o achado.

  *Não decorre disto nenhuma necessidade de recalibrar os canônicos:* eles não precisam
  realizar o ciclo nem ser equilibrados (serem desequilibrados é o ponto de partida do
  problema). O que precisavam era de um piso contra o qual serem lidos.

## 4. Fitness e dados

- [x] **🔴 (E) O gate de convergência do AG é inalcançável — por construção, não só na
  prática.** *Fato:* `ga.run` só testa convergência quando `dominance_penalty <= 1e-9`;
  na execução seed 42 o mínimo em 150 gerações foi **0,0052**.
  **Verificado:** é mais forte que "seis ordens de grandeza". `global_term` é uma RMS de
  `|WR − 0,5|/0,5` sobre contagens discretas: com 4 × 150 = 600 lutas por personagem, o
  menor valor **não-nulo** possível é `(1/600)/0,5/√5 ≈ 0,0015`. Não existe continuum
  entre 0 e 0,0015 — o gate em `1e-9` significa **exatamente zero**, isto é, os 5
  personagens com WR exatamente 300/600 na mesma avaliação, simultaneamente. Portanto
  `converged` é `False` por construção, e todo o ramo de confirmação
  (`SIMS_CONVERGENCE_CHECK`, `character_balanced`, `is_hard_counter` dentro de `ga.run`)
  é **código morto** — está descrito na metodologia e nunca executa.
  **✅ Resolvido em 2026-09-16 — o gate virou o próprio critério, e a confirmação virou
  independente.**

  **(1) O gate deixou de ser um limiar escalar.** Agora é `roster_balanced(best_detail)`:
  o mesmo predicado da confirmação, aplicado à avaliação do laço que já está em mãos
  (custo zero). `roster_balanced` (novo, em `fitness.py`) é *todo personagem em banda
  global* **e** *nenhum par counter duro* — a definição de equilíbrio do projeto, agora
  em um lugar só, consumida pela convergência do AG, pelo veredito por semente do
  `multi_run` (que tinha uma cópia inline) e pelo reporting.

  Por que não um limiar escalar calibrado: o composto inclui o `decis_term`, que **não
  faz parte da definição de convergência**. Um roster genuinamente convergido (5/5 em
  banda, 0 counters) mas com lutas decisivas teria dominance alto e seria barrado — a
  mesma classe de defeito do `1e-9`, só mais branda. Testar o predicado direto não tem
  essa lacuna.

  **(2) Achado novo no mesmo item: a confirmação não confirmava nada.** `ga.run` faz
  `set_seed_base(seed)` e `evaluate_detail_n` **resseta ao mesmo base** — a "reavaliação
  independente" rodava 200 sims em vez de 150 **no mesmo stream de RNG**. CRN é o certo
  para *seleção* (a diferença de fitness reflete genes, não sorteio) e errado para
  *validação*: mede a mesma realização do RNG com mais amostras, e o gate não pode
  discordar da confirmação. Medido no indivíduo que convergiu:

  | stream | equilibrado? | bonecos em banda | counters duros |
  |---|---|---|---|
  | treino (42) — o que a confirmação usava | **sim** | 5/5 | 0 |
  | 9999 | não | 5/5 | 1 |
  | 10000 / 10001 / 10002 | não | 5/5 | 2 |

  Note que o que quebra é sempre o **counter duro**, nunca o equilíbrio global — o ajuste
  ao stream se concentra no par-a-par, coerente com o item do piso de ruído abaixo.

  *Correção:* a confirmação passa a usar `seed + CONVERGENCE_SEED_OFFSET` (100000,
  escolhido para não colidir com treino 42+, `MULTI_RUN_VALIDATION_SEED` 9999 nem
  `EXTERNAL_VALIDATION_SEED_START` 10000+). Convergir passa a significar **"o equilíbrio
  sobrevive a um stream que o AG nunca viu"**, e o `best_detail` devolvido pelo AG passa
  a ser uma medição fora da amostra. Consequência esperada e aceita: convergência fica
  bem mais rara, e o headline "X% das execuções convergiram" cai — mas passa a significar
  alguma coisa. Medido num run curto (pop 120, 60 gerações, seed 42): o gate disparou
  **16 vezes** e a confirmação fora do stream rejeitou **as 16** — o mesmo indivíduo que,
  sob a confirmação antiga, teria "convergido" na geração 30. **E o critério é
  alcançável:** na medição de (C) com 150 gerações (pop 120, 80 sims, seed 42) o AG
  parou por **convergência**, com o equilíbrio confirmado num stream que ele nunca viu.
  Não é um critério inatingível trocado por outro — é um critério que agora exige
  convergência de verdade.
- [x] **`dominance_penalty` abaixo do piso de ruído: há ajuste ao stream, mas o
  equilíbrio sobrevive.** *Fato:* com 150 sims/matchup o desvio binomial da WR global
  (600 lutas) é ~2%, o que daria um `global_term` da ordem de 0,03 — e o AG chegou a
  0,0076 no laço, indicando adaptação à realização específica do RNG fixada pelo CRN.
  Fora do laço (`external_validation`, sementes 10000+, 500 sims) o mesmo indivíduo dá
  **0,0279 ± 0,0062**: degrada ~3,7×, mas mantém 5/5 bonecos em banda em todas as 10
  condições e **0/10** hard-counters — veredito **ROBUSTO**. *Conclusão:* o ajuste ao
  stream existe e precisa ser declarado, mas não é o que sustenta o resultado. Reportar
  sempre o número **fora** do laço.
- [x] **🔴 (B) O `dominance_penalty` composto esconde de onde vem a diferença entre os
  algoritmos.** *Fato novo:* decomposição nos três termos (semente 9999, 200 sims):

  | indivíduo | `global` (peso 1,0) | `cap` (0,5) | `decis` (0,5) | total |
  |---|---|---|---|---|
  | canônico | 0,7019 | 0,9795 | 0,4529 | 1,4181 |
  | melhor do AG | 0,0406 | 0,0000 | 0,0029 | **0,0421** |
  | NSGA-II `best_dominance` | **0,0327** | 0,0226 | 0,1788 | **0,1334** |

  O NSGA-II é **melhor que o AG no termo primário** (0,0327 < 0,0406). Ele perde por duas
  coisas secundárias: um hard-counter (Zoner×Grappler a 67,5%) e sobretudo o **piso** de
  decisividade — suas lutas ficam *fechadas demais* (decisividade por par 0,065–0,105
  contra `MATCHUP_FLOOR = 0,10`), enquanto o AG fica colado no piso (0,099–0,135).
  *Consequência:* a frase do `HANDOFF` "o AG escalar vence em `dominance_penalty`" está
  correta como número e errada como leitura — não é "o AG equilibra melhor", é "o AG
  produz lutas menos apertadas".
  **✅ Resolvido em 2026-09-16 — as duas metades.**

  **(1) O piso virou guarda de degenerescência: `MATCHUP_FLOOR` 0,10 → 0,02.** A premissa
  por trás do piso ("abaixo dele é quase-empate, luta que não aconteceu") **não vale no
  motor reformado**. Medido: **100% das lutas terminam em KO** em 70 pares — canônico, AG,
  os dois representantes do NSGA-II e três rosters aleatórios, sem uma única exceção.
  Então `D` baixo nunca é "a luta não aconteceu": é KO no fio, que é a melhor luta
  possível. O piso estava punindo exatamente o desfecho que o projeto quer.

  Faixas medidas para calibrar o guarda:

  | regime | como é produzido | `D` |
  |---|---|---|
  | degenerado | HP máx / dano mín / GUARDA total — 0% de KO, timeout com HP idêntico | **≤ 0,008** |
  | espelho puro | cada canônico contra si mesmo (par perfeitamente equilibrado por construção) | **0,020 – 0,033** |
  | pares reais | 70 pares dos 7 indivíduos medidos | **≥ 0,045** |

  O piso em **0,02** fica na base da faixa do espelho — abaixo do que dois personagens
  **idênticos** produzem. Efeito isolado sobre os mesmos dados: a 0,10 o piso penalizava
  5/10 (AG), 5/10 (`knee_point`) e 3/10 (`best_dominance`) pares; a 0,02 penaliza
  **0/10 em todos**. O `decis_term` do AG cai de 0,1179 para 0,0577 — o resto é todo teto,
  que é o guarda legítimo. No AG curto sob o fitness novo, os 10 pares deram `D` entre
  0,045 e 0,072 e o `decis_term` saiu **exatamente 0,0000**.

  **(2) Os três termos passam a ser reportados separados.** `_dominance_penalty` devolve
  um `DominanceTerms` guardado no `FitnessDetail`; o `multi_run` grava os três por semente
  e agregados e os imprime indentados sob o composto; o `compare_algorithms` imprime a
  decomposição lado a lado com a mediana de cada algoritmo. É **descritiva** e fica
  deliberadamente **fora** da bateria de Mann-Whitney — acrescentar métricas ali inflaria
  a correção de Holm sobre as que já estão lá (item F). Artefatos antigos sem
  `dominance_terms` agora falham com mensagem explícita pedindo para regerar, em vez de
  `KeyError`.

  *Segue aberto:* os **pesos** 1,0 / 0,5 / 0,5 continuam nunca variados (item abaixo).
- [ ] **`MATCHUP_WR_CAP = 0.15` provisório.** Define o que é "counter duro" e portanto
  quanto do ciclo de vantagens cabe no espaço permitido. *Pergunta:* há justificativa de
  domínio (FGC) para 15 pontos percentuais, ou é preciso um sweep?
  **Verificado (motor antigo):** no indivíduo evoluído o `cap_term` era **exatamente 0** —
  os 10 pares ficavam em [43,5%, 58,0%]. O teto nunca chegava a morder.
  **Revisto (motor reformado, 2026-09-16):** o quadro mudou — o AG curto sob o fitness
  novo espalha os pares de 34% a 66% e o `cap_term` sai **0,0160**, ou seja o teto agora
  morde. Faz sentido: a reforma do combate abriu espaço para vantagem par-a-par, que é
  justamente o que o cap regula. Ele voltou a ter função, e o sweep volta a fazer
  sentido — fica para a calibração (H).
- [ ] **Pesos 1.0 / 0.5 / 0.5 dos três termos do dominance.** Nunca variados.
  *Pergunta:* o que muda na fronteira ao mexer neles? (ver (B): hoje o termo com peso
  0,5 de decisividade é o que decide a comparação entre algoritmos).
- [ ] **A análise de sensibilidade mede no ponto errado do espaço.** *Fato:* ela roda
  fixa no **canônico** (`Individual.from_canonical()` está hardcoded em `_eval_task`, o
  tool não tem `--evolved`/`--nsga2`), e o canônico é saturado — Rushdown ganha 100% de
  tudo, Turtle 0%, 10/10 hard-counters. Com a WR presa no teto, perturbar um gene não
  muda nada, e o resultado é que **6 dos 7 atributos saem classificados como "neutros"**
  (só `attack_cooldown`, 5,6%, passa do piso de 1,8%). Isso é **efeito de teto**, não
  neutralidade de gene. *Pergunta:* a tabela precisa ser medida também num indivíduo
  equilibrado (evoluído / knee) para sustentar a afirmação "o AG enxerga o cromossomo";
  do jeito que está, ela sustenta o contrário do que se quer afirmar.
  **Verificado:** confirmado no artefato (WR global canônica 100%/0% reproduzida).
- [x] **🟡 (G) A sensibilidade usa dois critérios de corte incompatíveis, e o piso está
  subdimensionado.** *Fato novo:* `_classify` usa limiares fixos (≥5% visível, <3%
  neutro, entre os dois "borderline") enquanto a saída imprime um "piso de ruído
  binomial" de 1,77% que **não entra na classificação** — dois critérios diferentes na
  mesma tabela. Pior: o piso é o desvio de **uma** proporção (`√(0,25/800)`), mas o
  número classificado é uma **diferença** entre duas WRs (+σ e −σ). Mesmo com o
  pareamento CRN, o piso correto para uma diferença é maior (até √2× se as duas fossem
  independentes). **✅ Resolvido em 2026-09-16 — o piso passou a ser MEDIDO, e a classificação sai dele.**

  Em vez de estimar o piso analiticamente (e não usá-lo), o tool roda a própria maquinaria
  sob a hipótese nula: `|Δ WR|` entre **duas avaliações do mesmo roster, sem perturbação
  nenhuma**, sob seeds diferentes (`--null-reps`). Aí o Δ verdadeiro é zero por construção,
  então tudo que aparece é ruído de amostragem — exatamente na grandeza que a tabela
  classifica, que é uma **diferença** e não uma proporção. Critério único: `≤ piso` =
  neutro, `≤ 2× piso` = borderline, acima = visível.

  *Detalhe que quase passou:* as duas metades do par nulo precisam de **seeds diferentes**.
  Com a mesma seed e perturbação zero as avaliações são bit-idênticas e o Δ sai exatamente
  0 — não mediria nada. Quebrar o pareamento de propósito dá um piso **conservador** (a
  medição real usa CRN pareado e tem menos ruído); superestimar o piso torna a
  classificação mais exigente, que é o lado seguro.

  *Bug encontrado no caminho:* `_deltas_from` distinguia as metades do par pelo **sinal do
  deslocamento**, então com deslocamento zero as duas eram subtraídas (`−wr − wr`) e o piso
  saía em 200%. O sinal virou campo próprio da task.

  **Também resolvido o ponto de medir no lugar errado** (item acima): o tool ganhou
  `--evolved` / `--nsga2`, passando os genes na task em vez de chamar
  `Individual.from_canonical()` dentro do worker. A tabela do canônico segue disponível,
  agora rotulada como saturada na própria saída.

  **E o menor do `--workers`** (§7): o default virou `N_WORKERS` em vez de `None`, que
  resolvia para todos os núcleos e reabria o `WinError 1455`.
- [ ] **`SIMS_PER_MATCHUP = 150` vs as bandas de decisão.** Ruído binomial por matchup
  ~4% contra um cap de 15%. *Pergunta:* a margem é confortável o bastante, ou o número
  de sims precisa subir para o cap significar o que diz?

## 5. AG escalar e NSGA-II

- [ ] **Escalar e NSGA-II não param pelo mesmo critério.** O AG tem convergência +
  estagnação + teto; o NSGA-II roda `NSGA2_GENERATIONS` fixas. *Pergunta:* a assimetria
  é intencional? Ela afeta a comparação entre os dois.
  **Verificado (2026-09-10):** na prática a assimetria era menor do que parecia — a
  convergência do AG nunca disparava (§4/E) e na seed 42 ele também bateu o teto de 150
  gerações. A assimetria era de **descrição**, não de execução.
  **Revisto (2026-09-16):** com o gate de convergência corrigido a assimetria virou real
  — na medição de orçamento igual (pop 120, 150 gerações, seed 42) o AG **parou por
  convergência**, com o critério confirmado num stream que ele nunca viu, enquanto o
  NSGA-II rodou as 150 gerações fixas. *Pergunta reaberta:* comparar um algoritmo que
  para por critério com outro que para por orçamento exige declarar o que está sendo
  comparado — qualidade final sob orçamento igual, ou custo até atingir um critério?
- [x] **🔴 (C) O ponto do AG escalar não está na fronteira do NSGA-II — ele a domina.**
  *Fato novo, mesma condição para os dois (seed-base 42, 150 sims/matchup, exatamente
  como cada um foi avaliado no seu laço):*

  | ponto | dominance | drift | soma (L1) |
  |---|---|---|---|
  | **melhor do AG escalar** | **0,0076** | **0,2607** | **0,2683** |
  | NSGA-II `best_dominance` | 0,1063 | 0,2709 | 0,3772 |
  | NSGA-II `ideal_point` (mín L2) | 0,1986 | 0,1554 | 0,3540 |
  | NSGA-II `knee_point` | 0,3411 | 0,0885 | 0,4296 |
  | NSGA-II mín L1 da fronteira | 0,1234 | 0,2204 | 0,3438 |

  O ponto do AG **domina no sentido de Pareto** (melhor nos dois eixos) o
  `best_dominance` — que é exatamente o representante usado no `multi_run` e no
  `compare_algorithms`. A fronteira nunca chega a `dominance < 0,106`: só **27 dos 300**
  pontos têm `dom < 0,30` e **6** têm `dom < 0,15`; 84 dos 300 são duplicatas (216
  distintos). O `best_drift` da fronteira é o **próprio seed canônico** (drift 0,0000,
  dominance 1,4154), inalterado nas 150 gerações.

  *Diagnóstico provável:* colapso de pressão seletiva. O `front_sizes[0]` chega a
  **300/300 na geração 138** — com a população inteira em rank 0, o
  `nsga2_binary_tournament` decide só por *crowding distance*, que premia
  **espalhamento**, não qualidade; e `_select_next_population` trunca por crowding,
  favorecendo os extremos. A partir daí o NSGA-II para de convergir e passa a espalhar.

  *Consequência:* a afirmação central "o escalar é **um ponto** do trade-off que o
  NSGA-II mapeia" (CLAUDE.md, `docs/tcc/03`, `10-known-issues.md`) é **falsa nesta
  bateria** — o ponto do escalar está fora e melhor.
  **✅ Resolvido em 2026-09-16 — a causa não era colapso de front0, era o seed canônico.**

  **O diagnóstico do "colapso de pressão seletiva" estava errado.** A causa real é uma
  assimetria entre os dois objetivos: **`drift` tem piso 0 e o piso é alcançável** — o
  canônico *é* a referência, drift exatamente 0,0000 — enquanto o piso de `dominance` não
  é. Dominar `(1,2418, 0,0000)` exigiria `drift < 0`, que não existe. Logo o seed
  canônico é **imortal no rank 0**, por pior que seja o equilíbrio dele, e a mesma
  proteção se estende à vizinhança de drift ~0. O crowding não corrige porque só poda
  quando um front **transborda** a população, e front0 (78) nunca passou de 120.

  Medido sob o motor e o fitness atuais (pop 120, 60 gerações, 80 sims, seed 42 — a única
  diferença entre as colunas é a população inicial):

  | | com seed canônico | sem seed canônico |
  |---|---|---|
  | min `dominance` da fronteira | 0,2233 (estagnado) | **0,0896** (ainda caindo na gen 50) |
  | pontos com `dominance ≥ 1.0` | **40/78** | 1/44 |
  | front0 na geração 50 | 89/120 | 31/120 |
  | drift coberto | [0,000, 0,161] | [0,124, 0,300] |
  | queda do min dominance | 1ª metade −0,3970 · 2ª metade −0,0338 | monótona, sem platô |

  Metade da fronteira eram rosters tão desequilibrados quanto o canônico intocado,
  consumindo um terço da população **e um terço do esforço reprodutivo**. E a fronteira
  com seed nunca alcançava a região de drift ~0,29 onde moram as soluções equilibradas.

  *Correção:* o NSGA-II passa a iniciar com população 100% aleatória. No **AG escalar o
  mesmo seed ajuda** e por isso fica — lá o fitness é um número só, o canônico é ruim nele
  e some depois de doar genes (medido: com seed drift 0,2874, sem seed 0,3365, mesmo
  dominance). A assimetria é deliberada e está declarada em
  [`docs/reference/06-nsga2.md`](docs/reference/06-nsga2.md).

  *Verificado no orçamento real (150 gerações):* a nuvem **não reaparece** — 0/49 pontos
  com `dominance ≥ 1.0`, 0 imortais de drift ~0, min dominance 0,0346. O min drift desce
  sozinho (0,2934 → 0,0804) porque o NSGA-II seleciona por drift baixo, mas os pontos
  chegam lá **com dominance razoável** (máx da fronteira 0,9585), sem formar nuvem. Ou
  seja: o acúmulo vinha do seed, não da dinâmica — nenhum mecanismo novo é necessário.
  Se reaparecer em outro regime, a lista em ordem de intervenção é supressão de
  duplicatas → ε-dominância (Laumanns et al. 2002) → NSGA-II com restrições (Deb 2002 §VI).

  **(c) O comparável de mínimo L1 agora existe.** `select_representatives` extrai
  `scalar_optimum` = mínimo de `LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift`, a mesma
  função que o escalar otimiza. É o único ponto do NSGA-II que lê os `LAMBDA_*`, e é
  reporting, não busca. O `ideal_point` (mín L2) continua como ponto geométrico.

  **Resultado final, orçamentos iguais (pop 120, 150 gerações, 80 sims, seed 42):**

  | | dominance | drift | L1 |
  |---|---|---|---|
  | AG escalar | **0,0088** | 0,2856 | 0,2945 |
  | `scalar_optimum` da fronteira | 0,0481 | 0,1634 | **0,2115** |

  A alegação "o ponto do escalar domina a fronteira" **deixou de valer**: ele domina 3 de
  49 pontos, nenhum ponto o domina, e o NSGA-II agora **vence o escalar na própria função
  que o escalar otimiza**. A frase "o escalar é *um ponto* do trade-off que o NSGA-II
  mapeia" continua não sendo literalmente verdadeira, mas por outro motivo: o escalar
  alcança `dominance` 0,0088, **abaixo de toda a faixa da fronteira** [0,0346, 0,9585],
  então ele fica *além* da ponta de dominance dela, não fora por sub-convergência. Cada
  algoritmo alcança uma parte diferente do trade-off, e nenhum está sub-convergido.
- [ ] **Sweep de `LAMBDA_DRIFT` nunca feito.** É a demonstração de que o escalar é *um
  ponto* do trade-off. Hoje isso é afirmado, não medido — e por (C) a afirmação está
  contradita pela única bateria existente. É o experimento mais urgente da lista.
- [ ] **Crossover só por bloco de personagem.** Recombinação intra-personagem depende
  100% da mutação. *Pergunta:* limitação aceita e declarada, ou vale testar um crossover
  de gene?
- [ ] **Elitismo de 10% + torneio 3.** Nunca variados. *Pergunta:* precisam de
  justificativa além de "valores usuais"?
- [ ] **🟡 Degenerescência de escala nos pesos comportamentais.** *Fato novo:* a intenção
  é sorteada proporcionalmente a `(w_agg, w_ret, w_def)` — o comportamento depende **só
  da razão** entre os três. Multiplicar os três por uma constante não muda nada no
  combate, mas muda o `drift_penalty`. No indivíduo evoluído a soma dos pesos varia de
  0,42 (Rushdown) a 1,80 (Turtle) contra ~1,0–1,3 nos canônicos, e para o Zoner a
  distância bruta aos pesos canônicos é 0,367 enquanto a distância entre as **razões** é
  0,065 — quase todo o "drift de pesos" do Zoner é escala invisível ao combate.
  *Pergunta:* normalizar os pesos (simplex) na representação, ou medir o drift dos pesos
  sobre a razão? Do jeito que está, parte do eixo de identidade mede algo que o simulador
  não enxerga.

## 6. Protocolo experimental e artefatos

- [ ] **Round-robin uniforme.** Os 10 pares pesam igual; não modela matchmaking.
  *Pergunta:* declarar como escopo (posição atual) basta?
- [ ] **Equilíbrio condicionado a uma política fixa.** Os pesos `w_*` *são* a política;
  ninguém procura exploit contra o roster evoluído. É a objeção mais forte ao resultado.
  *Pergunta:* precisa aparecer na Discussão com que peso?
- [ ] **10 sementes é suficiente?** `MULTI_RUN_N_SEEDS = 10`. Com Mann-Whitney e n=10 o
  SciPy usa a aproximação assintótica (conservadora). *Pergunta:* subir para 20-30
  mudaria as conclusões, e o custo é aceitável (~3,8 min por execução)?
- [x] **(F) Holm rodava sobre 4 métricas, uma delas degenerada.** *Fato:*
  `n_chars_balanced` é **5/5 nas 20 execuções** (10 por algoritmo) — amostra conjunta
  constante, e `mannwhitneyu` devolve `p = nan` porque a correção de empates zera o
  denominador. Esse "teste" entrava na família de Holm como se fosse um, e o
  multiplicador virava **4 em vez de 3**. Além disso `_holm` ordenava os p-valores com um
  `nan` dentro; comparações com `nan` são sempre falsas, então a ordenação só saía certa
  por sorte do algoritmo de ordenação.

  **Corrigido em 2026-09-16.** `_is_degenerate` monta a família pela variância da
  amostra **conjunta** — critério objetivo, decidido pelos dados, declarável antes do
  teste (não é escolha de família feita depois de ver os p-valores). Note que é a
  conjunta: `ga` constante em 5 contra `nsga2` constante em 3 é a diferença mais forte
  possível, não degenerescência. A métrica excluída segue reportada como **descritiva**,
  com a nota do porquê, e `family_size` / `excluded_from_family` vão no artefato.
  `_holm` passou a **levantar `ValueError`** ao receber `nan`, em vez de ordenar por
  sorte — o filtro a montante garante que nunca dispare. Cobertura em
  `src/tests/test_compare_algorithms.py` (9º smoke test).

  *Efeito medido na bateria de 2026-09-16* (o número de `n_hard_counters` citado antes
  era da bateria anterior; hoje essa métrica sai com `p = 0,968`, Â₁₂ = 0,49,
  desprezível). O que a família inflada apagava é o **drift**:

  | família | `drift_penalty` (p bruto 0,0257 · Â₁₂ 0,80, efeito grande) |
  |---|---|
  | 4 métricas (antes) | 0,1030 |
  | **3 — a correta** | **0,0772** |
  | 2 (só os dois objetivos) | 0,0515 |

  **Nenhuma família torna o achado significativo** — nem a mínima, que para em 0,0515,
  acima de α por 0,0015. Isso é o que garante que o conserto é de **correção** e não de
  resultado: não havia prêmio em escolher a família menor. A leitura honesta segue
  sendo *efeito grande, direção consistente, não significativo a n = 10*. O que
  resolveria é poder amostral — item (7) da §9, aditivo.
- [ ] **Referências de estatística fora do `.bib`.** Derrac et al. 2011, Arcuri & Briand
  2011 e Vargha & Delaney 2000 são citadas nos docs e no código, mas **não estão** em
  `overleaf/TCC/bibliografia.bib`.
  **Verificado:** também ausentes de `overleaf/artigo-SBC/referencias.bib` e de
  `overleaf/artigo-latinware-2026/referencias.bib` — os três `.bib`.
- [ ] **O veredito da validação externa é binário e sensível a ruído.** *Fato:* o roster
  só é ROBUSTO se **nenhum** par virar hard-counter em **nenhuma** das 10 condições — 100
  oportunidades de falhar. O `best_dominance` do NSGA-II tem 5/5 bonecos robustos e
  apenas 1/10 pares que trip em alguma condição, e ainda assim sai FRÁGIL. *Pergunta:* o
  quantificador "em alguma condição" é o certo, ou o veredito deveria ser uma fração
  (ex.: par fora da banda em >X% das condições)?
- [ ] **`results/` não tem versionamento parcial.** Mexer em `config.py`, nos canônicos
  ou no motor invalida tudo de uma vez. *Pergunta:* vale gravar um snapshot da config
  dentro de cada artefato, para que um JSON antigo se denuncie sozinho?
- [x] **Checkup dos artefatos: reproduzem.** *Re-verificado em 2026-09-16, sob o motor
  atual:* re-avaliar o `best_individual` do `results/results.json` sob seed-base 42 com
  `SIMS_PER_MATCHUP` devolve `fitness = −0,257714` (gravado:
  `−0,25771363889712734`), `dom = 0,003863`, `drift = 0,253851` — **idêntico ao
  gravado**. Os números do `HANDOFF.md` conferem com os JSONs (`multi_run`,
  `comparison`, `external_validation`). Nada stale em `results/`.
  (A verificação de 2026-09-10 registrava `−0,268325 / 0,007601 / 0,260724`; eram do
  motor **anterior** à reforma do combate e ao `grab_power`, e do `results.json` que
  aquela bateria produziu. Não são comparáveis com os de hoje.)
- [ ] **🟡 `values.tex` mistura proveniências na célula que mais depende disso.** *Fato
  novo:* além do stale já registrado no `HANDOFF` (`\aggDomMean` 0,19 → 0,1403;
  `\aggDriftMean` 0,23 → 0,2450; `\aggHvMean` 1,75 → 1,8084; `\hcPerSeed` 2,1 → 2,7;
  `\domCanExt` 1,11 → 1,4162; os dois `values.tex`, SBC e latinware, são idênticos), a
  linha de `dominance` da tabela do trade-off usa `\domAg = 0,01` — o número **dentro**
  do laço. Os outros três da mesma linha coincidem dentro e fora (`\domCan` 1,42 ≈ 1,4162;
  `\domKnee` 0,34 ≈ 0,3443; `\domBd` 0,11 ≈ 0,1148), porque só o indivíduo do AG degrada
  materialmente fora do laço (0,0076 → 0,0279). *Pergunta:* a tabela precisa ser toda de
  fora do laço — do contrário a célula do AG é a única com vantagem de proveniência,
  exatamente onde o `HANDOFF` manda reportar o número externo.

## 7. Menores — sujeira e rastros

Sem impacto em resultado; entram porque o padrão do projeto é código limpo para banca.

- [x] ~~`report._print_header` anuncia `(seed=…, n=<--n>/matchup)` mas calcula com
  `evaluate_detail`, que usa `SIMS_PER_MATCHUP`.~~ **Corrigido em 2026-09-16:** passou a
  usar `evaluate_detail_n(ind, n)`.
- [x] ~~`sensitivity_analysis --workers` tem default `None` → todos os núcleos.~~
  **Corrigido em 2026-09-16:** default `N_WORKERS`.
- [ ] `expected_winner` nunca devolve `None`: os 10 pares têm vencedor canônico (cada
  arquétipo vence 2 e perde 2, sem conflito). O ramo `"par neutro"` de
  `MatchupRecord.cycle` e o símbolo `·` são código morto.
- [ ] `ga.run`, ao bater o teto, devolve o melhor da população **151ª** rotulado
  `generation = 149` e ausente do `history`. O elitismo faz coincidir na prática
  (verificado na seed 42: `fitness` gravado == último ponto do `history`), mas a
  rotulagem é enganosa.
- [ ] `nsga2._log_generation` imprime `front0={front_sizes[0]}/{n_fronts}` medido sobre a
  população **combinada** (600), enquanto `front0_ranges` na mesma linha vem da população
  **selecionada** (300) — daí sair `front0=302` num pop de 300.
- [x] ~~`docs/reference/07-configuration.md` aponta `ATTRIBUTE_BOUNDS` em "hoje ~L68–L82".~~
  **Corrigido em 2026-09-16:** as referências por linha (aqui e em `03-archetypes.md`)
  viraram referência por **símbolo** — número de linha envelhece a cada edição.

---

## 8. Ordem de execução

O critério é **dependência**, não gravidade: cada camada condiciona a de cima. E há
uma restrição dura — mexer no motor ou no fitness invalida `results/` inteiro, então
tudo o que muda número tem de ser resolvido **antes** de uma única regeneração final.

| # | Bloco | Por que aqui | Estado |
|---|---|---|---|
| 0 | **Integridade do combate** (M1, M1b, M2, M3, impasse) | se alguma mecânica está quebrada, todo o resto mede um simulador errado | ✅ 2026-09-10 |
| 1 | **D** — empate no desempate | bug de camada de combate; muda todos os números | ✅ 2026-09-10 |
| 2 | **A** + **B** — o que é "identidade" e o que é "equilíbrio" no fitness | as duas decisões de design; mudam a função objetivo | ✅ 2026-09-16 |
| 3 | **E** — gate de convergência | o limiar depende da métrica definida em (2) | ✅ 2026-09-16 |
| 4 | **C** — sub-convergência do NSGA-II | diagnosticar com o fitness já definido, senão testa duas vezes | ✅ 2026-09-16 |
| 5 | **H** — modelos nulos (era "recalibrar canônicos p/ o ciclo existir") | o ciclo não podia ser evidência; o que faltava era piso em toda métrica | ✅ 2026-09-16 |
| 6 | **R** — guard break / grab | decisão registrada: só depois de A–C | ✅ 2026-09-16 |
| 7 | **bateria completa** — regenerar `results/` | um corte único, com tudo estabilizado | ✅ 2026-09-16 |
| 8 | **F**, **G** | camada de análise: não exigem re-rodar o AG | ✅ 2026-09-16 |
| 9 | **§7 menores** + docs + `values.tex` | limpeza e sincronização final | **próximo** |

> Fechado o passo 7, a decisão seguinte não é um item desta tabela e sim a
> **[agenda de calibração (§9)](#9-agenda-de-calibração--as-constantes-provisórias-com-evidência)**:
> sete constantes ainda rotuladas "provisório", agora com a evidência que a
> bateria produziu. Todas mudam número — fechar qualquer uma obriga a regenerar
> `results/` de novo.

---

## 9. Agenda de calibração — as constantes provisórias, com evidência

Levantamento montado em 2026-09-16 **depois da bateria completa** (passo 7), para que
cada constante ainda rotulada "provisório" seja decidida com dado e não com intuição.
Todas elas mudam número: fechar qualquer uma obriga a **regenerar `results/`**. A bateria
atual congela os valores de hoje por omissão.

> Estado: **(1) e (2) fechados em 2026-09-16** — ambos **mantidos no valor atual**, com
> justificativa escrita, então **nada precisou ser regenerado**. Restam (3) a (7);
> **(3)** depende de decidir quanto ruído se aceita, e **(4) a (7)** podem ser
> declarados como estão, com justificativa.

### (1) ✅ `DOMINANCE_DECIS_WEIGHT = 0.5` — **fechado 2026-09-16: mantido, o termo não está morto**

**A premissa deste item estava errada, e o erro era de amostra.** `decis_term` sai
0,0000 em 10/10 sementes nos dois algoritmos — mas isso é medido **só nos indivíduos
finais**. Uma guarda que lê 0 no fim é uma guarda que funcionou: a busca saiu da região
ruim. Medido agora em **18 rosters × 10 pares = 180 pares** (sims = `MULTI_RUN_SIMS`,
seed = `MULTI_RUN_VALIDATION_SEED`):

| roster | `decis_term` | pares fora da banda |
|---|---|---|
| **canônico** — que *é* a geração 0 do AG escalar | **0,2834** | 5/10 acima do TETO |
| 8 aleatórios | 0,1005 – 0,6596 | 3–9/10 acima do TETO |
| espelho do Zoner — a solução trivial | 0,1282 | **10/10 abaixo do PISO** |
| 4 evoluídos (AG + 3 representantes do NSGA-II) | 0,0000 | 0/10 |

57/180 pares estouram o teto, e o `D` observado chega a **0,4903** contra um teto de
0,20 — a guarda opera bem **dentro** da faixa real, não fora dela.

*Decisão:* **manter em 0,5, declarado como guarda.** As duas metades pegam coisas
distintas e ambas disparam: o teto pega blowout (canônico, aleatórios), o piso pega
degenerescência (o espelho — a solução trivial de equilíbrio contra a qual a tese
argumenta). Justificativa gravada no comentário do `config.py`.

*Ressalva honesta:* a evidência sustenta que o **termo existe e opera**; ela não
calibra o **peso** 0,5 contra alternativas. Isso seria um sweep, e não há evidência
pedindo um.

*Correção de registro colhida junto:* o comentário do `MATCHUP_FLOOR` afirmava que 0,02
fica "abaixo do que dois personagens idênticos produzem". Falso — o espelho do Zoner dá
`D ∈ [0,016, 0,019]`. A faixa dos espelhos é bem mais larga do que estava registrado
(Zoner 0,016–0,019 · Turtle 0,027–0,032 · Rushdown 0,030–0,035 · CM 0,045–0,052 ·
Grappler 0,074–0,088). O piso é abaixo de todo par de personagens **distintos**, e morde
0/10 nos quatro evoluídos — o comentário foi corrigido.

### (2) ✅ `MATCHUP_WR_CAP = 0.15` — **fechado 2026-09-16: mantido, com âncora de domínio**

**Decisão:** manter 0,15 e apagar o rótulo "provisório". A justificativa que faltava é a
grade de matchup da FGC, que é dita em inteiros — 5-5, 6-4, 7-3, 8-2, ou seja
`|WR − 0.5|` de 0,00 · 0,10 · 0,20 · 0,30. O consenso de domínio é que **6-4 é vantagem
saudável** (existe em todo jogo) e **7-3 é counter**, então o cap tem de permitir 0,10 e
barrar 0,20.

O que decide entre os candidatos é o **ruído de medição**: um limiar colado num ponto da
grade vira cara-ou-coroa. Com σ ≈ 0,040 em p = 0,6 e `SIMS_PER_MATCHUP`:

| cap | limiar | 6-4 real dispara à toa | 7-3 real é capturado |
|---|---|---|---|
| 0,10 | 0,60 | **50,0%** | 99,6% |
| **0,15** | 0,65 | **10,6%** | **90,9%** |
| 0,20 | 0,70 | 0,6% | **50,0%** |

0,15 é o ponto médio da única lacuna que importa e o único valor que não reprova
sistematicamente um 6-4 legítimo nem deixa passar metade dos 7-3. Subir `SIMS_PER_MATCHUP`
(item 3) estreita as duas caudas **sem mover o cap** — os dois itens são independentes.

*Não houve sweep, e a razão é substantiva:* um sweep escolheria o cap pelo que o motor
produz, e o cap é justamente a definição de "counter duro" — defini-lo pelo resultado
seria a mesma circularidade que mantém o ciclo de vantagens fora do fitness.

<details>
<summary>Levantamento original do item (o que motivou a revisão)</summary>


**Evidência:** no motor antigo o `cap_term` era **exatamente 0** (não mordia nunca).
Agora: AG 0,0259 ± 0,0254, mordendo em **7/10** sementes; NSGA-II 0,0201 ± 0,0232,
mordendo em **5/10**. Hard-counters por execução: AG 0,90 ± 0,7 · NSGA-II 1,30 ± 1,6.
Roster inteiro equilibrado (5 em banda **e** 0 counters): AG **30%** · NSGA-II **50%**
das sementes.

*Leitura:* o cap deixou de ser decorativo — hoje é ele que decide se uma execução conta
como "roster equilibrado". Isso torna o valor 0,15 uma escolha de **resultado**, não de
formalidade: a 0,20 a taxa de roster equilibrado subiria muito; a 0,10, despencaria.
*Decidir:* justificar 0,15 por domínio (FGC: que WR ainda é "vantagem" e não
"counter"?) ou fazer um sweep e escolher pelo que o motor produz. Hoje não há
justificativa escrita para 15 pontos percentuais.

</details>

### (3) `SIMS_PER_MATCHUP = 150` — o ajuste ao stream é de 21×

**Evidência:** o melhor do AG (seed 42) dá `dominance` **0,0039 dentro do laço** e
**0,0804 ± 0,0158 fora** (10 condições independentes, 500 sims cada) — degrada **21×**.
E o que quebra não é ruído: `Zoner × Turtle` sai em **28,2% ± 1,9%** fora do laço, isto
é, um counter duro **sistemático** que a avaliação de 150 sims não enxergou. Veredito do
`external_validation`: **FRÁGIL** (5/5 bonecos robustos, mas 3/10 matchups viram counter
em alguma condição).

Ruído binomial de um matchup: ±4,08% com 150 sims · ±2,89% com 300 · ±2,04% com 600 —
contra um cap de 15%.

*Leitura:* o problema não é a margem do cap contra o ruído (4% contra 15% é folgado) — é
que com 150 sims o AG consegue **ajustar-se à realização específica do RNG**, e o
resultado não sobrevive fora dela. Subir os sims é o remédio direto e caro (custo linear:
a bateria de 90 min viraria ~180 min a 300 sims). *Decidir:* subir `SIMS_PER_MATCHUP`,
ou aceitar e **sempre reportar o número de fora do laço** como headline (o que já é a
recomendação registrada em §4).

### (4) ✅ Canônicos — **fechado 2026-09-16: declarados finais**

**"Melhor valor" não existe aqui, por construção.** Os canônicos são a **premissa** do
trabalho — o que cada arquétipo *é*, dado pela FGC e anterior à pergunta de equilíbrio —
não uma variável a otimizar. Ajustá-los para "ficarem melhores" (mais equilibrados, ou
realizando o ciclo) seria mexer na premissa para obter a resposta. O único critério
admissível é **coerência**, e ele precisa ser declarado antes.

**Critério de aceitação** (o que estava faltando, mais do que os valores):

| # | exigência | medido |
|---|---|---|
| 1 | **internamente coerentes** — cada arquétipo ocupa os extremos que o definem e tem assinatura comportamental própria | validador **23/23** (L1 inter + L2 intra + L3 behavioral) |
| 2 | **distintos entre si** — nenhum par é quase-cópia | as 10 distâncias par-a-par ≥ **0,3221** (mín.: CM × Grappler) |
| 3 | **desequilibrados** — é o ponto de partida do problema, não defeito | `dominance` **1,2690**; Turtle 0,0%, Rushdown 99,6% |

E o que **não** se exige, com a razão: realizar o ciclo (item H — é loteria de 1/24, não
pode ser evidência) e ser equilibrado (seria o problema já resolvido de graça).

Os três passam. *Decisão:* **finais**; rótulo "provisório" apagado.

**Duas limitações declaradas junto** — não motivam mudança, mas têm de aparecer no texto:

- **5 dos 55 genes estão colados no bound, e 4 são genes definidores:** Rushdown
  `attack_cooldown` = 1,0 (piso) e `speed` = 5,0 (teto); Turtle `hp` = 450 e
  `attack_cooldown` = 5,0 (tetos) e `damage` = 15,0 (piso). É intencional — o Rushdown
  *é* o mais rápido, a Turtle *é* a mais lenta e resistente — mas a consequência é real:
  esses genes **só podem driftar para dentro**. A identidade do Rushdown e da Turtle é
  assimetricamente protegida num sentido e livremente erodível no outro, e o
  `drift_penalty` não distingue os dois casos.
- **Os canônicos SÃO a referência do drift.** Qualquer mudança neles invalida todo número
  de drift já medido no projeto — o que é, por si, uma razão forte para congelá-los agora
  que passam no critério.

### (5) `TICK_SCALE = 5` e `ACTION_PERSISTENCE_SUBTICKS = 10`

**Evidência:** a sensibilidade no indivíduo **evoluído** (piso medido 7,9%) dá 4 genes
visíveis — `range` 28,7% · `damage` 21,0% · `hp` 18,7% · `attack_cooldown` 18,1% — e 4
abaixo do piso: `grab_power` 7,3% · `speed` 6,1% · `stun` 6,1% · `knockback` 2,4%.
(No canônico, saturado, quase tudo saía "neutro" — era efeito de teto, ver item G.)

*Leitura:* `speed` e `stun` abaixo do piso é suspeito e liga direto à incoerência de
escala já registrada: a persistência (10 sub-ticks) é **maior que o cooldown mínimo**
(5), então um `cooldown = 1` que sorteia GUARDA abre mão de duas janelas de ataque. E
`grab_power` a 7,3% fica **na borda** do piso — o gene novo mal é visível. *Decidir:*
testar `ACTION_PERSISTENCE_SUBTICKS = 5` (igualando ao cooldown mínimo) e ver se `speed`
e `stun` sobem acima do piso.

### (6) Degenerescência de escala nos pesos comportamentais

**Evidência:** a intenção é sorteada proporcionalmente a `(w_agg, w_ret, w_def)`, então
só a **razão** afeta o combate — mas o drift mede os valores absolutos. Medido no
indivíduo evoluído, a fração da distância de pesos que o simulador **não enxerga**:

| arquétipo | soma canôn. | soma evol. | dist. bruta | dist. razões | invisível |
|---|---|---|---|---|---|
| Zoner | 1,10 | 1,14 | 0,040 | 0,035 | 10% |
| Rushdown | 1,05 | 2,62 | 1,046 | 0,584 | **44%** |
| Combo Master | 0,95 | 1,62 | 0,596 | 0,423 | 29% |
| Grappler | 1,20 | 1,01 | 0,381 | 0,302 | 21% |
| Turtle | 1,30 | 2,29 | 0,801 | 0,358 | **55%** |

> ⚠️ **A tabela acima está confundida por escala** e superestima o problema. Ela compara
> distância no espaço bruto com distância no espaço normalizado — dois espaços de escalas
> diferentes —, então parte da "redução" é só reescala, não invisibilidade. Medição exata
> abaixo.

**Medição exata (2026-09-16).** Escalar os três pesos por uma constante `k > 0` não muda
**nada** no combate — a intenção é sorteada proporcionalmente. Logo a parcela do drift que
desaparece ao escolher o melhor `k` é penalidade cobrada por diferença que o simulador não
consegue distinguir. Sem ambiguidade de escala: mesma métrica, mesmos bounds, um único
grau de liberdade comprovadamente nulo.

| arquétipo | drift real | drift mín(k) | k ótimo | desperdiçado | % do total |
|---|---|---|---|---|---|
| Zoner | 0,0356 | 0,0356 | 0,992 | 0,0001 | 0,2% |
| **Rushdown** | 0,3302 | 0,2804 | 0,654 | 0,0499 | **15,1%** |
| Combo Master | 0,2957 | 0,2694 | 0,581 | 0,0263 | 8,9% |
| Grappler | 0,2516 | 0,2498 | 1,193 | 0,0018 | 0,7% |
| Turtle | 0,3560 | 0,3394 | 0,702 | 0,0166 | 4,7% |
| **MÉDIA** | **0,2539** | **0,2349** | | **0,0189** | **7,5%** |

*Leitura:* **7,5% do drift médio** é cobrado por diferença behaviouralmente nula — muito
menos que os "55%" que este item registrava, mas não desprezível: 0,0189 contra os ~0,04
que separam "identidade preservada" de "todos idênticos" (item H). Concentra-se no
Rushdown (15,1%) e no Combo Master (8,9%), e os `k` ótimos de 0,58–0,70 dizem o que
aconteceu — o AG **inflou a escala dos pesos** e o drift cobrou pela inflação.

Atenuante: o artefato afeta também os **modelos nulos** (um espelho tem escala de pesos
igualmente arbitrária), então cancela em parte na leitura de *posição entre piso e teto*.
Não cancela na leitura do drift absoluto.

*Decidir — duas formas de consertar, ambas exigem regenerar:*
- **na métrica** (mais estreito): `_archetype_deviation` normaliza os pesos no simplex
  antes de comparar. Poucas linhas, cirúrgico.
- **na representação** (mais principista): se só a razão importa, o indivíduo não deveria
  carregar o grau de liberdade extra. Mais limpo, mas mexe na semântica de mutação e
  crossover.

**Bundling:** o conserto custa uma regeneração, e o item (3) já custa uma. Decidir os dois
juntos paga uma regeneração em vez de duas.

### (7) `MULTI_RUN_N_SEEDS = 10` — e o item (F) está apagando o único achado

**Evidência do teste:**

| métrica | p bruto | p Holm (família 3) | Â₁₂ | efeito |
|---|---|---|---|---|
| `dominance_penalty` | 0,3075 | 0,6150 | 0,64 | médio |
| `drift_penalty` | **0,0257** | **0,0772** | **0,80** | **grande** |
| hard-counters/execução | 0,9683 | 0,9683 | 0,49 | desprezível |
| bonecos em banda/execução | — | — (fora da família) | 0,50 | desprezível |

*Leitura, depois de fechado o (F):* a única diferença real da bateria — o NSGA-II tem
drift menor, efeito **grande** (Â₁₂ = 0,80), p bruto **0,026** — melhorou de 0,1030 para
**0,0772** com a família correta, mas **segue não significativa**. E não é questão de
apertar mais a família: mesmo a mínima possível (2 métricas, só os dois objetivos do
Pareto) para em **0,0515**, acima de α por 0,0015. O gargalo é **poder amostral**, não
correção.

**Poder amostral medido (2026-09-16).** Simulação com 4000 réplicas por `n`: dois normais
separados por 1,190σ (a separação que produz exatamente Â₁₂ = 0,80), critério
`3 × p < 0,05` (Holm com a família de 3 já corrigida):

| n por algoritmo | poder |
|---|---|
| **10 — o atual** | **44,4%** |
| 15 | 73,1% |
| **20** | **85,9%** |
| 25 | 94,3% |
| 30 | 97,3% |
| 40 | 99,7% |

*Decisão:* **n = 20.** É o menor valor que passa do patamar convencional de 80% de poder.
Com os 10 atuais o experimento tem menos de 50% de chance de detectar um efeito
**grande** que provavelmente existe — é subdimensionado, e dizer "não significativo" a
partir dele diz mais sobre a amostra que sobre os algoritmos.

*Ressalva sobre "aditivo":* vale no sentido **estatístico** — as sementes 42–51 são
determinísticas e produzem resultado idêntico sob a mesma config, então nada do que já
foi medido se perde. **Não** vale no de compute: `multi_run` não tem resume, então
`--n-seeds 20` re-roda as 20 (~180 min em vez de +90).

**Bundling:** junto com (3) e (6), numa regeneração só.

### O que NÃO exige regenerar a bateria

Item **F** (acima), `sensitivity_analysis`, `external_validation`, os menores do §7
restantes, docs, `values.tex` e bibliografia. Todos recalculam a partir dos artefatos
existentes, em segundos ou minutos.

E o **sweep de `LAMBDA_DRIFT`** é **aditivo**: são execuções novas em λ diferentes, com a
bateria de hoje virando um ponto da curva. Não invalida nada.
