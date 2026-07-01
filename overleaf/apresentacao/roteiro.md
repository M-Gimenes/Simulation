# Roteiro da Defesa — *Balanceamento Competitivo com Preservação de Identidade*

**Apresentação:** `index.html` (abrir no navegador) &nbsp;·&nbsp; **Duração estimada:** ~10 min &nbsp;·&nbsp; **16 slides**

**Navegação:** `→` / `Espaço` / clique avança &nbsp;·&nbsp; `←` recua &nbsp;·&nbsp; `F` tela cheia &nbsp;·&nbsp; `Home`/`End` início/fim.

**Orientações gerais de apresentação**

- Os slides contêm pouco texto intencionalmente — a narração conduz o conteúdo. Não leia o slide; utilize-o como apoio visual.
- Nos slides de métricas (9 e 10), aguarde aproximadamente 1 segundo para que as barras sejam preenchidas antes de mencionar os valores — o efeito visual reforça a informação verbal.
- Faça uma pausa breve nos slides de impacto (3 e 14) antes de avançar.
- Reduza o ritmo de fala nos slides de resultados (11 e 12); ali está o núcleo da contribuição.

| #  | Slide                                  | ⏱ aprox.        |
| -- | -------------------------------------- | ---------------- |
| 1  | Abertura — Equilíbrio vs Identidade  | 0:30             |
| 2  | O problema — a tensão central        | 0:40             |
| 3  | Pergunta de pesquisa                   | 0:25             |
| 4  | Medir, não impor                      | 0:50             |
| 5  | Cinco arquétipos e ciclo de vantagens | 0:45             |
| 6  | Modelo de combate                      | 0:45             |
| 7  | Dois objetivos                         | 0:40             |
| 8  | AG escalar vs NSGA-II                  | 0:35             |
| 9  | Baseline canônico                     | 0:50             |
| 10 | Otimizar apenas o equilíbrio          | 0:40             |
| 11 | Fronteira de Pareto                    | 0:50             |
| 12 | Leitura do trade-off                   | 0:55             |
| 13 | Robustez                               | 0:40             |
| 14 | Resposta — impacto                    | 0:20             |
| 15 | Conclusão e trabalhos futuros         | 0:45             |
| 16 | Agradecimentos                         | 0:15             |
|    | **Total**                        | **~10:25** |

---

## Slide 1 — Abertura · ⏱ ~0:30

**No slide:** EQUILÍBRIO **vs** IDENTIDADE · título · autoria.

**Fala:** "Bom dia. Meu nome é Matheus Gimenes de Souza, e este é meu Trabalho de Conclusão de Curso, orientado pelo Professor Doutor Everson Scherrer Borges. O trabalho é intitulado *Balanceamento Competitivo com Preservação de Identidade*, e o próprio slide sintetiza a tensão que o motiva: de um lado o equilíbrio competitivo, do outro a identidade funcional dos personagens — a questão central é se é possível obter ambos simultaneamente."

---

## Slide 2 — O problema · ⏱ ~0:40

**No slide:** "Equilibrar é trivial quando todas as opções são iguais. O desafio é equilibrar preservando a diferença."

**Fala:** "Todo jogo competitivo bem projetado depende de dois fatores concomitantes: equilíbrio — nenhuma opção ser sistematicamente dominante — e identidade — os personagens possuírem estilos de jogo distintos e reconhecíveis. O problema é que esses dois fatores conflitam estruturalmente. Quando o designer ajusta os parâmetros para equalizar as taxas de vitória, o caminho de menor resistência é aproximar todos os personagens de um mesmo ponto no espaço de atributos, ou seja, homogeneizá-los. Equilibrar é trivial quando todas as opções são idênticas; o desafio real é equilibrar preservando a diferença."

---

## Slide 3 — Pergunta de pesquisa · ⏱ ~0:25

**No slide:** a pergunta de pesquisa em destaque.

**Fala:** "Esse contexto leva diretamente à pergunta de pesquisa: um Algoritmo Genético é capaz de atingir equilíbrio competitivo entre cinco arquétipos distintos *sem destruir* suas identidades funcionais?" *(pausa antes de avançar)*


---

