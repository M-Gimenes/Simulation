# TCC — Decisões de Design

**Equilíbrio Competitivo e Preservação de Identidade Arquetípica em Jogos de Luta: uma Abordagem por Algoritmos Genéticos Multi-objetivo**
Matheus Gimenes de Souza — Bacharelado em Sistemas de Informação — Ifes Campus Cachoeiro de Itapemirim

> Este documento descreve o **estado atual** do sistema (mecânicas, fitness, AG,
> NSGA-II e hiperparâmetros). É documento-referência: deve ser atualizado
> sempre que uma decisão de design mudar. Pontos de discussão para a redação
> da tese (justificativas, achados, perguntas em aberto) ficam em
> `pontos_importantes.md`.

---

## Pergunta Central

> "É possível atingir equilíbrio competitivo entre personagens de arquétipos
> distintos usando Algoritmos Genéticos, sem que o processo destrua suas
> identidades funcionais?"

## Diferencial Acadêmico

Propor e validar uma forma de medir quantitativamente se arquétipos foram
preservados após a evolução. A preservação **não é forçada** — o AG evolui
livremente, e analisamos o quanto cada personagem derivou do seu perfil
inicial. Equilíbrio com preservação ou equilíbrio com homogeneização são
ambos resultados cientificamente válidos — comparar os dois cenários é o
experimento central.

---

## Os 5 Arquétipos

### Ciclo de vantagens canônico — cada arquétipo vence 2 e perde para 2

| Arquétipo    | Vence                    | Motivo FGC                                              |
| ------------ | ------------------------ | ------------------------------------------------------- |
| Rushdown     | Zoner e Combo Master     | pressão não deixa iniciar setup                         |
| Zoner        | Grappler e Turtle        | controla espaço, fica fora da zona de punição           |
| Grappler     | Rushdown e Turtle        | grab é o counter canônico ao bloqueio; burst pune recuo |
| Combo Master | Grappler e Zoner         | Grappler lento morre pra combo; burst converte acerto   |
| Turtle       | Rushdown e Combo Master  | bloqueio absorve pressão e quebra setup de combo        |

> O ciclo **não está codificado em nenhuma penalidade do fitness**. É medido
> post-hoc como métrica de avaliação. Codificá-lo tornaria a pergunta de
> pesquisa circular ("o AG preserva identidade quando eu pago para preservar").

### Justificativas

- **Zoner:** Controla espaço com alcance máximo e knockback. Ataca antes do inimigo chegar e mantém distância. Perde para quem fecha rapidamente (Rushdown) ou converte um acerto em burst (Combo Master).
- **Rushdown:** Explode quem precisa de setup. Se ferra contra absorvedores de pressão (Turtle) e personagens com burst alto em contra-ataque (Grappler).
- **Combo Master:** Encadeia combos via stun — Grappler lento não escapa e Zoner morre para um acerto convertido. Perde para pressão constante (Rushdown) e para quem bloqueia o setup (Turtle).
- **Grappler:** Se encosta, acabou — burst máximo. Grab é o counter canônico ao bloqueio (Turtle). Sofre contra rápidos (Rushdown) e Combo Master que stuna antes.
- **Turtle:** Vive de erro do outro — destrói agressivos por atrito de HP%. Bloqueia o setup do Combo Master. Perde para quem controla distância (Zoner) e para o grab do Grappler.

---

## Atributos dos Personagens

### Bounds do AG

| Atributo        | Mín   | Máx   | Semântica                                                     |
| --------------- | ----- | ----- | ------------------------------------------------------------- |
| HP              | 300   | 400   | Pontos de vida                                                |
| Damage          | 10    | 20    | Dano por hit (unidades de HP) — mínimo de ~15 hits para KO    |
| Attack Cooldown | 1     | 5     | Ticks de espera entre ataques; menor = mais rápido            |
| Range           | 5     | 20    | Alcance em unidades de campo (todos < distância inicial = 50) |
| Speed           | 1     | 5     | Unidades de campo por tick                                    |
| Defense         | 0     | 0.30  | Redução de dano recebido (0 = nenhuma, 0.30 = 30%)            |
| Stun            | 0     | 5     | Ticks de stun causado (modificado por recovery do defensor)   |
| Knockback       | 0     | 3     | Unidades de campo empurradas por hit                          |
| Recovery        | 0     | 10    | **Inteiro em sub-ticks** subtraídos do stun recebido           |

