# 07 — Achados, limitações e o que falta

**Entra em**: Resultados / Discussão / Limitações.

## Achados

- **O modelo representa bem os arquétipos** (revisão do combate,
  [`../11-combat-review.md`](../reference/11-combat-review.md)): comportamento distinto e
  on-concept — Rushdown rusha, Turtle muralha, Zoner kita; DEFEND/RETREAT e
  espaçamento são usados de forma significativa. **Achado positivo** — o modelo não é
  uma caixa-preta arbitrária; os pesos produzem identidade comportamental visível.
- **O ciclo canônico não é trivialmente preservado em modo determinístico (baseline):**
  sem combo chaining / variância, muitos matchups do canônico ficam binários (100/0).
  Interpretação (ver [02](02-ciclo-canonico.md)): a estrutura FGC depende parcialmente
  de mecânicas estocásticas que foram removidas — é **achado, não falha**. *Cuidado*:
  distinguir esta quebra **do baseline** da quebra **pós-balanceamento** — esta última
  era forçada pelo objetivo antigo (WR por-matchup) e deixou de ser sob a reformulação
  **C2** (ver abaixo e [02](02-ciclo-canonico.md)).
- **`LAMBDA_DRIFT` alto prende o AG no canônico** (V1): com 6.0, o melhor indivíduo
  ficava colado no canônico (drift ≈ 0) e desbalanceado, porque mover-se custava ~6× o
  ganho em equilíbrio. Daí a decisão de `LAMBDA_DRIFT = 1.0` e o foco no NSGA-II (ver
  [04](04-caminhos-e-decisoes.md)).
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
  [03](03-formulacao-do-fitness.md).
- **Identidade precisou de duas réguas, e uma delas não pode ser citada como prova.** O
  `drift_penalty` (estrutural, no fitness) e o validador discordavam: 0,261 lido como
  "preservada" contra 8/21 lido como "destruída". Não era homogeneização, era **troca de
  papéis** — distância euclidiana é cega a **ranking**. Corrigido normalizando pelo range
  do bound e ponderando os genes definidores. Consequência a declarar: as **Layers 1-2 do
  validador ficaram parcialmente endógenas** (medem o eixo que o fitness otimiza) e valem
  como diagnóstico, não como prova; quem sustenta a leitura de identidade preservada é a
  **Layer 3** (comportamental) somada ao ciclo. A pergunta da tese diz *"functional
  identities"* — comportamento, não valor de gene.
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
identidade eram lidas contra o **teto**, como se o piso fosse zero. Medido com 13 rosters
nulos (5 espelhos + 8 aleatórios):

| métrica | piso | pior nulo | teto |
|---|---|---|---|
| validador (L1-L3) | ~6,8/21 | **12/21** | 21/21 |
| `drift_penalty` | ~0,33 (espelho) · ~0,41 (aleatório) | 0,326 | 0,000 |
| arestas do ciclo | 5/10 (analítico) | 8/10 | 10/10 |

Consequências para a redação:

- **Nunca citar valor cru.** Reportar `posição = (valor − piso)/(teto − piso)` e o
  p-valor empírico. O indivíduo antigo do `results.json`, lido como "8/21 = identidade
  destruída", está **no piso** (p = 0,46) — indistinguível de um roster aleatório.
- **O espelho é a objeção com números.** Cinco personagens idênticos são a solução trivial
  do equilíbrio e perdem identidade por apenas ~0,04 de drift, então a tese precisa
  responder isso medindo, não argumentando. **A leitura virou favorável**: na bateria atual
  o roster evoluído chega a **102% do equilíbrio trivialmente alcançável** — é *mais*
  equilibrado que o espelho (dominance 0,026 contra 0,025 do melhor espelho, 1,136 do
  aleatório) — sentado a **47%** do caminho entre o piso e o teto de identidade, e supera
  **todos os 35 nulos** nos três eixos de identidade (p < 0,03 em cada). Era 99% e
  p ≈ 0,08 com 13 nulos; o que mudou foi o motor **e** a resolução do p (que é 1/N).
- **O ciclo canônico não pode ser achado, e isso é demonstrável.** Ele é um torneio
  **regular** (cada arquétipo vence 2 e perde 2), e existem **24** torneios regulares
  rotulados em 5 vértices: acertar o rótulo específico é 1/24, e o acaso já entrega 5/10
  arestas. Calibrar o motor para realizá-lo é perseguir uma loteria cujo sucesso não
  distinguiria preservação de sorte.
- **O que substitui o ciclo é a não-transitividade.** Equilíbrio global e
  pedra-papel-tesoura são a **mesma estrutura**: um roster estritamente transitivo tem
  WRs 100/75/50/25/0, incompatível com todos perto de 50%. Logo o objetivo C2 não apenas
  *permite* o ciclo — ele **força** estrutura não-transitiva quando os pares são
  decididos. Medido em tríades circulares (0 = ordem estrita · 2,5 = acaso · 5 = máximo):
  o roster do AG na bateria dá **4,0 com pares em 43%–55%** (arestas decididas, contagem
  válida). Essa é a frase para a tese, e ela não depende de nenhuma tabela inventada pelo
  autor.

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
- **Os três sweeps exploratórios testaram os valores vigentes e os três passaram** — λ,
  pesos do dominance e, por último, elitismo / torneio, onde nenhum dos 7 braços superou
  10% / 3. Nenhum parâmetro do AG ficou sem ter sido variado.

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
  estrutural que o `drift_penalty` otimiza. A Layer 3 é *held-out*, não causalmente
  isolada: comportamento é downstream dos genes que o fitness move.
- **Dois genes ficam no limiar do piso de ruído.** Na sensibilidade do indivíduo evoluído
  (600 sims, 12 repetições do piso) `knockback` e `speed` têm sinal/ruído ~1,1: o AG mal
  os enxerga em volta desse indivíduo. Nenhum gene fica abaixo do piso, e a análise é
  local — no indivíduo em que se decidiu a persistência o `speed` tinha 2,0. Ver
  [05](05-validacao-metodologica.md).

## O que ainda falta

A base experimental está **fechada**: motor e fitness calibrados, os três sweeps
exploratórios feitos e a bateria com n = 20 regerada sob o motor final (2026-09-18).
As pendências de instrumentação de
[`../reference/10-known-issues.md`](../reference/10-known-issues.md) também estão fechadas; o
que resta lá são os limites estruturais, que são escopo declarado e vão para a Discussão.
Uma operação pendente, sem efeito em número: o pool de processos ficou persistente depois da
bateria, o que mudou o digest do motor, e a bateria precisa rodar de novo para os artefatos
voltarem a ler "atual" — a seed 42 já reproduziu bit a bit. Em termos de tese, falta a
**redação**: a
monografia e os artigos descrevem gerações anteriores do modelo, e o `values.tex` está
inteiramente obsoleto (ver [`../../HANDOFF.md`](../../HANDOFF.md) §5). Os números a citar
saem de `results/` e do `HANDOFF.md` §3 — nunca de rodadas anteriores ao motor atual, que
foram geradas sob outro modelo.
