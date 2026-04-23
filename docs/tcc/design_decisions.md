# TCC — Decisões de Design

**Aplicação de Algoritmos Genéticos para o Balanceamento de Personagens em Jogos Competitivos Digitais**
Matheus Gimenes de Souza — Bacharelado em Sistemas de Informação — Ifes Campus Cachoeiro de Itapemirim

---

## Pergunta Central

> "É possível atingir equilíbrio competitivo entre personagens de arquétipos distintos usando Algoritmos Genéticos, sem que o processo destrua suas identidades funcionais?"

## Diferencial Acadêmico

Propor e validar uma forma de medir quantitativamente se arquétipos foram preservados após a evolução. A preservação **não é forçada** — o AG evolui livremente e analisamos o quanto cada personagem derivou do seu perfil inicial. O resultado pode ser equilíbrio com preservação ou equilíbrio com homogeneização — ambos são válidos cientificamente e constituem em si os dois cenários que a tese compara.

---

## Os 5 Arquétipos

### Ciclo de vantagens fechado — cada arquétipo vence 2 e perde para 2

| Arquétipo    | Vence                   |
| ------------ | ----------------------- |
| Grappler     | Combo Master e Rushdown |
| Combo Master | Turtle e Zoner          |
| Zoner        | Grappler e Turtle       |
| Turtle       | Rushdown e Grappler     |
| Rushdown     | Zoner e Combo Master    |

### Justificativas

- **Zoner:** Controla espaço com alcance máximo e knockback. Sofre contra quem fecha distância rápido.
- **Rushdown:** Explode quem precisa de setup. Se ferra contra quem aguenta pressão e pune erro.
- **Combo Master:** Encadeia combos via stun. Perde para pressão constante e burst alto.
- **Grappler:** Se encosta, acabou — burst máximo. Sofre contra distância e quem stuna.
- **Turtle:** Vive de erro do outro — destrói agressivos por atrito de HP%. Perde para quem quebra defesa com stun.

---

## Atributos dos Personagens

### Limites (bounds do AG)

| Atributo        | Mín   | Máx   | Semântica                                                     |
| --------------- | ----- | ----- | ------------------------------------------------------------- |
| HP              | 300   | 500   | Pontos de vida                                                |
| Damage          | 10    | 20    | Dano por hit (unidades de HP)                                 |
| Attack Cooldown | 1     | 5     | Ticks de espera entre ataques; menor = mais rápido            |
| Range           | 5     | 20    | Alcance em unidades de campo (todos < distância inicial = 50) |
| Speed           | 1     | 5     | Unidades de campo por tick                                    |
| Defense         | 0     | 0.5   | Redução de dano recebido (0 = nenhuma, 0.5 = 50%)             |
| Stun            | 0     | 5     | Ticks de stun causado (modificado por recovery do defensor)   |
| Knockback       | 0     | 5     | Unidades de campo empurradas por hit                          |
| Recovery        | 0     | 0.7   | Resistência a stun (0 = nenhuma, 0.7 = 70% redução)          |

### Valores canônicos (semente inicial do AG)

| Classe       | HP  | Dmg | Cooldown | Range | Speed | Defense | Stun | Knockback | Recovery |
| ------------ | --- | --- | -------- | ----- | ----- | ------- | ---- | --------- | -------- |
| Zoner        | 300 | 12  | 3        | 20    | 2.0   | 0.10    | 1.0  | 5.0       | 0.30     |
| Rushdown     | 320 | 11  | 2        | 10    | 5.0   | 0.20    | 1.0  | 1.0       | 0.20     |
| Combo Master | 310 | 13  | 3        | 10    | 3.0   | 0.25    | 2.0  | 0.5       | 0.25     |
| Grappler     | 450 | 20  | 5        | 8     | 1.5   | 0.35    | 4.0  | 0.5       | 0.40     |
| Turtle       | 500 | 10  | 4        | 15    | 1.0   | 0.50    | 3.0  | 3.0       | 0.50     |

### Pesos comportamentais canônicos (w_*)

| Classe       | w_retreat | w_defend | w_aggressiveness |
| ------------ | --------- | -------- | ---------------- |
| Zoner        | 0.6       | 0.2      | 0.3              |
| Rushdown     | 0.1       | 0.1      | 0.9              |
| Combo Master | 0.0       | 0.2      | 0.7              |
| Grappler     | 0.1       | 0.5      | 0.8              |
| Turtle       | 0.5       | 0.7      | 0.2              |

