# 03 — Formulação do fitness: o que cada termo significa

**Entra em**: Metodologia (formulação do AG).

> As **fórmulas** estão em [`../05-genetic-algorithm.md`](../reference/05-genetic-algorithm.md).
> Aqui está o **significado e a justificativa** de cada escolha, para o texto da
> metodologia.

O fitness escalar tem **dois termos** — exatamente os dois objetivos do NSGA-II,
aqui como soma ponderada: `fitness = -(LAMBDA_DRIFT·drift + LAMBDA_DOMINANCE·dominance)`.

## `drift_penalty` — a operacionalização de "identidade"

Distância euclidiana normalizada de cada personagem ao seu perfil canônico (sobre os
12 genes). **É a tradução numérica de "preservação de identidade"** — o eixo que a
pergunta de pesquisa coloca em tensão com o equilíbrio — e o **verdadeiro mecanismo
anti-homogeneização** (puxa cada personagem para um canônico distinto). Com
`LAMBDA_DRIFT = LAMBDA_DOMINANCE`, identidade e equilíbrio pesam na mesma escala.

## `dominance_penalty` — por que decisividade por-luta numa banda

A decisão de design mais sutil do projeto; precisa ser bem justificada na metodologia:

- **Por que não win rate?** Em combate quase-determinístico o WR é **bimodal** (0 ou
  1) — um objetivo sem gradiente, só platôs e penhascos. A **margem** da luta varia
  continuamente e dá ao AG uma rampa para descer, mesmo sem estocasticidade.
- **Score por-luta contínuo:** KO contribui `0.5 + 0.5·(HP_frac do vencedor)` (esmaga
  → ~1.0; ganha no fio → ~0.5); timeout, a fração de HP%. Decisividade do matchup =
  `D = média(|score − 0.5|)`.
- **Por que uma BANDA `[0.05, 0.10]`, não "quanto menor melhor"?** Uma luta decidida
  por 1% é instável (parece coin-flip); o ideal competitivo é o vencedor fechar com
  **~10-20% de HP** de folga. A banda penaliza os **dois** extremos: blowout (decisiva
  demais) e quase-empate (fina demais).
- **Por que por-luta e não desvio da média?** `média(|score−0.5|)`, não
  `|média(score)−0.5|`: a média da WR zera quando blowouts se cancelam (55% A-esmaga /
  45% B-esmaga ⇒ WR ~50%, mas toda luta é blowout). A média por-luta detecta isso.
- **Por que RMS:** extremos pesam ~16× mais que moderados — impede o AG de esconder um
  matchup destruído atrás de uma média balanceada.
- **Direcionalmente cego (`|score − 0.5|`):** não codifica quem deveria vencer,
  preservando a não-circularidade ([01](01-pergunta-e-escopo.md)).
- **Win rate equilibrado emerge:** lutas apertadas (D na banda) + o ruído já existente
  (soft-policy/hesitação) ⇒ o WR cai perto de 50% **sozinho**. O equilíbrio "completo"
  (luta apertada **e** WR par) emerge da combinação, sem penalizar WR diretamente.

## O que o AG otimiza vs. o que é métrica post-hoc

A separação é o ponto científico: a tese argumenta sobre o que o AG **pode otimizar** e
o que **emerge sem ser codificado**.

| Métrica | Otimizada? | Onde aparece |
|---|---|---|
| `dominance_penalty` (decisividade por-luta) | **sim** | Fitness e NSGA-II |
| `drift_penalty` (distância ao canônico) | **sim** | Fitness e NSGA-II |
| WR binário por personagem | não | Relatório / convergência |
| Diferenciação entre personagens (homogeneização) | não | Métrica post-hoc (`drift_table`) |
| Preservação do ciclo canônico | **não** | Relatório post-hoc apenas |
| Sensibilidade dos genes | não | Validação metodológica ([05](05-validacao-metodologica.md)) |

> Houve um terceiro termo no fitness (`specialization_penalty`), **removido** — a razão
> e a trajetória dessa decisão estão em [04-caminhos-e-decisoes.md](04-caminhos-e-decisoes.md).
