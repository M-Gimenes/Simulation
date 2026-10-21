# Roteiro da defesa do TCC

Defesa do trabalho de conclusão de curso à banca (Prof. Dr. Flávio Izo e Prof. Dr. Rafael Silva
Guimarães; orientador Prof. Dr. Everson Scherrer Borges): **10 a 15 minutos de fala**, seguidos da
arguição. A banca já leu a monografia de 100 páginas.

A primeira apresentação, em 21/10/2026, contava os achados como a palestra de um artigo. Esta segue a
estrutura da monografia: introdução, referencial teórico, metodologia, resultados e conclusão. As falas
são mais técnicas em todos os blocos, sem perder o fio da história.

Todo número, na fala e nos slides, vem da monografia entregue (`overleaf/TCC/valores.tex` e os
capítulos de resultados e discussão), isto é, da bateria de 23/09/2026. Nada foi re-rodado: as
figuras dos slides foram redesenhadas, em tamanho de projeção, a partir dos mesmos artefatos de
`results/`. Há uma exceção: o ganho do Numba (cerca de 150 vezes sobre Python puro, slide 13) é uma
medição do projeto (`docs/reference/09-reproducibility.md`) e não está na monografia. Se perguntarem,
diga isso.

A mesma fala está nas notas do orador de cada slide em `slides.pptx`.

## A história em uma frase por bloco

1. **Introdução (slides 2–4).** Equilibrar um elenco é caro, manual e nunca termina. Há dois erros
   possíveis: um personagem dominar, ou todos ficarem iguais. A pergunta é se um AG equilibra sem
   apagar as identidades; ela se divide em QP1, QP2 e QP3, e os objetivos específicos seguem a ordem do
   trabalho.
2. **Referencial (5–8).** Equilibrar não é igualar: o equilíbrio admite vantagens recíprocas, e
   Gingold liga isso a um ciclo. O AG só enxerga o problema pela aptidão, e uma aptidão simulada tem
   ruído. Com dois objetivos, dá para somar ou comparar por dominância (NSGA-II). Nenhum trabalho
   anterior trata luta em tempo real, equilíbrio contra identidade e identidade medida fora da busca ao
   mesmo tempo.
3. **Metodologia (9–13).** A busca usa a simulação como caixa-preta, e o que se mede depois nunca
   volta ao laço. O simulador separa postura (sorteada) de ataque (regra). A aptidão contém o que cada
   arquétipo *é*, nunca quem deve *vencer*. São cinco braços pareados no mesmo orçamento, e a
   implementação torna cada número reprodutível.
4. **Resultados (14–20).** O AG equilibra (QP1) e replica fora do laço. A identidade que sobra se
   deve ao termo, mas a política se perde (QP2). Nenhum algoritmo domina o outro, mas o AG escalar fica
   longe do próprio ótimo; o motivo são dois estágios da seleção escalar, e o híbrido, que protege a
   identidade no início, recupera boa parte dela sem custo de equilíbrio (QP3).
5. **Conclusão (21–23).** Sim, com pressão explícita por identidade e uma busca que mantenha a
   diversidade sob ruído. Cinco contribuições; limites e próximos passos saem dos próprios achados.

## O fio entre o referencial e o resto

Cada slide do referencial planta algo que a metodologia usa e os resultados cobram. Faça a ligação em
voz alta quando chegar nela: é ela que mostra domínio da teoria, mais do que a definição sozinha.

- **Slide 5, vantagens recíprocas** → o termo global da aptidão (slide 11), que deixa cada
  personagem vencer dois e perder dois. O ciclo como hipótese → R1.
- **Slide 6, torneio ordinal** → "só a razão entre os pesos importa", o λ = 1 do slide 11. **Aptidão
  ruidosa** → os sorteios comuns e a rotação (slide 9), a reavaliação com mil lutas (slide 12) e o
  segundo estágio (slide 19, "é o problema da aptidão ruidosa").
- **Slide 7, a escalarização fixa o ponto** → o escalar numa ponta da fronteira (slide 18). A
  **multiobjetivização** e o extremo de menor desvio que ninguém domina → o híbrido (slide 20).
- **Slide 8, Browne e Maire** → a validação externa (slide 15). A **lacuna** → as contribuições
  (slide 22).
- Dentro da metodologia, "passo quatro vezes menor nos pesos" (slide 9) volta no slide 17, a política.

## Código de cores dos slides

Para se guiar sem ler: **azul** é o AG escalar, **laranja** o NSGA-II, **verde-água** o híbrido e
**cinza-escuro** os controles, as mesmas cores das figuras da monografia. **Vermelho** é desequilíbrio
(e "frágil"), **roxo** é desvio de identidade e os perfis canônicos. Nos títulos, **QP1/QP2/QP3** em
verde dizem a qual questão o slide responde, e o cabeçalho marca a seção atual (Introdução,
Referencial, Metodologia, Resultados, Conclusão).

## Tempo por slide

