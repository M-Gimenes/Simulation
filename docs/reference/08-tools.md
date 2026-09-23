# 08 — Ferramentas

Tudo o que consome o motor, em três pacotes divididos pelo que fazem com um roster
(critério em [02-architecture.md](02-architecture.md)). Todos rodam como módulo a partir
da raiz: `py -m src.analysis.<nome>`, `py -m src.experiments.<nome>`,
`py -m src.visualization.<nome>`.

## `src.analysis` — inspecionar um roster

Imprimem e não gravam nada. Operam sobre o canônico, o melhor do AG (`--evolved`) ou um
representante do NSGA-II (`--nsga2 [rep]`).

### `report` — dossiê do indivíduo (porta de entrada)

**Um comando** que compõe os tools de avaliação num relatório único: cabeçalho de
fitness (fitness, drift_penalty, dominance_penalty) + matchups (equilíbrio) + drift
de genes + diferenciação (homogeneização) + fingerprint (comportamento) + validador
(estrutura) + **modelos nulos** (piso, teto e posição de cada métrica). Não duplica
lógica — chama as funções dos outros tools.

A seção de modelos nulos vem por último de propósito: ela é o que dá sentido às
anteriores. Valor cru de identidade não diz nada sem o piso, e os pisos deste projeto
estão longe de zero. Os rosters de referência são **recalculados a cada execução** e
nunca lidos de cache — baseline silenciosamente obsoleto é exatamente o erro que o dossiê
existe para evitar. Os defaults (`--seed`, `--n`) são os do `baselines`
(`MULTI_RUN_VALIDATION_SEED`, `MULTI_RUN_SIMS`), e o validador da seção de identidade roda
com `IDENTITY_BEHAVIORAL_SIMS`, como o `baselines.measure` — assim a tabela de nulos do
dossiê é a mesma do `baselines.json`, e o placar impresso é o `valor` da tabela de
posição.

```bash
py -m src.analysis.report --evolved              # dossiê completo do melhor do AG
py -m src.analysis.report --nsga2 scalar_optimum
py -m src.analysis.report --evolved --n-random 60   # mais nulos = mais resolução no p
```

Os tools abaixo continuam rodando isolados (pra quando você quer só um ângulo), e
os de propósito diferente (`sensitivity_analysis`, `viewer`, `nsga2_plots`) ficam
**fora** do dossiê.

### `analyze_matchups`

Roda os 10 matchups (ou um par específico) com N simulações cada e reporta
estatísticas, matriz de WR e resumos.

```bash
py -m src.analysis.analyze_matchups                       # todos, canônico, N=1000
py -m src.analysis.analyze_matchups rushdown zoner        # par específico
py -m src.analysis.analyze_matchups --evolved --n 50      # indivíduo evoluído
py -m src.analysis.analyze_matchups --nsga2 knee_point    # representante do Pareto
py -m src.analysis.analyze_matchups --seed 42             # ver ressalva de seed abaixo
```

Saídas: estatísticas por luta (hits, dano, stun, ticks em/fora de range, mix de
ações, KO-rate, duração, distância), **matriz 5×5** de WR — cada célula marcada pelo
veredito de counter do par, a mesma banda do resumo — e os resumos (alinhados ao
headline **C2**):

- **WR global por personagem (headline):** alvo 50%; `= Equilibrado` em `[40%, 60%]`
  (via `fitness.character_balanced`), `⬆` domina, `⬇` fraco. É o eixo principal de
  equilíbrio — nenhum boneco domina o roster.
- **Counter por par** (cego à direção): `✗ counter duro` só quando o par sai de
  `[35%, 65%]` (`fitness.is_hard_counter`, `|WR − 50%| > MATCHUP_WR_CAP`); dentro do
  teto é `=` (aresta de ciclo permitida, não desbalanço). Leitura secundária ao
  headline global.
- **Ciclo canônico** (descritivo, não pass/fail): o favorito observado bate com o
  vencedor esperado pelo ciclo? `→ mantido` / `↯ invertido`. O ciclo é métrica
  *post-hoc*, nunca alvo.

### `drift_table`

Decompõe o `drift_penalty` por personagem e por gene: canônico vs evoluído, Δ
absoluto, Δ normalizado e o **peso do gene no drift**. Mesma normalização do fitness
(`fitness.gene_drift`): fração do range do bound, `(x − lo)/(hi − lo)`. Genes
marcados com ★ são os `defining_genes` do arquétipo e pesam `DRIFT_DEFINING_WEIGHT`.
O desvio por personagem (`deviation_i`) vem de
`fitness._archetype_deviation`, então é idêntico ao que entra no `drift_penalty`;
a média dos 5 é o próprio `drift_penalty`. Mostra **o preço pago** pela evolução —
a visão que faltava do trade-off central da tese.

```bash
py -m src.analysis.drift_table              # canônico (sanity — drift ≈ 0)
py -m src.analysis.drift_table --evolved    # melhor do AG
py -m src.analysis.drift_table --nsga2 knee_point
```

