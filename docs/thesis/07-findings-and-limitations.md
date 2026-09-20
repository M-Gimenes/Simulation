# 07 — Achados, limitações e o que falta

**Entra em**: Resultados / Discussão / Limitações.

## Achados

- **O modelo representa os arquétipos — depois da reforma de 2026-09-10** (auditoria do
  combate, [`../reference/11-combat-review.md`](../reference/11-combat-review.md)). Uma
  revisão anterior concluíra o mesmo medindo no canônico saturado, onde nenhuma mecânica
  parece quebrada; a auditoria achou quatro defeitos que atingiam justamente os genes de
  identidade do Zoner e do Combo Master, e os corrigiu. No motor atual o canônico passa
  nas 23 asserções do validador, inclusive nas 5 comportamentais — Rushdown pressiona,
  Turtle guarda, Zoner segura distância, Combo Master trava, Grappler quebra guarda.
  **Achado positivo, com a ressalva de método**: auditar mecânica exige um ponto
  não-saturado do espaço.
- **O ciclo canônico não é trivialmente preservado no modelo quase-determinístico (baseline):**
  sem combo chaining / variância, muitos matchups do canônico ficam binários (100/0).
  Interpretação (ver [02](02-canonical-cycle.md)): a estrutura FGC depende parcialmente
  de mecânicas estocásticas que foram removidas — é **achado, não falha**. *Cuidado*:
  distinguir esta quebra **do baseline** da quebra **pós-balanceamento** — esta última
  era forçada pelo objetivo antigo (WR por-matchup) e deixou de ser sob a reformulação
  **C2** (ver abaixo e [02](02-canonical-cycle.md)).
- **`LAMBDA_DRIFT` alto prende o AG no canônico**: com 6.0, o melhor indivíduo
  ficava colado no canônico (drift ≈ 0) e desbalanceado, porque mover-se custava ~6× o
  ganho em equilíbrio. Daí a decisão de `LAMBDA_DRIFT = 1.0` e o foco no NSGA-II (ver
  [04](04-design-decisions.md)).