Os valores canônicos **não são hardcoded** no motor — são usados como semente da população inicial e como baseline para medir drift. O AG pode divergir livremente deles.

---

## Estrutura do Indivíduo no AG

Cada indivíduo representa o **conjunto completo dos 5 personagens** — não um personagem isolado. Isso porque o winrate de cada personagem depende de todos os outros simultaneamente.

**Total: 60 genes por indivíduo** (5 personagens × 12 genes cada)

- Cromossomo 1 — Atributos (9 genes): `[hp, damage, attack_cooldown, range, speed, defense, stun, knockback, recovery]`
- Cromossomo 2 — Pesos comportamentais (3 genes): `[w_retreat, w_defend, w_aggressiveness]`

---

## Simulação de Combate

### Campo

- Tamanho: 100 unidades
- Distância inicial entre lutadores: 50 unidades (posições 25 e 75)
- Distância mínima: 0 / máxima: 100

### TICK_SCALE — Resolução Sub-tick

`TICK_SCALE = 5` é um multiplicador que aumenta a resolução temporal dos timers internos (cooldown e stun). Sem ele, `attack_cooldown ∈ [1, 5]` teria apenas 5 valores discretos possíveis, criando platôs amplos no espaço de fitness e dificultando a evolução.

Com TICK_SCALE, os valores internos operam em sub-ticks:

- Cooldown armazenado: `round(attack_cooldown × TICK_SCALE)` → 5 a 25 sub-ticks
- Stun armazenado: `_resolve_attack` já retorna em sub-ticks internamente
- Movimento por sub-tick: `speed / TICK_SCALE`

Qualquer reimplementação do loop de combate (ex.: `analyze_matchups.py`) deve aplicar TICK_SCALE corretamente para ser fiel ao motor principal.

### Fluxo por tick

1. **Escolha de ação** via sistema de prioridade (personagem stunado perde a ação; com probabilidade `ACTION_EPSILON`, ação aleatória)
2. **Movimento** (ADVANCE / RETREAT) — ambos alteram posição absoluta com passo `speed / TICK_SCALE`
3. **Ataques** resolvidos simultaneamente — aplica dano (com variância ±20%), stun, knockback, e seta cooldown do atacante em `round(attack_cooldown × TICK_SCALE)` sub-ticks
4. **Decremento de timers** — apenas timers não recém-setados por ataque neste tick

> O decremento ocorre no final do tick. Timers setados por um ataque neste tick não são decrementados até o próximo, garantindo que `stun=1` e `cooldown=1` (em ticks reais) sejam valores com efeito mínimo significativo.

### 4 Ações Disponíveis

`ATTACK` | `ADVANCE` | `RETREAT` | `DEFEND`

### Sistema de Decisão — Prioridade

Modela um jogador experiente com decisões determinísticas baseadas no estado atual. Os pesos `w_*` controlam limiares comportamentais, não probabilidades — mesmo estado → mesma ação.

```
Prioridades (ordem decrescente):
  1. ATTACK  — se em range e pronto (can_hit)
  2. Sob ameaça (inimigo pronto e dentro de RETREAT_ZONE_FACTOR × range_inimigo):
       w_aggressiveness > w_retreat E w_aggressiveness > w_defend → ADVANCE
       w_retreat > w_defend → RETREAT  (kite / criar distância)
       senão                → DEFEND   (absorver e punir na oportunidade)
  3. ADVANCE — fora de range ou encurralado (próximo à parede)
  4. DEFEND  — default: em range, em cooldown, sem ameaça ativa
```

Os três pesos competem simetricamente — o dominante vence. Não há limiares fixos, o que garante que o espaço genético seja contínuo e o AG tenha gradiente real para evoluir o comportamento sob ameaça.

### Regras de Combate

- ATTACK causa dano apenas se `distance ≤ range`; cooldown só é setado em acerto (sem desperdício em whiff)
- DEFEND reduz dano para `damage × (1 - defense) × 0.2` quando o oponente ataca no mesmo tick
- Stun efetivo: `round(attacker.stun × (1 - defender.recovery))`, cap = `round(attacker.attack_cooldown × STUN_CAP_MULTIPLIER × TICK_SCALE)`
- `STUN_CAP_MULTIPLIER = 2.0` → permite exatamente 1 hit extra durante o stun, habilitando combo chaining sem lockdown infinito
- Knockback: empurra o defensor `knockback` unidades para longe após cada hit