São 2156 palavras. A 150 palavras por minuto, ritmo calmo, a fala leva 14:22; a 165, ritmo da
Latinoware, 13:04. O referencial leva 2:43 a 150 e 2:28 a 165. O limite é 15 minutos: ensaie com
cronômetro e, se passar de 13:30, use os cortes abaixo, que somam cerca de 70 segundos.

| # | Slide | Palavras | a 150 ppm | a 165 ppm |
|---|---|---|---|---|
| 1 | Capa | 51 | 0:20 | 0:19 |
| 2 | Introdução: o contexto | 86 | 0:34 | 0:31 |
| 3 | Introdução: o problema | 79 | 0:32 | 0:29 |
| 4 | Introdução: pergunta e objetivos | 99 | 0:40 | 0:36 |
| 5 | Referencial: equilíbrio competitivo e arquétipos | 102 | 0:41 | 0:37 |
| 6 | Referencial: algoritmos genéticos e aptidão ruidosa | 100 | 0:40 | 0:36 |
| 7 | Referencial: otimização multiobjetivo e NSGA-II | 102 | 0:41 | 0:37 |
| 8 | Referencial: trabalhos relacionados | 104 | 0:42 | 0:38 |
| 9 | Metodologia: arquitetura | 114 | 0:46 | 0:41 |
| 10 | Metodologia: representação e simulador | 112 | 0:45 | 0:41 |
| 11 | Metodologia: a aptidão (premissa, nunca resposta) | 113 | 0:45 | 0:41 |
| 12 | Metodologia: braços e protocolo | 109 | 0:44 | 0:40 |
| 13 | Metodologia: implementação | 89 | 0:36 | 0:32 |
| 14 | QP1: da hierarquia ao equilíbrio | 94 | 0:38 | 0:34 |
| 15 | QP1: fora do laço | 93 | 0:37 | 0:34 |
| 16 | QP2: o controle sem identidade | 99 | 0:40 | 0:36 |
| 17 | QP2: a política | 97 | 0:39 | 0:35 |
| 18 | QP3: a fronteira | 92 | 0:37 | 0:33 |
| 19 | QP3: por quê? Dois estágios | 93 | 0:37 | 0:34 |
| 20 | QP3: o híbrido | 90 | 0:36 | 0:33 |
| 21 | Conclusão: as três respostas | 84 | 0:34 | 0:31 |
| 22 | Conclusão: contribuições | 72 | 0:29 | 0:26 |
| 23 | Conclusão: limites e próximos passos | 82 | 0:33 | 0:30 |
| 24 | Obrigado (fica na tela durante as perguntas) | 0 | 0:00 | 0:00 |
| | **Total** | **2156** | **14:22** | **13:04** |

## Fala

### 1. Capa

Boa tarde, professores. Meu nome é Matheus Gimenes, e vou apresentar o meu trabalho de conclusão de curso, orientado pelo professor Everson. O trabalho aplica algoritmos genéticos ao balanceamento de personagens em jogos de luta e pergunta se é possível equilibrar um elenco sem apagar o que torna cada personagem único.

### 2. Introdução: o contexto

Os jogos digitais faturaram 188,8 bilhões de dólares em 2025, segundo a Newzoo, e sobre essa base cresceram os esports. Quando há competição, o equilíbrio entre personagens deixa de ser só uma questão de design: se poucos são viáveis, o jogo perde profundidade estratégica. Hoje, equilibrar é um ciclo manual de ajustar números, testar, observar e repetir, que continua depois do lançamento, a cada atualização. Há cerca de duas décadas, a computação evolutiva estuda como automatizar parte desse ciclo, usando a simulação como função de avaliação.

### 3. Introdução: o problema

Há duas formas de errar no balanceamento. A mais conhecida é deixar um personagem forte demais, e todos passam a escolhê-lo. A segunda aparece ao corrigir a primeira: os números são ajustados até ninguém dominar, mas os personagens ficam parecidos. No limite, dar a todos os mesmos atributos produz equilíbrio perfeito, e a escolha deixa de importar; esse elenco espelho é, no trabalho, a solução trivial de referência. O desafio fica entre os dois erros: equilibrar preservando a diferença.

### 4. Introdução: pergunta e objetivos

A pergunta de pesquisa é se um algoritmo genético consegue equilibrar cinco arquétipos de um jogo de luta sem destruir as suas identidades funcionais. Ela se divide em três questões: se o elenco fica equilibrado, inclusive fora da otimização; se a identidade sobrevive além do que sobreviveria sem um termo de identidade; e onde o AG escalar, o NSGA-II e um híbrido ficam no compromisso entre os dois. Os objetivos específicos seguem a ordem do trabalho: modelar os arquétipos, construir o simulador, formular a aptidão, comparar os três algoritmos no mesmo orçamento e medir a identidade fora da busca.

### 5. Referencial: equilíbrio competitivo e arquétipos

