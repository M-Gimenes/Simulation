# 05 — Validação metodológica

**Entra em**: Metodologia (validação) e/ou Resultados.

Pilares de validação que sustentam a credibilidade dos experimentos. Os dois
primeiros (reprodutibilidade, sensibilidade) validam o **método**; os quatro
seguintes (N execuções, comparação estatística, qualidade da fronteira, validação
externa) constituem o **protocolo experimental** incorporado da literatura — ver o
status em
[08-literature-methods.md](08-literature-methods.md). O "como" de cada
ferramenta está em [`../reference/08-tools.md`](../reference/08-tools.md).

## Reprodutibilidade

- O combate sorteia com `np.random` **dentro do JIT (Numba)**, cujo RNG é independente
  do `np.random` de nível Python e **só semeável de dentro de um `@njit`**. Por isso a
  reprodutibilidade não é trivial — e era um ponto silenciosamente quebrado (ver a
  trajetória em [04-design-decisions.md](04-design-decisions.md)).
- **Como é garantida hoje:** **Common Random Numbers com uma semente por luta** — cada
  luta do round-robin é semeada a partir do seed-base, do par e do número da luta, e o
  seed-base é propagado aos workers do paralelismo. Reprodutível independente de qual
  worker avalia, e a luta *k* do par *m* recebe os mesmos sorteios em todo indivíduo (a
  diferença de fitness reflete genes, não sorteio → seleção menos enganada). Detalhe técnico em
  [`../reference/09-reproducibility.md`](../reference/09-reproducibility.md).
- **Ponto para a tese:** experimentos com `--seed` são **replicáveis** (afirmação que
  uma tese de método precisa poder fazer), e foi **verificado empiricamente**.

## Análise de sensibilidade — o AG enxerga todos os genes?

- **Pergunta:** algum dos 11 genes — os 8 atributos e os 3 pesos da política — é
  **neutro**, isto é, sem pressão seletiva, de modo que ele só drifta por random walk e
  não é "otimizado"?
- **Como medir** (`sensitivity_analysis`): para cada (arquétipo, gene), deslocar o gene
  numa janela de 2σ — o σ que a mutação usa nele — e medir `Δ WR` **global** do
  personagem. Perto do bound a janela **desliza** para dentro em vez de ser cortada (senão
  um gene encostado no limite pareceria menos visível só por estar na borda). Genes cuja
  média de `|Δ|` fica **abaixo do piso medido** são neutros; `≤ 2× piso` é borderline.
- **O piso é medido, não estimado, e na estatística que é classificada.** O piso analítico
  (`sqrt(0.25/(4·sims))`, ±1,8% a 200 sims) é o desvio de **uma proporção**, mas o número
  classificado é a **média, sobre os 5 personagens, de |Δ|** — uma diferença entre duas
  WRs, médias de cinco. O tool roda exatamente essa estatística sob a hipótese nula —
  janela de largura zero, os dois lados sob seeds diferentes (`--null-reps`) — e fica com o
  maior valor que o ruído produziu. Até 2026-09-18 o piso era o máximo de **uma célula**,
  outra grandeza (a média de 5 varia bem menos): 0,068 contra 0,037 na estatística certa,
  no mesmo evoluído. Seeds diferentes são necessárias: com a mesma seed e janela zero as
  avaliações são bit-idênticas e o Δ sai 0. Quebrar o pareamento dá um piso **conservador**
  (a medição real usa CRN pareado), que é o lado seguro. O piso e a classificação vão no
  artefato JSON junto da matriz completa.
- **Onde medir importa tanto quanto como.** O tool rodava fixo no canônico, que é
  **saturado** (Rushdown ~100% global, Turtle ~0%): com a WR presa no teto, perturbar um
  gene não muda nada e quase tudo saía "neutro" por efeito de teto, não por neutralidade —
  a tabela sustentava o contrário do que se quer afirmar. A medida citável é a do
  `--evolved`, num roster equilibrado. **Leitura preliminar**, no evoluído da bateria de
  2026-09-18 com o motor atual (a bateria seguinte a substitui): contra o piso de 0,037,
  seis atributos saem visíveis (`range` 0,403 · `attack_cooldown` 0,286 · `damage` 0,202 ·
  `hp` 0,175 · `stun` 0,106 · `grab_power` 0,085), `speed` e `knockback` (0,055) e
  `w_aggressiveness` (0,049) borderline, e `w_retreat` (0,026) e `w_defend` (0,024)
  **abaixo do piso**. A limitação a declarar muda de lugar: na escala da mutação, o AG
  quase não enxerga a **política** pelo equilíbrio — o único gradiente que a puxa ao
  canônico é o do drift. A análise é **local** — mede a paisagem em volta de um indivíduo
  e muda com ele.
- **Variância controlada:** usa pareamento de seeds (*common random numbers*) entre os
  dois lados da janela — técnica que **só funciona após o fix de reprodutibilidade**
  (antes, ineficaz).
- **Para que serve na tese:** sustenta a afirmação de que a seleção atua sobre todo o
  cromossomo (ou identifica explicitamente quais genes são inertes — foi o caso do
  antigo `recovery`, cuja neutralidade motivou sua remoção; ver
  [07-findings-and-limitations.md](07-findings-and-limitations.md)). Valida o **método**, não a
  qualidade do indivíduo — mas *precisa* de um indivíduo não-saturado para medir, e é
  por isso que a medida citável é a do `--evolved`, não a do canônico.

## Múltiplas execuções independentes + estatística agregada (item 1.1)

