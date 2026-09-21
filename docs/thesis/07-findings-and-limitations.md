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

### Achados da bateria de 2026-09-21 (n = 20, com os dois controles)

Estes são os achados citáveis. Os números completos estão em
[`../status/HANDOFF.md`](../status/HANDOFF.md) §2 e o porquê de cada um em
[04](04-design-decisions.md), a partir de «O controle `λ_drift = 0`».

- **A identidade sai de graça — é o achado que responde à pergunta de pesquisa.** O
  controle `λ_drift = 0`, mesmo AG, mesma amostra, mesmo orçamento, **sem** o termo de
  identidade, não equilibra melhor (`dominance` 0,0534 contra 0,0399, p_Holm 0,063 — e a
  favor do AG *com* o termo; hard-counters empatados em 0, p = 0,553) e **zera a
  identidade nas quatro réguas**: drift 0,4055 contra 0,2473, validador L1+L2 6 contra 11,
  Layer 3 1 contra 3, τ **−0,0304 contra 0,2811**, todas com p_Holm ≤ 0,00024 e efeito
  grande. Na média das 20 execuções o braço sem drift dá τ = +0,007 ± 0,151: o acaso com
  três casas decimais.
- **A identidade funcional está acima do acaso, e a régua que mostra isso é o controle —
  não os modelos nulos.** No indivíduo da seed 42 a Layer 3 dá 3/5 (p = 0,03, empatando
  com o melhor nulo) e τ = 0,314 (p = 0,06, um fio abaixo do melhor nulo, 0,316): um
  único roster contra 35 nulos não tem resolução para concluir. Contra o braço λ = 0, com
  20 execuções de cada lado, as duas separam com efeito grande. **Isto corrige a leitura
  preliminar de 2026-09-18**, que dava a identidade funcional no piso (L3 1/5, p = 0,74;
  τ = 0,19, p = 0,14).
- **A semente canônica não explica a diferença entre os algoritmos.** O segundo controle
  separa só no drift (0,2703 contra 0,2473, p_Holm 0,043) e em mais nada.
- **Cada algoritmo ocupa um extremo, agora com seis métricas.** As seis da família de Holm
  são significativas com efeito grande, divididas exatamente nas duas metades da pergunta:
  o AG escalar vence as duas de equilíbrio (`dominance` Â₁₂ 0,10; hard-counters 0 contra
  3, Â₁₂ 0,03) e o NSGA-II as quatro de identidade (drift Â₁₂ **1,00** — separação total —,
  L1+L2 0,05, Layer 3 0,24, τ 0,09). Fora da família, o contraste mais duro: **o AG termina
  com o roster equilibrado em 14/20 sementes e o NSGA-II em 0/20**.
- **A vantagem do AG em equilíbrio é quase toda de counters duros.** `global_term` 0,0397
  contra 0,0490 (perto), `cap_term` 0,0030 contra 0,0807 (longe). A frase certa é "os dois
  equilibram o roster globalmente parecido, e o NSGA-II deixa pares passarem do teto".
- **Equilibrar os cinco globalmente deixou de discriminar.** `n_chars_balanced` dá 5/5 em
  **80 de 80 execuções** — os dois algoritmos e os dois controles, inclusive o braço sem
  termo de identidade. O que discrimina são os pares.
- **Só o AG escalar replica fora do laço.** Único dos quatro rótulos ROBUSTO na replicação
  (`dominance` 0,0373 fora contra 0,0251 dentro — degradação de 1,5×, contra 21× na
  bateria pré-rotação), robusto a 4 das 8 regras perturbadas, 2 inconclusivas, 2 frágeis.
  Canônico, NSGA-II `scalar_optimum` e `knee_point` falham a replicação e as 8 regras.
- **O ciclo autoral não sobrevive ao equilíbrio.** 5/10 arestas, a média exata dos nulos,
  posição 0%, p = 0,63 — o objetivo é cego à direção por construção. O Grappler × Turtle,
  aresta canônica forte (100% no canônico), é achatado a 51% ± 6% nas 20 sementes.
- **Convergência é regra, não exceção — mesmo com a confirmação fora do stream.** O AG
  convergiu em 20/20 sementes, na geração 31,3 ± 13,2, embora a confirmação tenha recusado
  71% dos disparos do gate (50 de 70). Convergir é o **primeiro** sucesso de um teste
  repetido a cada geração, não equilíbrio estável: das 20 convergidas, 14 terminaram com o
  roster equilibrado na reavaliação.
- **O AG quase não enxerga a política pelo equilíbrio.** Na sensibilidade (11 genes,
  janela 2σ, piso medido em 3,5%) os três pesos ocupam o fundo do ranking: `w_defend` 2,9%
  e `w_aggressiveness` 3,0% abaixo do piso, `w_retreat` 4,8% no limiar, contra `range`
  30,8% no topo. O único gradiente que os puxa de volta ao canônico é o do drift — e o
  controle λ = 0 mostra o que acontece sem ele.
- **Os três sweeps testaram os valores vigentes e os três se mantiveram**, mas duas
  conclusões mudaram de forma: λ = 1,0 deixou de empatar com os λ menores e passou a
  **dominá-los** (mesmo `dominance`, drift 0,10–0,13 melhor, τ dez vezes maior), e o
  default de elitismo/torneio deixou de ser o melhor em counters e em `cap_term` — é
  mantido por ter o melhor drift e a melhor concordância de ranking dos oito braços, e a
  afirmação passou de "nenhum braço os supera" para "**nenhum braço os domina**".
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
  ficam abaixo do piso de ruído da sensibilidade e o terceiro no limiar (medido na bateria
  de 2026-09-21 — ver acima). A análise é local, e muda com o indivíduo. Ver
  [05](05-methodological-validation.md).
- **Convergir não é ficar equilibrado.** `converged_at` é o primeiro disparo do gate que
  sobrevive à confirmação, num teste repetido a cada geração; a fração que termina
  equilibrada é outra métrica, e as duas vão juntas.

## O que ainda falta

**A base experimental está rodada.** A bateria de 2026-09-21 cobriu os 16 passos sobre o
motor atual, com os dois controles, e `py -m src.tests.test_provenance` marca todo
`results/` como *atual* ou *braço de experimento*. Os achados acima são os dela. As
pendências de instrumentação de
[`../reference/10-known-issues.md`](../reference/10-known-issues.md) estão fechadas; o que
resta lá são os limites estruturais, que são escopo declarado e vão para a Discussão.

Falta a **redação**: a monografia e os artigos descrevem gerações anteriores do modelo, e
o `values.tex` está inteiramente obsoleto — agora com números definitivos para refazê-lo
(ver [`../status/HANDOFF.md`](../status/HANDOFF.md) §4). Os números a citar saem de
`results/` e do `docs/status/HANDOFF.md` §2 — nunca de rodadas anteriores ao motor atual,
que foram geradas sob outro modelo.