> **Bounds apertados em relação a versões anteriores** (eram HP 300–500,
> defense 0–0.5, knockback 0–5, recovery 0–0.7 float multiplicativo). O
> aperto eliminou exploits do AG: tank acima do Turtle, defesa absurda,
> zoning trivial via expulsão de range, e stun-immunity via recovery
> extrema. Recovery virou inteiro subtrativo para eliminar o platô
> multiplicativo (mutações pequenas eram invisíveis após `round()`).

### Valores canônicos (semente inicial do AG)

| Classe       | HP  | Dmg | Cooldown | Range | Speed | Defense | Stun | Knockback | Recovery |
| ------------ | --- | --- | -------- | ----- | ----- | ------- | ---- | --------- | -------- |
| Zoner        | 300 | 12  | 4        | 18    | 2.5   | 0.05    | 1.0  | 2.0       | 2        |
| Rushdown     | 320 | 11  | 1        | 10    | 5.0   | 0.10    | 1.0  | 1.0       | 3        |
| Combo Master | 350 | 13  | 3        | 10    | 3.0   | 0.15    | 3.5  | 0.5       | 3        |
| Grappler     | 380 | 20  | 4        | 8     | 2.0   | 0.20    | 2.5  | 0.5       | 4        |
| Turtle       | 400 | 10  | 5        | 13    | 1.5   | 0.25    | 2.0  | 1.0       | 7        |

### Pesos comportamentais canônicos (w_*)

| Classe       | w_retreat | w_defend | w_aggressiveness |
| ------------ | --------- | -------- | ---------------- |
| Zoner        | 0.60      | 0.20     | 0.30             |
| Rushdown     | 0.05      | 0.10     | 0.90             |
| Combo Master | 0.05      | 0.20     | 0.70             |
| Grappler     | 0.10      | 0.40     | 0.70             |
| Turtle       | 0.40      | 0.70     | 0.20             |

Os valores canônicos **não são hardcoded** no motor — são usados como semente
da população inicial e como baseline para medir drift. O AG diverge
livremente.

---

## Estrutura do Indivíduo no AG

Cada indivíduo representa o **conjunto completo dos 5 personagens** — não um
personagem isolado. Razão: o WR de cada personagem depende dos outros 4
simultaneamente; evoluir um personagem isolado não tem sentido.

**Total: 60 genes por indivíduo** (5 personagens × 12 genes cada)

- Cromossomo 1 — Atributos (9 genes): `[hp, damage, attack_cooldown, range, speed, defense, stun, knockback, recovery]`
- Cromossomo 2 — Pesos comportamentais (3 genes): `[w_retreat, w_defend, w_aggressiveness]`

---

## Simulação de Combate

Toda a lógica vive **exclusivamente** dentro de funções JIT compiladas pelo
Numba (`_simulate_combat_jit` para o fitness, `_simulate_combat_traced_jit`
para tools que precisam de instrumentação tick-a-tick). Não há
reimplementação Python paralela do loop — tools que precisam visualizar a
luta consomem `CombatTrace` em vez de redobrar a lógica.

### Campo

- Tamanho: 100 unidades
- Distância inicial entre lutadores: 50 unidades (posições 25 e 75)
- Distância mínima: 0 / máxima: 100
- `WALL_CORNER_THRESHOLD = 10`: dentro de 10 unidades das paredes, considera-se encurralado

### TICK_SCALE — resolução sub-tick

`TICK_SCALE = 5` é um multiplicador que aumenta a resolução temporal dos
timers internos (cooldown, stun, movimento). Sem ele, `attack_cooldown ∈
[1, 5]` teria apenas 5 valores discretos, criando platôs amplos no espaço de
fitness. Com TICK_SCALE, internamente operam de 5 a 25 sub-ticks.

