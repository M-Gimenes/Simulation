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
  não-dominados**: na bateria de 2026-09-21 isso vale em 18 das 20 sementes, com uma
  semente para cada lado. O que **não** vale é o escalar vencer na própria função: na
  soma `dominance + drift` (λ = 1/1) a fronteira do NSGA-II tem um ponto melhor em
  **20/20** sementes no stream do laço (medianas 0,2658 contra 0,2052) — ver
  "O AG escalar perde na própria função" abaixo. Vale como lição de método na
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
| arestas do ciclo ⚠ | 5/10 (cada aresta é cara-ou-coroa) | 8/10 | 10/10 |
| concordância de ranking (τ, desde 2026-09-18) | +0,001 | +0,338 | 1,000 |

> ⚠ **A linha do ciclo foi refeita em 2026-09-22.** O piso de 5/10 segue válido (os nulos
> aleatórios têm arestas decididas), mas o "pior nulo 8/10" e qualquer valor de alvo medidos
> a 200 lutas por par são ruído: a margem mediana das arestas de um roster equilibrado é
> 0,048 contra σ = 0,035. A métrica saiu do `baselines` para
> `src.experiments.cycle_structure` — ver «O ciclo era medido numa resolução em que não
> funcionava», abaixo. As outras três linhas da tabela não são afetadas.

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

### Achados da bateria de 2026-09-23 (n = 20, dois controles + o braço híbrido)

> **Esta seção foi refeita sobre a bateria de 2026-09-23.** Ela re-executa a de 2026-09-21
> com os cinco consertos adiados aplicados e `MULTI_RUN_SIMS` = 1000 (era 200). Os
> indivíduos são **os mesmos** — 40 de 40 execuções com semente saíram bit a bit idênticas
> —, então **nenhum número de identidade mudou**. Mudou só o que a régua mede, e com ele
> **duas leituras viraram de lado**, ambas marcadas ⚠. Ver [04](04-design-decisions.md),
> «A política de adiar conserto inerte foi verificada».

Estes são os achados citáveis. Os números completos estão em
[`../status/HANDOFF.md`](../status/HANDOFF.md) §2 e o porquê de cada um em
[04](04-design-decisions.md), a partir de «O controle `λ_drift = 0`».

- **A identidade não custa equilíbrio, e o termo é o que a segura — este é o achado que
  responde à pergunta de pesquisa.** O controle `λ_drift = 0`, mesmo AG, mesma amostra,
  mesmo orçamento, **sem** o termo de identidade, **zera a identidade nas quatro réguas**:
  drift 0,4055 contra 0,2473, validador L1+L2 6 contra 11, Layer 3 1 contra 3, τ
  **−0,0304 contra 0,2811**, todas com p_Holm ≤ 0,0045 e efeito grande. Na média das 20
  execuções o braço sem drift dá τ = +0,007 ± 0,151: o acaso com três casas decimais.
  > ⚠ **Correção de 2026-09-23: o efeito no EQUILÍBRIO caiu de significativo para não
  > significativo.** A 200 lutas por par esta linha dava `dominance` 0,0534 contra 0,0399,
  > p_Holm = 0,038, e sustentava a frase "a identidade não custa equilíbrio — **melhora**".
  > A 1000 lutas, com os **mesmos indivíduos**, dá 0,0432 contra 0,0355, **p_Holm =
  > 0,059**. Sobrevivem a direção, o tamanho de efeito (Â₁₂ = 0,30, médio, inalterado) e o
  > p bruto (0,030); o que cai é a sobrevivência à correção de Holm sobre a família de 6.
  > O braço λ = 0 é o mais ruidoso dos dois, então a régua grossa o penalizava mais —
  > parte do que parecia efeito era a medida errando contra o braço ruidoso. A frase
  > defensável é *"tirar a identidade está associado a pior equilíbrio, com efeito médio
  > que não alcança significância"*. Os hard-counters também não separam (p = 0,180).
- **A identidade funcional está acima do acaso, e a régua que mostra isso é o controle —
  não os modelos nulos.** No indivíduo da seed 42 a Layer 3 dá 3/5 (p = 0,03, empatando
  com o melhor nulo) e τ = 0,314 (p = 0,06, um fio abaixo do melhor nulo, 0,316): um
  único roster contra 35 nulos não tem resolução para concluir. Contra o braço λ = 0, com
  20 execuções de cada lado, as duas separam com efeito grande. **Isto corrige a leitura
  preliminar de 2026-09-18**, que dava a identidade funcional no piso (L3 1/5, p = 0,74;
  τ = 0,19, p = 0,14).
