# Roteiro da apresentação à banca (TCC)

Primeira apresentação à banca (Prof. Dr. Flávio Izo e Prof. Dr. Rafael Silva Guimarães; orientador
Prof. Dr. Everson Scherrer Borges), em 21 de outubro de 2026: **10 minutos de fala e 10 de perguntas**.
A banca já recebeu a monografia de 100 páginas, então a fala conta a história e as decisões, e o
detalhe fica nos slides de reserva.

Todo número, na fala e nos slides, vem da monografia entregue (`overleaf/TCC/valores.tex` e os
capítulos de resultados e discussão), isto é, da bateria de 23/09/2026. Nada foi re-rodado: as
figuras dos slides foram redesenhadas, em tamanho de projeção, a partir dos mesmos artefatos de
`results/`.

A mesma fala está nas notas do orador de cada slide em `slides.pptx`.

## A história em uma frase por bloco

1. **Problema (slides 2–3).** Equilibrar tem dois erros: um personagem dominar, ou todos ficarem
   iguais. A pergunta é se um AG equilibra sem apagar as identidades, dividida em QP1, QP2 e QP3.
2. **Método (4–7).** Um simulador em que cada gene pesa; uma aptidão que contém o que cada arquétipo
   *é*, nunca quem deve *vencer*; o ciclo do AG, em que o desequilíbrio é avaliado com ruído; e o
   NSGA-II, que troca a soma pela dominância de Pareto, no mesmo orçamento e ao lado de um controle
   sem identidade.
3. **Resultados (8–14).** O AG equilibra (QP1) e replica fora do laço. A identidade que sobra se deve
   ao termo, mas a política se perde (QP2). Nenhum algoritmo domina o outro, mas o AG escalar fica
   longe do próprio ótimo; o motivo são dois estágios da seleção escalar, e o híbrido, que protege a
   identidade no início, recupera boa parte dela sem custo de equilíbrio (QP3).
4. **Conclusão (15–16).** Sim, com pressão explícita por identidade e uma busca que mantenha a
   diversidade sob ruído. Limites e próximos passos saem dos próprios achados.

Os slides 6 e 7 plantam o que os resultados cobram: "o desequilíbrio tem ruído" volta no 13 (o
segundo estágio), "passo 4× menor" volta no 11 (a política), e "o elenco de menor desvio nunca é
descartado" volta no 14 (o híbrido).

## Código de cores dos slides

Para se guiar sem ler: **azul** é o AG escalar, **laranja** o NSGA-II, **verde-água** o híbrido e
**cinza-escuro** o controle sem o termo de identidade (λ = 0), as mesmas cores das figuras da
monografia. **Vermelho** é desequilíbrio (e "frágil"), **roxo** é desvio de identidade. Nos títulos,
**QP1/QP2/QP3** em verde dizem a qual questão o slide responde, e o cabeçalho marca a seção atual.

## Tempo por slide

São 1593 palavras. A 150 palavras por minuto, ritmo calmo de apresentação, a fala leva
10:37; a 165, ritmo da Latinoware, 9:39. Os slides do ciclo do AG e do NSGA-II acrescentaram
cerca de 55 segundos à versão apresentada em 21/10. Ensaie com cronômetro: se passar de 9:30, use
os cortes abaixo, que somam cerca de 53 segundos.

