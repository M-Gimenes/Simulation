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
| **A** | O AG escalar equilibra **destruindo a identidade** (validador 7/21) e nenhum dos dois medidores de identidade do sistema acusa | §3 | aberto |
| **B** | "O AG vence em `dominance_penalty`" não é "o AG equilibra melhor" — a diferença está no **piso de decisividade**, e o NSGA-II é melhor no termo primário | §4 | aberto |
| **C** | O ponto do AG escalar **não está** na fronteira do NSGA-II: ele a **domina**, justamente no representante usado em toda a comparação | §5 | aberto |
| **E** | O gate de convergência é inalcançável **por construção** (o termo é quantizado), não só na prática | §4 | aberto |
| **F** | Holm roda sobre 4 métricas, uma delas degenerada (`p = nan`) — infla a correção nas outras três | §6 | aberto |
| **G** | A sensibilidade usa dois critérios de corte incompatíveis na mesma saída, e o piso de ruído está subdimensionado | §4 | aberto |
| **H** | O ciclo canônico não é realizado nem pelo próprio canônico (5/10 = nível de acaso) — o baseline não distingue preservação de sorte | §3 | aberto |
| **R** | **Eixo Recurso sem counter:** DEFEND não tem custo nem quebra de guarda, e o grab ausente é ao mesmo tempo a identidade do Grappler e uma aresta do ciclo | §2 | adiado p/ depois de A–C |

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
- [ ] **Decisividade caiu abaixo do piso.** *Fato novo:* no AG curto, os 10 pares deram
  decisividade entre 0,05 e 0,13 contra `MATCHUP_FLOOR = 0,10` — as lutas ficaram
  **apertadas demais** pelo critério atual (vencedor fecha com ~10-25% de HP). Ou o piso
  está descalibrado para o novo motor, ou ele está pedindo algo que o modelo não deve
  querer. Amarra com o item (B) em §4.
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
- [ ] **(R) O eixo Recurso não tem counter — e o grab ausente é o mesmo problema em três
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

  *Perguntas a responder antes de escolher:* o grab deve ter **alcance próprio** (menor
  que o `range`, como na FGC) ou usar o mesmo? Deve ter **cooldown próprio**? E o efeito
  contra quem **não** está defendendo — dano normal, ou é uma jogada que só vale contra
  guarda (o que a torna genuinamente um counter, e não um golpe melhor)?
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
- [ ] **Normalização do drift usa `x / hi`** (fração do máximo do bound), não
  `(x − lo) / (hi − lo)`. *Pergunta:* a escolha é deliberada? Ela faz genes com `lo`
  alto (ex.: HP, mín 250) parecerem menos deslocados do que estão.
  **Verificado:** o efeito é de **1,3×** no indivíduo evoluído — `drift_penalty` 0,2607
  com a normalização atual contra 0,3417 com `(x − lo)/(hi − lo)`. O maior desvio
  individual é o do Turtle: 0,2894 → 0,4535 (o HP 450→288 conta como −0,36 hoje e −0,81
  na normalização por range). A convenção atual **subestima sistematicamente** o desvio
  dos genes de `lo` alto — e é justamente neles que o AG se moveu mais.
- [ ] **🔴 (A) O AG equilibra destruindo a identidade — e nenhum medidor do sistema
  acusa.** *Fato novo.* Validador de identidade (21 asserções de ranking) contra a
  `dominance_penalty` fora do laço:

  | indivíduo | dominance (fora do laço) | validador | drift | diferenciação |
  |---|---|---|---|---|
  | canônico | 1,4162 | **21/21** | 0,000 | 1,00 |
  | melhor do AG escalar | 0,0279 | **7/21** | 0,261 | 0,92 |
  | NSGA-II `knee_point` | 0,3443 | **20/21** | 0,089 | 0,96 |
  | NSGA-II `best_dominance` | 0,1148 | **13/21** | 0,271 | 0,96 |
  | NSGA-II `ideal_point` | — | 16/21 | 0,155 | — |

  O que o AG fez com os genes: Turtle HP 450→288 e dano 15→28 (a "muralha viva" virou o
  boneco de **menor** HP e **maior** dano); Rushdown speed 5,0→2,7 e `w_aggressiveness`
  0,90→0,10 (o agressivo virou defensivo); Zoner range 18→9 (o de maior alcance virou o
  de **menor**); Combo Master perdeu o rank 1 de stun. Quatro dos cinco convergiram para
  dano 24–28 (topo do bound) e HP 284–291 (fundo do bound).

  **O problema não é o resultado — é que os dois instrumentos de identidade do projeto
  não o detectam:**
  - `drift_penalty` dá **0,261 para o AG e 0,271 para o `best_dominance`** — praticamente
    empatados, enquanto o validador dá 7/21 contra 13/21. Drift é distância euclidiana
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
  *Perguntas:* (a) o eixo de identidade otimizado deveria ser o score do validador (ou
  um relaxamento contínuo dele) em vez de — ou junto de — drift? (b) se drift continuar,
  precisa ser ponderado pelos genes definidores de cada arquétipo? (c) `\valAg = 7` já
  está no `values.tex`: a redação assume esse número como resultado, enquanto o
  `drift_penalty` do mesmo indivíduo é lido como "identidade preservada a 0,26" — as
  duas leituras não podem coexistir no texto.