- **A semente canônica não explica a diferença entre os algoritmos.** O segundo controle
  separa só no drift (0,2703 contra 0,2473, p_Holm 0,0073) e em mais nada.
- **Cada algoritmo ocupa um extremo, agora com seis métricas.** As seis da família de Holm
  são significativas com efeito grande, divididas exatamente nas duas metades da pergunta:
  o AG escalar vence as duas de equilíbrio (`dominance` 0,0355 contra 0,0759, Â₁₂ 0,07;
  hard-counters 0 contra 3, Â₁₂ 0,03) e o NSGA-II as quatro de identidade (drift Â₁₂ **1,00** — separação total —,
  L1+L2 0,05, Layer 3 0,24, τ 0,09). Fora da família, o contraste mais duro: **o AG termina
  com o roster equilibrado em 16/20 sementes e o NSGA-II em 0/20**.
- **A vantagem do AG em equilíbrio é quase toda de counters duros.** `global_term` 0,0318
  contra 0,0401 (perto), `cap_term` 0,0032 contra 0,0736 (longe). A frase certa é "os dois
  equilibram o roster globalmente parecido, e o NSGA-II deixa pares passarem do teto".
- **Equilibrar os cinco globalmente deixou de discriminar.** `n_chars_balanced` dá 5/5 em
  **80 de 80 execuções** — os dois algoritmos e os dois controles, inclusive o braço sem
  termo de identidade. O que discrimina são os pares.
- **Só o AG escalar replica fora do laço.** Único dos quatro rótulos ROBUSTO na replicação
  (`dominance` 0,0373 fora contra 0,0251 dentro — degradação de 1,5×, contra 21× na
  bateria pré-rotação), robusto a 4 das 8 regras perturbadas, 2 inconclusivas, 2 frágeis.
  Canônico, NSGA-II `scalar_optimum` e `knee_point` falham a replicação e as 8 regras.
- **O ciclo autoral não sobrevive ao equilíbrio** — e o objetivo é cego à direção por
  construção. O Grappler × Turtle, aresta canônica forte (100% no canônico), é achatado a
  51% ± 6% nas 20 sementes. **O número desta linha foi refeito em 2026-09-22** (era "5/10,
  posição 0%, p = 0,63", medido a 200 lutas por par, onde a direção de cada aresta é
  sorteio): ver «O ciclo era medido numa resolução em que não funcionava», abaixo.
- **Convergência é regra, não exceção — mesmo com a confirmação fora do stream.** O AG
  convergiu em 20/20 sementes, na geração 31,3 ± 13,2, embora a confirmação tenha recusado
  71% dos disparos do gate (50 de 70). Convergir é o **primeiro** sucesso de um teste
  repetido a cada geração, não equilíbrio estável: das 20 convergidas, 16 terminaram com o
  roster equilibrado na reavaliação — eram 14 a 200 lutas por par, e duas delas eram ruído
  da régua.
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

### O AG escalar não é ótimo na própria função (2026-09-22)

Investigação sobre os artefatos da bateria de 2026-09-21, scripts e dados em
`diagnostics/` (fora de `src/`, sem carimbo de proveniência). **Registro de trabalho em
`CONTINUE.md`**; o que está aqui é o achado. Ainda **não** rodou na bateria — os braços
abaixo usam as sementes 42–46, que são as da bateria, e por isso ainda não escolhem
configuração (ver «O que ainda falta»).

- **O NSGA-II vence o AG escalar na soma que o escalar otimiza.** Em `dominance + drift`
  (λ = 1/1), a fronteira tem um ponto melhor em **20/20** sementes no stream do laço
  (medianas 0,2658 contra 0,2052), o `scalar_optimum` vence em **18/20** na reavaliação e
  em **5/5** a 1000 lutas × 8 streams. Isso **não** contradiz a relação de Pareto: os dois
  seguem mutuamente não-dominados em 18/20, porque o ponto do AG fica *além* da ponta de
  menor dominance da fronteira em **19/20** (0,017 contra 0,05). Ele não está atrás da
  fronteira — está num extremo dela, e o extremo não é o ótimo de λ = 1/1.
- **A causa é uma assimetria de ruído entre os dois termos do escalar.** `drift` é
  determinístico; `dominance` é amostrado, com desvio 0,015–0,028 a 150 lutas (mesmo
  roster, 30 streams). Depois da geração ~31 — exatamente a geração média de convergência
  — o gradiente verdadeiro de `dominance` acabou e o que sobra é ruído ~60× maior que o
  ganho de drift por geração (0,0003). A seleção escalar gasta a pressão em sorte.
