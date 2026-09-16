# 08 — Ferramentas

Em `src/tools/`. Todas rodam como módulo a partir da raiz (`py -m src.tools.<nome>`)
e operam sobre o canônico, o melhor do AG (`--evolved`) ou um representante do
NSGA-II (`--nsga2 [rep]`).

## `report` — dossiê do indivíduo (porta de entrada)

**Um comando** que compõe os tools de avaliação num relatório único: cabeçalho de
fitness (fitness, drift_penalty, dominance_penalty) + matchups (equilíbrio) + drift
de genes + diferenciação (homogeneização) + fingerprint (comportamento) + validador
(estrutura) + **modelos nulos** (piso, teto e posição de cada métrica). Não duplica
lógica — chama as funções dos outros tools.

A seção de modelos nulos vem por último de propósito: ela é o que dá sentido às
anteriores. Valor cru de identidade não diz nada sem o piso, e os pisos deste projeto
estão longe de zero. Os rosters de referência são **recalculados a cada execução**
(~2s) e nunca lidos de cache — baseline silenciosamente obsoleto é exatamente o erro
que o dossiê existe para evitar.

```bash
py -m src.tools.report --evolved              # dossiê completo do melhor do AG
py -m src.tools.report --nsga2 scalar_optimum
py -m src.tools.report --evolved --n-random 20   # mais nulos = mais resolução no p
```

Os tools abaixo continuam rodando isolados (pra quando você quer só um ângulo), e
os de propósito diferente (`sensitivity_analysis`, `viewer`, `nsga2_plots`) ficam
**fora** do dossiê.

## `analyze_matchups`

Roda os 10 matchups (ou um par específico) com N simulações cada e reporta
estatísticas, matriz de WR e resumos.

```bash
py -m src.tools.analyze_matchups                       # todos, canônico, N=1000
py -m src.tools.analyze_matchups rushdown zoner        # par específico
py -m src.tools.analyze_matchups --evolved --n 50      # indivíduo evoluído
py -m src.tools.analyze_matchups --nsga2 knee_point    # representante do Pareto
py -m src.tools.analyze_matchups --seed 42             # ver ressalva de seed abaixo
```