- [ ] **🟡 (H) O canônico não realiza o próprio ciclo de vantagens.** *Fato novo:*
  medido sob a semente 9999 com 200 sims, o roster canônico dá WR global Rushdown
  **100%**, Turtle **0%**, Zoner 25%, Grappler 73%, CM 52%; 10/10 pares são
  hard-counter; e o ciclo canônico é mantido em **5 de 10 arestas** (Zoner×Grappler,
  Rushdown×Grappler, Rushdown×Turtle, CM×Grappler e CM×Turtle saem invertidos).
  Arestas mantidas: canônico 5/10, AG 5/10, `knee_point` 5/10, `best_dominance` 6/10 —
  todos no nível do acaso.
  *Pergunta:* a tabela do ciclo em `archetypes.py`/CLAUDE.md é uma intenção de design da
  FGC sem realização no motor. Medir "quanto do ciclo sobreviveu" contra um baseline que
  já está em 5/10 não distingue preservação de sorte. Ou o motor precisa realizar o ciclo
  no canônico (calibração), ou a métrica post-hoc precisa de outra régua.

## 4. Fitness e dados

- [ ] **🔴 (E) O gate de convergência do AG é inalcançável — por construção, não só na
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
  *Pergunta:* o gate vira um limiar calibrado (o `GLOBAL_CONVERGENCE_THRESHOLD` já existe
  e já é a régua do reporting), ou o critério de parada por convergência sai?
- [x] **`dominance_penalty` abaixo do piso de ruído: há ajuste ao stream, mas o
  equilíbrio sobrevive.** *Fato:* com 150 sims/matchup o desvio binomial da WR global
  (600 lutas) é ~2%, o que daria um `global_term` da ordem de 0,03 — e o AG chegou a
  0,0076 no laço, indicando adaptação à realização específica do RNG fixada pelo CRN.
  Fora do laço (`external_validation`, sementes 10000+, 500 sims) o mesmo indivíduo dá
  **0,0279 ± 0,0062**: degrada ~3,7×, mas mantém 5/5 bonecos em banda em todas as 10
  condições e **0/10** hard-counters — veredito **ROBUSTO**. *Conclusão:* o ajuste ao
  stream existe e precisa ser declarado, mas não é o que sustenta o resultado. Reportar
  sempre o número **fora** do laço.
- [ ] **🔴 (B) O `dominance_penalty` composto esconde de onde vem a diferença entre os
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
  *Pergunta:* reportar os três termos separados no `multi_run`/`compare_algorithms` (hoje
  só o composto vai para o artefato), e decidir se o **piso** de decisividade deveria
  estar no fitness: ele empurra na direção oposta ao `global_term` (equilibrar aproxima
  as lutas; o piso pune lutas próximas), e hoje é ele quem decide a comparação entre os
  dois algoritmos.
- [ ] **`MATCHUP_WR_CAP = 0.15` provisório.** Define o que é "counter duro" e portanto
  quanto do ciclo de vantagens cabe no espaço permitido. *Pergunta:* há justificativa de
  domínio (FGC) para 15 pontos percentuais, ou é preciso um sweep?
  **Verificado:** no indivíduo evoluído o `cap_term` é **exatamente 0** — os 10 pares
  ficam em [43,5%, 58,0%], bem dentro de [35%, 65%]. O teto nunca chega a morder; quem
  define o resultado é `global` + o piso de decisividade. Um sweep de `MATCHUP_WR_CAP`
  no regime atual não mudaria nada — antes de calibrá-lo, ver se ele ainda tem função.
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
- [ ] **🟡 (G) A sensibilidade usa dois critérios de corte incompatíveis, e o piso está
  subdimensionado.** *Fato novo:* `_classify` usa limiares fixos (≥5% visível, <3%
  neutro, entre os dois "borderline") enquanto a saída imprime um "piso de ruído
  binomial" de 1,77% que **não entra na classificação** — dois critérios diferentes na
  mesma tabela. Pior: o piso é o desvio de **uma** proporção (`√(0,25/800)`), mas o
  número classificado é uma **diferença** entre duas WRs (+σ e −σ). Mesmo com o
  pareamento CRN, o piso correto para uma diferença é maior (até √2× se as duas fossem
  independentes). *Pergunta:* unificar num único critério — classificar contra o piso
  correto da diferença — antes de citar a tabela.
- [ ] **`SIMS_PER_MATCHUP = 150` vs as bandas de decisão.** Ruído binomial por matchup
  ~4% contra um cap de 15%. *Pergunta:* a margem é confortável o bastante, ou o número
  de sims precisa subir para o cap significar o que diz?