## Slide 4 — Cinco arquétipos + ciclo · ⏱ ~0:45

**No slide:** pentágono do ciclo de vantagens · papéis dos cinco arquétipos.

**Fala:** "O experimento foi conduzido sobre cinco arquétipos clássicos da comunidade de jogos de luta: o *rushdown*, agressor de curta distância; o *zoner*, que controla o espaço à distância; o *grappler*, focado em agarrões de alto dano; o *combo master*, que converte acertos em sequências; e a *turtle*, personagem defensivo que pune os erros do adversário. Entre eles existe um ciclo de vantagens não transitivo — análogo ao pedra-papel-tesoura — no qual cada arquétipo vence dois e perde para dois. É importante destacar que esse roster e esse ciclo constituem uma hipótese de trabalho, não uma verdade prescrita, razão pela qual são mensurados apenas ao final da otimização."

---

## Slide 5 — Modelo de combate · ⏱ ~0:45

**No slide:** campo unidimensional · pipeline intenção → execução.

**Fala:** "Para avaliar cada configuração gerada pelo algoritmo, simula-se um combate um contra um, passo a passo, num campo unidimensional. A cada instante, o lutador determina sua ação em duas fases: primeiro é amostrada uma *intenção* — avançar, recuar ou defender — de acordo com os pesos comportamentais do personagem; em seguida, essa intenção é mapeada para uma ação concreta. Essa amostragem da intenção constitui a *única* fonte de estocasticidade do sistema, o que mantém o modelo controlado e os resultados reprodutíveis."

---

## Slide 6 — Dois objetivos · ⏱ ~0:40

**No slide:** *drift* (identidade) vs *dominance* (equilíbrio).

**Fala:** "Da simulação derivam os dois objetivos do problema de otimização. O primeiro é o *drift*: a distância euclidiana normalizada de cada personagem ao seu perfil canônico — mensura preservação de identidade; quanto menor, mais fiel ao arquétipo original. O segundo é o *dominance*: quantifica o desequilíbrio, ou seja, o quanto algum arquétipo domina ou é dominado pelo elenco; quanto menor, mais equilibrado o roster. O balanceamento é, portanto, um problema genuinamente bi-objetivo."

---

## Slide 7 — AG escalar vs NSGA-II · ⏱ ~0:35

**No slide:** um ponto vs fronteira completa.

**Fala:** "O problema é abordado por dois métodos. O AG escalar combina os dois objetivos em uma soma ponderada e retorna uma única solução — correspondente a um ponto específico do trade-off. O NSGA-II, por sua vez, opera sem pesos fixos e mapeia a fronteira de Pareto completa, do extremo que maximiza a preservação de identidade ao extremo que maximiza o equilíbrio competitivo."

---

## Slide 8 — Baseline canônico · ⏱ ~0:50

**No slide:** validador 21/21 · drift 0 · confrontos 0/10 · Rushdown 100% · Turtle 0%.

**Fala:** "O ponto de partida é o roster canônico. Em termos de identidade, ele é perfeito por construção: satisfaz todas as 21 asserções do validador e apresenta desvio nulo. Em termos de equilíbrio, porém, é completamente inadequado: nenhum dos dez confrontos é equilibrado, o *rushdown* apresenta taxa de vitória global de cem por cento, e a *turtle* não vence nenhum adversário. Um resultado adicional relevante: mesmo o ciclo de vantagens hipotetizado se sustenta em apenas cinco das dez arestas no modelo determinístico. Ou seja, o roster canônico, isoladamente, não reproduz o comportamento esperado pela teoria dos jogos de luta."

---

## Slide 9 — Otimizar só o equilíbrio · ⏱ ~0:40

**No slide:** confrontos 10/10 · validador 7/21.

**Fala:** "Quando o AG escalar é configurado para otimizar exclusivamente o equilíbrio, ele o obtém: todos os dez confrontos tornam-se equilibrados. O custo, contudo, é expressivo — o validador de identidade regride de 21 para 7 asserções satisfeitas, e os personagens passam a apresentar perfis progressivamente semelhantes. Esse resultado empírico confirma a tensão prevista na formulação do problema: equalizar as taxas de vitória, sem qualquer contrapartida, dissolve as identidades funcionais. É precisamente isso que justifica o tratamento como problema bi-objetivo."

