# 05 — Validação metodológica

**Entra em**: Metodologia (validação) e/ou Resultados.

Pilares de validação que sustentam a credibilidade dos experimentos. Os dois
primeiros (reprodutibilidade, sensibilidade) validam o **método**; os quatro
seguintes (N execuções, comparação estatística, qualidade da fronteira, validação
externa) constituem o **protocolo experimental** incorporado da literatura — ver o
status em
[08-metodologias-da-literatura.md](08-metodologias-da-literatura.md). O "como" de cada
ferramenta está em [`../reference/08-tools.md`](../reference/08-tools.md).

## Reprodutibilidade

- O combate sorteia com `np.random` **dentro do JIT (Numba)**, cujo RNG é independente
  do `np.random` de nível Python e **só semeável de dentro de um `@njit`**. Por isso a
  reprodutibilidade não é trivial — e era um ponto silenciosamente quebrado (ver a
  trajetória em [04-caminhos-e-decisoes.md](04-caminhos-e-decisoes.md)).
- **Como é garantida hoje:** **reset ao seed-base (Common Random Numbers)** — toda
  avaliação reseta o RNG do combate ao mesmo seed-base, propagado aos workers do
  paralelismo. Reprodutível independente de qual worker avalia, e todo indivíduo é
  avaliado sob o mesmo stream de RNG (a diferença de fitness reflete genes, não sorteio
  → seleção menos enganada). Detalhe técnico em
  [`../09-reproducibility.md`](../reference/09-reproducibility.md).
- **Ponto para a tese:** experimentos com `--seed` são **replicáveis** (afirmação que
  uma tese de método precisa poder fazer), e foi **verificado empiricamente**.

## Análise de sensibilidade — o AG enxerga todos os genes?

- **Pergunta:** algum dos 8 atributos é **neutro** — isto é, sem pressão seletiva, de
  modo que ele só drifta por random walk e não é "otimizado"?
- **Como medir** (`sensitivity_analysis`): para cada (arquétipo, atributo), perturbar o
  gene em ±σ e medir `|Δ WR|` **global** do personagem. Atributos cujo Δ médio fica
  **abaixo do piso medido** são neutros; `≤ 2× piso` é borderline.
- **O piso é medido, não estimado** — e a diferença importa para o texto. O piso analítico
  (`sqrt(0.25/(4·sims))`, ±1,8% a 200 sims) é o desvio de **uma proporção**, mas o número
  classificado é uma **diferença** entre duas WRs: grandeza errada. O tool roda a própria
  maquinaria sob a hipótese nula — `|Δ WR|` entre duas avaliações do **mesmo** roster,
  **sem perturbação**, sob seeds diferentes (`--null-reps`). Ali o Δ verdadeiro é zero por
  construção, então tudo que aparece é ruído, na mesma grandeza que a tabela classifica.
  Seeds diferentes são necessárias: com a mesma seed e perturbação zero as avaliações são
  bit-idênticas e o Δ sai 0. Quebrar o pareamento de propósito dá um piso **conservador**
  (a medição real usa CRN pareado e tem menos ruído), que é o lado seguro. O piso medido e
  a classificação vão no artefato JSON junto da matriz completa.
- **Onde medir importa tanto quanto como.** O tool rodava fixo no canônico, que é
  **saturado** (Rushdown ~100% global, Turtle ~0%): com a WR presa no teto, perturbar um
  gene não muda nada e quase tudo saía "neutro" por efeito de teto, não por neutralidade —
  a tabela sustentava o contrário do que se quer afirmar. Com `--evolved`, no roster
  equilibrado da bateria de 2026-09-18, **4 dos 8** atributos saem visíveis (`range`
  0,393 · `attack_cooldown` 0,213 · `hp` 0,191 · `damage` 0,183, contra um piso de 0,057)
  e os outros 4 borderline (`grab_power` 0,110 · `stun` 0,073 · `speed` 0,071 ·
  `knockback` 0,067) — **nenhum abaixo do piso**. Uma medição mais fina (600 sims, 12
  repetições do piso, piso 0,051) põe `speed` e `knockback` **no limiar**, com
  sinal/ruído ~1,1: a limitação a declarar é que o AG mal enxerga esses dois genes em volta
  do indivíduo evoluído. A análise é **local** — mede a paisagem em volta de um indivíduo e
  muda com ele.
- **Variância controlada:** usa pareamento de seeds (*common random numbers*) entre +σ
  e −σ — técnica que **só funciona após o fix de reprodutibilidade** (antes, ineficaz).