O equilíbrio competitivo tem duas leituras. Na simetria estatística, cada opção tem 50% contra cada outra. Nas vantagens recíprocas, de Adams e Elias, cada opção vence alguns confrontos e perde outros, sem que nenhuma domine. Gingold mostra, nas ações de um jogo de luta, que para nenhuma escolha ser imbatível as vantagens precisam formar um ciclo, como no Pedra-Papel-Tesoura. Levo o argumento aos personagens: cinco arquétipos, o menor elenco em que cada um vence dois e perde dois. O ciclo é hipótese minha, medida só depois. Para a aptidão, equilibrar é impedir que alguém domine, e não forçar 50% em cada par.

### 6. Referencial: algoritmos genéticos e aptidão ruidosa

Um algoritmo genético, de Holland e Goldberg, evolui uma população por seleção, cruzamento e mutação, e a aptidão é o seu único elo com o problema. Três propriedades importam: o torneio depende só da ordem das aptidões, então numa soma só a razão entre os pesos conta; o cruzamento por blocos herda juntas partes coerentes do cromossomo; e o passo da mutação regula exploração e explotação. Quando a aptidão vem de simulação, ela é uma variável aleatória, e, como discutem Jin e Branke, a seleção passa a premiar sorte. As defesas são números aleatórios comuns e reavaliar a solução final.

### 7. Referencial: otimização multiobjetivo e NSGA-II

Com dois objetivos em conflito, não há um ótimo único. A escalarização soma os dois com pesos, o que fixa de antemão o ponto do compromisso. A alternativa é a dominância de Pareto: uma solução domina outra se não é pior em nenhum objetivo e é melhor em pelo menos um, e as não dominadas formam a fronteira. O NSGA-II, de Deb e colegas, ordena a população em frentes, prefere os pontos isolados para espalhar a fronteira e põe pais e filhos na mesma disputa. E Knowles mostrou que separar os termos de uma soma preserva diversidade: é a ideia do híbrido.

### 8. Referencial: trabalhos relacionados

Esse tipo de busca é aplicado ao balanceamento há duas décadas, no que Togelius e colegas chamam de geração de conteúdo baseada em busca. Hom e Marks evoluíram regras de jogos de tabuleiro; Browne e Maire, jogos inteiros, avaliados por medidas externas à aptidão, princípio que adoto. O mais próximo é Chen e colegas, que equilibraram raças de um MMORPG em combate por turnos. Volz e colegas usaram otimização multiobjetivo num jogo de cartas. Nenhum trata luta em tempo real, nenhum formula o problema como compromisso entre equilíbrio e identidade, e nenhum mede se a identidade sobrevive. É nessa interseção que o trabalho entra.

### 9. Metodologia: arquitetura

O sistema tem duas camadas: a simulação decide as lutas sem conhecer os objetivos, e a otimização a usa como caixa-preta. Os perfis canônicos entram como referência do desvio e, no AG escalar, como semente da geração zero, ao lado de 299 elencos sorteados. Todos os elencos de uma geração enfrentam os mesmos sorteios, semeados luta a luta, e os sorteios mudam a cada geração, para a busca não se ajustar a eles. A seleção usa elitismo de 10% e torneio de três; o cruzamento passa cada personagem inteiro de um pai; e a mutação gaussiana atinge 5% dos genes, com passo quatro vezes menor nos pesos. As medições finais nunca voltam ao laço.

### 10. Metodologia: representação e simulador

Cada personagem tem onze genes: oito atributos, como vida, dano, alcance e agarrão, que dizem o que ele pode fazer, e três pesos, que dizem o que ele tende a fazer. A decisão central do simulador é separar dois canais. A postura, entre avançar, recuar e guardar, é sorteada com probabilidade proporcional aos pesos e mantida por um tick, de cinco sub-ticks; esse sorteio é a única fonte de aleatoriedade. O ataque é uma regra: sai quando a recarga terminou, o oponente está ao alcance e o personagem não guarda. É isso que faz do controle de distância uma estratégia. A guarda reduz o dano em 40%, e o agarrão a rompe.

### 11. Metodologia: a aptidão (premissa, nunca resposta)

A aptidão pode conter o que cada arquétipo é, a premissa, mas nunca quem deve vencer quem, a resposta. O desequilíbrio tem três termos: o principal é a raiz da média dos quadrados da distância de cada taxa de vitória global a 50%; os secundários barram confrontos acima de 65%, entre o 6-4 saudável e o 7-3 de um counter, e lutas decididas por massacre. Todos usam a distância a 50%, nunca a direção. O desvio mede a distância de cada gene ao canônico, normalizada pela faixa, com peso três nos genes definidores. O AG escalar soma os dois termos com pesos iguais, o joelho de uma varredura; o NSGA-II os minimiza separados.

### 12. Metodologia: braços e protocolo

A bateria tem cinco braços. O AG escalar e o NSGA-II são os dois que a pergunta compara; o NSGA-II começa de uma população sorteada e entra nos testes pelo ponto da fronteira que minimiza a mesma soma. Dois controles repetem o escalar com um só fator alterado: sem o termo de identidade, o contrafactual da QP2, e sem a semente canônica. O quinto é o híbrido. São 20 execuções por braço, com as mesmas sementes, então o desenho é pareado: Wilcoxon, Â12 e correção de Holm sobre uma família fixa de métricas. Os elencos finais são reavaliados com mil lutas por par e lidos contra 35 modelos nulos.

