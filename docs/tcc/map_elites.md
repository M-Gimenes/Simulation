# MAP-Elites: Mapeamento do Espaço de Soluções para Calibração de Hiperparâmetros

> **Nota para escrita do TCC:** Este documento descreve a teoria, a aplicação e as decisões de design do MAP-Elites implementado neste trabalho. O conteúdo está estruturado em seções que podem ser incorporadas diretamente na escrita acadêmica, com fórmulas, justificativas e referências cruzadas ao sistema principal.

---

## 1. Introdução ao MAP-Elites

MAP-Elites (*Multi-dimensional Archive of Phenotypic Elites*) é um algoritmo evolucionário de iluminação de qualidade (*quality-diversity*), proposto por Mouret e Clune (2015). Diferentemente dos algoritmos genéticos tradicionais — que buscam uma única solução ótima —, o MAP-Elites tem como objetivo produzir um **mapa diversificado de soluções de alta qualidade**, onde cada solução ocupa uma região distinta de um espaço de comportamento definido pelo pesquisador.

A ideia central é separar dois conceitos que algoritmos convencionais tratam como um só:

- **Qualidade (*fitness*):** quão boa é a solução em termos do objetivo principal.
- **Descritor comportamental (*behavioral descriptor*):** em que região do espaço de comportamento a solução se encontra, independentemente de sua qualidade.

O resultado é um **arquivo** (*archive*): uma grade multidimensional onde cada célula contém a melhor solução encontrada para aquela combinação específica de descritores comportamentais.

---

## 2. Algoritmo

O MAP-Elites segue o seguinte procedimento geral:

```
1. Inicializar o arquivo com N_INIT indivíduos aleatórios
2. Para cada iteração de 1 a N_ITERATIONS:
   a. Selecionar aleatoriamente um indivíduo do arquivo
   b. Aplicar operador de variação (mutação) → gerar filho
   c. Avaliar o filho → obter (qualidade, descritor)
   d. Mapear o descritor para a célula (bx, by) do grid
   e. Se a célula estiver vazia OU o filho tiver qualidade melhor
      → substituir o ocupante atual pelo filho
3. Retornar o arquivo preenchido
```

A seleção aleatória uniforme entre células ocupadas (passo 2a) garante que todas as regiões do espaço comportamental recebam atenção exploratória, sem pressão seletiva que concentre a busca em um único ótimo.

---

## 3. Aplicação neste Trabalho

### 3.1 Motivação

O sistema principal deste TCC usa um Algoritmo Genético (AG) para evoluir conjuntos de 5 personagens de jogo com equilíbrio competitivo. A função de fitness do AG é:

$$f = (1 - \text{balance\_error}) - \lambda \cdot \text{attribute\_cost} - \lambda_{\text{drift}} \cdot \text{drift\_penalty} - \lambda_{\text{matchup}} \cdot \text{matchup\_dominance\_penalty}$$

Os três termos de penalidade competem entre si: reduzir `drift_penalty` (manter os personagens próximos dos valores canônicos) pode exigir aceitar um `balance_error` maior, e vice-versa. Os pesos $\lambda_{\text{drift}}$ e $\lambda_{\text{matchup}}$ controlam esse trade-off.

O problema é que **não há forma analítica de escolher esses pesos a priori** — eles dependem da geometria do espaço de soluções, que só é conhecida empiricamente. Valores errados podem:

- Tornar a penalidade de drift dominante, impedindo que o AG evolua livremente
- Tornar a penalidade de matchup irrelevante, aceitando matchups com 80%+ de winrate
- Criar escalas incompatíveis entre os termos, distorcendo a superfície de fitness

O MAP-Elites resolve esse problema ao **mapear empiricamente o espaço antes de rodar o AG**, revelando como `balance_error` e `drift_penalty` se relacionam na prática para este sistema específico.

### 3.2 Espaço Comportamental

O grid do MAP-Elites é bidimensional:

| Dimensão | Descritor | Bins | Intervalo |
|----------|-----------|------|-----------|
| Eixo X | `balance_error` | 10 | [0.0, 0.5] |
| Eixo Y | `drift_penalty` | 8 | [0.0, 0.6] |

Isso gera **80 células** no total (10 × 8). Cada célula representa uma combinação específica de quão balanceado é o conjunto de personagens e quão distante dos valores canônicos ele está.

