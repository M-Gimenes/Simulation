# Roteiro da defesa — *Balanceamento competitivo com preservação de identidade*

**Deck:** `index.html` (duplo-clique abre no navegador) · **Duração-alvo:** ~10 min · **16 slides**

**Controles:** `→` / `Espaço` / clique avança · `←` volta · `F` tela cheia · `Home`/`End` início/fim.

**Dicas de entrega**
- Os slides têm pouco texto **de propósito** — a narração carrega o conteúdo. Não leia o slide; use-o de apoio.
- Nos slides de medidores (9 e 10), deixe as barras "carregarem" ~1 s antes de citar o número — o efeito reforça a fala.
- Faça uma pausa curta nos slides-impacto (3 e 14) antes de virar.
- Fale devagar nos resultados (11 e 12); é onde está o miolo.

| # | Slide | ⏱ aprox. |
|---|---|---|
| 1 | Abertura (Equilíbrio vs Identidade) | 0:30 |
| 2 | O problema — a tensão | 0:40 |
| 3 | Pergunta de pesquisa | 0:25 |
| 4 | Medir, não impor | 0:50 |
| 5 | Arquétipos + ciclo | 0:45 |
| 6 | Modelo de combate | 0:45 |
| 7 | Dois objetivos | 0:40 |
| 8 | Escalar vs NSGA-II | 0:35 |
| 9 | Baseline canônico | 0:50 |
| 10 | Otimizar só o equilíbrio | 0:40 |
| 11 | Fronteira de Pareto | 0:50 |
| 12 | Lendo o trade-off | 0:55 |
| 13 | Robustez | 0:40 |
| 14 | Resposta (impacto) | 0:20 |
| 15 | Conclusão + futuro | 0:45 |
| 16 | Obrigado | 0:15 |
| | **Total** | **~10:25** |

---

## Slide 1 — Abertura · ⏱ ~0:30
**No slide:** EQUILÍBRIO **vs** IDENTIDADE + título e autoria.

**Fala:** "Bom dia a todos. Meu nome é Matheus Gimenes, e este é o meu trabalho de conclusão de curso, orientado pelo professor Everson Borges. O título é *Balanceamento competitivo com preservação de identidade*. E o slide já resume a tensão que motiva tudo: de um lado o equilíbrio, do outro a identidade dos personagens — e a pergunta é se dá para ter os dois ao mesmo tempo."

---

## Slide 2 — O problema · ⏱ ~0:40
**No slide:** "Equilibrar é trivial quando todas as opções são iguais. O desafio é equilibrar preservando a diferença."

**Fala:** "Todo jogo competitivo bom depende de duas coisas ao mesmo tempo: equilíbrio — nenhuma opção ser dominante — e identidade — os personagens serem distintos, com estilos próprios. O problema é que essas duas coisas brigam. Quando o designer mexe nos números para igualar as taxas de vitória, o caminho mais fácil é aproximar todo mundo de um mesmo ponto, ou seja, homogeneizar. Equilibrar é trivial se todos forem iguais; o desafio de verdade é equilibrar preservando a diferença."

---

## Slide 3 — Pergunta de pesquisa · ⏱ ~0:25
**No slide:** a pergunta, em destaque.

**Fala:** "Daí a pergunta de pesquisa, bem direta: um Algoritmo Genético consegue atingir equilíbrio competitivo entre cinco arquétipos distintos *sem destruir* as identidades funcionais deles?" *(pausa curta antes de virar)*

---

## Slide 4 — Medir, não impor · ⏱ ~0:50
**No slide:** desvio → penalidade suave (objetivo); ciclo → post hoc.

**Fala:** "A decisão metodológica mais importante do trabalho está aqui: eu **não** forço a identidade. Se eu programasse o algoritmo para preservá-la, ele preservaria — mas só porque foi recompensado pra isso, e a resposta seria circular, não valeria nada. Então faço duas coisas: o desvio em relação ao perfil canônico entra como uma penalidade suave, um dos objetivos que o algoritmo otimiza; e o ciclo de vantagens — quem vence quem — não entra na otimização de jeito nenhum, é só medido depois, *post hoc*. Assim, se a identidade sobreviver, é um achado genuíno."

---

## Slide 5 — Cinco arquétipos + ciclo · ⏱ ~0:45
**No slide:** pentágono do ciclo + papéis dos 5 arquétipos.

**Fala:** "Os cinco arquétipos são os clássicos da comunidade de jogos de luta: *rushdown*, o agressor; *zoner*, que controla o espaço à distância; *grappler*, do agarrão de alto dano; *combo master*, que converte um acerto em sequência; e *turtle*, o defensor que pune erros. Entre eles existe um ciclo não transitivo, tipo pedra-papel-tesoura: cada um vence dois e perde para dois. E um detalhe importante — esse roster e esse ciclo são uma hipótese que eu construí, não uma lei. Por isso ele é medido depois, nunca imposto."

---

## Slide 6 — Modelo de combate · ⏱ ~0:45
**No slide:** campo 1D + intenção → execução.

**Fala:** "Para avaliar cada configuração, eu simulo combate um contra um, tick a tick, num campo unidimensional. A cada instante o lutador decide a ação em duas fases: primeiro uma *intenção* — avançar, recuar ou defender — amostrada segundo os pesos de comportamento daquele personagem; depois essa intenção vira uma ação concreta. Essa amostragem da intenção é a *única* fonte de aleatoriedade do sistema, o que mantém tudo controlado e reprodutível."

---

## Slide 7 — Dois objetivos · ⏱ ~0:40
**No slide:** *drift* (identidade) vs *dominance* (equilíbrio).