Saídas: estatísticas por luta (hits, dano, stun, ticks em/fora de range, mix de
ações, KO-rate, duração, distância), **matriz 5×5** de WR e os resumos (alinhados ao
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

## `drift_table`

Decompõe o `drift_penalty` por personagem e por gene: canônico vs evoluído, Δ
absoluto, Δ normalizado e o **peso do gene no drift**. Mesma normalização do fitness
(`fitness.gene_drift`): fração do range do bound, `(x − lo)/(hi − lo)`. Genes
marcados com ★ são os `defining_genes` do arquétipo e pesam `DRIFT_DEFINING_WEIGHT`.
O desvio por personagem (`deviation_i`) vem de
`fitness._archetype_deviation`, então é idêntico ao que entra no `drift_penalty`;
a média dos 5 é o próprio `drift_penalty`. Mostra **o preço pago** pela evolução —
a visão que faltava do trade-off central da tese.

```bash
py -m src.tools.drift_table              # canônico (sanity — drift ≈ 0)
py -m src.tools.drift_table --evolved    # melhor do AG
py -m src.tools.drift_table --nsga2 knee_point
```

Complementa o `archetype_validator`: o validator checa **ordem** (Turtle ainda é o
mais defensivo?), a tabela de drift mede **distância** (o quanto cada gene se moveu).
No fim, reporta a **diferenciação** (distância média par-a-par dos 5 vs a do
canônico, como `ratio`): `ratio ~1` = os 5 seguem distintos; `< 1` = homogeneização
(convergiram entre si). É o medidor direto do eixo *homogeneização* da tese.

## `fingerprint`

Retrato de **como cada personagem joga**, agregado sobre seus 4 matchups: ataques
conectados por luta (`atk_landed`), mix de ações (ADV/RET + **DEF dividido em
guarda escolhido vs parede forçada**), % fora de range, % stunado, distância média
e stun aplicado por luta. Mostra canônico vs evoluído + Δ por personagem. Mede
identidade **comportamental** (o Zoner evoluído ainda kita?) — o terceiro ângulo,
junto da estrutural (`archetype_validator`) e da de genes (`drift_table`). A
agregação por personagem é o helper compartilhado `analyze_matchups.behavioral_profile`,
também consumido pela Layer 3 do validador (fonte única). O DEFEND vem dividido para
não contaminar a defesa real com o artefato de encurralamento (ver `04-combat-model.md`).
O antigo "ATK" (fração de sub-ticks em estado ATTACK) foi substituído por
`atk_landed` — ataque é evento instantâneo gated por cooldown, então a fração de
sub-ticks era estruturalmente minúscula e enganosa.

```bash
py -m src.tools.fingerprint              # canônico (baseline, Δ=0)
py -m src.tools.fingerprint --evolved    # evoluído vs canônico
py -m src.tools.fingerprint --nsga2 knee_point
```

## `baselines` — modelos nulos: o piso de cada métrica

Toda métrica de identidade do projeto vinha sendo lida contra o **teto** (o canônico),
como se o piso fosse zero. Nenhuma tem piso zero, e isso invalidava as leituras:

| métrica | piso medido | teto | o que `8/21` parecia | o que era |
|---|---|---|---|---|
| validador (L1-L3) | **~6,8/21**, com nulo chegando a **12/21** | 21/21 | "38% preservado" | no acaso |
| `drift_penalty` | **~0,33** (espelho) · ~0,41 (aleatório) | 0,000 | — | 0,04 separa "preservado" de aniquilado |
| arestas do ciclo | **5/10** (cada aresta é cara-ou-coroa) | 10/10 | — | sem sinal possível |

Ler `8/21` como "38% da identidade sobreviveu" é o mesmo erro de ler 20% numa prova de
cinco alternativas como "sabe 20% da matéria".

Rosters de referência que o tool monta e mede:

- **canônico** — identidade intacta, equilíbrio terrível. O teto de identidade.
- **espelho** (5 cópias do mesmo arquétipo, um roster por arquétipo) — equilíbrio
  perfeito por simetria, identidade zero por construção. É a **solução trivial** do
  problema de equilíbrio, e portanto a resposta numérica à objeção *"por que não deixar
  os cinco iguais?"*, que até aqui não tinha resposta medida.
- **aleatório** (N rosters) — sem projeto nenhum. O chão absoluto.

Saída: cada métrica como `posição = (valor − piso) / (teto − piso)`, o **pior nulo** (o
melhor resultado que um roster sem estrutura alcançou) e um **p-valor empírico** — a
fração dos nulos que igualam ou superam o observado. O piso é uma **distribuição**, não
um ponto: com 13 nulos a resolução do p é 1/13, então `p = 0` afirma apenas `p < 0,08`.

```bash
py -m src.tools.baselines                      # só os rosters de referência
py -m src.tools.baselines --evolved            # + posiciona o melhor do AG
py -m src.tools.baselines --nsga2 scalar_optimum
py -m src.tools.baselines --n-random 20 --sims 200   # mais nulos = mais resolução no p
```

Também reporta **tríades circulares** (Kendall & Babington Smith 1940) como medida de
estrutura **sem autoria**: `C(n,3) − Σ C(dᵢ,2)`, na escala 0 (ordem estrita) · 2,5
(acaso) · 5 (máximo em 5 personagens). O máximo é exatamente o torneio **regular**, que
é o mesmo que equilíbrio global perfeito — um roster estritamente transitivo teria WRs
100/75/50/25/0, incompatível com todos perto de 50%. Por isso **equilíbrio global não é
achatamento: ele força estrutura não-transitiva**. A contagem só significa algo com
arestas *decididas*, então o espalhamento das WR por par vem sempre ao lado.

> **Por que o ciclo canônico não pode ser um achado.** Ele é um torneio regular (cada
> arquétipo vence 2 e perde 2) e existem **24** torneios regulares rotulados em 5
> vértices — acertar o rótulo específico é 1/24. O que sobrevive à troca de rótulos é a
> estrutura, não a atribuição; por isso `circular_triads` mede algo e
> `cycle_edges_kept` não.

## `archetype_validator`

Asserções de identidade em 3 camadas (rank ordinal entre os 5):

- **Layer 1 — estrutural inter (13):** rankings de genes entre os 5 personagens
  (Rushdown tem maior speed e menor cooldown, Zoner tem maior range/knockback/
  w_retreat, Combo Master tem maior stun, Grappler tem maior damage e maior
  `grab_power`, Turtle tem maior hp e cooldown, menor speed, maior w_defend).
- **Layer 2 — estrutural intra (5):** comparações normalizadas dentro de um
  personagem (`norm(range) > norm(speed)` no Zoner, etc.). Normalização = fração do
  range do bound `(x − lo)/(hi − lo)` (mesma convenção do `fitness`).
- **Layer 3 — comportamental (5):** identidade **funcional** (como o personagem
  *joga*), sobre o `behavioral_profile` (roda combate, estocástico). Uma asserção
  primária por arquétipo: Zoner = maior `mean_dist`; Rushdown = maior `atk_landed`;
  Turtle = maior `def_chosen` (guarda escolhido, não encurralado); Combo Master =
  maior `stun_inflicted`; Grappler = maior `guard_break` (dano arrancado pela guarda
  alheia).

  Até 2026-09-16 a Layer 3 tinha **4 asserções para 5 arquétipos**: sem a mecânica de
  agarrão, a identidade do Grappler não tinha expressão comportamental distinta do
  corpo-a-corpo do Rushdown. A entrada do `grab_power` fechou a lacuna — e não por
  acaso: era a mesma lacuna que o deixava com um único gene definidor e que deixava a
  aresta "Grappler vence Turtle" do ciclo sem mecanismo no motor.

> **Independência dos instrumentos.** As Layers 1-2 medem identidade **estrutural** —
> o mesmo eixo que o `drift_penalty` otimiza, já que os `defining_genes` de cada
> arquétipo espelham as asserções da Layer 1. São, portanto, **parcialmente
> endógenas**: um score alto ali em parte reflete a penalidade ter funcionado. A
> Layer 3 mede identidade **funcional** e nada no fitness referencia comportamento —
> é ela, com o ciclo de vantagens, que sustenta a leitura post-hoc de identidade.

Layers 1-2 são **ranking ordinal** de genes; resolvem rápido, sem combate. Por que
a Layer 3 importa: as estruturais não detectam quando os genes certos **não se
traduzem em ação** (ex.: Zoner com `w_retreat` alto que, encurralado, vira DEFEND
em vez de kitar). A Layer 3 fecha essa lacuna. É opt-in (`behavioral_n>0` em
`run_validation`); o standalone e o `report` a rodam por default (`--n`, `--seed`).

```bash
py -m src.tools.archetype_validator [--evolved | --nsga2 [rep]] [--n 200] [--seed 42]
py -m src.tools.archetype_validator --n 0    # só estrutural (Layers 1-2)
```

## `sensitivity_analysis`

> **Atualizado em 2026-09-16.** O piso de ruído deixou de ser estimado analiticamente e
> passou a ser **medido**, e a classificação inteira sai dele — antes havia dois
> critérios incompatíveis na mesma tabela (limiares fixos de 5%/3% na classificação, e um
> piso binomial impresso que não entrava nela). O piso analítico também era o desvio de
> **uma** proporção, enquanto o número classificado é uma **diferença** entre duas WRs.
>
> O piso medido é o `|Δ WR|` entre **duas avaliações do mesmo roster, sem perturbação
> nenhuma**, sob seeds diferentes (`--null-reps`): o Δ verdadeiro ali é zero, então tudo
> que aparece é ruído. Seeds diferentes são necessárias — com a mesma seed e perturbação
> zero as avaliações são bit-idênticas e o Δ sai exatamente 0. Quebrar o pareamento dá um
> piso **conservador**, já que a medição real usa CRN pareado e tem menos ruído.
>
> Critério único: `≤ piso` neutro · `≤ 2× piso` borderline · acima, visível.
>
> Ganhou também `--evolved` / `--nsga2`. Importa: **no canônico o roster é saturado**
> (Rushdown ~100%, Turtle ~0%), e com a WR presa no teto perturbar um gene não muda nada
> — quase tudo sai "neutro" por efeito de teto, não por neutralidade. A afirmação "o AG
> enxerga o cromossomo" precisa ser medida num roster equilibrado.


Para cada (arquétipo, atributo), perturba o gene em ±σ e mede `Δ WR`. Atributos
com `|Δ|` médio abaixo do piso binomial são genes "neutros" (drift por random
walk, sem pressão seletiva).

```bash
py -m src.tools.sensitivity_analysis --sims 500 --workers 1
```

O pareamento +σ/−σ é feito com `seed_combat(seed)` (o RNG do combate é interno ao
Numba — `random.seed` não o afeta), então os dois lados do par compartilham o mesmo
stream: o Δ medido é efeito do gene, não do sorteio. Ver
[09-reproducibility.md](09-reproducibility.md).

Salva a matriz completa em `results/sensitivity/sensitivity_analysis.json` (Δ WR por
arquétipo × atributo, σ usado por gene, piso de ruído binomial e a classificação
visível/borderline/neutro) — o console é volátil e a tabela é citada na validação
metodológica.

## `multi_run` — N execuções independentes + estatística agregada

Item 1.1 da metodologia (Eiben & Smith 2015; Deb 2001): um EA é estocástico, então
uma seed é uma **amostra**, não um resultado. Roda o algoritmo escolhido sobre N
sementes consecutivas (`MULTI_RUN_SEED_START..+N-1`), reavalia o melhor indivíduo de
cada execução sob uma **semente de validação fixa** (`MULTI_RUN_VALIDATION_SEED`) —
independente do treino e comum a todas as execuções (Common Random Numbers) — e agrega.

```bash
py -m src.tools.multi_run                    # ambos os algoritmos, defaults do config
py -m src.tools.multi_run --algorithm nsga2  # só NSGA-II (best_dominance por seed)
py -m src.tools.multi_run --algorithm ga     # só AG escalar (best por seed)
py -m src.tools.multi_run --n-seeds 30       # escala o experimento
```

Representante por execução: AG escalar → `best`. O NSGA-II devolve uma **fronteira**,
não um ponto — qual ponto representa a execução é uma escolha explícita
(`--nsga2-representative`, default `best_dominance`), gravada no artefato como
`nsga2_representative`. Saídas agregadas (impressas + salvas em `results/multi_run/multi_run_<algo>.json`):

- **média ± desvio** de `dominance_penalty` — **decomposto** nos três termos
  (`global_term`, `cap_term`, `decis_term`, gravados por semente e agregados) — e de
  `drift_penalty`. O composto sozinho não distingue perder no termo primário
  (peso 1,0) de perder num secundário (peso 0,5);
- **WR global por personagem** (média ± desvio) + **fração de sementes em que cada
  boneco fica equilibrado** (WR global em `[0.40, 0.60]`, via `character_balanced`);
- **hard-counters por execução** (média ± desvio; pares fora de `[0.35, 0.65]`);
- **fração de sementes que equilibram o ROSTER** (5 bonecos em banda **e** 0
  hard-counters) — a frase-tese (*"em N execuções, X% equilibraram o roster"*);
- **(secundário)** WR média por matchup + fração de sementes em que cada par vira
  counter duro;
- **(só NSGA-II)** hipervolume e spacing da fronteira por seed, média ± desvio
  (item 1.2 — ver [06-nsga2.md](06-nsga2.md)).

Parametrizado em `config.py` (`MULTI_RUN_*`) para escalar N facilmente. Mata a
fragilidade de amostra única: um matchup travado (ex.: Combo×Rush) numa seed pode ser
azar ou estrutural, e só N execuções respondem.

## `compare_algorithms` — comparação estatística AG × NSGA-II

O `multi_run` agrega média ± desvio de cada algoritmo, mas média ± desvio não decide
se a diferença entre os dois é real ou ruído de amostragem. Este tool **não roda
nada**: lê os dois artefatos do `multi_run` e aplica sobre as amostras por semente
(prática padrão para algoritmos estocásticos — Derrac et al. 2011; Arcuri & Briand
2011):

- **Mann-Whitney U** bicaudal (não-paramétrico, duas amostras independentes — não
  assume normalidade, e as métricas são limitadas por baixo em 0);
- **Â₁₂ de Vargha-Delaney** como tamanho de efeito — `P(execução do AG > execução do
  NSGA-II)`, com 0.5 = sem efeito. Um p pequeno diz que a diferença existe; o Â₁₂ diz
  se ela é grande o bastante para importar;
- **Holm-Bonferroni** sobre as 4 métricas testadas (`dominance_penalty`,
  `drift_penalty`, hard-counters por execução, bonecos em banda por execução) — sem
  correção, 4 testes a α=0.05 inflam a chance de falso positivo.

Além dos testes, imprime e grava a **decomposição do `dominance_penalty`**: mediana
dos três termos lado a lado, com o peso de cada um. É **descritiva** e fica
deliberadamente **fora** da bateria inferencial — somar métricas ao Mann-Whitney
infla a correção de Holm sobre as que já estão lá (item F da revisão). Serve para ler
de **onde** vem a diferença: o termo primário é o `global_term`, e é ele que diz quem
equilibra o roster melhor.

```bash
py -m src.tools.multi_run --algorithm both   # gera os dois artefatos
py -m src.tools.compare_algorithms           # compara e salva
```

Aborta se os dois `multi_run` não compartilharem sementes, semente de validação e
sims/matchup — comparar execuções sob condições diferentes não é comparação. Salva em
`results/multi_run/comparison_ga_vs_nsga2.json`, registrando também qual representante
da fronteira representou o NSGA-II.

## `external_validation` — validação externa ao fitness (estilo Ludi)

Item 3.2 da metodologia (Browne & Maire 2010): não confiar num único número de
fitness — validar o artefato evoluído **fora do laço de otimização**, sob condições
que o AG nunca otimizou. Fixa UM indivíduo (canônico / `--evolved` / `--nsga2 [rep]`)
e o reavalia sob K sementes de avaliação **totalmente novas** (`EXTERNAL_VALIDATION_*`,
a partir de 10000 — fora do range de treino 42.. e da seed do `multi_run` 9999), cada
uma com mais sims (`EXTERNAL_VALIDATION_SIMS=500`) para CI apertado.

```bash
py -m src.tools.external_validation                    # canônico
py -m src.tools.external_validation --evolved          # melhor do AG
py -m src.tools.external_validation --nsga2 best_dominance
py -m src.tools.external_validation --n-seeds 30 --sims 1000
```

Reporta, salvando em `results/external_validation/external_validation_<label>.json`:

- `dominance_penalty` / `drift_penalty` média ± desvio através das condições;
- por personagem: WR global média ± desvio + flag **robusto** (WR global em
  `[0.40, 0.60]` em TODAS as K condições);
- por matchup: WR média ± desvio + flag **⚠** (vira counter duro em ALGUMA condição);
- **veredito do roster**: ROBUSTO (todos os bonecos robustos **e** nenhum par vira
  counter duro) vs FRÁGIL (algum boneco/par sensível à semente → overfitting ao fitness).

**Diferença vs `multi_run` (1.1):** lá varia-se a *execução evolutiva* (muitos
indivíduos, uma seed de validação); aqui fixa-se UM indivíduo e varia-se a *avaliação*
(ruído fora do laço). Complementar: `multi_run` mede a fragilidade de amostra única do
processo; `external_validation` mede a robustez do artefato escolhido. A bateria de
**identidade** post-hoc (ciclo, drift, fingerprint, validador) é determinística nos
genes e já vive no `report`; este tool cobre o eixo **estocástico** (equilíbrio), onde
o overfitting ao fitness se esconde. A parte "contra política diferente" do método
liga-se ao item 2.1 (coevolução), fora do escopo deste tool.

## `viewer` / `web_viewer`

Visualizadores de uma luta, consumindo `CombatTrace`:

```bash
py -m src.tools.viewer          # ASCII no terminal
py -m src.tools.web_viewer      # browser interativo em localhost:8080
```

## `nsga2_plots`

Plot 2D da fronteira de Pareto (dominance × drift) com os 4 representantes
destacados. Chamado automaticamente por `py main.py --algorithm nsga2`; salva em
`results/plots/nsga2/<timestamp>/pareto_front.png`.