### 13. Metodologia: implementação

O sistema é escrito em Python, e o laço de combate é compilado com Numba, cerca de 150 vezes mais rápido que Python puro. Uma execução do AG escalar simula 68 milhões de lutas; uma do NSGA-II, 135 milhões. A avaliação roda em processos paralelos, e, como cada luta é semeada pela sua posição, o resultado não depende do número de processos. Cada arquivo de resultado registra a configuração e resumos do código que o produziu: carregar um desatualizado gera aviso, e gerar outro a partir dele é recusado.

### 14. QP1: da hierarquia ao equilíbrio

Começo pela primeira questão. O canônico, à esquerda, é uma hierarquia: o Rushdown vence praticamente todas as lutas, o Turtle nenhuma, e o desequilíbrio é 1,28. À direita, a média das vinte execuções do AG escalar, com todos os confrontos entre 46% e 54%. A convergência exige o equilíbrio no laço e numa reavaliação com sorteios inéditos; veio nas vinte execuções, em média na geração 31, e dezesseis terminam equilibradas. É perto da simetria, mas não nela: as taxas globais ficam a 1,6 ponto de 50%, contra 0,7 de puro ruído num elenco espelho.

### 15. QP1: fora do laço

Equilibrar no laço não basta, porque a busca pode se ajustar aos sorteios. Na validação externa, o elenco foi testado com cinco mil lutas por par em sementes inéditas, e cada taxa de vitória foi classificada pelo intervalo de Wilson de 95% contra a faixa. Ele foi o único dos quatro elencos testados a replicar o equilíbrio. Alterando uma regra do combate por vez, resiste a quatro das oito mudanças, fica inconclusivo em duas e quebra no campo menor e na persistência maior. É um equilíbrio real, mas ajustado às regras do treino.

### 16. QP2: o controle sem identidade

Na segunda questão, a evidência é o controle. Sem o termo de identidade, o mesmo algoritmo, com o mesmo orçamento, perde identidade nas quatro métricas, com efeito grande e p corrigido de no máximo 0,0044, e cai ao nível de elencos sorteados. A concordância τ, a correlação de Kendall entre a ordem canônica e a do elenco nas métricas de comportamento, vai de 0,28 a praticamente zero. No equilíbrio, os braços não se separam depois de Holm. A identidade que sobrevive se deve ao termo, que não custou equilíbrio mensurável, mas é parcial: três de cinco asserções de comportamento.

### 17. QP2: a política

O que mais se perde é a política. O Rushdown canônico avança em 86% das intenções; no AG escalar, em 39%, e os cinco convergem para uma política parecida. A análise de sensibilidade explica: no passo de mutação atual, cada peso move a taxa de vitória em 3 a 5 pontos, perto do piso de ruído de 3,5. Com o passo relativo dos atributos, move de 12 a 17 pontos, mais que o atordoamento. A política pesa no combate, mas, com mutação quatro vezes menor, cada passo dela some no ruído. A busca quase não a enxerga.

### 18. QP3: a fronteira

Na terceira questão, cada linha cinza é a fronteira de uma execução do NSGA-II, e os pontos azuis são o AG escalar. O NSGA-II preserva mais identidade, com τ de 0,54, mas deixa 2,8 counters por elenco e nenhum elenco equilibrado. O escalar fica além da ponta de equilíbrio da fronteira em 19 de 20 sementes, e, semente a semente, nenhum dos dois domina o outro em 18 de 20. Mas, na própria soma que o escalar otimiza, a fronteira tem um ponto melhor que o dele em todas as vinte sementes.

### 19. QP3: por quê? Dois estágios

Por que o escalar não chega ao próprio ótimo? Em dois estágios. No início, as diferenças de equilíbrio entre elencos são grandes, e a soma privilegia esse termo: o canônico sai na terceira geração, e, na vigésima, o elenco mais fiel que resta já tem desvio 0,24. Depois da convergência, o desvio é exato, mas o desequilíbrio é amostrado, e o seu ruído é cerca de sessenta vezes o ganho de identidade por geração. É o problema da aptidão ruidosa: a seleção passa a premiar sorte, e a identidade perdida quase não volta.

### 20. QP3: o híbrido

Se a explicação está certa, proteger a identidade no início deveria ajudar, e é o que o híbrido faz: na fase de Pareto, o elenco de menor desvio nunca é dominado, então nunca é descartado. Com o mesmo orçamento, ele chega perto da identidade do NSGA-II, com desvio de 0,17 contra 0,25 e τ de 0,52 contra 0,28, efeitos grandes com p corrigido de no máximo 0,0058, e mantém o equilíbrio do escalar, com dezesseis elencos equilibrados em vinte. O preço é a velocidade: converge na geração 98, contra 31.

### 21. Conclusão: as três respostas

