# 02 — Status epistemológico do ciclo canônico

**Entra em**: Introdução / Metodologia (e Discussão, se o ciclo quebrar).

> O *conteúdo* do ciclo (quem vence quem, e por quê) está em
> [`../reference/03-archetypes.md`](../reference/03-archetypes.md). Aqui está o **status** dele: o que ele
> é epistemologicamente, e por que a tese não depende dele estar "certo".

## O ciclo é uma construção do autor, não uma lei do sistema

O ciclo (Rushdown > Zoner > Grappler > … ) é uma **construção** derivada da convenção
FGC, usada como **hipótese de estrutura preservável**. Não é uma propriedade física
emergente das mecânicas — é uma expectativa que se *mede* contra o que o sistema
produz.

## Quebra do ciclo é um achado, não uma falha

O sistema não tem obrigação de "entregar o ciclo"; tem obrigação de **equilibrar** e
de **permitir medir** a preservação de identidade. Se o ciclo não se sustenta no
modelo — quase-determinístico, com o sorteio de intenção como única fonte de sorte —,
isso **revela** algo: que a estrutura FGC depende parcialmente de elementos de combo e
variância (combo chaining, dano variável) que foram conscientemente deixados de fora.
Isso é resultado, não erro de método.

### Duas quebras distintas — não confundir (reformulação C2)

É preciso separar **duas** possíveis quebras do ciclo, com leituras diferentes:

1. **No baseline (canônico):** o modelo pode não produzir o ciclo nem antes de
   qualquer otimização — leitura acima (mecânicas de combo e variância omitidas).
   **Segue válida:** o canônico é deliberadamente desequilibrado, com vários pares em
   100/0.
2. **Após o balanceamento:** antes da reformulação **C2**, o objetivo tinha como
   termo primário a WR **por-matchup**, cujo ótimo é *todo par a 50%* — equilíbrio
   plano, que por construção é **incompatível com o ciclo** (um ciclo exige que
   pares tenham vencedor). Ou seja, o próprio objetivo **forçava** a quebra, e
   atribuí-la a "mecânicas omitidas" seria errado nesse caso. Sob **C2**, o
   equilíbrio passou a ser **global** (nenhum boneco domina o roster) com um teto de
   hard-counter que **mantém as arestas do ciclo como vantagens** dentro de uma
   banda. O objetivo deixou de forçar a quebra: o ciclo virou **expressável**.

Com isso, **"o ciclo emerge das identidades preservadas?"** passa a ser o achado
real — e C2 é robusto ao próprio fracasso: se o ciclo emergir, ótimo; se o
equilíbrio plano dominar mesmo havendo espaço para o ciclo, isso também é um achado
honesto sobre o trade-off, não um artefato da função objetivo. (A formulação de C2
está em [03-fitness-formulation.md](03-fitness-formulation.md) e
[`../reference/05-genetic-algorithm.md`](../reference/05-genetic-algorithm.md).)

## O ciclo poderia ser outro — e isso não compromete a tese

A atribuição das arestas é uma **operacionalização entre várias defensáveis**:
- há consenso FGC para a maioria (Rushdown × Zoner, Grappler × Turtle, Turtle ×
  Rushdown);
- algumas admitem leituras alternativas conforme jogo/era/meta;
- **cada aresta tem justificativa de domínio documentada** ([`../reference/03-archetypes.md`](../reference/03-archetypes.md)) —
  é estipulativo, não arbitrário (trocar uma exigiria nova justificativa, não sortear
  outro valor).

A tese **não depende do ciclo específico ser "o correto"**: um ciclo alternativo
defensável daria outros canônicos, mas o experimento sobre o trade-off equilíbrio ×
identidade produziria um achado **da mesma natureza**. **O ciclo é palco, não objeto
de teste.**

> Análoga útil para a redação: ninguém trata "por que 5 arquétipos e não 4 ou 7?" como
> falha metodológica — é operacionalização. "Por que esse ciclo e não outro?" é da
> mesma natureza.

## O ciclo autoral não serve de régua — e por quê

Contar arestas mantidas **é** informativo quando os pares estão decididos: realizar as 10
teria p = 1/1024 sob cara-ou-coroa. O que impede o ciclo de servir de régua de preservação
é outra coisa, medida: **o próprio canônico realiza só 6 das 10 arestas** no motor (o
Turtle canônico perde para todos). Não se preserva o que a premissa não tinha — o ciclo é
hipótese do autor sobre como os arquétipos deveriam se enfrentar, e o modelo não a
realiza nem antes da otimização.

Duas leituras substituem a contagem de arestas, e nenhuma depende de autoria:

- **as direções que o canônico realiza** — consequência da premissa, não da autoria: o
  favorito de cada confronto sobrevive ao equilíbrio? Medido no evoluído da bateria de
  2026-09-18 (2000 lutas por par): 5/10, exatamente o acaso;
- **a estrutura não-transitiva** (tríades circulares). Ela não depende do rótulo, mas é em
  boa parte **implicada** pelo objetivo: um roster estritamente transitivo tem WRs
  100/75/50/25/0, incompatível com todos perto de 50%, então equilíbrio global com pares
  decididos força intransitividade. O que o objetivo não implica é os pares seguirem
  decididos — e só uma amostra grande mostra isso: a 200 lutas por par, um espelho (puro
  ruído) chega às mesmas tríades.

Números e leitura em [07-findings-and-limitations.md](07-findings-and-limitations.md).