- Movimento por sub-tick: `speed / TICK_SCALE`
- Cooldown na hora do hit: `round(attack_cooldown * TICK_SCALE)`
- Stun na hora do hit: `round(attacker.stun * TICK_SCALE) − defender.recovery`, com cap

### 4 Ações Disponíveis

`ATTACK` | `ADVANCE` | `RETREAT` | `DEFEND`

### Sistema de Decisão (priority-based)

Por sub-tick, prioridade decrescente:

```
1. ATTACK            — em range próprio E cooldown pronto
2. ADVANCE           — fora de range OU encurralado contra parede
3. HELD COMMITMENT   — repete a última ação soft-policy se persist > 0
4. NEW SOFT POLICY   — sorteia ADVANCE / RETREAT / DEFEND
                       com probabilidades ∝ (w_aggressiveness, w_retreat, w_defend)
                       e fixa a escolha por ACTION_PERSISTENCE_SUBTICKS sub-ticks
```

> **Soft policy é a única fonte de estocasticidade do combate.** Versões
> antigas do sistema usavam comparação dura entre os pesos
> (`w_aggressiveness > w_retreat AND w_aggressiveness > w_defend → ADVANCE`),
> o que tornava os pesos *categóricos*: só importava a ordem; magnitudes
> eram invisíveis ao AG. A soft policy faz cada peso ter efeito contínuo:
> Δ no peso vira Δ proporcional na probabilidade da ação, dando ao AG
> gradiente em todo o domínio dos pesos.

### Persistência de ação (`ACTION_PERSISTENCE_SUBTICKS = 10`)

Uma vez sorteada uma ação por soft policy, ela é mantida pelos próximos 10
sub-ticks (≈ 2 ticks lógicos) antes de re-sortear. Sem persistência, o
personagem rolaria o dado 5× por tick lógico, gerando flip-flopping
patológico entre RETREAT/DEFEND/ADVANCE. A persistência simula
commitment / momentum: decidir recuar é uma decisão que dura uma batida.

A persistência é **interrompida** quando alguma prioridade superior dispara
(ATTACK ou ADVANCE forçado por estar fora de range / encurralado).

### Fluxo por sub-tick

1. **Escolha de ação** (sistema de prioridade acima). Personagem stunado perde a ação.
2. **Movimento** (ADVANCE / RETREAT) — passo `speed / TICK_SCALE`, clamped a `[0, FIELD_SIZE]`.
3. **Snapshot dos timers** (para o decremento "decrement-stale").
4. **Resolução simultânea de ataques A→B e B→A** — aplica dano, stun, knockback, e seta cooldown do atacante apenas se `dmg > 0`.
5. **Decremento de timers stale** — só decrementa timers que **não** foram setados neste tick.

### Regras de combate

- **Dano determinístico**: `damage × (1 − defense)`. Sem variância por hit.
- **DEFEND** reduz o dano recebido para `damage × (1 − defense) × DEFEND_DAMAGE_REDUCTION` (40% do dano com `DEFEND_DAMAGE_REDUCTION = 0.4`, ou seja, 60% de redução).
- **Stun efetivo**: `max(0, round(attacker.stun × TICK_SCALE) − defender.recovery)`, com cap em `STUN_CAP_MULTIPLIER × attacker.attack_cooldown × TICK_SCALE`.
- **`STUN_CAP_MULTIPLIER = 0.6`** garante que o stun é estritamente menor que o cooldown do atacante — o defensor sempre tem uma janela livre antes do próximo hit. Quebra o soft-perma-lock que existia em valores ≥ 1.0.
- **Cooldown só em acerto**: o cooldown do atacante só é setado quando há dano efetivo (`if dmg > 0.0`). Um ATTACK fora de range não desperdiça cooldown.
- **Knockback**: empurra o defensor `knockback` unidades para longe do atacante após cada hit, clamped ao campo.

### Decremento pós-ataque (decrement-stale)

