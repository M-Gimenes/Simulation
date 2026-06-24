# 08 — Metodologias da literatura: o que vale incorporar ao sistema

**Entra em**: Metodologia (procedimento experimental), Discussão e Trabalhos Futuros.

> Leitura das metodologias dos papers do `.bib` (ver `overleaf/TCC/bibliografia.bib`)
> filtrada pelo **que é aplicável a ESTE sistema** (AG/NSGA-II balanceando 5
> arquétipos via combate 1v1 round-robin). Cada item: **o que o paper faz → como
> mapeia no nosso sistema → o que ganha → custo/prioridade**. Não é revisão
> bibliográfica genérica; é um backlog metodológico priorizado.

O sistema hoje roda **uma execução** (uma seed) e lê o resultado por inspeção
(dossiê, `drift_table`, `fingerprint`, validador). Isso é suficiente pra mostrar
*que funciona*, mas a literatura de computação evolutiva e de balanceamento por
busca dá um **protocolo experimental** que torna o resultado defensável e mais
robusto. Os achados recentes (ex.: o matchup Combo×Rush travado em uma única seed —
ver [07](07-achados-e-limitacoes.md)) são exatamente o tipo de coisa que esse
protocolo pega.

---

## Tier 1 — Adotar já (baixo custo, alto retorno)

### 1.1 Múltiplas execuções independentes + estatística agregada
**Fontes:** Eiben & Smith 2015 (cap. *Working with Evolutionary Algorithms*); Deb 2001.

**O que fazem:** um EA é estocástico, então **uma rodada não é um resultado** — é
uma amostra. A prática padrão é rodar *N* execuções independentes (sementes
distintas) e reportar **média ± desvio** das métricas, além de *success rate* (quantas
rodadas atingiram o critério), *MBF* (mean best fitness) e, ao comparar duas
configurações, um **teste estatístico** não-paramétrico (Mann–Whitney / Wilcoxon).

**No nosso sistema:** rodar o NSGA-II (e o AG escalar) com seeds fixas `42..46`
(≥ 5, idealmente 10–30), e agregar:
- distribuição de `dominance_penalty` / `drift_penalty` do `best_dominance` por seed;
- fração de seeds que equilibram cada matchup (ex.: Combo×Rush);
- WR média ± desvio por personagem **através das seeds**.

**O que ganha:** mata a fragilidade de amostra única — o stun-lock Combo×Rush pode
ser "azar de uma seed" ou estrutural, e só *N* rodadas respondem. Vira a frase de
tese: *"em 30 execuções, X% equilibraram todos os 10 matchups; WR média 50±k%"*.
É **o exemplo que você citou** (rodar várias vezes e agregar), e é a base de tudo.

**Custo/prioridade:** baixo (só tempo de CPU + um script de agregação). **🟢 Alta.**

### 1.2 Métricas quantitativas de qualidade da fronteira de Pareto
**Fontes:** Deb 2001 (cap. de métricas); Deb et al. 2002 (NSGA-II).

**O que fazem:** comparar fronteiras de Pareto "no olho" não escala. A literatura
usa indicadores numéricos: **hipervolume** (área/volume dominado em relação a um
ponto de referência — captura convergência *e* espalhamento num número só) e
**spread/spacing** (uniformidade da distribuição dos pontos na fronteira).

**No nosso sistema:** calcular hipervolume da fronteira `(dominance, drift)` por
seed (ponto de referência fixo, ex.: `(1.5, 1.0)` = piores valores possíveis) e
reportar média ± desvio. Adiciona uma curva/coluna aos plots NSGA-II que já existem
(`nsga2_plots`).

**O que ganha:** comparação objetiva entre seeds e entre configurações (ex.: efeito
de `HESITATION_RATE` ou de `SIMS_PER_MATCHUP` na qualidade da fronteira), sem
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
manter as builds (os 9 atributos) e **coevoluir uma "estratégia adversária"** (os 3
pesos, ou uma política mais rica) que tenta *quebrar* o equilíbrio. Se um exploit
existe (como o stun-lock Combo×Rush), a coevolução o encontra.

**O que ganha:** responde a pergunta crítica *"o equilíbrio é robusto ou só vale
para a política assumida?"* — uma das objeções mais fortes que a banca pode levantar.
Transforma o stun-lock de achado anedótico em teste sistemático de robustez.

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
gene) para *restrição de ações*: rodar o combate desligando ATTACK/DEFEND/RETREAT de
um lado e medir o Δ-WR. Aplicado ao Combo×Rush, mostra **quanto do 100/0 vem do
stun-lock** (ex.: limitar o re-stun e ver a WR mover).

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
`MUTATION_RATE`/`TOURNAMENT_SIZE`/`ELITE_SIZE`.

**Custo/prioridade:** baixo. **🟡 Baixa** — bom como diagnóstico de apoio.

---

## Resumo priorizado

| # | Metodologia | Fonte | Esforço | Prioridade |
|---|---|---|---|---|
| 1.1 | N execuções + estatística agregada | Eiben&Smith 2015; Deb 2001 | Baixo | 🟢 **Alta** |
| 1.2 | Hipervolume + spread da fronteira | Deb 2001/2002 | Baixo | 🟢 **Alta** |
| 3.2 | Bateria + validação externa ao fitness | Browne 2010 | Baixo | 🟢 Média-alta |
| 2.1 | Coevolução p/ stress-test do equilíbrio | Chen 2014; Livingstone 2006 | Médio-alto | 🟡 Média-alta |
| 2.2 | Restricted play / handicap de mecânicas | Hom 2007; Jaffe 2012 | Médio | 🟡 Média |
| 3.1 | MAP-Elites / Novelty (fingerprint = descritor) | Mouret 2015; Lehman 2011 | Alto | 🟡 Média (futuro) |
| 4.1 | Penalidade adaptativa de drift | Michalewicz 1996 | Baixo-médio | 🟡 Baixa (exp.) / 🟢 Alta (cite) |
| 4.2 | Diagnóstico de diversidade | Eiben 1998; Whitley 1994 | Baixo | 🟡 Baixa |

**Se for fazer só uma coisa:** 1.1 (N execuções agregadas) — é o piso metodológico,
resolve a fragilidade de seed única e é o que a banca vai cobrar primeiro. **Se for
fazer duas:** 1.1 + 1.2 (hipervolume), que juntas dão o protocolo experimental
completo do lado evolutivo. As de maior valor *científico* (não só de rigor) são 2.1
(coevolução) e 3.1 (QD) — fortes como trabalho futuro mesmo que não entrem agora.

> **Nota de fonte:** as metodologias de Hom 2007, Chen 2014, Browne 2010 foram
> conferidas no resumo dos artigos; Preuss et al. 2012 (CEC) não foi localizado com
> precisão na busca — **verificar o escopo exato na fonte** antes de afirmar sua
> contribuição metodológica na tese.