| # | Slide | Palavras | a 150 ppm | a 165 ppm |
|---|---|---|---|---|
| 1 | Capa | 49 | 0:20 | 0:18 |
| 2 | Problema: duas formas de errar | 83 | 0:33 | 0:30 |
| 3 | Problema: o elenco e a pergunta | 110 | 0:44 | 0:40 |
| 4 | Método: o simulador | 117 | 0:47 | 0:43 |
| 5 | Método: a aptidão (premissa, nunca resposta) | 128 | 0:51 | 0:47 |
| 6 | Método: o ciclo do AG | 112 | 0:45 | 0:41 |
| 7 | Método: o NSGA-II e o protocolo | 135 | 0:54 | 0:49 |
| 8 | QP1: da hierarquia ao equilíbrio | 86 | 0:34 | 0:31 |
| 9 | QP1: fora do laço | 97 | 0:39 | 0:35 |
| 10 | QP2: o controle sem identidade | 103 | 0:41 | 0:37 |
| 11 | QP2: a política | 96 | 0:38 | 0:35 |
| 12 | QP3: a fronteira | 98 | 0:39 | 0:36 |
| 13 | QP3: por quê? Dois estágios | 101 | 0:40 | 0:37 |
| 14 | QP3: o híbrido | 92 | 0:37 | 0:33 |
| 15 | Conclusão: as três respostas | 93 | 0:37 | 0:34 |
| 16 | Limites e próximos passos | 93 | 0:37 | 0:34 |
| 17 | Obrigado (fica na tela durante as perguntas) | 0 | 0:00 | 0:00 |
| | **Total** | **1593** | **10:37** | **9:39** |

## Fala

### 1. Capa

Boa tarde, professores. Meu nome é Matheus Gimenes, e vou apresentar o meu trabalho de conclusão de curso, orientado pelo professor Everson. O trabalho trata do balanceamento de personagens em jogos de luta e pergunta se é possível equilibrar um elenco sem apagar o que torna cada personagem único.

### 2. Problema: duas formas de errar

Existem duas formas de errar no balanceamento de um jogo competitivo. A mais conhecida é deixar um personagem forte demais, e então todos passam a escolhê-lo. A segunda costuma aparecer justamente ao corrigir a primeira: os números são ajustados até que ninguém domine, mas, no caminho, os personagens ficam parecidos. No limite, dar a todos os mesmos atributos produz um equilíbrio perfeito, e a escolha do personagem deixa de importar. O desafio deste trabalho fica entre os dois erros: equilibrar preservando a diferença.

### 3. Problema: o elenco e a pergunta

Usamos os jogos de luta, em que os estilos de personagem são bem definidos. O elenco tem cinco arquétipos clássicos do gênero: o Rushdown, da pressão; o Zoner, do controle de distância; o Grappler, do agarrão; o Combo Master, aqui representado pelo atordoamento; e o Turtle, da defesa. Os valores de cada arquétipo foram definidos por mim e são a premissa do trabalho. O elenco é desequilibrado de propósito, para que haja o que equilibrar. A pergunta de pesquisa é se um algoritmo genético consegue equilibrar esses cinco arquétipos sem destruir as suas identidades funcionais, e ela se divide em três questões: equilíbrio, identidade e o compromisso entre os dois.

### 4. Método: o simulador

Para avaliar um elenco, construímos um simulador de combate. Cada personagem tem onze genes: oito atributos, que dizem o que ele pode fazer, e três pesos, que dizem o que ele tende a fazer. A decisão central do modelo é separar dois canais. A postura, entre avançar, recuar e guardar, é sorteada com probabilidade proporcional aos pesos, e esse sorteio é a única fonte de aleatoriedade da luta. O ataque é uma regra: sai sempre que o oponente está ao alcance e o personagem não está defendendo. É isso que faz do controle de distância uma estratégia. No algoritmo genético, o indivíduo é o elenco inteiro, com 55 genes, avaliado em dez confrontos de 150 lutas cada.

### 5. Método: a aptidão (premissa, nunca resposta)

Os trabalhos que aplicam busca ao balanceamento não medem se a identidade sobrevive. Aqui, ela entra na aptidão com uma regra: a aptidão pode conter o que cada arquétipo é, que é a premissa, mas nunca quem deve vencer quem, que é a resposta procurada. O desequilíbrio mede o quanto cada personagem se afasta de 50% de vitórias no total, sem exigir 50% em cada confronto, e barra counters acima de 65% e lutas decididas por massacre, sempre pela distância a 50%, nunca pela direção. O desvio mede a distância de cada personagem ao seu perfil canônico, com peso triplo nos genes que definem o arquétipo. Já a identidade funcional, se o personagem ainda joga como ele mesmo, é medida depois, por métricas que a busca não vê.

### 6. Método: o ciclo do AG