Voltando às questões. No equilíbrio, sim: em todas as execuções e fora do laço, com sensibilidade a duas regras. Na identidade, em parte, e a parte preservada se deve ao termo; a política é o que mais se perde. No compromisso, o escalar fica na ponta do equilíbrio, o NSGA-II na da identidade, e o híbrido reúne os dois. Então, é possível equilibrar sem destruir as identidades, desde que haja pressão explícita por identidade e uma busca que mantenha a diversidade sob avaliação ruidosa.

### 22. Conclusão: contribuições

Daí saem cinco contribuições: uma formulação não circular, que separa premissa de resposta; evidência controlada de que a identidade preservada se deve ao termo; uma falha da seleção escalar sob ruído, com um híbrido que a contorna no mesmo orçamento; a perda de identidade localizada na política, decidida pelo passo de mutação; e lições de método, como piso medido para cada métrica, resolução à altura da margem e rastreabilidade de cada número.

### 23. Conclusão: limites e próximos passos

O modelo ainda é simples: o ciclo que propus não se realiza nem no canônico, que é uma hierarquia, o que indica que faltam mecânicas, como combos e janelas de punição; e o equilíbrio foi medido contra uma política fixa, sem oponente tentando explorá-lo. Os próximos passos são calibrar o passo da política contra o ruído, políticas que dependam do estado da luta, oponentes que coevoluem e calibrar o híbrido no orçamento completo. O código é aberto e está no GitHub. Obrigado.

### 24. Obrigado (fica na tela durante as perguntas)

_Sem fala. O QR code e o resumo ficam na tela durante a arguição._

## Se o tempo apertar

Cortes prontos, do menos ao mais custoso. Cada um sai inteiro, sem quebrar a frase que fica.

1. **Slide 13**, "Uma execução do AG escalar simula 68 milhões de lutas; uma do NSGA-II, 135 milhões." (6 s).
   Os números ficam nos cartões.
2. **Slide 8**, ", no que Togelius e colegas chamam de geração de conteúdo baseada em busca" (5 s); a frase
   termina em "há duas décadas". O rodapé cita Togelius.
3. **Slide 11**, ", o joelho de uma varredura" (2 s). Se perguntarem por que λ = 1, está nas perguntas.
4. **Slide 10**, "A guarda reduz o dano em 40%, e o agarrão a rompe." (4 s). Fica escrito no slide.
5. **Slide 6**, "As defesas são números aleatórios comuns e reavaliar a solução final." (4 s). O cartão
   mostra, e o slide 9 fala dos sorteios comuns.
6. **Slide 3**, "; esse elenco espelho é, no trabalho, a solução trivial de referência" (4 s); a frase
   termina em "a escolha deixa de importar".
7. **Slide 12**, "Os elencos finais são reavaliados com mil lutas por par e lidos contra 35 modelos nulos."
   (6 s). Os números ficam no painel.
8. **Slide 18**, ", e, semente a semente, nenhum dos dois domina o outro em 18 de 20" (6 s); a frase termina
   em "em 19 de 20 sementes".
9. **Slide 14**, "É perto da simetria, mas não nela: as taxas globais ficam a 1,6 ponto de 50%, contra 0,7
   de puro ruído num elenco espelho." (10 s). Vai para as perguntas.
10. **Slide 13**, "Cada arquivo de resultado registra a configuração e resumos do código que o produziu:
    carregar um desatualizado gera aviso, e gerar outro a partir dele é recusado." (10 s). O painel
    de reprodutibilidade mostra.
11. **Slide 4**, "Os objetivos específicos seguem a ordem do trabalho: [...] e medir a identidade fora da
    busca." (12 s). Os cinco cartões ficam na tela; aponte para eles.

Não corte:

- no slide 5, "O ciclo é hipótese minha, medida só depois" e a última frase: sem elas, a aptidão parece
  codificar o ciclo;
- o slide 11, porque sem ele a identidade na aptidão parece circular;
- o slide 16, porque o controle é a evidência da QP2;
- o slide 19, porque sem ele o híbrido aparece sem motivo.

Algumas partes ficam inteiras porque os resultados as cobram:

- no slide 9, os sorteios que mudam a cada geração e o passo quatro vezes menor nos pesos, cobrados nos
  slides 19 e 17;
- no slide 7, a frase de Knowles, cobrada no 20;
- no slide 8, as duas últimas frases (a lacuna), cobradas no 22.

## Slides de reserva

Ficam depois do "Obrigado" e não contam no tempo. Numerados R1 a R13 no canto.

