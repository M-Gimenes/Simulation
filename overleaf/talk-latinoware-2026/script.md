# Roteiro da apresentação: Latinoware 2026 (Latin.Science)

Fala da apresentação do artigo "Balanceamento competitivo com preservação de identidade: Algoritmos
Genéticos e NSGA-II em arquétipos de jogos de luta" (`overleaf/artigo-latinware-2026/`). O limite da
sessão é de 5 minutos, com perguntas à parte.

A fala conta a história do trabalho, mas cada etapa carrega uma decisão técnica com o seu motivo: como
a luta é simulada e por que ela se repete 150 vezes; por que o indivíduo é o elenco inteiro; como o
desbalanço é calculado e por que ele não exige 50% em cada confronto; por que não somar os objetivos;
e como o resultado foi validado. O registro é formal e leve, sem gíria.

Todo número, na fala e nos slides, vem do artigo submetido (`values.tex` e `main.tex`): 10 genes por
personagem, população de 300 elencos, até 150 gerações, validador de 21 asserções, 150 lutas por
confronto, 10 sementes. O sistema mudou depois da submissão (a bateria atual do TCC tem 23 asserções)
e nada do estado atual entra aqui.

A mesma fala está nas notas do orador de cada slide em `slides.pptx`.

## Tempo por slide

São 805 palavras. Uma leitura rápida de uma versão anterior (661 palavras) levou 3:30, ou cerca de
189 palavras por minuto; nesse ritmo, esta versão leva 4:16. Com slides, pausas e o nervosismo do dia, o
ritmo costuma cair; a 165 palavras por minuto, ela leva 4:53. Ensaie com cronômetro: se passar de
4:40, use os cortes abaixo.

| # | Slide | Palavras | a 189 ppm | a 165 ppm |
|---|---|---|---|---|
| 1 | Capa | 34 | 0:11 | 0:12 |
| 2 | Problema: duas formas de errar no balanceamento | 79 | 0:25 | 0:29 |
| 3 | Problema: elenco e pergunta | 61 | 0:19 | 0:22 |
| 4 | Método: a luta simulada | 68 | 0:22 | 0:25 |
| 5 | Método: o algoritmo genético | 63 | 0:20 | 0:23 |
| 6 | Método: os dois objetivos | 130 | 0:41 | 0:47 |
| 7 | Resultados: antes e depois | 89 | 0:28 | 0:32 |
| 8 | Resultados: somar os objetivos | 95 | 0:30 | 0:35 |
| 9 | Resultados: fronteira e validação | 108 | 0:34 | 0:39 |
| 10 | Conclusão | 78 | 0:25 | 0:28 |
| | **Total** | **805** | **4:16** | **4:53** |

## Fala

### 1. Capa

Olá a todos. Meu nome é Matheus, sou estudante de Sistemas de Informação no Ifes, campus Cachoeiro de
Itapemirim. Vou apresentar um trabalho sobre um problema que todo jogo competitivo enfrenta a cada
atualização.

### 2. Problema: duas formas de errar no balanceamento

Existem duas formas de errar no balanceamento de um jogo competitivo. A mais conhecida é deixar um
personagem forte demais: todos passam a escolhê-lo. A outra é mais sutil e costuma aparecer justamente
ao corrigir a primeira. Os números são ajustados até que ninguém domine, mas, no caminho, os
personagens ficam parecidos e perdem o que os tornava únicos. O jogo fica equilibrado, mas a escolha
do personagem deixa de importar. O desafio, portanto, é equilibrar preservando a diferença.

### 3. Problema: elenco e pergunta

Para estudar esse problema, escolhemos os jogos de luta, em que o confronto é um contra um e cada
estilo é bem definido. Montamos um elenco com cinco estilos clássicos do gênero, que se enfrentam como
em pedra, papel e tesoura. A pergunta da pesquisa é: um algoritmo genético consegue equilibrar esses
cinco estilos sem destruir a identidade de cada um?

### 4. Método: a luta simulada

Para avaliar um elenco, construímos um simulador de combate. A luta acontece em um campo de uma
dimensão. Fora do alcance, o personagem avança; ao alcance, ele sorteia uma intenção, avançar, recuar
ou defender, com probabilidade proporcional aos seus pesos de comportamento. Esse sorteio é a única
fonte de aleatoriedade da luta. Por isso, cada confronto é repetido cento e cinquenta vezes, para
estimar a taxa de vitória.

### 5. Método: o algoritmo genético

