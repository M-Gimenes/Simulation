# 07 — Configuração

Todos os hiperparâmetros em `src/engine/config.py`. Single source — nada de
constantes espalhadas.

## Bounds dos genes (`ATTRIBUTE_BOUNDS`, `WEIGHT_BOUNDS`)

São **8 atributos** + 3 pesos = 11 genes por personagem (`defense` e `recovery`
foram removidos do modelo — ver [04-combat-model.md](04-combat-model.md)).

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
| w_retreat / w_defend / w_aggressiveness | 0 | 1 | pesos do sorteio de intenção |

Todos os genes são contínuos — não há mais atributo inteiro (`recovery`, o único,
foi removido).

### Calibração (por que estes bounds)

> Os bounds e os canônicos foram re-ajustados ao novo modelo de combate e
> permanecem **provisórios — a calibrar**.

- **Stun ∈ [0, 0.6] (fração, timer contínuo):** o stun é uma fração do cooldown do
  próprio atacante, aplicada como `stun × attack_cooldown × TICK_SCALE` em ponto
  flutuante. Como `0.6 < 1`, o stun aplicado é sempre menor que o cooldown — o
  defensor sempre tem uma janela livre, o que **substitui** o antigo
  `STUN_CAP_MULTIPLIER` (a invariante é garantida pelo bound do gene e coberta por
  teste em `test_combat`). O timer era arredondado para inteiro até 2026-09-10, o que
  deixava o gene com **4 níveis efetivos** para um atacante de `cooldown = 1`
  (`round(cd × TICK_SCALE) = 5` sub-ticks, `round(stun × 5) ∈ {0,1,2,3}`) — na prática
  um gene categórico. Com o timer contínuo a amplitude do gene a ±1σ de mutação subiu
  de 6,8% para 17,4%.
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
| `ELITE_RATE` | 0.10 | **fração** da população preservada por elitismo — é o que o laço lê, via `operators.elite_count(pop_size)`. **Testado** (2026-09-18: 0 · 0,05 · 0,20 · 0,30): nenhum braço o supera |
| `ELITE_SIZE` | 30 | derivação de `ELITE_RATE` no orçamento default; referência, não a fonte |
| `MAX_GENERATIONS` | 150 | orçamento de gerações (o AG roda todas — não é limite de parada) |
| `STAGNATION_LIMIT` | 30 | gerações sem melhoria > 0.001 até **registrar** `stagnated_at` (evento, não parada) |
| `GLOBAL_CONVERGENCE_THRESHOLD` | 0.10 | desvio máximo da WR **global** por personagem p/ convergência (ninguém domina o roster); também a banda "boneco equilibrado" no reporting |
| `TOURNAMENT_SIZE` | 3 | candidatos por torneio (AG escalar). **Testado** (2026-09-18: 2 · 5 · 7): nenhum braço o supera |
| `MUTATION_RATE` | 0.05 | probabilidade de mutação por gene |
| `ATTRIBUTE_MUTATION_SIGMA` | 0.10 | sigma como fração do range (atributos) |
| `WEIGHT_MUTATION_SIGMA` | 0.025 | sigma como fração do range (pesos) — inércia |
| `SIMS_PER_MATCHUP` | 150 | simulações por matchup (~4% std binomial @ 50% WR) |
| `SIMS_CONVERGENCE_CHECK` | 200 | sims extras para confirmar convergência |
| `GENERATION_SEED_STRIDE` | 1000 | passo entre os streams de avaliação de gerações consecutivas: `fitness.generation_seed(base, g)` = `base × STRIDE + g`. O CRN vale **dentro** de uma geração; entre gerações o stream muda, para que a busca não possa se ajustar a uma realização do RNG (medido: razão dentro/fora do laço 4,14 → 2,20, 5/5 sementes). Com geração < STRIDE, duas sementes de treino nunca compartilham stream |
| `CONVERGENCE_SEED_OFFSET` | 100000 | deslocamento do stream de RNG da **confirmação** de convergência. O laço usa CRN (correto para seleção); reavaliar no mesmo stream não confirma nada — mede a mesma realização do RNG com mais amostras. Somado à semente de treino, dá a cada execução um hold-out próprio. Não colide com treino 42+, `MULTI_RUN_VALIDATION_SEED` 9999 nem `EXTERNAL_VALIDATION_SEED_START` 10000+ |
| `LAMBDA_DRIFT` | 1.0 | peso da drift_penalty (só AG escalar) — igual ao dominance; trade-off central. **Joelho medido da curva** (sweep de 2026-09-17): `dominance` fica plano em ~0,048 até aqui e explora para 0,19 em λ=2 e 0,34 em λ=4. Só a RAZÃO entre os dois λ importa — a seleção é ordinal |
| `DRIFT_DEFINING_WEIGHT` | 3.0 | peso dos `defining_genes` de cada arquétipo no drift (demais genes = 1.0). Mede identidade **estrutural**: mover o alcance do Zoner custa mais que mover o stun dele. `1.0` volta ao drift uniforme. Calibrado medindo a concordância com o validador — ver [05-genetic-algorithm.md](05-genetic-algorithm.md) |
| `LAMBDA_DOMINANCE` | 1.0 | peso da dominance_penalty (só AG escalar) |
| `MATCHUP_THRESHOLD` | 0.20 | teto da banda de decisividade (vencedor fecha ~40% HP — acima = blowout) |
| `MATCHUP_FLOOR` | 0.02 | piso da banda de decisividade — **guarda de degenerescência**, não banda de qualidade. Não morde em operação normal (0/10 pares). Era 0.10, que penalizava 5/10 pares e decidia a comparação AG × NSGA-II. Faixas medidas: degenerado `≤ 0,008`, espelho puro `0,020–0,033`, pares reais `≥ 0,045` |
| `DOMINANCE_GLOBAL_WEIGHT` | 1.0 | peso do termo **primário** (balanço global por personagem) do dominance_penalty |
| `DOMINANCE_CAP_WEIGHT` | 0.5 | peso do teto de hard-counter (excesso de `\|WR−0.5\|` acima de `MATCHUP_WR_CAP`). **Sweep 2026-09-17:** com cap e decis em 0 o AG chega ao melhor `global_term` de todos (0,0170) e a **10/10 counters duros** — os secundários são carga estrutural. Subir para 2,0 melhora counters, mas a n = 5 não se distingue de ruído |
| `DOMINANCE_DECIS_WEIGHT` | 0.5 | peso do termo de decisividade — o teto guarda contra blowout-coinflip; o piso, contra degenerescência. **Fechado 2026-09-16:** é guarda, e guarda ativa — dispara no canônico (0.2834) e nos aleatórios, zera nos evoluídos. **Sweep 2026-09-17:** desligá-lo sozinho triplica os hard-counters (0,6 → 3,2) e piora o `cap_term` (0,0063 → 0,1440) — ler 0 é ele funcionando |
| `MATCHUP_WR_CAP` | 0.15 | meia-banda do hard-counter: par é counter duro se `\|WR−0.5\| > 0.15` (fora de [0.35, 0.65]). **Fechado 2026-09-16:** ponto médio entre 6-4 (0.10, vantagem) e 7-3 (0.20, counter) na grade da FGC — justificativa e tabela de ruído no comentário do `config.py` |
| `N_WORKERS` | 8 | processos na avaliação paralela (None = todos os núcleos; 1 = serial). **Não é só gosto:** o pool é recriado a cada geração, então o custo de spawn escala com o nº de workers — medido nesta máquina, 8 workers é ~2,2× mais rápido que 28, e 28 estourava o limite de commit do Windows. Não afeta o resultado (CRN propagado aos workers) |
| `FIELD_SIZE` | 100 | tamanho do campo |
| `INITIAL_DISTANCE` | 50 | distância inicial entre lutadores (> todos os `range`, então a luta começa em impasse) |
| `ACTION_PERSISTENCE_SUBTICKS` | 5 | sub-ticks que uma intenção sorteada é mantida (zerado no impasse e ao ser stunado). **Fechado 2026-09-16:** 5 = 1 tick = cooldown mínimo, então GUARDA custa **uma** janela de ataque e não duas; a 10 a razão sinal/ruído era pior em **8/8** genes, com `speed` e `stun` abaixo do piso |
| `TICK_SCALE` | 5 | resolução sub-tick de cooldown/stun/movimento |
| `MAX_TICKS` | 2500 | `500 × TICK_SCALE` — duração máxima de uma luta |
| `DEFEND_DAMAGE_REDUCTION` | 0.6 (= 1 − 0.4) | multiplicador no dano ao defender (recebe 60% = **40% de redução**) |
| `NSGA2_POP_SIZE` | 300 | alias de POPULATION_SIZE |
| `NSGA2_GENERATIONS` | 150 | alias de MAX_GENERATIONS |
| `NSGA2_OBJECTIVES` | (dominance, drift) | objetivos do NSGA-II |
| `HYPERVOLUME_REFERENCE` | (2.0, 1.0) | ponto de referência do hipervolume (piores valores de dominance/drift; dominance vai a 2.0 sob C2) |
| `MULTI_RUN_SEED_START` | 42 | primeira semente da agregação `multi_run` |
| `MULTI_RUN_N_SEEDS` | 10 | nº de execuções independentes a agregar. **O protocolo é 20** (poder medido — n=10 dá 44,4%, n=20 dá 85,9% para Â₁₂ = 0,80 com a família de Holm de 3), e a bateria de 2026-09-18 rodou com `--n-seeds 20`; as sementes 42..51 reproduziram bit a bit as da bateria de n = 10. O default segue 10 — **pendência**: sem o flag, o `multi_run` sobrescreve a bateria com n = 10 (ver [10-known-issues](10-known-issues.md) §1.2) |
| `MULTI_RUN_VALIDATION_SEED` | 9999 | semente de validação (reavaliação independente do treino, comum a todas as execuções) |
| `MULTI_RUN_SIMS` | 200 | sims/matchup na reavaliação independente (= `SIMS_CONVERGENCE_CHECK`) |
| `EXTERNAL_VALIDATION_SEED_START` | 10000 | primeira semente de avaliação da validação externa (item 3.2) |
| `EXTERNAL_VALIDATION_N_SEEDS` | 10 | nº de condições de avaliação independentes |
| `EXTERNAL_VALIDATION_SIMS` | 500 | sims/matchup por condição (> treino, p/ CI apertado) |

Os termos de fitness são detalhados em
[05-genetic-algorithm.md](05-genetic-algorithm.md); as mecânicas de combate em
[04-combat-model.md](04-combat-model.md).
