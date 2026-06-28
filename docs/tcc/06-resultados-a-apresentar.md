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
ganha e se perde em cada ponta. O plot é anotado com **hipervolume** e **spacing**
(item 1.2) — o número que quantifica a qualidade da fronteira sem inspeção visual e
permite comparar configurações.

## 4. Comparação canônico × evoluído

A base de tudo: rodar o `report` no canônico estabelece o ponto de partida (drift 0,
ciclo de referência, comportamento de referência) contra o qual todo evoluído é lido.

## 5. Estatística agregada de N execuções (`multi_run`)

**O resultado central do lado evolutivo** (item 1.1). Em vez de um indivíduo de uma
seed, a tabela agregada sobre 10+ seeds:

| Saída | Evidencia |
|---|---|
| dominance/drift **média ± desvio** | onde o processo aterrissa *em média*, com dispersão |
| **WR global por personagem** (média ± desvio) | nenhum boneco domina o roster (o headline de equilíbrio sob C2) |
| **contagem de hard-counters** | quantos pares saem de `[0.30, 0.70]` — counters esmagadores |
| **fração de seeds que equilibram o roster** | a frase-tese — *"em N execuções, X% equilibraram o roster (5 bonecos em banda, 0 hard-counters)"* |
| (NSGA-II) **hipervolume ± desvio** | qualidade média da fronteira através das seeds |

É a peça que transforma "funciona numa seed" em afirmação estatística — e contextualiza
achados de seed única (ex.: um par travado) como estruturais ou amostrais.

> **Nota (C2):** o headline de equilíbrio é a WR **global** por personagem + ausência
> de hard-counter, **não** "cada par a 50%". O `multi_run` já reporta nesse formato
> (fração de sementes que equilibram o roster); a banda por-matchup vira leitura
> secundária.

## 6. Robustez do equilíbrio fora do laço (`external_validation`)

Item 3.2. Pega o indivíduo escolhido (tipicamente `best_dominance`) e mostra se o
equilíbrio **sobrevive a condições de avaliação novas**: veredito **robusto/frágil**
por matchup + do roster. Evidencia que o equilíbrio reportado não é overfit ao fitness.
Apresentar junto do dossiê do indivíduo, como sua *sustentação de robustez*.

## 7. Validação metodológica (sustentação)

- **Tabela de sensibilidade** (`sensitivity_analysis`): mostra que o AG enxerga os
  genes (ou quais são neutros). Vai junto da metodologia, não dos resultados de um
  indivíduo. Ver [05](05-validacao-metodologica.md).
- **Reprodutibilidade**: reportar o seed usado em cada experimento.

## O fio condutor dos Resultados

1. Estabelecer o **baseline** (canônico) e mostrar que o ciclo não é trivialmente
   preservado no modelo determinístico ([07](07-achados-e-limitacoes.md)).
2. Mostrar a **fronteira de Pareto** (com hipervolume) — o trade-off equilíbrio ×
   identidade.
3. Detalhar **dossiês** de pontos-chave da fronteira (preserva vs equilibra), usando
   drift + diferenciação + fingerprint + validador para *quantificar* preservação vs
   homogeneização.
4. Subir de uma seed para a **estatística agregada de N execuções** (`multi_run`) — a
   evidência estatística — e mostrar a **robustez** do indivíduo central
   (`external_validation`).
5. Concluir sobre a **pergunta de pesquisa** a partir do que a fronteira, os dossiês e
   a agregação mostram.

> O que **não** vai nos resultados (é sobre o AG/processo, não sobre um indivíduo):
> detalhes de mecânica, e o "como" técnico — esses ficam na Metodologia, referenciando
> [`../`](../reference/README.md).
