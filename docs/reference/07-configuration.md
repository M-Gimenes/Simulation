# 07 — Configuração

Todos os hiperparâmetros em `src/engine/config.py`. Single source — nada de
constantes espalhadas.

## Bounds dos genes (`ATTRIBUTE_BOUNDS`, `WEIGHT_BOUNDS`)

São **8 atributos** + 3 pesos = 11 genes por personagem.

> **Fonte única:** `src/engine/config.py` → `ATTRIBUTE_BOUNDS` / `WEIGHT_BOUNDS`
> A tabela abaixo espelha o código; **em divergência, o código
> vence** — ao mudar um bound, atualize lá e só reflita aqui.

| Atributo | Mín | Máx | Semântica |
|---|---|---|---|
| HP | 250 | 450 | pontos de vida |
| Damage | 15 | 30 | dano por hit (flat; só reduzido por DEFEND) |
| Attack Cooldown | 1 | 5 | ticks entre ataques; menor = mais rápido |
| Range | 5 | 20 | alcance (todos < distância inicial 50) |
| Speed | 1 | 5 | unidades de campo por tick |
| Stun | 0 | 0.6 | **fração** do cooldown do atacante, timer contínuo (< 1 garante stun < cooldown) |
| Knockback | 0 | 3 | unidades empurradas por hit |
| Grab power | 0 | 1 | quanto o agarrão soma ao multiplicador de dano contra alvo em guarda (0,6 + grab) |
| w_retreat / w_defend / w_aggressiveness | 0 | 1 | pesos do sorteio de intenção |

Todos os genes são contínuos.

### Por que estes bounds

Bounds e canônicos estão **fechados** (declarados finais em 2026-09-16): os canônicos
são a premissa, não variável a otimizar — ver [thesis/04](../thesis/04-design-decisions.md).

- **Stun ∈ [0, 0.6] (fração, timer contínuo):** o stun é uma fração do cooldown do
  próprio atacante, aplicada como `stun × attack_cooldown × TICK_SCALE` em ponto
  flutuante. Como `0.6 < 1`, o stun aplicado é sempre menor que o cooldown — o
  defensor sempre tem uma janela livre, garantido pelo bound do gene e coberto por
  teste em `test_combat`, sem constante de teto separada. O timer é contínuo porque
  arredondá-lo deixaria o gene com 4 níveis efetivos para um atacante de `cooldown = 1`.
- **HP 250–450:** comporta os 5 canônicos (Zoner 300 … Turtle 450, no teto) com
  headroom inferior.
- **Knockback ≤ 3:** teto razoável acima do Zoner (2); evita zoning trivial por
  expulsão de range.
