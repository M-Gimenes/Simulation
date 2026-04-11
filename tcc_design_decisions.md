# TCC — Decisões de Design

**Aplicação de Algoritmos Genéticos para o Balanceamento de Personagens em Jogos Competitivos Digitais**
Matheus Gimenes de Souza — Bacharelado em Sistemas de Informação — Ifes Campus Cachoeiro de Itapemirim

---

## Pergunta Central

> "É possível atingir equilíbrio competitivo entre personagens de arquétipos distintos usando Algoritmos Genéticos, sem que o processo destrua suas identidades funcionais?"

## Diferencial Acadêmico

Propor e validar uma forma de medir quantitativamente se arquétipos foram preservados após a evolução. A preservação **não é forçada** — o AG evolui livremente e analisamos o quanto cada personagem derivou do seu perfil inicial. O resultado pode ser equilíbrio com preservação ou equilíbrio com homogeneização — ambos são válidos cientificamente.

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

| Atributo        | Mín   | Máx   | Semântica                                           |
| --------------- | ----- | ----- | --------------------------------------------------- |
| HP              | 300   | 500   | Pontos de vida                                      |
| Damage          | 10    | 20    | Dano por hit (unidades de HP)                       |
| Attack Cooldown | 1     | 5     | Ticks de espera entre ataques; menor = mais rápido  |
| Range           | 5     | 20    | Alcance em unidades de campo (todos < distância inicial de 50) |
| Speed           | 1     | 5     | Unidades de campo por tick                          |
| Defense         | 0     | 0.5   | Redução de dano recebido (0 = nenhuma, 0.5 = 50%)  |
| Stun            | 0     | 5     | Ticks de stun causado (modificado por recovery do defensor) |
| Knockback       | 0     | 5     | Unidades de campo empurradas por hit                |
| Recovery        | 0     | 0.5   | Resistência a stun (0 = nenhuma, 0.5 = 50% redução)|

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

### Fluxo por tick

1. **Escolha de ação** via sistema de prioridade (personagem stunado perde a ação; com probabilidade `ACTION_EPSILON`, ação aleatória)
2. **Movimento** (ADVANCE / RETREAT) — ambos alteram posição absoluta
3. **Ataques** resolvidos simultaneamente — aplica dano (com variância ±15%), stun, knockback, e seta cooldown do atacante
4. **Decremento de timers** — apenas timers não recém-setados por ataque neste tick

> O decremento ocorre no final do tick. Timers setados por um ataque neste tick não são decrementados até o próximo, garantindo que `stun=1` e `cooldown=1` sejam valores mínimos com efeito real.

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

Os três pesos competem simetricamente — o dominante vence. Não há limiares fixos,
o que garante que o espaço genético seja contínuo e o AG tenha gradiente real para
evoluir o comportamento sob ameaça.

Pesos ativos (3 por personagem): `w_retreat`, `w_defend`, `w_aggressiveness`.

### Regras de Combate

- ATTACK causa dano apenas se `distance ≤ range`; cooldown só é setado em acerto (sem desperdício em whiff)
- DEFEND reduz dano para `damage * (1 - defense) * 0.2` quando o oponente ataca no mesmo tick
- Stun efetivo: `round(attacker.stun * (1 - defender.recovery))`, cap = `round(attacker.attack_cooldown)`
- Knockback: empurra o defensor `knockback` unidades para longe após cada hit

### Condição de Vitória

- **KO:** HP chega a zero
- **Timer esgotado:** vence quem tem maior HP percentual `(hp_atual / hp_max)`

---

## Função de Fitness

```
balance_error          = mean(|winrate_i - 0.5|)          para cada personagem i (WR agregado)
attribute_cost         = 1 - mean_specialization           sobre todos os personagens
drift_penalty          = mean(distância_normalizada_ao_canônico_i)
matchup_dominance_pen  = max(excess_ij)                    pior matchup direto (não mean — evita diluição)

fitness = (1 - balance_error)
        - LAMBDA         * attribute_cost
        - LAMBDA_DRIFT   * drift_penalty
        - LAMBDA_MATCHUP * matchup_dominance_penalty
```

Avaliação por **round-robin completo**: 10 matchups únicos × `SIMS_PER_MATCHUP` simulações.

### Por que max e não mean no matchup_dominance_penalty

`mean` dilui: um personagem com 100% vs um e 50% vs três teria penalidade de apenas 0.25. Com `max`, um único matchup absurdo já puxa a penalidade ao máximo, forçando o GA a corrigir dominâncias individuais.

---

## Critérios de Convergência

