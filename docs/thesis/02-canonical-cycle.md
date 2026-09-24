# 02 — Status epistemológico do ciclo canônico

**Entra em**: Introdução / Metodologia / Discussão.

> O *conteúdo* do ciclo (quem vence quem, e por quê) está em
> [`../reference/03-archetypes.md`](../reference/03-archetypes.md). Aqui está o **status**
> dele: o que ele é epistemologicamente, o que foi medido, e por que a tese não depende
> dele se realizar.

## Em uma frase

O ciclo é uma **premissa declarada e falsificada**: autorada a partir da convenção FGC,
mantida deliberadamente **fora** do fitness, e medida uma vez na resolução que ela exige.
O motor não a realiza — nem depois do equilíbrio, **nem no próprio canônico**. Isso é
achado, e é o que a Discussão apresenta.

## O ciclo é uma construção do autor, não uma lei do sistema

O ciclo (Rushdown > Zoner > Grappler > …) é uma **construção** derivada da convenção FGC,
usada como **hipótese de estrutura preservável**. Não é propriedade emergente das
mecânicas — é expectativa que se *mede* contra o que o sistema produz.

O campo `ArchetypeDefinition.beats` existe no código, congelado, e **nenhuma função de
fitness o lê** (`grep` resolve). Essa é a parte do argumento de não-circularidade que se
verifica em vez de se prometer: a resposta estava à mão e foi deliberadamente deixada de
fora. É a razão de o campo continuar existindo mesmo depois de falseado — ver
[04](04-design-decisions.md), «O ciclo saiu do `baselines`».

| | o que é | pode entrar no fitness? |
|---|---|---|
| **premissa** | o que cada arquétipo **é** — valores canônicos, `defining_genes` | **sim** (`drift_penalty`) |
| **resposta** | quem vence quem (`beats`) | **nunca** — seria responder à pergunta com ela mesma |

## O que foi medido

`src/experiments/cycle_structure.py` → `results/cycle/cycle_structure.json`, 16 × 1000 =
**16.000 lutas por par** (σ = 0,0040), sobre as 20 sementes da bateria. Conta só as
arestas **decididas** (`|WR − 0,5| > 2σ`): aresta indecisa é sorteio, e contá-la mistura
sinal com ruído nos dois sentidos.

| grupo | n | mantidas | decididas | mantidas **E** decididas | margem mediana | tríades |
|---|---|---|---|---|---|---|
| canônico | 1 | 6,00/10 | 10,00/10 | 6,00/10 | 0,5000 | **1,00** |
| AG escalar | 20 | 5,60/10 | 9,30/10 | 5,25/10 | 0,0481 | 3,71 |
| NSGA-II | 20 | 4,95/10 | 9,85/10 | 4,90/10 | 0,1037 | 4,17 |
| espelhos (controle de ruído) | 5 | 5,40/10 | **1,00/10** | 0,60/10 | 0,0033 | 2,59 |
| aleatórios (piso) | 30 | 4,97/10 | 10,00/10 | 4,97/10 | 0,4909 | 0,40 |

**Veredito: o ciclo não é realizado, com uma inclinação fraca e não significativa na
direção autoral.** O AG mantém **105 de 186 arestas decididas — 56,5%, binomial
p = 0,091**; os 30 nulos aleatórios ficam em 49,7% (p = 0,128, Â₁₂ = 0,63). O NSGA-II dá
4,90/10, o acaso com duas casas. A frase honesta não é "destruído" nem "preservado", é
**indistinguível do acaso**.