- **R1, ciclo:** arestas decididas e mantidas, tríades circulares, o ciclo proposto por extenso.
- **R2, equações:** as duas penalidades e as duas formulações (escalar e biobjetivo).
- **R3, perfis canônicos:** os 11 genes dos 5 arquétipos, com os genes definidores em negrito.
- **R4, validação externa:** veredito e desequilíbrio de 4 elencos em 9 condições.
- **R5, métricas por braço:** as seis métricas da família de testes, execução por execução.
- **R6, convergência:** desequilíbrio e desvio do melhor elenco por geração.
- **R7, sensibilidade:** o quanto cada gene move a taxa de vitória, contra o piso de ruído.
- **R8, lição de método:** 200 contra 1.000 lutas por par no controle λ = 0.
- **R9, modelos nulos:** canônico, espelhos e aleatórios em todas as métricas.
- **R10, comparações:** AG contra NSGA-II e híbrido, com p corrigido e Â₁₂.
- **R11, representantes da fronteira:** best_drift, joelho, ideal, scalar_optimum, best_dominance.
- **R12, parâmetros:** valor e o que sustenta cada um (medido, domínio, projeto).
- **R13, combate em detalhe:** tempo, intenção, ataque, guarda e agarrão, recarga, desfecho.

## Perguntas prováveis

Respostas com o que a monografia sustenta. Onde ela não investiga, a resposta diz isso.

**A identidade está na aptidão. O resultado não é circular?**
A aptidão contém o que cada arquétipo *é* (os perfis canônicos), que é a premissa; nunca quem deve
vencer quem, que é a resposta. Os três termos do desequilíbrio usam só a distância a 50% e não dizem
qual lado deveria ganhar. E o termo de desvio é penalidade, não restrição: ele perde boa parte das
disputas, porque o AG escalar termina com 11 das 18 asserções estruturais, contra 18 do canônico, e
perde mais da metade da concordância comportamental. A identidade *funcional*, que responde à
pergunta, é medida por métricas de comportamento que nenhum termo da aptidão vê. (Slides 9 e 11, R2.)

**Então por que as asserções sobre os genes não bastam como evidência?**
Porque são parcialmente endógenas: medem o mesmo eixo que o termo de desvio, e qualquer busca com
esse termo supera os nulos nelas. Por isso a evidência vem da Camada 3 e da concordância τ, lidas
contra o controle λ = 0, e não contra os nulos: um elenco isolado empata com o melhor nulo na Camada 3
(3 de 5) e fica um fio abaixo dele em τ (0,314 contra 0,316).

**O que são as 23 asserções e o τ?**
O validador tem 13 asserções sobre genes entre personagens (o Rushdown é o mais rápido, o Turtle tem
mais vida), 5 sobre genes de um mesmo personagem e 5 de comportamento (o Zoner luta mais longe, o
Rushdown conecta mais golpes, o Turtle escolhe mais defesa, o Combo Master atordoa mais, o Grappler
causa mais dano através da guarda). Empate conta contra. O τ é o τ-b de Kendall entre a ordem
canônica e a do elenco dos 5 personagens em cada uma das 10 métricas de comportamento, em média: 1 é
a ordem canônica, 0 é o acaso.

**Os arquétipos têm base na literatura?**
Não há uma taxonomia acadêmica consolidada: as descrições de arquétipos vêm da comunidade competitiva,
que não serve como referência formal. Por isso, o recorte de cinco é uma construção operacional do
autor, ancorada na transposição do argumento de Gingold das ações para os personagens. Os valores
canônicos são a premissa (R3), e o ciclo é uma hipótese testada depois (R1).

**O Gingold fala de personagens?**
Não. O ciclo dele é entre ações dentro da luta: golpe, defesa e o agarrão que vence a defesa. A
transposição para personagens é deste trabalho, e a monografia diz isso. Do artigo vem só o argumento
de que nenhuma escolha é imbatível se as vantagens formam um ciclo. (Slide 5.)

**Qual a diferença para o trabalho de Chen et al. (2014)?**
É o mais próximo: equilíbrio entre raças de personagens, avaliado por simulação de combates. Há três
diferenças. O combate é por turnos, sem posicionamento contínuo nem janelas de ação curtas. A
formulação é coevolução cooperativa, sem fronteira de Pareto, embora os autores reconheçam o problema
como multiobjetivo. E o equilíbrio é o único critério otimizado e medido: a identidade das raças não
entra. (Slide 8.)

**Por que NSGA-II, e não outro algoritmo multiobjetivo?**
É um dos algoritmos evolutivos multiobjetivo mais usados, e com dois objetivos a ordenação em frentes
e a aglomeração funcionam bem. O trabalho não compara algoritmos multiobjetivo entre si: o que ele
compara é somar contra comparar por dominância, com os mesmos operadores de variação e o mesmo
orçamento. A busca por diversidade (novelty search, MAP-Elites) aparece como trabalho futuro.

**Por que λ = 1?**
Saiu de uma varredura da razão λ_drift/λ_dom, em orçamento reduzido. Até 1, o desequilíbrio fica
estável (0,041 a 0,044 com λ de 0,25, 0,5 e 1) e a identidade melhora; acima, a identidade melhora
mas o desequilíbrio sobe para 0,183 (λ = 2) e 0,356 (λ = 4), com 4,2 e 7,8 hard counters por elenco. É
o joelho. Só a razão importa, porque o torneio é ordinal (slide 6).

