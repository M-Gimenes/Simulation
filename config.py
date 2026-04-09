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

# ── Paralelismo ──────────────────────────────────────────────────────────────

N_WORKERS = None  # None = todos os núcleos da CPU; 1 = desativa paralelismo

# ── Bounds dos atributos (escala 0–100) ─────────────────────────────────────

ATTRIBUTE_BOUNDS = [
    (300.0, 500.0),  # hp            — pontos de vida
    (10.0,  20.0),   # damage        — dano por hit (unidades de HP)
    (1.0,   10.0),   # attack_speed  — ataques por 10 ticks; wait = round(10 / attack_speed)
    (5.0,   20.0),   # range         — alcance em unidades de campo
    (1.0,    5.0),   # speed         — unidades de campo por tick
    (0.0,    0.5),   # defense       — redução de dano recebido (0 = nenhuma, 1 = total)
    (0.0,    5.0),   # stun          — ticks de stun máximo causado (modificado por recovery)
    (0.0,   10.0),   # knockback     — unidades de campo empurradas por hit
    (0.0,    0.5),   # recovery      — resistência a stun (0 = nenhuma, 1 = imune)
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
    "hp", "damage", "attack_speed", "range",
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

WALL_CORNER_THRESHOLD = 10  # unidades — distância da parede em que o lutador é
                             # considerado "encurralado" e pode usar ADVANCE para crossing