Complementa o `archetype_validator`: o validator checa **ordem** (Turtle ainda é o
mais defensivo?), a tabela de drift mede **distância** (o quanto cada gene se moveu).
No fim, reporta a **diferenciação** (distância média par-a-par dos 5 vs a do
canônico, como `ratio`): `ratio ~1` = os 5 seguem distintos; `< 1` = homogeneização
(convergiram entre si). É o medidor direto do eixo *homogeneização* da tese.

### `fingerprint`

Retrato de **como cada personagem joga**, agregado sobre seus 4 matchups: ataques
conectados por luta (`atk_landed`), mix de posturas (ADV/RET + **DEF dividido em
guarda escolhido vs parede forçada**), % fora de range, % stunado, distância média,
stun aplicado por luta e dano arrancado pela guarda (`guard_break`, a assinatura do
Grappler). Mostra canônico vs evoluído + Δ por personagem — cada perfil medido no
próprio roster, então o Δ mistura o que o personagem mudou com o que os oponentes
mudaram. Mede
identidade **comportamental** (o Zoner evoluído ainda kita?) — o terceiro ângulo,
junto da estrutural (`archetype_validator`) e da de genes (`drift_table`). A
agregação por personagem é o helper compartilhado `analyze_matchups.behavioral_profile`,
também consumido pela Layer 3 do validador (fonte única). O DEFEND vem dividido para
não contaminar a defesa real com o artefato de encurralamento (ver `04-combat-model.md`).
O ataque é contado como evento (`atk_landed`), não como fração de sub-ticks: ele é
instantâneo e gated por cooldown.

O default de `--seed` é `MULTI_RUN_VALIDATION_SEED` e o de `--n` é
`IDENTITY_BEHAVIORAL_SIMS` — os mesmos do `report` e do `baselines`, para que a tabela
impressa aqui seja **a que está gravada** em `baselines.json` (campo
`behavioral_profile`), e não um segundo perfil em circulação. Para redigir, citar do
artefato; este tool é a leitura formatada dele.

```bash
py -m src.analysis.fingerprint              # canônico (baseline, Δ=0)
py -m src.analysis.fingerprint --evolved    # evoluído vs canônico
py -m src.analysis.fingerprint --nsga2 knee_point
```

### `archetype_validator`

Asserções de identidade em 3 camadas (rank ordinal entre os 5):

- **Layer 1 — estrutural inter (13):** rankings de genes entre os 5 personagens
  (Rushdown tem maior speed e menor cooldown, Zoner tem maior range/knockback/
  P(RECUAR), Combo Master tem maior stun, Grappler tem maior damage e maior
  `grab_power`, Turtle tem maior hp e cooldown, menor speed, maior P(GUARDA)). Os pesos
  entram como **probabilidade de intenção** (`Character.intention_probabilities`) — só a
  razão entre eles age no combate, então a escala crua não pode mudar o veredito. E um
  **empate conta contra** a asserção (`_rank_against`): "o de maior alcance" só passa se
  for estritamente o maior.
- **Layer 2 — estrutural intra (5):** comparações normalizadas dentro de um
  personagem (`norm(range) > norm(speed)` no Zoner, etc.). Normalização = fração do
  range do bound `(x − lo)/(hi − lo)` (mesma convenção do `fitness`).
- **Layer 3 — comportamental (5):** identidade **funcional** (como o personagem
  *joga*), sobre o `behavioral_profile` (roda combate, estocástico). Uma asserção
  primária por arquétipo: Zoner = maior `mean_dist`; Rushdown = maior `atk_landed`;
  Turtle = maior `def_chosen` (guarda escolhido, não encurralado); Combo Master =
  maior `stun_inflicted`; Grappler = maior `guard_break` (dano arrancado pela guarda
  alheia).
- **Concordância de ranking comportamental** (`rank_agreement`, junto da Layer 3): τ-b de
  Kendall entre a ordem dos 5 personagens no canônico e no roster, em cada uma das 10
  métricas do `behavioral_profile`, na média — 1 = a ordem do canônico, 0 = acaso, −1 =
  invertida. É a régua funcional **contínua**: a Layer 3 são 5 bits (ser o 1º ou não), e
  ficar em 2º por um fio conta igual a ficar em 5º. O perfil do canônico de referência é
  medido nas mesmas condições (`canonical_profile(n, seed)`).

> **Independência dos instrumentos.** As Layers 1-2 medem identidade **estrutural** —
> o mesmo eixo que o `drift_penalty` otimiza, já que os `defining_genes` de cada
> arquétipo espelham as asserções da Layer 1. São, portanto, **parcialmente
> endógenas**: um score alto ali em parte reflete a penalidade ter funcionado. A
> Layer 3 e a concordância medem identidade **funcional**, e nada no fitness referencia
> comportamento — são *held-out*, mas **não independentes**: cada asserção da Layer 3 é
> consequência quase direta de um gene definidor (o stun infligido vem do gene de stun,
> a guarda quebrada do `grab_power`). O ciclo de vantagens não é régua de identidade (o
> canônico só realiza 6/10 dele).

