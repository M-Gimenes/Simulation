# docs/thesis — material para a escrita do TCC

Aqui mora o **"por quê"** e o **"o que significa"** — argumentação, interpretação,
trajetória de decisões e o que apresentar — material de **redação** da monografia.
O **"como funciona"** (mecânicas, fórmulas, parâmetros, assinaturas) é da referência
técnica em [`../reference/`](../reference/README.md) (`01`–`12`); aqui **não se duplica**
isso, apenas se referencia.

> **Contrato de auto-suficiência:** `reference/` e `thesis/` juntas são o **retrato
> completo do estado do sistema**. Uma sessão futura deve conseguir redigir o TCC
> **inteiro** a partir daqui — `thesis/` dá a narrativa e o que cada saída evidencia,
> `reference/` dá o detalhe técnico — recorrendo ao código apenas para citar um trecho
> pontual. O `status/` fica fora do contrato: é registro de trabalho e descreve um
> momento. Toda mudança de design precisa refletir nas duas árvores antes de encerrar a
> tarefa (instrução permanente do `CLAUDE.md`). O **status do que está implementado vs
> citar/futuro** vive em [08-literature-methods.md](08-literature-methods.md).

> A pasta `overleaf/` (raiz) tem os textos redigidos — a monografia (`TCC/`) e os
> artigos derivados dela (`artigo-SBC/`, `artigo-latinware-2026/`, este último um
> short paper de 3–4 páginas comprimido do SBC) — e não é tocada por estes arquivos.
> Os artigos compartilham `values.tex` como fonte única dos números experimentais.
> Pendências e limites do sistema: [`../reference/10-known-issues.md`](../reference/10-known-issues.md).

> ⚠️ **Números de resultado.** Os números citados aqui são da bateria de 2026-09-18, medida
> antes do CRN por luta — que troca todos os sorteios. A próxima bateria os substitui;
> releia cada número contra ela antes de citar (ver
> [`../reference/10-known-issues.md`](../reference/10-known-issues.md) §1).

## Mapa

| Arquivo | Cobre | Entra na tese em |
|---|---|---|
| [01-question-and-scope.md](01-question-and-scope.md) | Pergunta de pesquisa, a decisão de não forçar identidade, não-circularidade, escopo | Introdução, Objetivos |
| [02-canonical-cycle.md](02-canonical-cycle.md) | Status epistemológico do ciclo (construção, operacionalização defensável) | Introdução / Metodologia |
| [03-fitness-formulation.md](03-fitness-formulation.md) | Interpretação das fórmulas (drift, dominância) e o que é otimizado vs post-hoc | Metodologia |
| [04-design-decisions.md](04-design-decisions.md) | Trajetória das decisões de design — que problema cada mudança resolveu | Metodologia / Discussão |
| [05-methodological-validation.md](05-methodological-validation.md) | Reprodutibilidade e análise de sensibilidade | Metodologia (validação) |
| [06-results-to-present.md](06-results-to-present.md) | Quais saídas mostrar (dossiê, histórico do AG, fronteira NSGA-II…) e o que cada uma evidencia | Resultados |
| [07-findings-and-limitations.md](07-findings-and-limitations.md) | Achados, limitações e o que ainda falta investigar | Resultados / Discussão / Limitações |
| [08-literature-methods.md](08-literature-methods.md) | Metodologias dos papers do `.bib`, priorizadas, **+ status de implementação e decisão de escopo** (o que está feito vs citar vs trabalho futuro) | Metodologia / Discussão / Trabalhos Futuros |
| [09-values-and-choices.md](09-values-and-choices.md) | Catálogo de **todo valor e toda escolha** do sistema, cada um com o tipo de evidência que o sustenta (`[medido]`, `[domínio]`, `[coerência]`, `[projeto]`) e o ponteiro para o porquê — inclui os valores sem justificativa registrada, declarados como tal | Metodologia (todos os subcapítulos) / Limitações |

## Convenção

Cada arquivo é **autocontido** num tema e marca onde entra na tese. Quando uma
decisão de design mudar, atualizar o arquivo `thesis/` afetado **e** o
`docs/reference/*.md` técnico correspondente.
