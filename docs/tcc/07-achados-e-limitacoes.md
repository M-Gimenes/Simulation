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
  Removendo o seed (só do NSGA-II — no escalar ele ajuda), o NSGA-II passa a **vencer o
  AG escalar na própria função que o escalar otimiza** (L1 0,2115 contra 0,2945).
  Enquanto a fronteira estava contaminada, toda comparação media sub-convergência do
  NSGA-II, não trade-off. Vale como lição de método na Discussão: **um detalhe de
  inicialização pode inverter a conclusão de uma comparação entre algoritmos.**

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
- **O espelho é a objeção da banca com números.** Cinco personagens idênticos equilibram
  *melhor* que o roster evoluído (dominance 0,02–0,05 contra 0,049–0,084) e perdem
  identidade por apenas ~0,04 de drift. A tese precisa responder isso medindo, não
  argumentando. Leitura atual do AG novo: **99% do equilíbrio trivialmente alcançável**,
  com identidade **~30% acima do piso** (p ≈ 0,08 com 13 nulos — sugestivo, não
  estabelecido; mais nulos aumentam a resolução).
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
  o AG novo dá **3,0 com pares em 34%–66%** (arestas decididas, contagem válida). Essa é
  a frase para a tese, e ela não depende de nenhuma tabela inventada pelo autor.

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

## O que ainda falta (para fechar a base experimental)

Backlog técnico detalhado em [`../10-known-issues.md`](../reference/10-known-issues.md). Em
termos de tese, falta:
- **Calibrar e re-rodar tudo (passo de maior retorno):** o motor de combate e o
  objetivo mudaram (simplificação + reformulação **C2**), então **todas as rodadas
  anteriores estão invalidadas** — os números históricos (ex.: "`best_dominance` 8/10
  matchups") foram gerados sob o modelo antigo e **não devem ser citados**. Calibrar
  os provisórios (`MATCHUP_WR_CAP`, bound/valores de `stun`-fração, canônicos
  re-tunados, `ACTION_PERSISTENCE_SUBTICKS`) e então executar `multi_run` (10+ seeds),
  `external_validation` e a fronteira/HV, e **interpretar**. A infraestrutura de
  agregação (item 1.1) já está pronta.
- (O reporting já foi **realinhado** ao headline C2 — `analyze_matchups`, `multi_run`
  e `external_validation` reportam WR **global** por personagem + hard-counters; ver
  [`../reference/10-known-issues.md`](../reference/10-known-issues.md). Falta só
  **executar** com a calibração final.)
- **Os instrumentos já estão prontos:** leitura por indivíduo (`report`, `drift_table`
  com diferenciação, `fingerprint`, validador), agregação estatística (`multi_run`,
  item 1.1), qualidade de fronteira (`pareto_metrics`, item 1.2) e robustez fora do
  laço (`external_validation`, item 3.2). Ver o status completo em
  [08-metodologias-da-literatura.md](08-metodologias-da-literatura.md).
