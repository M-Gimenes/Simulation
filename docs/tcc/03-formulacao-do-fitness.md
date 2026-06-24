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

## `dominance_penalty` — WR primária + decisividade secundária

A decisão de design mais sutil do projeto, e a que mais evoluiu; precisa ser bem
justificada na metodologia, incluindo a trajetória (uma hipótese intermediária foi
falsificada — ver [04](04-caminhos-e-decisoes.md)). O termo combina **dois sinais por
matchup**:

```
e = DOMINANCE_WR_WEIGHT·|WR−0.5|/0.5  +  DOMINANCE_DECIS_WEIGHT·decis_excess
```

### Termo primário — balanço de win rate (`|WR − 0.5| / 0.5`)
É o objetivo direto de balanceamento: contínuo, sem banda morta, gradiente liso até
50%. **Por que isto e não só a margem da luta?** Porque medir só a margem é **cego à
frequência de vitória**: um personagem pode vencer 100% das vezes fechando sempre por
margem fina (luta apertada, vencedor determinístico) — `D ≈ 0.075`, dentro da banda,
penalidade zero, apesar de WR 100%. A objeção histórica ao WR ("em combate
determinístico o WR é bimodal, sem gradiente") **não vale mais**: a soft-policy +
`HESITATION_RATE` tornam o WR **graduado** quando as lutas estão apertadas, logo com
gradiente utilizável.

### Termo secundário — decisividade por-luta numa banda
Regularizador de **qualidade de luta** (peso menor, `0.5`). Score por-luta contínuo:
KO contribui `0.5 + 0.5·(HP_frac do vencedor)` (esmaga → ~1.0; ganha no fio → ~0.5);
timeout, a fração de HP%. Decisividade do matchup `D = média(|score − 0.5|)`, com
excesso fora da **banda `[0.05, 0.10]`** (vencedor fecha com ~10-20% de HP de folga).

- **Por que mantê-lo, se o WR já balanceia?** Guarda contra o **blowout-coinflip**: 55%
  A-esmaga / 45% B-esmaga ⇒ WR ~50% (termo primário satisfeito) mas toda luta é um
  massacre. A decisividade por-luta — `média(|score−0.5|)`, não `|média(score)−0.5|` —
  detecta isso (todo blowout dá margem ~0.5).
- **Por que uma banda, não "quanto menor melhor"?** Uma luta decidida por 1% é instável
  (parece coin-flip); a banda penaliza os **dois** extremos: blowout e fina demais.

### Propriedades comuns
- **RMS sobre os 10 pares:** extremos pesam mais que moderados — impede o AG de esconder
  um matchup destruído atrás de uma média balanceada.
- **Direcionalmente cego (`|WR − 0.5|`, `|score − 0.5|`):** não codifica quem deveria
  vencer, preservando a não-circularidade ([01](01-pergunta-e-escopo.md)).

## O que o AG otimiza vs. o que é métrica post-hoc

A separação é o ponto científico: a tese argumenta sobre o que o AG **pode otimizar** e
o que **emerge sem ser codificado**.

| Métrica | Otimizada? | Onde aparece |
|---|---|---|
| `dominance_penalty` (WR + decisividade por-luta) | **sim** | Fitness e NSGA-II |
| `drift_penalty` (distância ao canônico) | **sim** | Fitness e NSGA-II |
| WR binário por personagem | não | Relatório / convergência |
| Diferenciação entre personagens (homogeneização) | não | Métrica post-hoc (`drift_table`) |
| Preservação do ciclo canônico | **não** | Relatório post-hoc apenas |
| Sensibilidade dos genes | não | Validação metodológica ([05](05-validacao-metodologica.md)) |

> Houve um terceiro termo no fitness (`specialization_penalty`), **removido** — a razão
> e a trajetória dessa decisão estão em [04-caminhos-e-decisoes.md](04-caminhos-e-decisoes.md).
