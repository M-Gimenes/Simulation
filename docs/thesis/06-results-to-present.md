# 06 — Resultados a apresentar

**Entra em**: Resultados (e parte da Discussão).

Quais saídas o sistema produz, **qual delas mostrar** no capítulo de Resultados, e
**o que cada uma evidencia**. Como gerar cada tool: [`../reference/08-tools.md`](../reference/08-tools.md).

## 1. Dossiê de um indivíduo (`report`)

O artefato por-indivíduo. `py -m src.analysis.report --evolved` (ou `--nsga2 <rep>`)
reúne, num relatório único:

| Bloco | Evidencia |
|---|---|
| Cabeçalho: `fitness`, `drift_penalty`, `dominance_penalty` | onde o indivíduo está no trade-off |
| Matriz de matchups + WR global + tríades circulares | **equilíbrio** alcançado, e se os pares seguem decididos (as tríades só valem com pares decididos, e são em boa parte implicadas pelo equilíbrio; as arestas do ciclo autoral são descritivas — o canônico só realiza 6/10) |
| Tabela de drift por gene + `drift_penalty` | **identidade de genes** — *o preço pago* pela evolução |
| Diferenciação par-a-par (`ratio`) | **homogeneização** — os 5 ainda são distintos? |
| Fingerprint (canônico vs evoluído) | **identidade comportamental** — ainda joga como o arquétipo? (o Δ mistura o personagem com os oponentes, que também mudaram) |
| Validador (score /23: 18 estruturais + 5 comportamentais) + concordância de ranking (τ) | **identidade estrutural e funcional**. Nunca citar o score cru: o piso é ~6/23 e um roster aleatório chega a 10/23 — reportar a **posição** entre piso e teto (`baselines`), e ler a parte funcional (Layer 3, τ) separada da estrutural, que é endógena |

Apresentar o dossiê do(s) indivíduo(s) escolhido(s) — tipicamente o **canônico** (baseline)
e os representantes de interesse do NSGA-II.

## 2. Histórico de convergência do AG escalar

`run()` retorna `history` (lista de `GenerationStats`): `best/mean/worst fitness`,
`drift_penalty`, `dominance_penalty` por geração, e `ga.save_results` grava esse
histórico em `results/single_run/ga.json` junto com a semente e a condição de parada — a
curva sai do artefato, sem re-rodar. Plotar essas curvas mostra a **trajetória de
otimização** — o AG melhora? converge, estagna ou bate o teto de gerações? como drift
e dominância evoluem um contra o outro? É a evidência de que o processo *funciona*
(ou de onde ele empaca).

## 3. Fronteira de Pareto do NSGA-II (o artefato central)

`nsga2_plots` gera o gráfico **dominância × drift** com os 5 representantes
(`best_dominance`, `best_drift`, `knee_point`, `ideal_point`, `scalar_optimum`). **É a
peça que torna o trade-off explícito** e responde diretamente à pergunta de pesquisa:
- o extremo `best_dominance` = **equilíbrio com mais homogeneização** (drift alto);
- o extremo `best_drift` = **identidade preservada com menos equilíbrio**;
- o `knee_point` = melhor compromisso;
- o `scalar_optimum` = o ponto que minimiza a mesma soma que o AG escalar otimiza — o
  comparável dele.

Mostrar a fronteira **e** os dossiês (`report --nsga2 best_dominance` vs
`--nsga2 best_drift`) é o coração do capítulo: dá pra *ver* e *quantificar* o que se
ganha e se perde em cada ponta. O plot é anotado com **hipervolume** e **spacing**
(item 1.2) — o número que quantifica a qualidade da fronteira sem inspeção visual e
permite comparar configurações.

## 4. Comparação canônico × evoluído

A base de tudo: rodar o `report` no canônico estabelece o ponto de partida (drift 0,
ciclo de referência, comportamento de referência) contra o qual todo evoluído é lido.

## 4b. Modelos nulos — piso e teto de cada métrica (`baselines`)

