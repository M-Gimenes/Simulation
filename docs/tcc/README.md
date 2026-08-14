# docs/tcc — material para a escrita do TCC

Aqui mora o **"por quê"** e o **"o que significa"** — argumentação, interpretação,
trajetória de decisões e o que apresentar — material de **redação** da monografia.
O **"como funciona"** (mecânicas, fórmulas, parâmetros, assinaturas) é da referência
técnica em [`../`](../reference/README.md) (`docs/01`–`docs/11`); aqui **não se duplica** isso,
apenas se referencia.

> **Contrato de auto-suficiência:** `docs/` (as duas árvores juntas) é o **retrato
> completo do estado do sistema**. Uma sessão futura deve conseguir redigir o TCC
> **inteiro** a partir daqui — `tcc/` dá a narrativa e o que cada saída evidencia,
> `reference/` dá o detalhe técnico — recorrendo ao código apenas para citar um trecho
> pontual. Toda mudança de design precisa refletir nas duas árvores antes de encerrar a
> tarefa (instrução permanente do `CLAUDE.md`). O **status do que está implementado vs
> citar/futuro** vive em [08-metodologias-da-literatura.md](08-metodologias-da-literatura.md).

> A pasta `overleaf/` (raiz) tem os textos redigidos — a monografia (`TCC/`) e os
> artigos derivados dela (`artigo-SBC/`, `artigo-latinware-2026/`, este último um
> short paper de 3–4 páginas comprimido do SBC) — e não é tocada por estes arquivos.
> Os artigos compartilham `values.tex` como fonte única dos números experimentais.
> Backlog de decisões/calibrações pendentes: [`../10-known-issues.md`](../reference/10-known-issues.md).

## Mapa

| Arquivo | Cobre | Entra na tese em |
|---|---|---|
| [01-pergunta-e-escopo.md](01-pergunta-e-escopo.md) | Pergunta de pesquisa, a decisão de não forçar identidade, não-circularidade, escopo | Introdução, Objetivos |
| [02-ciclo-canonico.md](02-ciclo-canonico.md) | Status epistemológico do ciclo (construção, operacionalização defensável) | Introdução / Metodologia |
| [03-formulacao-do-fitness.md](03-formulacao-do-fitness.md) | Interpretação das fórmulas (drift, dominância) e o que é otimizado vs post-hoc | Metodologia |
| [04-caminhos-e-decisoes.md](04-caminhos-e-decisoes.md) | Trajetória das decisões de design — que problema cada mudança resolveu | Metodologia / Discussão |
| [05-validacao-metodologica.md](05-validacao-metodologica.md) | Reprodutibilidade e análise de sensibilidade | Metodologia (validação) |
| [06-resultados-a-apresentar.md](06-resultados-a-apresentar.md) | Quais saídas mostrar (dossiê, histórico do AG, fronteira NSGA-II…) e o que cada uma evidencia | Resultados |
| [07-achados-e-limitacoes.md](07-achados-e-limitacoes.md) | Achados, limitações e o que ainda falta investigar | Resultados / Discussão / Limitações |
| [08-metodologias-da-literatura.md](08-metodologias-da-literatura.md) | Metodologias dos papers do `.bib`, priorizadas, **+ status de implementação e decisão de escopo** (o que está feito vs citar vs trabalho futuro) | Metodologia / Discussão / Trabalhos Futuros |

## Convenção

Cada arquivo é **autocontido** num tema e marca onde entra na tese. Quando uma
decisão de design mudar, atualizar o arquivo `tcc/` afetado **e** o `docs/*.md`
técnico correspondente.