Decrementos acontecem no **fim** do tick, comparando o valor atual com o
valor pré-ataque. Se um ataque setou o timer neste tick (`current > pre`),
ele é preservado até o próximo. Isso garante que `stun = 1` e `cooldown =
1` (em ticks lógicos) sejam valores mínimos com efeito significativo.

### Condição de vitória

- **KO**: HP chega a zero
- **Timer esgotado** (`MAX_TICKS = 500 × TICK_SCALE = 2500` sub-ticks): vence quem tem maior HP percentual `(hp_atual / hp_max)`

---

## Função de Fitness

### AG escalar (mono-objetivo)

```
fitness = -(LAMBDA_SPECIALIZATION × specialization_penalty
          + LAMBDA_DRIFT          × drift_penalty
          + LAMBDA_DOMINANCE      × dominance_penalty)
```

Todos os termos em `[0, 1]`, todos minimizados.

| Termo                    | Peso (LAMBDA) | O que penaliza                                       |
| ------------------------ | ------------- | ---------------------------------------------------- |
| `specialization_penalty` | 0.2           | Builds homogêneas internas (max−min normalizado)     |
| `drift_penalty`          | 6.0           | Distância euclidiana ao perfil canônico              |
| `dominance_penalty`      | 1.0           | Dominância em matchups (RMS de excessos sobre 60%)   |

Avaliação por **round-robin completo**: C(5,2) = 10 matchups × `SIMS_PER_MATCHUP` simulações.

### `specialization_penalty`

`specialization_i = max(atributos_normalizados_i) − min(atributos_normalizados_i)`

Mede dispersão interna de cada build (0 = atributos homogêneos, 1 = máxima
diferença). Penaliza personagens sem identidade — impede que todos evoluam
para builds genéricos e neutros.

```
specialization_penalty = 1 − mean_i(specialization_i)
```

### `drift_penalty`

Distância euclidiana normalizada ao perfil canônico, calculada sobre
atributos e pesos juntos:

```
deviation_i = sqrt(mean( ((attr_norm − canonical_norm)² ) + ((w − w_canonical)² ) ))
drift_penalty = mean_i(deviation_i)
```

Ponderada por `LAMBDA_DRIFT = 6.0`, é o termo mais pesado do fitness escalar
— reflete o trade-off central do TCC: queremos balance, mas não a ponto de
descaracterizar arquétipos.

### `dominance_penalty`

```
excess_ij        = max(0, |score_ij − 0.5| − MATCHUP_THRESHOLD) / (0.5 − MATCHUP_THRESHOLD)
dominance_penalty = sqrt(mean_ij(excess_ij²))
```

- **Direcionalmente cego**: usa `|score − 0.5|`, não codifica qual lado deveria vencer cada matchup. Codificar o ciclo aqui forçaria identidade → pergunta circular.
- **HP-weighted scoring**: opera sobre `matchup_scores`, não WR binário. Em KO, score é 1.0/0.0; em timeout, score é a fração de HP% do vencedor (`hp_pct_i / (hp_pct_i + hp_pct_j)`). Um stalemate 55%/45% entra como score≈0.55, não 1.0. Razão: matchups que estouram `MAX_TICKS` sem KO seriam coin flips em sinal binário; o score contínuo elimina o falso sinal.
- **RMS, não mean**: o quadrado faz matchups extremos (100/0) pesarem ~16× mais que moderados (70/30), evitando que o AG "esconda" um matchup destruído atrás de uma média balanceada.
- **`MATCHUP_THRESHOLD = 0.10`**: matchups dentro de [40%, 60%] não penalizam.

### NSGA-II ignora os λ

`evaluate_objectives` retorna apenas `(dominance_penalty, drift_penalty)` em
escala bruta. O Pareto front é calculado nessas duas dimensões sem
ponderação. Mudar `LAMBDA_*` não afeta o NSGA-II.

---

## Critérios de Convergência

O AG escalar para por convergência quando **ambos**:

1. `dominance_penalty ≈ 0` no melhor indivíduo (sem matchup acima de 60%)
2. Cada matchup direto: `|wr_ij − 0.5| ≤ MATCHUP_CONVERGENCE_THRESHOLD` (0.10), confirmado com `SIMS_CONVERGENCE_CHECK = 200` simulações extras

