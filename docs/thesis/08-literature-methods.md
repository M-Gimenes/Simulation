# 08 — Metodologias da literatura: o que vale incorporar ao sistema

**Entra em**: Metodologia (procedimento experimental), Discussão e Trabalhos Futuros.

> Leitura das metodologias dos papers do `.bib` (ver `overleaf/TCC/bibliografia.bib`)
> filtrada pelo **que é aplicável a ESTE sistema** (AG/NSGA-II balanceando 5
> arquétipos via combate 1v1 round-robin). Cada item: **o que o paper faz → como
> mapeia no nosso sistema → o que ganha → custo/prioridade**. Não é revisão
> bibliográfica genérica; é um backlog metodológico priorizado.

Originalmente o sistema lia o resultado de **uma execução** (uma seed) por inspeção
(dossiê, `drift_table`, `fingerprint`, validador) — suficiente pra mostrar *que
funciona*, mas frágil. A literatura de computação evolutiva e de balanceamento por
busca dá um **protocolo experimental** que torna o resultado defensável e mais
robusto. Os itens de **Tier 1** desse protocolo (mais o 3.2) **já foram incorporados**
ao sistema — ver a seção de status ao final; os achados de seed única (um par travado
numa seed) são exatamente o que ele pega.

> **Nota:** os itens abaixo descrevem cada metodologia da literatura. O **estado de
> adoção** de cada uma (implementado / citar / futuro) e o racional de escopo estão
> na seção **[Status de implementação e decisão de escopo](#status-de-implementação-e-decisão-de-escopo-2026-06-24)**
> ao final — leia-a primeiro para saber o que já é parte do sistema.

---

## Tier 1 — Adotar já (baixo custo, alto retorno)

### 1.1 Múltiplas execuções independentes + estatística agregada
**Fontes:** Eiben & Smith 2015 (cap. *Working with Evolutionary Algorithms*); Deb 2001.

**O que fazem:** um EA é estocástico, então **uma rodada não é um resultado** — é
uma amostra. A prática padrão é rodar *N* execuções independentes (sementes
distintas) e reportar **média ± desvio** das métricas, além de *success rate* (quantas
rodadas atingiram o critério), *MBF* (mean best fitness) e, ao comparar duas
configurações, um **teste estatístico** não-paramétrico (Mann–Whitney / Wilcoxon).

**No nosso sistema:** rodar o NSGA-II (e o AG escalar) com as mesmas seeds fixas
(`MULTI_RUN_SEED_START..+N−1`, default 42..51), agregar (headline C2) e comparar os
dois algoritmos com teste + tamanho de efeito (`compare_algorithms`):
- distribuição de `dominance_penalty` / `drift_penalty` do `best_dominance` por seed;
- fração de seeds em que cada boneco fica equilibrado (WR global em [40%, 60%]) e em
  que aparece algum hard-counter (par fora de [35%, 65%]);
- WR global média ± desvio por personagem **através das seeds**.

**O que ganha:** mata a fragilidade de amostra única — um par travado pode ser "azar
de uma seed" ou estrutural, e só *N* rodadas respondem. Vira a frase de tese:
*"em 30 execuções, X% equilibraram o roster (5 bonecos em banda, 0 hard-counters); WR global média 50±k%"*.
É **o exemplo que você citou** (rodar várias vezes e agregar), e é a base de tudo.

**Custo/prioridade:** baixo (só tempo de CPU + um script de agregação). **🟢 Alta.**

### 1.2 Métricas quantitativas de qualidade da fronteira de Pareto
**Fontes:** Deb 2001 (cap. de métricas); Deb et al. 2002 (NSGA-II).

**O que fazem:** comparar fronteiras de Pareto "no olho" não escala. A literatura
usa indicadores numéricos: **hipervolume** (área/volume dominado em relação a um
ponto de referência — captura convergência *e* espalhamento num número só) e
**spread/spacing** (uniformidade da distribuição dos pontos na fronteira).

**No nosso sistema:** calcular hipervolume da fronteira `(dominance, drift)` por
seed (ponto de referência fixo, `(1.3, 0.4)`, ancorado nos modelos nulos) e
reportar média ± desvio. Adiciona uma curva/coluna aos plots NSGA-II que já existem
(`nsga2_plots`).

**O que ganha:** comparação objetiva entre seeds e entre configurações (ex.: efeito
de `MATCHUP_WR_CAP` ou de `SIMS_PER_MATCHUP` na qualidade da fronteira), sem
depender de inspeção visual. Métrica madura e esperada por banca.

**Custo/prioridade:** baixo (hipervolume 2D é trivial). **🟢 Alta.**

---

## Tier 2 — Alto valor científico (mais esforço, fortalecem a validade)

### 2.1 Coevolução para *stress-test* do equilíbrio
**Fontes:** Chen, Mori & Matsuba 2014 (PIPE + algoritmo coevolutivo cooperativo p/
balancear MMORPG); Livingstone 2006 (coevolução em IA de estratégia).

**O que fazem:** em vez de avaliar contra um adversário fixo, **coevoluem** os
agentes/estratégias junto com o conteúdo, de modo que o equilíbrio precise
sobreviver a um oponente que *se adapta* — não a uma política congelada.

**No nosso sistema:** hoje o comportamento é a *soft-policy* fixa (pesos `w_*`). Um
risco real: o equilíbrio observado pode ser **artefato da política fixa**. Proposta —
manter as builds (os 8 atributos) e **coevoluir uma "estratégia adversária"** (os 3
pesos, ou uma política mais rica) que tenta *quebrar* o equilíbrio. Se um exploit
existe contra o roster evoluído, a coevolução o encontra.

**O que ganha:** responde a pergunta crítica *"o equilíbrio é robusto ou só vale
para a política assumida?"* — uma das objeções mais fortes que a banca pode levantar.
Transforma a busca por exploits de inspeção anedótica em teste sistemático de
robustez.

**Custo/prioridade:** médio-alto (novo loop coevolutivo). **🟡 Média-alta** — forte
candidato a *trabalho futuro* se não couber no escopo atual.

### 2.2 *Restricted play* / análise por handicap das mecânicas
**Fontes:** Hom & Marks 2007 (balanço via *playouts* simulados + motor de jogo
genérico); Jaffe et al. 2012, *Evaluating Competitive Game Balance with Restricted
Play* (surge na mesma linha — **verificar a fonte**: é AIIDE 2012, peer-reviewed,
apesar de ter sido marcada como duvidosa no `.md` antigo).

**O que fazem:** medem a contribuição de uma mecânica ao equilíbrio **restringindo**
um jogador (proibindo uma ação, fixando um parâmetro) e observando o quanto o
resultado muda. Se restringir a ação X não altera a WR, X é irrelevante ao balanço.

**No nosso sistema:** generaliza o `sensitivity_analysis` (que já perturba ±σ por
gene) para *restrição de ações*: rodar o combate desligando uma postura
(ADVANCE / RETREAT / DEFEND) ou o agarrão de um lado e medir o Δ-WR. Aplicado a um par
travado, mostra **quanto do desequilíbrio vem de cada mecânica**.

**O que ganha:** diagnóstico causal das mecânicas (não só "o gene importa", mas
"*por qual mecânica* ele importa"), e uma ferramenta para classificar mecânicas
degeneradas. Liga direto à teoria competitiva de Sirlin (2.4 abaixo).

**Custo/prioridade:** médio (instrumentar restrição no JIT/`CombatTrace`). **🟡 Média.**

---

## Tier 3 — Reformular o problema (diversidade de soluções)

### 3.1 Quality-Diversity / MAP-Elites + Novelty Search
**Fontes:** Mouret & Clune 2015 (MAP-Elites, *illuminating search spaces*); Lehman &
Stanley 2011 (*novelty search* — abandonar o objetivo).

**O que fazem:** em vez de procurar *a* melhor solução, **iluminam** o espaço:
mantêm um arquivo de soluções de alto desempenho indexado por um **descritor
comportamental** (não pelo objetivo). MAP-Elites reporta *coverage* (quantas células
preenchidas) e *QD-score*. Novelty search recompensa ser *diferente* do já visto.

**No nosso sistema:** já temos o descritor pronto — o **`fingerprint`** (distribuição
ATK/ADV/RET/DEF por personagem). Proposta: rodar MAP-Elites com 2 dimensões
comportamentais do *roster* (ex.: agressividade média × dispersão de estilos) e
guardar, em cada célula, a build mais equilibrada (`dominance` mínimo). O resultado é
um **mapa de rosters equilibrados E distintos**, não um único ponto.

**O que ganha:** ataca diretamente a tese de "equilíbrio *sem* destruir identidade":
mostra *quantas* configurações distintas de roster atingem equilíbrio, em vez de uma.
Complementa a fronteira de Pareto (que vê só `dominance × drift`, sem o eixo
comportamental). E o argumento de não-circularidade do Lehman (não codificar o
objetivo) **ecoa o seu** (não codificar o ciclo) — conexão teórica de alto valor.

**Custo/prioridade:** alto (novo algoritmo). **🟡 Média** como *trabalho futuro*;
o gancho teórico (Lehman ↔ não-circularidade) vale citar **já** na Discussão.

### 3.2 Bateria de métricas + validação externa ao fitness
**Fonte:** Browne & Maire 2010 (Ludi: qualidade via *self-play* + bateria de
critérios mensuráveis; validação culminando em jogos publicáveis/jogados por humanos).

**O que fazem:** não confiam num número de fitness só — avaliam o artefato evoluído
contra **um conjunto** de indicadores quantitativos independentes e depois validam
*fora* do laço de otimização (jogo real / humanos).

**No nosso sistema:** já temos a bateria (ciclo post-hoc, `drift_table`,
`fingerprint`, `archetype_validator`). O que falta é o **passo de validação externa**:
confirmar o `best_dominance` num protocolo independente do fitness — ex.: `N`
simulações com seed totalmente nova, ou contra uma política diferente da treinada
(liga-se a 2.1). Enquadrar a bateria atual como "metodologia estilo Ludi" já
fortalece a seção de validação.

**O que ganha:** blinda contra *overfitting ao fitness* (equilíbrio que só existe sob
as condições exatas do treino). Baixo custo, alto efeito retórico.

**Custo/prioridade:** baixo (reusa o que existe). **🟢 Média-alta.**

---

## Tier 4 — Refinamentos pontuais

### 4.1 Penalidade adaptativa para preservação de identidade
**Fonte:** Michalewicz & Schoenauer 1996 (tratamento de restrições em EAs: penalidades
estáticas vs dinâmicas vs adaptativas; *vale a referência também pra justificar a
escolha atual de penalidade soft em vez de restrição rígida*).

**O que fazem:** comparam esquemas de penalidade; penalidades **dinâmicas** (peso
cresce com a geração) permitem explorar cedo e apertar a restrição no fim.

**No nosso sistema:** o `LAMBDA_DRIFT` é fixo (1.0). Um *schedule* (drift solto cedo,
apertando ao longo das gerações) poderia deixar o AG escalar explorar builds ousadas
antes de puxar de volta à identidade. Aplicável **só ao AG escalar** (o NSGA-II é sem
peso, por design). Vale também como **citação de metodologia** pra justificar a
penalidade soft já adotada.

**Custo/prioridade:** baixo-médio. **🟡 Baixa** como experimento; **🟢 Alta** como
*citação* na Metodologia (preenche a lacuna de `metodologia.tex`, hoje sem citações).

### 4.2 Diagnóstico de diversidade / convergência prematura
**Fontes:** Eiben & Schippers 1998 (exploração×explotação); Whitley 1994 (pressão de
seleção, *takeover time*).

**O que fazem:** monitoram a **diversidade populacional** ao longo das gerações pra
detectar convergência prematura (população colapsa antes de achar boas soluções).

**No nosso sistema:** plotar a diversidade genética por geração (já temos histórico
no `ga.py`/`nsga2.py`). Se a população colapsa cedo, justifica mexer em
`MUTATION_RATE`/`TOURNAMENT_SIZE`/`ELITE_RATE`.

**Custo/prioridade:** baixo. **🟡 Baixa** — bom como diagnóstico de apoio.

> **Feito em 2026-09-22, e achou algo.** O diagnóstico saiu de "se sobrar tempo" para
> achado: na réplica instrumentada da seed 42, o drift mínimo da população sai de 0,0000
> (a semente canônica) para 0,17 em **g7** e 0,24 em g20, quando `dominance` ainda tinha
> 1,13 dos seus 1,35 por entregar — e daí em diante mínimo, p10 e mediana ficam a ~0,005
> um do outro. **É convergência prematura no eixo da identidade**, e é o mecanismo por trás
> de o AG escalar não ser ótimo na própria função (→
> [07](07-findings-and-limitations.md)). Note que o remédio não foi mexer em
> `MUTATION_RATE`/`TOURNAMENT_SIZE`/`ELITE_RATE` como o item previa — o sweep desses três
> não domina os defaults —, e sim **decompor o objetivo**: ver 4.3.

### 4.3 Multi-objetivização como robustez a ruído
**Fontes:** Knowles, Watson & Corne 2001 (*Reducing local optima in single-objective
problems by multi-objectivization*); Jensen 2004 (funções auxiliares); Fieldsend & Everson
2015 (otimização multiobjetivo sob avaliação ruidosa).

**O que fazem:** decompor um objetivo único em vários e otimizá-los por dominância de
Pareto muda a paisagem de busca — ótimos locais do escalar deixam de ser ótimos, e
extremos da fronteira ficam protegidos da extinção.

**No nosso sistema:** é a explicação do achado de 2026-09-22, e a leitura vai além da
fonte original. O escalar soma um termo **ruidoso** (`dominance`, desvio 0,015–0,028) com
um **determinístico** (`drift`); passada a convergência, a seleção responde ao ruído do
primeiro e a linhagem fiel morre. No NSGA-II o `drift` é objetivo separado e sem ruído, e
o extremo de drift baixo fica **imortal no rank 0** pela crowding infinita. A
multi-objetivização aqui não está removendo ótimo local — está **protegendo a linhagem que
o ruído mataria**. O híbrido (NSGA-II → AG escalar, orçamento igual) explora as duas
coisas: a decomposição preserva a diversidade, o escalar refina o equilíbrio.

**Custo/prioridade:** já medido nas sementes 42–46; falta escolher nas 1000–1004 e rodar a
bateria. **🟢 Alta** se o achado se sustentar — é contribuição de método, não ferramenta.

---

## Resumo priorizado

| # | Metodologia | Fonte | Esforço | Status |
|---|---|---|---|---|
| 1.1 | N execuções + estatística agregada | Eiben&Smith 2015; Deb 2001 | Baixo | ✅ **Implementado** (`multi_run.py`) |
| 1.2 | Hipervolume + spacing da fronteira | Deb 2001/2002 | Baixo | ✅ **Implementado** (`pareto_metrics.py`) |
| 3.2 | Bateria + validação externa ao fitness | Browne 2010 | Baixo | ✅ **Implementado** (`external_validation.py`) |
| 2.1 | Coevolução p/ stress-test do equilíbrio | Chen 2014; Livingstone 2006 | Médio-alto | 🔭 Trabalho futuro (citar) |
| 2.2 | Restricted play / handicap de mecânicas | Hom 2007; Jaffe 2012 | Médio | 🔭 Futuro / opcional |
| 3.1 | MAP-Elites / Novelty (fingerprint = descritor) | Mouret 2015; Lehman 2011 | Alto | 🔭 Trabalho futuro (citar gancho teórico) |
| 4.1 | Penalidade adaptativa de drift | Michalewicz 1996 | Baixo-médio | 📚 Citar (justifica penalidade soft) |
| 4.2 | Diagnóstico de diversidade | Eiben 1998; Whitley 1994 | Baixo | ⚪ Opcional (figura de apoio) |

> **Nota de fonte:** as metodologias de Hom 2007, Chen 2014, Browne 2010 foram
> conferidas no resumo dos artigos; Preuss et al. 2012 (CEC) não foi localizado com
> precisão na busca — **verificar o escopo exato na fonte** antes de afirmar sua
> contribuição metodológica na tese.

---

## Status de implementação e decisão de escopo (2026-06-24)

Revisão de escopo para um **TCC de graduação**: o objetivo é um sistema
metodologicamente sólido **sem over-scoping**. O aparato de medição já está acima da
régua de graduação; o risco a partir daqui não é falta de método, é o oposto — uma
tese rica em maquinário e pobre em achados. **O valor seguinte estava em rodar os
experimentos reais e interpretar os números, não em construir mais ferramentas** — e
eles foram rodados: `multi_run` com 20 sementes, comparação estatística, validação
externa e modelos nulos (resultados no `docs/status/HANDOFF.md` §2). Decisão tomada:

### ✅ Implementado — entra como Metodologia + Resultados
- **1.1 — N execuções + estatística agregada** (`src/experiments/multi_run.py`): roda AG
  escalar e NSGA-II sobre N sementes (parametrizado em `config.py`, `MULTI_RUN_*`);
  agrega dominance/drift média±σ, WR global por boneco + fração de sementes que o
  equilibram, hard-counters por execução, e a fração de sementes que equilibram o
  roster. Reavalia cada melhor indivíduo sob uma seed de validação comum (Common
  Random Numbers). → Metodologia (protocolo experimental) + Resultados (a frase-tese
  *"em N execuções, X% equilibraram o roster"*).
- **1.2 — Hipervolume + spacing** (`src/engine/pareto_metrics.py`): qualidade da
  fronteira `(dominance, drift)` num número (ref `HYPERVOLUME_REFERENCE=(2.0,1.0)`).
  Impresso no run, anotado no plot, agregado por seed no `multi_run`. → Metodologia +
  Resultados (qualidade/comparação de fronteiras sem inspeção visual).
- **3.2 — Validação externa ao fitness** (`src/experiments/external_validation.py`): fixa
  UM indivíduo e o reavalia sob K sementes de avaliação **novas** (≥10000), com
  veredito robusto/frágil do roster e a contagem de condições em que cada par e cada
  boneco falham. → Metodologia (validação estilo Ludi; blinda contra overfitting ao
  fitness).
- **1.1 (parte estatística) — teste não-paramétrico** (`src/experiments/compare_algorithms.py`):
  fecha o item que faltava do 1.1. Sobre as amostras por semente do `multi_run`, aplica
  **Mann-Whitney U** bicaudal + tamanho de efeito **Â₁₂ de Vargha-Delaney** + correção
  de **Holm-Bonferroni** na família de métricas comparadas. Antes, AG e NSGA-II eram agregados
  lado a lado mas nunca comparados formalmente — "média X < média Y" não é resultado
  sem teste. → Metodologia (procedimento de comparação) + Resultados (AG escalar vs
  NSGA-II com p e efeito, não só médias).

Detalhe técnico de cada um na referência: [`../reference/08-tools.md`](../reference/08-tools.md),
[`../reference/06-nsga2.md`](../reference/06-nsga2.md), [`../reference/07-configuration.md`](../reference/07-configuration.md).

### 📚 Não implementar — citar (custo zero, fecha o capítulo)
- **4.1 — Penalidade adaptativa** (Michalewicz & Schoenauer 1996): citar para
  **justificar a penalidade soft já adotada** (`LAMBDA_DRIFT` fixo, deviação penalizada
  e não restringida) em vez de restrição rígida. Implementar o *schedule* é experimento
  opcional sem retorno claro num TCC.

### 🔭 Trabalho futuro — citar como direção, não implementar
- **2.1 — Coevolução** (Chen 2014; Livingstone 2006) e **3.1 — MAP-Elites / Novelty**
  (Mouret 2015; Lehman 2011): contribuições de pesquisa próprias; implementá-las
  viraria outro projeto. Valem como **Trabalhos Futuros**, e o gancho teórico
  **Lehman ↔ não-circularidade** (não codificar o objetivo ↔ não codificar o ciclo)
  é forte na Discussão.
- **2.2 — Restricted play** (Hom 2007; Jaffe 2012): baixo/médio custo e útil, mas **não é
  requisito**. Fica como "se sobrar tempo" / trabalho futuro.

### ⏳ Reclassificado em 2026-09-22
- **4.2 — Diagnóstico de diversidade** (Eiben 1998; Whitley 1994) saiu de "se sobrar
  tempo" para **feito, e com achado**: a população colapsa no eixo da identidade na
  geração 7. Entra em Resultados/Discussão, não em Trabalhos Futuros.
- **4.3 — Multi-objetivização** (Knowles, Watson & Corne 2001; Jensen 2004; Fieldsend &
  Everson 2015) é **referência nova**, ainda fora dos três `.bib`. Sustenta a explicação do
  achado e, se o híbrido se sustentar nas sementes 1000–1004, a contribuição de método.
