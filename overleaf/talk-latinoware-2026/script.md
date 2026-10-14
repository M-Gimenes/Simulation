# Roteiro da apresentação: Latinoware 2026 (Latin.Science)

Fala da apresentação do artigo "Balanceamento competitivo com preservação de identidade: Algoritmos
Genéticos e NSGA-II em arquétipos de jogos de luta" (`overleaf/artigo-latinware-2026/`). O limite da
sessão é de 5 minutos, com perguntas à parte.

O objetivo da fala é contar a história do trabalho, não resumir o artigo: fazer a plateia sentir o
problema, entender a decisão central e sair lembrando de um resultado. O detalhe técnico fica nas
reservas e nas perguntas.

Todo número, na fala e nos slides, vem do artigo submetido (`values.tex` e `main.tex`): 10 genes por
personagem, validador de 21 asserções, 150 lutas por confronto, 10 sementes. O sistema mudou depois da
submissão (a bateria atual do TCC tem 23 asserções) e nada do estado atual entra aqui.

A mesma fala está nas notas do orador de cada slide em `slides.pptx`.

## Tempo por slide

Estimativa a 135 palavras por minuto. No total são 528 palavras, ou 3:54; a 120 palavras por minuto,
4:24. A folga é proposital: a fala tem pausas (depois do gancho, antes do "caiu direitinho na armadilha
do patch" e no joelho da curva) e elas valem mais que mais uma frase.

| # | Slide | Palavras | Tempo |
|---|---|---|---|
| 1 | Capa | 23 | 0:10 |
| 2 | Problema: dois jeitos de estragar | 81 | 0:36 |
| 3 | Problema: elenco e pergunta | 75 | 0:33 |
| 4 | Método | 114 | 0:50 |
| 5 | Resultados: antes e depois | 74 | 0:32 |
| 6 | Resultados: fronteira | 87 | 0:38 |
| 7 | Conclusão | 74 | 0:32 |
| | **Total** | **528** | **3:54** |

## Fala

### 1. Capa (0:10)

Oi, eu sou o Matheus, do Ifes de Cachoeiro. Meu TCC é sobre um problema que todo jogo competitivo
enfrenta a cada atualização.

### 2. Problema: dois jeitos de estragar (0:36)

Tem dois jeitos de estragar um jogo competitivo. O primeiro todo mundo conhece: um personagem fica forte
demais e todo mundo passa a jogar com ele. O segundo é mais traiçoeiro. Sai um patch, mexem nos números
até ninguém dominar, e no caminho os personagens perdem o que tinham de único. Eu jogo mais LoL, e lá
vejo isso direto: um ajuste aqui, outro ali, e de repente dois campeões jogam quase igual. Fica
equilibrado, mas tanto faz quem você escolhe.

### 3. Problema: elenco e pergunta (0:33)

No TCC, levamos isso pro jogo de luta, onde é um contra um e cada estilo é bem marcado. Montamos cinco
estilos clássicos. O rushdown, que vive colado no adversário. O zoner, que mantém distância. O grappler,
que aposta em golpes pesados. O combo master, que encadeia sequências. E o turtle, que se defende e
espera o erro. A pergunta é: um algoritmo genético consegue equilibrar esses cinco sem apagar o que
cada um é?

### 4. Método (0:50)

Cada personagem vira dez números: vida, dano, alcance, velocidade, e o quanto ele prefere avançar,
recuar ou defender. Pra avaliar um elenco, um simulador põe os cinco pra lutar todos contra todos, cento
e cinquenta vezes cada confronto. O algoritmo faz o que a evolução faz: gera elencos, cruza os melhores,
muta e repete.

E aqui está a decisão mais importante do trabalho: não mandamos o algoritmo preservar os personagens.
Ele só busca duas coisas: ficar equilibrado e não se afastar demais do original. Se afastar custa, mas
pode. Quem deveria vencer quem, ele nunca fica sabendo; isso só medimos depois. Se a identidade fosse
regra, sobreviveria por obrigação. Assim, se sobreviver, é resultado.

### 5. Resultados: antes e depois (0:32)

O ponto de partida é o elenco original, que chamamos de canônico. Ele passa nos vinte e um testes que
escrevemos pra conferir quem é quem. Mas nenhum dos dez confrontos é equilibrado: um personagem ganha
todas as lutas, outro não ganha nenhuma.

Aí o algoritmo soma os dois objetivos e equilibra. E consegue: dez de dez confrontos equilibrados. Só
que sobram sete dos vinte e um testes. Caiu direitinho na armadilha do patch.

### 6. Resultados: fronteira (0:38)

Então rodamos de novo com o NSGA-II, que, em vez de uma resposta, devolve o cardápio inteiro de
compromissos. Cada ponto aqui é um elenco. Pra esquerda, mais equilíbrio; pra baixo, mais identidade. O
canto de baixo à esquerda está vazio: pra ganhar de um lado, perde-se do outro. Mas olha o joelho da
curva: o desbalanço já caiu três quartos do caminho e vinte dos vinte e um testes continuam valendo.
Quem desenha o jogo passa a escolher onde parar, sabendo o preço de cada passo.

### 7. Conclusão (0:32)

A resposta, ainda preliminar, é sim, mas não de graça. E agora esse preço tem número. O modelo é bem
mais simples que um jogo de verdade, e o próximo passo é testar contra um adversário que também se
adapta.

Se você faz jogo, joga competitivo ou curte algoritmo genético e quer ver isso por dentro, o código
está no GitHub, nesse QR code. Estou por aqui, é só me chamar pra conversar. Obrigado.

### 8. Dúvidas?

Slide de perguntas, sem fala. O QR code do repositório fica na tela o tempo todo.

## Se o tempo apertar

Cortes prontos, do menos ao mais custoso. Juntos economizam cerca de 30 segundos.

1. **Slide 6, última frase** ("Quem desenha o jogo passa a escolher onde parar..."): 5 s. O slide 7 diz
   a mesma coisa.
2. **Slide 3, a frase de ponte** ("No TCC, levamos isso pro jogo de luta..."): 5 s. Emende direto com
   "Montamos cinco estilos clássicos de jogo de luta".
3. **Slide 4, o ciclo da evolução** ("O algoritmo faz o que a evolução faz..."): 6 s. Está na tela.
4. **Slide 2, a frase do LoL**: 9 s. Só corte se estiver muito apertado; é a parte mais sua da fala.

Não corte a segunda metade do slide 4. Sem ela, os resultados parecem circulares: a plateia acha que o
algoritmo preservou a identidade porque foi mandado.

## Slides de reserva

Ficam depois do "Dúvidas?" e não contam no tempo. Use só se perguntarem.

- **Slide 9, robustez:** 10 execuções, 10 sementes novas e o ciclo de vantagens.
- **Slide 10, limites:** modelo simplificado, cinco arquétipos, sem matchmaking; calibração,
  coevolução e quality-diversity como próximos passos.
- **Slide 11, método:** os dois algoritmos lado a lado e o orçamento (300 elencos, 150 gerações).
- **Slide 12, Tabela I:** os quatro pontos do compromisso e as seis métricas, como no artigo.
- **Slide 13, desbalanço:** os três termos (global, teto de hard-counter, decisividade) e seus pesos.
- **Slide 14, identidade:** a equação do desvio e os instrumentos medidos por fora.

## Perguntas prováveis

Respostas com o que o artigo sustenta. Onde o artigo não investiga, a resposta diz isso.

**Por que jogo de luta, se o exemplo foi LoL?**
Porque o jogo de luta é o caso mais limpo do mesmo problema: um contra um, sem composição de time,
itens nem mapa, e com estilos de personagem bem definidos. Dá para simular milhares de lutas e medir
quem vence quem. Num MOBA o mesmo raciocínio vale, mas o modelo teria que ser muito maior.

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
10 sementes novas, 9 dos 10 confrontos da solução mais equilibrada seguem equilibrados. (Slide 9.)

**O que é o joelho da fronteira? Ele é equilibrado?**
É o ponto intermediário do compromisso. Na execução do artigo, ele leva o desbalanço de 1,42 para
0,34 e preserva 20 das 21 asserções. Mas só 2 dos 10 pares caem na banda de 40% a 60%, porque o ganho
ali é de equilíbrio global (cada personagem perto de 50% no total), não par a par. Por isso a fala diz
"o desbalanço caiu três quartos", e não "quase equilibrado".

**Qual é a função do AG escalar?**
A soma dos dois objetivos com pesos iguais: fitness = −(desvio + desbalanço). Ele entrega um ponto do
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
   no slide 4, a legenda do slide 6 e o subtítulo do slide 7.
4. No slide 4, a caixa "Medido depois" e a seta que chega nela estão tracejadas.
5. O QR code dos slides 7 e 8 abre `github.com/M-Gimenes/Simulation` (teste com o celular na tela do
   computador).

## Tamanho de fonte

O data-show da sala não está bem posicionado, então nenhum texto dos slides 1 a 8 fica abaixo de
28 pt (o slide tem 20 polegadas de largura, então 28 pt aqui equivalem a uns 19 pt num slide padrão).
As exceções são da moldura do evento ("Realização:" e o nome do congresso na capa) e os números dos
eixos dentro da figura da fronteira, que é uma imagem. As reservas, depois do "Dúvidas?", mantêm as
fontes menores. Ao editar, mantenha esse piso.