**Fala:** "Da simulação saem os dois objetivos do problema. O primeiro é o *drift*: a distância de cada personagem ao seu perfil canônico — mede identidade; quanto menor, mais fiel. O segundo é o *dominance*: mede desequilíbrio, o quanto algum arquétipo domina o elenco; quanto menor, mais equilibrado. Balanceamento, aqui, é literalmente um problema de dois objetivos."

---

## Slide 8 — Escalar vs NSGA-II · ⏱ ~0:35
**No slide:** 1 ponto vs fronteira inteira.

**Fala:** "Eu ataco esse problema de dois jeitos. O AG escalar junta os dois objetivos numa soma ponderada e entrega uma única solução — um ponto do trade-off. Já o NSGA-II não usa pesos: ele mapeia a fronteira de Pareto inteira, do extremo que preserva a identidade ao extremo que equilibra tudo."

---

## Slide 9 — Baseline canônico · ⏱ ~0:50
**No slide:** validador 21/21 e drift 0 · confrontos 0/10, Rush 100% / Turtle 0%.

**Fala:** "Começando pelo ponto de partida, o roster canônico. Em identidade ele é perfeito por construção: passa nas 21 asserções do validador e o desvio é zero. Mas em equilíbrio é péssimo: nenhum dos dez confrontos é equilibrado, o *rushdown* ganha de todo mundo — cem por cento — e o *turtle* não ganha de ninguém. E tem um achado interessante: mesmo o ciclo que eu hipotetizei só se sustenta em cinco das dez arestas. Ou seja, o modelo determinístico, sozinho, não reproduz o ciclo dos jogos reais."

---

## Slide 10 — Otimizar só o equilíbrio · ⏱ ~0:40
**No slide:** confrontos 10/10 · validador 7/21.

**Fala:** "Agora, quando eu deixo o AG escalar perseguir o equilíbrio, ele consegue: os dez confrontos ficam equilibrados. Mas olha o custo — o validador de identidade despenca de 21 para 7, e os personagens começam a se parecer. Isso confirma, na prática, a tensão que a pergunta previa: igualar as vitórias, sozinho, dissolve as identidades. E é exatamente isso que justifica tratar os dois como objetivos separados."

---

## Slide 11 — Fronteira de Pareto · ⏱ ~0:50
**No slide:** curva com best_drift, knee point e best_dominance.

**Fala:** "E aqui está o artefato central do trabalho: a fronteira de Pareto do NSGA-II, com trezentas soluções não dominadas. Cada ponto é um elenco possível. Num extremo, o *best_drift* — que é o próprio canônico: identidade máxima, mas desequilíbrio alto. No outro, o *best_dominance*: equilíbrio máximo. E no meio, o joelho da curva, o melhor compromisso. A fronteira responde à pergunta de forma visual: equilíbrio e identidade realmente são conflitantes, e dá para medir exatamente quanto se troca de um pelo outro."

---

## Slide 12 — Lendo o trade-off · ⏱ ~0:55
**No slide:** tabela com a coluna *knee point* em destaque.

**Fala:** "Vamos ler os números — repara na coluna do joelho, em destaque. Ele reduz o desequilíbrio de 1,42 para 0,34, quer dizer, pega quase todo o ganho de equilíbrio; e mesmo assim mantém 20 das 21 asserções de identidade, praticamente intacto. Já o extremo *best_dominance* equilibra ainda mais — nove dos dez confrontos — mas aí a identidade cai para 13 de 21. Ou seja: o joelho da fronteira é o ponto doce, onde você ganha quase todo o equilíbrio quase sem abrir mão da identidade."

---

## Slide 13 — Robustez · ⏱ ~0:40
**No slide:** 10 execuções (90–100%) · validação externa 5/5 e 9/10.

**Fala:** "Como um algoritmo evolutivo é estocástico, eu não confio numa execução só. Agregando dez execuções independentes, cada personagem fica globalmente equilibrado em 90 a 100 por cento das vezes — isso é a parte estrutural, não sorte. E, para fechar, eu revalido a melhor solução *fora* do laço de otimização, com dez sementes totalmente novas: os cinco personagens continuam equilibrados e nove dos dez confrontos se mantêm. Ou seja, não é sobreajuste à função de avaliação."

---

## Slide 14 — Resposta · ⏱ ~0:20
**No slide:** "Sim — equilíbrio substancial, identidade preservada."

**Fala:** "Então, a resposta à pergunta é *sim*: dá para ter equilíbrio substancial com a identidade preservada. E o principal — o trade-off entre os dois, que antes o designer fazia no olho, vira uma escolha explícita e informada." *(pausa antes de virar)*

---

## Slide 15 — Conclusão + trabalhos futuros · ⏱ ~0:45
**No slide:** 3 conclusões + limitações/futuro.

**Fala:** "Concluindo: equilíbrio substancial é compatível com identidade largamente preservada — quase intacta no joelho da fronteira; o equilíbrio *total* é que exige alguma homogeneização; e a grande contribuição é a fronteira permitir *escolher* conscientemente esse ponto, em vez de aceitar o resultado fixo de uma soma ponderada. Entre as limitações, o modelo de combate é simplificado e são só cinco arquétipos. E como trabalhos futuros vejo três direções: coevolução, para estressar o equilíbrio contra um oponente que também se adapta; *quality-diversity* com MAP-Elites; e análise de mecânicas por *restricted play*."

---

## Slide 16 — Obrigado · ⏱ ~0:15
**No slide:** agradecimento + contato.

**Fala:** "É isso. Obrigado pela atenção — fico à disposição da banca para as perguntas."