Nenhuma métrica de identidade tem piso zero, então nenhuma pode ser citada crua. O
`baselines` mede o que cada uma marca **sem estrutura nenhuma** — rosters-espelho (cinco
cópias de um arquétipo: equilíbrio perfeito, identidade zero) e rosters aleatórios — e
reporta cada métrica como **posição entre piso e teto**, com p-valor empírico. Evidencia
duas coisas que a redação precisa: onde cada régua de identidade do evoluído fica em
relação ao acaso — lidas **separadas**, porque as estruturais são endógenas e vencer os
nulos nelas é quase garantido —, e a resposta numérica à objeção *"por que não deixar os
cinco iguais?"*: o espelho é a solução trivial do equilíbrio, e o evoluído é comparado a
ela (a leitura certa, se o `dominance` empatar com o do espelho, é "tão equilibrado quanto
a simetria perfeita, dentro do ruído", não "mais equilibrado"). O que os nulos **não**
fazem é isolar o efeito do termo de drift — isso é o controle `λ_drift = 0` (§5).

## 5. Estatística agregada de N execuções (`multi_run`)

**O resultado central do lado evolutivo** (item 1.1). Em vez de um indivíduo de uma
seed, a tabela agregada sobre 20 seeds:

| Saída | Evidencia |
|---|---|
| dominance/drift **média ± desvio** | onde o processo aterrissa *em média*, com dispersão |
| **WR global por personagem** (média ± desvio) | nenhum boneco domina o roster (o headline de equilíbrio sob C2) |
| **contagem de hard-counters** | quantos pares saem de `[0.35, 0.65]` — counters esmagadores |
| **fração de seeds que equilibram o roster** | a frase-tese — *"em N execuções, X% equilibraram o roster (5 bonecos em banda, 0 hard-counters)"* |
| decomposição do `dominance_penalty` | se a diferença veio do termo primário ou de um secundário |
| **identidade** por semente (validador estrutural, Layer 3, τ) | se o equilíbrio preservou a identidade — funcional e estrutural, lidas separadas |
| (AG escalar) **taxa e geração de convergência** | o eixo de velocidade, que o orçamento fixo abriu (convergir = primeiro equilíbrio confirmado, não equilíbrio no fim) |
| (NSGA-II) **hipervolume ± desvio** | qualidade média da fronteira através das seeds |

Os **controles** (`results/controls/`) têm a mesma tabela: o AG com `λ_drift = 0` e o AG sem
a semente canônica, cada um com 20 sementes no orçamento da bateria.

É a peça que transforma "funciona numa seed" em afirmação estatística — e contextualiza
achados de seed única (ex.: um par travado) como estruturais ou amostrais.

> **Nota (C2):** o headline de equilíbrio é a WR **global** por personagem + ausência
> de hard-counter, **não** "cada par a 50%". O `multi_run` já reporta nesse formato
> (fração de sementes que equilibram o roster); a banda por-matchup vira leitura
> secundária.

## 5b. AG escalar × NSGA-II, com teste (`compare_algorithms`)

As duas tabelas do `multi_run` colocam os algoritmos lado a lado, mas "média X <
média Y" não é resultado: com 20 execuções por algoritmo, a diferença ainda pode ser
amostragem. O `compare_algorithms` fecha isso — **Mann-Whitney U** bicaudal,
**Â₁₂ de Vargha-Delaney** (tamanho de efeito) e **Holm-Bonferroni** sobre uma família fixa
de 7 métricas (equilíbrio e identidade), sobre as mesmas sementes reavaliadas sob a mesma
condição de validação.

O que reportar: por métrica, mediana de cada lado, `p` corrigido e Â₁₂ — e a leitura em
uma frase (diferença significativa e para qual lado, ou ausência dela). Três comparações:

- **AG × NSGA-II**, com o NSGA-II representado pelo `scalar_optimum` (o comparável do
  escalar, decidido antes da bateria) e, ao lado, a **relação de Pareto por semente** — em
  quantas o ponto do AG domina algum ponto da fronteira, é dominado por ela, ou nenhum dos
  dois. É a leitura que não depende de escolher representante. O `best_dominance` fica como
  leitura secundária;
- **AG × `λ_drift = 0`** — o que o termo de drift preserva, régua por régua, e a que custo
  em equilíbrio. É o resultado que responde "o método preserva identidade?";
- **AG × sem semente canônica** — quanto da diferença AG × NSGA-II é inicialização.

## 6. Robustez do equilíbrio fora do laço (`external_validation`)

Item 3.2. Pega um indivíduo — a bateria roda o canônico, o melhor do AG, o
`scalar_optimum` e o `knee_point` — e responde duas perguntas com 5000 lutas por par:
a **replicação** (o equilíbrio se confirma sob as regras do treino, com sementes novas?) e
a **robustez** (ele sobrevive a cada regra perturbada — distância inicial, campo,
persistência, redução da guarda?). Cada condição sai ROBUSTA / FRÁGIL / INCONCLUSIVA pelo
IC de cada WR contra a banda. A tabela que junta o `dominance` de dentro do laço com o da
replicação evidencia que o equilíbrio reportado não é ajuste ao stream de treino; a de
robustez, se ele depende das regras exatas. Apresentar junto do dossiê do indivíduo.

## 7. Validação metodológica (sustentação)

- **Tabela de sensibilidade** (`sensitivity_analysis`): mostra quais dos 11 genes o AG
  enxerga pelo equilíbrio (ou quais são neutros — os pesos da política ficam no limiar),
  com artefato em `results/sensitivity/sensitivity_analysis.json`. Vai junto da
  metodologia, não dos resultados de um indivíduo. Ver [05](05-methodological-validation.md).
- **Reprodutibilidade**: reportar o seed usado em cada experimento.

## Artefatos que a redação não pode esquecer

Quatro números/figuras que a redação deve usar:

- **Decomposição do `dominance_penalty` nos três termos** (`global` / `cap` / `decis`),
  por semente e agregada — o `multi_run` grava, o `compare_algorithms` imprime lado a
  lado. Sem ela a frase "o algoritmo X vence em `dominance_penalty`" é ambígua: perder no
  termo primário (peso 1,0) e perder num secundário (peso 0,5) são leituras opostas do
  mesmo composto. **Nunca citar o composto sozinho numa comparação.**
- **Contagem de rejeições da confirmação de convergência.** O gate dispara N vezes e a
  confirmação fora do stream rejeita M delas — é o ajuste ao stream de RNG quantificado,
  em uma linha. Medido em 60 gerações: 16 disparos, 16 rejeições. Na bateria de n = 20 (150
  gerações): 70 disparos, 50 rejeições (71%), e mesmo assim as 20 sementes convergem, na
  geração 34,8 ± 17,1. Junto, sempre, a fração que **termina** equilibrada (14/20 naquela
  bateria): convergir é o primeiro sucesso de um teste repetido, não equilíbrio estável.
- **A fronteira do NSGA-II com e sem o seed canônico**, lado a lado. É a figura que
  mostra que um detalhe de inicialização consumia metade da fronteira — e serve de aviso
  metodológico na Discussão.
- **O representante `scalar_optimum` marcado na fronteira.** É o comparável correto do AG
  escalar (mínimo da soma ponderada que ele otimiza); o `ideal_point` é geométrico (o mais
  próximo do ponto utópico) e é outro ponto. Ao comparar escalar × NSGA-II, dizer qual
  representante está sendo usado — sempre. A bateria grava as duas comparações: contra o
  `scalar_optimum`, a manchete (`comparison_ga_vs_nsga2.json`), e contra o
  `best_dominance` (`comparison_ga_vs_nsga2_best_dominance.json`).
- **As duas comparações contra os controles** (`results/controls/comparison_ga_vs_*.json`).
  A de `λ_drift = 0` é a que diz se o método preserva identidade; sem ela, "a identidade
  do evoluído supera os nulos" não distingue o método de qualquer roster otimizado.

## O fio condutor dos Resultados

1. Estabelecer o **baseline** (canônico, deliberadamente desequilibrado) e os **modelos
   nulos** — o piso contra o qual toda métrica de identidade é lida
   ([07](07-findings-and-limitations.md)).
2. Mostrar a **fronteira de Pareto** (com hipervolume) — o trade-off equilíbrio ×
   identidade.
3. Detalhar **dossiês** de pontos-chave da fronteira (preserva vs equilibra), usando
   drift + diferenciação + fingerprint + validador para *quantificar* preservação vs
   homogeneização.
4. Subir de uma seed para a **estatística agregada de N execuções** (`multi_run` +
   `compare_algorithms`) — a evidência estatística —, isolar o efeito do método com os
   **controles**, e mostrar a **replicação e a robustez** do indivíduo central
   (`external_validation`).
5. Concluir sobre a **pergunta de pesquisa** a partir do que a fronteira, os dossiês e
   a agregação mostram.

> O que **não** vai nos resultados (é sobre o AG/processo, não sobre um indivíduo):
> detalhes de mecânica, e o "como" técnico — esses ficam na Metodologia, referenciando
> [`../`](../reference/README.md).