### Condição de Vitória

- **KO:** HP chega a zero
- **Timer esgotado:** vence quem tem maior HP percentual `(hp_atual / hp_max)`

---

## Função de Fitness

```
balance_error          = mean(|wr_i - 0.5|)  sobre os 5 personagens (WR agregado)
attribute_cost         = 1 - mean(specialization_i)  sobre os 5 personagens
drift_penalty          = mean(distância_euclidiana_normalizada_ao_canônico_i)
matchup_dominance_pen  = mean(excess_ij)  sobre os 10 pares  ← mean, não max

fitness = (1 - balance_error)
        - LAMBDA         × attribute_cost
        - LAMBDA_DRIFT   × drift_penalty
        - LAMBDA_MATCHUP × matchup_dominance_penalty
```

Avaliação por **round-robin completo**: C(5,2) = 10 matchups × `SIMS_PER_MATCHUP` simulações.

`BALANCE_MODE = "aggregate"` — `balance_error` usa WR agregado por personagem (média dos matchups em que participou), não o WR de cada par direto.

### Specialization (attribute_cost)

`specialization_i = max(atributos_normalizados_i) - min(atributos_normalizados_i)`

Mede dispersão interna do build: 0 = atributos homogêneos, 1 = máxima diferença. Penaliza personagens sem identidade de build — impede que todos evoluam para builds genéricos e neutros.

### Drift Penalty

Distância euclidiana normalizada ao perfil canônico, calculada sobre atributos e pesos juntos:

```
deviation_i = sqrt(mean((attr_norm - canonical_norm)² + (w - w_canonical)²))
drift_penalty = mean(deviation_i)
```

Com `LAMBDA_DRIFT = 0.0`, a penalidade é calculada e logada mas **não influencia o fitness** — o AG evolui livremente. Aumentar `LAMBDA_DRIFT` ancora os personagens ao canônico.

### Por que mean (não max) no matchup_dominance_penalty

`mean(excess_ij)` dá sinal de gradiente para **todos os matchups problemáticos**. Se um personagem domina dois adversários e o GA corrige um, o fitness melhora — sinal contínuo que guia a evolução.

Com `max`, o GA recebe sinal apenas do pior matchup isolado. Corrigir um par ruim enquanto outro piora não muda o fitness se o segundo se tornar o novo máximo — o gradiente some nos demais pares.

`excess_ij = max(0, |wr_ij - 0.5| - MATCHUP_THRESHOLD) / (0.5 - MATCHUP_THRESHOLD)`

Pares dentro de `MATCHUP_THRESHOLD` (60% WR) não penalizam.

---

## Critérios de Convergência

O AG para quando **ambos** são satisfeitos (confirmados com `SIMS_CONVERGENCE_CHECK` simulações extras):

1. `balance_error ≤ CONVERGENCE_THRESHOLD` (0.02) — WR agregado de cada personagem próximo de 50%
2. Cada matchup direto: `|wr_ij - 0.5| ≤ MATCHUP_CONVERGENCE_THRESHOLD` (0.10) — nenhum par com dominância acima de 60%

A condição 2 impede parada prematura quando um personagem tem 50% de WR médio mas domina um adversário específico.

---

## Operadores do AG

### Seleção

Torneio com K=3.

### Cruzamento

Por personagem completo (bloco) — preserva coerência interna entre atributos e pesos comportamentais de um mesmo arquétipo.

### Mutação

Gaussiana com sigma como fração do range. Pesos têm sigma menor (inércia evolutiva):
- Atributos: `sigma = ATTRIBUTE_MUTATION_SIGMA × (max - min)` = 10% do range
- Pesos: `sigma = WEIGHT_MUTATION_SIGMA × (max - min)` = 2% do range

### Elitismo

Top 10% (ELITE_SIZE = 10) preservados diretamente a cada geração.

---

## NSGA-II — Otimização Multi-objetivo

Além do AG mono-objetivo, o sistema implementa o NSGA-II (Deb et al., 2002) como algoritmo alternativo, ativado com `--algorithm nsga2`.

Em vez de colapsar tudo num único escalar de fitness, o NSGA-II otimiza os 3 objetivos simultaneamente, todos minimizados:

| Objetivo                    | Fórmula                      | Significado                           |
| --------------------------- | ---------------------------- | ------------------------------------- |
| `f1 = balance_error`        | mean(\|wr_i - 0.5\|)         | Equilíbrio agregado                   |
| `f2 = matchup_dominance`    | mean(excess_ij) sobre 10 pares | Pior matchup direto                 |
| `f3 = drift_penalty`        | mean(desvio_euclidiano_i)    | Preservação de arquétipo             |

