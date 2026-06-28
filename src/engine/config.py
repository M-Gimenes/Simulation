"""
Hiperparâmetros do AG e da simulação de combate — single source.
Tabela comentada completa e notas de calibração em docs/reference/07-configuration.md.
"""

# ── AG: população e parada ───────────────────────────────────────────────────

POPULATION_SIZE = 300
ELITE_SIZE = int(POPULATION_SIZE * 0.1)   # 10% preservados por elitismo a cada geração
MAX_GENERATIONS = 150
STAGNATION_LIMIT = 30                      # gerações sem melhoria > 0.001 antes de parar
# Convergência do AG (C2) = balanço global (abaixo) + ausência de hard-counter
# (MATCHUP_WR_CAP, na seção de fitness).
GLOBAL_CONVERGENCE_THRESHOLD = 0.10        # |WR global − 0.5| máx por personagem (ninguém domina o roster)

# ── AG: operadores ───────────────────────────────────────────────────────────

TOURNAMENT_SIZE = 3              # candidatos por seleção por torneio
MUTATION_RATE = 0.05            # probabilidade de mutação por gene
ATTRIBUTE_MUTATION_SIGMA = 0.1   # sigma da mutação, como fração do range do atributo
WEIGHT_MUTATION_SIGMA = 0.025    # idem para os pesos (menor = mais inércia)

# ── Fitness: simulações ──────────────────────────────────────────────────────

SIMS_PER_MATCHUP = 150         # simulações por matchup no round-robin
SIMS_CONVERGENCE_CHECK = 200   # simulações extras para confirmar convergência

# ── Fitness: pesos do AG escalar ─────────────────────────────────────────────
# fitness = -(LAMBDA_DRIFT·drift_penalty + LAMBDA_DOMINANCE·dominance_penalty).

LAMBDA_DRIFT = 1.0       # peso do desvio arquetípico (drift_penalty)
LAMBDA_DOMINANCE = 1.0   # peso do desbalanço de matchups (dominance_penalty)

# ── Fitness: dominância ──────────────────────────────────────────────────────
# dominance_penalty = GLOBAL·global + CAP·cap + DECIS·decis (máx 2.0). 
#   global → |WR_global − 0.5| por personagem.
#   cap    → limitar dominância de confrontos.
#   decis  → decisividade por luta fora da banda saudável.

DOMINANCE_GLOBAL_WEIGHT = 1.0
DOMINANCE_CAP_WEIGHT = 0.5
DOMINANCE_DECIS_WEIGHT = 0.5

# Meia-banda do hard-counter: (|X - 0.5|) < WR < (|X + 0.5|)
MATCHUP_WR_CAP = 0.15

# Banda de decisividade, em margem |score − 0.5| 

MATCHUP_FLOOR = 0.10       # piso: abaixo é quase-empate (vencedor fecha ~20% HP)
MATCHUP_THRESHOLD = 0.20   # teto: acima é blowout (vencedor fecha ~40% HP)

# ── Paralelismo ──────────────────────────────────────────────────────────────

N_WORKERS = None   # None = todos os núcleos da CPU; 1 = avaliação serial

# ── Simulação de combate ─────────────────────────────────────────────────────

FIELD_SIZE = 100                  # tamanho do campo (unidades)
INITIAL_DISTANCE = 50             # distância inicial entre lutadores
TICK_SCALE = 5                    # resolução sub-tick de cooldown/stun/movimento (mais granularidade = menos platôs no AG)
MAX_TICKS = 500 * TICK_SCALE      # duração máxima de uma luta
DEFEND_DAMAGE_REDUCTION = 1 - 0.4     # multiplicador no dano recebido ao defender
ACTION_PERSISTENCE_SUBTICKS = 10  # sub-ticks que uma intenção sorteada é mantida (inércia/momentum)

# ── Bounds e nomes dos genes ─────────────────────────────────────────────────
# 7 atributos + 3 pesos por personagem; todos contínuos. Semântica e calibração

ATTRIBUTE_BOUNDS = [
    (250.0, 450.0),  # hp
    (15.0, 30.0),    # damage (flat; só reduzido por DEFEND)
    (1.0, 5.0),      # attack_cooldown (ticks entre ataques; menor = mais rápido)
    (5.0, 20.0),     # range (< INITIAL_DISTANCE)
    (1.0, 5.0),      # speed
    (0.0, 0.6),      # stun — fração do cooldown do atacante; bound < 1 garante stun < cooldown
    (0.0, 3.0),      # knockback
]

WEIGHT_BOUNDS = [
    (0.0, 1.0),  # w_retreat
    (0.0, 1.0),  # w_defend
    (0.0, 1.0),  # w_aggressiveness
]

ATTRIBUTE_NAMES = ["hp", "damage", "attack_cooldown", "range", "speed", "stun", "knockback"]
WEIGHT_NAMES = ["w_retreat", "w_defend", "w_aggressiveness"]

# ── NSGA-II ──────────────────────────────────────────────────────────────────

NSGA2_POP_SIZE = POPULATION_SIZE
NSGA2_GENERATIONS = MAX_GENERATIONS
NSGA2_OBJECTIVES = ["dominance_penalty", "drift_penalty"]  # objetivos Pareto, sem ponderação
HYPERVOLUME_REFERENCE = (2.0, 1.0)  # piores valores (dominance ≤ 2.0, drift ≤ 1.0); fixo p/ HV comparável entre execuções

# ── Multi-run: N execuções independentes + estatística agregada ──────────────

MULTI_RUN_SEED_START = 42         # primeira semente; execuções usam 42, 43, ..., 42+N−1
MULTI_RUN_N_SEEDS = 10           # nº de execuções independentes a agregar
MULTI_RUN_VALIDATION_SEED = 9999  # seed comum de reavaliação (CRN): desacopla a métrica da seed de treino
MULTI_RUN_SIMS = SIMS_CONVERGENCE_CHECK  # sims/matchup na reavaliação independente

# ── Validação externa ao fitness (estilo Ludi — Browne & Maire 2010) ─────────

EXTERNAL_VALIDATION_SEED_START = 10000  # primeira semente de avaliação (independente do treino)
EXTERNAL_VALIDATION_N_SEEDS = 10        # nº de condições de avaliação independentes
EXTERNAL_VALIDATION_SIMS = 500          # sims/matchup por condição (> treino, p/ CI apertado)
