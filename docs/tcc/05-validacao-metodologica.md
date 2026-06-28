# 05 — Validação metodológica

**Entra em**: Metodologia (validação) e/ou Resultados.

Pilares de validação que sustentam a credibilidade dos experimentos. Os dois
primeiros (reprodutibilidade, sensibilidade) validam o **método**; os três últimos
(N execuções, qualidade da fronteira, validação externa) constituem o **protocolo
experimental** incorporado da literatura — ver o status em
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

- **Pergunta:** algum dos 7 atributos é **neutro** — isto é, sem pressão seletiva, de
  modo que ele só drifta por random walk e não é "otimizado"?
- **Como medir** (`sensitivity_analysis`): para cada (arquétipo, atributo), perturbar o
  gene em ±σ e medir `|Δ WR|`. Atributos cujo Δ médio fica **abaixo do piso binomial**
  (~4% com 150 sims) são genes neutros.
- **Variância controlada:** usa pareamento de seeds (*common random numbers*) entre +σ
  e −σ — técnica que **só funciona após o fix de reprodutibilidade** (antes, ineficaz).
- **Para que serve na tese:** sustenta a afirmação de que a seleção atua sobre todo o
  cromossomo (ou identifica explicitamente quais genes são inertes — foi o caso do
  antigo `recovery`, cuja neutralidade motivou sua remoção; ver
  [07-achados-e-limitacoes.md](07-achados-e-limitacoes.md)). Não avalia um indivíduo;
  valida o **método**.

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
