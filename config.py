"""
Configurações globais do sistema.
Todos os hiperparâmetros do AG e da simulação de combate estão aqui.
"""

# ── AG — População e critérios de parada ────────────────────────────────────

POPULATION_SIZE       = 100
ELITE_SIZE            = 10     # indivíduos preservados por elitismo por geração
MAX_GENERATIONS       = 100     # limite de gerações
STAGNATION_LIMIT      = 50     # gerações sem melhoria > 0.001 antes de parar
CONVERGENCE_THRESHOLD = 0.02   # desvio máximo de balance_error para convergência (≈48–52%)
MATCHUP_CONVERGENCE_THRESHOLD = 0.10  # desvio máximo de WR por matchup (≈30–70%)

# ── AG — Operadores ──────────────────────────────────────────────────────────

TOURNAMENT_SIZE          = 3    # candidatos por seleção por torneio
MUTATION_RATE            = 0.1  # probabilidade de mutação por gene
ATTRIBUTE_MUTATION_SIGMA = 0.1 # sigma como fração do range do atributo — exploração ampla
WEIGHT_MUTATION_SIGMA    = 0.02 # sigma como fração do range do peso — inércia evolutiva

# ── Função de fitness ────────────────────────────────────────────────────────

SIMS_PER_MATCHUP       = 30    # simulações por matchup no round-robin
SIMS_CONVERGENCE_CHECK = 50    # simulações extras para confirmar convergência

LAMBDA                 = 0.2   # peso da penalidade de especialização (attribute_cost)
LAMBDA_DRIFT           = 0.0   # peso da penalidade de desvio arquetípico (drift_penalty)
                                # 0.0 = evolução livre  |  alto = âncora ao canônico
                                # trade-off central do TCC: equilíbrio vs preservação
LAMBDA_MATCHUP         = 1     # peso da penalidade do pior matchup direto

MATCHUP_THRESHOLD      = 0.10  # excesso acima de 50% que inicia penalização (60% WR = limiar)

BALANCE_MODE = "aggregate"     # como calcular balance_error:
                                # "matchup"   → mean(|wr_ij - 0.5|) sobre os 10 pares
                                # "aggregate" → mean(|wr_i  - 0.5|) sobre os 5 personagens

# ── Paralelismo ──────────────────────────────────────────────────────────────

N_WORKERS = None  # None = todos os núcleos da CPU; 1 = desativa paralelismo

# ── Simulação — Campo ────────────────────────────────────────────────────────

FIELD_SIZE            = 100  # tamanho do campo em unidades
INITIAL_DISTANCE      = 50   # distância inicial entre os lutadores
WALL_CORNER_THRESHOLD = 10   # distância da parede para considerar o lutador encurralado

# ── Simulação — Estocasticidade ──────────────────────────────────────────────

DAMAGE_VARIANCE = 0.20  # ±20% por hit — variância de execução no dano
ACTION_EPSILON  = 0.20  # prob. de ação aleatória por tick — erros de decisão

# ── Simulação — Decisão ──────────────────────────────────────────────────────

MAX_TICKS           = 500  # duração máxima de uma partida (ticks)
RETREAT_ZONE_FACTOR = 2.0  # zona de ameaça proativa = fator × range do inimigo

# ── Bounds dos genes ─────────────────────────────────────────────────────────

ATTRIBUTE_BOUNDS = [
    (300.0, 500.0),  # hp
    (10.0,  20.0),   # damage
    (1.0,   5.0),    # attack_cooldown
    (5.0,   20.0),   # range
    (1.0,   5.0),    # speed
    (0.0,   0.5),    # defense
    (0.0,   5.0),    # stun
    (0.0,   5.0),    # knockback
    (0.0,   0.5),    # recovery
]

WEIGHT_BOUNDS = [
    (0.0, 1.0),  # w_retreat
    (0.0, 1.0),  # w_defend
    (0.0, 1.0),  # w_aggressiveness
]

ATTRIBUTE_NAMES = ["hp", "damage", "attack_cooldown", "range", "speed", "defense", "stun", "knockback", "recovery"]
WEIGHT_NAMES    = ["w_retreat", "w_defend", "w_aggressiveness"]

# ── NSGA-II ─────────────────────────────────────────────────────────────────

# Aliases — permitem tunar o NSGA-II sem alterar os parâmetros do AG clássico.
NSGA2_POP_SIZE      = POPULATION_SIZE
NSGA2_GENERATIONS   = MAX_GENERATIONS
NSGA2_OBJECTIVES    = ["balance_error", "matchup_dominance_penalty", "drift_penalty"]
