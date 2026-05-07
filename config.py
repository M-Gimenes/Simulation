"""
Configurações globais do sistema.
Todos os hiperparâmetros do AG e da simulação de combate estão aqui.
"""

# ── AG — População e critérios de parada ────────────────────────────────────

POPULATION_SIZE       = 300
ELITE_SIZE            = 10     # indivíduos preservados por elitismo por geração
MAX_GENERATIONS       = 100     # limite de gerações
STAGNATION_LIMIT      = 50     # gerações sem melhoria > 0.001 antes de parar
MATCHUP_CONVERGENCE_THRESHOLD = 0.10  # desvio máximo de WR por matchup (≈30–70%)

# ── AG — Operadores ──────────────────────────────────────────────────────────

TOURNAMENT_SIZE          = 3    # candidatos por seleção por torneio
MUTATION_RATE            = 0.1  # probabilidade de mutação por gene
ATTRIBUTE_MUTATION_SIGMA = 0.1 # sigma como fração do range do atributo — exploração ampla
WEIGHT_MUTATION_SIGMA    = 0.02 # sigma como fração do range do peso — inércia evolutiva

# ── Função de fitness ────────────────────────────────────────────────────────

SIMS_PER_MATCHUP       = 100   # simulações por matchup no round-robin
                                # 100 → erro padrão binomial em WR=50% ≈ 5%
                                # (vs 7% com 50 sims). Custo: ~2× mais lento, mas
                                # move atributos de baixo efeito (knockback, range,
                                # recovery) acima do piso de ruído da fitness.
SIMS_CONVERGENCE_CHECK = 200   # simulações extras para confirmar convergência
                                # alto o suficiente para que a margem de erro
                                # binomial (~3.5% a 50% WR) caiba folgadamente
                                # dentro de MATCHUP_CONVERGENCE_THRESHOLD (10%)

LAMBDA_SPECIALIZATION  = 0.2   # peso da penalidade de homogeneização (specialization_penalty)
LAMBDA_DRIFT           = 6.0   # peso da penalidade de desvio arquetípico (drift_penalty)
                                # 0.0 = evolução livre  |  alto = âncora ao canônico
                                # trade-off central do TCC: equilíbrio vs preservação
LAMBDA_DOMINANCE       = 1.0   # peso da penalidade de dominância em matchups (dominance_penalty)

MATCHUP_THRESHOLD      = 0.10  # excesso acima de 50% que inicia penalização (60% WR = limiar)

# ── Paralelismo ──────────────────────────────────────────────────────────────

N_WORKERS = None  # None = todos os núcleos da CPU; 1 = desativa paralelismo

# ── Simulação — Campo ────────────────────────────────────────────────────────

FIELD_SIZE            = 100  # tamanho do campo em unidades
INITIAL_DISTANCE      = 50   # distância inicial entre os lutadores
WALL_CORNER_THRESHOLD = 10   # distância da parede para considerar o lutador encurralado

# ── Simulação — Persistência de ação ─────────────────────────────────────────

ACTION_PERSISTENCE_SUBTICKS = 10  # após escolher uma ação por soft policy,
                                   # repete a mesma escolha por N sub-ticks
                                   # adicionais antes de re-amostrar. Evita
                                   # yo-yo (ADV-RET-ADV-RET tick a tick) e
                                   # modela commitment estratégico do jogador.
                                   # ATTACK e ADVANCE forçado (out of range /
                                   # cornered) sempre overrideiam o commitment.

# ── Simulação — Resolução temporal ────────────────────────────────────────────

TICK_SCALE = 5  # resolução sub-tick para cooldown e stun
                # cooldown e stun são multiplicados por este fator antes de round()
                # → 5× mais valores discretos possíveis, eliminando platôs do GA

STUN_CAP_MULTIPLIER = 1.0  # cap de stun = multiplier × cooldown do atacante
                            # 1.0 = stun nunca excede cooldown — não há combo chaining,
                            # cada hit landa um stun e o atacante já saiu do cooldown
                            # quando o alvo recupera. Evita estratégias degeneradas
                            # de perma-lock que o GA antes explorava.

# ── Simulação — Decisão ──────────────────────────────────────────────────────

MAX_TICKS              = 500 * TICK_SCALE  # duração máxima ajustada à resolução
DEFEND_DAMAGE_REDUCTION = 0.4  # multiplicador de dano recebido ao defender (40%)
                                # 0.2 era 80% de redução — defender trivializava trades
                                # e o GA não tinha incentivo para evoluir defense/recovery.
                                # 0.4 mantém defesa valiosa sem dominar a meta.

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
    (0,    15),      # recovery (sub-ticks subtraídos do stun recebido)
]

# Atributos cujo gene representa unidades inteiras. Mutações continuam gaussianas
# em escala contínua (preservando gradiente do AG ao longo de gerações), mas o
# valor armazenado é arredondado em clip() para o int mais próximo. Isso
# elimina o platô multiplicativo de recovery — cada unidade subtrai 1 sub-tick
# de stun, então a função fitness vê um efeito visível por unidade.
INTEGER_ATTRIBUTES = {8}  # índice de RECOVERY

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
NSGA2_OBJECTIVES    = ["dominance_penalty", "drift_penalty"]
