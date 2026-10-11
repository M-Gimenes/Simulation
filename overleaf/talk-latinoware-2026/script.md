# Roteiro da apresentação: Latinoware 2026 (Latin.Science)

Fala da apresentação do artigo "Balanceamento competitivo com preservação de identidade: Algoritmos
Genéticos e NSGA-II em arquétipos de jogos de luta" (`overleaf/artigo-latinware-2026/`). O limite da
sessão é de 5 minutos, com perguntas à parte.

Todo número, na fala e nos slides, vem do artigo submetido (`values.tex` e `main.tex`): 10 genes por
personagem, validador de 21 asserções, 150 lutas por confronto, 10 sementes. O sistema mudou depois da
submissão e nada do estado atual entra aqui.

A mesma fala está nas notas do orador de cada slide em `slides.pptx`.

## Tempo por slide

Estimativa a 135 palavras por minuto, um ritmo de fala calmo. No total são 604 palavras, ou 4:28; as trocas de slide somam uns 10 segundos. A 120 palavras por minuto a fala passa de 5 minutos (5:02), então ensaie com cronômetro e use os cortes abaixo se precisar.

| # | Slide | Palavras | Tempo |
|---|---|---|---|
| 1 | Capa | 26 | 0:12 |
| 2 | Problema | 78 | 0:35 |
| 3 | Ideia central | 95 | 0:42 |
| 4 | Método | 74 | 0:33 |
| 5 | Resultados | 82 | 0:36 |
| 6 | Resultados | 100 | 0:44 |
| 7 | Robustez | 72 | 0:32 |
| 8 | Conclusão | 77 | 0:34 |
| | **Total** | **604** | **4:28** |

## Fala

### 1. Capa (0:12)

Olá. Eu sou o Matheus, do Ifes de Cachoeiro de Itapemirim. Vou mostrar como equilibrar os personagens de um jogo de luta sem deixar todos iguais.

### 2. Problema (0:35)

Num jogo competitivo, equilíbrio é cada personagem ter uma chance parecida de vencer. Só que os bons jogos são feitos de estilos bem diferentes, que se enfrentam como pedra, papel e tesoura: um pressiona, outro mantém distância, outro bate forte, outro encadeia golpes, outro se defende. O risco: ao ajustar os números para igualar as vitórias, os personagens ficam parecidos. Daí a pergunta: um algoritmo genético consegue equilibrar esses cinco estilos sem destruir o que cada um é?

### 3. Ideia central (0:42)

A decisão central foi não forçar a identidade. O elenco original, que chamamos de canônico, é ponto de partida e régua, nunca regra: afastar-se dele custa, mas é permitido. O algoritmo busca duas coisas ao mesmo tempo: pouco desvio em relação ao canônico e pouco desbalanço. E o desbalanço é cego à direção: mede se alguém domina, não quem deveria vencer. Quem vence quem só é medido depois, fora da busca. Se isso entrasse na conta, o algoritmo preservaria por obrigação, e a pergunta se responderia sozinha. Medindo por fora, preservar ou perder vira resultado.

### 4. Método (0:33)

Para avaliar um elenco, um simulador põe os cinco para lutar, todos contra todos: dez confrontos, cento e cinquenta lutas em cada. Cada personagem são dez números: sete atributos, como vida, dano e alcance, e três pesos que dizem quanto ele avança, recua ou defende. Dois algoritmos fazem a busca. O genético escalar soma os dois objetivos e entrega uma solução. O NSGA-II mantém os dois separados e entrega a curva inteira de compromissos.

### 5. Resultados (0:36)

O elenco canônico tem a identidade intacta: passa nos vinte e um testes. Mas é muito desequilibrado. Nenhum dos dez confrontos é equilibrado, e um personagem vence todas as lutas enquanto outro não vence nenhuma. Quando o genético escalar evolui esse elenco, o equilíbrio vem: os dez confrontos ficam entre quarenta e sessenta por cento de vitória. Só que a conta chega do outro lado: sobram sete dos vinte e um testes. O equilíbrio veio, e boa parte da identidade foi embora.

### 6. Resultados (0:44)