- **Sobreajuste ao stream, quantificado** (`dominance` no laço → reavaliado, medido a
  1000 lutas por par): AG escalar 0,0172 → 0,0355 (**1,80×**, pior em 17/20); controle
  λ = 0 0,0184 → 0,0432 (**2,33×**); NSGA-II 0,0559 → 0,0759 (1,25×). *(A 200 lutas as
  mesmas razões liam 2,58× / 3,21× / 1,52× — a régua grossa inflava todas, e mais a de
  quem tem mais ruído. A ordenação entre os três, que é o achado, não muda.)* **Quanto mais a seleção se concentra no termo ruidoso,
  mais a execução compra sorte** — e o braço sem identidade, que só tem o termo ruidoso,
  é o pior dos três. Casa com os 71% de disparos do gate recusados pela confirmação.
- **A linhagem fiel morre na geração 7.** Réplica instrumentada da seed 42
  (`diagnostics/data/base42.json`, reproduz o artefato bit a bit): o drift mínimo da
  população sai de 0,0000 (g0–g2, a semente canônica) para 0,17 em **g7** e 0,24 em g20,
  quando `dominance` ainda tinha 1,13 dos seus 1,35 por entregar. Em g20 a população é um
  aglomerado de largura 0,045 (mínimo 0,2406, mediana 0,2861): não sobrou diversidade de
  drift para recombinar, e as 130 gerações seguintes rendem 0,05. No NSGA-II isso não
  ocorre — `drift` é objetivo separado e sem ruído, e o extremo de drift baixo fica
  protegido no rank 0 pela crowding infinita. É **multi-objetivização** (Knowles, Watson
  & Corne 2001) agindo como robustez a ruído, leitura que [08](08-literature-methods.md)
  ainda não cobre.
- **Consequência para a pergunta de pesquisa: o trade-off medido é um teto do custo da
  identidade, não o custo.** Um híbrido NSGA-II 75 gerações → AG escalar 75 (**orçamento
  igual**, mesmas 300 × 150 no total) reavaliado a 1000 lutas em 4 sorteios novos:

  | braço | dom | hard counters | drift | L1+L2 | L3 | τ | soma |
  |---|---|---|---|---|---|---|---|
  | AG escalar | 0,0380 | 0,30 | 0,2396 | 12,2 | 2,40 | +0,284 | 0,2776 |
  | NSGA-II `scalar_optimum` | 0,0835 | 3,50 | 0,1487 | 15,4 | 4,00 | +0,593 | 0,2322 |
  | **híbrido, orçamento igual** | **0,0254** | **0,30** | **0,1664** | **15,2** | **4,40** | **+0,551** | **0,1918** |
  | híbrido com 2× orçamento | 0,0364 | 0,30 | 0,1492 | 15,0 | 4,00 | +0,606 | 0,1856 |

  Contra o AG escalar, por semente: melhor em `dominance` **4/5**, em drift **5/5**, em τ
  **5/5**, empate em hard counters e em elencos equilibrados (14/20 contra 16/20 medições,
  dentro do ruído). Boa parte do que hoje se lê como "o AG troca identidade por
  equilíbrio" é **falha de busca sob avaliação ruidosa**, não trade-off da função — o que
  torna a resposta à pergunta de pesquisa mais afirmativa, não menos.
- **`MULTI_RUN_SIMS = 200` não tem resolução para ranquear rosters.** O veredito acima
  **inverteu** entre 200 sims (um stream) e 1000 sims (quatro): a 200, o híbrido parecia
  pagar equilíbrio pela identidade. Serve de alerta de método: o ruído de medição é
  simétrico entre braços e a média de n = 20 o dilui, então os agregados da bateria
  seguem válidos — mas **nenhuma leitura por semente, nem nenhuma comparação em amostra
  pequena, pode ser feita a 200**. Ver [04](04-design-decisions.md) e
  [09](09-values-and-choices.md).

### O híbrido responde o achado do AG escalar (2026-09-23)

O achado de 2026-09-22 dizia que a escalarização direta perde a linhagem fiel sob
avaliação ruidosa, e que o trade-off medido era um **teto** do custo da identidade. A
bateria de 2026-09-23 mediu a correção com n = 20 e orçamento inteiro.