Com a aptidão definida, o algoritmo genético repete um ciclo. A população tem 300 elencos: na geração zero, o canônico e 299 sorteados. Cada elenco é avaliado no round-robin. O desvio sai direto dos genes, mas o desequilíbrio sai das lutas, e os sorteios mudam a cada geração, para que a busca não se ajuste a eles. Por isso, o desequilíbrio é sempre uma estimativa com ruído. Os 10% melhores passam direto, e cada pai é o melhor de um torneio de três. O cruzamento passa cada personagem inteiro de um dos pais, e a mutação perturba alguns genes, com passo quatro vezes menor nos pesos. Isso se repete por 150 gerações.

### 7. Método: o NSGA-II e o protocolo

O NSGA-II usa o mesmo ciclo, com outra seleção. Em vez de somar os dois termos, ele compara por dominância: um elenco domina outro se não é pior em nenhum dos dois e é melhor em pelo menos um. Os que ninguém domina formam a fronteira, e, entre eles, a seleção prefere os mais isolados, para espalhá-la. Uma consequência importa adiante: o elenco de menor desvio nunca é dominado, então nunca é descartado. A saída é a fronteira; para comparar, usamos o ponto dela que minimiza a mesma soma do escalar. Completam o desenho o híbrido, com o NSGA-II na primeira metade e o escalar na segunda, e o controle sem o termo de identidade. Cada braço rodou vinte vezes, com as mesmas sementes, e os elencos finais são reavaliados com mil lutas por par.

### 8. QP1: da hierarquia ao equilíbrio

Começo pela primeira questão. À esquerda está o elenco original, que chamamos de canônico. Ele é uma hierarquia: o Rushdown vence praticamente todas as lutas, o Turtle não vence nenhuma, e nove dos dez confrontos são decididos em mais de 99% das lutas. À direita está a média das vinte execuções do algoritmo escalar, com todos os confrontos entre 46% e 54%. O algoritmo convergiu em todas as execuções, em média na geração 31, e dezesseis delas terminaram com o elenco equilibrado, perto da simetria perfeita.

### 9. QP1: fora do laço

Equilibrar dentro do laço não basta, porque a busca pode se ajustar aos sorteios que viu. Na validação externa, o elenco evoluído foi testado com sorteios inéditos e cinco mil lutas por par, e foi o único dos quatro elencos testados que replicou o equilíbrio. Depois, alteramos uma regra do combate de cada vez, regras que a busca nunca viu. O equilíbrio resistiu a quatro das oito mudanças, ficou inconclusivo em duas e quebrou em duas: no campo menor e na persistência maior da intenção. É um equilíbrio real, mas ajustado às regras em que foi encontrado.

### 10. QP2: o controle sem identidade

Na segunda questão, a evidência decisiva é o controle. Sem o termo de identidade, o mesmo algoritmo, com o mesmo orçamento, perde a identidade nas quatro métricas, com efeito grande, e fica no nível de elencos sorteados ao acaso. A concordância de comportamento, que vale 1 no canônico, fica em 0,28 com o termo e praticamente em zero sem ele. No equilíbrio, os dois braços não se separam depois da correção de Holm. A identidade que sobrevive se deve, portanto, ao termo, e ele não custou equilíbrio mensurável. Mas essa identidade é parcial: o algoritmo escalar mantém três das cinco asserções de comportamento.

### 11. QP2: a política

O que mais se perde é a política, os pesos de comportamento. O Rushdown canônico avança em 86% das intenções; no algoritmo escalar, em 39%, e os cinco personagens convergem para uma política parecida. A política pesa no combate: com o mesmo passo de mutação dos atributos, os pesos mudam a taxa de vitória em 12 a 17 pontos percentuais. O problema é que a mutação dos pesos é quatro vezes menor, e, nesse passo, o efeito de cada mutação fica no nível do ruído da avaliação. Na prática, a busca quase não enxerga a política.

### 12. QP3: a fronteira