- **`recovery` era evolutivamente neutro → removido (2026-06-27):** o gene funcionava
  mecanicamente (Turtle resistia a stun), mas drifava para o piso 0 — em lutas que são
  blowouts, resistir ao stun **não muda o desfecho**, logo não havia pressão seletiva.
  Foi um dos motivos para **removê-lo** do modelo (junto de `defense`) na simplificação
  do combate. O achado vira ilustração ("um gene sem efeito no desfecho não é
  otimizado"), não uma pendência.

### Achados da auditoria de 2026-09-16 (A, B, E, C)

Cinco resultados que **precisam** aparecer na redação — os quatro primeiros são sobre
método, o último é sobre o objeto.

- **A linha premissa/resposta é o que sustenta a não-circularidade.** O fitness pode
  codificar **o que cada arquétipo é** (valores canônicos, genes definidores); nunca
  **quem vence quem** nem **se equilíbrio e identidade são compatíveis**. É essa
  distinção que responde à objeção óbvia ("se identidade está no fitness, você não está
  forçando o resultado?"). O argumento decisivo é empírico: com `LAMBDA_DRIFT = 1.0`
  ligado o run inteiro, o AG **mesmo assim** trocou identidade por equilíbrio (8/21 no
  validador). Penalidade não é restrição — o termo existe e pode perder. Detalhe em
  [03](03-fitness-formulation.md).
- **Identidade precisou de duas réguas, e uma delas não pode ser citada como prova.** O
  `drift_penalty` (estrutural, no fitness) e o validador discordavam: 0,261 lido como
  "preservada" contra 8/21 lido como "destruída". Não era homogeneização, era **troca de
  papéis** — distância euclidiana é cega a **ranking**. Corrigido normalizando pelo range
  do bound e ponderando os genes definidores. Consequência a declarar: as **Layers 1-2 do
  validador ficaram parcialmente endógenas** (medem o eixo que o fitness otimiza) e valem
  como diagnóstico, não como prova; quem pode sustentar uma leitura de identidade
  preservada são as réguas **funcionais** — a Layer 3 e, desde 2026-09-18, a concordância
  de ranking comportamental. O ciclo não serve: o próprio canônico só realiza 6/10 dele. A
  pergunta da tese diz *"functional identities"* — comportamento, não valor de gene.
- **Duas premissas do fitness não sobreviveram à medição.** (i) O piso de decisividade
  existia para punir "lutas que não acontecem", mas **100% das lutas terminam em KO** no
  motor reformado (70 pares, rosters aleatórios inclusive) — decisividade baixa é KO no
  fio, a melhor luta possível. O piso empurrava contra o termo primário e era ele, um
  termo secundário de peso 0,5, quem decidia a comparação entre algoritmos. (ii) O
  `cap_term` era exatamente 0 no motor antigo e **voltou a morder** no reformado (0,0160),
  porque a reforma abriu espaço para vantagem par-a-par.
- **O critério de convergência era código morto, e consertá-lo revelou ajuste ao stream.**
  O gate `dominance_penalty ≤ 1e-9` era insatisfazível *por construção* (RMS sobre
  contagens discretas: o menor valor não-nulo é ~0,0015). E a "reavaliação independente"
  rodava **no mesmo stream de RNG do treino**, então não podia discordar do gate. Com a
  confirmação fora do stream: em 60 gerações o gate dispara **16×** e a confirmação
  rejeita **as 16** — o ajuste ao stream, quantificado. O que quebra é sempre o
  **par-a-par**, nunca a WR global.
- **A leitura da comparação AG × NSGA-II inverteu, e o motivo é instrutivo.** O seed
  canônico é **imortal** no NSGA-II: `drift` tem piso 0 *alcançável*, então dominar o
  canônico exigiria `drift < 0`. Resultado medido: 40 dos 78 pontos da fronteira eram
  rosters tão desequilibrados quanto o canônico intocado, comendo um terço da população.
  Enquanto a fronteira estava contaminada, toda comparação media sub-convergência do
  NSGA-II, não trade-off. Removendo o seed (só do NSGA-II — no escalar ele ajuda), o mapa
  do trade-off passou a existir, e no orçamento de produção os dois ficam **mutuamente
  não-dominados**: o escalar domina 0 dos 64 pontos, nenhum o domina, e ele vence na
  própria função que otimiza (L1 0,2331 contra 0,2487). Vale como lição de método na
  Discussão: **um detalhe de inicialização pode inverter a conclusão de uma comparação
  entre algoritmos** — e, no mesmo item, o orçamento também inverteu (a pop 120 a leitura
  era 0,2115 contra 0,2945, a favor do NSGA-II), o que é a razão de a comparação de
  qualidade só ser feita sobre a bateria.

### Nenhuma métrica do projeto tinha piso (2026-09-16)

Achado de método com consequência direta em toda leitura de resultado. As três réguas de
identidade eram lidas contra o **teto**, como se o piso fosse zero. Medido com 35 rosters
nulos (5 espelhos + 30 aleatórios), bateria de 2026-09-18:

| métrica | piso médio | pior nulo | teto |
|---|---|---|---|
| validador (L1-L3) | 6,4/23 (5,97 com o empate contado contra a asserção) | **10/23** | 23/23 |
| `drift_penalty` | 0,377 (espelho) · 0,415 (aleatório) | 0,327 | 0,000 |
| arestas do ciclo | 5/10 (cada aresta é cara-ou-coroa) | 8/10 | 10/10 |
| concordância de ranking (τ, desde 2026-09-18) | +0,001 | +0,338 | 1,000 |

Consequências para a redação:

- **Nunca citar valor cru.** Reportar `posição = (valor − piso)/(teto − piso)` e o
  p-valor empírico. O indivíduo evoluído de antes da reforma do fitness, lido como "8/21 =
  identidade destruída", estava **no piso** (p = 0,46) — indistinguível de um roster
  aleatório.
- **O espelho é a objeção com números.** Cinco personagens idênticos são a solução trivial
  do equilíbrio e perdem identidade por apenas ~0,04 de drift, então a tese precisa
  responder isso medindo, não argumentando. Na bateria de 2026-09-18 o `dominance` do
  roster evoluído (0,026) ficou **no mesmo nível** do dos espelhos (0,025–0,037, fora o do
  Zoner, que o piso de decisividade penaliza) — e esse nível é o piso de ruído amostral de
  200 lutas. A leitura certa é *tão equilibrado quanto a simetria perfeita, dentro do
  ruído*; a frase anterior, "mais equilibrado que o espelho (0,026 contra 0,025)", tinha o
  sinal trocado. Na identidade, o evoluído supera os 35 nulos em drift e nas Layers 1-2 —
  as réguas endógenas —, mas não na funcional (ver abaixo).
- **O ciclo autoral não serve de régua — mas não por ser "loteria".** Com arestas
  decididas, realizar as 10 teria p = 1/1024; o argumento da loteria de 1/24 estava errado.
  O motivo real é que **o próprio canônico realiza só 6/10** do ciclo no motor: não se
  preserva o que a premissa não tinha. E contra as direções que o canônico **realiza**, o
  evoluído mantém 5/10 (2000 lutas por par) — o acaso: o favorito de cada confronto não
  sobreviveu ao equilíbrio.
- **A não-transitividade existe, mas é em boa parte implicada pelo objetivo.** Um roster
  estritamente transitivo tem WRs 100/75/50/25/0, incompatível com todos perto de 50%,
  então equilíbrio global com pares **decididos** força intransitividade. As "4,0 tríades
  com pares em 43%–55%" citadas antes não mostravam isso: a 200 lutas por par, esse
  espalhamento é o do puro ruído, e um espelho chega às mesmas 4,0 tríades. A evidência
  que existe é a de 5000 lutas por par (validação externa): os 10 pares decididos
  (|z| ≥ 3,6, WR de 42,0% a 57,8%) formando um torneio **regular** (5 tríades). O que é
  achado — não implicado — é os pares **seguirem decididos** sob o equilíbrio; a
  intransitividade vem junto.

### Achados da bateria com n = 20 (2026-09-18)

- **A comparação AG × NSGA-II se sustenta a n = 20, e o efeito de n = 10 estava inflado.**
  As três métricas da família de Holm seguem significativas com efeito grande —
  `dominance` p 0,0123 (Â₁₂ 0,27, AG melhor), `drift` p 0,00007 (0,89, NSGA-II melhor),
  counters p 0,0018 (0,21, AG melhor). Mas os três Â₁₂ andaram na direção de 0,5 em relação
  ao n = 10 (0,20 · 0,94 · 0,14), o padrão típico de amostra pequena. Cita-se o de n = 20.
- **A vantagem do AG em equilíbrio é inteiramente de counters duros.** No termo primário
  (`global_term`) os dois empatam — mediana 0,0375 contra 0,0382; no `cap_term`, 0,0000
  contra 0,0357. A frase certa não é "o AG equilibra melhor", e sim "os dois equilibram o
  roster globalmente igual, e o NSGA-II deixa pares passarem do teto". Em rosters que
  passam no critério completo: 14/20 do AG contra 4/20 do `best_dominance`.
- **Convergência é regra, não exceção — mesmo com a confirmação fora do stream.** O AG
  convergiu em 20/20 sementes, na geração 34,8 ± 17,1, embora a confirmação tenha recusado
  71% dos disparos do gate (50 de 70). A confirmação atrasa a convergência, não a impede.
  Mas convergir é o **primeiro** sucesso de um teste repetido a cada geração, não
  equilíbrio estável: das 20 sementes convergidas, 14 terminaram com o roster equilibrado
  na reavaliação.
- **Os três sweeps exploratórios testaram os valores vigentes e os três passaram** — λ,
  pesos do dominance e, por último, elitismo / torneio, onde nenhum dos 7 braços superou
  10% / 3. Nenhum parâmetro do AG ficou sem ter sido variado.

### Achados da auditoria do zero (2026-09-18) — preliminares

Medidos sobre o indivíduo da bateria de 2026-09-18, reavaliado no motor atual. A próxima
bateria — com os controles — é que os confirma ou não; ficam aqui como hipótese a testar,
com o número que a motivou.

- **A identidade funcional medida está no piso.** A Layer 3 do evoluído dava 1/5, com
  p = 0,74 contra os 35 nulos, e a concordância de ranking comportamental dá τ = +0,19,
  com p = 0,14 — nenhuma das duas réguas funcionais o distingue de um roster aleatório.
  A política conta a mesma história: o Rushdown evoluído guardava mais do que avançava e
  era o **menos** agressivo dos cinco; o Zoner avançava mais do que recuava; o Turtle
  recuava mais do que guardava. Se a bateria confirmar, a resposta à pergunta de pesquisa
  é que o equilíbrio alcançado preserva a identidade **estrutural** (o drift segura os
  genes) e **não** a funcional — e o controle `λ_drift = 0` dirá quanto dessa preservação
  estrutural é do termo de drift.
- **O AG quase não enxerga a política pelo equilíbrio.** Na análise de sensibilidade com o
  passo da mutação, `w_retreat` e `w_defend` ficam abaixo do piso de ruído e
  `w_aggressiveness` no limiar. O único gradiente que puxa os pesos de volta ao canônico é
  o do drift — o que é coerente com a política embaralhada acima.
- **O stun era um gene de platô para o atacante rápido.** Até a correção dos timers, variar
  o stun do Rushdown evoluído em 31 valores dava 5 WR distintas; agora, 27.

## Limitações conhecidas

- O modelo de combate é uma **simplificação** de FGCs reais — sem frames de
  startup/recovery por golpe, mix-ups, neutral game, oclusão.
- **5 arquétipos** bastam para um ciclo; FGCs reais têm 10+.
- O fitness combina identidade e equilíbrio numa **soma ponderada** (escalar) ou
  **Pareto 2D** (NSGA-II) — outras formulações do trade-off são possíveis.
- O **round-robin** assume todos os arquétipos jogados igualmente — não modela
  matchmaking onde jogadores escolhem matchups favoráveis.
- **Inicialização assimétrica entre os dois algoritmos** (2026-09-16): o AG escalar
  inicia com `[canônico] + aleatórios`, o NSGA-II com população 100% aleatória. Não é
  descuido — é consequência medida da assimetria dos objetivos (ver Achados). Precisa
  ser declarado explicitamente ao comparar os dois.
- **As Layers 1-2 do validador são parcialmente endógenas** — medem o mesmo eixo
  estrutural que o `drift_penalty` otimiza. As réguas funcionais (Layer 3 e concordância)
  são *held-out*, não causalmente isoladas: cada asserção da Layer 3 é consequência quase
  direta de um gene definidor, e comportamento é downstream dos genes que o fitness move.
  A Layer 3 tem ainda só 5 bits; a concordância de ranking existe para isso.
- **A política é o que o AG menos enxerga.** Na escala da mutação, dois dos três pesos
  ficam abaixo do piso de ruído da sensibilidade (preliminar — ver acima). A análise é
  local, e muda com o indivíduo. Ver [05](05-methodological-validation.md).
- **Convergir não é ficar equilibrado.** `converged_at` é o primeiro disparo do gate que
  sobrevive à confirmação, num teste repetido a cada geração; a fração que termina
  equilibrada é outra métrica, e as duas vão juntas.

## O que ainda falta

A base experimental está **definida**, e falta rodá-la. Depois da bateria de 2026-09-18
o motor mudou (CRN por luta, timers com resto acumulado) e o protocolo ganhou os dois
controles, a manchete no `scalar_optimum` com a relação de Pareto, a concordância de
ranking e a validação externa com regras perturbadas. A bateria (`run_overnight.ps1`)
precisa rodar de novo, e os números desta pasta e do `docs/status/HANDOFF.md` §2 — os
achados acima inclusive, e em especial os preliminares — têm de ser relidos contra ela
antes de qualquer citação. As pendências de instrumentação de
[`../reference/10-known-issues.md`](../reference/10-known-issues.md) estão fechadas; o que
resta lá são os limites estruturais, que são escopo declarado e vão para a Discussão. Em termos de tese, falta a **redação**: a
monografia e os artigos descrevem gerações anteriores do modelo, e o `values.tex` está
inteiramente obsoleto (ver [`../status/HANDOFF.md`](../status/HANDOFF.md) §4). Os números a citar
saem de `results/` e do `docs/status/HANDOFF.md` §2 — nunca de rodadas anteriores ao motor atual, que
foram geradas sob outro modelo.