- **Grab power ∈ [0, 1]:** o ponto neutro 0,4 (`1 − 0,6`) anula a guarda; só o Grappler
  canônico (0,9) passa dele — ver [04-combat-model.md](04-combat-model.md#grab).
- **Sem `defense` nem `recovery`:** o dano é flat (só DEFEND e o agarrão o modificam) e
  o stun é aplicado direto.

## Tabela de hiperparâmetros

| Parâmetro | Valor | Efeito |
|---|---|---|
| `POPULATION_SIZE` | 300 | tamanho da população |
| `ELITE_RATE` | 0.10 | **fração** da população preservada por elitismo — é o que o laço lê, via `operators.elite_count(pop_size)`. Testado contra 0 · 0,05 · 0,20 · 0,30: nenhum braço o supera |
| `ELITE_SIZE` | 30 | derivação de `ELITE_RATE` no orçamento default; referência, não a fonte |
| `MAX_GENERATIONS` | 150 | orçamento de gerações (o AG roda todas — não é limite de parada) |
| `STAGNATION_LIMIT` | 30 | gerações sem melhoria > 0.001 até **registrar** `stagnated_at` (evento, não parada) |
| `GLOBAL_CONVERGENCE_THRESHOLD` | 0.10 | desvio máximo da WR **global** por personagem p/ convergência (ninguém domina o roster); também a banda "boneco equilibrado" no reporting |
| `TOURNAMENT_SIZE` | 3 | candidatos por torneio (AG escalar). Testado contra 2 · 5 · 7: nenhum braço o supera |
| `MUTATION_RATE` | 0.05 | probabilidade de mutação por gene |
| `ATTRIBUTE_MUTATION_SIGMA` | 0.10 | sigma como fração do range (atributos) |
| `WEIGHT_MUTATION_SIGMA` | 0.025 | sigma como fração do range (pesos) — inércia |
| `SIMS_PER_MATCHUP` | 150 | simulações por matchup (~4% std binomial @ 50% WR) |
| `SIMS_CONVERGENCE_CHECK` | 200 | sims extras para confirmar convergência |
| `GENERATION_SEED_STRIDE` | 1000 | passo entre os streams de avaliação de gerações consecutivas: `fitness.generation_seed(base, g)` = `base × STRIDE + g`. O CRN vale **dentro** de uma geração (uma semente por luta, `fitness.fight_seed`); entre gerações o stream muda, para que a busca não possa se ajustar a uma realização do RNG. Com geração < STRIDE, duas sementes de treino nunca compartilham stream |
| `CONVERGENCE_SEED_OFFSET` | 100000 | deslocamento do stream de RNG da **confirmação** de convergência. O laço usa CRN (correto para seleção); reavaliar no mesmo stream não confirma nada — mede a mesma realização do RNG com mais amostras. Somado à semente de treino, dá a cada execução um hold-out próprio. Não colide com treino 42+, `MULTI_RUN_VALIDATION_SEED` 9999 nem `EXTERNAL_VALIDATION_SEED_START` 10000+ |
| `LAMBDA_DRIFT` | 1.0 | peso da drift_penalty (só AG escalar) — igual ao dominance; trade-off central. **Joelho da curva** no sweep de λ: `dominance` fica plano até aqui e só então explode. Só a RAZÃO entre os dois λ importa — a seleção é ordinal |
| `DRIFT_DEFINING_WEIGHT` | 3.0 | peso dos `defining_genes` de cada arquétipo no drift (demais genes = 1.0). Mede identidade **estrutural**: mover o alcance do Zoner custa mais que mover o stun dele. `1.0` volta ao drift uniforme. Calibrado medindo a concordância com o validador — ver [thesis/04](../thesis/04-design-decisions.md) |
| `LAMBDA_DOMINANCE` | 1.0 | peso da dominance_penalty (só AG escalar) |
| `MATCHUP_THRESHOLD` | 0.20 | teto da banda de decisividade (vencedor fecha ~40% HP — acima = blowout) |
| `MATCHUP_FLOOR` | 0.02 | piso da banda de decisividade — **guarda de degenerescência**, não banda de qualidade: toda luta termina em KO, então `D` baixo é KO no fio. Fica na base da faixa dos espelhos, abaixo do que dois personagens idênticos produzem, e não morde pares de personagens distintos |
| `DOMINANCE_GLOBAL_WEIGHT` | 1.0 | peso do termo **primário** (balanço global por personagem) do dominance_penalty |
| `DOMINANCE_CAP_WEIGHT` | 0.5 | peso do teto de hard-counter (excesso de `\|WR−0.5\|` acima de `MATCHUP_WR_CAP`). O sweep dos pesos mostrou os secundários como carga estrutural: sem eles o AG entrega todos os pares como counter duro — ver [thesis/04](../thesis/04-design-decisions.md) |
| `DOMINANCE_DECIS_WEIGHT` | 0.5 | peso do termo de decisividade — o teto guarda contra blowout-coinflip; o piso, contra degenerescência. Lê 0 nos indivíduos evoluídos porque funciona: dispara no canônico e nos aleatórios, e desligá-lo multiplica os hard-counters |
| `MATCHUP_WR_CAP` | 0.15 | meia-banda do hard-counter: par é counter duro se `\|WR−0.5\| > 0.15` (fora de [0.35, 0.65]). Ponto médio entre 6-4 (0.10, vantagem) e 7-3 (0.20, counter) na grade da FGC — justificativa e tabela de ruído no comentário do `config.py` |
| `N_WORKERS` | `min(8, núcleos)` | processos do pool persistente (1 = serial). Teto de 8: com todos os núcleos os processos carregando llvmlite estouravam o limite de commit do Windows, e acima de 8 o ganho some no ruído (8w 1,04 s · 12w ~1,0 s · 16w ~0,9 s por geração de 300). Não afeta o resultado (o estado do pai viaja com cada tarefa) e fica fora do carimbo |
| `FIELD_SIZE` | 100 | tamanho do campo |
| `INITIAL_DISTANCE` | 50 | distância inicial entre lutadores (> todos os `range`, então a luta começa em impasse) |
| `ACTION_PERSISTENCE_SUBTICKS` | 5 | sub-ticks que uma intenção sorteada é mantida (zerado no impasse e ao ser stunado). 5 = 1 tick = cooldown mínimo, então GUARDA custa exatamente **uma** janela de ataque — ver [thesis/04](../thesis/04-design-decisions.md) |
| `TICK_SCALE` | 5 | resolução sub-tick de cooldown/stun/movimento |
| `MAX_TICKS` | 2500 | `500 × TICK_SCALE` — duração máxima de uma luta |
| `DEFEND_DAMAGE_REDUCTION` | 0.6 (= 1 − 0.4) | multiplicador no dano ao defender (recebe 60% = **40% de redução**) |
| `NSGA2_POP_SIZE` | 300 | alias de POPULATION_SIZE |
| `NSGA2_GENERATIONS` | 150 | alias de MAX_GENERATIONS |
| `NSGA2_OBJECTIVES` | (dominance, drift) | objetivos do NSGA-II |
| `HYPERVOLUME_REFERENCE` | (2.0, 1.0) | ponto de referência do hipervolume (piores valores de dominance/drift; dominance vai a 2.0 sob C2) |
| `MULTI_RUN_SEED_START` | 42 | primeira semente da agregação `multi_run` |
| `MULTI_RUN_N_SEEDS` | 20 | nº de execuções independentes a agregar — o menor n com poder ≥ 80% (n=10 dá 44,4%, n=20 dá 85,9% para Â₁₂ = 0,80 com a família de Holm de 3). **Fora do carimbo de proveniência**, como `N_WORKERS`: só define o tamanho da amostra, que o artefato do `multi_run` grava no corpo |
| `MULTI_RUN_VALIDATION_SEED` | 9999 | semente de validação (reavaliação independente do treino, comum a todas as execuções) |
| `MULTI_RUN_SIMS` | 200 | sims/matchup na reavaliação independente (= `SIMS_CONVERGENCE_CHECK`) |
| `EXTERNAL_VALIDATION_SEED_START` | 10000 | primeira semente de avaliação da validação externa (item 3.2) |
| `EXTERNAL_VALIDATION_N_SEEDS` | 10 | nº de condições de avaliação independentes |
| `EXTERNAL_VALIDATION_SIMS` | 500 | sims/matchup por condição (> treino, p/ CI apertado) |

Os termos de fitness são detalhados em
[05-genetic-algorithm.md](05-genetic-algorithm.md); as mecânicas de combate em
[04-combat-model.md](04-combat-model.md).