O caso mais nítido é o Grappler × Turtle, a aresta canônica mais forte ("o agarrão é o
counter do bloqueio", 100% no canônico): o AG a achata para 51% ± 6% nas 20 sementes,
hard-counter em nenhuma.

## O achado que não era esperado: o canônico também não tem um ciclo

Das 10 arestas, o canônico realiza 6 — e as 4 que quebra são **inversões totais**:

| aresta canônica | WR real no canônico |
|---|---|
| Combo Master > Grappler | 0,002 |
| Grappler > Rushdown | 0,006 |
| Turtle > Rushdown | 0,000 |
| Turtle > Combo Master | 0,000 |

Lidas juntas: **o Rushdown ganha de todos e a Turtle perde para todos.** Isso não é
pedra-papel-tesoura, é hierarquia — e as tríades circulares confirmam: o canônico marca
**1,00 de 5** (ordem quase estrita), contra 3,71 do AG.

Inverte a leitura antiga. A estrutura cíclica não foi destruída pelo equilíbrio: **ela
nunca existiu no motor.** Quem produz não-transitividade é o AG (3,71 tríades com 9,3/10
arestas decididas, contra 0,40 dos aleatórios) — com a ressalva de que equilíbrio global
com pares decididos **força** intransitividade (um roster estritamente transitivo teria
WRs 100/75/50/25/0, incompatível com todos perto de 50%), então isso é em boa parte
consequência do objetivo e não evidência independente dele.

## Quebra do ciclo é achado, não falha

O sistema não tem obrigação de entregar o ciclo; tem obrigação de **equilibrar** e de
**permitir medir** a preservação de identidade. A pergunta de pesquisa não menciona o
ciclo: ela é sobre equilíbrio e identidade **funcional**, cujas réguas são o validador
(Layer 3) e a concordância de ranking τ. O ciclo não sustenta nenhuma metade dela.

Que o modelo não produza o ciclo revela algo: a estrutura FGC depende parcialmente de
combo chaining e variância de dano, conscientemente deixados fora. Resultado, não erro de
método.

### Duas quebras distintas — não confundir (reformulação C2)

1. **No canônico:** o modelo não produz o ciclo nem antes de qualquer otimização. Medido
   acima (6/10, e hierarquia). O canônico é deliberadamente desequilibrado, com vários
   pares em 100/0.
2. **Após o balanceamento:** antes da reformulação **C2**, o termo primário era a WR
   **por-matchup**, cujo ótimo é *todo par a 50%* — equilíbrio plano, por construção
   incompatível com um ciclo (que exige vencedor em cada par). O objetivo **forçava** a
   quebra, e atribuí-la a "mecânicas omitidas" seria errado. Sob **C2** o equilíbrio é
   **global** (nenhum boneco domina o roster) com um teto de hard-counter que mantém as
   arestas como vantagens dentro de uma banda: o ciclo virou **expressável**. A quebra
   medida hoje é, portanto, do tipo 1 — da premissa —, não artefato da função objetivo.

C2 é robusto ao próprio fracasso: se o ciclo emergisse, ótimo; ele não emergiu, e isso é
achado honesto sobre o trade-off. (Formulação em
[03-fitness-formulation.md](03-fitness-formulation.md) e
[`../reference/05-genetic-algorithm.md`](../reference/05-genetic-algorithm.md).)

## O ciclo poderia ser outro — e isso não compromete a tese

A atribuição das arestas é uma **operacionalização entre várias defensáveis**:
- há consenso FGC para a maioria (Rushdown × Zoner, Grappler × Turtle, Turtle × Rushdown);
- algumas admitem leituras alternativas conforme jogo/era/meta;
- **cada aresta tem justificativa de domínio documentada**
  ([`../reference/03-archetypes.md`](../reference/03-archetypes.md)) — é estipulativo, não
  arbitrário: trocar uma exigiria nova justificativa, não sortear outro valor.

A tese **não depende do ciclo específico ser "o correto"**: um ciclo alternativo
defensável daria outros canônicos, mas o experimento sobre o trade-off equilíbrio ×
identidade produziria achado **da mesma natureza**. **O ciclo é palco, não objeto de
teste.**

> Análoga útil para a redação: ninguém trata "por que 5 arquétipos e não 4 ou 7?" como
> falha metodológica — é operacionalização. "Por que esse ciclo e não outro?" é da mesma
> natureza.

## Por que o ciclo não é régua de identidade

Contar arestas **é** informativo com pares decididos: realizar as 10 teria p = 1/1024 sob
cara-ou-coroa. O que o desqualifica como régua de preservação é medido: **o próprio
canônico realiza só 6/10**. Não se preserva o que a premissa não tinha.

As réguas de identidade são outras, e estão em
[07](07-findings-and-limitations.md): estrutural (`drift_penalty`, validador L1-L2) e
funcional (validador Layer 3, concordância de ranking τ) — esta última a que responde a
pergunta de pesquisa.

## Armadilha de medição que este item produziu

A contagem de arestas viveu no `baselines` até 2026-09-22, medida a `MULTI_RUN_SIMS` = 200
lutas por par. **Nessa resolução ela media ruído, não ciclo**: a margem mediana das
arestas de um roster equilibrado é 0,048, contra σ = 0,035 a 200 lutas. Provas:

- o mesmo roster lê **5/10 a 200 lutas e 8/10 a 16.000**;
- os **espelhos** — cinco cópias do mesmo arquétipo, estrutura de torneio zero por
  construção — marcavam 5,40/10 "mantidas" com **1,00/10 decididas**. Uma métrica que dá
  acima do piso num roster sem nenhuma estrutura está medindo sorteio.

O piso de 5/10 sempre foi válido (os nulos aleatórios têm arestas decididas, margem
mediana 0,49); o inválido era o valor do alvo. Daí o número antigo, «5/10, posição 0%,
p = 0,63», ter sido **substituído** — e a conclusão ter sobrevivido à troca, agora com
evidência em vez de ruído. Registro em [04](04-design-decisions.md), «O ciclo saiu do
`baselines`».

> **Regra de citação:** o ciclo sai de `results/cycle/cycle_structure.json`, nunca do
> `baselines.json` (onde não existe mais) nem de uma contagem a 200 lutas. E não se cita o
> 8/10 do roster do dossiê: ele é o topo da distribuição do próprio AG, que vai de 2 a 8
> nas 20 sementes.
