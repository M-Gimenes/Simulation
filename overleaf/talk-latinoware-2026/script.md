# Roteiro da apresentação: Latinoware 2026 (Latin.Science)

Fala da apresentação do artigo "Balanceamento competitivo com preservação de identidade: Algoritmos
Genéticos e NSGA-II em arquétipos de jogos de luta" (`overleaf/artigo-latinware-2026/`). O limite da
sessão é de 5 minutos, com perguntas à parte.

O objetivo da fala é contar a história do trabalho, não resumir o artigo: apresentar o problema,
mostrar as duas decisões técnicas que o resolvem (medir a identidade por fora da busca e não somar os
objetivos) e deixar um resultado na memória. O registro é formal e leve: sem gíria e sem jargão
desnecessário. O detalhe técnico restante fica nas reservas e nas perguntas.

Todo número, na fala e nos slides, vem do artigo submetido (`values.tex` e `main.tex`): 10 genes por
personagem, validador de 21 asserções, 150 lutas por confronto, 10 sementes. O sistema mudou depois da
submissão (a bateria atual do TCC tem 23 asserções) e nada do estado atual entra aqui.

A mesma fala está nas notas do orador de cada slide em `slides.pptx`.

## Tempo por slide

São 640 palavras. A 150 palavras por minuto, um ritmo mais acelerado, a fala leva 4:16; a 135, um
ritmo calmo, 4:44. Ensaie com cronômetro: se passar de 4:45, use os cortes abaixo.

| # | Slide | Palavras | a 150 ppm |
|---|---|---|---|
| 1 | Capa | 34 | 0:14 |
| 2 | Problema: duas formas de comprometer um jogo | 76 | 0:30 |
| 3 | Problema: elenco e pergunta | 79 | 0:32 |
| 4 | Método | 135 | 0:54 |
| 5 | Resultados: antes e depois | 83 | 0:33 |
| 6 | Resultados: somar os objetivos | 76 | 0:30 |
| 7 | Resultados: fronteira | 88 | 0:35 |
| 8 | Conclusão | 69 | 0:28 |
| | **Total** | **640** | **4:16** |

## Fala

### 1. Capa

Olá a todos. Meu nome é Matheus, sou estudante de Sistemas de Informação no Ifes, campus Cachoeiro de
Itapemirim. Vou apresentar um trabalho sobre um problema que todo jogo competitivo enfrenta a cada
atualização.

### 2. Problema: duas formas de comprometer um jogo

Existem duas formas de comprometer um jogo competitivo. A primeira é a mais conhecida: um personagem
fica forte demais, e todos os jogadores passam a escolhê-lo. A segunda é mais sutil. Para corrigir a
primeira, ajustam-se os números até que ninguém domine. Só que, nesse processo, os personagens podem
perder justamente aquilo que os tornava únicos. O jogo fica equilibrado, mas a escolha do personagem
deixa de importar. O desafio, portanto, é equilibrar preservando a diferença.

### 3. Problema: elenco e pergunta

Para estudar esse problema, escolhemos os jogos de luta, em que o confronto é um contra um e cada
estilo é bem definido. Montamos um elenco com cinco estilos clássicos do gênero. Eles vão do rushdown,
que pressiona o tempo todo, ao turtle, que se defende e espera o erro, e se enfrentam como em pedra,
papel e tesoura. A pergunta da pesquisa é: um algoritmo genético consegue equilibrar esses cinco
estilos sem destruir a identidade de cada um?

### 4. Método

Cada personagem é descrito por dez números: atributos como vida, dano, alcance e velocidade, e pesos
que indicam o quanto ele prefere avançar, recuar ou se defender. Para avaliar um elenco, um simulador
coloca os cinco para lutar todos contra todos, cento e cinquenta vezes em cada confronto. O algoritmo
genético faz o que a evolução faz: gera elencos, combina os melhores, aplica mutações e repete.

A decisão central do trabalho é esta: não obrigamos o algoritmo a preservar os personagens. Ele busca
apenas duas coisas: equilíbrio e proximidade com o elenco original. Afastar-se do original tem um
custo, mas é permitido. Quem deveria vencer quem nunca entra na busca; isso só é medido depois. Se a
identidade fosse uma regra, ela sobreviveria por obrigação. Medida por fora, sua preservação passa a
ser um resultado.

### 5. Resultados: antes e depois

O ponto de partida é o elenco original, que chamamos de canônico. Ele passa nos vinte e um testes que
escrevemos para verificar a identidade de cada personagem, mas nenhum dos dez confrontos é
equilibrado: um personagem vence todas as lutas, e outro não vence nenhuma.

A primeira abordagem foi um algoritmo genético que soma os dois objetivos. Ele equilibra todos os dez
confrontos. Porém, restam apenas sete dos vinte e um testes. Ou seja, caiu exatamente no problema que
descrevemos no início.

### 6. Resultados: somar os objetivos

Por que isso aconteceu? Porque somar os objetivos já é uma escolha. Com pesos iguais, o algoritmo
decide sozinho quanto de identidade vale um pouco mais de equilíbrio, e entrega um único elenco. Por
isso usamos também o NSGA-II, um algoritmo multiobjetivo que não faz essa soma. Ele só descarta um
elenco se existir outro melhor nos dois objetivos ao mesmo tempo. O que sobra é a fronteira de Pareto:
o conjunto dos melhores compromissos encontrados.

### 7. Resultados: fronteira