Layers 1-2 são **ranking ordinal** de genes; resolvem rápido, sem combate. Por que
a Layer 3 importa: as estruturais não detectam quando os genes certos **não se
traduzem em ação** (ex.: Zoner com `w_retreat` alto que, encurralado, vira DEFEND
em vez de kitar). A Layer 3 fecha essa lacuna. É opt-in (`behavioral_n>0` em
`run_validation`); o standalone e o `report` a rodam por default (`--n`, `--seed`).

```bash
py -m src.analysis.archetype_validator [--evolved | --nsga2 [rep]] [--n 200] [--seed 42]
py -m src.analysis.archetype_validator --n 0    # só estrutural (Layers 1-2), sem τ
```

## `src.experiments` — o protocolo

Cada um grava um artefato em `results/` (uma pasta por tool) com o carimbo de
proveniência — incluindo o digest do **código de medição** da própria ferramenta
([09-reproducibility.md](09-reproducibility.md)). São os passos da bateria
(`scripts/run_battery.ps1`). Os que partem de um indivíduo salvo (`--evolved`,
`--nsga2`) **recusam** um artefato de origem obsoleto, em vez de só avisar: o artefato
novo sairia carimbado como atual carregando o indivíduo de outro sistema.

### `multi_run` — N execuções independentes + estatística agregada

Item 1.1 da metodologia (Eiben & Smith 2015; Deb 2001): um EA é estocástico, então
uma seed é uma **amostra**, não um resultado. Roda o algoritmo escolhido sobre N
sementes consecutivas (`MULTI_RUN_SEED_START..+N-1`), reavalia o melhor indivíduo de
cada execução sob uma **semente de validação fixa** (`MULTI_RUN_VALIDATION_SEED`) —
independente do treino e comum a todas as execuções (Common Random Numbers) — e agrega.

```bash
py -m src.experiments.multi_run                    # ambos os algoritmos, defaults do config
py -m src.experiments.multi_run --algorithm nsga2  # só NSGA-II (scalar_optimum por seed)
py -m src.experiments.multi_run --algorithm ga     # só AG escalar (best por seed)
py -m src.experiments.multi_run --algorithm ga --lambda-drift 0     # controle: sem drift
py -m src.experiments.multi_run --algorithm ga --no-canonical-seed  # controle: sem semente
```

Representante por execução: AG escalar → `best`. O NSGA-II devolve uma **fronteira**,
não um ponto — qual ponto representa a execução é uma escolha explícita
(`--nsga2-representative`, default `scalar_optimum` = `HEADLINE_REPRESENTATIVE`, o
comparável do escalar), gravada no artefato como `nsga2_representative`. Os **cinco**
representantes de cada semente ficam gravados ao lado dele, em `representatives`, cada um
reavaliado da mesma forma — o de topo é um deles. É o que deixa o `compare_algorithms`
refazer a comparação contra outro ponto sem re-rodar o NSGA-II. Saídas agregadas
(impressas + salvas):

- **média ± desvio** de `dominance_penalty` — **decomposto** nos três termos
  (`global_term`, `cap_term`, `decis_term`, gravados por semente e agregados) — e de
  `drift_penalty`. O composto sozinho não distingue perder no termo primário
  (peso 1,0) de perder num secundário (peso 0,5);
- **WR global por personagem** (média ± desvio) + **fração de sementes em que cada
  boneco fica equilibrado** (WR global em `[0.40, 0.60]`, via `character_balanced`);
- **hard-counters por execução** (média ± desvio; pares fora de `[0.35, 0.65]`);
- **fração de sementes que equilibram o ROSTER** (5 bonecos em banda **e** 0
  hard-counters) — a frase-tese (*"em N execuções, X% equilibraram o roster"*);
- **identidade** de cada roster, nas condições dos modelos nulos
  (`IDENTITY_BEHAVIORAL_SIMS` lutas por par, semente de validação): validador estrutural
  (`validator_structural`, Layers 1-2), comportamental (`validator_behavioral`, Layer 3) e
  a concordância de ranking comportamental com o canônico (`rank_agreement`, τ) — por
  semente, em cada um dos cinco representantes do NSGA-II, e agregados em `identity`;
- **(secundário)** WR média por matchup + fração de sementes em que cada par vira
  counter duro;
- **(só NSGA-II)** hipervolume e spacing da fronteira por seed, média ± desvio
  (item 1.2 — ver [06-nsga2.md](06-nsga2.md)), **mais os objetivos de toda a fronteira**
  (`front_objectives`) e a amplitude do front 0 por geração (`front_history`);
