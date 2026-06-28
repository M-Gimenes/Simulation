# 03 — Formulação do fitness: o que cada termo significa

**Entra em**: Metodologia (formulação do AG).

> As **fórmulas** estão em [`../05-genetic-algorithm.md`](../reference/05-genetic-algorithm.md).
> Aqui está o **significado e a justificativa** de cada escolha, para o texto da
> metodologia.

O fitness escalar tem **dois termos** — exatamente os dois objetivos do NSGA-II,
aqui como soma ponderada: `fitness = -(LAMBDA_DRIFT·drift + LAMBDA_DOMINANCE·dominance)`.

## `drift_penalty` — a operacionalização de "identidade"

Distância euclidiana normalizada de cada personagem ao seu perfil canônico (sobre os
10 genes). **É a tradução numérica de "preservação de identidade"** — o eixo que a
pergunta de pesquisa coloca em tensão com o equilíbrio — e o **verdadeiro mecanismo
anti-homogeneização** (puxa cada personagem para um canônico distinto). Com
`LAMBDA_DRIFT = LAMBDA_DOMINANCE`, identidade e equilíbrio pesam na mesma escala.

## `dominance_penalty` — balanço global + teto de hard-counter + decisividade (C2)

A decisão de design mais sutil do projeto, e a que mais evoluiu; precisa ser bem
justificada na metodologia, incluindo a trajetória (uma hipótese intermediária foi
falsificada, e a métrica de equilíbrio foi reformulada — ver
[04](04-caminhos-e-decisoes.md)). Sob a formulação **C2**, equilíbrio = **nenhum
personagem domina o roster** (não "cada par a 50%"). A penalidade soma **três
sinais**:

```
dominance = DOMINANCE_GLOBAL_WEIGHT·global_term + DOMINANCE_CAP_WEIGHT·cap_term + DOMINANCE_DECIS_WEIGHT·decis_term
```

### Termo primário — balanço **global** por personagem
`global_term = RMS_i(|WR_global_i − 0.5| / 0.5)`, onde `WR_global` é o win rate
agregado do personagem sobre seus 4 oponentes. O ótimo é "ninguém domina o roster",
mas **não** força cada par a 50%: um boneco a 50% global pode vencer 2 e perder 2 —
exatamente o espaço em que o **ciclo de vantagens** pode existir.

> **Por que global, e não por-matchup?** O primário antigo era a WR **por-matchup**,
> cujo ótimo é *todo par a 50%* — equilíbrio plano. Mas um ciclo exige que pares
> tenham vencedor: otimizar "todo par a 50%" **destrói o ciclo por construção**, e a
> quebra seria um artefato do objetivo, não um achado. Sob C2 o objetivo deixa de
> forçar a quebra, e a emergência do ciclo vira o achado real (ver
> [02-ciclo-canonico.md](02-ciclo-canonico.md)).

### Termo secundário — teto de hard-counter
`cap_term = RMS_par(max(0, |WR_par − 0.5| − MATCHUP_WR_CAP) / (0.5 − MATCHUP_WR_CAP))`.
Penaliza só o excesso **acima** de `MATCHUP_WR_CAP` (banda `[0.30, 0.70]`). Mantém as
arestas do ciclo como **vantagens** (um par pode ter favorito), barrando apenas os
**counters esmagadores** (ex.: 100×0). Dentro da banda, o par não é penalizado.

### Termo secundário — decisividade por-luta numa banda
Regularizador de **qualidade de luta**. Score por-luta contínuo: KO contribui
`0.5 + 0.5·(HP_frac do vencedor)` (esmaga → ~1.0; ganha no fio → ~0.5); timeout, a
fração de HP%. Decisividade do matchup `D = média(|score − 0.5|)`, com excesso fora da
**banda `[0.10, 0.20]`** (vencedor fecha com ~20-40% de HP de folga).

- **Por que mantê-lo?** Guarda contra o **blowout-coinflip**: 55% A-esmaga / 45%
  B-esmaga ⇒ WR global ~50% (primário satisfeito) mas toda luta é um massacre. A
  decisividade por-luta — `média(|score−0.5|)`, não `|média(score)−0.5|` — detecta
  isso (todo blowout dá margem ~0.5).
- **Por que uma banda, não "quanto menor melhor"?** Uma luta decidida por 1% é instável
  (parece coin-flip); a banda penaliza os **dois** extremos: blowout e fina demais.

### Propriedades comuns
- **RMS** (sobre os 5 bonecos no global, sobre os 10 pares nos secundários): extremos
  pesam mais que moderados — impede o AG de esconder um boneco dominante ou um counter
  duro atrás de uma média balanceada.
- **Direcionalmente cego (`|WR − 0.5|`, `|score − 0.5|`):** não codifica quem deveria
  vencer, preservando a não-circularidade ([01](01-pergunta-e-escopo.md)).
- **Gradiente:** a objeção histórica ao WR ("em combate determinístico o WR é bimodal,
  sem gradiente") é contornada porque, quando as lutas ficam apertadas, o sorteio de
  intenção flipa desfechos e a WR vira **graduada** (ver
  [`../reference/11-combat-review.md`](../reference/11-combat-review.md)).

## O que o AG otimiza vs. o que é métrica post-hoc

A separação é o ponto científico: a tese argumenta sobre o que o AG **pode otimizar** e
o que **emerge sem ser codificado**.

| Métrica | Otimizada? | Onde aparece |
|---|---|---|
| `dominance_penalty` (global por personagem + teto de hard-counter + decisividade) | **sim** | Fitness e NSGA-II |
| `drift_penalty` (distância ao canônico) | **sim** | Fitness e NSGA-II |
| WR **global** por personagem (alvo 50%) | **sim** (termo primário do dominance) | Fitness, relatório, convergência |
| WR **por-matchup** exata (cada par a 50%) | **não** (só o teto de hard-counter) | Relatório post-hoc |
| Diferenciação entre personagens (homogeneização) | não | Métrica post-hoc (`drift_table`) |
| Preservação do ciclo canônico | **não** | Relatório post-hoc apenas |
| Sensibilidade dos genes | não | Validação metodológica ([05](05-validacao-metodologica.md)) |

> Houve um terceiro termo no fitness (`specialization_penalty`), **removido** — a razão
> e a trajetória dessa decisão estão em [04-caminhos-e-decisoes.md](04-caminhos-e-decisoes.md).