O resultado é uma **fronteira de Pareto** — conjunto de soluções em que melhorar um objetivo implica piorar outro. Cinco representantes são extraídos automaticamente:

- `best_balance` — mínimo em f1
- `best_matchup` — mínimo em f2
- `best_drift` — mínimo em f3
- `knee_point` — ponto de máxima curvatura (mais distante do plano formado pelos 3 extremos)
- `ideal_point` — mais próximo da utopia (0, 0, 0) em distância euclidiana

O NSGA-II torna explícito o trade-off que o AG mono-objetivo colapsa num escalar — especialmente a tensão entre balanceamento (f1+f2) e preservação de arquétipo (f3), que é a pergunta central do TCC.

---

## Validação de Arquétipos (archetype_validator.py)

20 asserções estruturais verificam se o indivíduo preserva as identidades arquetípicas. São verificações de **ranking ordinal**, não de magnitude absoluta — por exemplo: "Zoner tem maior range que todos" (não "Zoner tem range ≥ X").

Grupos de asserções:
- Dominância de atributos específicos por arquétipo (range do Zoner, cooldown do Rushdown, HP do Turtle, etc.)
- Pesos comportamentais consistentes com o papel (Rushdown agressivo, Turtle defensivo, Zoner kitador)
- Invariantes combinados (Grappler tem burst alto = dano alto + cooldown lento)

**Limitação importante:** o validator não detecta homogeneização funcional. Se todos os personagens convergirem para valores próximos mas o Zoner ainda tiver `range = 20.1` e os demais `range = 20.0`, todas as 20 asserções passam — mas a diferença funcional é nula. O mecanismo de proteção real contra homogeneização é `LAMBDA_DRIFT > 0` (ver seção seguinte).

---

## Risco de Homogeneização Silenciosa

O AG pode, em princípio, satisfazer todas as 20 asserções do validator e ainda assim homogeneizar funcionalmente os personagens — mantendo diferenças ordinais mínimas que passam nas verificações sem gerar comportamento distinto no combate.

**Por que isso acontece:** com `LAMBDA_DRIFT = 0.0`, o fitness não penaliza desvio do canônico. O AG pode convergir para um equilíbrio em que todos os personagens têm atributos próximos, com diferenças suficientes apenas para preservar a ordem (Zoner tem o maior range, Rushdown o menor cooldown), mas não a magnitude que define a identidade.

**Como detectar:** `drift_penalty` é sempre calculado e logado mesmo com `LAMBDA_DRIFT = 0`. Um drift alto com boa balance_error indica homogeneização.

**Como mitigar:** aumentar `LAMBDA_DRIFT`. Isso cria a tensão central do TCC — quanto maior o LAMBDA_DRIFT, mais os personagens preservam sua identidade e mais difícil fica atingir equilíbrio perfeito. O NSGA-II expõe essa fronteira explicitamente sem precisar ajustar o escalar manualmente.

---

## Hiperparâmetros