O NSGA-II mostra o que existe entre esses dois extremos. Cada ponto do gráfico é um elenco. Para a esquerda, mais equilíbrio; para baixo, mais identidade. O canto de baixo à esquerda está vazio: para ganhar um, perde-se o outro. À direita, embaixo, está o canônico. No joelho, o desbalanço já caiu três quartos do caminho, e vinte dos vinte e um testes continuam valendo. No extremo do equilíbrio, nove dos dez confrontos ficam equilibrados, mas sobram treze testes. E o equilíbrio total do genético escalar deixa sete. Quem projeta o jogo passa a escolher um ponto sabendo o preço.

### 7. Robustez (0:32)

Isso se sustenta? Repetindo a busca dez vezes, cada personagem termina equilibrado em noventa a cem por cento das execuções. E, testando a solução mais equilibrada em dez sorteios que o algoritmo nunca viu, nove dos dez confrontos continuam equilibrados: não é sobreajuste. Já o ciclo de quem vence quem fica em cinco ou seis relações de dez em todos os pontos. A evolução não o destrói, mas também não o recupera.

### 8. Conclusão (0:34)

Então a resposta, ainda preliminar, é sim, com uma ressalva: dá para equilibrar sem destruir as identidades, mas isso tem um preço, e esse preço pode ser medido. Os limites: o modelo é bem mais simples que um jogo real, são só cinco arquétipos, e todos se enfrentam na mesma proporção. Os próximos passos são fechar a calibração, testar o equilíbrio contra um oponente que também se adapta e mapear quantos elencos diferentes chegam ao equilíbrio. Obrigado.

### 9. Dúvidas?

Slide de perguntas, sem fala.

## Se o tempo apertar

Cortes prontos, do menos ao mais custoso. Juntos economizam cerca de 35 segundos.

1. **Slide 6, última frase** ("Quem projeta o jogo passa a escolher um ponto sabendo o preço."): 5 s.
2. **Slide 7, primeira medida** ("Repetindo a busca dez vezes ... das execuções."): 8 s. Emende com
   "Testando a solução mais equilibrada...".
3. **Slide 8, os limites** ("Os limites: ... na mesma proporção."): 11 s. Ficam na tela como palavras-chave.
4. **Slide 4, os dez números** ("Cada personagem são dez números ... recua ou defende."): 12 s. O total fica na tela.

Não corte o slide 3. Sem ele, os resultados dos slides 5 a 7 parecem circulares.

## Slides de reserva

Ficam depois do "Dúvidas?" e não contam no tempo. Use só se perguntarem.

- **Slide 10, Tabela I:** os quatro pontos do compromisso e as seis métricas, como no artigo.
- **Slide 11, desbalanço:** os três termos (global, teto de hard-counter, decisividade) e seus pesos.
- **Slide 12, identidade:** a equação do desvio e os três instrumentos medidos por fora.

## Perguntas prováveis

Respostas com o que o artigo sustenta. Onde o artigo não investiga, a resposta diz isso.

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
10 sementes novas, 9 dos 10 confrontos da solução mais equilibrada seguem equilibrados.

**O que é o joelho da fronteira?**
É o ponto intermediário do compromisso. Na execução do artigo, ele leva o desbalanço de 1,42 para
0,34 e preserva 20 das 21 asserções. Só 2 dos 10 pares caem na banda de 40% a 60%, porque o ganho
ali é de equilíbrio global, não par a par.

**Qual é a função do AG escalar?**
A soma dos dois objetivos com pesos iguais: fitness = −(desvio + desbalanço). Ele entrega um ponto do
compromisso; o NSGA-II dispensa os pesos e mapeia a fronteira.

**Isso serve para um jogo real?**
Ainda não diretamente. O modelo é uma simplificação, o estudo usa cinco arquétipos contra dez ou mais
dos jogos reais, e o todos contra todos supõe que todos são jogados na mesma proporção. É um trabalho
em andamento.

## Depois de importar no Google Slides

Suba `slides.pptx` no Drive e abra com o Google Slides. Vale conferir quatro coisas, porque a
conversão foi verificada aqui só por uma prévia aproximada:

1. O logo do Latin.Science aparece no cabeçalho de todos os slides e na capa.
2. A fonte é Montserrat em todos os textos (se algum cair em Arial, a largura muda).
3. No slide 3, a caixa "Medição post hoc" e a seta que chega nela estão tracejadas.
4. Nenhum texto encosta na borda do próprio cartão, em especial nos slides 3, 6 e 10.