O GA para quando **ambos** são satisfeitos (confirmados com `SIMS_CONVERGENCE_CHECK` simulações extras):

1. WR agregado de cada personagem: `|wr_i - 0.5| ≤ CONVERGENCE_THRESHOLD` (0.03)
2. Cada matchup direto: `|wr_ij - 0.5| ≤ MATCHUP_CONVERGENCE_THRESHOLD` (0.20)

A condição 2 impede parada prematura quando um personagem tem 50% médio mas domina um adversário específico.

---

## Operadores do AG

### Seleção

Torneio com K=3.

### Cruzamento

Por personagem completo (bloco) — preserva coerência interna entre atributos e pesos.

### Mutação

Gaussian com sigma = fração do range. Pesos têm sigma menor (inércia evolutiva):
- Atributos: `sigma = 0.05 * (max - min)`
- Pesos: `sigma = 0.02 * (max - min)`

### Elitismo

Top 10% preservados diretamente a cada geração.

---

## Hiperparâmetros

| Parâmetro                     | Valor | Efeito                                                  |
| ----------------------------- | ----- | ------------------------------------------------------- |
| `POPULATION_SIZE`             | 100   | Tamanho da população                                    |
| `ELITE_SIZE`                  | 10    | Indivíduos preservados por elitismo (10%)               |
| `MAX_GENERATIONS`             | 20    | Limite de gerações                                      |
| `STAGNATION_LIMIT`            | 50    | Gerações sem melhoria > 0.001 antes de parar            |
| `CONVERGENCE_THRESHOLD`       | 0.03  | Desvio máximo de WR agregado para convergência          |
| `MATCHUP_CONVERGENCE_THRESHOLD` | 0.20 | Desvio máximo de WR por matchup para convergência      |
| `LAMBDA`                      | 0.2   | Peso da penalidade de especialização                    |
| `LAMBDA_DRIFT`                | 0.0   | Peso da âncora ao canônico (0 = evolução livre)         |
| `LAMBDA_MATCHUP`              | 1.0   | Peso da penalidade do pior matchup direto               |
| `MATCHUP_THRESHOLD`           | 0.15  | Excesso acima de 50% que começa a penalizar (65%)       |
| `SIMS_PER_MATCHUP`            | 15    | Simulações por matchup (estabilidade de WR)             |
| `SIMS_CONVERGENCE_CHECK`      | 50    | Simulações extras para confirmar convergência           |
| `DAMAGE_VARIANCE`             | 0.20  | ±20% por hit — variância de execução no dano            |
| `ACTION_EPSILON`              | 0.10  | Prob. de ação aleatória por tick — erro de decisão      |
| `MUTATION_RATE`               | 0.1   | Taxa de mutação por gene                                |
| `TOURNAMENT_SIZE`             | 3     | Candidatos por seleção por torneio                      |

---

## Decisões Arquiteturais Importantes

- **Modularidade:** Simulação e GA são módulos independentes. O AG pode ser comparado futuramente com MAP-Elites, NSGA-II, etc.
- **Preservação emergente:** Arquétipos não são forçados — o AG evolui livremente e a preservação é medida via `LAMBDA_DRIFT`.
- **Sistema de prioridade determinístico:** Simula um jogador experiente — mesma situação → mesma ação. Academicamente mais defensável que softmax: separa *identidade* (quem o personagem é, via `w_*`) de *competência* (o que ele faz em cada situação, via prioridades fixas).
- **Estocasticidade em duas camadas:** `DAMAGE_VARIANCE=0.20` (±20% por hit) modela imprecisão de execução no dano; `ACTION_EPSILON=0.10` (10% de ação aleatória por tick) modela erros de decisão. As duas fontes são independentes e se combinam para criar spread suficiente para winrates não-binários em 15 simulações.
- **Pesos como limiares comportamentais:** `w_aggressiveness >= 0.7` separa agressivos (Rushdown, Grappler, CM) de reativos (Zoner, Turtle). `w_retreat > w_defend` separa kitadores de absorvedores.
- **Inércia evolutiva:** Pesos (`w_*`) têm sigma de mutação menor que atributos, tendendo a preservar comportamento naturalmente.
- **Decremento pós-ataque:** Garante que valores mínimos de stun e cooldown (= 1) sejam semanticamente significativos.
- **Penalidade por pior matchup (max):** Força o GA a corrigir dominâncias individuais, não apenas médias.
- **Cooldown só em acerto:** Personagem que tenta atacar fora de range não desperdiça cooldown (tratado em `_resolve_attack`).