No algoritmo genético, cada indivíduo é um elenco inteiro, e não um personagem, porque o equilíbrio é
uma propriedade do conjunto. São cinco personagens com dez genes cada, entre atributos de combate e
pesos de comportamento. A população tem trezentos elencos. A cada geração, eles são avaliados no
simulador, os melhores são selecionados e cruzados, trocando personagens inteiros entre si, e sofrem
mutações.

### 6. Método: os dois objetivos

A maior parte dos trabalhos de balanceamento por busca otimiza apenas o equilíbrio. Aqui, a identidade
é um segundo objetivo, explícito: o desvio, a distância de cada personagem ao seu perfil original. O
equilíbrio é medido pelo desbalanço, cujo termo principal é o quanto cada personagem se afasta de
cinquenta por cento de vitórias no total. Ele não exige cinquenta por cento em cada confronto, de
propósito: um personagem pode vencer dois adversários e perder para dois, que é o espaço do pedra,
papel e tesoura. Dois termos secundários barram confrontos esmagadores e lutas decididas por margens
extremas.

Nenhum desses termos diz quem deveria vencer quem; isso só é medido depois, fora da busca. Se a
identidade fosse uma regra, sobreviveria por obrigação. Medida por fora, sua preservação vira
resultado.

### 7. Resultados: antes e depois

O ponto de partida é o elenco original, que chamamos de canônico. Ele passa nos vinte e um testes que
escrevemos para verificar a identidade dos personagens, como o rushdown ser o mais rápido. Mas nenhum
dos dez confrontos é equilibrado: um personagem vence todas as lutas, e outro não vence nenhuma.

A primeira abordagem foi um algoritmo genético que soma os dois objetivos. Ele equilibra todos os dez
confrontos. Porém, restam apenas sete dos vinte e um testes. Ou seja, caiu exatamente no problema que
descrevemos no início.

### 8. Resultados: somar os objetivos

Por que isso aconteceu? Porque somar os objetivos já é uma escolha. Com pesos iguais, o algoritmo
decide sozinho quanto de identidade vale um pouco mais de equilíbrio, e entrega um único elenco. Por
isso usamos também o NSGA-II, um algoritmo multiobjetivo que não faz essa soma. Ele só descarta um
elenco se existir outro melhor nos dois objetivos ao mesmo tempo. Internamente, ordena a população em
frentes de não dominância e, dentro de cada frente, prefere os elencos mais isolados, para que a
fronteira fique bem distribuída. O resultado é a fronteira de Pareto.

### 9. Resultados: fronteira e validação

Cada ponto deste gráfico é um elenco. Para a esquerda, mais equilíbrio; para baixo, mais identidade. O
canto inferior esquerdo está vazio: para ganhar de um lado, é preciso perder do outro. No joelho da
curva, o ponto em que ela muda de inclinação, o desbalanço já caiu três quartos do caminho, enquanto
vinte dos vinte e um testes continuam valendo.

Como o algoritmo é estocástico, uma execução é só uma amostra. Repetimos a busca dez vezes, e cada
personagem termina equilibrado em nove ou dez delas. E, testado em sorteios de luta nunca vistos, o
elenco mais equilibrado mantém nove dos dez confrontos equilibrados: não é sobreajuste.

### 10. Conclusão

O modelo ainda é simplificado, e o próximo passo é aperfeiçoar a modelagem do ambiente de combate,
incluindo mais variáveis no sistema, como os tempos de início e de recuperação dos golpes. O código é
aberto, segue em desenvolvimento e está disponível no GitHub, pelo QR code, para quem quiser testá-lo.

Para concluir: a resposta, ainda preliminar, é sim. É possível equilibrar sem apagar as identidades,
mas não sem custo, e esse custo agora pode ser medido. Obrigado.

### 11. Dúvidas?

Slide de perguntas, sem fala. O QR code do repositório fica na tela o tempo todo.

## Se o tempo apertar

Os acréscimos técnicos foram escritos como blocos que saem inteiros, sem quebrar a frase seguinte.
Cortes prontos, do menos ao mais custoso:

1. **Slide 8, o funcionamento interno do NSGA-II** ("Internamente, ordena a população... bem
   distribuída."): 9 s. Fica nas perguntas.
2. **Slide 2, a penúltima frase** ("O jogo fica equilibrado, mas a escolha do personagem deixa de
   importar."): 4 s. O cartão da direita diz isso.
3. **Slide 9, a primeira metade da validação** ("Repetimos a busca dez vezes, e cada personagem termina
   equilibrado em nove ou dez delas."): 5 s. Emende "Como o algoritmo é estocástico, uma execução é só
   uma amostra. Testado em sorteios de luta nunca vistos...".
4. **Slide 9, a validação inteira** (o segundo parágrafo): 17 s. A linha "Validado em 10 execuções e em
   sorteios novos" fica na tela, e a reserva de robustez responde se perguntarem.

Não corte o slide 6 nem o slide 8 inteiros. São as duas decisões técnicas do trabalho: sem a primeira,
os resultados parecem circulares; sem a segunda, a fronteira aparece sem motivo.

## Slides de reserva

Ficam depois do "Dúvidas?" e não contam no tempo. Use só se perguntarem.

- **Slide 12, robustez:** 10 execuções, 10 sementes novas e o ciclo de vantagens.
- **Slide 13, limites:** modelo simplificado, cinco arquétipos, sem matchmaking; calibração,
  coevolução e quality-diversity como próximos passos.
- **Slide 14, método:** os dois algoritmos lado a lado e o orçamento (300 elencos, 150 gerações).
- **Slide 15, Tabela I:** os quatro pontos do compromisso e as seis métricas, como no artigo.
- **Slide 16, desbalanço:** a equação completa e o que cada termo barra.
- **Slide 17, identidade:** a equação do desvio e os instrumentos medidos por fora.

## Perguntas prováveis

Respostas com o que o artigo sustenta. Onde o artigo não investiga, a resposta diz isso.

**Por que jogo de luta?**
Porque é o caso mais limpo do problema: um contra um, sem composição de time, itens nem mapa, e com
estilos de personagem bem definidos. Dá para simular milhares de lutas e medir quem vence quem. Em
jogos de time o mesmo raciocínio vale, mas o modelo teria que ser muito maior.

**Por que algoritmo genético, e não outro método?**
Porque o simulador funciona como uma caixa-preta: é estocástico e não tem derivada, então métodos
baseados em gradiente não se aplicam diretamente. Um método evolutivo só precisa avaliar candidatos,
e o NSGA-II estende o mesmo esquema para dois objetivos sem precisar de pesos. O artigo não compara
com outras famílias de métodos; isso fica como trabalho futuro.

**Por que sortear a intenção, em vez de uma regra fixa?**
Porque o sorteio faz os pesos de comportamento agirem de forma contínua: mudar um pouco o peso muda um
pouco a frequência da ação. Com uma regra fixa, o efeito seria em degraus, e o algoritmo não teria um
gradiente sobre esses genes. A intenção sorteada é mantida por dez sub-ticks, para simular
comprometimento. Esse sorteio é a única fonte de aleatoriedade: o dano é fixo, reduzido em 40% se o
alvo defende.

**Por que 150 lutas por confronto?**
Porque a luta é estocástica e uma luta isolada não estima a taxa de vitória. Cada elenco é avaliado
com 1.500 lutas (10 confrontos × 150). O artigo não apresenta um estudo de sensibilidade desse número.

**Como funcionam o cruzamento e a mutação?**
O cruzamento é por bloco de personagem: o filho recebe cada um dos cinco personagens inteiro, de um
pai ou do outro, em vez de misturar genes de arquétipos diferentes. A mutação é gaussiana, com desvio
quatro vezes menor nos pesos de comportamento do que nos atributos. Há também elitismo. Os dois
algoritmos usam os mesmos operadores.

**Por que o indivíduo é o elenco e não o personagem?**
Porque o que se mede é o elenco: equilíbrio só existe entre personagens, nos confrontos de todos
contra todos. Avaliar um personagem isolado não diria se o conjunto está equilibrado.

**Como exatamente o desbalanço é calculado?**
desbalanço = 1,0 × global + 0,5 × counter + 0,5 × decisividade. O termo global é |WR − 0,5| / 0,5
por personagem, sobre a taxa de vitória agregada contra os quatro oponentes. O counter penaliza o
excesso de |WR do par − 0,5| acima de 0,15. A decisividade penaliza lutas em que o vencedor não
termina com 20% a 40% de vida, o que barra massacres alternados com taxa perto de 50%. Os três usam
distâncias a 0,5 e nunca dizem qual arquétipo deveria vencer. (Slide 16.)

**E o desvio?**
É a distância euclidiana normalizada de cada personagem ao seu perfil canônico, sobre os 10 genes,
em média entre os cinco. Os atributos são normalizados pelo limite superior do gene; os pesos já estão
entre 0 e 1. (Slide 17.)

**O que é a distância de aglomeração?**
No NSGA-II, dentro de uma mesma frente, os elencos são comparados pela distância aos vizinhos no
espaço dos objetivos. Os mais isolados são preferidos, o que mantém a fronteira espalhada em vez de
concentrada num trecho.

**Com outros pesos, o AG escalar não chegaria ao joelho?**
Em princípio, outros pesos levariam a outros pontos. Mas seria preciso escolher os pesos antes, sem
saber o custo de cada um, e rodar uma vez para cada escolha. O NSGA-II entrega o conjunto inteiro numa
execução, e a escolha fica para depois, com os números na mão. O artigo usa pesos iguais e não testa
outras combinações.

**Se o desvio está na função objetivo, a identidade não está sendo imposta?**
O desvio é uma penalidade suave, não uma restrição: o algoritmo pode se afastar do canônico, e se
afasta (o AG escalar termina com desvio 0,26 e 7 de 21 asserções). O que nunca entra em penalidade
alguma é quem vence quem. Validador, diferenciação, perfil e ciclo são medidos depois, fora da busca.

**De onde vêm os cinco arquétipos e o ciclo de vantagens?**
São uma construção dos autores. A literatura fundamenta a estrutura não transitiva, do tipo
pedra-papel-tesoura, de forma geral, mas não define um conjunto específico nem um ciclo fechado. O
elenco e o ciclo são tratados como hipótese, não como lei a reproduzir.

**O que são os 21 testes?**
Asserções de ranqueamento: 17 sobre os genes (o rushdown com a maior velocidade, o turtle com a maior
vida) e 4 sobre o jogo efetivo. No canônico, o rushdown avança em 73% das ações, o turtle defende em
46% e o zoner recua em 44%.

**Por que o ciclo não aparece nem no elenco canônico?**
No modelo, só 5 das 10 relações se sustentam no canônico. O artigo lê isso como indício de que a
estrutura não transitiva dos jogos reais depende de mecânicas que o modelo deixa de fora: frames de
inicialização e recuperação, mix-ups e oclusão.

**Por que o AG escalar chega a mais equilíbrio do que o extremo da fronteira do NSGA-II?**
A Tabela I mostra a diferença (desbalanço 0,01 contra 0,11, com desvio parecido), e o artigo não a
investiga. O que ele reporta é que zerar todos os counters de par é sensível à semente no NSGA-II:
sobram 2,1 ± 1,1 pares por execução.

**O resultado depende da semente?**
Em 10 execuções independentes do NSGA-II, o desbalanço fica em 0,19 ± 0,04 e o desvio em 0,23 ± 0,03.
O equilíbrio global é estável: cada personagem termina equilibrado em 90 a 100% das execuções. E, sob
10 sementes novas, 9 dos 10 confrontos da solução mais equilibrada seguem equilibrados. (Slide 12.)

**O que é o joelho da fronteira? Ele é equilibrado?**
É o ponto intermediário do compromisso. Na execução do artigo, ele leva o desbalanço de 1,42 para
0,34 e preserva 20 das 21 asserções. Mas só 2 dos 10 pares caem na banda de 40% a 60%, porque o ganho
ali é de equilíbrio global (cada personagem perto de 50% no total), não par a par. Por isso a fala diz
"o desbalanço caiu três quartos do caminho", e não "quase equilibrado".

**Isso serve para um jogo real?**
Ainda não diretamente. O modelo é uma simplificação, o estudo usa cinco arquétipos contra dez ou mais
dos jogos reais, e o todos contra todos supõe que todos são jogados na mesma proporção. É um trabalho
em andamento.

## Depois de importar no Google Slides

Suba `slides.pptx` no Drive e abra com o Google Slides. Vale conferir cinco coisas, porque a conversão
foi verificada aqui só por uma prévia aproximada (sem a fonte Montserrat instalada):

1. O logo do Latin.Science aparece no cabeçalho de todos os slides e na capa.
2. A fonte é Montserrat em todos os textos (se algum cair em Arial, a largura muda).
3. Nenhum texto quebra linha ou encosta na borda do próprio cartão, em especial os três termos do
   desbalanço no slide 6, a legenda dos genes no slide 5, a regra do NSGA-II no slide 8 e o subtítulo
   do slide 10.
4. No slide 6, a caixa "medido só depois" está tracejada.
5. O QR code dos slides 10 e 11 abre `github.com/M-Gimenes/Simulation` (teste com o celular na tela
   do computador).

## Tamanho de fonte

O data-show da sala não está bem posicionado, então nenhum texto dos slides 1 a 11 fica abaixo de
28 pt (o slide tem 20 polegadas de largura, então 28 pt aqui equivalem a uns 19 pt num slide padrão).
As exceções são da moldura do evento ("Realização:" e o nome do congresso na capa) e os números dos
eixos dentro da figura da fronteira, que é uma imagem. As reservas, depois do "Dúvidas?", mantêm as
fontes menores. Ao editar, mantenha esse piso.
