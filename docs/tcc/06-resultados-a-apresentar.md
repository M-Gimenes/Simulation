# 06 — Resultados a apresentar

**Entra em**: Resultados (e parte da Discussão).

Quais saídas o sistema produz, **qual delas mostrar** no capítulo de Resultados, e
**o que cada uma evidencia**. Como gerar cada tool: [`../08-tools.md`](../reference/08-tools.md).

## 1. Dossiê de um indivíduo (`report`)

O artefato por-indivíduo. `py -m src.tools.report --evolved` (ou `--nsga2 <rep>`)
reúne, num relatório único:

| Bloco | Evidencia |
|---|---|
| Cabeçalho: `fitness`, `drift_penalty`, `dominance_penalty` | onde o indivíduo está no trade-off |
| Matriz de matchups + WR global + ciclo | **equilíbrio** alcançado, e quanto do ciclo sobreviveu |
| Tabela de drift por gene + `drift_penalty` | **identidade de genes** — *o preço pago* pela evolução |
| Diferenciação par-a-par (`ratio`) | **homogeneização** — os 5 ainda são distintos? |
| Fingerprint (canônico vs evoluído) | **identidade comportamental** — ainda joga como o arquétipo? |
| Validador (score /20) | **identidade estrutural** — invariantes de ranking |

Apresentar o dossiê do(s) indivíduo(s) escolhido(s) — tipicamente o **canônico** (baseline)
e os representantes de interesse do NSGA-II.

## 2. Histórico de convergência do AG escalar

`run()` retorna `history` (lista de `GenerationStats`): `best/mean/worst fitness`,
`drift_penalty`, `dominance_penalty` por geração. Plotar essas curvas mostra a
**trajetória de otimização** — o AG melhora? converge, estagna ou bate o teto de
gerações? como drift e dominância evoluem um contra o outro? É a evidência de que o
processo *funciona* (ou de onde ele empaca).

## 3. Fronteira de Pareto do NSGA-II (o artefato central)

`nsga2_plots` gera o gráfico **dominância × drift** com os 4 representantes
(`best_dominance`, `best_drift`, `knee_point`, `ideal_point`). **É a peça que torna o
trade-off explícito** e responde diretamente à pergunta de pesquisa:
- o extremo `best_dominance` = **equilíbrio com mais homogeneização** (drift alto);
- o extremo `best_drift` = **identidade preservada com menos equilíbrio**;
- o `knee_point` = melhor compromisso.

Mostrar a fronteira **e** os dossiês (`report --nsga2 best_dominance` vs
`--nsga2 best_drift`) é o coração do capítulo: dá pra *ver* e *quantificar* o que se
ganha e se perde em cada ponta.

## 4. Comparação canônico × evoluído

A base de tudo: rodar o `report` no canônico estabelece o ponto de partida (drift 0,
ciclo de referência, comportamento de referência) contra o qual todo evoluído é lido.

## 5. Validação metodológica (sustentação)

- **Tabela de sensibilidade** (`sensitivity_analysis`): mostra que o AG enxerga os
  genes (ou quais são neutros). Vai junto da metodologia, não dos resultados de um
  indivíduo. Ver [05](05-validacao-metodologica.md).
- **Reprodutibilidade**: reportar o seed usado em cada experimento.

## O fio condutor dos Resultados

1. Estabelecer o **baseline** (canônico) e mostrar que o ciclo não é trivialmente
   preservado no modelo determinístico ([07](07-achados-e-limitacoes.md)).
2. Mostrar a **fronteira de Pareto** — o trade-off equilíbrio × identidade.
3. Detalhar **dossiês** de pontos-chave da fronteira (preserva vs equilibra), usando
   drift + diferenciação + fingerprint + validador para *quantificar* preservação vs
   homogeneização.
4. Concluir sobre a **pergunta de pesquisa** a partir do que a fronteira e os dossiês
   mostram.

> O que **não** vai nos resultados (é sobre o AG/processo, não sobre um indivíduo):
> detalhes de mecânica, e o "como" técnico — esses ficam na Metodologia, referenciando
> [`../`](../reference/README.md).