Na terceira questão, cada linha cinza é a fronteira de uma execução do NSGA-II, e os pontos azuis são o algoritmo escalar. O canto inferior esquerdo está vazio: para ganhar de um lado, perde-se do outro. O NSGA-II preserva mais identidade, mas deixa quase três confrontos desequilibrados por elenco e não termina equilibrado em nenhuma execução. O escalar fica além da ponta de equilíbrio da fronteira, pagando em desvio, e nenhum dos dois domina o outro. Mas, na própria soma que o escalar otimiza, a fronteira tem um ponto melhor que o dele em todas as vinte sementes.

### 13. QP3: por quê? Dois estágios

Por que o escalar não chega ao próprio ótimo? A explicação tem dois estágios, que esta execução mostra. No início, as diferenças de equilíbrio entre elencos são grandes, e a soma privilegia esse termo: o canônico sai da população na terceira geração, e, na vigésima, o elenco mais fiel que ainda resta já tem desvio 0,24. Depois da convergência, o desvio é calculado de forma exata, mas o desequilíbrio é estimado por sorteio, e o ruído dele é cerca de sessenta vezes o ganho de identidade por geração. A seleção passa a premiar sorte, e a identidade perdida quase não volta.

### 14. QP3: o híbrido

Se essa explicação está certa, proteger a identidade no início da busca deveria ajudar, e é isso que o híbrido faz: na fase de Pareto, o elenco de menor desvio nunca é descartado. Com o mesmo orçamento, o híbrido chega perto da identidade do NSGA-II, com a concordância quase dobrando, de 0,28 para 0,52, e mantém o equilíbrio do escalar, com dezesseis elencos equilibrados em vinte. O preço é a velocidade: ele converge na geração 98, contra 31. Parte da perda de identidade vem, portanto, da seleção escalar, e não do problema.

### 15. Conclusão: as três respostas

Voltando às três questões. No equilíbrio, a resposta é sim: em todas as execuções e também fora do laço, com sensibilidade a algumas regras. Na identidade, a resposta é parcial, e a parte preservada se deve ao termo de identidade, que não custou equilíbrio mensurável. No compromisso, o escalar fica na ponta do equilíbrio, o NSGA-II na da identidade, e o híbrido reúne os dois. Então, é possível equilibrar sem destruir as identidades, desde que haja pressão explícita por identidade e uma busca capaz de manter a diversidade de identidade sob avaliação ruidosa.

### 16. Limites e próximos passos

O modelo de combate ainda é simples. O ciclo de vantagens que propus para os arquétipos não se realiza nem no elenco canônico, que é uma hierarquia, o que indica que faltam mecânicas, como combos e janelas de punição. E o equilíbrio foi medido contra uma política fixa, sem nenhum oponente tentando explorá-lo. Os próximos passos são calibrar o passo de mutação da política contra o ruído, usar políticas que dependam do estado da luta e testar o equilíbrio contra oponentes que se adaptam. O código é aberto e está no GitHub. Obrigado.

### 17. Obrigado (fica na tela durante as perguntas)

_Sem fala. O QR code e o resumo ficam na tela durante a arguição._

## Se o tempo apertar

Cortes prontos, do menos ao mais custoso. Cada um sai inteiro, sem quebrar a frase seguinte.

1. **Slide 4**, "É isso que faz do controle de distância uma estratégia." (4 s). Fica para as
   perguntas: num modelo de canal único, o personagem de longo alcance perdia 100% das lutas.
2. **Slide 4**, "avaliado em dez confrontos de 150 lutas cada" (3 s); a frase termina em "com 55
   genes". O slide 6 repete a avaliação.
3. **Slide 13**, "que esta execução mostra" (2 s). Basta apontar o gráfico.
4. **Slide 12**, "O canto inferior esquerdo está vazio: para ganhar de um lado, perde-se do outro."
   (6 s). O slide 7 já mostrou que abaixo da fronteira não há ninguém.
5. **Slide 7**, a frase do híbrido e do controle ("Completam o desenho...") (10 s). Os dois cartões
   ficam na tela, o híbrido é explicado no slide 14 e o controle no 10.