| Parâmetro                        | Valor   | Efeito                                                          |
| -------------------------------- | ------- | --------------------------------------------------------------- |
| `POPULATION_SIZE`                | 100     | Tamanho da população                                            |
| `ELITE_SIZE`                     | 10      | Indivíduos preservados por elitismo (10%)                       |
| `MAX_GENERATIONS`                | 100     | Limite de gerações                                              |
| `STAGNATION_LIMIT`               | 50      | Gerações sem melhoria > 0.001 antes de parar                    |
| `CONVERGENCE_THRESHOLD`          | 0.02    | Desvio máximo de balance_error para convergência (≈48–52%)      |
| `MATCHUP_CONVERGENCE_THRESHOLD`  | 0.10    | Desvio máximo de WR por matchup para convergência (60%)         |
| `TOURNAMENT_SIZE`                | 3       | Candidatos por seleção por torneio                              |
| `MUTATION_RATE`                  | 0.1     | Probabilidade de mutação por gene                               |
| `ATTRIBUTE_MUTATION_SIGMA`       | 0.1     | Sigma como fração do range (atributos)                          |
| `WEIGHT_MUTATION_SIGMA`          | 0.02    | Sigma como fração do range (pesos) — inércia evolutiva          |
| `LAMBDA`                         | 0.2     | Peso da penalidade de especialização                            |
| `LAMBDA_DRIFT`                   | 0.0     | Peso da âncora ao canônico (0 = evolução livre)                 |
| `LAMBDA_MATCHUP`                 | 1.0     | Peso da penalidade de matchup (mean dos excessos)               |
| `MATCHUP_THRESHOLD`              | 0.10    | Excesso acima de 50% que começa a penalizar (60% WR = limiar)   |
| `SIMS_PER_MATCHUP`               | 30      | Simulações por matchup (estabilidade de WR)                     |
| `SIMS_CONVERGENCE_CHECK`         | 50      | Simulações extras para confirmar convergência                   |
| `DAMAGE_VARIANCE`                | 0.20    | ±20% por hit — variância de execução no dano                    |
| `ACTION_EPSILON`                 | 0.20    | Prob. de ação aleatória por tick — erro de decisão              |
| `TICK_SCALE`                     | 5       | Resolução sub-tick para cooldown e stun (5× mais granularidade) |
| `STUN_CAP_MULTIPLIER`            | 2.0     | Cap de stun = multiplier × cooldown do atacante                 |
| `NSGA2_POP_SIZE`                 | 100     | Tamanho da população do NSGA-II (alias de POPULATION_SIZE)      |
| `NSGA2_GENERATIONS`              | 100     | Gerações do NSGA-II (alias de MAX_GENERATIONS)                  |
| `N_WORKERS`                      | None    | Núcleos para avaliação paralela (None = todos)                  |
| `BALANCE_MODE`                   | aggregate | Como calcular balance_error (aggregate = WR por personagem)  |

---

## Decisões Arquiteturais

- **Dois algoritmos independentes:** AG clássico (mono-objetivo) e NSGA-II (multi-objetivo) compartilham o mesmo motor de simulação e operadores. O NSGA-II torna explícito o trade-off que o AG colapsa num escalar.
- **Preservação emergente:** Arquétipos não são forçados — o AG evolui livremente e a preservação é medida via `drift_penalty`. `LAMBDA_DRIFT = 0.0` é o ponto de partida; variar esse parâmetro é o experimento central do TCC.
- **Sistema de prioridade determinístico:** Simula um jogador experiente — mesma situação → mesma ação. Academicamente mais defensável que softmax: separa *identidade* (quem o personagem é, via `w_*`) de *competência* (o que ele faz em cada situação, via prioridades fixas).
- **Estocasticidade em duas camadas:** `DAMAGE_VARIANCE = 0.20` (±20% por hit) modela imprecisão de execução no dano; `ACTION_EPSILON = 0.20` (20% de ação aleatória por tick) modela erros de decisão. As duas fontes são independentes e criam spread suficiente para winrates não-binários em 30 simulações.
- **Pesos como limiares comportamentais:** `w_aggressiveness ≥ 0.7` separa agressivos (Rushdown, Grappler, CM) de reativos. `w_retreat > w_defend` separa kitadores (Zoner) de absorvedores (Turtle).
- **Inércia evolutiva:** Pesos (`w_*`) têm sigma de mutação 5× menor que atributos, tendendo a preservar comportamento naturalmente — o AG precisa de pressão seletiva maior para mudar estratégias do que para ajustar estatísticas.
- **Decremento pós-ataque:** Garante que valores mínimos de stun e cooldown (= 1 tick real) sejam semanticamente significativos. Timers setados no tick atual não decrementam até o próximo.
- **Cooldown só em acerto:** Personagem que tenta atacar fora de range não desperdiça cooldown — tratado dentro do `if dmg > 0` em `_resolve_attack`. Incentiva o AG a evoluir range coerente com o papel do personagem.
- **TICK_SCALE elimina platôs:** Sem o multiplicador, `attack_cooldown ∈ {1, 2, 3, 4, 5}` cria apenas 5 gradientes discretos. Com TICK_SCALE=5, os valores internos vão de 5 a 25, dando ao AG 21 posições distintas — landscape de fitness mais suave.
- **Crossover por bloco de personagem:** Preserva coerência entre atributos e pesos de um mesmo arquétipo. Crossover por gene individual quebraria builds coerentes ao misturar atributos de arquétipos incompatíveis.
- **Validator como diagnóstico, não como constraint:** As 20 asserções verificam identidade estrutural após a evolução, mas não são aplicadas como restrição hard durante o AG. Isso mantém o espaço de busca contínuo e evita zonas proibidas artificiais.
