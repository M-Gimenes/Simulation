# 02 — Status epistemológico do ciclo canônico

**Entra em**: Introdução / Metodologia (e Discussão, se o ciclo quebrar).

> O *conteúdo* do ciclo (quem vence quem, e por quê) está em
> [`../03-archetypes.md`](../reference/03-archetypes.md). Aqui está o **status** dele: o que ele
> é epistemologicamente, e por que a tese não depende dele estar "certo".

## O ciclo é uma construção do autor, não uma lei do sistema

O ciclo (Rushdown > Zoner > Grappler > … ) é uma **construção** derivada da convenção
FGC, usada como **hipótese de estrutura preservável**. Não é uma propriedade física
emergente das mecânicas — é uma expectativa que se *mede* contra o que o sistema
produz.

## Quebra do ciclo é um achado, não uma falha

O sistema não tem obrigação de "entregar o ciclo"; tem obrigação de **equilibrar** e
de **permitir medir** a preservação de identidade. Se o ciclo não se sustenta no
modelo determinístico, isso **revela** algo: que a estrutura FGC depende parcialmente
de elementos estocásticos/de combo (combo chaining, variância) que foram
conscientemente removidos ou minimizados. Isso é resultado, não erro de método.

### Duas quebras distintas — não confundir (reformulação C2)

É preciso separar **duas** possíveis quebras do ciclo, com leituras diferentes:

1. **No baseline (canônico):** o modelo de combate determinístico pode não produzir
   o ciclo nem antes de qualquer otimização — leitura acima (mecânicas estocásticas
   omitidas). **Segue válida.**
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
está em [03-formulacao-do-fitness.md](03-formulacao-do-fitness.md) e
[`../reference/05-genetic-algorithm.md`](../reference/05-genetic-algorithm.md).)

## O ciclo poderia ser outro — e isso não compromete a tese

A atribuição das arestas é uma **operacionalização entre várias defensáveis**:
- há consenso FGC para a maioria (Rushdown × Zoner, Grappler × Turtle, Turtle ×
  Rushdown);
- algumas admitem leituras alternativas conforme jogo/era/meta;
- **cada aresta tem justificativa de domínio documentada** ([`../03-archetypes.md`](../reference/03-archetypes.md)) —
  é estipulativo, não arbitrário (trocar uma exigiria nova justificativa, não sortear
  outro valor).

A tese **não depende do ciclo específico ser "o correto"**: um ciclo alternativo
defensável daria outros canônicos, mas o experimento sobre o trade-off equilíbrio ×
identidade produziria um achado **da mesma natureza**. **O ciclo é palco, não objeto
de teste.**

> Análoga útil para a redação: ninguém trata "por que 5 arquétipos e não 4 ou 7?" como
> falha metodológica — é operacionalização. "Por que esse ciclo e não outro?" é da
> mesma natureza.
