# 07 — Configuração

Todos os hiperparâmetros em `src/engine/config.py`. Single source — nada de
constantes espalhadas.

## Bounds dos genes (`ATTRIBUTE_BOUNDS`, `WEIGHT_BOUNDS`)

| Atributo | Mín | Máx | Semântica |
|---|---|---|---|
| HP | 300 | 400 | pontos de vida |
| Damage | 10 | 20 | dano por hit — mínimo ~15 hits para KO (300/20) |
| Attack Cooldown | 1 | 5 | ticks entre ataques; menor = mais rápido |
| Range | 5 | 20 | alcance (todos < distância inicial 50) |
| Speed | 1 | 5 | unidades de campo por tick |
| Defense | 0 | 0.30 | redução de dano recebido |
| Stun | 0 | 5 | ticks de stun causado (antes de recovery e cap) |
| Knockback | 0 | 3 | unidades empurradas por hit |
| Recovery | 0 | 10 | **inteiro** em sub-ticks subtraídos do stun recebido |
| w_retreat / w_defend / w_aggressiveness | 0 | 1 | pesos da soft policy |

`INTEGER_ATTRIBUTES = {8}` (recovery) — arredondado para int em `clip()`.

### Calibração (por que estes bounds)

Bounds apertados em relação a versões antigas (eram HP 300–500, defense 0–0.5,
knockback 0–5, recovery 0–0.7 float). Cada aperto fechou um exploit do AG:

- **HP 300–400:** elimina "tank acima do Turtle" como espaço de exploit.
- **Defense ≤ 0.30:** teto colado no Turtle (0.25) + headroom; evita defesa absurda.
- **Knockback ≤ 3:** teto razoável acima do Zoner (2); evita zoning trivial por
  expulsão de range.
- **Recovery 0–10 inteiro:** teto reduzido evita stun-immunity; o formato inteiro
  subtrativo (era multiplicativo float) elimina o platô em que mutações pequenas
  sumiam após `round()`.

## Tabela de hiperparâmetros

| Parâmetro | Valor | Efeito |
|---|---|---|
| `POPULATION_SIZE` | 300 | tamanho da população |
| `ELITE_SIZE` | 30 | 10% × POPULATION_SIZE — preservados por elitismo |
| `MAX_GENERATIONS` | 150 | limite de gerações |
| `STAGNATION_LIMIT` | 30 | gerações sem melhoria > 0.001 antes de parar |
| `MATCHUP_CONVERGENCE_THRESHOLD` | 0.10 | desvio máximo de WR por matchup p/ convergência |
| `TOURNAMENT_SIZE` | 3 | candidatos por torneio (AG escalar) |
| `MUTATION_RATE` | 0.05 | probabilidade de mutação por gene |
| `ATTRIBUTE_MUTATION_SIGMA` | 0.10 | sigma como fração do range (atributos) |
| `WEIGHT_MUTATION_SIGMA` | 0.025 | sigma como fração do range (pesos) — inércia |
| `SIMS_PER_MATCHUP` | 150 | simulações por matchup (~4% std binomial @ 50% WR) |
| `SIMS_CONVERGENCE_CHECK` | 200 | sims extras para confirmar convergência |
| `LAMBDA_DRIFT` | 1.0 | peso da drift_penalty (só AG escalar) — igual ao dominance; trade-off central |
| `LAMBDA_DOMINANCE` | 1.0 | peso da dominance_penalty (só AG escalar) |
| `MATCHUP_THRESHOLD` | 0.10 | teto da banda de decisividade (vencedor fecha ~20% HP — acima = blowout) |
| `MATCHUP_FLOOR` | 0.05 | piso da banda de decisividade (vencedor fecha ~10% HP — abaixo = fino demais) |
| `DOMINANCE_WR_WEIGHT` | 1.0 | peso do termo primário (WR) do dominance_penalty — `\|WR−0.5\|/0.5` contínuo |
| `DOMINANCE_DECIS_WEIGHT` | 0.5 | peso do termo secundário (decisividade) do dominance_penalty — guarda contra blowout-coinflip |
| `HESITATION_RATE` | 0.10 | prob./tick de hesitar (sortear ação ponderada num ramo determinístico). **Provisório — calibrar** |
| `N_WORKERS` | None | núcleos para avaliação paralela (None = todos; 1 = serial) |
| `FIELD_SIZE` | 100 | tamanho do campo |
| `INITIAL_DISTANCE` | 50 | distância inicial entre lutadores |
| `WALL_CORNER_THRESHOLD` | 10 | distância da parede para considerar encurralado |
| `ACTION_PERSISTENCE_SUBTICKS` | 10 | sub-ticks que uma ação soft-policy é mantida |
| `TICK_SCALE` | 5 | resolução sub-tick de cooldown/stun/movimento |
| `STUN_CAP_MULTIPLIER` | 0.6 | cap de stun = mult × cooldown do atacante (< 1.0 quebra perma-lock) |
| `MAX_TICKS` | 2500 | `500 × TICK_SCALE` — duração máxima de uma luta |
| `DEFEND_DAMAGE_REDUCTION` | 0.4 | multiplicador no dano ao defender (40% recebido) |
| `NSGA2_POP_SIZE` | 300 | alias de POPULATION_SIZE |
| `NSGA2_GENERATIONS` | 150 | alias de MAX_GENERATIONS |
| `NSGA2_OBJECTIVES` | (dominance, drift) | objetivos do NSGA-II |
| `HYPERVOLUME_REFERENCE` | (1.5, 1.0) | ponto de referência do hipervolume (piores valores de dominance/drift) |
| `MULTI_RUN_SEED_START` | 42 | primeira semente da agregação `multi_run` |
| `MULTI_RUN_N_SEEDS` | 10 | nº de execuções independentes a agregar — aumentar para escalar |
| `MULTI_RUN_VALIDATION_SEED` | 9999 | semente de validação (reavaliação independente do treino, comum a todas as execuções) |
| `MULTI_RUN_SIMS` | 200 | sims/matchup na reavaliação independente (= `SIMS_CONVERGENCE_CHECK`) |
| `EXTERNAL_VALIDATION_SEED_START` | 10000 | primeira semente de avaliação da validação externa (item 3.2) |
| `EXTERNAL_VALIDATION_N_SEEDS` | 10 | nº de condições de avaliação independentes |
| `EXTERNAL_VALIDATION_SIMS` | 500 | sims/matchup por condição (> treino, p/ CI apertado) |

Os termos de fitness são detalhados em
[05-genetic-algorithm.md](05-genetic-algorithm.md); as mecânicas de combate em
[04-combat-model.md](04-combat-model.md).