Outras condições de parada: `STAGNATION_LIMIT = 30` gerações sem melhoria
> 0.001, ou `MAX_GENERATIONS = 150`.

---

## Operadores do AG

### Seleção

Torneio com `TOURNAMENT_SIZE = 3` (escalar) ou torneio binário por
dominância + crowding (NSGA-II).

### Cruzamento

Por **bloco de personagem** — cada personagem do filho é clonado integral
de um dos pais (50/50). Preserva coerência interna entre atributos e pesos
de um mesmo arquétipo. Crossover por gene quebraria builds coerentes ao
misturar atributos de arquétipos incompatíveis.

### Mutação

Gaussiana com sigma como fração do range, aplicada gene a gene com
probabilidade `MUTATION_RATE = 0.05`:

- Atributos: `sigma = ATTRIBUTE_MUTATION_SIGMA × (max − min)` = 10% do range
- Pesos: `sigma = WEIGHT_MUTATION_SIGMA × (max − min)` = 2.5% do range

Pesos têm sigma 4× menor (inércia evolutiva): atributos definem capacidade,
pesos definem estratégia — explorar mais capacidades do que mudar de
estratégia.

`Character.clip()` aplica os bounds após cada mutação. Atributos em
`INTEGER_ATTRIBUTES` (atualmente apenas `recovery`, índice 8) são
arredondados para int após o clamp — a representação interna continua
float (mutação gaussiana é contínua, dando gradiente ao AG), mas o valor
armazenado e usado no combate é inteiro.

### Elitismo

Top 10% (`ELITE_SIZE = int(POPULATION_SIZE × 0.1) = 30` para `POPULATION_SIZE = 300`) preservados diretamente a cada geração.

---

## NSGA-II — Otimização Multi-objetivo

Variante multi-objetivo do AG (Deb et al., 2002), ativada com
`--algorithm nsga2`. Otimiza **2 objetivos** simultaneamente, ambos
minimizados:

| Objetivo            | Significado                                                |
| ------------------- | ---------------------------------------------------------- |
| `dominance_penalty` | Dominância de matchups (RMS sobre HP-weighted scores)      |
| `drift_penalty`     | Preservação de arquétipo (distância euclidiana ao canônico)|

**4 representantes** são extraídos automaticamente da Pareto front:

- `best_dominance` — mínimo em `dominance_penalty`
- `best_drift` — mínimo em `drift_penalty`
- `knee_point` — ponto de máxima curvatura (mais distante da reta entre os dois extremos)
- `ideal_point` — mais próximo da utopia `(0, 0)` em distância euclidiana

O NSGA-II torna explícito o trade-off que o AG mono-objetivo colapsa num
escalar — exatamente a tensão central do TCC entre balance e preservação
de arquétipo.

---

## Validação de Arquétipos (`tools/archetype_validator.py`)

20 asserções estruturais verificam preservação ordinal das identidades:

- **Layer 1 — Inter-character (14 asserções)**: rankings entre os 5 personagens — Rushdown tem maior `speed`, Zoner tem maior `range`, Turtle tem maior `hp`/`defense`/`recovery`, etc.
- **Layer 2 — Intra-character normalizado (6 asserções)**: comparações dentro do mesmo personagem em escala normalizada — `norm(range) > norm(speed)` no Zoner, `norm(speed) > norm(range)` no Rushdown, etc.

São verificações de **ranking ordinal**, não de magnitude absoluta — por
exemplo: "Zoner tem maior range que todos" (não "Zoner tem range ≥ X").

**Limitação importante**: o validator não detecta homogeneização funcional.
Se todos os personagens convergirem para valores próximos mas o Zoner ainda
tiver `range = 20.1` e os demais `range = 20.0`, todas as asserções passam
— mas a diferença funcional é nula. O mecanismo de proteção real contra
homogeneização é `LAMBDA_DRIFT > 0` no fitness escalar (e a presença de
`drift_penalty` como objetivo no NSGA-II).