| métrica | AG escalar | híbrido | p (Holm) | Â₁₂ |
|---|---|---|---|---|
| `dominance_penalty` | 0,0355 | 0,0287 | 1,00 | 0,51 (desprezível) |
| hard-counters | 0 | 0 | 1,00 | 0,49 (desprezível) |
| `drift_penalty` | 0,2473 | **0,1663** | **1,1 × 10⁻⁵** | 0,97 (grande) |
| validador L1+L2 | 11 | **15** | **0,0026** | 0,12 (grande) |
| validador L3 | 3 | **4** | **0,0058** | 0,24 (grande) |
| concordância τ | 0,2811 | **0,5215** | **0,00084** | 0,15 (grande) |

- **O custo da identidade era mesmo um teto, e o teto era alto.** Repartir o mesmo
  orçamento entre 75 gerações de NSGA-II e 75 do AG escalar recupera a identidade do
  NSGA-II **sem mover nenhuma das duas métricas de equilíbrio** — Â₁₂ 0,51 e 0,49, e
  16/20 rosters equilibrados nos dois braços. Boa parte do que a tese lia como "o AG troca
  identidade por equilíbrio" era **falha de busca sob avaliação ruidosa**, não trade-off
  da função.
- **O híbrido pega a metade boa de cada algoritmo.** Contra o NSGA-II: mesma identidade
  (drift 0,1708 contra 0,1484; τ +0,484 contra +0,521; Layer 3 3,70 contra 3,65) com
  **0,25 hard-counters contra 2,80** e **16/20 rosters equilibrados contra 0/20**.
- **O mecanismo se confirmou em três lugares**, e não só no resultado: o drift do híbrido
  para onde o NSGA-II para (a linhagem fiel sobreviveu à fase 1); o sobreajuste ao stream
  cai para **1,67×** contra 1,80× do escalar e 2,33× do controle λ = 0, na ordem que a
  teoria prevê; e a convergência chega tarde — geração **98,3 ± 20,2** contra 31,3 ± 13,2,
  com 81% dos disparos do gate recusados contra 71%. **Velocidade é o único preço**, e é
  esperado: as 75 primeiras gerações são de Pareto e não perseguem o predicado de
  equilíbrio.
- **O que isso muda na resposta à pergunta de pesquisa.** "Dá para equilibrar sem destruir
  as identidades funcionais?" fica mais afirmativa: com o mesmo orçamento, τ sobe de
  +0,281 para +0,522 e a Layer 3 de 3 para 4, sem perder equilíbrio. A régua funcional —
  a que a pergunta nomeia — quase dobra.
- **Ressalva:** a configuração (split 0,5, carregando a fronteira inteira) veio do
  desempate de simplicidade, não de evidência; no orçamento reduzido nenhum braço passou
  no filtro de equilíbrio e a ordenação entre splits não transferiu. Afirmar que 0,5 é o
  **melhor** split exigiria um sweep no orçamento inteiro, que não foi feito. O que está
  medido é que **este** split não cobra equilíbrio pela identidade que entrega.

### O ciclo era medido numa resolução em que não funcionava (2026-09-22)

Achado de método com consequência direta numa afirmação da tese. `cycle_edges_kept` vivia
no `baselines`, medido a `MULTI_RUN_SIMS` = 200 lutas por par — e a margem mediana das
arestas de um roster **equilibrado** é 0,048, contra um desvio binomial de 0,035 a 200
lutas. Nessa resolução a direção de cada aresta é cara-ou-coroa.

O que expôs isso foram os **espelhos**: cinco cópias do mesmo arquétipo, estrutura de
torneio zero por construção, marcavam **5,40/10 "mantidas" com 1,00/10 decididas**. Uma
métrica que dá acima do piso num roster sem nenhuma estrutura está medindo sorteio. E o
mesmo roster do dossiê lê **5/10 a 200 lutas e 8/10 a 16.000**.

Refeito em `src/experiments/cycle_structure.py` (16 × 1000 = 16.000 lutas por par,
σ = 0,0040), contando só as arestas **decididas** (`|WR − 0,5| > 2σ`):

| grupo | n | mantidas | decididas | mantidas **E** decididas | margem mediana | tríades |
|---|---|---|---|---|---|---|
| canônico | 1 | 6,00/10 | 10,00/10 | 6,00/10 | 0,5000 | **1,00** |
| AG escalar | 20 | 5,60/10 | 9,30/10 | 5,25/10 | 0,0481 | 3,71 |
| NSGA-II | 20 | 4,95/10 | 9,85/10 | 4,90/10 | 0,1037 | 4,17 |
| espelhos (controle de ruído) | 5 | 5,40/10 | **1,00/10** | 0,60/10 | 0,0033 | 2,59 |
| aleatórios (piso) | 30 | 4,97/10 | 10,00/10 | 4,97/10 | 0,4909 | 0,40 |

