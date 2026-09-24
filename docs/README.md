# Documentação do projeto

Organizada em três frentes:

- **[`reference/`](reference/README.md)** — referência técnica do sistema (como
  funciona): combate, AG, NSGA-II, config, tools, reprodutibilidade, pontos em
  aberto, revisão do combate. Mantida em sincronia com o código.
- **[`thesis/`](thesis/README.md)** — material de redação da monografia (o porquê, a
  trajetória de decisões, o que apresentar nos resultados).
- **[`status/`](status/HANDOFF.md)** — registros de trabalho: o
  [`HANDOFF.md`](status/HANDOFF.md) (estado atual e resultados da última bateria, por onde
  começar) e o [`REVIEW.md`](status/REVIEW.md) (a auditoria de coerência e o que dela segue
  aberto). Descrevem o momento, não o sistema — o que vale para a tese é migrado para
  `reference/` e `thesis/`.

Para instruções de trabalho com o repositório, ver `CLAUDE.md` (raiz); para
instalação e execução rápida, ver o `README.md` da raiz.

> A pasta `overleaf/` (raiz) tem os textos redigidos — a monografia (`TCC/`) e os
> artigos derivados dela (`artigo-SBC/`, `artigo-latinware-2026/`) — e **não** é
> tocada por esta documentação. Os artigos compartilham `values.tex` como fonte
> única dos números experimentais: ao refazer as rodadas, atualizar esse arquivo
> em cada um.

> **Convenção de idioma**: nomes de arquivos e pastas em inglês; o texto dos `.md`
> pode ser em português.