- **(só AG escalar)** `converged_at` por semente, agregado em `convergence` — o eixo de
  **velocidade**. Como os dois algoritmos rodam orçamento fixo
  ([05-genetic-algorithm.md](05-genetic-algorithm.md)), convergir é evento registrado e
  não parada. A média sai só sobre as sementes que **convergiram** — imputar um valor às
  outras exigiria um número para "não convergiu", que não existe; a taxa carrega essa
  metade. Convergir é o **primeiro** equilíbrio confirmado, não equilíbrio no fim: a
  fração de sementes que terminam equilibradas é a linha de cima, e as duas se leem
  juntas. Junto vão `convergence_gate_fired` e `convergence_rejected` (o ajuste ao stream
  quantificado) e `in_loop_objectives` — o `(dominance, drift)` do melhor no stream da
  última geração, o mesmo da fronteira do NSGA-II da mesma semente, que alimenta a
  relação de Pareto do `compare_algorithms`. O NSGA-II **não** tem eixo de velocidade: "o
  roster está equilibrado?" não é pergunta que se faça a uma fronteira;
- **sempre, por semente:** os `genes` do representante (no NSGA-II, também os de cada um
  dos cinco) e a trajetória por geração (`history` no escalar, `front_history` no NSGA-II).
  Guardar custa ~30 KB contra minutos de execução, e é a diferença entre responder uma
  pergunta nova a partir do artefato ou re-rodar o experimento.

> **Regra que os artefatos deste tool seguem: gravar o que é caro de reproduzir.** Toda
> métrica agregada se recalcula do `per_seed` em segundos; o que não se recalcula é o que
> exigiu horas de busca — a fronteira, os genes (dos cinco representantes, no NSGA-II), a
> trajetória. Com a fronteira guardada, comparar um λ novo contra ela não exige re-rodar o
> NSGA-II.

Parametrizado em `config.py` (`MULTI_RUN_*`). O default de `MULTI_RUN_N_SEEDS` é o
protocolo (20), e é com ele que a bateria roda, sem flag.

#### Três destinos: bateria, controles, exploratórios

`artifact_path` decide onde o artefato mora a partir do que o **corpo** dele registra:

| destino | quando | citável? |
|---|---|---|
| `results/multi_run/multi_run_<algo>.json` | inteiramente no protocolo | sim — é a bateria |
| `results/controls/multi_run_<algo>_<desvios>.json` | desvio só de **desenho** (λ, pesos do dominance, seleção, semente canônica, representante de topo), com a amostra e o orçamento do protocolo | sim — braço de controle |
| `results/exploratory/multi_run_<algo>_<desvios>.json` | desvio de **amostra ou orçamento** (população, gerações, nº e início das sementes, sims da reavaliação) | não — ordena configurações |

O nome é montado dos desvios **reais**, nunca de um rótulo passado à mão: um nome fixo
faria dois braços diferentes se sobrescreverem, e cair no caminho da bateria faria uma
execução barata **apagar** horas de bateria sem aviso. Antes de 2026-09-18 a função só
olhava orçamento, λ, pesos e seleção — um `--n-seeds 3` no resto do protocolo gravava por
cima da bateria de n = 20. `test_multi_run` cobre os três destinos.

#### Flags que variam a configuração sem editar o `config.py`

| flag | varia | lido por |
|---|---|---|
| `--pop` / `--generations` | orçamento | `ga.run` / `nsga2.run` |
| `--lambda-drift` / `--lambda-dominance` | pesos do escalar | `fitness` (propagado ao pool) |
| `--dom-global` / `--dom-cap` / `--dom-decis` | pesos dos 3 termos do dominance | `fitness` (propagado ao pool) |
| `--elite-rate` / `--tournament-size` | pressão seletiva | `operators` (**só o processo pai**) |
| `--no-canonical-seed` | população inicial do AG escalar | `ga.run` |
| `--n-seeds` / `--seed-start` / `--sims` | amostra | `multi_run` |

Duas invariantes além do destino:

1. **O carimbo registra o que a execução usou**, não o que está no arquivo — via
   `provenance.override`, então cada braço tem `fingerprint` próprio e
   `Divergence.is_experiment_arm` o separa de "artefato obsoleto".
2. **O que atravessa o spawn é propagado explicitamente.** Os λ, os pesos do dominance e
   as regras do combate são lidos pelos *workers*, então viajam num `RuntimeState` (ver
   [09-reproducibility.md](09-reproducibility.md)); elitismo, torneio e a semente
   canônica são lidos só pelo pai e **não** precisam disso.

O tool avisa em cada caso — e no dos pesos do dominance avisa o principal: **o composto
não é comparável entre braços**, porque os pesos o definem. A comparação é pelos *termos*
e pelas métricas post-hoc. No de elitismo/torneio e no da semente canônica avisa que
valem só para o AG escalar.

### `compare_algorithms` — comparação estatística entre dois conjuntos de execuções