**Por que esses dois descritores?** Eles capturam o trade-off central da pesquisa: é possível obter equilíbrio competitivo sem abandonar as identidades originais dos arquétipos? O eixo X mede a qualidade do equilíbrio; o eixo Y mede o custo em termos de desvio dos valores originais.

### 3.3 Métrica de Qualidade

Dentro de cada célula, a qualidade que determina qual solução é mantida é o `matchup_dominance_penalty`:

$$\text{matchup\_dominance\_penalty} = \max_{(i,j)} \left( \frac{\max\left(0,\ |\text{wr}_{ij} - 0{,}5| - \theta\right)}{0{,}5 - \theta} \right)$$

onde $\text{wr}_{ij}$ é a taxa de vitória do personagem $i$ contra $j$, e $\theta = 0{,}15$ é o limiar de tolerância (`MATCHUP_THRESHOLD`). O uso de $\max$ (em vez de média) garante que **um único matchup dominante force correção**, sem ser diluído pelos demais pares equilibrados.

Essa escolha separa as preocupações:

- **Onde a solução está no mapa** → determinado por `balance_error` e `drift_penalty`
- **Qual é a melhor solução naquela região** → determinado por `matchup_dominance_penalty`

### 3.4 Métricas de Avaliação

Cada indivíduo é avaliado via round-robin completo: $\binom{5}{2} = 10$ matchups, cada um com `SIMS_PER_MATCHUP` simulações de combate. As métricas derivadas são:

**Balance error** — desvio médio das taxas de vitória em relação a 50%:

$$\text{balance\_error} = \frac{1}{|\mathcal{M}|} \sum_{(i,j) \in \mathcal{M}} |\text{wr}_{ij} - 0{,}5|$$

onde $\mathcal{M}$ é o conjunto dos 10 pares de matchup.

**Drift penalty** — distância euclidiana normalizada ao perfil canônico, média sobre os 5 personagens:

$$\text{drift\_penalty} = \frac{1}{5} \sum_{k=1}^{5} d_k, \quad d_k = \sqrt{\frac{1}{n_g} \left( \sum_{a} \left(\frac{x_a - c_a}{m_a}\right)^2 + \sum_{w} (x_w - c_w)^2 \right)}$$

onde $x_a$ são os atributos evoluídos, $c_a$ os valores canônicos, $m_a$ os tetos de normalização, $x_w$ os pesos comportamentais evoluídos, $c_w$ os pesos canônicos, e $n_g = 12$ é o número de genes por personagem (9 atributos + 3 pesos).

---

## 4. Fronteira de Trade-off e Calibração de Lambdas

### 4.1 Fronteira Empírica

Ao final da execução, o MAP-Elites produz uma **fronteira de trade-off**: para cada nível de `drift_penalty` (cada linha do grid), seleciona-se a célula com menor `balance_error`. Isso define uma curva Pareto empírica:

$$\mathcal{F} = \left\{ \left(\text{bal}^*_{y},\ \text{drift}_y\right) \mid y \in \{0, \ldots, 7\} \right\}$$

Essa curva responde à pergunta central: *dado que toleramos um certo grau de desvio dos valores canônicos, qual o melhor equilíbrio competitivo que se consegue atingir?*

### 4.2 Detecção do Joelho

O ponto de joelho (*knee point*) da curva é identificado pelo método de **máxima distância perpendicular** à reta que une os extremos da fronteira. Para cada ponto $p_i = (\text{bal}_i, \text{drift}_i)$, computa-se:

$$\text{dist}_i = \frac{|\Delta y \cdot \text{bal}_i - \Delta x \cdot \text{drift}_i + x_2 y_1 - y_2 x_1|}{\sqrt{\Delta x^2 + \Delta y^2}}$$

onde $(x_1, y_1)$ e $(x_2, y_2)$ são os pontos extremos da fronteira, e $\Delta x = x_2 - x_1$, $\Delta y = y_2 - y_1$.

O joelho representa a região de **maior ganho marginal**: antes dele, pequenas reduções de drift geram grandes ganhos de equilíbrio; após ele, o retorno diminui. É o ponto naturalmente indicado para calibrar $\lambda_{\text{drift}}$.

### 4.3 Calibração de λ_drift

