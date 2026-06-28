# 08 — Ferramentas

Em `src/tools/`. Todas rodam como módulo a partir da raiz (`py -m src.tools.<nome>`)
e operam sobre o canônico, o melhor do AG (`--evolved`) ou um representante do
NSGA-II (`--nsga2 [rep]`).

## `report` — dossiê do indivíduo (porta de entrada)

**Um comando** que compõe os tools de avaliação num relatório único: cabeçalho de
fitness (fitness, drift_penalty, dominance_penalty) + matchups (equilíbrio) + drift
de genes + diferenciação (homogeneização) + fingerprint (comportamento) + validador
(estrutura). Não duplica lógica — chama as funções dos outros tools.

```bash
py -m src.tools.report --evolved    # dossiê completo do melhor do AG
py -m src.tools.report --nsga2 best_dominance
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
  `[30%, 70%]` (`fitness.is_hard_counter`, `|WR − 50%| > MATCHUP_WR_CAP`); dentro do
  teto é `=` (aresta de ciclo permitida, não desbalanço). Leitura secundária ao
  headline global.
- **Ciclo canônico** (descritivo, não pass/fail): o favorito observado bate com o
  vencedor esperado pelo ciclo? `→ mantido` / `↯ invertido`. O ciclo é métrica
  *post-hoc*, nunca alvo.

## `drift_table`

Decompõe o `drift_penalty` por personagem e por gene: canônico vs evoluído, Δ
absoluto e Δ normalizado (mesma normalização do fitness — atributos por máximo do
bound, pesos crus). O desvio por personagem (`deviation_i`) vem de
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

## `archetype_validator`

Asserções de identidade em 3 camadas (rank ordinal entre os 5):

- **Layer 1 — estrutural inter (12):** rankings de genes entre os 5 personagens
  (Rushdown tem maior speed e menor cooldown, Zoner tem maior range/knockback/
  w_retreat, Combo Master tem maior stun, Grappler tem maior damage, Turtle tem
  maior hp e cooldown, menor speed, maior w_defend).
- **Layer 2 — estrutural intra (5):** comparações normalizadas dentro de um
  personagem (`norm(range) > norm(speed)` no Zoner, etc.). Normalização = fração do
  máximo `x/hi` (mesma convenção do `fitness`).
- **Layer 3 — comportamental (4):** identidade **funcional** (como o personagem
  *joga*), sobre o `behavioral_profile` (roda combate, estocástico). Uma asserção
  primária por arquétipo: Zoner = maior `mean_dist`; Rushdown = maior `atk_landed`;
  Turtle = maior `def_chosen` (guarda escolhido, não encurralado); Combo Master =
  maior `stun_inflicted`. **Grappler não recebe asserção** — o combate não modela
  grab/throw, então sua identidade não tem expressão comportamental distinta
  (fica fora do denominador, marcado no relatório). Achado honesto: 4 de 5
  identidades se expressam funcionalmente.

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

Para cada (arquétipo, atributo), perturba o gene em ±σ e mede `Δ WR`. Atributos
com `|Δ|` médio abaixo do piso binomial são genes "neutros" (drift por random
walk, sem pressão seletiva).

```bash
py -m src.tools.sensitivity_analysis --sims 500 --workers 1
```

> ⚠️ A redução de variância por pareamento de seeds descrita no docstring **não
> está funcionando** — o combate roda no RNG do Numba, que ignora `random.seed`.
> Ver [09-reproducibility.md](09-reproducibility.md) e
> [10-known-issues.md](10-known-issues.md).

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

Representante por execução: AG escalar → `best`; NSGA-II → `best_dominance` da
fronteira. Saídas agregadas (impressas + salvas em `results/multi_run/multi_run_<algo>.json`):

- **média ± desvio** de `dominance_penalty` e `drift_penalty`;
- **WR global por personagem** (média ± desvio) + **fração de sementes em que cada
  boneco fica equilibrado** (WR global em `[0.40, 0.60]`, via `character_balanced`);
- **hard-counters por execução** (média ± desvio; pares fora de `[0.30, 0.70]`);
- **fração de sementes que equilibram o ROSTER** (5 bonecos em banda **e** 0
  hard-counters) — a frase-tese (*"em N execuções, X% equilibraram o roster"*);
- **(secundário)** WR média por matchup + fração de sementes em que cada par vira
  counter duro;
- **(só NSGA-II)** hipervolume e spacing da fronteira por seed, média ± desvio
  (item 1.2 — ver [06-nsga2.md](06-nsga2.md)).

Parametrizado em `config.py` (`MULTI_RUN_*`) para escalar N facilmente. Mata a
fragilidade de amostra única: um matchup travado (ex.: Combo×Rush) numa seed pode ser
azar ou estrutural, e só N execuções respondem.

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

> **Nota:** o JSON de `external_validation` commitado no repo é **obsoleto** (gerado
> pré-C2/pré-mudança de combate) — re-rodar após calibrar (ver
> [10-known-issues.md](10-known-issues.md)).

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