---

## Slide 10 — Fronteira de Pareto · ⏱ ~0:50

**No slide:** curva com best_drift, knee point e best_dominance.

**Fala:** "O principal artefato do trabalho é a fronteira de Pareto obtida pelo NSGA-II, composta por trezentas soluções não dominadas. Cada ponto representa um roster candidato. No extremo identificado como *best_drift* encontra-se o próprio canônico: identidade máxima, mas desbalanço elevado. No extremo oposto, o *best_dominance*: equilíbrio máximo. No meio da curva, o *knee point* representa o melhor compromisso entre os dois objetivos. A fronteira responde à pergunta de pesquisa de forma quantitativa e visual: os dois objetivos são de fato conflitantes, e é possível mensurar com precisão o quanto se cede de um ao melhorar o outro."

---

## Slide 11 — Leitura do trade-off · ⏱ ~0:55

**No slide:** tabela comparativa com a coluna *knee point* em destaque.

**Fala:** "Examinando os números — com atenção à coluna do *knee point*, destacada na tabela. Ele reduz o desbalanço de 1,42 para 0,34, capturando a maior parte do ganho de equilíbrio; e ainda assim preserva 20 das 21 asserções de identidade, mantendo o roster praticamente intacto. O extremo *best_dominance*, por sua vez, equilibra ainda mais — nove dos dez confrontos — mas ao custo de reduzir o validador de identidade para 13 de 21. A interpretação é clara: o *knee point* representa o ponto ótimo de operação, onde se obtém ganho de equilíbrio substancial com perda de identidade mínima."

---

## Slide 12 — Robustez · ⏱ ~0:40

**No slide:** 10 execuções (90–100%) · validação externa 5/5 e 9/10.

**Fala:** "Dado que algoritmos evolutivos são estocásticos, a análise de robustez é indispensável. Ao agregar dez execuções independentes, verifica-se que cada personagem se mantém globalmente equilibrado em 90 a 100 por cento das execuções — indicando que o resultado não é produto de uma configuração de semente favorável. Complementarmente, a melhor solução encontrada é revalidada *fora* do laço de otimização, com dez sementes totalmente inéditas: os cinco personagens permanecem equilibrados e nove dos dez confrontos se sustentam em todas as condições testadas. Conclui-se que não há sobreajuste à função de avaliação."

---

## Slide 13 — Resposta · ⏱ ~0:20

**No slide:** "Sim — equilíbrio substancial, identidade preservada."

**Fala:** "A resposta à pergunta de pesquisa é *sim*: é possível obter equilíbrio competitivo substancial com identidade funcional amplamente preservada. Mais do que isso — o trade-off entre os dois objetivos, que anteriormente era tratado de forma artesanal pelo designer, torna-se uma escolha explícita, fundamentada e navegável." *(pausa antes de avançar)*

---

## Slide 14 — Conclusão e trabalhos futuros · ⏱ ~0:45

**No slide:** três conclusões · limitações e direções futuras.

**Fala:** "Sintetizando as conclusões: equilíbrio substancial é compatível com identidade largamente preservada — praticamente intacta no *knee point* da fronteira; equilíbrio total, por sua vez, demanda alguma homogeneização; e a principal contribuição é a fronteira de Pareto permitir que o designer *escolha conscientemente* o ponto de operação desejado, em lugar de aceitar o resultado fixo de uma soma ponderada. Entre as limitações do trabalho, destaca-se o modelo de combate simplificado — sem frames de animação ou situações de mix-up — e a restrição a cinco arquétipos. Como direções para trabalhos futuros, identificam-se três caminhos: a coevolução, para estressar o equilíbrio contra um oponente que também se adapta; a abordagem de *quality-diversity* com MAP-Elites; e a análise de mecânicas via *restricted play*."

---

## Slide 15 — Agradecimentos · ⏱ ~0:15

**No slide:** agradecimento e contato.

**Fala:** "Concluo aqui minha apresentação. Agradeço à banca pela atenção e coloco-me à disposição para as perguntas."
