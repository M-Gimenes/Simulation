# 07 — Configuração

Todos os hiperparâmetros em `src/engine/config.py`. Single source — nada de
constantes espalhadas.

## Bounds dos genes (`ATTRIBUTE_BOUNDS`, `WEIGHT_BOUNDS`)

São **7 atributos** + 3 pesos = 10 genes por personagem (`defense` e `recovery`
foram removidos do modelo — ver [04-combat-model.md](04-combat-model.md)).

| Atributo | Mín | Máx | Semântica |
|---|---|---|---|
| HP | 250 | 450 | pontos de vida |
| Damage | 10 | 20 | dano por hit (flat; só reduzido por DEFEND) |
| Attack Cooldown | 1 | 5 | ticks entre ataques; menor = mais rápido |
| Range | 5 | 20 | alcance (todos < distância inicial 50) |
| Speed | 1 | 5 | unidades de campo por tick |
| Stun | 0 | 0.6 | **fração** do cooldown do atacante (< 1 garante stun < cooldown) |
| Knockback | 0 | 3 | unidades empurradas por hit |
| w_retreat / w_defend / w_aggressiveness | 0 | 1 | pesos do sorteio de intenção |

Todos os genes são contínuos — não há mais atributo inteiro (`recovery`, o único,
foi removido).

### Calibração (por que estes bounds)

> Os bounds e os canônicos foram re-ajustados ao novo modelo de combate e
> permanecem **provisórios — a calibrar**.

- **Stun ∈ [0, 0.6] (fração):** o stun passou de valor absoluto a fração do
  cooldown do próprio atacante. Como `0.6 < 1`, o stun aplicado é sempre menor que
  o cooldown — o defensor sempre tem uma janela livre, o que **substitui** o antigo
  `STUN_CAP_MULTIPLIER` (a invariante agora é garantida pelo bound do gene). A
  garantia depende do acoplamento `stun_bound × TICK_SCALE`: com `cd_min = 1` e
  `TICK_SCALE = 5`, `round(0.6 × 5) = 3 < 5`. Se `TICK_SCALE` caísse para 1,
  `round(0.6 × 1) = 1` empataria com o cooldown mínimo.
- **HP 250–450:** comporta os 5 canônicos (Zoner 300 … Turtle 450, no teto) com
  headroom inferior.
- **Knockback ≤ 3:** teto razoável acima do Zoner (2); evita zoning trivial por
  expulsão de range.
- **`defense` e `recovery` removidos:** o dano é flat (só DEFEND reduz) e o stun
  bruto é aplicado direto; não há mais redução passiva de dano nem resistência a
  stun como genes. Trajetória em [tcc/04-caminhos-e-decisoes.md](../tcc/04-caminhos-e-decisoes.md).

## Tabela de hiperparâmetros

| Parâmetro | Valor | Efeito |
|---|---|---|
| `POPULATION_SIZE` | 300 | tamanho da população |
| `ELITE_SIZE` | 30 | 10% × POPULATION_SIZE — preservados por elitismo |
| `MAX_GENERATIONS` | 150 | limite de gerações |
| `STAGNATION_LIMIT` | 30 | gerações sem melhoria > 0.001 antes de parar |
| `GLOBAL_CONVERGENCE_THRESHOLD` | 0.10 | desvio máximo da WR **global** por personagem p/ convergência (ninguém domina o roster); também a banda "boneco equilibrado" no reporting |
| `TOURNAMENT_SIZE` | 3 | candidatos por torneio (AG escalar) |
| `MUTATION_RATE` | 0.05 | probabilidade de mutação por gene |
| `ATTRIBUTE_MUTATION_SIGMA` | 0.10 | sigma como fração do range (atributos) |
| `WEIGHT_MUTATION_SIGMA` | 0.025 | sigma como fração do range (pesos) — inércia |
| `SIMS_PER_MATCHUP` | 150 | simulações por matchup (~4% std binomial @ 50% WR) |
| `SIMS_CONVERGENCE_CHECK` | 200 | sims extras para confirmar convergência |
| `LAMBDA_DRIFT` | 1.0 | peso da drift_penalty (só AG escalar) — igual ao dominance; trade-off central |
| `LAMBDA_DOMINANCE` | 1.0 | peso da dominance_penalty (só AG escalar) |
| `MATCHUP_THRESHOLD` | 0.20 | teto da banda de decisividade (vencedor fecha ~40% HP — acima = blowout) |
| `MATCHUP_FLOOR` | 0.10 | piso da banda de decisividade (vencedor fecha ~20% HP — abaixo = fino demais) |
| `DOMINANCE_GLOBAL_WEIGHT` | 1.0 | peso do termo **primário** (balanço global por personagem) do dominance_penalty |
| `DOMINANCE_CAP_WEIGHT` | 0.5 | peso do teto de hard-counter (excesso de `\|WR−0.5\|` acima de `MATCHUP_WR_CAP`) |
| `DOMINANCE_DECIS_WEIGHT` | 0.5 | peso do termo de decisividade — guarda contra blowout-coinflip |
| `MATCHUP_WR_CAP` | 0.20 | meia-banda do hard-counter: par é counter duro se `\|WR−0.5\| > 0.20` (fora de [0.30, 0.70]). **Provisório — calibrar** |
| `N_WORKERS` | None | núcleos para avaliação paralela (None = todos; 1 = serial) |
| `FIELD_SIZE` | 100 | tamanho do campo |
| `INITIAL_DISTANCE` | 50 | distância inicial entre lutadores |
| `ACTION_PERSISTENCE_SUBTICKS` | 10 | sub-ticks que uma intenção sorteada é mantida |
| `TICK_SCALE` | 5 | resolução sub-tick de cooldown/stun/movimento |
| `MAX_TICKS` | 2500 | `500 × TICK_SCALE` — duração máxima de uma luta |
| `DEFEND_DAMAGE_REDUCTION` | 0.4 | multiplicador no dano ao defender (40% recebido) |
| `NSGA2_POP_SIZE` | 300 | alias de POPULATION_SIZE |
| `NSGA2_GENERATIONS` | 150 | alias de MAX_GENERATIONS |
| `NSGA2_OBJECTIVES` | (dominance, drift) | objetivos do NSGA-II |
| `HYPERVOLUME_REFERENCE` | (2.0, 1.0) | ponto de referência do hipervolume (piores valores de dominance/drift; dominance vai a 2.0 sob C2) |
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
