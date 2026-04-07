"""
Configurações globais do sistema.
Hiperparâmetros do AG e definições dos arquétipos.
"""

# ── Hiperparâmetros do AG ────────────────────────────────────────────────────

POPULATION_SIZE       = 100
ELITE_SIZE            = 10      # 10% de 100
MAX_GENERATIONS       = 20
CONVERGENCE_THRESHOLD = 0.02    # winrate entre 48% e 52%
STAGNATION_LIMIT      = 50      # gerações sem melhoria > 0.001
MAX_TICKS             = 500     # duração máxima de uma partida (ticks)
LAMBDA                = 0.3     # peso da penalidade de especialização no fitness
LAMBDA_DRIFT          = 0.0     # peso da penalidade de desvio arquetípico no fitness
                                # 0.0 = evolução completamente livre (sem âncora ao canônico)
                                # maior = mais pressão para preservar identidade do arquétipo
                                # trade-off central do TCC: equilíbrio vs preservação
MUTATION_RATE         = 0.1
TOURNAMENT_SIZE       = 3
SIMS_PER_MATCHUP      = 30      # simulações por matchup no round-robin (estabiliza winrate)
SIMS_CONVERGENCE_CHECK = 50     # sims extras usadas só para confirmar convergência

# ── Bounds dos atributos (escala 0–100) ─────────────────────────────────────

ATTRIBUTE_BOUNDS = [
    (0.0, 1000.0),  # hp      — escala maior: HP >> dano, combates decididos por atrito
    (0.0, 100.0),   # damage
    (0.0, 100.0),   # cooldown — alto = ataca rápido (invertido na simulação: wait = (100-cd)/10)
    (0.0, 100.0),   # range
    (0.0, 100.0),   # speed
    (0.0, 100.0),   # defense
    (0.0, 100.0),   # stun
    (0.0, 100.0),   # knockback
    (0.0, 100.0),   # recovery
]

WEIGHT_BOUNDS = [
    (0.0, 1.0),     # w_attack
    (0.0, 1.0),     # w_advance
    (0.0, 1.0),     # w_retreat
    (0.0, 1.0),     # w_defend
    (0.0, 1.0),     # w_aggressiveness
]

# Sigma de mutação como fração do range
ATTRIBUTE_MUTATION_SIGMA = 0.05   # 5% do range → strength maior
WEIGHT_MUTATION_SIGMA    = 0.02   # 2% do range → inércia evolutiva

# Temperatura do softmax de decisão de ação
# < 1.0 → distribuição mais concentrada (comportamento reflete melhor os pesos w_*)
# = 1.0 → softmax padrão (scores normalizados ~0.25 resultam em distribuição quase uniforme)
# Valor recomendado: 0.1 garante que o melhor score domina sem tornar comportamento 100% determinístico
SCORE_TEMPERATURE = 0.1

# ── Nomes dos genes (para logging e visualizações) ──────────────────────────

ATTRIBUTE_NAMES = [
    "hp", "damage", "cooldown", "range",
    "speed", "defense", "stun", "knockback", "recovery",
]

WEIGHT_NAMES = [
    "w_attack", "w_advance", "w_retreat", "w_defend", "w_aggressiveness",
]

# ── Campo de batalha ─────────────────────────────────────────────────────────

FIELD_SIZE       = 100   # unidades
INITIAL_DISTANCE = 50
MIN_DISTANCE     = 0
MAX_DISTANCE     = 100
