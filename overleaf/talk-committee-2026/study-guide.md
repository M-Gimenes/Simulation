# Guia de estudo: o TCC e a apresentação à banca

Este guia explica o trabalho no estado em que foi entregue (monografia de 100 páginas, bateria de
23/09/2026) e a apresentação de defesa, reestruturada depois da primeira apresentação à banca, em
21/10/2026. Ele foi escrito para você retomar o trabalho inteiro depois de tudo o que mudou desde a
Latinoware.

Nenhum número aqui é novo. Todos vêm da monografia (`overleaf/TCC/valores.tex` e os capítulos) ou
dos artefatos de `results/` que ela cita. Onde há uma conta feita só para explicar um conceito, como
um exemplo do intervalo de Wilson, o texto avisa que é uma **conta ilustrativa**: ela não está na
monografia e não deve ser citada como resultado.

A fala e o tempo de cada slide estão em `script.md`. Este guia explica o que está por trás deles.

## Sumário

1. [O trabalho em uma página](#1-o-trabalho-em-uma-página)
2. [O que mudou desde a Latinoware](#2-o-que-mudou-desde-a-latinoware)
3. [O problema e a pergunta](#3-o-problema-e-a-pergunta)
4. [O simulador de combate](#4-o-simulador-de-combate)
5. [Como um elenco é avaliado](#5-como-um-elenco-é-avaliado)
6. [A função de aptidão](#6-a-função-de-aptidão)
7. [O ruído da avaliação](#7-o-ruído-da-avaliação)
8. [Os três algoritmos](#8-os-três-algoritmos)
9. [O protocolo: o que está sendo comparado](#9-o-protocolo-o-que-está-sendo-comparado)
10. [As métricas, uma a uma](#10-as-métricas-uma-a-uma)
11. [A estatística: Wilson, Wilcoxon, Â₁₂, Holm](#11-a-estatística-wilson-wilcoxon-â₁₂-holm)
12. [Os resultados, por questão](#12-os-resultados-por-questão)
13. [A interpretação](#13-a-interpretação)
14. [A apresentação, slide a slide](#14-a-apresentação-slide-a-slide)
15. [O que não afirmar](#15-o-que-não-afirmar)
16. [Glossário](#16-glossário)

---

## 1. O trabalho em uma página

**A pergunta.** Um algoritmo genético consegue equilibrar cinco arquétipos de um jogo de luta sem
destruir as suas identidades funcionais?

**O sistema.** Um simulador de luta um contra um. Cada indivíduo do algoritmo é um **elenco inteiro**:
5 personagens × 11 genes = 55 genes. Um elenco é avaliado pondo todos contra todos: 10 confrontos ×
150 lutas = 1.500 lutas. A aptidão tem dois termos: o **desequilíbrio** (`P_dom`) e o **desvio de
identidade** (`P_drift`).

**O experimento.** Três algoritmos (AG escalar, NSGA-II e um híbrido dos dois) e dois controles (o AG
escalar sem o termo de identidade e o AG escalar sem a semente canônica). Cada um é um **braço**,
rodado 20 vezes com as mesmas sementes (42 a 61), sempre com 300 elencos × 150 gerações.

**A resposta.** Sim, com uma qualificação sobre quanto da identidade sobrevive.

| Questão | Resposta | Números principais |
|---|---|---|
| **QP1** Equilíbrio | Sim | 20/20 execuções convergem (geração 31 em média); 16/20 terminam equilibradas; o elenco testado replica fora do laço; robusto a 4 de 8 regras alteradas |
| **QP2** Identidade | Em parte, e a parte que sobra se deve ao termo de identidade | Sem o termo, as 4 métricas de identidade caem ao nível de elencos sorteados (τ 0,28 → −0,03), e o equilíbrio não muda de forma significativa (p de Holm 0,059). A política é o que mais se perde |
| **QP3** Compromisso | Nenhum algoritmo domina o outro, mas o AG escalar não chega ao seu próprio ótimo | Na soma desequilíbrio + desvio, a fronteira do NSGA-II tem ponto melhor que o AG em 20/20 sementes. O híbrido quase dobra a concordância τ (0,28 → 0,52) sem perder equilíbrio (16/20 equilibrados nos dois) |

**A mensagem final.** Preservar identidade exige pressão explícita por identidade e uma busca que
mantenha a diversidade de identidade sob avaliação ruidosa.

**As cinco contribuições** (Conclusão da monografia):
1. Uma formulação não circular: a aptidão contém a **premissa** (o que cada arquétipo é), nunca a
   **resposta** (quem vence quem).
2. Evidência controlada: o controle λ = 0 mostra que a identidade preservada se deve ao termo.
3. Uma falha da seleção escalar: ela termina num extremo do compromisso, longe do próprio ótimo, em
   dois estágios.
4. A perda de identidade está na política, por causa do passo de mutação somado ao ruído.
5. Lições de método: piso medido para métricas de identidade, cuidado com medições grosseiras,
   resolução compatível com a margem do fenômeno, proveniência registrada em cada artefato.

---

## 2. O que mudou desde a Latinoware

O artigo da Latinoware começou a ser escrito em 14/08/2026 e usa os números do sistema daquela época.
O sistema continuou mudando até a bateria de 23/09/2026, que é a única citável. A palestra da
Latinoware usou só os números do artigo; a da banca usa só os da bateria. **Os dois conjuntos não são
comparáveis**, porque mudaram o combate, o desvio, o validador, a forma de avaliar e a amostra.

### 2.1 Antes e agora

| Aspecto | Artigo da Latinoware | TCC (bateria de 23/09) |
|---|---|---|
| Genes por personagem | 10 (7 atributos + 3 pesos) | **11**: entrou o agarrão (`grab_power`) |
| Ataque | era uma das ações escolhidas: quem recuava não golpeava | **dois canais**: a postura é sorteada, o ataque é uma regra; avançar e recuar golpeiam, só a guarda abre mão do golpe |
| Fora do alcance | o personagem avançava sempre | a intenção é sorteada sempre; o avanço só é imposto no **impasse** (ninguém alcança ninguém) |
| Persistência da intenção | 10 sub-ticks | **5** sub-ticks |
| Corpos | se atravessavam | **colisão** |
| Empate | ia para o lado A | **meia vitória** para cada lado |
| Temporizadores | arredondados a cada golpe | **resto acumulado** (difusão de erro) |
| Desvio | distância euclidiana; atributos divididos pelo limite superior; todos os genes com o mesmo peso | raiz da média **ponderada**: dividido pela **amplitude** do gene, **peso 3** nos genes definidores, pesos de comportamento **reescalados** |
| Validador | 21 asserções (17 de genes + 4 de comportamento) | **23** (13 + 5 + 5); empate conta contra; pesos lidos como probabilidades |
| Identidade funcional contínua | não havia | **concordância τ** |
| "Equilibrado" | confronto com taxa de vitória entre 40% e 60%; o artigo contava pares equilibrados (x de 10) | **predicado**: todo personagem entre 40% e 60% no total **e** nenhum par acima de 65%; conta-se **hard counters** |
| Sorteios da avaliação | o mesmo stream em todas as gerações | CRN dentro da geração (uma semente por luta) e **stream novo a cada geração** |
| População inicial do NSGA-II | canônico + 299 sorteados | **300 sorteados** |
| Execuções | uma execução (semente 42) para a tabela; 10 do NSGA-II para média ± desvio-padrão | **20 por braço**, mesmas sementes, 5 braços |
| Braços | AG escalar e NSGA-II | + **híbrido**, **controle λ = 0**, **controle sem semente** |
| Medição do resultado | dentro do laço | **reavaliação** com 1.000 lutas por par, semente comum |
| Estatística | média ± desvio-padrão | **Wilcoxon pareado + Â₁₂ + Holm**, e **35 modelos nulos** |
| Representantes da fronteira | best_dominance, knee_point, best_drift | + ideal_point e **scalar_optimum** (o da comparação principal) |
| Hipervolume | referência (2; 1), valor 1,80 | referência **(1,3; 0,4)**, valor 0,395 ± 0,011 |
| Validação externa | 10 sementes novas; 9 de 10 confrontos equilibrados | **replicação** (5.000 lutas por par) + **robustez** a 8 regras alteradas, com **intervalo de Wilson** |
| Ciclo de vantagens | contado sem separar arestas decididas de indecisas: 5/10 no canônico | teste próprio com **16.000 lutas por par**, contando só arestas **decididas**: 6/10 no canônico |
| Desequilíbrio do canônico | 1,42 | **1,28** |

### 2.2 As afirmações que mudaram de sentido

| Na Latinoware | Agora | Por quê |
|---|---|---|
| "O AG escalar equilibra os 10 confrontos, mas homogeneíza: 7 de 21 asserções" | O AG escalar equilibra (16/20 elencos) e preserva identidade **parcial**: 11 de 18 asserções de genes e 3 de 5 de comportamento, na mediana. Essa identidade se deve ao termo de desvio | Mudaram o validador, o desvio, o combate e a amostra. E o controle λ = 0 mostra o que seria homogeneizar de verdade: sem o termo, a identidade fica no nível do acaso |
| "O joelho da fronteira é o compromisso: o desbalanço cai três quartos e preserva 20 de 21" | O joelho preserva quase toda a identidade (Camada 3 em 5/5, τ = 0,70), mas **não é equilibrado em nenhuma execução** (6,85 hard counters em média) | Com o predicado de equilíbrio e 20 execuções, os pontos que interessam à pergunta estão na **ponta de equilíbrio** da fronteira |
| "Validado em sementes novas: 9 de 10 confrontos" | **Só o AG escalar replica.** O scalar_optimum do NSGA-II falha (Rushdown × Combo Master em 32,7%), e o joelho e o canônico falham com folga. Fora das regras do treino, o AG escalar é robusto em 4 de 8 | A validação externa passou a separar replicação (mesmas regras) de robustez (regras novas), com intervalo de confiança |
| "Ciclo: 5 de 10 arestas mantidas" | O ciclo **não se realiza nem no canônico** (6/10, uma hierarquia). Nos elencos do AG, 56,5% das arestas decididas seguem a direção proposta, sem diferença do acaso (p = 0,091) | Com poucas lutas, a contagem é ruído: a 200 lutas por par, espelhos, sem estrutura alguma, marcavam 5,4 arestas "mantidas". O teste foi refeito com 16.000 lutas por par |
| (não existia) | O controle λ = 0, a perda da política, o AG escalar fora do próprio ótimo, os dois estágios e o híbrido | São achados da bateria de setembro |

### 2.3 Por que tanto mudou

Três mudanças explicam a maior parte da diferença.

- **O combate de canal único invalidava o Zoner.** Quando atacar era uma ação escolhida, recuar
  significava não golpear. Num par de teste (alcance 20 contra alcance 6 e velocidade máxima), o
  personagem de longo alcance perdia 100% das lutas, qualquer que fosse o alcance ou a repulsão,
  justamente os genes que definem o Zoner, e a repulsão tinha efeito negativo. Com dois canais, o
  mesmo personagem vence 49%, e variar a repulsão leva a taxa de vitória de 27% a 72%.
- **A busca "decorava" os sorteios.** No artigo, todas as gerações eram avaliadas com o mesmo stream
  de sorteios. A busca podia achar elencos equilibrados naquela sequência, e não no jogo. A razão
  entre o desequilíbrio dentro do laço e o de sorteios novos caiu de 4,14 para 2,20 quando o stream
  passou a mudar a cada geração.
- **A medição ganhou referência.** Sem modelos nulos e sem controle, "7 de 21" ou "20 de 21" não
  tinham escala. Hoje se sabe, por exemplo, que um elenco sorteado já satisfaz cerca de 6 das 23
  asserções por acaso.

Uma afirmação também caiu durante as baterias de setembro, depois da Latinoware: "tirar o termo de
identidade **piora** o equilíbrio". Com 200 lutas por par ela era significativa (p de Holm 0,038); com
1.000 lutas, nos mesmos elencos, deixou de ser (0,059). Ver a seção 13.5.

---

## 3. O problema e a pergunta

### 3.1 As duas formas de errar

1. Um personagem forte demais: todos escolhem o mesmo.
2. Ao corrigir o primeiro erro, os personagens ficam parecidos. No limite, cinco cópias do mesmo
   personagem são perfeitamente equilibradas, e a escolha deixa de importar.

O trabalho fica entre os dois: equilibrar preservando a diferença.

### 3.2 A linha que impede a pergunta de ser circular

**A aptidão pode conter a premissa, nunca a resposta.**

| | O que é | Pode entrar na aptidão? |
|---|---|---|
| **Premissa** | O que cada arquétipo **é**: os perfis canônicos e os genes definidores | Sim, como o termo de desvio |
| **Resposta** | Quem vence quem, e se equilíbrio e identidade são compatíveis | Nunca; só é medida depois (*post hoc*) |

"O Zoner é definido pelo alcance" é premissa. "O Zoner deve vencer o Grappler" é resposta. Se a
resposta estivesse na aptidão, o algoritmo a exibiria por ter sido pago para isso, e o resultado não
provaria nada.

Dois detalhes sustentam a linha:
- O desvio é **penalidade, não restrição**. O algoritmo pode se afastar do canônico pagando um custo, e
  ele de fato se afasta: o AG escalar termina com 11 de 18 asserções de genes, contra 18 do canônico.
- A identidade **funcional** (se o personagem ainda joga como ele mesmo) é medida por métricas de
  comportamento que nenhum termo da aptidão vê.

### 3.3 O elenco

Os cinco arquétipos e os seus valores são **construção sua**, a premissa do trabalho, e não algo
tirado da literatura. Foram declarados finais antes da bateria, por três critérios: coerentes com a
descrição de cada arquétipo (passam nas 23 asserções), distintos entre si e **desequilibrados de
propósito**, para que haja o que equilibrar.

| Arquétipo | vida | dano | intervalo | alcance | velocidade | atordoamento | repulsão | agarrão | FRENTE | RECUAR | GUARDA |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Zoner | 300 | 20 | 4 | **18** | 2,5 | 0,10 | **2,0** | 0,05 | 0,30 | **0,60** | 0,20 |
| Rushdown | 320 | 16 | **1** | 10 | **5,0** | 0,10 | 1,0 | 0,20 | **0,90** | 0,05 | 0,10 |
| Combo Master | 350 | 18 | 3 | 10 | 3,0 | **0,55** | 0,5 | 0,30 | 0,70 | 0,05 | 0,20 |
| Grappler | 400 | **27** | 4 | 8 | 2,0 | 0,30 | 0,5 | **0,90** | 0,70 | 0,10 | 0,40 |
| Turtle | **450** | 15 | **5** | 13 | **1,5** | 0,20 | 1,0 | 0,15 | 0,20 | 0,40 | **0,70** |

Em negrito, os **genes definidores**: aqueles em que o arquétipo ocupa, por projeto, um extremo do
elenco. Eles pesam 3 no desvio e coincidem com a Camada 1 do validador.

Limites de busca: vida 250–450, dano 15–30, intervalo 1–5, alcance 5–20, velocidade 1–5,
atordoamento 0–0,6, repulsão 0–3, agarrão 0–1, pesos 0–1.

Em probabilidade de intenção (seção 4.3), o Rushdown canônico avança em 86% das intenções, o Zoner
recua em 55% e o Turtle guarda em 54%.

### 3.4 As três questões

- **QP1 (equilíbrio).** O algoritmo alcança equilíbrio competitivo, e esse equilíbrio se sustenta fora
  das condições em que foi otimizado?
- **QP2 (identidade).** As identidades funcionais sobrevivem além do que sobreviveria se a aptidão não
  tivesse termo de identidade?
- **QP3 (compromisso).** Como o AG escalar, o NSGA-II e o híbrido se posicionam no compromisso entre
  equilíbrio e identidade?

Repare na formulação da QP2: "além do que sobreviveria **sem o termo**". É por isso que o controle
λ = 0 é a evidência da QP2, e não os modelos nulos.

### 3.5 O ciclo de vantagens proposto

Também é construção sua, uma **hipótese**, nunca um alvo da busca.

| Vence | Perde | Motivo no gênero |
|---|---|---|
| Rushdown | Zoner | pressão não deixa montar o jogo de distância |
| Rushdown | Combo Master | pressão antes do combo |
| Zoner | Grappler | controla o espaço, fica fora do alcance do agarrão |
| Zoner | Turtle | fica fora da zona de punição |
| Grappler | Rushdown | o agarrão pune a pressão |
| Grappler | Turtle | o agarrão é o counter clássico do bloqueio |
| Combo Master | Grappler | personagem lento morre para combo |
| Combo Master | Zoner | um acerto vira a luta |
| Turtle | Rushdown | o bloqueio absorve a pressão |
| Turtle | Combo Master | o bloqueio quebra o combo |

Cada arquétipo vence dois e perde dois. O resultado (seção 12.6) é que o canônico só realiza 6 dessas
10 arestas.

---

## 4. O simulador de combate

O critério de projeto foi que **cada gene movesse o resultado das lutas de forma visível para a
busca**. Cada regra abaixo veio com uma medição que a justifica.

### 4.1 Campo e tempo

- Campo de uma dimensão, comprimento 100; os lutadores começam a 50 de distância (posições 25 e 75).
  Nenhum alcance passa de 20, então ninguém golpeia antes de se mover.
- O tempo é discreto. Um **tick** tem **5 sub-ticks**, a unidade real da simulação, para dar
  resolução aos genes de tempo (com ticks inteiros, o intervalo entre golpes teria só 5 valores).
- A duração máxima (2.500 sub-ticks) é só uma trava: nas medições, **100% das lutas terminaram em
  nocaute**, com cerca de 340 sub-ticks em média.

### 4.2 Dois canais de ação

A decisão central do modelo:
- A **postura** (avançar, recuar ou guardar) é escolhida por sorteio.
- O **ataque** é uma **regra**: sai sempre que a recarga terminou, o oponente está ao alcance (medido
  depois do movimento) e a postura não é de guarda.

Avançar e recuar golpeiam; só quem guarda abre mão do golpe. É isso que faz do controle de distância
uma estratégia: "zonear" é golpear mantendo a distância. Os números estão na seção 2.3.

### 4.3 O sorteio da intenção

Quando não há intenção vigente, o lutador sorteia uma, com probabilidade proporcional aos pesos:

```
P(FRENTE) = w_F / (w_F + w_R + w_G)
P(RECUAR) = w_R / (w_F + w_R + w_G)
P(GUARDA) = w_G / (w_F + w_R + w_G)
```

- **Por que sorteio proporcional, e não "faz a ação de maior peso"?** Com a regra determinística, só a
  ordem dos pesos importaria, e toda mutação que não invertesse a ordem passaria despercebida. Com o
  sorteio, mudar um pouco um peso muda um pouco a frequência da ação: a busca tem sinal contínuo.
- **Só a razão entre os pesos importa.** Multiplicar os três por 2 dá o mesmo personagem. Por isso o
  desvio reescala os pesos e o validador os lê como probabilidades.
- **É a única fonte de aleatoriedade da luta.** O dano é fixo. Uma luta é reproduzível a partir da
  semente.

**Tradução da intenção em postura:**

| Intenção | Condição | Postura | Golpeia? |
|---|---|---|---|
| FRENTE | sempre | avanço | sim |
| RECUAR | há espaço atrás | recuo | sim |
| RECUAR | encurralado na borda | defesa **forçada** | não |
| GUARDA | sempre | defesa | não |
| qualquer | ninguém alcança ninguém (**impasse**) | avanço imposto | sim |
| qualquer | atordoado | nenhuma, perde o sub-tick | não |

- **Persistência de 5 sub-ticks.** A intenção sorteada vale por 5 sub-ticks, um tick, que é também o
  intervalo do atacante mais rápido. Sortear GUARDA custa exatamente uma janela de ataque. Contra 10
  sub-ticks, o valor 5 melhorou a razão sinal/ruído da sensibilidade nos 8 atributos (ganhos de 25% a
  81%). Durante o atordoamento, a intenção e o contador ficam congelados.
- **Impasse.** Sem a regra, dois personagens passivos recuariam até as bordas: 100% das lutas entre
  Zoner e Turtle canônicos acabavam por tempo, sem nenhum golpe. A regra não atrapalha o zoning,
  porque quem está ao alcance do oponente continua livre para recuar.
- **Defesa forçada.** Fica registrada à parte, para que o encurralamento não conte como "disposição
  defensiva" nas métricas de comportamento.

### 4.4 Movimento e colisão

Os dois se movem ao mesmo tempo, `velocidade / 5` por sub-tick. Se fossem se cruzar, param no ponto de
encontro. Sem colisão, eles se atravessavam 134 vezes por luta no canônico, e o alcance perdia efeito
no corpo a corpo.

### 4.5 O golpe

Um golpe tem quatro efeitos:

- **Dano**, fixo, com um único modificador, a postura do alvo:
  - alvo **não** defende: dano × 1;
  - alvo **defende**: dano × (0,6 + agarrão do atacante).

  Com agarrão 0, a guarda corta 40%. Com 0,4 (ponto neutro), a guarda é anulada. Acima disso,
  defender é pior que não defender, até 1,6×. Só o Grappler canônico (0,9 → 1,5×) passa do ponto
  neutro. O agarrão não é uma quarta ação: é uma condição na resolução do golpe, contra quem guarda, e
  não muda nada contra quem avança ou recua.
- **Atordoamento**: o alvo perde, em média, `atordoamento × intervalo × 5` sub-ticks. Como o gene vai
  até 0,6, o atordoamento sempre acaba antes do golpe seguinte do atacante: não existe travamento
  permanente.
- **Repulsão**: o alvo é empurrado `repulsão` unidades, até a borda.
- **Recarga**: o atacante espera, em média, `intervalo × 5` sub-ticks.

### 4.6 Temporizadores com resto acumulado

`intervalo × 5` e o atordoamento dão números quebrados, e o temporizador conta sub-ticks inteiros.
Arredondar cada golpe deixaria os genes em degraus. A solução é a **difusão de erro**: o resto de um
golpe passa para o seguinte. Um intervalo de 6,5 sub-ticks vira 7, 6, 7, 6..., com média exata 6,5, e
o combate continua determinístico. Medido: no atordoamento de um Rushdown evoluído, variado em 31
valores, o arredondamento simples dá 5 taxas de vitória distintas; a difusão de erro dá 27.

### 4.7 Fim da luta

Nocaute, ou, no tempo máximo, vence quem conserva a maior **fração** de vida. Frações iguais (incluindo
nocaute duplo) dão **empate**, que vale meia vitória. Sem o empate, o desempate ia sempre para o lado
esquerdo, que na avaliação é sempre o arquétipo de menor índice: o espelho do Rushdown, que por
simetria daria 50%, dava 54,9% a esse lado.

---

## 5. Como um elenco é avaliado

### 5.1 Todos contra todos

Os 5 personagens formam C(5,2) = **10 pares**; cada par luta **150 vezes**: 1.500 lutas por avaliação.

- **Taxa de vitória do par** `p_ij`: fração das lutas que `i` vence contra `j` (empate = meia
  vitória). Vale `p_ji = 1 − p_ij`.
- **Taxa de vitória global** de um personagem: a média das suas 4 taxas de par.
- **Decisividade** `D_ij`: quanto as lutas são folgadas, não quem as vence. Cada luta recebe um escore
  `s` (no nocaute, `0,5 + 0,5 × fração de vida que o vencedor conserva`, do ponto de vista dele), e
  `D` é a média de `|s − 0,5|`. Como todas as lutas acabam em nocaute, `D` é metade da vida média com
  que o vencedor termina. `D` alto = lutas que são massacres, seja quem for o vencedor.

### 5.2 O tamanho do ruído

Uma taxa de vitória medida em `n` lutas tem desvio-padrão binomial de cerca de `√(0,25 / n)` perto de
50%. Esta tabela ajuda a ler todos os números de lutas do trabalho:

| Lutas por par | Desvio-padrão perto de 50% | Onde aparece |
|---|---|---|
| 150 | ~4 pontos percentuais | avaliação dentro da busca |
| 200 | ~3,5 pontos | confirmação da convergência; perfil comportamental; sensibilidade |
| 1.000 | ~1,6 ponto | reavaliação da bateria |
| 5.000 | ~0,7 ponto | validação externa |
| 16.000 | ~0,4 ponto | teste do ciclo |

(150, 1.000 e 16.000 estão na monografia; 200 e 5.000 são conta ilustrativa com a mesma fórmula.)

---

## 6. A função de aptidão

### 6.1 Desvio de identidade (`P_drift`, roxo nos slides)

Para cada gene `k` do personagem do arquétipo `a`:

```
e = (gene − canônico) / (limite superior − limite inferior)
δ_a = √( Σ ω·e² / Σ ω )        ω = 3 nos genes definidores de a, 1 nos demais
P_drift = média de δ_a nos 5 personagens
```

- Vale **0 no canônico**, e é **exato**: depende só dos genes, não de simulação.
- **Dividir pela amplitude**, e não pelo limite superior: na vida (250 a 450), afastar-se 162 pontos é
  percorrer 81% do intervalo, mas só 36% do máximo. Só com a amplitude a ordem dos elencos pelo desvio
  concorda com a do validador.
- **Peso 3** nos genes definidores: ampliou a separação entre elencos de identidade diferente de 0,017
  para 0,043 unidades de desvio. Pesos maiores ampliariam pouco e tornariam quase gratuitos os demais
  genes.
- **Pesos reescalados para a soma canônica** antes da comparação, porque a escala não muda o combate.
  Sem isso, 7,5% do desvio de um elenco evoluído era cobrança por uma diferença sem efeito.
- Também barra a solução trivial: cinco cópias do mesmo personagem são simétricas, mas quatro delas
  estão longe do próprio perfil.

**Conta ilustrativa.** Um elenco igual ao canônico, exceto pelo alcance do Zoner, de 18 para 13:
`e = (13 − 18) / 15 = −0,333`. O alcance é definidor do Zoner (peso 3), e o Zoner tem 3 genes
definidores, então `Σω = 3×3 + 8×1 = 17`. `δ_Zoner = √(3 × 0,111 / 17) = 0,140`. Os outros quatro
estão em zero, e `P_drift = 0,140 / 5 = 0,028`.

### 6.2 Desequilíbrio (`P_dom`, vermelho nos slides)

Equilíbrio, aqui, **não** é cada par em 50%. Esse equilíbrio "plano" impediria qualquer ciclo de
vantagens. Equilíbrio é **nenhum arquétipo dominar o elenco**: um personagem com 50% no total pode
vencer dois confrontos e perder dois.

```
P_dom = 1,0 × global + 0,5 × counter + 0,5 × decisividade        (de 0 a 2)
```

| Termo | O que mede | O que barra |
|---|---|---|
| **global** (primário) | raiz da média dos quadrados, nos 5 personagens, de `|WR_global − 0,5| / 0,5` | um personagem dominar o elenco |
| **counter** (secundário) | raiz da média dos quadrados, nos 10 pares, do **excesso** de `|WR_par − 0,5|` acima de 0,15 | confrontos esmagadores (acima de 65%), compensados em outros pares |
| **decisividade** (secundário) | nos 10 pares, quanto `D` sai da faixa [0,02; 0,20] | pares em que os lados se alternam em massacres (55% de vitórias folgadas de um lado e 45% do outro dão ~50%, com lutas muito decididas) |

- Os três são **cegos à direção**: usam `|p − 0,5|` e `|s − 0,5|`, e nada diz qual lado deveria vencer.
- **Leitura do termo global em pontos percentuais:** global × 50 = afastamento médio (RMS) da taxa
  global em relação a 50%. O AG escalar tem global 0,032 → 1,6 ponto percentual.
- **Por que 0,15 (65%) na tolerância de counter.** As tabelas de confronto do gênero são escritas como
  5-5, 6-4, 7-3, 8-2. Na leitura da comunidade, 6-4 é vantagem saudável e 7-3 já é counter. A
  tolerância precisa admitir 0,10 (6-4), barrar 0,20 (7-3) e não coincidir com um ponto da grade, onde
  o ruído reprovaria um valor legítimo metade das vezes. Com 150 lutas:

  | Tolerância | Limiar | 6-4 verdadeiro acusado | 7-3 verdadeiro detectado |
  |---|---|---|---|
  | 0,10 | 60% | 50,0% | 99,6% |
  | **0,15** | **65%** | **10,6%** | **90,9%** |
  | 0,20 | 70% | 0,6% | 50,0% |

- **Teto da decisividade (0,20)**: `D > 0,20` = o vencedor termina, em média, com mais de 40% da vida.
  Disparou em 57 dos 180 pares numa medição com 18 elencos de referência.
- **Piso da decisividade (0,02)**: só uma guarda contra elencos degenerados (lutas que não se decidem).
  Fica acima de um elenco construído para isso (`D ≤ 0,008`) e abaixo de qualquer par de personagens
  distintos. Dos espelhos, só o do Zoner cai abaixo dele.
- **Os termos secundários são necessários, e isso foi medido.** Sem os dois, a busca chegou ao menor
  termo global de todas as configurações, mas transformou 8,6 dos 10 pares em hard counters. Sem a
  decisividade, os hard counters foram de 0,4 para 2,6. Eles valem zero no elenco final justamente
  porque funcionaram.

### 6.3 As duas formulações

```
AG escalar:  F = −(λ_drift · P_drift + λ_dom · P_dom),   λ_drift = λ_dom = 1   (maximiza F)
NSGA-II:     minimiza o vetor (P_dom, P_drift), sem pesos
```

- Os **mesmos dois termos** nos dois algoritmos, então a comparação não confunde método com objetivo.
- **Só a razão λ_drift/λ_dom importa**, porque o torneio é ordinal (só compara quem é melhor).
- **λ = 1 é o joelho** de uma varredura (seção 9.6): até 1, o desequilíbrio fica estável (0,041 a 0,044
  com λ de 0,25, 0,5 e 1) e a identidade melhora; acima, o desequilíbrio dispara (0,183 com λ = 2 e
  0,356 com λ = 4).

### 6.4 O que a busca otimiza e o que só é medido depois

| Grandeza | Na aptidão? |
|---|---|
| Desvio ponderado (`P_drift`) | sim |
| Desequilíbrio global, hard counters, decisividade (`P_dom`) | sim |
| Cada par exatamente em 50% | não |
| Identidade funcional (Camada 3, τ) | não, *post hoc* |
| Ciclo de vantagens | não, *post hoc* |
| Robustez a regras novas | não, *post hoc* |

---

## 7. O ruído da avaliação

`P_dom` é estimado a partir de lutas sorteadas; só `P_drift` é exato. Em 30 sorteios diferentes, o
`P_dom` de um mesmo elenco evoluído varia com desvio-padrão de **0,017** a 150 lutas por par, da mesma
ordem do próprio `P_dom` desses elencos. Isso é central para a QP3.

### 7.1 Números aleatórios comuns (CRN) dentro da geração

Todos os indivíduos de uma geração são avaliados **com os mesmos sorteios**: é dar a mesma prova a
todos os candidatos. Cada luta tem semente própria, derivada da geração, do par e do número da luta.
Assim, a luta 37 de Zoner × Rushdown usa os mesmos sorteios em todos os indivíduos, e pares sem
personagem alterado saem idênticos. O ruído não some: um gene que muda uma luta faz o resto dela se
desenrolar de outro jeito. Num elenco com um gene deslocado, a diferença de aptidão entre as duas
versões ainda varia com desvio-padrão de 0,013 a 0,028.

### 7.2 Stream novo a cada geração

A geração `g` da execução de semente `r` usa a semente-base `1000·r + g`. Sem essa rotação, a população
se ajustava a uma única sequência de sorteios ("decorava o gabarito"). Com ela, a razão entre o
desequilíbrio dentro do laço e o de sorteios novos caiu de 4,14 para 2,20.

Dois custos:
- Os sobreviventes de cada geração, inclusive a elite, são reavaliados no stream novo.
- A "melhor aptidão já vista" deixa de fazer sentido (seria o máximo de valores ruidosos, que sobe por
  sorte). Por isso **não há critério de parada por estagnação**.

### 7.3 Viés de seleção: por que o número "dentro do laço" é otimista

O elenco devolvido foi escolhido **porque** teve boa avaliação, e parte dela é sorte. Selecionar o
máximo de estimativas ruidosas dá um valor puxado para o lado bom. Por isso o trabalho reporta os
elencos **reavaliados** (seção 9.3), e a razão entre o laço e a reavaliação aparece como resultado:
1,80 no AG escalar (0,017 no laço → 0,0355 reavaliado).

---

## 8. Os três algoritmos

Os três usam a mesma representação, o mesmo combate, a mesma avaliação, os mesmos operadores e o mesmo
orçamento: **300 elencos, 150 gerações**. O NSGA-II também é um algoritmo genético; "AG escalar"
quer dizer o algoritmo de um objetivo só, a soma ponderada.

### 8.1 AG escalar

| Etapa | Como é |
|---|---|
| Inicialização | o canônico + 299 elencos sorteados nos limites |
| Seleção | torneio de 3: cada pai é o melhor de 3 sorteados |
| Cruzamento | **por bloco de personagem**: cada um dos 5 personagens do filho vem inteiro de um pai ou do outro (probabilidade 1/2) |
| Mutação | cada gene muda com probabilidade 0,05 (cerca de 2,75 dos 55 genes por filho), por perturbação gaussiana com desvio de **10% da amplitude nos atributos** e **2,5% nos pesos** |
| Elitismo | os 10% melhores (30 elencos) passam sem mudança |
| Orçamento | sempre 150 gerações |
| Saída | o melhor elenco da última geração e a geração de convergência |

- **Bloco de personagem**: capacidade e estratégia de um personagem são herdadas juntas. O custo é que
  a recombinação dentro de um personagem fica só por conta da mutação.
- **Mutação dos pesos 4× menor**: para dar inércia à estratégia. Esse é o custo descoberto na QP2
  (seção 13.2).
- **A semente canônica.** Com desvio zero, o canônico (`F ≈ −1,28`) fica sempre na elite da geração 0:
  entre os 11 melhores de 300 nas 20 execuções, posição mediana 5, o melhor de todos em uma (semente
  55). Na semente 42, ele sai da população na **geração 3**, assim que surgem elencos mais
  equilibrados. O efeito de ele existir só no AG é medido pelo controle sem semente.

**Convergência é um evento registrado, não um critério de parada.** Um elenco está **equilibrado**
quando:

```
todo personagem tem taxa global entre 40% e 60%   (ε = 0,10)
e nenhum par passa de 65%                          (κ = 0,15)
```

A **geração de convergência** é a primeira em que o melhor elenco satisfaz isso **duas vezes**:
dentro do laço e numa reavaliação com 200 lutas por par num stream que a busca nunca viu (inédito a
cada geração). Parar mais cedo confundiria "achou melhor" com "gastou menos"; e o NSGA-II não pode
parar por esse critério, porque "está equilibrado?" não é uma pergunta que se faça a uma fronteira.

### 8.2 NSGA-II

Os conceitos que a banca pode perguntar:

- **Dominância de Pareto.** O elenco A domina o B se A é melhor ou igual nos dois objetivos e
  estritamente melhor em pelo menos um. O NSGA-II só descarta um elenco se houver outro melhor nos
  dois ao mesmo tempo.
- **Ordenação não dominada.** A população é dividida em frentes: a frente 1 tem os elencos que
  ninguém domina; a frente 2, os que só a frente 1 domina; e assim por diante.
- **Distância de aglomeração.** Dentro de uma frente, mede quão isolado é cada ponto em relação aos
  vizinhos. Os extremos da frente recebem distância infinita. Prefere-se o mais isolado, para a
  fronteira ficar espalhada.
- **Seleção dos pais**: torneio binário decidido pela frente e, no empate, pela aglomeração.
- **Sobrevivência**: junta pais e filhos (600), e a próxima geração recebe as frentes inteiras, em
  ordem, até completar 300; a última frente que cabe só em parte é completada pelos mais isolados.

Diferenças em relação ao AG escalar:
- **População inicial inteiramente sorteada.** O canônico tem desvio zero, então ninguém pode
  dominá-lo: ele e a vizinhança ficariam para sempre na frente 1, por mais desequilibrados que fossem.
  Numa execução de teste com a semente, 40 dos 78 pontos da fronteira final tinham `P_dom ≥ 1`.
- **O dobro de avaliações.** Pais e filhos são comparados no mesmo conjunto, e objetivos medidos em
  streams diferentes não são comparáveis, então os pais são reavaliados a cada geração. O orçamento é
  igualado pelo número de **filhos** por geração. Uma execução do AG simula cerca de 68 milhões de
  lutas; uma do NSGA-II, cerca de 135 milhões.
- **Saída: uma fronteira**, não um elenco. Para comparar, extraem-se **5 representantes**:

| Representante | Como é escolhido |
|---|---|
| best_drift | o extremo de menor desvio |
| best_dominance | o extremo de menor desequilíbrio |
| knee_point | o "joelho": maior distância perpendicular à reta entre os dois extremos |
| ideal_point | o mais próximo do ponto utópico (o melhor valor de cada objetivo) |
| **scalar_optimum** | o que minimiza a própria função do AG escalar, `P_dom + P_drift` |

- O joelho e o ideal usam objetivos normalizados pela amplitude da fronteira; em unidades cruas, a
  escala do desequilíbrio (até 2) decidiria a geometria. A normalização mudou o ideal em 19 de 20
  fronteiras.
- O **scalar_optimum** é o da comparação principal, escolhido **antes** da bateria: é o ponto da
  fronteira que responde à mesma pergunta que o AG escalar. Comparar com o best_dominance mediria a
  escolha do ponto, que perde identidade por construção; ele fica como comparação secundária.

### 8.3 Híbrido

- **75 gerações de NSGA-II + 75 de AG escalar**, no mesmo orçamento. A fronteira final da primeira
  fase entra inteira na população inicial do AG, completada por sorteados. Devolve um elenco.
- A fase escalar continua a rotação de streams de onde a de Pareto parou. A convergência é contada na
  escala da execução inteira: convergir na geração 3 da fase escalar é convergir na 78.
- **Motivação**: no NSGA-II, o elenco de menor desvio nunca é descartado (está na frente 1 com
  aglomeração infinita), e o desvio não compete com o ruído do desequilíbrio. A fase de Pareto
  preserva as linhagens fiéis ao canônico; a escalar refina o equilíbrio. O nome técnico é
  **multiobjetivização** (Knowles et al., 2001).
- **A divisão 0,5 não foi otimizada.** O critério de escolha foi escrito antes da varredura, mas, no
  orçamento reduzido, nenhuma configuração passou no filtro de equilíbrio, e a escolha caiu no
  desempate por simplicidade. Nesse orçamento, inclusive, ela preservou **menos** identidade que o AG
  escalar (desvio 0,255 contra 0,234). O efeito só apareceu no orçamento da bateria.

---

## 9. O protocolo: o que está sendo comparado

### 9.1 Os braços

| Braço | O que é | Para que serve |
|---|---|---|
| **AG escalar** | a configuração principal | o algoritmo que a pergunta testa |
| **NSGA-II** | o algoritmo de comparação | QP3; entra pelo scalar_optimum e, secundariamente, pelo best_dominance |
| **Controle λ = 0** | o AG escalar sem o termo de desvio | **o contrafactual da QP2**: equilibrar sem pagar pela identidade |
| **Controle sem semente** | o AG escalar com população inicial toda sorteada, como a do NSGA-II | separar "algoritmo" de "inicialização" |
| **Híbrido** | 75 gerações de NSGA-II + 75 de AG escalar | contribuição de método |

Todos: 20 execuções (sementes 42 a 61), 300 elencos, 150 gerações.

### 9.2 Pareamento

A semente fixa **tudo** o que é aleatório numa execução: a população inicial, os sorteios do
cruzamento e da mutação e o stream de cada geração. A execução de semente 42 do AG e a de semente 42 do
controle formam um **bloco**, não duas amostras independentes. Por isso o teste é **pareado**
(seção 11.2).

### 9.3 Os níveis de medição

Esta é a tabela que mais ajuda a não confundir números:

| Nível | Lutas por par | Sorteios | Para que serve |
|---|---|---|---|
| Dentro do laço | 150 | o stream da última geração | seleção; a figura da fronteira; a relação de Pareto por semente |
| Confirmação | 200 | stream inédito, novo a cada geração | o evento de convergência |
| **Reavaliação** | **1.000** | **semente 9999, comum a todas as execuções de todos os braços** | **todas as métricas de equilíbrio dos testes** |
| Perfil comportamental | 200 | semente 9999 | Camada 3 e τ |
| Validação externa | 5.000 (10 × 500) | sementes 10.000 a 10.009 | replicação e robustez (elencos da semente 42) |
| Teste do ciclo | 16.000 (16 × 1.000) | 16 streams próprios | ciclo e tríades |
| Sensibilidade | 200 | sementes próprias | o quanto cada gene move a vitória |

A semente comum na reavaliação faz as diferenças entre execuções refletirem os **elencos**, e não os
sorteios da medição. Cada uso de números aleatórios tem a sua família de sementes, e as famílias não
se sobrepõem.

**Por que 1.000 e não 150 na reavaliação.** Em elencos do AG (sementes 42 a 44), o `P_dom` de um mesmo
elenco varia com desvio-padrão de 0,017 a 150 lutas e de 0,006 a 1.000. E há **viés**: como `P_dom`
usa `|p − 0,5|`, o ruído o empurra para cima (média 0,050 a 150 lutas, 0,038 a 1.000). Uma medição
grosseira subestima o equilíbrio, mais ainda nos elencos mais equilibrados.

### 9.4 As comparações

**Testes formais** (Wilcoxon pareado + Â₁₂ + Holm), sempre o AG escalar contra outro braço:

| Comparação | Responde a | Resultado em uma linha |
|---|---|---|
| AG × NSGA-II (scalar_optimum) | QP3, comparação principal | AG vence as 2 de equilíbrio; NSGA-II vence as 4 de identidade; todas com efeito grande |
| AG × NSGA-II (best_dominance) | QP3, robustez da escolha do ponto | mesmas 6 direções e significância, efeitos um pouco menores no equilíbrio |
| **AG × controle λ = 0** | **QP2** | AG vence as 4 de identidade com efeito grande; equilíbrio não separa (p de Holm 0,059) |
| AG × controle sem semente | a semente explica a diferença com o NSGA-II? | só o desvio separa (0,2703 contra 0,2473); não explica |
| AG × híbrido | contribuição de método | híbrido vence as 4 de identidade; equilíbrio idêntico (p de Holm 1,00) |

**Leituras descritivas** (fora dos testes, para não encarecer a correção):
- A **decomposição** de `P_dom` nos três termos: mostra se a diferença vem de desequilíbrio global ou
  de counters.
- A **relação de Pareto por semente**: o ponto do AG contra a fronteira **inteira** do NSGA-II da mesma
  semente, ambos dentro do laço. Domina algum ponto, é dominado, ou nenhum dos dois. Não depende da
  escolha de representante.
- A **soma `P_dom + P_drift`**: o AG está no ótimo da própria função?
- O **híbrido contra o NSGA-II**: só descritivo, porque a família opõe o AG a cada braço, sem comparar
  os outros braços entre si.

**Contra referências** (não são controles do método):
- **Modelos nulos** (seção 10.6): o que é acaso em cada métrica.
- **Validação externa**: 4 elencos da semente 42 (AG, scalar_optimum, joelho e canônico).
- **Teste do ciclo**: cada grupo contra o acaso (binomial) e contra 30 elencos aleatórios.
- **Sensibilidade**: cada gene contra um piso de ruído medido.

### 9.5 Por que o controle λ = 0, e não os nulos, é a evidência da QP2

- Os **nulos** dizem o que é acaso numa métrica, mas não são otimizados. Superá-los no desvio é
  garantido a qualquer busca que tenha o desvio na aptidão.
- O **controle** é a mesma busca, com a mesma amostra e o mesmo orçamento, sem o termo. A diferença
  entre ele e o AG isola o efeito do termo.

### 9.6 As varreduras de calibração (antes da bateria)

Em orçamento reduzido (população 120, 60 gerações, sementes 1000 a 1004, disjuntas das da bateria),
mudando um parâmetro por vez:

| Braço | `P_dom` | global | Hard counters | Equilibrados | Desvio | τ |
|---|---|---|---|---|---|---|
| **Adotada** (λ = 1; pesos 1/0,5/0,5; elitismo 10%; torneio 3) | 0,042 | 0,040 | 0,4 | 3/5 | 0,245 | 0,42 |
| λ = 0,25 | 0,041 | 0,032 | 1,2 | 2/5 | 0,377 | 0,02 |
| λ = 0,5 | 0,044 | 0,039 | 0,4 | 3/5 | 0,346 | −0,05 |
| λ = 2 | 0,183 | 0,042 | 4,2 | 1/5 | 0,139 | 0,60 |
| λ = 4 | 0,356 | 0,069 | 7,8 | 0/5 | 0,090 | 0,72 |
| pesos 1/0/0 | – | 0,023 | 8,6 | 0/5 | 0,156 | 0,53 |
| pesos 1/0,5/0 | – | 0,031 | 2,6 | 1/5 | 0,248 | 0,30 |
| pesos 1/1/1 | – | 0,030 | 0,0 | 5/5 | 0,301 | 0,11 |
| pesos 1/2/0,5 | – | 0,041 | 0,0 | 5/5 | 0,348 | 0,16 |
| torneio 2 | 0,040 | 0,040 | 0,2 | 4/5 | 0,264 | 0,36 |

Leituras:
- **λ**: até 1, o equilíbrio não melhora com λ menor e o τ cai ao acaso; acima de 1, a identidade
  melhora e o equilíbrio desaba. λ = 1 é o joelho.
- **Pesos de `P_dom`**: pesos secundários maiores zeram os hard counters, mas pagam em identidade; a
  repartição 0,5/0,5 fica onde eles já sustentam o equilíbrio sem dominar a identidade.
- **Elitismo e torneio**: nenhuma alternativa domina a adotada (o torneio 2 tem menos counters e mais
  equilibrados, mas paga em desvio e τ). A afirmação é "testados, nada os supera em tudo", não
  "ótimos".
- **Ressalvas**: 5 sementes só ordenam, não declaram vencedores; e o orçamento reduzido não se
  transfere (a ordem entre AG e NSGA-II se inverte com população 120). Por isso nenhuma comparação
  entre algoritmos é feita nesse orçamento.

---

## 10. As métricas, uma a uma

### 10.1 Métricas de equilíbrio

| Métrica | O que mede | Escala | Leitura |
|---|---|---|---|
| `P_dom` | desequilíbrio composto (seção 6.2) | 0 a 2; **menor é melhor** | canônico 1,28; AG 0,0355; espelhos 0,033 |
| termo global | afastamento dos personagens de 50% no total | 0 a 1; ×50 = pontos percentuais | AG 0,032 (1,6 pp); espelhos 0,014 (0,7 pp, puro ruído) |
| termo de counter | excesso dos pares além de 65% | 0 a 1 | AG 0,0032; NSGA-II 0,0736 (20× maior) |
| Hard counters | número de pares além de 65% | 0 a 10; menor é melhor | AG 0,20 por elenco (média); NSGA-II 2,80 |
| Personagens em banda | personagens com taxa global entre 40% e 60% | 0 a 5 | 5/5 em todas as execuções de todos os braços; por isso saiu dos testes |
| Elenco equilibrado | o predicado da seção 8.1 | sim/não | AG 16/20; NSGA-II 0/20 |
| Geração de convergência | primeira geração com o predicado confirmado | 0 a 149 | AG 31,3 ± 13,2; híbrido 98,3 ± 20,2 |
| Razão laço/reavaliação | `P_dom` reavaliado ÷ `P_dom` no laço | ≥ 1 | mede quanto da seleção foi sorte (seção 13.3) |

### 10.2 Identidade estrutural (os genes)

| Métrica | O que mede | Escala | Leitura |
|---|---|---|---|
| `P_drift` | distância ponderada ao canônico (seção 6.1) | 0 = canônico; **menor é melhor** | AG 0,2473; NSGA-II 0,1445; sorteados 0,415 |
| Validador, Camada 1 | 13 asserções: quem lidera o elenco em cada gene definidor | 0 a 13 | |
| Validador, Camada 2 | 5 asserções: relações entre genes do mesmo personagem | 0 a 5 | |

As Camadas 1 e 2 são reportadas juntas (0 a 18). São **parcialmente endógenas**: medem o mesmo eixo que
o termo de desvio otimiza, então ir bem nelas reflete, em parte, o termo funcionando.

### 10.3 O validador de identidade (23 asserções)

| Camada | Arquétipo | Asserção |
|---|---|---|
| **1** genes, entre personagens (13) | Rushdown | maior velocidade; menor intervalo entre golpes; maior probabilidade de FRENTE |
| | Zoner | maior alcance; maior repulsão; maior probabilidade de RECUAR |
| | Combo Master | maior atordoamento |
| | Grappler | maior dano; maior agarrão |
| | Turtle | menor velocidade; maior intervalo; mais vida; maior probabilidade de GUARDA |
| **2** genes, no mesmo personagem (5) | Zoner | alcance maior que velocidade |
| | Rushdown | velocidade maior que alcance |
| | Grappler | vida maior que velocidade |
| | Combo Master | atordoamento maior que repulsão; velocidade maior que alcance |
| **3** comportamento (5) | Zoner | maior distância média de luta |
| | Rushdown | mais golpes conectados por luta |
| | Turtle | maior fração de defesa escolhida |
| | Combo Master | maior atordoamento infligido |
| | Grappler | maior dano arrancado através da guarda |

Na Camada 2, os genes são comparados normalizados pela amplitude dos limites.

Duas regras impedem identidade de graça:
- **Empate conta contra.** "O maior" tem de ser estritamente o maior. Sem a regra, cinco cópias
  idênticas passavam em 4 das 13 asserções da Camada 1 só pela ordem no elenco.
- **Pesos lidos como probabilidades de intenção**, porque a escala dos pesos não muda o combate.

Cada asserção vale um bit (ficar em segundo por pouco vale o mesmo que ficar em último), e a Camada 3
tem só 5 bits. Por isso existe uma métrica funcional contínua, a τ.

### 10.4 Identidade funcional (o comportamento)

**O perfil comportamental** de um personagem tem 10 métricas, medidas sub-tick a sub-tick e com média
nos seus 4 confrontos (200 lutas por par, semente 9999):

| Métrica | Definição |
|---|---|
| Avanço, recuo | fração dos sub-ticks ativos em avanço e em recuo |
| Defesa escolhida | fração em defesa por intenção GUARDA |
| Defesa forçada | fração em defesa por falta de espaço para recuar |
| Fora de alcance | fração da luta em que age sem alcançar o oponente |
| Atordoado | fração da luta atordoado |
| Golpes conectados | golpes que acertam, por luta |
| Distância média | distância média entre os lutadores |
| Atordoamento infligido | sub-ticks de atordoamento aplicados, por luta |
| Quebra de guarda | dano extra arrancado pelo agarrão através da guarda, por luta |

**Camada 3** = as 5 asserções de comportamento acima (0 a 5).

**Concordância τ** (Kendall τ-b): para cada uma das 10 métricas, compara-se a **ordem** dos 5
personagens no canônico com a ordem no elenco medido; τ é a média das 10.

- Com 5 personagens há 10 pares de personagens. Para cada par, a ordem dos dois é a mesma do canônico
  (concordante) ou invertida (discordante). Sem empates, `τ = (concordantes − discordantes) / 10`.
  O τ-b é a versão corrigida para empates.
- **Conta ilustrativa:** se o elenco mantém a ordem canônica numa métrica, exceto por dois personagens
  vizinhos trocados, são 9 pares concordantes e 1 discordante: τ = (9 − 1) / 10 = 0,8.
- **1** = ordem canônica em todas as métricas; **0** = sem relação (acaso); **−1** = ordem invertida.
- O canônico é medido nas mesmas condições do elenco (mesmo número de lutas, mesma semente). Como é uma
  medida de ordem, um deslocamento comum a todos (lutas mais longas, por exemplo) não conta como perda.
- **200 lutas por par, escolhido por reteste**: medida 3 vezes no mesmo elenco com sementes
  diferentes, variou de 0,19 a 0,28 com 120 lutas e de 0,23 a 0,24 com 200.

**Held-out, mas não independente.** Nenhum termo da aptidão fala de comportamento, então essas
métricas ficam de fora da otimização. Mas cada asserção comportamental é consequência quase direta de
um gene definidor (o atordoamento infligido vem do gene de atordoamento, a quebra de guarda vem do
agarrão). Um elenco pode manter o gene e perder o comportamento; o contrário é improvável.

### 10.5 Diferenciação (só descritiva)

Distância média entre os 10 pares de personagens de um elenco (8 atributos normalizados + 3
probabilidades). Vale 0 em cinco cópias. **Não serve como evidência de homogeneização**: elencos
sorteados são bem diferenciados sem ter identidade alguma, e o controle λ = 0 (1,16) fica **acima** do
AG escalar (1,09). Valores: canônico 1,35; sorteados 1,20; AG 1,09; híbrido 1,20; NSGA-II 1,22.

### 10.6 Modelos nulos, posição e p empírico

**35 elencos sem otimização:**
- **5 espelhos**: cinco cópias do perfil canônico de um arquétipo. São a **solução trivial** do
  equilíbrio (simétricos, sem identidade) e servem de teto de equilíbrio.
- **30 aleatórios**: sorteados nos limites. Nem equilibrados, nem com identidade: o piso.

| Elenco | `P_dom` | Desvio | Genes (de 18) | Comport. (de 5) | τ | Diferenciação |
|---|---|---|---|---|---|---|
| Canônico | 1,28 | 0 | 18 | 5 | 1 | 1,35 |
| Espelhos (média) | 0,033 | 0,377 | 2,6 | 0,6 | −0,18 | 0 |
| Aleatórios (média) | 1,33 | 0,415 | 5,4 | 1,0 | −0,02 | 1,20 |
| Aleatórios (melhor em cada coluna) | 1,05 | 0,327 | 9 | 3 | 0,32 | – |

Lições da tabela:
- **Nenhuma métrica de identidade tem piso zero.** O acaso já dá cerca de 6 das 23 asserções (a média
  dos 35 nulos; 6,5 só nos aleatórios), e o melhor nulo chega a 10.
- **Nem a simetria tem `P_dom` zero.** O espelho do Zoner vale 0,106, dos quais 0,085 vêm do piso de
  decisividade (lutas apertadas demais, não desequilíbrio). Os outros quatro espelhos ficam entre 0,011
  e 0,025. O termo global médio dos espelhos (0,014) é o que o ruído produz num elenco perfeitamente
  simétrico, e é contra ele que se lê o equilíbrio global.

**Posição** = `(valor − piso) / (teto − piso)`, com o piso na média dos 35 nulos e o teto no canônico
(identidade) ou na média dos espelhos (`P_dom`). **p empírico** = fração dos 35 nulos que igualam ou
superam o valor (resolução 1/35 ≈ 0,03).

Cuidado com a posição de `P_dom`: o AG escalar dá 100%, mas só porque o piso (1,14) está muito longe.
Pelo termo global, ele fica **perto** da simetria (1,6 pp contra 0,7 pp de ruído), **sem alcançá-la**.

### 10.7 Qualidade da fronteira

- **Hipervolume**: a área do espaço de objetivos dominada pela fronteira, limitada por um ponto de
  referência. Mede ao mesmo tempo proximidade do ótimo e extensão; **maior é melhor**. A referência
  (1,3; 0,4) vem dos nulos (`P_dom` perto do canônico, desvio perto dos espelhos). Com a referência
  nos máximos teóricos (2; 1), o hipervolume ocupava 90% da área em qualquer fronteira e não
  distinguia uma da outra. Valor: 0,395 ± 0,011.
- **Espaçamento** (Schott): desvio-padrão das distâncias de cada ponto ao vizinho mais próximo; **menor
  = mais uniforme**. Valor: 0,012 ± 0,003.

### 10.8 Estrutura de vantagens

- **Aresta decidida**: o par se afasta de 50% por mais de 2 desvios-padrão (com 16.000 lutas, o
  desvio-padrão é ~0,004).
- **Aresta mantida**: decidida **na direção** do ciclo proposto. Arestas indecisas ficam fora: seriam
  ruído nos dois sentidos.
- Compara-se a **taxa** mantidas/decididas, não a contagem: um elenco aleatório decide quase tudo, e um
  equilibrado decide menos; a contagem crua puniria o equilibrado.
- **Tríades circulares**: trios em que A vence B, B vence C e C vence A. 0 numa hierarquia estrita, 2,5
  em média num torneio sorteado, 5 no máximo (cada um vence 2 e perde 2). Só tem sentido com arestas
  decididas: os espelhos marcam 2,59 tríades com uma única aresta decidida.

### 10.9 Sensibilidade

Para cada gene de cada personagem do elenco do AG escalar (semente 42), desloca-se o gene numa janela
de **2 desvios de mutação** e mede-se quanto a taxa global muda (média nos 5 personagens). O **piso de
ruído** é a mesma estatística com janela zero e sorteios diferentes (o maior de 3 repetições).
- **neutro**: não passa do piso;
- **limítrofe**: até 2× o piso;
- **visível**: acima disso.

Usa-se o elenco evoluído, e não o canônico, porque no canônico as taxas estão presas em 0% e 100% e
todo gene pareceria neutro. Se a janela passa de um limite, ela desliza para dentro, sem encolher.

---

## 11. A estatística: Wilson, Wilcoxon, Â₁₂, Holm

### 11.1 Intervalo de confiança de Wilson (validação externa)

**O problema.** Uma taxa de vitória medida (por exemplo, 32,7% em 5.000 lutas) é uma **estimativa**. Se
as lutas fossem refeitas com outros sorteios, sairia um número um pouco diferente. O intervalo de
confiança de 95% é a faixa de valores verdadeiros compatíveis com o que foi medido.

**Por que Wilson.** A fórmula "de livro" (Wald: `p̂ ± 1,96·√(p̂(1−p̂)/n)`) funciona mal perto de 0% e
100% e com poucas observações: com 0 vitórias em 10 lutas, ela dá o intervalo [0%; 0%], como se a
medida fosse exata. O intervalo de Wilson (1927) corrige isso e tem cobertura mais próxima dos 95%
prometidos. Com 0 em 10, ele dá cerca de [0%; 27,8%] (conta ilustrativa). Com 5.000 lutas e taxas no
meio da escala, os dois quase coincidem; Wilson é a escolha segura em geral.

A fórmula, com `z = 1,96`:

```
centro = (p̂ + z²/2n) / (1 + z²/n)
meia-largura = z / (1 + z²/n) · √( p̂(1 − p̂)/n + z²/4n² )
```

**Como o trabalho usa.** Em cada condição da validação externa (5.000 lutas por par), cada uma das 15
taxas (5 globais + 10 de par) recebe o seu intervalo e é classificada contra a sua faixa: [40%; 60%]
para as globais, [35%; 65%] para os pares.

| Classificação da taxa | Regra |
|---|---|
| **dentro** | o intervalo inteiro está dentro da faixa |
| **fora** | o intervalo inteiro está fora |
| **inconclusiva** | o intervalo cruza a borda |

| Veredito da condição | Regra |
|---|---|
| **robusto** | as 15 taxas dentro |
| **frágil** | alguma taxa fora |
| **inconclusivo** | nenhuma fora, mas alguma inconclusiva |

**Conta ilustrativa.** O par Rushdown × Combo Master do scalar_optimum, na replicação, ficou em 32,7%
com 5.000 lutas. O intervalo de Wilson vai de cerca de 31,4% a 34,0%: inteiro abaixo de 35%, portanto
**fora**, e a condição é **frágil**. Já um par a 35,5% teria intervalo de cerca de 34,2% a 36,8%,
cruzando a borda de 35%: **inconclusivo**.

**Por que essa regra, e não "falhou em alguma semente".** A regra antiga reprovava se o elenco falhasse
em qualquer uma das K sementes; quanto mais sementes, mais chance de uma falhar por ruído, e o
veredito ficava mais severo só por medir mais. Somar as 10 sementes numa amostra só (5.000 lutas) e
usar o intervalo faz mais amostra **estreitar** o intervalo, e não piorar o veredito.

### 11.2 Wilcoxon de postos sinalizados (o teste principal)

Usado para comparar dois braços, métrica por métrica.

1. Para cada semente (42 a 61), calcula-se a diferença entre os dois braços: `d_i = AG_i − outro_i`.
2. Descartam-se as diferenças **nulas** (não informam direção). Isso importa nos hard counters, em que
   muitas execuções dão 0 nos dois braços.
3. Ordenam-se as diferenças pelo valor absoluto e dá-se um posto a cada uma (1 para a menor).
4. Somam-se os postos das diferenças positivas e os das negativas. Se não houvesse diferença entre os
   braços, as duas somas seriam parecidas; o p-valor diz quão improvável é um desequilíbrio tão grande
   entre elas.

- **Bicaudal**: testa diferença nos dois sentidos.
- **Não paramétrico**: não supõe distribuição normal, só usa a ordem das diferenças. Adequado para
  métricas como contagem de asserções ou de counters.
- **Pareado** porque a execução `i` dos dois braços compartilha a semente.

### 11.3 Mann-Whitney U (reportado ao lado)

A versão **não pareada**: junta as 40 observações e compara os postos dos dois grupos. Foi o teste
principal na primeira bateria completa e deu lugar ao Wilcoxon quando se constatou que o desenho é
pareado. Ignorar o pareamento é conservador, não inválido. Continua reportado, sem correção, para
mostrar que nenhuma conclusão depende da troca: contra o scalar_optimum, dá p bruto menor que 0,004 nas
seis métricas.

### 11.4 Â₁₂ de Vargha-Delaney (o tamanho do efeito)

O p-valor diz se há diferença; o Â₁₂ diz **quão grande** ela é.

**Â₁₂ = probabilidade de uma execução do AG dar valor maior que uma do outro braço** (empates contam
meio). Calcula-se sobre todos os 20 × 20 pares possíveis.

- 0,5 = sem efeito.
- Magnitude por `|Â₁₂ − 0,5|`: desprezível abaixo de 0,06; pequeno até 0,14; médio até 0,21; grande
  acima.

**Como ler o sentido.** Â₁₂ sempre pergunta "o AG dá valor **maior**?". Quem é **melhor** depende da
métrica:

| Métrica | Melhor é | Â₁₂ baixo significa | Â₁₂ alto significa |
|---|---|---|---|
| `P_dom`, hard counters, desvio | menor | AG melhor | AG pior |
| Camadas 1-2, Camada 3, τ | maior | AG pior | AG melhor |

Exemplos da bateria:
- AG × NSGA-II, `P_dom`: Â₁₂ = 0,07 → em 93% dos confrontos entre execuções, o AG tem desequilíbrio
  **menor** → o AG é muito mais equilibrado (efeito grande).
- AG × NSGA-II, desvio: Â₁₂ = 1,00 → o AG tem desvio **maior** em todos os confrontos → separação
  completa a favor do NSGA-II.
- AG × λ = 0, τ: Â₁₂ = 0,87 → o AG tem τ maior em 87% → AG melhor (grande).
- AG × λ = 0, `P_dom`: Â₁₂ = 0,30 → o AG tende a ser mais equilibrado, com efeito **médio**
  (|0,30 − 0,5| = 0,20), mas sem significância depois de Holm.

### 11.5 Correção de Holm (múltiplas comparações)

**O problema.** Cada comparação testa 6 ou 7 métricas. Testando muitas vezes a 5%, aumenta a chance de
pelo menos um "falso positivo".

**O procedimento.** Com `m` p-valores:
1. Ordenam-se do menor para o maior.
2. O menor é multiplicado por `m`, o segundo por `m − 1`, ..., o maior por 1.
3. Garante-se que um p corrigido nunca é menor que o anterior (máximo acumulado), e nada passa de 1.

É menos conservador que Bonferroni (que multiplicaria todos por `m`) e controla a mesma taxa de erro.

**A família.** São **7 métricas fixadas antes da bateria**, as mesmas em todas as comparações: 3 de
equilíbrio (`P_dom`, hard counters, personagens em banda) e 4 de identidade (desvio, Camadas 1-2,
Camada 3, τ). Fixar antes impede escolher as métricas depois de ver os resultados. A única regra de
saída: se as 40 observações forem todas iguais, não há teste. Isso aconteceu com "personagens em
banda" (5/5 sempre), então **a família efetiva é 6**.

**O exemplo do controle λ = 0.** As 4 métricas de identidade têm os menores p brutos. `P_dom`, com p
bruto 0,030, é o 5º de 6, multiplicado por 2: ≈ 0,059, acima de 0,05. Os hard counters, o maior, ficam
em 0,18. É assim que uma diferença com p bruto de 0,03 não sobrevive à correção.

### 11.6 Outros testes que aparecem

- **Teste binomial** (ciclo): se o elenco não tivesse relação com o ciclo, cada aresta decidida
  seguiria a direção proposta com probabilidade 1/2. 105 de 186 (56,5%) dá p = 0,091: não se distingue
  de 50%.
- **Mann-Whitney + Â₁₂ contra os aleatórios** (ciclo): taxa de arestas mantidas do AG contra a dos 30
  aleatórios: p = 0,128, Â₁₂ = 0,63.
- **p empírico** contra os 35 nulos (seção 10.6).

### 11.7 Por que 20 execuções e por que medianas

- **Poder.** Uma simulação (4.000 réplicas) mostrou que, para um efeito grande (Â₁₂ = 0,80), 20
  execuções por braço detectam o efeito com probabilidade de 85,9%; 10 execuções, só 44,4%. A
  simulação foi feita com o teste não pareado e família de 3 métricas; o pareado tende a ter mais
  poder e a família de 7 corrige mais, então o número é ordem de grandeza.
- **Medianas**: os testes trabalham com postos, e a mediana é a estatística coerente com eles; também
  é menos sensível a uma execução atípica. Exceção: hard counters aparecem em **média** por execução
  (a mediana é 0 contra 3, a média 0,20 contra 2,80).

---

## 12. Os resultados, por questão

Salvo aviso, os valores são **medianas das 20 execuções**, e as métricas de equilíbrio vêm da
**reavaliação com 1.000 lutas por par**.

### 12.1 O ponto de partida: o canônico

Uma **hierarquia**: o Rushdown vence praticamente todas as lutas, o Turtle não vence nenhuma, e 9 dos
10 pares são hard counters decididos em mais de 99% das lutas. A única aresta moderada é Zoner ×
Grappler (63%). `P_dom` = 1,28, no nível de um elenco sorteado. Identidade máxima por construção:
desvio 0, 23/23 asserções, τ = 1.

### 12.2 QP1: equilíbrio

**Convergência.** 20/20 execuções do AG convergem, na geração 31,3 ± 13,2 (entre 13 e 56). O
desequilíbrio do melhor elenco cai de 0,68 (geração 0) para 0,030 (geração 30), na mediana, e depois
oscila num patamar. O desvio cai de ~0,4 para 0,29 na geração 30 e depois declina devagar até 0,25.

**A confirmação importou.** Das 70 vezes em que o melhor elenco pareceu equilibrado dentro do laço, 50
não sobreviveram à reavaliação em sorteios inéditos (71% recusados). "Convergir" marca o **primeiro**
sucesso confirmado de um teste repetido a cada geração, não um estado estável. Por isso se reporta
também quantos **terminam** equilibrados: 16/20.

**Equilíbrio reavaliado:**

| Braço | `P_dom` [quartis] | global | counter | Hard counters | Equilibrados |
|---|---|---|---|---|---|
| AG escalar | 0,0355 [0,0252; 0,0418] | 0,0318 | 0,0032 | 0,20 | 16/20 |
| Híbrido | 0,0287 [0,0229; 0,0437] | 0,0287 | 0,0042 | 0,25 | 16/20 |
| NSGA-II (scalar_optimum) | 0,0759 [0,0492; 0,1031] | 0,0385 | 0,0736 | 2,80 | 0/20 |
| NSGA-II (best_dominance) | 0,0551 [0,0402; 0,0708] | 0,0378 | 0,0467 | 2,05 | 4/20 |
| Controle λ = 0 | 0,0432 [0,0303; 0,0524] | 0,0432 | 0,0000 | 0,05 | 19/20 |
| Controle sem semente | 0,0264 [0,0183; 0,0481] | 0,0264 | 0,0016 | 0,10 | 18/20 |

Leituras:
- **Todos os personagens** de todas as execuções de todos os braços ficam entre 40% e 60% no total. O
  equilíbrio global não discrimina os métodos; **os pares** discriminam.
- O NSGA-II equilibra os personagens globalmente quase tanto quanto o AG (global 0,0385 contra
  0,0318), mas o termo de counter é 20× maior: sobram pares desequilibrados.
- Na média das 20 execuções do AG, todos os pares ficam entre 46% e 54%. Em execuções individuais, só
  dois pares passaram de 65%, cada um em 2 de 20 execuções: Zoner × Turtle e Rushdown × Combo Master.
- Repare que o controle λ = 0 termina equilibrado **mais vezes** (19/20) e tem `P_dom` mediano
  **maior** (0,0432). E o controle sem semente tem o menor `P_dom` (0,0264). Nenhuma dessas diferenças
  é significativa contra o AG (seção 12.3).

**Fora do laço** (elencos da semente 42; veredito e `P_dom` sobre 5.000 lutas por par):

| Condição | AG escalar | NSGA-II scalar_opt. | NSGA-II joelho | Canônico |
|---|---|---|---|---|
| Replicação (regras do treino) | R 0,033 | F 0,051 | F 0,400 | F 1,277 |
| Distância inicial 40 | R 0,025 | F 0,068 | F 0,394 | F 1,277 |
| Distância inicial 60 | R 0,040 | F 0,045 | F 0,396 | F 1,278 |
| Campo 80 | **F** 0,087 | F 0,143 | F 0,470 | F 1,297 |
| Campo 120 | R 0,033 | F 0,160 | F 0,407 | F 1,272 |
| Persistência 4 | I 0,110 | F 0,273 | F 0,440 | F 1,283 |
| Persistência 6 | **F** 0,153 | F 0,230 | F 0,441 | F 1,271 |
| Guarda 0,55 | I 0,075 | F 0,108 | F 0,397 | F 1,277 |
| Guarda 0,65 | R 0,061 | F 0,063 | F 0,444 | F 1,278 |

(R robusto, I inconclusivo, F frágil.)

- **Replicação**: só o AG replica (`P_dom` 0,033 fora do laço contra 0,025 dentro). O scalar_optimum
  falha por um par (Rushdown × Combo Master em 32,7%).
- **Robustez do AG**: 4 robustas, 2 inconclusivas, 2 frágeis. No campo 80, o Zoner passa a vencer o
  Turtle em 68,8%. Na persistência 6, o Combo Master vence o Turtle em 69,4%, e o Turtle cai a 39,3%
  no total. Nas inconclusivas, um único par cruza a borda de 35%. A persistência é a regra a que o
  equilíbrio é mais sensível (os dois maiores `P_dom` da coluna).
- As 8 regras alteradas: distância inicial 40/60 (em vez de 50), campo 80/120 (em vez de 100),
  persistência 4/6 (em vez de 5), multiplicador da guarda 0,55/0,65 (em vez de 0,6). Todas dentro do
  que o modelo sustenta (a distância inicial continua maior que qualquer alcance).

**O que a busca enxerga** (sensibilidade, elenco do AG, semente 42, piso de ruído 3,46 pp):

| Gene | Variação média da taxa global (pp) | Classe |
|---|---|---|
| alcance | 30,8 | visível |
| dano | 26,2 | visível |
| intervalo entre golpes | 25,7 | visível |
| vida | 23,9 | visível |
| agarrão | 18,6 | visível |
| atordoamento | 10,4 | visível |
| peso de RECUAR | 4,8 | limítrofe |
| repulsão | 4,3 | limítrofe |
| velocidade | 3,51 | limítrofe (acima do piso por 0,05) |
| peso de FRENTE | 3,0 | neutro |
| peso de GUARDA | 2,9 | neutro |

A janela dos pesos é **4× mais estreita**, porque a mutação deles é 4× menor. Numa medição feita para
a monografia com a **mesma janela relativa** dos atributos (10% da amplitude para cada lado), os pesos
movem a taxa global em **12 a 17 pp** (RECUAR 16,5; FRENTE 14,3; GUARDA 12,4), acima do atordoamento,
da repulsão e da velocidade. A política pesa no combate; o que a esconde é o passo da mutação.

### 12.3 QP2: identidade

**O AG sozinho, contra os nulos.** A identidade estrutural fica bem acima do acaso (desvio 0,2473
contra 0,415 dos sorteados; 11 de 18 asserções de genes contra 5,4 em média e 9 no melhor nulo), mas
isso é parcialmente endógeno. A funcional é modesta: Camada 3 em 3/5 e τ = 0,28, acima da média dos
sorteados (1,0 e −0,02), mas no topo da distribuição dos nulos (o melhor sorteado também chega a 3 e a
τ = 0,316). Um elenco isolado não tem resolução para concluir: o da semente 42 empata com o melhor
nulo na Camada 3 (p = 0,03) e fica um fio abaixo dele em τ (0,314, p = 0,06). **A evidência vem do
controle.**

**O contrafactual:**

| Métrica | AG | λ = 0 | p de Holm | Â₁₂ | Sem semente | p de Holm | Â₁₂ |
|---|---|---|---|---|---|---|---|
| `P_dom` | 0,0355 | 0,0432 | 0,059 | 0,30 | 0,0264 | 0,99 | 0,55 |
| Hard counters | 0 | 0 | 0,18 | 0,57 | 0 | 0,83 | 0,55 |
| Desvio | 0,2473 | 0,4055 | 1,1·10⁻⁵ | 0,00 | 0,2703 | 0,0073 | 0,25 |
| Camadas 1-2 | 11 | 6 | 4,2·10⁻⁴ | 0,98 | 10,5 | 0,31 | 0,66 |
| Camada 3 | 3 | 1 | 0,0044 | 0,85 | 2 | 0,59 | 0,64 |
| τ | 0,28 | −0,03 | 6,7·10⁻⁴ | 0,87 | 0,19 | 0,39 | 0,67 |

- **Sem o termo, a perda é completa, até o acaso**: desvio 0,4055 (sorteado: 0,415), 6 asserções de
  genes e 1 de comportamento (média dos sorteados), τ médio de +0,007 nas 20 execuções.
- **No equilíbrio, não separa**: p bruto 0,030, p de Holm 0,059, efeito médio. Sustenta "a identidade
  não custou equilíbrio mensurável", **não** "a identidade melhora o equilíbrio".
- **Sem semente**: só o desvio separa. As outras estimativas também favorecem a semente, sem
  significância. A semente contribui um pouco e não explica a diferença entre AG e NSGA-II.

**O que se preserva e o que se perde** (em quantas das 20 execuções cada asserção vale):
- O AG preserva melhor o ritmo do Rushdown (velocidade e intervalo), o atordoamento do Combo Master e o
  agarrão do Grappler: 16 de 20 cada.
- Perde mais os traços do Zoner e do Turtle: entre 9 e 12 de 20.
- O padrão mais nítido: "o Rushdown é o que mais avança" vale em **só 4 a 5 de 20 em todos os
  braços**, inclusive nos que preservam mais identidade. Em boa parte das falhas, o Combo Master
  (FRENTE canônico 0,74, já perto do Rushdown) passa a avançar mais que ele: 10/20 no AG, 13/20 no
  NSGA-II, 14/20 no híbrido. A asserção comportamental correspondente ("o que mais golpeia") cai para
  3 de 20 no AG.
- O controle λ = 0 fica no nível do acaso em cada asserção (nas Camadas 1 e 3, o acaso dá cerca de 4
  em 20).

**A política** (probabilidade da intenção que define cada arquétipo):

| Arquétipo | Intenção | Canônico | AG | Híbrido | NSGA-II | λ = 0 |
|---|---|---|---|---|---|---|
| Rushdown | FRENTE | 0,86 | 0,39 | 0,47 | 0,48 | 0,35 |
| Combo Master | FRENTE | 0,74 | 0,47 | 0,51 | 0,55 | 0,40 |
| Grappler | FRENTE | 0,58 | 0,41 | 0,44 | 0,44 | 0,36 |
| Zoner | RECUAR | 0,55 | 0,33 | 0,45 | 0,46 | 0,19 |
| Turtle | GUARDA | 0,54 | 0,45 | 0,47 | 0,48 | 0,40 |

A política de todos se afasta do canônico, mas **não** em direção a uma política sorteada (1/3 em cada
intenção): os personagens convergem para um perfil comum que recua pouco. No AG, os quatro arquétipos
além do Zoner recuam em 0,17 a 0,23 das intenções. No controle λ = 0, as políticas dos cinco são
praticamente indistinguíveis (FRENTE 0,35–0,40, RECUAR 0,19–0,28, GUARDA 0,36–0,43).

### 12.4 QP3: o compromisso

**A fronteira.** As 20 fronteiras finais do NSGA-II têm em média 53 pontos e são estáveis (hipervolume
0,395 ± 0,011; espaçamento 0,012 ± 0,003). O compromisso é íngreme: na ponta de identidade, desvio
~0,06 com `P_dom` acima de 1 (tão desequilibrado quanto o canônico); reduzir `P_dom` a um décimo disso
custa 0,08 a 0,1 de desvio.

**Os representantes** (reavaliados):

| Representante | `P_dom` | Desvio | Hard counters | Equilibrados | Genes | Comport. | τ |
|---|---|---|---|---|---|---|---|
| best_drift | 1,056 | 0,059 | 8,45 | 0/20 | 18 | 5 | 0,80 |
| knee_point | 0,405 | 0,087 | 6,85 | 0/20 | 17 | 5 | 0,70 |
| ideal_point | 0,396 | 0,087 | 7,25 | 0/20 | 17,5 | 5 | 0,71 |
| scalar_optimum | 0,076 | 0,145 | 2,80 | 0/20 | 15 | 4 | 0,54 |
| best_dominance | 0,055 | 0,166 | 2,05 | 4/20 | 15 | 4 | 0,51 |

Os três pontos geométricos preservam quase tudo, mas **nenhum é equilibrado em nenhuma execução**. Os
pontos que interessam à pergunta estão na ponta de equilíbrio.

**AG escalar contra NSGA-II e híbrido:**

| Métrica | AG | NSGA-II s.o. | p Holm | Â₁₂ | NSGA-II b.d. | p Holm | Â₁₂ | Híbrido | p Holm | Â₁₂ |
|---|---|---|---|---|---|---|---|---|---|---|
| `P_dom` | 0,0355 | 0,0759 | 9,5·10⁻⁵ | 0,07 | 0,0551 | 0,0034 | 0,18 | 0,0287 | 1,00 | 0,51 |
| Hard counters | 0 | 3 | 3,4·10⁻⁴ | 0,03 | 2 | 0,0021 | 0,14 | 0 | 1,00 | 0,49 |
| Desvio | 0,2473 | 0,1445 | 1,1·10⁻⁵ | 1,00 | 0,1663 | 2,3·10⁻⁵ | 0,98 | 0,1663 | 1,1·10⁻⁵ | 0,97 |
| Camadas 1-2 | 11 | 15 | 3,4·10⁻⁴ | 0,05 | 15 | 0,0013 | 0,09 | 15 | 0,0026 | 0,12 |
| Camada 3 | 3 | 4 | 0,0027 | 0,24 | 4 | 0,0034 | 0,24 | 4 | 0,0058 | 0,24 |
| τ | 0,28 | 0,54 | 1,1·10⁻⁴ | 0,09 | 0,51 | 5,2·10⁻⁴ | 0,13 | 0,52 | 8,4·10⁻⁴ | 0,15 |

- **Contra o NSGA-II**: as 6 métricas significativas, todas com efeito grande, divisão limpa. O AG
  vence as 2 de equilíbrio; o NSGA-II vence as 4 de identidade (separação completa no desvio).
- **Contra o best_dominance**: mesmas direções e significância, efeitos menores no equilíbrio.
- **Contra o híbrido**: equilíbrio idêntico (Â₁₂ ≈ 0,5, p = 1,00); o híbrido vence as 4 de identidade.

**Relação de Pareto por semente** (dentro do laço):
- Em 18/20 sementes, o AG e a fronteira são **mutuamente não dominados**; em 1, o AG domina algum ponto;
  em 1, é dominado.
- Em 19/20, o ponto do AG fica **além** da ponta de equilíbrio da fronteira (`P_dom` 0,017 contra 0,048
  do ponto mais equilibrado dela), pagando em desvio.

**Mas o AG não está no ótimo da própria função.** Na soma `P_dom + P_drift`, a fronteira tem um ponto
melhor que o AG em **20/20** sementes dentro do laço (medianas 0,205 contra 0,266). Como o laço
favorece mais o AG (razão 1,80 contra 1,25), refez-se com os elencos reavaliados: o scalar_optimum tem
soma menor em 18/20.

**O híbrido.**
- Identidade próxima do NSGA-II (desvio 0,1663 contra 0,1445; τ 0,52 contra 0,54; mesma Camada 3) com
  o equilíbrio do AG (0,25 hard counters contra 2,80; 16/20 equilibrados contra 0/20).
- Além da ponta de equilíbrio em 19/20 sementes, mas com desvio menor que o AG. Nunca é dominado pela
  fronteira; domina algum ponto dela em 5/20.
- **Perto do ótimo da própria função**: a fronteira tem soma menor que a dele em só 3/20 sementes
  (contra 20/20 no AG); a mediana da soma no laço é 0,185, abaixo do melhor ponto da fronteira
  (0,205). Reavaliado, tem soma menor que o scalar_optimum em 14/20.
- **Preço: velocidade.** Converge na geração 98,3 ± 20,2 contra 31,3 ± 13,2, porque as primeiras 75
  gerações são de Pareto e não perseguem o predicado de equilíbrio.

### 12.5 A degradação entre o laço e a reavaliação

Razão mediana `P_dom` reavaliado ÷ `P_dom` no laço:

| Braço | Razão |
|---|---|
| Controle λ = 0 (só otimiza `P_dom`) | 2,33 |
| Controle sem semente | 1,95 |
| AG escalar | 1,80 |
| Híbrido | 1,67 |
| NSGA-II (scalar_optimum) | 1,25 |

A razão acompanha o peso que a seleção dá ao termo ruidoso. É uma tendência, não uma ordem exata (os
braços com a mesma soma variam entre si).

### 12.6 O ciclo de vantagens

| Grupo | Elencos | Decididas (de 10) | Mantidas (das decididas) | Tríades (de 5) | Margem |
|---|---|---|---|---|---|
| Canônico | 1 | 10,00 | 6/10 (60%) | 1,00 | 0,500 |
| AG escalar | 20 | 9,30 | 105/186 (56,5%) | 3,71 | 0,048 |
| NSGA-II | 20 | 9,85 | 98/197 (49,7%) | 4,17 | 0,104 |
| Espelhos | 5 | 1,00 | 3/5 | 2,59 | 0,003 |
| Aleatórios | 30 | 10,00 | 149/300 (49,7%) | 0,40 | 0,491 |

- **O canônico só realiza 6 das 10 arestas**, e as 4 que quebra são inversões completas: o Combo Master
  vence o Grappler em 0,2% das lutas, o Grappler vence o Rushdown em 0,6%, e o Turtle não vence nem o
  Rushdown nem o Combo Master. É uma hierarquia (1 tríade de 5), não um ciclo.
- **Nos evoluídos, o ciclo não se realiza**: o AG tem 56,5% na direção proposta, sem diferença do acaso
  (p = 0,091; contra os aleatórios p = 0,128, Â₁₂ = 0,63). O NSGA-II, praticamente metade. A aresta
  mais emblemática, Grappler × Turtle, é 100% no canônico e 52% na média do AG.
- **Os evoluídos são fortemente não transitivos** (3,7 a 4,2 tríades), mas isso é favorecido pelo
  objetivo (seção 13.4).
- **Por que 16.000 lutas.** A margem mediana das arestas de um elenco do AG é de só 0,048. Com 1.000
  lutas (desvio-padrão 0,016), 37% das arestas desses elencos ficariam abaixo do limiar de decisão.

---

## 13. A interpretação

### 13.1 A resposta e a objeção previsível

A objeção mais previsível: "com a identidade na aptidão, o algoritmo só foi pago para preservá-la".
Três respostas:
1. O termo de desvio **perde** boa parte das disputas: o AG termina com 11 de 18 asserções de genes e
   perde mais da metade da concordância comportamental. A troca foi resolvida pela busca, não pela
   formulação.
2. As métricas que respondem à pergunta medem **comportamento**, que nenhum termo da aptidão vê.
3. O ciclo não se realizar é informativo justamente porque a busca não foi paga nem para produzi-lo
   nem para destruí-lo.

Até o peso adotado, identidade e equilíbrio **não se mostraram antagônicos**. O antagonismo aparece
além dele (λ = 2 e 4 na varredura) e na fronteira do NSGA-II (mais identidade perto do equilíbrio tem
preço em `P_dom`). No peso adotado, **o que limita a identidade do AG é a busca, não a função
objetivo**.

### 13.2 A política é o que menos se preserva

Com o passo adotado, dois dos três pesos são os únicos genes abaixo do piso de ruído. A explicação
não é a política pesar pouco (com a mesma janela relativa, os pesos movem 12 a 17 pp). Ela está em
três coisas juntas:
1. **O passo de mutação dos pesos é 4× menor**, e nesse passo o efeito de cada mutação fica no nível
   do ruído.
2. **O ponto de partida**: quase toda a população inicial é sorteada, então as políticas começam, em
   média, perto da mistura uniforme.
3. **O único sinal que diferencia uma mutação de política** é o termo de desvio: exato, mas pequeno a
   cada passo, e, na soma escalar, encoberto pelo ruído do desequilíbrio.

Os braços em que o desvio é objetivo separado (NSGA-II e híbrido), com o mesmo passo, preservam mais a
política: o Zoner recua em 0,46 e 0,45 contra 0,33 no AG. No controle λ = 0, sem nada que as puxe de
volta, as políticas ficam indistinguíveis.

Consequência para quem aplicar a técnica: **o passo de mutação, somado ao ruído da avaliação, decide o
que a busca enxerga**. Ele precisa ser calibrado contra o ruído, e não só contra a plausibilidade da
mudança. E: **a identidade estrutural pode sobreviver enquanto a funcional se perde** (o Rushdown
mantém velocidade e ritmo, mas avança em 39% e só em 3/20 é o que mais golpeia). Por isso a pergunta
exige a medida funcional.

### 13.3 Como a seleção escalar perde identidade: dois estágios

Em 19/20 sementes o AG fica além da ponta de equilíbrio, e a fronteira tem um ponto melhor na soma que
ele otimiza em 20/20. A causa age em dois estágios:

**Estágio 1, início da busca (pressão, não ruído).** Longe do equilíbrio, as diferenças verdadeiras de
`P_dom` entre elencos são grandes, e a soma as privilegia. O canônico e os elencos próximos dele, muito
desequilibrados, perdem para sorteados mais equilibrados. Na réplica instrumentada da semente 42, o
canônico sai na geração 3, o menor desvio da população sobe para 0,17 na geração 7 e para 0,24 na
geração 20, e a população vira um aglomerado com largura de só 0,045 em desvio: sem diversidade de
identidade para recombinar. Isso **não é efeito do ruído**: as diferenças de `P_dom` ainda são muito
maiores que ele.

**Estágio 2, depois da convergência (ruído).** O desvio é exato; o desequilíbrio é amostrado, com
ruído da ordem do próprio valor. Esgotadas as diferenças verdadeiras, o ruído fica, cerca de **60×
maior que o ganho de desvio por geração**. Um elenco com mais identidade perde o torneio para outro com
menos identidade e uma avaliação de equilíbrio mais sortuda. A seleção gasta pressão em sorte, e a
identidade perdida quase não volta (desvio 0,29 na geração 30, 0,25 no fim).

**Três observações consistentes com isso:**
1. A degradação laço → reavaliação acompanha o peso do termo ruidoso (2,33 → 1,80 → 1,25).
2. A confirmação da convergência recusou 71% dos elencos que pareciam equilibrados.
3. **O híbrido**, a mais forte: na fase de Pareto, o elenco de menor desvio fica protegido qualquer que
   seja o `P_dom`, e o desvio não compete com o ruído. Resultado: identidade perto do NSGA-II,
   equilíbrio do AG, perto do ótimo da própria função.

**Ressalvas:** o híbrido é consistente com a explicação, mas **não separa os estágios** (não mede
quanto do ganho vem da diversidade preservada e quanto da proteção contra o ruído). A divisão 0,5 veio
de desempate. E o preço é real: converge três vezes mais tarde.

**Consequência para a pergunta:** o compromisso medido pelo AG escalar é um **limite superior** do
custo da identidade. Parte do que pareceria "equilibrar exige sacrificar identidade" é propriedade da
seleção escalar, não do problema.

### 13.4 O ciclo que o modelo não realiza

Não havia ciclo a preservar: a quebra já está no canônico. Duas explicações, não excludentes:
1. **Calibração**: o critério que aceitou os perfis exigia desequilíbrio, não um ciclo.
2. **Abstração do modelo**: várias vantagens clássicas dependem de mecânicas ausentes. O Turtle vence o
   Rushdown porque pune janelas de recuperação, que só existem com quadros de animação; o Combo Master
   vence o Grappler porque transforma um acerto numa sequência longa. Com dano fixo e ataque como
   regra, vantagem vira **taxa de dano**, e diferenças grandes de taxa de dano produzem hierarquias.

Os evoluídos são não transitivos, mas isso é favorecido pelo objetivo: numa ordem estrita, o primeiro
vence os quatro e fica acima de 50% no total, e o último abaixo, então o termo global só zera quando
as vantagens se compensam em ciclos. (A faixa de equilíbrio, sozinha, não exige isso: uma ordem estrita
com margens de 5 pp dá taxas globais entre 45% e 55%.) O algoritmo produz estrutura cíclica, mas não
**a** estrutura autoral. Como o objetivo é cego à direção, isso é o esperado, e **confirma** que o ciclo
não foi codificado na busca.

### 13.5 Lições de método

1. **Nenhuma métrica de identidade tem piso zero.** Sem nulos, "3 de 5 asserções" pareceria mais da
   metade da identidade funcional; na verdade empata com o melhor de 30 sorteados.
2. **Uma medição grosseira pode produzir uma diferença significativa que não se sustenta.** Com 200
   lutas por par, o controle λ = 0 parecia significativamente **menos** equilibrado (0,0534 contra
   0,0399, p de Holm 0,038). Com 1.000 lutas, os **mesmos elencos, idênticos gene a gene**, deram
   0,0432 contra 0,0355 e p de Holm 0,059, com o mesmo tamanho de efeito (Â₁₂ = 0,30). O erro de
   medição de cada elenco a 200 lutas era da ordem da diferença entre os braços. O viés da régua
   grosseira não explica a mudança: pelo modelo binomial, ele deveria ter **aproximado** os braços. A
   mudança de resolução foi aplicada a todos os braços igualmente e **enfraqueceu** uma afirmação, o
   que afasta a suspeita de ajuste. Sobreviveu a afirmação mais estreita.
3. **A resolução precisa acompanhar a margem.** Com 200 lutas, o ciclo parecia mantido em 5 de 10
   arestas, e os espelhos (sem estrutura) marcavam 5,4. Com 16.000 lutas e só arestas decididas, os
   espelhos decidem uma única aresta, e o teste passou a separar estrutura de ruído.

### 13.6 Limitações

| Limitação | O que significa |
|---|---|
| **Política fixa** | Os personagens não aprendem, e ninguém procura uma estratégia que explore o elenco. É a objeção mais forte ao equilíbrio. Teste natural: coevolução |
| Política cega ao estado | A intenção não depende de vida, distância, recarga ou atordoamento do oponente: é uma mistura fixa de três posturas |
| Combate abstrato | Sem quadros de animação, janelas de punição, combos ou tipos de ataque |
| Confronto uniforme | O todos-contra-todos pesa os 10 pares igualmente, sem a escolha de personagens de um metagame |
| Perfis autorais | Uma operacionalização entre várias; o desvio protege com rigor desigual (o Combo Master tem 1 gene definidor, o Turtle 4: 23% contra 63% do peso) |
| Métricas funcionais não independentes | Cada asserção comportamental decorre de um gene definidor; a Camada 3 tem 5 bits |
| Parâmetros não calibrados | Campo, distância, guarda, mutação, população, gerações. A validação externa mede a dependência dos parâmetros de combate, não dos da busca |
| Análises com um elenco | Validação externa, sensibilidade e réplica instrumentada usam a semente 42; a sensibilidade é local |
| Comparação restrita | Só AG escalar, NSGA-II e híbrido, com um orçamento |

### 13.7 Trabalhos futuros

1. Testar o equilíbrio contra oponentes que se adaptam (coevolução).
2. Dar à política o passo que a identidade exige (calibrado contra o ruído) ou inicializar perto dos
   perfis canônicos.
3. Políticas que dependam do estado da luta.
4. Mecânicas que sustentem ciclos (janelas de punição, encadeamento).
5. Explorar a diversidade de elencos equilibrados (MAP-Elites, usando o perfil comportamental).
6. Calibrar o híbrido no orçamento completo.

---

## 14. A apresentação, slide a slide

A defesa segue a estrutura da monografia, em cinco blocos que o cabeçalho marca: **Introdução (2–4) →
Referencial (5–8) → Metodologia (9–13) → Resultados (14–20) → Conclusão (21–23)**. No bloco de
resultados, a QP3 tem três slides que formam um arco próprio: "o AG não está no ótimo" → "por quê?" →
"o híbrido conserta". Cada slide do referencial planta algo que os outros blocos cobram; a lista das
ligações está em `script.md`, seção "O fio entre o referencial e o resto".

**Código de cores**: azul = AG escalar; laranja = NSGA-II; verde-água = híbrido; cinza-escuro =
controles; vermelho = desequilíbrio (e "frágil"); roxo = desvio e perfis canônicos. QP1/QP2/QP3 em
verde no título dizem a qual questão o slide responde; o cabeçalho marca a seção.

### Introdução

**Slide 1, Capa.** Título, você, orientador e banca. A data aparece só como "2026": ponha a da defesa.
Mensagem: o tema e a pergunta em uma frase.

**Slide 2, "Equilibrar um elenco é caro, manual e nunca termina".** Esquerda: o mercado (US$ 188,8 bi
em 2025 e 3,58 bi de jogadores, segundo a Newzoo) e a definição de esports de Hamari e Sjöblom.
Direita: o ciclo manual (ajustar, testar, observar, corrigir), caro e sem fim. Faixa: a computação
evolutiva tenta automatizar parte desse ciclo. Os números da Newzoo são de relatório de indústria, sem
revisão por pares, e a monografia avisa isso.

**Slide 3, "Há duas formas de errar no balanceamento de um elenco".** Dois cartões com barras de taxa
de vitória: um personagem domina / todos ficam em 50% (cinza, iguais). Mensagem: o desafio fica entre
os dois (seção 3.1). A fala acrescenta que o elenco espelho é a solução trivial de referência
(seção 10.6).

**Slide 4, "Pergunta de pesquisa e objetivos".** A pergunta, QP1–QP3 e os cinco objetivos específicos
da monografia, que seguem a ordem da metodologia (seção 3.4). Os cinco arquétipos, que ficavam aqui na
primeira apresentação, foram para o slide 5.

### Referencial

**Slide 5, "Equilibrar não é igualar todos os confrontos".** Esquerda: simetria estatística contra
vantagens recíprocas (Adams; Elias, Garfield e Gutschera) e o argumento de Gingold. Direita: o ciclo
proposto, desenhado como um torneio: cada arquétipo vence o vizinho seguinte no sentido horário e,
pela diagonal, o que vem depois dele. Mensagem: a aptidão mede "ninguém domina o elenco", e não "50%
em cada par" (seções 3.5 e 6.2); o ciclo é hipótese, testada depois. Ciclo medido → **R1**.

**Slide 6, "Algoritmo genético: a aptidão é o único elo com o problema".** Esquerda: o ciclo genérico
(população → aptidão → seleção → variação, com elitismo), cada passo com a propriedade que o trabalho
usa. O torneio é ordinal, por isso só a razão entre os λ importa. O cruzamento por blocos herda partes
coerentes, aqui o personagem inteiro. O passo da mutação regula exploração e explotação, e é o passo
4× menor dos pesos que volta no slide 17. Direita: a aptidão ruidosa. O gráfico é **ilustrativo**, não
é dado: seis candidatos com valor real (traço), estimativa (ponto) e ruído (barra); o mais bem
avaliado, em vermelho, não é o melhor de verdade. Defesas: números aleatórios comuns e reavaliação
(seção 7).

**Slide 7, "Dois objetivos em conflito: somar ou comparar por dominância".** Esquerda: o diagrama de
dominância, também ilustrativo, com os dois eixos minimizados, a fronteira em laranja, a região que A
domina sombreada com B dentro e o extremo de menor desvio, que ninguém domina. Direita: escalarização
(Deb, 2001: pesos fixados de antemão, regiões não convexas inalcançáveis), NSGA-II (Deb et al., 2002:
frentes de não dominância, aglomeração, elitismo) e multiobjetivização (Knowles et al., 2001: separar
os termos preserva diversidade, a base do híbrido). Mensagem: seção 8.2. O extremo de menor desvio é o
que o slide 20 cobra. Representantes → **R11**.

**Slide 8, "Trabalhos relacionados: nenhum mede se a identidade sobrevive".** Tabela com Hom e Marks,
Browne e Maire, Chen et al. e Volz et al. (domínio e formulação) contra os três requisitos: luta em
tempo real, equilíbrio contra identidade como compromisso explícito e identidade medida fora da busca.
A linha "Este trabalho" é a única com os três. Rodapé: Togelius et al. como o campo, e Browne e Maire
como a origem do princípio da validação externa. Mensagem: a lacuna, que vira as contribuições do slide
22. O que cada referência diz está logo abaixo, depois da lista de slides.

### Metodologia

**Slide 9, "Arquitetura: a busca usa a simulação como caixa-preta".** A figura de arquitetura da
monografia, com os números do AG:

- os perfis canônicos (roxo) entram como semente e como referência do desvio;
- dentro do laço tracejado de 150 gerações:
  - população: 300 elencos, e na geração 0 o canônico e 299 sorteados;
  - avaliação: 10 pares × 150 lutas; o desequilíbrio vem das lutas, com ruído, e o desvio dos genes,
    exato; os sorteios são iguais na geração e novos a cada geração;
  - seleção: elitismo de 10% e torneio de 3, por soma ou por dominância;
  - variação: o personagem vem inteiro de um pai, e a mutação gaussiana atinge 5% dos genes, com passo
    de 10% da faixa (2,5% nos pesos);
- embaixo, a saída e a medição fora do laço.

Mensagem: seções 5, 7 e 8.1. A não circularidade (seção 3.2) aparece como a seta tracejada que não
volta ao laço.

**Slide 10, "Um simulador de luta em que cada gene muda o resultado".** Esquerda: a luta (campo 1D,
tick de 5 sub-ticks, postura sorteada e mantida por um tick, ataque como regra, guarda × 0,6 rompida
pelo agarrão). Direita: o indivíduo (grade 5 × 11, 55 genes, 1.500 lutas por avaliação). Mensagem: os
dois canais (seção 4.2). Detalhe → **R13**.

**Slide 11, "A aptidão diz o que cada arquétipo é, nunca quem deve vencer".** Esquerda: o
desequilíbrio (três termos com os pesos 1,0/0,5/0,5), o desvio (normalizado pela faixa, peso 3 nos
definidores) e as duas formulações (soma com pesos iguais; NSGA-II minimiza os dois). Direita,
tracejado: o que só é medido depois. A fala acrescenta que o limite de 65% fica entre o 6-4 e o 7-3 da
convenção do gênero (seção 6.2). Mensagem: premissa sim, resposta nunca (seção 3.2). **Não corte.**
Equações → **R2**.

**Slide 12, "Protocolo: cinco braços, mesmo orçamento, mesmas sementes".** Esquerda: os cinco braços
com o papel de cada um (seção 9.1). Direita: 20 execuções pareadas, 300 × 150, reavaliação com 1.000
lutas, 35 modelos nulos e Wilcoxon pareado com Â₁₂ e Holm sobre a família fixa de 7 métricas (seções
9.2, 10.6 e 11).

**Slide 13, "Implementação: combate compilado e cada número rastreável".** Três números: cerca de 150×
com Numba, uma medição do projeto que **não está na monografia**; 68 e 135 milhões de lutas por
execução do AG e do NSGA-II. A organização do código (engine → experiments → results →
visualization) e a reprodutibilidade (a semente fixa tudo; o carimbo de proveniência avisa ao carregar
e recusa ao gravar).

### Resultados

**Slide 14, QP1 "O AG escalar leva uma hierarquia ao equilíbrio".** As duas matrizes (porcentagem de
vitórias da **linha** contra a **coluna**, medidas com 16.000 lutas por par; à direita, a média das 20
execuções do AG). Números: 1,28 → 0,036; 20/20 convergiram (geração 31); 16/20 terminaram
equilibradas. A fala acrescenta a leitura contra o espelho: 1,6 ponto de 50% contra 0,7 de ruído.
Por que dois números (20/20 e 16/20) → seção 12.2. Convergência → **R6**.

**Slide 15, QP1 "Fora do laço, o equilíbrio se repete, mas depende das regras".** Esquerda: replica (o
único dos 4). Direita: as 8 regras com o veredito. Rodapé: 4 robustas · 2 inconclusivas · 2 frágeis.
Como o veredito é dado (intervalo de Wilson) → seção 11.1. Tabela completa → **R4**.

**Slide 16, QP2 "Sem o termo, a identidade cai ao nível do acaso".** Três colunas (AG, λ = 0,
sorteados) em quatro métricas: desvio 0,25/0,41/0,42; genes 11/6/5,4; comportamento 3/1/1,0; τ
0,28/−0,03/−0,02. Rodapé: equilíbrio 0,036 contra 0,043, p = 0,059. Mensagem: o controle é a evidência
da QP2; a identidade que sobra é do termo, e ele não custou equilíbrio mensurável. **Não corte.**
200 contra 1.000 lutas → **R8**. Nulos → **R9**.

**Slide 17, QP2 "A política é o que mais se perde, e a busca mal a enxerga".** Esquerda: chance de o
Rushdown avançar (86/48/47/39/35%). Direita: efeito dos pesos com o passo atual (3,0/4,8/2,9) e com o
passo dos atributos (14,3/16,5/12,4), contra o ruído (~3,5). Mensagem: seção 13.2. Sensibilidade
completa → **R7**.

**Slide 18, QP3 "Nenhum domina, mas o AG escalar não atinge o seu ótimo".** A figura: eixo x =
desequilíbrio em **escala logarítmica**; eixo y = desvio. Cada linha cinza em degraus é a fronteira de
uma execução do NSGA-II; quadrados laranja = scalar_optimum; círculos azuis = AG escalar; X cinza =
controle λ = 0 (equilibrados, mas lá em cima no desvio); estrela = canônico (desvio 0, desequilíbrio
1,28). Todos os pontos são **dentro do laço**. Mensagem: nenhum domina (18 de 20 sementes mutuamente
não dominadas; o escalar além da ponta em 19 de 20), mas 20/20 na soma (seção 12.4). Representantes →
**R11**. Comparação completa → **R10**.

**Slide 19, QP3 "Por quê? A soma escalar perde identidade em dois estágios".** Figura da semente 42:
em cima, o desequilíbrio do melhor elenco (escala log); embaixo, o desvio do elenco mais fiel ainda na
população, com 0,17 (geração 7) e 0,24 (geração 20) marcados. Faixa vermelha = estágio 1 (gerações 0 a
20); faixa cinza = estágio 2 (30 em diante). A fala amarra com o slide 6: "é o problema da aptidão
ruidosa". Mensagem: seção 13.3. **Não corte**: sem ele, o híbrido aparece sem motivo.

**Slide 20, QP3 "O híbrido une a identidade do NSGA-II ao equilíbrio do AG".** Tabela: equilibrados
16/16/0; counters 0,20/0,25/2,80; desvio 0,25/0,17/0,14; τ 0,28/0,52/0,54; convergência 31/98/—.
Rodapé: identidade p ≤ 0,0058; equilíbrio p = 1,00. Mensagem: parte da perda de identidade vem da
seleção escalar, não do problema. (O NSGA-II não tem convergência porque o predicado não se aplica a
uma fronteira.)

### Conclusão

**Slide 21, "Sim: é possível equilibrar sem destruir as identidades".** As três respostas e a
mensagem final (seção 1).

**Slide 22, "Cinco contribuições, da formulação à medição".** As cinco contribuições da conclusão da
monografia: formulação não circular, evidência controlada, a falha da seleção escalar (com o híbrido),
a perda localizada na política e as lições de método. Cada uma responde a uma linha da lacuna do slide
8 ou a um achado.

**Slide 23, "O modelo ainda é simples; os próximos passos saem dos achados".** Limites (combate
abstrato; ciclo não realizado nem no canônico; política fixa) e próximos passos (passo da política,
políticas dependentes do estado, coevolução, calibrar o híbrido). Cada próximo passo responde a um
achado.

**Slide 24, Obrigado.** QR code do repositório; fica na tela durante as perguntas.

### O que cada referência diz (e o que não diz)

Os slides 2 e 5 a 8 citam autores pelo nome, e a banca pode perguntar sobre qualquer um. O que segue é
o que a monografia usa de cada um. Os itens marcados "conferido" foram checados contra o texto
original em 30/09/2026.

- **Newzoo (2025).** US$ 188,8 bi em 2025, com projeção de US$ 206,5 bi para 2028; 3,58 bi de
  jogadores, cerca de 61,5% da população *online*. Relatório de indústria, sem revisão por pares.
  Conferido.
- **Hamari e Sjöblom (2017).** Esports são uma forma de esporte em que a entrada dos jogadores e a saída
  do sistema são mediadas por sistemas eletrônicos.
- **Adams (2014).** O equilíbrio é a condição em que nenhuma opção domina sistematicamente as outras. Um
  elenco com poucos personagens viáveis reduz a profundidade estratégica.
- **Elias, Garfield e Gutschera (2012).** O equilíbrio é uma propriedade estrutural dos jogos. Eles
  separam o equilíbrio entre jogadores do equilíbrio interno ao espaço de opções.
- **Gingold (2006).** O ciclo é entre **ações** dentro da luta: golpe, defesa e o agarrão que vence a
  defesa. A seção 3.1 do artigo mostra que, se nenhuma escolha é imbatível, o grafo de vantagens tem um
  ciclo. Ele **não** fala de personagens: a transposição para o elenco é deste trabalho. Conferido.
- **Holland (1975), Goldberg (1989), Eiben e Smith (2015).** Fundamentos do AG. O torneio depende só da
  ordem das aptidões. A mutação regula exploração e explotação (Eiben e Schippers, 1998).
- **Deb (2001).** A escalarização exige fixar os pesos de antemão e não alcança as regiões não convexas
  da fronteira, quaisquer que sejam os pesos.
- **Deb et al. (2002).** O NSGA-II combina ordenação não dominada rápida, distância de aglomeração e
  sobrevivência elitista de pais e filhos. A seleção dos pais é por torneio binário.
- **Knowles, Watson e Corne (2001).** Tratar como objetivos separados os termos de uma soma pode reduzir
  ótimos locais, porque mantém soluções que a soma descartaria.
- **Jin e Branke (2005).** É um levantamento sobre otimização evolutiva sob incerteza. A monografia o
  cita para três efeitos da aptidão ruidosa:
  - a seleção responde ao ruído;
  - avaliações afortunadas são favorecidas;
  - o melhor fica superestimado.

  O texto completo **não** foi conferido; se for citar além disso, leia antes.
- **Law (2015).** Números aleatórios comuns: as alternativas comparadas são avaliadas sob os mesmos
  sorteios, o que reduz a variância das diferenças.
- **Hom e Marks (2007).** Um AG que evolui as regras de jogos de tabuleiro abstratos, avaliadas por
  partidas entre agentes.
- **Browne e Maire (2010).** Evolução de jogos completos, avaliados por critérios estruturais e por
  simulação. É trabalho independente de Hom e Marks, não uma extensão. Conferido.
- **Chen, Mori e Matsuba (2014).** Equilíbrio entre **raças** (não classes) de um MMORPG, por coevolução
  cooperativa das funções de crescimento de atributos. O modelo de combate é por turnos, declarado no
  artigo de 2012 dos mesmos autores. Eles reconhecem o problema como multiobjetivo, mas não usam
  fronteira de Pareto. Conferido.
- **Volz, Rudolph e Naujoks (2016).** Equilíbrio do Top Trumps com um algoritmo evolutivo
  multiobjetivo, com objetivos de justiça e de interesse.
- **Togelius et al. (2011).** Levantamento da geração procedural de conteúdo baseada em busca. O
  equilíbrio **não** é uma categoria da taxonomia; aparece só como critério de avaliação em exemplos.
  Conferido.
- **Derrac et al. (2011) e Arcuri e Briand (2011).** Testes não paramétricos para comparar algoritmos
  estocásticos. O Â₁₂ é recomendação de Arcuri e Briand, **não** de Derrac. Conferido.

### As reservas (R1 a R13), depois do "Obrigado"

| Se perguntarem sobre | Mostre | Neste guia |
|---|---|---|
| Ciclo de vantagens, tríades | R1 | 12.6, 13.4 |
| Fórmulas da aptidão, λ | R2 | 6 |
| Valores canônicos, genes definidores | R3 | 3.3 |
| Validação externa em detalhe | R4 | 11.1, 12.2 |
| Distribuição das métricas por braço | R5 | 12.2, 12.3 |
| Convergência, trajetórias | R6 | 12.2 |
| Sensibilidade, genes neutros | R7 | 10.9, 12.2 |
| 200 contra 1.000 lutas, a afirmação que caiu | R8 | 13.5 |
| Modelos nulos, piso, espelhos | R9 | 10.6 |
| Comparações com p e Â₁₂ | R10 | 11.4, 12.4 |
| Representantes da fronteira, joelho | R11 | 8.2, 12.4 |
| Origem de cada parâmetro | R12 | 9.6 |
| Regras do combate | R13 | 4 |

As respostas prontas para as perguntas prováveis estão em `script.md`, seção "Perguntas prováveis".

---

## 15. O que não afirmar

| Não diga | Diga |
|---|---|
| "A identidade melhora o equilíbrio" | "A identidade não custou equilíbrio mensurável" (p de Holm 0,059) |
| "O AG escalar atinge a simetria perfeita" | "Chega perto da simetria, sem alcançá-la" (1,6 pp contra 0,7 pp de ruído) |
| "O equilíbrio é robusto" | "Replica, e é robusto a 4 de 8 regras alteradas; frágil em 2" |
| "O NSGA-II é pior" | "Nenhum domina o outro: o AG vence em equilíbrio, o NSGA-II em identidade" |
| "O híbrido prova a explicação dos dois estágios" | "É consistente com ela, mas não separa os estágios" |
| "Metade e metade é a melhor divisão do híbrido" | "A divisão veio de um desempate por simplicidade; calibrar é trabalho futuro" |
| "O AG destruiu o ciclo" | "Não havia ciclo a preservar: o canônico é uma hierarquia" |
| "As asserções de genes provam a identidade" | "São parcialmente endógenas; a evidência funcional vem do controle" |
| "A política não importa no combate" | "Importa (12 a 17 pp com a mesma janela); o passo de mutação é que a esconde" |
| "λ = 1, elitismo 10% e torneio 3 são ótimos" | "λ = 1 é o joelho medido; elitismo e torneio foram testados e nada os supera em tudo" |
| "Convergiu, então está equilibrado" | "Convergir é o primeiro sucesso confirmado; 16/20 terminam equilibrados" |
| "A diferenciação mostra a homogeneização" | "A diferenciação não separa identidade de dispersão" |
| "A validação externa vale para todas as execuções" | "Foi feita nos elencos da semente 42" |
| Números do artigo da Latinoware (21 asserções, 7/21, 20/21, 9/10, 1,42) | Só os da bateria de 23/09 |
| "Os arquétipos vêm da literatura" | "A literatura fundamenta a estrutura não transitiva em geral; os cinco perfis e o ciclo são construção minha, tratados como hipótese" |

---

## 16. Glossário

| Termo | Significado |
|---|---|
| **Arquétipo** | estilo de personagem (Rushdown, Zoner, Grappler, Combo Master, Turtle) |
| **Perfil canônico** | os 11 valores de referência de um arquétipo; a premissa |
| **Gene definidor** | gene em que o arquétipo é, por projeto, o extremo do elenco; peso 3 no desvio |
| **Elenco** (*roster*) | os 5 personagens; é o indivíduo do algoritmo |
| **Política** | os 3 pesos de comportamento (FRENTE, RECUAR, GUARDA) |
| **Intenção / postura** | a intenção é sorteada; a postura é o que o personagem faz no sub-tick |
| **Tick / sub-tick** | unidade de projeto / unidade real da simulação (1 tick = 5 sub-ticks) |
| **Round-robin** | todos contra todos: 10 pares |
| **WR** (*win rate*) | taxa de vitória |
| **Hard counter** | par em que um lado vence mais de 65% |
| **Decisividade** | quão folgadas são as lutas de um par, independente de quem vence |
| **`P_dom`** (*dominance_penalty*) | desequilíbrio, de 0 a 2 |
| **`P_drift`** (*drift_penalty*) | desvio de identidade estrutural |
| **λ** | peso de cada termo na aptidão escalar; λ = 0 = sem o termo de desvio |
| **Premissa / resposta** | o que pode / não pode entrar na aptidão |
| ***Post hoc*** | medido depois da busca, sem voltar ao laço |
| ***Held-out*** | fora da otimização (nenhum termo da aptidão o vê) |
| **Endógeno** | mede o mesmo eixo que a aptidão otimiza |
| **Braço** | uma configuração experimental rodada 20 vezes |
| **Bateria** | o conjunto de todas as execuções e análises de 23/09/2026 |
| **Semente** | número que fixa todos os sorteios de uma execução |
| **Stream** | a sequência concreta de sorteios gerada por uma semente |
| **CRN** | *common random numbers*: todos os indivíduos avaliados com os mesmos sorteios |
| **Dentro do laço / reavaliado** | medido na busca (150 lutas, stream da última geração) / medido depois (1.000 lutas, semente 9999) |
| **Convergência** | primeira geração em que o melhor elenco está equilibrado, confirmado em sorteios inéditos |
| **Fronteira de Pareto** | os elencos que nenhum outro supera nos dois objetivos ao mesmo tempo |
| **Dominar** (Pareto) | ser melhor ou igual nos dois objetivos e melhor em pelo menos um |
| **Distância de aglomeração** | quão isolado um ponto está na sua frente; mantém a fronteira espalhada |
| **scalar_optimum** | o ponto da fronteira que minimiza `P_dom + P_drift`; o da comparação principal |
| **best_dominance / best_drift** | os extremos da fronteira (mais equilibrado / mais fiel) |
| **knee_point / ideal_point** | o joelho / o mais próximo do ponto utópico |
| **Hipervolume** | área dominada pela fronteira até um ponto de referência |
| **Multiobjetivização** | usar uma formulação multiobjetivo para preservar soluções que a soma descartaria |
| **Modelo nulo** | elenco sem otimização (espelho ou sorteado), usado como piso |
| **Espelho** | cinco cópias do mesmo perfil canônico; a solução trivial do equilíbrio |
| **Controle** | o mesmo algoritmo com um único fator de desenho trocado |
| **Validador** | as 23 asserções de identidade, em 3 camadas |
| **τ** (concordância) | Kendall τ-b médio entre a ordem canônica e a do elenco em 10 métricas de comportamento |
| **Aresta decidida / mantida** | par fora de 50% por mais de 2σ / decidido na direção proposta |
| **Tríade circular** | A vence B, B vence C, C vence A |
| **Intervalo de Wilson** | intervalo de confiança para uma proporção, robusto perto de 0% e 100% |
| **Wilcoxon pareado** | teste de postos sobre as diferenças entre execuções de mesma semente |
| **Mann-Whitney** | a versão não pareada, reportada ao lado |
| **Â₁₂** | probabilidade de o AG dar valor maior; 0,5 = sem efeito |
| **Holm** | correção para várias métricas testadas ao mesmo tempo |
| **Família de testes** | as 7 métricas fixadas antes da bateria (6 efetivas) |
| **Artefato / proveniência** | arquivo de resultado em `results/` / o registro, dentro dele, da configuração e do código que o produziram |