O `multi_run` agrega média ± desvio de cada configuração, mas média ± desvio não decide
se a diferença entre duas é real ou ruído de amostragem. Este tool **não roda nada**: lê
dois artefatos do `multi_run` e aplica sobre as amostras por semente (prática padrão para
algoritmos estocásticos — Derrac et al. 2011; Arcuri & Briand 2011). Dois usos, o mesmo
aparato:

- **AG × NSGA-II** (default) — a comparação entre algoritmos;
- **AG × controle** (`--control PATH`) — a bateria contra um braço de
  `results/controls/`: `λ_drift = 0` (quanto da identidade o termo de drift segura) e sem
  semente canônica (quanto da diferença entre algoritmos é inicialização).

A estatística:

- **Mann-Whitney U** bicaudal (não-paramétrico, duas amostras independentes — não
  assume normalidade, e as métricas são limitadas por baixo em 0);
- **Â₁₂ de Vargha-Delaney** como tamanho de efeito — `P(execução de a > execução de b)`,
  com 0.5 = sem efeito;
- **Holm-Bonferroni** sobre uma **família fixa de 7 métricas** — equilíbrio
  (`dominance_penalty`, hard-counters, bonecos em banda) e identidade (`drift_penalty`,
  validador estrutural, validador comportamental, concordância de ranking) —, a mesma em
  toda comparação, então nenhuma escolhe as métricas depois de ver os dados. Ficam de fora
  só as **degeneradas** (`_is_degenerate`: amostra conjunta sem variação, onde
  Mann-Whitney é indefinido); elas seguem na tabela como descritivas, e `family_size` /
  `excluded_from_family` vão gravados.

> Para o **porquê** de cada peça — o que a correção de Holm resolve, como o
> procedimento funciona passo a passo e como ler o resultado — ver
> [12-statistical-testing.md](12-statistical-testing.md).

Além dos testes, dois blocos **descritivos**, deliberadamente fora da família de Holm:

- a **decomposição do `dominance_penalty`** — mediana dos três termos lado a lado, com o
  peso de cada um. Serve para ler de **onde** vem a diferença: o termo primário é o
  `global_term`, e é ele que diz quem equilibra o roster melhor;
- no AG × NSGA-II, a **relação de Pareto por semente**: o ponto do AG
  (`in_loop_objectives`) contra a fronteira inteira do NSGA-II da mesma semente
  (`front_objectives`) — domina algum ponto dela, é dominado, ou nenhum dos dois. As três
  leituras são exclusivas (a fronteira é mutuamente não-dominada), os dois lados estão no
  mesmo stream (o da última geração), e a leitura não depende de representante nenhum.

```bash
py -m src.experiments.multi_run --algorithm both   # gera os dois artefatos (20 sementes)
py -m src.experiments.compare_algorithms           # AG × NSGA-II (scalar_optimum) + Pareto
py -m src.experiments.compare_algorithms --nsga2-representative best_dominance
py -m src.experiments.compare_algorithms --control results/controls/multi_run_ga_drift0_dom1.json
```

Recusa entrada que não descreva o sistema atual (um controle é aceito quando a divergência
é exatamente o override que ele declara) — a comparação sai carimbada com a configuração
vigente, e não pode herdar números de outra. E aborta se os dois artefatos não
compartilharem sementes, semente de validação, sims/matchup e orçamento. Grava em
`results/multi_run/comparison_ga_vs_nsga2.json` (manchete, `scalar_optimum`),
`comparison_ga_vs_nsga2_<REP>.json` (outro representante) e
`results/controls/comparison_ga_vs_<braço>.json` (controles).

### `external_validation` — replicação e robustez fora do laço (estilo Ludi)

Item 3.2 da metodologia (Browne & Maire 2010): não confiar num único número de
fitness — validar o artefato evoluído **fora do laço de otimização**. Fixa UM indivíduo
(canônico / `--evolved` / `--nsga2 [rep]`) e responde duas perguntas, cada uma com
`EXTERNAL_VALIDATION_N_SEEDS` sementes novas (a partir de 10000) somadas numa amostra de
5000 lutas por par:

- **replicação** — as regras do treino: o equilíbrio medido durante a busca se confirma
  com mais lutas, em sementes que o AG nunca viu?
- **robustez** — uma regra de combate perturbada por vez
  (`EXTERNAL_VALIDATION_RULE_PERTURBATIONS`: distância inicial 40/60, campo 80/120,
  persistência 4/6, redução da guarda 0,55/0,65): o equilíbrio sobrevive fora das
  condições exatas em que foi otimizado? As regras entram por `combat.set_rules` e voltam
  a `TRAINING_RULES` ao fim de cada condição.

```bash
py -m src.experiments.external_validation                    # canônico
py -m src.experiments.external_validation --evolved          # melhor do AG
py -m src.experiments.external_validation --nsga2 scalar_optimum
py -m src.experiments.external_validation --n-seeds 20 --sims 1000
```