- **O veredito não mudou de sinal, mudou de qualidade.** O AG mantém **105 de 186 arestas
  decididas — 56,5%, binomial p = 0,091**; os 30 nulos ficam em 49,7% (p = 0,128,
  Â₁₂ = 0,63); o NSGA-II dá 4,90/10. A frase certa não é "destruído" nem "preservado", é
  **indistinguível do acaso**, com inclinação fraca e não significativa na direção autoral.
- **Achado novo que a resolução antiga escondia: o canônico também não tem um ciclo.**
  Realiza 6/10, e as 4 arestas que quebra são **inversões totais** (Combo Master >
  Grappler 0,002; Grappler > Rushdown 0,006; Turtle > Rushdown 0,000; Turtle > Combo
  Master 0,000). Lidas juntas: o Rushdown ganha de todos e a Turtle perde para todos —
  hierarquia, não pedra-papel-tesoura. As tríades confirmam: **1,00 de 5** no canônico
  contra 3,71 do AG e 0,40 dos aleatórios. **A estrutura cíclica não foi destruída pelo
  equilíbrio; ela nunca existiu no motor.** Isso reforça o argumento já registrado em
  [02](02-canonical-cycle.md): não se preserva o que a premissa não tinha.
- **Quem produz não-transitividade é o AG**, com ressalva: equilíbrio global com pares
  decididos **força** intransitividade (um roster estritamente transitivo teria WRs
  100/75/50/25/0), então as 3,71 tríades são em boa parte consequência do objetivo, não
  evidência independente dele. O que o objetivo não implica é as arestas seguirem
  decididas — e 9,3/10 decididas a 16.000 lutas é o que mostra isso.
- **Consequência de instrumentação:** as duas métricas saíram do `baselines` (que mede 36
  rosters a 200 lutas e não podia subir de resolução junto) para um experimento próprio,
  passo 17 da bateria. O campo `beats` fica no código: é premissa declarada e a parte
  verificável da não-circularidade. Ver [04](04-design-decisions.md), «O ciclo saiu do
  `baselines`».

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
- **O drift protege as cinco identidades com rigor desigual.** `defining_genes` tem 1
  gene no Combo Master (`stun`) e 4 na Turtle. Como os definidores pesam 3,0 e a RMS
  normaliza pela soma dos pesos, o Combo Master concentra **23%** do peso no gene que o
  define e a Turtle **63%** nos seus quatro. "Identidade preservada" é medida com
  exigência diferente por arquétipo — consequência de as definições terem cardinalidades
  diferentes, não erro de cálculo, mas precisa ser declarada ao comparar drift **entre**
  personagens.
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

**A base experimental está rodada.** A bateria de 2026-09-21 cobriu os 16 passos que
existiam então, sobre o motor atual e com os dois controles; o passo 17
(`cycle_structure`) foi criado e rodado em 2026-09-22, à parte. `py -m
src.tests.test_provenance` marca todo `results/` como *atual* ou *braço de experimento*, e
os achados acima são desses artefatos. Em
[`../reference/10-known-issues.md`](../reference/10-known-issues.md) restam **uma pendência
acionável** (o híbrido, abaixo), **cinco consertos adiados** que só valem junto da próxima
re-execução, e os limites estruturais, que são escopo declarado e vão para a Discussão.

**A decisão que estava em aberto foi fechada em 2026-09-23:** o híbrido NSGA-II → AG
escalar foi medido com n = 20 no orçamento inteiro e **adotado como terceiro braço do
protocolo** — mesma balança, identidade muito maior. Ver «O híbrido responde o achado do AG
escalar», acima, e [04](04-design-decisions.md) para a decisão. O que sobrou de aberto
dali é uma pergunta menor e declarada: **qual o melhor split**, que exigiria um sweep no
orçamento inteiro. O 0,5 atual veio do desempate de simplicidade.

Falta a **redação**: a monografia e os artigos descrevem gerações anteriores do modelo, e
o `values.tex` está inteiramente obsoleto — agora com números definitivos para refazê-lo
(ver [`../status/HANDOFF.md`](../status/HANDOFF.md) §4). Os números a citar saem de
`results/` e do `docs/status/HANDOFF.md` §2 — nunca de rodadas anteriores ao motor atual,
que foram geradas sob outro modelo.
