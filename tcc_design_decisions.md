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

| Arquétipo | Vence |
|---|---|
| Grappler | Combo Master e Rushdown |
| Combo Master | Turtle e Zoner |
| Zoner | Grappler e Turtle |
| Turtle | Rushdown e Grappler |
| Rushdown | Zoner e Combo Master |

### Justificativas

- **Zoner:** Controla espaço, destrói quem precisa chegar andando. Sofre contra quem entra rápido ou pune padrão.
- **Rushdown:** Explode quem precisa de setup. Se ferra contra quem aguenta pressão e pune erro.
- **Combo Master:** Precisa tocar — ganha de quem dá abertura ou joga lento. Perde para pressão constante e burst alto.
- **Grappler:** Se encosta, acabou — pune quem precisa ficar perto. Sofre contra distância e defesa sólida.
- **Turtle:** Vive de erro do outro — destrói agressivos. Perde para quem não se expõe ou quebra defesa.

---

## Atributos dos Personagens (escala 0–100)

### Princípios de calibração
- **Regra dos 5 hits**: o golpe mais forte (Grappler, dmg=15) contra o defensor mais fraco
  (Combo Master, HP=60, def=35%) resulta em 15×0.65=9.75 de dano por hit → mínimo 6 hits para matar.
  Nenhum 1-shot ou 2-shot possível nos valores canônicos.
- **Damage reduzido** (6–15 em vez de 25–90): diferenciação vem de HP, defense, cooldown e stun.
- **Range < distância inicial (50)** para todos: nenhum personagem ataca no primeiro tick;
  há sempre uma fase de aproximação. Exceção: Zoner range=45 fica a 5 unidades da distância
  inicial, garantindo vantagem imediata mas não instantânea.

| Classe | HP | Damage | Cooldown | Range | Speed | Defense | Stun | Knockback | Recovery |
|---|---|---|---|---|---|---|---|---|---|
| Zoner | 60 | 10 | 30 | 45 | 35 | 25 | 20 | 55 | 40 |
| Rushdown | 65 | 10 | 10 | 20 | 90 | 30 | 35 | 20 | 25 |
| Combo Master | 60 | 12 | 15 | 20 | 85 | 35 | 80 | 20 | 65 |
| Grappler | 90 | 15 | 70 | 15 | 30 | 65 | 55 | 40 | 85 |
| Turtle | 95 | 6 | 65 | 35 | 25 | 90 | 25 | 30 | 80 |

### Lógica dos valores por arquétipo

| Arquétipo | Atributo dominante | Atributo mínimo | Mecanismo de vitória |
|---|---|---|---|
| Zoner | range=45, knockback=55 | defense=25, stun=20 | Kiting: empurra oponente para fora do range; acumula hits grátis durante aproximação |
| Rushdown | speed=90, cooldown=10 | range=20, recovery=25 | Volume de ataques (1 wait → ataca a cada 2 ticks); fecha distância antes de Zoner acumular hits |
| Combo Master | stun=80, speed=85 | hp=60, defense=35 | Lockdown: stun cap=2/ciclo de 3t → oponente age 1/3 do tempo; encadeia combos em cima |
| Grappler | hp=90, damage=15 | range=15, speed=30 | Burst próximo + recovery=85 resiste stun do CM; alta defense absorve aproximação |
| Turtle | hp=95, defense=90 | damage=6, speed=25 | Atrito: quase imune a dano direto; vence agressivos pelo timer com HP% superior |

---

## Estrutura do Indivíduo no AG

Cada indivíduo representa o **conjunto completo dos 5 personagens** — não um personagem isolado. Isso porque o winrate de cada personagem depende de todos os outros simultaneamente.

**Total: 70 genes por indivíduo** (5 personagens × 14 genes cada)

### Cromossomo 1 — Attributes (9 genes)
```
[hp, damage, cooldown, range, speed, defense, stun, knockback, recovery]
```

### Cromossomo 2 — Behavioral Weights (5 genes)
```
[w_attack, w_advance, w_retreat, w_defend, w_aggressiveness]
```

---

## Simulação de Combate

### Campo
- Tamanho: 100 unidades
- Distância inicial: 50
- Distância mínima: 0 / máxima: 100

### Movimentação
```python
distance_moved = (speed / 100) * 5
```

### 4 Ações Disponíveis
`attack` | `advance` | `retreat` | `defend`

