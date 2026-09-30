# Retomada — estado do projeto

O retrato do agora: o que está pronto e o que falta. Não guarda números nem histórico, para
não envelhecer contra os docs:

- **números citáveis:** os artefatos em `results/`, extraídos por
  `py -m diagnostics.battery_numbers`; na monografia, `overleaf/TCC/valores.tex`, que indica
  o artefato de cada macro;
- **achados:** [`docs/thesis/07-findings-and-limitations.md`](../thesis/07-findings-and-limitations.md);
- **o porquê de cada decisão:** [`docs/thesis/04-design-decisions.md`](../thesis/04-design-decisions.md);
- **pendências e limites do sistema:** [`docs/reference/10-known-issues.md`](../reference/10-known-issues.md);
- **revisão do texto da monografia:** [`REVIEW.md`](REVIEW.md) §2.

A versão longa anterior deste arquivo, com as tabelas da bateria, fica no git:
`git show 37a3587:docs/status/HANDOFF.md`.

---

## Pronto

- **Sistema fechado.** Motor, fitness e protocolo calibrados; canônicos declarados finais.
- **`results/` atual.** Bateria de 2026-09-23 (n = 20, 19 passos: AG escalar, NSGA-II, os
  dois controles, o híbrido e o teste do ciclo) e validação externa regerada em 2026-09-29,
  com o `dominance` calculado sobre a amostra somada. `py -m src.tests.test_provenance` não
  acusa artefato obsoleto. A bateria de 2026-09-21 (reavaliação a 200 lutas) está em
  `results_previous/` e não é citável.
- **Monografia reescrita** (2026-09-29) sobre essa bateria, com números em `valores.tex` e
  figuras por `py -m src.visualization.thesis_figures`. Compila sem referência indefinida.

## Falta

1. **Revisão da monografia:** os itens T1 a T16 e os menores de [`REVIEW.md`](REVIEW.md)
   §2.3, numa passada só, com as regras da §2.1.
2. **Pendências do autor:** dedicatória, agradecimentos e epígrafe (ocultos no `main.tex`
   até terem texto); orientador, banca e data de aprovação em `macros.tex`; ficha
   catalográfica (feita pela biblioteca); leitura final do texto.
3. **Artigo da Latinware:** o `values.tex` dele é o do snapshot aceito (n = 10, motor
   anterior). Atualizar só se a versão final ainda aceitar mudança; nesse caso, o
   `dominance` do AG vem de fora do laço, como as demais células da linha.
4. **Código que espera a próxima re-execução** (editar agora obsoleta artefatos):
   separar medição de impressão no `analyze_matchups` e os docstrings desatualizados —
   [`10-known-issues`](../reference/10-known-issues.md) §1.

## Para começar uma sessão

- `.\scripts\setup.ps1`: o `.venv/` não vem no git, e o Python do sistema não tem `numpy`,
  `numba` nem `scipy`.
- Não há LaTeX local: a monografia compila no Overleaf.