**Identidade e equilíbrio são antagônicos, então?**
No peso adotado, não de forma mensurável: tirar o termo de identidade não melhora o equilíbrio
significativamente (0,043 contra 0,036, p de Holm 0,059). O antagonismo aparece além desse peso, na
varredura, e na fronteira do NSGA-II. A afirmação defensável é "a identidade não custou equilíbrio
mensurável", não "a identidade melhora o equilíbrio".

**Por que 150 lutas por par? Não é pouco?**
Para a busca, o desvio-padrão binomial perto de 50% é de cerca de 4 pontos, pequeno diante da
tolerância de 15 do hard counter. As lutas são semeadas por posição (números aleatórios comuns
dentro da geração), e os sorteios mudam a cada geração para a busca não se ajustar a eles. Para
*medir* o resultado, 150 é grosseiro: o desequilíbrio de um mesmo elenco varia 0,017 entre sorteios a
150 lutas e 0,006 a 1.000, e a régua grosseira ainda puxa o valor para cima. Por isso a reavaliação
usa 1.000 lutas por par. (R8.)

**Por que a convergência recusou tantos elencos?**
Das 70 vezes em que o melhor elenco pareceu equilibrado dentro do laço, 50 não sobreviveram à
reavaliação em sorteios inéditos: a busca se ajusta aos sorteios que viu. Convergir marca o primeiro
sucesso confirmado de um teste repetido a cada geração, e não um estado estável; por isso o slide 14
mostra também os 16 de 20 que *terminam* equilibrados.

**Por que o teste é pareado? Por que 20 execuções?**
A mesma semente fixa a população inicial, os sorteios dos operadores e os da avaliação nos dois
braços, então a execução i de um braço e a i do outro formam um bloco. O teste não pareado de
Mann-Whitney dá as mesmas conclusões (p brutos menores que 0,004 contra o NSGA-II). Vinte é o menor n
com pelo menos 80% de poder para um efeito grande (Â₁₂ = 0,80): 85,9%, contra 44,4% com 10.

**O AG começa com o canônico na população e o NSGA-II não. Isso não enviesa a comparação?**
No NSGA-II, o canônico tem desvio zero e ninguém o domina: ele e a vizinhança ficariam para sempre na
primeira frente, por mais desequilibrados que fossem (numa execução de teste, 40 dos 78 pontos da
fronteira tinham desequilíbrio acima de 1). No AG, o efeito foi medido com um controle sem semente: ele
só difere no desvio (0,270 contra 0,247), e não explica a diferença entre AG e NSGA-II. Os slides 9
e 12 mostram a semente e o controle, então esta pergunta é provável.

**Por que comparar com o scalar_optimum, e não com outro ponto da fronteira?**
É o ponto da fronteira que minimiza a mesma função do AG escalar, escolhido antes da bateria. Contra
o extremo de equilíbrio (best_dominance), as seis diferenças mantêm direção e significância. (R10, R11.)

**Se o NSGA-II dá a fronteira inteira, por que não basta ele?**
Nenhuma das 20 execuções termina com um elenco equilibrado: sobram 2,8 hard counters por elenco, em
média. O joelho e o ponto ideal preservam quase toda a identidade (τ de 0,70 a 0,80), mas não são
equilibrados em nenhuma execução.

**A divisão do híbrido (metade e metade) é a melhor?**
Não foi medido. O critério de escolha foi escrito antes da varredura, mas, no orçamento reduzido,
nenhuma configuração passou no filtro de equilíbrio, e a escolha caiu no desempate por simplicidade.
Nesse orçamento, inclusive, a configuração adotada preservou *menos* identidade que o AG escalar
(desvio 0,255 contra 0,234); o efeito só apareceu no orçamento da bateria. Calibrar é trabalho futuro.

**O híbrido prova a explicação dos dois estágios?**
Não; ele é consistente com ela, mas não separa os estágios. Há mais duas observações a favor: a
degradação entre o laço e a reavaliação acompanha o peso que a seleção dá ao termo ruidoso (2,33 sem o
termo de identidade, 1,80 no AG, 1,25 no NSGA-II), e a confirmação recusou 71% dos elencos que pareciam
equilibrados.

**Por que o cruzamento troca personagens inteiros?**
Para que capacidade e estratégia de um personagem sejam herdadas juntas: o Zoner do filho vem inteiro
do pai A ou do pai B, nunca com o alcance de um e os pesos do outro. É o cruzamento por blocos do
referencial, aplicado ao bloco que é coerente por dentro. O custo é que a recombinação dentro de um
personagem fica só por conta da mutação. (Slides 6 e 9.)

**O NSGA-II não faz o dobro de avaliações? A comparação é justa?**
Faz o dobro: pais e filhos são comparados no mesmo conjunto e, como os sorteios mudam a cada geração,
os pais são reavaliados (cerca de 135 milhões de lutas por execução, contra 68 milhões do AG). O
orçamento é igualado pelo número de filhos por geração, isto é, pelo número de elencos novos que cada
busca experimenta. As avaliações extras do NSGA-II medem de novo os pais no sorteio da geração e não
acrescentam busca.