Em cada condição, cada WR (a global de cada boneco e a de cada par) é classificada pelo
**IC de Wilson (95%)** contra a banda — `[40%, 60%]` para o boneco, `[35%, 65%]` para o
par: **dentro** (IC inteiro na banda), **fora** (IC inteiro fora — falha estatisticamente
clara) ou **inconclusivo** (IC atravessa a borda). A condição é ROBUSTA se tudo está
dentro, FRÁGIL se algo está fora, INCONCLUSIVA no resto. Grava em
`results/external_validation/external_validation_<label>.json` o veredito da replicação e
a contagem de condições de robustez em cada veredito.

O veredito **não depende de quantas sementes se usa**: o anterior ("counter duro em
alguma das K condições") ficava mais severo a cada semente acrescentada, mesmo com o
roster intacto, e as K "condições" eram só sementes — replicação, não robustez.

**Diferença vs `multi_run` (1.1):** lá varia-se a *execução evolutiva*; aqui fixa-se UM
indivíduo e varia-se a *avaliação* (amostra nova e regras novas). A parte "contra
política diferente" do método liga-se ao item 2.1 (coevolução), fora do escopo.

### `sensitivity_analysis`

Para cada (arquétipo, gene) — os 8 atributos **e** os 3 pesos —, desloca o gene numa
janela de 2σ (o σ que a mutação usa nele) e mede `Δ WR` do personagem. Genes com `|Δ|`
médio abaixo do **piso medido** são "neutros" (drift por random walk, sem pressão
seletiva).

**A janela tem sempre 2σ.** Perto do bound ela **desliza** para dentro dele em vez de ser
cortada: cortá-la mediria, num gene encostado no limite, metade do deslocamento dos
outros, e o gene pareceria menos visível só por estar na borda.

**O piso é medido, e na estatística que é classificada.** O número classificado de cada
gene é a média, sobre os 5 personagens, de `|Δ WR|`. O piso (`--null-reps`) roda
exatamente essa estatística sob a hipótese nula — janela de largura zero, os dois lados
sob seeds diferentes (com a mesma seed seriam bit-idênticos) — e fica com o maior valor
que o ruído produziu. Quebrar o pareamento deixa o piso **conservador**, já que a medição
real usa CRN pareado. Critério único: `≤ piso` neutro · `≤ 2× piso` borderline · acima,
visível.

**Onde medir importa.** No canônico o roster é saturado (Rushdown ~100%, Turtle ~0%), e
com a WR presa no teto deslocar um gene não muda nada — quase tudo sai "neutro" por
efeito de teto. A medida citável é a de `--evolved` / `--nsga2`, num roster equilibrado.
A análise é **local**: mede a paisagem em volta de um indivíduo, e muda com ele.

```bash
py -m src.experiments.sensitivity_analysis --evolved
py -m src.experiments.sensitivity_analysis --evolved --sims 600 --null-reps 12   # piso mais fino
```

Os dois lados da janela são avaliados sob o mesmo seed-base, e cada luta é semeada por
`fitness.fight_seed`: os dois lados recebem os mesmos sorteios luta a luta, e o Δ medido é
efeito do gene, não do sorteio. Salva a matriz completa em
`results/sensitivity/sensitivity_analysis.json` (Δ WR por arquétipo × gene, σ por gene, o
piso — `noise_floor_measured` e `noise_floor_mean` — e a classificação).

### `baselines` — modelos nulos: o piso de cada métrica

Nenhuma métrica de identidade do projeto tem piso zero, então nenhuma pode ser lida
contra o teto (o canônico) sozinho. Os valores exatos dependem da semente de avaliação,
e o tool os recalcula a cada execução; as ordens de grandeza (35 nulos, 5 espelhos + 30
aleatórios):

| métrica | piso | teto | leitura |
|---|---|---|---|
| validador (L1-L3) | ~6/23, com nulo chegando a **10/23** | 23/23 | score cru não é "% preservado" |
| validador (L1-L2) | ~5/18, com nulo chegando a **9/18** | 18/18 | endógeno — vencer os nulos aqui é quase garantido para um roster otimizado com drift |
| validador (L3) | ~1/5, com nulo chegando a 3/5 | 5/5 | a parte funcional, lida separada |
| concordância de ranking (τ) | −0,04, com nulo chegando a **+0,32** | 1,00 | a régua funcional contínua |
| `drift_penalty` | **0,377** (espelho) · 0,415 (aleatório) | 0,000 | 0,04 separa o espelho do aleatório |
| `dominance_penalty` | ~1,1 (aleatório); os **espelhos** ficam em 0,025–0,037 (fora o do Zoner) | média dos espelhos | o teto de equilíbrio é a solução trivial, no piso de ruído |

O validador conta empate **contra** a asserção: cinco cópias do mesmo personagem não têm
"o de maior alcance". Antes de 2026-09-18 o desempate era pela ordem do índice, e todo
espelho passava em 4 das 13 asserções da Layer 1 de graça.

Rosters de referência que o tool monta e mede:

- **canônico** — identidade intacta, equilíbrio terrível. O teto de identidade.
- **espelho** (5 cópias do mesmo arquétipo, um roster por arquétipo) — equilíbrio
  perfeito por simetria, identidade zero por construção. É a **solução trivial** do
  problema de equilíbrio, e portanto a resposta numérica à objeção *"por que não deixar
  os cinco iguais?"*.
- **aleatório** (N rosters) — sem projeto nenhum. O chão absoluto.

Saída: cada métrica como `posição = (valor − piso) / (teto − piso)`, o **pior nulo** (o
melhor resultado que um roster sem estrutura alcançou) e um **p-valor empírico** — a
fração dos nulos que igualam ou superam o observado. O piso é uma **distribuição**, e a
resolução do p é 1/N: com 35 nulos, nenhum nulo igualando o observado afirma `p < 0,03`.
Por isso o default de `--n-random` é **30**, o valor do protocolo.

> **O que os nulos não fazem:** isolar o efeito do método. Eles não são otimizados, então
> um roster evoluído com penalidade de drift vencê-los em drift e nas Layers 1-2 é
> esperado. O contrafactual é o controle `λ_drift = 0` (`multi_run` + `compare_algorithms
> --control`).

Além dos agregados, cada roster medido (as referências e o alvo) leva no artefato as
**três tabelas cruas** que os sustentam, para que a redação não dependa de re-rodar um
tool e ler o terminal:

- `per_gene_drift` — o Δ normalizado gene a gene, por personagem, via `drift_genes`: a
  mesma forma que o `_archetype_deviation` compara (os 3 pesos entram reescalados para a
  soma canônica), então as linhas somam no desvio do personagem;
- `differentiation` — a distância média par-a-par dos 5 (`drift_table.mean_pairwise_distance`),
  o medidor de homogeneização. O evoluído da seed 42 dá 1,201 contra 1,353 do canônico:
  **89% da diferenciação preservada**;
- `behavioral_profile` — as 10 métricas comportamentais por personagem, recomputadas sob a
  **mesma semeadura** que o `run_validation` usa internamente, então são bit a bit o perfil
  que produziu a Layer 3 e o τ daquele roster, não uma segunda medição.

```bash
py -m src.experiments.baselines                      # só os rosters de referência
py -m src.experiments.baselines --evolved            # + posiciona o melhor do AG
py -m src.experiments.baselines --nsga2 scalar_optimum
py -m src.experiments.baselines --n-random 60 --sims 400   # mais nulos = mais resolução no p
```

> **O ciclo e as tríades saíram daqui em 2026-09-22** para
> `src.experiments.cycle_structure`. A 200 lutas por par a direção de cada aresta de um
> roster equilibrado é sorteio (margem mediana 0,048 contra σ = 0,035), e os espelhos —
> estrutura de torneio zero por construção — marcavam 5,40/10 "mantidas" com 1,00/10
> decididas. O `baselines` mede 36 rosters com perfil comportamental e não podia subir de
> resolução junto, então a métrica mudou de casa em vez de ser consertada no lugar.

### `cycle_structure` — o ciclo autoral, falsificado uma vez

Grava `results/cycle/cycle_structure.json`. Mede a estrutura do torneio de matchups na
resolução que ela exige: **16 × 1000 = 16.000 lutas por par** (σ = 0,0040), sobre o
canônico, as 20 sementes de cada algoritmo, 30 rosters aleatórios (piso) e os 5 espelhos
(controle de ruído). Os streams são compartilhados entre rosters (CRN), então a diferença
entre grupos é de genes.

```bash
py -m src.experiments.cycle_structure                   # protocolo (passo 17 da bateria)
py -m src.experiments.cycle_structure --streams 4 --sims 500   # rodada barata
```

Três regras de desenho, e todas vêm do erro que motivou o tool:

- **Só arestas decididas contam** (`|WR − 0,5| > 2σ`). Aresta indecisa é sorteio, e
  contá-la mistura sinal com ruído nos dois sentidos. A 200 lutas, 10 arestas "mantidas"
  por 0,002 de margem não são estrutura nenhuma.
- **Grupos comparados pela taxa `mantidas/decididas`, nunca pela contagem.** Um roster
  aleatório decide 10/10 arestas e um equilibrado 9,3/10: comparar contagem crua puniria o
  equilibrado por ter uma aresta em cima do limiar.
- **O espelho entra como controle de ruído**, não como piso de identidade (o papel dele no
  `baselines`). Cinco cópias do mesmo arquétipo têm estrutura de torneio zero por
  construção, então o que a métrica marcar neles é o que ela marca sem nada para marcar.

Reporta ainda as **tríades circulares** (Kendall & Babington Smith 1940),
`C(n,3) − Σ C(dᵢ,2)`, na escala 0 (ordem estrita) · 2,5 (acaso) · 5 (máximo, o torneio
regular). Elas não dependem de autoria, mas são em boa parte **implicadas** pelo objetivo:
um roster estritamente transitivo teria WRs 100/75/50/25/0, incompatível com todos perto
de 50%, então equilíbrio global com pares decididos força intransitividade.

> **O ciclo é premissa, não régua.** Ele nunca esteve no fitness (o objetivo é cego à
> direção), e o próprio canônico realiza só 6/10 dele — não se preserva o que a premissa
> não tinha. Este tool existe para falsificá-lo **uma vez**, com número citável, não para
> reportá-lo por execução. Status e leitura em
> [`../thesis/02-canonical-cycle.md`](../thesis/02-canonical-cycle.md).

### `hybrid_choice` — o critério que escolhe a configuração do híbrido

Lê os braços do `run_hybrid_sweep.ps1` em `results/exploratory/` e grava
`hybrid_choice.json` com a **trilha da decisão**: quem foi eliminado, por quê, e o que
decidiu o desempate. O critério mora em código porque decisão de projeto tomada depois de
ver os números não é decisão, é ajuste.

```bash
py -m src.experiments.hybrid_choice
```

Na ordem:

1. **Elimina quem é pior em equilíbrio** — a entrega é um elenco equilibrado, e um braço
   que compra identidade com equilíbrio responde outra pergunta. Com n = 5 uma mediana por
   um fio é ruído, então a eliminação exige evidência consistente: perder
   `dominance_penalty` em ≥ 4 das 5 sementes, **ou** ser pior nas duas medidas ao mesmo
   tempo.
2. **Maximiza quantas das 4 réguas de identidade bate** (drift, L1+L2, Layer 3, τ).
3. **Desempata por τ** — a régua funcional contínua, a que responde *"functional
   identities"*.
4. **Desempata pela configuração mais simples** (0,5 / `front`). Com n = 5 nada separa do
   ruído, e escolher por um fio é escolher por sorte.

Não usa a soma `dominance + drift`: braços se comparam pelos **termos** e pelas métricas
post-hoc, nunca pelo composto que os `LAMBDA_*` definem.

> **Ele escolhe a CONFIGURAÇÃO; quem decide a ADOÇÃO é a bateria.** Em orçamento reduzido
> a âncora ainda não degradou — o AG escalar a 60 gerações tem τ = 0,463 contra 0,281 a
> 150 —, então o sweep compara o híbrido contra um escalar artificialmente forte e tende a
> **subestimá-lo**. Se nenhum braço passar no filtro, a escolha cai na configuração mais
> simples com `adoption_deferred = true`, e a bateria mede o braço com n = 20 de qualquer
> forma. É a regra geral do projeto aplicada aqui: orçamento reduzido ordena
> configurações, nunca declara vencedor.

## `src.visualization` — viewers e plots

### `viewer` / `web_viewer`

Visualizadores de uma luta, consumindo `CombatTrace`:

```bash
py -m src.visualization.viewer          # ASCII no terminal
py -m src.visualization.web_viewer      # browser interativo em localhost:8080
```

### `nsga2_plots`

Plot 2D da fronteira de Pareto (dominance × drift) com os 5 representantes
destacados, anotado com hipervolume e spacing. Chamado automaticamente por `py main.py --algorithm nsga2`; salva em
`results/single_run/plots/<timestamp>/pareto_front.png`. Como o `ga_plots`, também
redesenha **a partir do artefato** (`py -m src.visualization.nsga2_plots`), sem re-rodar
os 7 min do NSGA-II.

**Representantes coincidem com frequência, e a figura mostra isso.** Nada impede dois
critérios de escolherem o mesmo ponto: na bateria de 2026-09-21, `best_dominance` e
`scalar_optimum` caem no mesmo ponto em **11 das 20 sementes**, e `knee_point` e
`ideal_point` também em 11/20. Desenhados no mesmo tamanho, o segundo cobriria o primeiro
e a legenda citaria um marcador ausente da figura — então os marcadores são desenhados
**aninhados** (do maior ao menor em cada posição) e a caixa de anotação lista as
coincidências.

### `ga_plots`

A contraparte escalar: as **curvas de convergência** do AG, em dois painéis —
`best/mean/worst fitness` e os dois termos (`dominance_penalty`, `drift_penalty`) do
melhor indivíduo, com `converged_at` como linha vertical. É o item §2 do
[`../thesis/06-results-to-present.md`](../thesis/06-results-to-present.md).

Lê o **artefato** (`single_run/ga.json`), não o objeto em memória: o `main.py` o chama
logo depois de salvar, e rodar sozinho não re-executa o AG. Salva em
`results/single_run/plots/ga_convergence.png`.

As curvas **flutuam** entre gerações em vez de subir monotonicamente — é o efeito
declarado da rotação do stream por geração, e a razão de não existir evento de
estagnação (ver [05-genetic-algorithm.md](05-genetic-algorithm.md)).

```bash
py -m src.visualization.ga_plots                      # do single_run/ga.json
py -m src.visualization.ga_plots --results <path>     # de outro artefato de AG
```