O valor sugerido para $\lambda_{\text{drift}}$ é calculado como a razão entre as variações locais de `balance_error` e `drift_penalty` no joelho:

$$\lambda_{\text{drift}} = \left| \frac{\Delta \text{balance\_error}}{\Delta \text{drift\_penalty}} \right|_{\text{joelho}}$$

**Interpretação:** se no joelho uma redução de 0,1 em `drift_penalty` custa 0,05 de `balance_error`, então $\lambda_{\text{drift}} = 0{,}5$. Esse valor faz com que, na função de fitness do AG, o custo de 0,1 de drift seja exatamente equivalente a 0,05 de desequilíbrio — calibrando as escalas de forma consistente com a geometria real do espaço.

### 4.4 Calibração de λ_matchup

O valor sugerido para $\lambda_{\text{matchup}}$ é:

$$\lambda_{\text{matchup}} = \frac{1}{\max(\text{pen\_range},\ 0{,}1)}, \quad \text{pen\_range} = \max(\text{matchup\_pen}) - \min(\text{matchup\_pen})$$

onde `matchup_pen` são os valores de `matchup_dominance_penalty` dos pontos da fronteira. Isso normaliza a penalidade de matchup para que sua escala seja comparável à do `balance_error`.

---

## 5. Design Decisions Relevantes

### Por que o MAP-Elites roda sem pressão de drift?

O `LAMBDA_DRIFT = 0.0` durante a execução do MAP-Elites é **intencional**. O objetivo não é produzir soluções que minimizem drift — é explorar livremente o espaço para descobrir o que é possível em cada região da grade. Se drift fosse penalizado durante a exploração, o algoritmo sub-amostraria artificialmente as regiões de alto drift, tornando a fronteira empírica enviesada e a calibração resultante incorreta.

Em outras palavras: o MAP-Elites é o **experimento de calibração**, não uma fase de otimização. Seus lambdas são o output, não o input.

### Separação entre descritor e qualidade

A arquitetura do MAP-Elites deliberadamente usa `balance_error` e `drift_penalty` como descritores comportamentais (eixos do grid), e `matchup_dominance_penalty` como métrica de qualidade dentro de cada célula. Essa escolha evita que o algoritmo confunda as três dimensões: uma solução pode ter baixo `balance_error` mas péssimo pior-caso de matchup, e o mapa preserva essa distinção ao comparar soluções apenas dentro da mesma célula.

### Cobertura do grid

Com 80 células e 50.000 iterações, o grid raramente fica completamente preenchido — a maioria das mutações cai em células já ocupadas. O objetivo não é cobertura total, mas sim cobertura **suficiente da fronteira** para que o joelho possa ser detectado com confiança. Células interiores (longe da fronteira Pareto) são menos críticas para a calibração.

---

## 6. Parâmetros de Execução

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `GRID_X_BINS` | 10 | Bins no eixo `balance_error` |
| `GRID_Y_BINS` | 8 | Bins no eixo `drift_penalty` |
| `GRID_X_MAX` | 0.5 | Valor máximo de `balance_error` no grid |
| `GRID_Y_MAX` | 0.6 | Valor máximo de `drift_penalty` no grid |
| `N_INIT` | 200 | Indivíduos na inicialização |
| `N_ITERATIONS` | 50.000 | Iterações do loop principal |
| `SIMS_PER_MATCHUP` | 15 | Simulações por matchup na avaliação |

---

## 7. Integração com o Sistema Principal

O fluxo de uso do MAP-Elites no contexto deste trabalho é:

```
1. Executar map_elites.py
      ↓
2. Observar fronteira de trade-off e joelho
      ↓
3. Copiar os valores sugeridos de LAMBDA_DRIFT e LAMBDA_MATCHUP
      ↓
4. Atualizar config.py com esses valores
      ↓
5. Executar main.py (AG principal)
```

O MAP-Elites **não é parte do AG principal** — é uma ferramenta auxiliar de análise e calibração que deve ser executada uma vez antes do experimento definitivo, ou sempre que os parâmetros de simulação forem alterados de forma significativa (ex.: mudança em `DAMAGE_VARIANCE`, `ACTION_EPSILON`, ou na definição dos arquétipos canônicos).

---

## Referência

Mouret, J.-B., & Clune, J. (2015). Illuminating search spaces by mapping elites. *arXiv preprint arXiv:1504.04909*.