---

## Tools de análise

| Tool                          | Função                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------- |
| `tools/analyze_matchups.py`   | Roda matchups do canônico ou de um indivíduo evoluído, com estatísticas finais  |
| `tools/sensitivity_analysis.py` | ±σ Δ-WR por gene — detecta atributos neutros (drift por random walk)          |
| `tools/archetype_validator.py`| 20 asserções ordinais sobre identidade arquetípica                              |
| `tools/viewer.py`             | ASCII viewer da luta (consome `CombatTrace`)                                    |
| `tools/web_viewer.py`         | Browser viewer interativo em `localhost:8080` (consome `CombatTrace`)           |
| `tools/nsga2_plots.py`        | Plots da Pareto front 2D                                                        |

---

## Hiperparâmetros (estado atual em `src/config.py`)

| Parâmetro                        | Valor    | Efeito                                                                |
| -------------------------------- | -------- | --------------------------------------------------------------------- |
| `POPULATION_SIZE`                | 300      | Tamanho da população                                                  |
| `ELITE_SIZE`                     | 30       | 10% × POPULATION_SIZE — preservados por elitismo                      |
| `MAX_GENERATIONS`                | 150      | Limite de gerações                                                    |
| `STAGNATION_LIMIT`               | 30       | Gerações sem melhoria > 0.001 antes de parar                          |
| `MATCHUP_CONVERGENCE_THRESHOLD`  | 0.10     | Desvio máximo de WR por matchup para declarar convergência            |
| `TOURNAMENT_SIZE`                | 3        | Candidatos por torneio (AG escalar)                                   |
| `MUTATION_RATE`                  | 0.05     | Probabilidade de mutação por gene                                     |
| `ATTRIBUTE_MUTATION_SIGMA`       | 0.10     | Sigma como fração do range (atributos)                                |
| `WEIGHT_MUTATION_SIGMA`          | 0.025    | Sigma como fração do range (pesos) — inércia evolutiva                |
| `SIMS_PER_MATCHUP`               | 150      | Simulações por matchup no round-robin (~4% binomial std @ 50% WR)     |
| `SIMS_CONVERGENCE_CHECK`         | 200      | Sims extras para confirmar convergência                               |
| `LAMBDA_SPECIALIZATION`          | 0.2      | Peso da specialization_penalty (AG escalar)                           |
| `LAMBDA_DRIFT`                   | 6.0      | Peso da drift_penalty (AG escalar) — alto, é o trade-off central      |
| `LAMBDA_DOMINANCE`               | 1.0      | Peso da dominance_penalty (AG escalar)                                |
| `MATCHUP_THRESHOLD`              | 0.10     | Excesso acima de 50% que inicia penalização (60% WR = limiar)         |
| `TICK_SCALE`                     | 5        | Resolução sub-tick (5–25 valores internos por gene de tempo)          |
| `MAX_TICKS`                      | 2500     | `500 × TICK_SCALE` — duração máxima de uma luta em sub-ticks          |
| `ACTION_PERSISTENCE_SUBTICKS`    | 10       | Sub-ticks que uma ação soft-policy é mantida antes de re-sortear      |
| `STUN_CAP_MULTIPLIER`            | 0.6      | Cap de stun = mult × cooldown do atacante. `< 1.0` quebra perma-lock  |
| `DEFEND_DAMAGE_REDUCTION`        | 0.4      | Multiplicador no dano recebido ao defender (40% recebido = 60% red.)  |
| `FIELD_SIZE`                     | 100      | Tamanho do campo                                                      |
| `INITIAL_DISTANCE`               | 50       | Distância inicial entre lutadores                                     |
| `WALL_CORNER_THRESHOLD`          | 10       | Distância da parede para considerar encurralado                       |
| `N_WORKERS`                      | None     | Núcleos para avaliação paralela (None = todos)                        |
| `NSGA2_POP_SIZE`                 | 300      | Alias de POPULATION_SIZE                                              |
| `NSGA2_GENERATIONS`              | 150      | Alias de MAX_GENERATIONS                                              |
| `NSGA2_OBJECTIVES`               | (dom, drift) | Objetivos do NSGA-II                                              |