Cada ponto deste gráfico é um elenco. Para a esquerda, mais equilíbrio; para baixo, mais identidade. O
canto inferior esquerdo está vazio: para ganhar de um lado, é preciso perder do outro. No extremo do
equilíbrio, o elenco mais equilibrado da fronteira tem nove dos dez confrontos equilibrados, mas
preserva treze testes. Já no joelho da curva, o desbalanço caiu três quartos do caminho, enquanto
vinte dos vinte e um testes continuam valendo. Quem projeta o jogo pode, então, escolher onde parar,
conhecendo o custo de cada passo.

### 8. Conclusão

A resposta, ainda preliminar, é sim: é possível equilibrar sem apagar as identidades, mas não sem
custo, e esse custo agora pode ser medido. O modelo ainda é simplificado, e o próximo passo é testar
o equilíbrio contra um adversário que também se adapta.

O código é aberto e está disponível no GitHub, pelo QR code, para quem quiser testá-lo. O projeto
segue em desenvolvimento e recebendo atualizações. Obrigado.

### 9. Dúvidas?

Slide de perguntas, sem fala. O QR code do repositório fica na tela o tempo todo.

## Se o tempo apertar

Cortes prontos, do menos ao mais custoso. Juntos economizam cerca de 30 segundos a 150 ppm.

1. **Slide 7, última frase** ("Quem projeta o jogo pode, então, escolher onde parar..."): 5 s. A
   conclusão diz a mesma coisa.
2. **Slide 7, o extremo do equilíbrio** ("No extremo do equilíbrio... preserva treze testes."): 8 s. Os
   números ficam na tabela.
3. **Slide 4, o ciclo da evolução** ("O algoritmo genético faz o que a evolução faz..."): 6 s. Mantenha
   se a plateia parecer leiga.
4. **Slide 3, os dois extremos do elenco** ("Eles vão do rushdown... e espera o erro,"): 8 s. Emende com
   "Montamos um elenco com cinco estilos clássicos do gênero, que se enfrentam como em pedra, papel e
   tesoura."

Não corte a segunda metade do slide 4 nem o slide 6. São as duas decisões técnicas do trabalho: sem a
primeira, os resultados parecem circulares; sem a segunda, a fronteira aparece sem motivo.

## Slides de reserva

Ficam depois do "Dúvidas?" e não contam no tempo. Use só se perguntarem.

- **Slide 10, robustez:** 10 execuções, 10 sementes novas e o ciclo de vantagens.
- **Slide 11, limites:** modelo simplificado, cinco arquétipos, sem matchmaking; calibração,
  coevolução e quality-diversity como próximos passos.
- **Slide 12, método:** os dois algoritmos lado a lado e o orçamento (300 elencos, 150 gerações).
- **Slide 13, Tabela I:** os quatro pontos do compromisso e as seis métricas, como no artigo.
- **Slide 14, desbalanço:** os três termos (global, teto de hard-counter, decisividade) e seus pesos.
- **Slide 15, identidade:** a equação do desvio e os instrumentos medidos por fora.

## Perguntas prováveis

Respostas com o que o artigo sustenta. Onde o artigo não investiga, a resposta diz isso.

**Por que jogo de luta?**
Porque é o caso mais limpo do problema: um contra um, sem composição de time, itens nem mapa, e com
estilos de personagem bem definidos. Dá para simular milhares de lutas e medir quem vence quem. Em
jogos de time o mesmo raciocínio vale, mas o modelo teria que ser muito maior.

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
10 sementes novas, 9 dos 10 confrontos da solução mais equilibrada seguem equilibrados. (Slide 10.)

**O que é o joelho da fronteira? Ele é equilibrado?**
É o ponto intermediário do compromisso. Na execução do artigo, ele leva o desbalanço de 1,42 para
0,34 e preserva 20 das 21 asserções. Mas só 2 dos 10 pares caem na banda de 40% a 60%, porque o ganho
ali é de equilíbrio global (cada personagem perto de 50% no total), não par a par. Por isso a fala diz
"o desbalanço caiu três quartos do caminho", e não "quase equilibrado".

**Qual é a função do AG escalar?**
A soma dos dois objetivos com pesos iguais: aptidão = −(desvio + desbalanço). Ele entrega um ponto do
compromisso; o NSGA-II dispensa os pesos e mapeia a fronteira.

**Isso serve para um jogo real?**
Ainda não diretamente. O modelo é uma simplificação, o estudo usa cinco arquétipos contra dez ou mais
dos jogos reais, e o todos contra todos supõe que todos são jogados na mesma proporção. É um trabalho
em andamento.

## Depois de importar no Google Slides

Suba `slides.pptx` no Drive e abra com o Google Slides. Vale conferir cinco coisas, porque a conversão
foi verificada aqui só por uma prévia aproximada (sem a fonte Montserrat instalada):

1. O logo do Latin.Science aparece no cabeçalho de todos os slides e na capa.
2. A fonte é Montserrat em todos os textos (se algum cair em Arial, a largura muda).
3. Nenhum texto quebra linha ou encosta na borda do próprio cartão, em especial "perto do original"
   no slide 4, a regra do NSGA-II no slide 6, a legenda do slide 7 e o subtítulo do slide 8.
4. No slide 4, a caixa "Medido depois" e a seta que chega nela estão tracejadas.
5. O QR code dos slides 8 e 9 abre `github.com/M-Gimenes/Simulation` (teste com o celular na tela do
   computador).

## Tamanho de fonte

O data-show da sala não está bem posicionado, então nenhum texto dos slides 1 a 9 fica abaixo de
28 pt (o slide tem 20 polegadas de largura, então 28 pt aqui equivalem a uns 19 pt num slide padrão).
As exceções são da moldura do evento ("Realização:" e o nome do congresso na capa) e os números dos
eixos dentro da figura da fronteira, que é uma imagem. As reservas, depois do "Dúvidas?", mantêm as
fontes menores. Ao editar, mantenha esse piso.