- **Para que serve na tese:** sustenta a afirmação de que a seleção atua sobre todo o
  cromossomo (ou identifica explicitamente quais genes são inertes — foi o caso do
  antigo `recovery`, cuja neutralidade motivou sua remoção; ver
  [07-achados-e-limitacoes.md](07-achados-e-limitacoes.md)). Valida o **método**, não a
  qualidade do indivíduo — mas *precisa* de um indivíduo não-saturado para medir, e é
  por isso que a medida citável é a do `--evolved`, não a do canônico.

## Múltiplas execuções independentes + estatística agregada (item 1.1)

- **Pergunta:** um AG é estocástico — um resultado de **uma seed** é representativo, ou
  é azar/sorte daquela amostra?
- **Como** (`multi_run`): rodar AG e NSGA-II sobre N sementes (10+), reavaliar o melhor
  indivíduo de cada uma sob uma seed de validação comum, e reportar **média ± desvio**
  de dominance/drift, **WR global por personagem** e a **fração de sementes que
  equilibram o roster** (5 bonecos em banda, 0 hard-counters). Fontes: Eiben & Smith 2015; Deb 2001.
- **Para que serve na tese:** é o **piso metodológico** — substitui "numa execução, deu
  X" por *"em N execuções, X% equilibraram o roster; WR global média 50±k%"*.
  Resolve diretamente a fragilidade de seed única (ex.: o Combo×Rush travado em uma
  seed — [07](07-achados-e-limitacoes.md) — vira pergunta respondível: azar ou
  estrutural?).

## Comparação estatística entre algoritmos (parte do item 1.1)

- **Pergunta:** o `multi_run` dá média ± desvio de cada algoritmo. Quando a média de um
  é melhor que a do outro, isso é diferença real ou amostragem de 10 execuções?
- **Como** (`compare_algorithms`): sobre as amostras por semente já gravadas,
  **Mann-Whitney U** bicaudal (não-paramétrico, não assume normalidade) +
  **Â₁₂ de Vargha-Delaney** (tamanho de efeito — o `p` diz se a diferença existe, o Â₁₂
  diz se ela importa) + **Holm-Bonferroni** na família de métricas comparadas —
  hoje 3, porque "bonecos em banda" dá 5/5 nas 20 execuções e Mann-Whitney é
  indefinido em amostra conjunta constante. Fontes: Derrac
  et al. 2011; Arcuri & Briand 2011; Vargha & Delaney 2000 (limiares do Â₁₂).
  **Nenhuma das três está em `bibliografia.bib` ainda** — adicionar ao redigir.
  Explicação do aparato, do zero:
  [`../reference/12-statistical-testing.md`](../reference/12-statistical-testing.md).
- **Para que serve na tese:** é o que separa "o AG escalar deu média menor" de "o AG
  escalar é melhor nessa métrica". Ressalva a declarar: o NSGA-II devolve uma
  fronteira, então a comparação depende de **qual ponto** a representa — o artefato
  grava `nsga2_representative`.

## Qualidade da fronteira de Pareto: hipervolume + spacing (item 1.2)

- **Pergunta:** comparar fronteiras "no olho" não escala — como quantificar se uma
  fronteira é melhor (mais próxima da utopia e mais espalhada) que outra?
- **Como** (`pareto_metrics`): **hipervolume** (área dominada vs ponto de referência
  fixo `(2.0, 1.0)` = piores valores; maior = melhor) e **spacing** de Schott
  (uniformidade; menor = melhor). Fontes: Deb 2001/2002.
- **Para que serve na tese:** comparação **objetiva** entre seeds e entre configurações
  (efeito de `MATCHUP_WR_CAP`, `SIMS_PER_MATCHUP`, etc.) sem inspeção visual. Métrica
  madura e esperada num trabalho com NSGA-II.

## Validação externa ao fitness (item 3.2)

- **Pergunta:** o equilíbrio de um indivíduo evoluído é **robusto**, ou é overfit às
  condições exatas (seed/sims) em que foi treinado?
- **Como** (`external_validation`): fixar UM indivíduo e reavaliá-lo sob K sementes de
  avaliação **totalmente novas** (≥10000, fora do treino), com mais sims; marcar cada
  matchup como **robusto** (equilibrado em TODAS as K condições) ou frágil, e dar um
  **veredito do roster**. Fonte: Browne & Maire 2010 (Ludi).
- **Para que serve na tese:** blinda contra *overfitting ao fitness* — valida o
  artefato **fora do laço de otimização**, sobre condições que o AG nunca otimizou. A
  bateria de **identidade** (drift, fingerprint, validador) é determinística nos genes
  e cobre o eixo de identidade; esta valida o eixo **estocástico** (equilíbrio), onde o
  overfitting se esconde. A versão "contra política diferente" liga ao item 2.1
  (coevolução, trabalho futuro — [08](08-metodologias-da-literatura.md)).