---

## Decisões Arquiteturais

- **Dois algoritmos compartilhando o mesmo motor**: AG escalar (mono-objetivo) e NSGA-II (multi-objetivo) compartilham simulação, fitness por componente e operadores. O NSGA-II torna explícito o trade-off que o escalar colapsa num peso `LAMBDA_DRIFT` fixo.
- **Preservação emergente, não imposta**: arquétipos não são forçados — o AG evolui livremente e a preservação é medida via `drift_penalty`. Variar `LAMBDA_DRIFT` (no escalar) ou caminhar pela Pareto front (NSGA-II) é o experimento central do TCC.
- **Soft policy probabilística com persistência**: única fonte de estocasticidade no combate. Modela mistura comportamental real (jogador não é 100% consistente), dá gradiente contínuo ao AG sobre os 3 pesos, e torna `drift_penalty` em pesos coerente com o comportamento que ele mede.
- **Combate determinístico no dano**: variância por hit (`DAMAGE_VARIANCE`) e ação aleatória uniforme (`ACTION_EPSILON`) foram **removidas**. Reduziam o sinal das mutações abaixo do piso de ruído binomial sem trazer realismo proporcional. Estocasticidade é desejável só onde modela incerteza estratégica relevante.
- **Pesos como probabilidades, não limiares**: cada peso tem efeito contínuo sobre `P(ação)`. Antes (hard policy), pesos eram efetivamente categóricos — `WEIGHT_MUTATION_SIGMA = 0.025` raramente cruzava o threshold entre dois pesos, então a maioria das mutações era invisível ao AG.
- **Inércia evolutiva nos pesos**: sigma de mutação 4× menor que atributos. Atributos = capacidade; pesos = estratégia. Queremos explorar mais capacidades do que mudar de estratégia.
- **Decremento pós-ataque (decrement-stale)**: garante que valores mínimos de stun e cooldown (= 1 tick lógico) sejam semanticamente significativos.
- **Cooldown só em acerto**: ataque que sai mas erra (distância pode ter mudado depois do movimento) não desperdiça cooldown.
- **`STUN_CAP_MULTIPLIER < 1.0`**: stun é estritamente menor que o cooldown do atacante. Garante uma janela livre entre hits — quebra o soft-perma-lock degenerado em que stun ≈ cooldown fazia o defensor reentrar no stun assim que saía.
- **Recovery como inteiro subtrativo**: cada unidade subtrai 1 sub-tick do stun recebido. A versão multiplicativa `stun × (1 − recovery_float)` produzia rounding plateaus invisíveis ao AG.
- **HP-weighted scoring no `dominance_penalty`**: stalemates por timeout entram com sinal proporcional ao HP%, não como coin flip binário. Eliminou o falso sinal em pares lentos como Zoner × Turtle.
- **RMS no `dominance_penalty`**: extremos pesam 16× mais que moderados — impede o AG de "esconder" um matchup destruído atrás de uma média balanceada.
- **TICK_SCALE elimina platôs**: sem o multiplicador, `attack_cooldown ∈ {1,2,3,4,5}` cria 5 gradientes discretos. Com `TICK_SCALE = 5`, internamente vai de 5 a 25, dando 21 posições distintas — landscape de fitness mais suave.
- **Crossover por bloco de personagem**: preserva coerência interna entre atributos e pesos do mesmo arquétipo.
- **Validator como diagnóstico, não constraint**: as 20 asserções verificam identidade estrutural após a evolução, mas não são aplicadas como restrição hard durante o AG. Isso mantém o espaço de busca contínuo e evita zonas proibidas artificiais.
- **Loop de combate único, JIT-only**: toda a lógica vive em duas funções `@njit` (`_simulate_combat_jit` e `_simulate_combat_traced_jit`). Não há reimplementação Python paralela — tools que precisam de instrumentação consomem `CombatTrace`. Elimina a fonte tradicional de divergência entre Python e JIT.