## 5. AG escalar e NSGA-II

- [ ] **Escalar e NSGA-II não param pelo mesmo critério.** O AG tem convergência +
  estagnação + teto; o NSGA-II roda `NSGA2_GENERATIONS` fixas. *Pergunta:* a assimetria
  é intencional? Ela afeta a comparação entre os dois.
  **Verificado:** na prática a assimetria é menor do que parece — a convergência do AG
  nunca dispara (§4/E) e na seed 42 ele também bateu o teto de 150 gerações
  (`stop_reason = "máximo de gerações (150)"`, `stagnated = False`). Os dois rodaram 150
  gerações. A assimetria é de **descrição**, não de execução.
- [ ] **🔴 (C) O ponto do AG escalar não está na fronteira do NSGA-II — ele a domina.**
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
  *Perguntas:* (a) o NSGA-II precisa de mais gerações / população menor / mecanismo
  contra o colapso de front0? (b) enquanto isso não for resolvido, qualquer comparação
  AG × NSGA-II mede sub-convergência do NSGA-II, não trade-off; (c) o comparável de
  mínimo L1 continua não sendo extraído (`select_representatives` só tem `best_*`,
  `knee` e `ideal` = mín **L2**).
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
- [ ] **🟡 (F) Holm roda sobre 4 métricas, uma delas degenerada.** *Fato novo:*
  `n_chars_balanced` é **5/5 nas 20 execuções** (10 por algoritmo) — amostras idênticas,
  e `mannwhitneyu` devolve `p = nan`. Esse "teste" entra na família de Holm como se fosse
  um, e o multiplicador vira **4 em vez de 3**. Efeito concreto: `n_hard_counters` sai
  com `p_Holm = 0,0495` — significativo por 0,0005; com a família correta de 3 métricas
  seria **0,033**. Além disso `_holm` ordena os p-valores com um `nan` dentro;
  comparações com `nan` são sempre falsas, então a ordenação só saiu certa por sorte do
  algoritmo de ordenação. *Pergunta:* descartar métricas degeneradas da família (e do
  relatório) antes de aplicar Holm, e tratar `nan` explicitamente.
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
- [x] **Checkup dos artefatos: reproduzem.** *Verificado:* re-avaliar o `best_individual`
  do `results/results.json` sob seed-base 42 com 150 sims devolve `fitness = −0,268325`,
  `dom = 0,007601`, `drift = 0,260724` — **idêntico ao gravado**. Os números do
  `HANDOFF.md` conferem com os JSONs (`multi_run`, `comparison`, `external_validation`).
  Nada stale em `results/`.
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

- [ ] `report._print_header` anuncia `(seed=…, n=<--n>/matchup)` mas calcula
  `fitness`/`drift`/`dominance` com `evaluate_detail`, que usa `SIMS_PER_MATCHUP` (150) —
  não o `--n` (default 200). O cabeçalho e o resto do dossiê rodam com n diferentes.
- [ ] `sensitivity_analysis --workers` tem default `None` → todos os núcleos, ignorando a
  decisão documentada `N_WORKERS = 8` que existe por causa do `WinError 1455`.
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
- [ ] `docs/reference/07-configuration.md` aponta `ATTRIBUTE_BOUNDS` em "hoje ~L68–L82";
  hoje é L76–L92.

---

## 8. Ordem de execução

O critério é **dependência**, não gravidade: cada camada condiciona a de cima. E há
uma restrição dura — mexer no motor ou no fitness invalida `results/` inteiro, então
tudo o que muda número tem de ser resolvido **antes** de uma única regeneração final.

| # | Bloco | Por que aqui | Estado |
|---|---|---|---|
| 0 | **Integridade do combate** (M1, M1b, M2, M3, impasse) | se alguma mecânica está quebrada, todo o resto mede um simulador errado | ✅ 2026-09-10 |
| 1 | **D** — empate no desempate | bug de camada de combate; muda todos os números | ✅ 2026-09-10 |
| 2 | **A** + **B** — o que é "identidade" e o que é "equilíbrio" no fitness | as duas decisões de design; mudam a função objetivo | próximo |
| 3 | **E** — gate de convergência | o limiar depende da métrica definida em (2) | |
| 4 | **C** — sub-convergência do NSGA-II | diagnosticar com o fitness já definido, senão testa duas vezes | |
| 5 | **H** — recalibrar canônicos para o ciclo existir | depende de (0) motor sadio e (2) régua de identidade | |
| 6 | **R** — guard break / grab | decisão registrada: só depois de A–C | |
| 7 | **bateria completa** — regenerar `results/` | um corte único, com tudo estabilizado | |
| 8 | **F**, **G** | camada de análise: não exigem re-rodar o AG (G re-roda só a sensibilidade) | |
| 9 | **§7 menores** + docs + `values.tex` | limpeza e sincronização final | |