### Sistema de Decisão — Softmax Scoring
```python
me_hit    = in_range * (1 - cooldown)
enemy_hit = enemy_in_range * (1 - enemy_cooldown)

damage_value = me_hit * damage
risk         = enemy_hit * enemy_damage

score_attack  = w_attack  * me_hit * (damage_value - risk)
score_advance = w_advance * (1 - me_hit) * (damage_value - risk + w_aggressiveness)
score_retreat = w_retreat * enemy_hit * (risk - damage_value)
score_defend  = w_defend  * enemy_hit * risk
```

Ação escolhida via **softmax** sobre os 4 scores.

### Regras de Combate
- `attack` só é possível se `distance <= range`
- `defend` reduz dano para 20% quando oponente ataca no mesmo tick:
  `damage_final = damage * (1 - defense) * 0.2`
- `stun` trava o oponente por X ticks após hit
- `knockback` empurra o oponente X unidades após hit

### Condição de Vitória
- **KO:** HP chega a zero
- **Timer esgotado:** vence quem tem maior HP percentual `(hp_atual / hp_max)`

---

## Função de Fitness

```python
balance_error  = mean(|winrate_i - 0.5|)   # para cada personagem i
attribute_cost = sum(attribute²) / normalization
fitness = (1 - balance_error) - λ * attribute_cost
```

Avaliação por **round-robin completo**: 10 matchups únicos por indivíduo.

---

## Operadores do AG

### Seleção
Torneio com K=3.

```python
def tournament_selection(population, k=3):
    candidates = random.sample(population, k)
    return max(candidates, key=lambda x: x.fitness)
```

### Cruzamento
Por personagem completo (bloco) — preserva coerência interna entre atributos e pesos de cada personagem.

```python
def crossover(parent1, parent2):
    child = []
    for character in range(5):
        donor = random.choice([parent1, parent2])
        child.append(donor[character])
    return child
```

### Mutação
W's têm mutation strength menor que atributos para criar **inércia evolutiva** que tende a preservar arquétipos naturalmente.

```python
attribute_bounds = [
    (0, 100),  # hp
    (0, 100),  # damage
    (0, 100),  # cooldown
    (0, 100),  # range
    (0, 100),  # speed
    (0, 100),  # defense
    (0, 100),  # stun
    (0, 100),  # knockback
    (0, 100),  # recovery
]

weight_bounds = [
    (0, 1),  # w_attack
    (0, 1),  # w_advance
    (0, 1),  # w_retreat
    (0, 1),  # w_defend
    (0, 1),  # w_aggressiveness
]

def mutate(individual, mutation_rate=0.1):
    for character in individual:
        # attributes — higher mutation strength
        for i in range(len(character.attributes)):
            if random.random() < mutation_rate:
                min_v, max_v = attribute_bounds[i]
                sigma = 0.05 * (max_v - min_v)
                character.attributes[i] += random.gauss(0, sigma)
                character.attributes[i] = clip(character.attributes[i], min_v, max_v)

        # weights — lower mutation strength to preserve archetype inertia
        for i in range(len(character.weights)):
            if random.random() < mutation_rate:
                min_v, max_v = weight_bounds[i]
                sigma = 0.02 * (max_v - min_v)
                character.weights[i] += random.gauss(0, sigma)
                character.weights[i] = clip(character.weights[i], min_v, max_v)

    return individual
```

### Elitismo
Top 10% preservados diretamente a cada geração.

---

## Hiperparâmetros

```python
POPULATION_SIZE        = 100
ELITE_SIZE             = 10     # 10% de 100
MAX_GENERATIONS        = 500
CONVERGENCE_THRESHOLD  = 0.02   # winrate entre 48% e 52%
STAGNATION_LIMIT       = 50     # gerações sem melhoria > 0.001
MAX_TICKS              = 500    # duração máxima de uma partida
LAMBDA                 = 0.3    # peso da penalidade de custo no fitness
MUTATION_RATE          = 0.1
TOURNAMENT_SIZE        = 3
```

---

## Decisões Arquiteturais Importantes

- **Modularidade:** O AG pode ser trocado facilmente — simulação e fitness são módulos independentes. Futuramente pode ser comparado com MAP-Elites, NSGA-II ou outros.
- **Preservação emergente:** Arquétipos não são forçados — o AG evolui livremente e a preservação é medida comparando perfil final vs perfil inicial de cada personagem.
- **Urgência por timer:** Descartada por ora — fica como trabalho futuro.
- **Comportamento emergente:** W's evoluem junto com atributos, não são hardcoded.
- **Inércia evolutiva:** W's têm mutation strength menor que atributos, tendendo a preservar arquétipos naturalmente sem impor restrições.
- **Custo quadrático:** `custo(x) = x²` — atributos extremos são punidos exponencialmente, evitando super-heróis sem bloquear valores altos quando necessários.