6. **Slide 7**, a última frase ("Cada braço rodou vinte vezes...") (8 s). O rodapé mostra os números.
7. **Slide 6**, "para que a busca não se ajuste a eles" (4 s); a frase termina em "a cada geração".
   Se perguntarem por que os sorteios mudam, é a resposta.
8. **Slide 9**, "regras que a busca nunca viu" e a última frase (8 s). O resumo "4 robustas · 2
   inconclusivas · 2 frágeis" fica na tela.
9. **Slide 2**, "No limite, dar a todos os mesmos atributos..." (8 s). O cartão da direita mostra a
   solução trivial; a frase é a mais forte do slide, por isso fica por último.

Não corte o slide 5 (sem ele, a identidade na aptidão parece circular), o 10 (o controle é a
evidência da QP2) nem o 13 (sem ele, o híbrido aparece sem motivo). Os slides 6 e 7 também ficam
inteiros nas partes que os resultados cobram: o ruído do desequilíbrio e o passo 4× menor (slide 6) e
"o elenco de menor desvio nunca é descartado" (slide 7). Pelo mesmo motivo, a frase do passo de
mutação no slide 11 ("O problema é que...") saiu da lista de cortes: é ela que fecha o "4× menor" do
slide 6.

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
pergunta, é medida por métricas de comportamento que nenhum termo da aptidão vê. (Slide 5, R2.)

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

**Por que λ = 1?**
Saiu de uma varredura da razão λ_drift/λ_dom, em orçamento reduzido. Até 1, o desequilíbrio fica
estável (0,041 a 0,044 com λ de 0,25, 0,5 e 1) e a identidade melhora; acima, a identidade melhora
mas o desequilíbrio sobe para 0,183 (λ = 2) e 0,356 (λ = 4), com 4,2 e 7,8 hard counters por elenco. É
o joelho. Só a razão importa, porque o torneio é ordinal.

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
sucesso confirmado de um teste repetido a cada geração, e não um estado estável; por isso o slide 8
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
só difere no desvio (0,270 contra 0,247), e não explica a diferença entre AG e NSGA-II. Com o
slide 6 mostrando o canônico na geração 0, esta pergunta ficou mais provável.

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
do pai A ou do pai B, nunca com o alcance de um e os pesos do outro. O custo é que a recombinação
dentro de um personagem fica só por conta da mutação. (Slide 6.)

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
(1,16) fica acima do AG escalar (1,09). A homogeneização aparece na política (slide 11).

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
aviso; gerar um novo a partir dele é recusado.

**Por que os números são diferentes dos do artigo da Latinoware?**
O artigo foi submetido antes da versão final do sistema: lá eram 10 genes por personagem, 21 asserções
e 10 execuções; a monografia tem o gene de agarrão (11 genes), 23 asserções, 20 execuções por braço e o
híbrido. A bateria citável é a de 23/09/2026.

## Depois de importar no Google Slides

Suba `slides.pptx` no Drive e abra com o Google Slides. A conferência aqui foi feita por uma prévia
que usa as métricas reais da Open Sans, mas não pelo Google Slides; vale olhar:

1. A fonte é **Open Sans** em todos os textos (é fonte do Google, deve vir sozinha).
2. Nenhum título quebra linha. Se algum quebrar, reduza para 24 pt.
3. Slide 6: "sorteios novos a cada geração: o desequilíbrio tem ruído" quebra em duas linhas sem
   encostar na linha de cima, e o círculo "150 gerações" não cobre texto dos cartões.
4. Slide 7: os rótulos do diagrama (A, B, "fronteira", "menor desvio") não encostam na curva, e o
   rodapé cabe em uma linha.
5. Slide 9: "inconclusivo" cabe no cartão cinza.
6. Slide 5: a caixa "Só medido depois" está tracejada.
7. O QR code do último slide abre `github.com/M-Gimenes/Simulation` (teste com o celular na tela).
8. Notas do orador: Ver > Mostrar notas do orador, ou no modo Apresentador.

Ajuste a saudação do slide 1 ao horário ("Bom dia" ou "Boa tarde").