**Por que a mutação dos pesos é quatro vezes menor?**
Para dar inércia à estratégia e evitar saltos de comportamento. O custo, descoberto nos resultados, é
que nesse passo cada mutação de política fica no nível do ruído. Com o mesmo passo relativo dos
atributos, os pesos movem a taxa de vitória em 12 a 17 pontos, acima do atordoamento (10,4). (R7.)

**Por que o ciclo de vantagens não aparece?**
Porque não havia ciclo a preservar: o canônico realiza só 6 das 10 arestas, e as 4 que quebra são
inversões completas, com o Rushdown vencendo todos e o Turtle perdendo para todos (uma hierarquia, 1
tríade circular de 5). Num modelo com dano fixo e sem animações nem combos, a vantagem vira taxa de
dano, o que tende a produzir hierarquias. Nos elencos do AG, 56,5% das arestas decididas seguem a
direção proposta, sem diferença do acaso (p = 0,091). Como a aptidão é cega à direção, esse é o
resultado esperado, e ele confirma que o ciclo não foi codificado na busca. (R1.)

**Os elencos evoluídos são não transitivos?**
Sim, com 3,7 tríades circulares em 5, contra 0,4 dos aleatórios. Mas o termo global favorece isso,
porque numa ordem estrita o primeiro colocado fica acima de 50%; não é evidência independente.

**A diferenciação entre personagens não mostra a homogeneização?**
Não serve como evidência: elencos sorteados são dispersos sem ter identidade, e o controle sem o termo
(1,16) fica acima do AG escalar (1,09). A homogeneização aparece na política (slide 17).

**Qual é a principal limitação do equilíbrio?**
Ele é medido contra uma política fixa: os personagens não aprendem e ninguém procura uma estratégia
que explore o elenco. Testar com oponentes que coevoluem é o próximo passo natural. Além disso, o
round-robin pesa os 10 pares igualmente, sem a escolha de personagens de um metagame real.

**Por que algoritmo genético, e não outro método?**
O simulador é estocástico e de caixa-preta, sem gradiente; um método evolutivo só precisa avaliar
candidatos, e o NSGA-II estende o mesmo esquema a dois objetivos. O trabalho não compara com outras
famílias de métodos; isso está nas limitações.

**Isso serve para um jogo real?**
Não diretamente: o combate é abstrato, são cinco arquétipos e a política é fixa. O que se transfere é
a formulação (premissa na aptidão, resposta só medida depois) e o protocolo de medição, com piso
medido, controle e validação fora do laço.

**Como garantir que os números são reprodutíveis?**
Toda execução é reprodutível pela semente, e cada arquivo de resultado registra a configuração e
resumos do código do motor e da medição que o produziram. Carregar um artefato desatualizado gera
aviso; gerar um novo a partir dele é recusado. (Slide 13.)

**De onde vem o "150 vezes mais rápido"?**
É uma medição do projeto, a compilação do laço de combate com Numba contra o mesmo laço em Python
puro, registrada na documentação do código (`docs/reference/09-reproducibility.md`). A monografia não
cita esse número; ela diz só que o laço é compilado para código de máquina.

**Por que os números são diferentes dos do artigo da Latinoware?**
O artigo foi submetido antes da versão final do sistema: lá eram 10 genes por personagem, 21 asserções
e 10 execuções; a monografia tem o gene de agarrão (11 genes), 23 asserções, 20 execuções por braço e o
híbrido. A bateria citável é a de 23/09/2026.

## Depois de importar no Google Slides

Suba `slides.pptx` no Drive e abra com o Google Slides. A conferência aqui foi feita por uma prévia
que usa as métricas reais da Open Sans e por uma renderização do PowerPoint, mas não pelo Google
Slides; vale olhar:

1. A fonte é **Open Sans** em todos os textos (é fonte do Google, deve vir sozinha).
2. Nenhum título quebra linha. Se algum quebrar, reduza para 24 pt.
3. Slide 5: os rótulos do ciclo não encostam nas setas, e as pontas das setas aparecem.
4. Slide 6: "selecionado" não encosta nas barras do gráfico.
5. Slide 7: os rótulos do diagrama (A, B, "fronteira", "menor desvio") não encostam na curva.
6. Slide 8: a tabela cabe, e os cabeçalhos ficam em até três linhas.
7. Slide 9: o rótulo "laço evolutivo: 150 gerações" cobre a linha de retorno com o fundo branco, e
   os textos dos quatro cartões cabem.
8. Slide 11: a caixa "Só medido depois" está tracejada.
9. Slide 15: "inconclusivo" cabe no cartão cinza.
10. O QR code do último slide abre `github.com/M-Gimenes/Simulation` (teste com o celular na tela).
11. Notas do orador: Ver > Mostrar notas do orador, ou no modo Apresentador.

Ajuste a saudação do slide 1 ao horário ("Bom dia" ou "Boa tarde") e ponha a data da defesa na
capa, que hoje mostra só "Cachoeiro de Itapemirim, 2026".
