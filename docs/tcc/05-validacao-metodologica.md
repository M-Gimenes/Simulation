# 05 — Validação metodológica

**Entra em**: Metodologia (validação) e/ou Resultados.

Dois pilares de validação que sustentam a credibilidade dos experimentos.

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

- **Pergunta:** algum dos 9 atributos é **neutro** — isto é, sem pressão seletiva, de
  modo que ele só drifta por random walk e não é "otimizado"?
- **Como medir** (`sensitivity_analysis`): para cada (arquétipo, atributo), perturbar o
  gene em ±σ e medir `|Δ WR|`. Atributos cujo Δ médio fica **abaixo do piso binomial**
  (~4% com 150 sims) são genes neutros.
- **Variância controlada:** usa pareamento de seeds (*common random numbers*) entre +σ
  e −σ — técnica que **só funciona após o fix de reprodutibilidade** (antes, ineficaz).
- **Para que serve na tese:** sustenta a afirmação de que a seleção atua sobre todo o
  cromossomo (ou identifica explicitamente quais genes são inertes — ex.: o `recovery`,
  ver [07-achados-e-limitacoes.md](07-achados-e-limitacoes.md)). Não avalia um
  indivíduo; valida o **método**.