- **Pergunta:** um AG é estocástico — um resultado de **uma seed** é representativo, ou
  é azar/sorte daquela amostra?
- **Como** (`multi_run`): rodar AG e NSGA-II sobre N sementes (20 — o menor n com poder
  ≥ 80% para um efeito grande), reavaliar o melhor
  indivíduo de cada uma sob uma seed de validação comum, e reportar **média ± desvio**
  de dominance/drift, **WR global por personagem**, a **fração de sementes que
  equilibram o roster** (5 bonecos em banda, 0 hard-counters) e a **identidade** de cada
  roster (validador estrutural e comportamental, concordância de ranking). Fontes: Eiben &
  Smith 2015; Deb 2001.
- **Controles**, com a mesma amostra e o mesmo orçamento: o AG com `λ_drift = 0` (quanta
  identidade sobra sem o termo de drift) e o AG sem a semente canônica (quanto da diferença
  entre os algoritmos é inicialização). Os nulos do `baselines` não são otimizados, e
  vencê-los em drift é garantido por construção; o controle é o contrafactual certo.
- **Para que serve na tese:** é o **piso metodológico** — substitui "numa execução, deu
  X" por *"em N execuções, X% equilibraram o roster; WR global média 50±k%"*.
  Resolve diretamente a fragilidade de seed única: um par travado numa seed vira
  pergunta respondível — azar ou estrutural?

## Comparação estatística entre algoritmos (parte do item 1.1)

- **Pergunta:** o `multi_run` dá média ± desvio de cada algoritmo. Quando a média de um
  é melhor que a do outro, isso é diferença real ou amostragem de 20 execuções?
- **Como** (`compare_algorithms`): sobre as amostras por semente já gravadas,
  **Mann-Whitney U** bicaudal (não-paramétrico, não assume normalidade) +
  **Â₁₂ de Vargha-Delaney** (tamanho de efeito — o `p` diz se a diferença existe, o Â₁₂
  diz se ela importa) + **Holm-Bonferroni** numa família fixa de 7 métricas — equilíbrio
  (dominance, counters, bonecos em banda) e identidade (drift, validador estrutural e
  comportamental, concordância) —, a mesma em toda comparação, com as degeneradas (amostra
  conjunta constante, Mann-Whitney indefinido) fora. Fontes: Derrac et al. 2011; Arcuri &
  Briand 2011; Vargha & Delaney 2000 (limiares do Â₁₂); Holm 1979 — todas já nos três
  `.bib`. Explicação do aparato, do zero:
  [`../reference/12-statistical-testing.md`](../reference/12-statistical-testing.md).
- **Para que serve na tese:** é o que separa "o AG escalar deu média menor" de "o AG
  escalar é melhor nessa métrica". O NSGA-II devolve uma fronteira, então a comparação
  depende de **qual ponto** a representa: a manchete usa o `scalar_optimum`, o comparável
  do escalar, decidido antes da bateria; e a **relação de Pareto por semente** — o ponto do
  AG contra a fronteira inteira, no mesmo stream — não depende de ponto nenhum. O mesmo
  aparato compara a bateria com cada controle (`--control`).

## Qualidade da fronteira de Pareto: hipervolume + spacing (item 1.2)

- **Pergunta:** comparar fronteiras "no olho" não escala — como quantificar se uma
  fronteira é melhor (mais próxima da utopia e mais espalhada) que outra?
- **Como** (`pareto_metrics`): **hipervolume** (área dominada vs ponto de referência
  fixo `(1.3, 0.4)`, ancorado nos modelos nulos — `dominance` do canônico e drift do
  espelho; maior = melhor) e **spacing** de Schott (uniformidade; menor = melhor). Com a
  referência antiga, (2,0; 1,0), o HV saturava em 90% da área. Fontes: Deb 2001/2002.
- **Para que serve na tese:** comparação **objetiva** entre seeds e entre configurações
  (efeito de `MATCHUP_WR_CAP`, `SIMS_PER_MATCHUP`, etc.) sem inspeção visual. Métrica
  madura e esperada num trabalho com NSGA-II.

## Validação externa ao fitness (item 3.2)

- **Pergunta:** o equilíbrio de um indivíduo evoluído se **replica** com mais lutas, e é
  **robusto** a regras de combate que o AG nunca viu?
- **Como** (`external_validation`): fixar UM indivíduo e reavaliá-lo em duas perguntas,
  cada uma com 10 sementes novas (≥ 10000) somadas numa amostra de 5000 lutas por par:
  **replicação** (regras do treino) e **robustez** (uma constante de regra perturbada por
  vez — distância inicial, tamanho do campo, persistência, redução da guarda). Cada WR é
  classificada pelo IC de Wilson (95%) contra a banda — dentro, fora, inconclusivo —, e
  cada condição recebe ROBUSTA / FRÁGIL / INCONCLUSIVA. O veredito não depende do número
  de sementes, como o antigo "falhou em alguma das K" dependia. Fonte: Browne & Maire
  2010 (Ludi).
- **Para que serve na tese:** blinda contra *overfitting ao fitness* — valida o artefato
  **fora do laço de otimização**. Trocar só a semente testaria só o ruído de amostragem;
  trocar a regra testa se o equilíbrio depende das condições exatas em que foi otimizado.
  A bateria de **identidade** (drift, fingerprint, validador) cobre o eixo de identidade;
  esta valida o eixo do **equilíbrio**. A versão "contra política diferente" liga ao item
  2.1 (coevolução, trabalho futuro — [08](08-literature-methods.md)).
