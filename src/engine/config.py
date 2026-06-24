"""
Configurações globais do sistema.
Todos os hiperparâmetros do AG e da simulação de combate estão aqui.
"""

# ── AG — População e critérios de parada ────────────────────────────────────

POPULATION_SIZE = 300
ELITE_SIZE = int(POPULATION_SIZE * 0.1)  # indivíduos preservados por elitismo por geração
MAX_GENERATIONS = 150  # limite de gerações
STAGNATION_LIMIT = 30  # gerações sem melhoria > 0.001 antes de parar
MATCHUP_CONVERGENCE_THRESHOLD = 0.10  # desvio máximo de WR por matchup

# ── AG — Operadores ──────────────────────────────────────────────────────────

TOURNAMENT_SIZE = 3  # candidatos por seleção por torneio
MUTATION_RATE = 0.05  # probabilidade de mutação por gene
ATTRIBUTE_MUTATION_SIGMA = 0.1  # sigma como fração do range do atributo
WEIGHT_MUTATION_SIGMA = 0.025  # sigma como fração do range do peso

# ── Função de fitness ────────────────────────────────────────────────────────

SIMS_PER_MATCHUP = 150  # simulações por matchup no round-robin
SIMS_CONVERGENCE_CHECK = 200  # simulações extras para confirmar convergência
LAMBDA_DRIFT = 1.0  # peso da penalidade de desvio arquetípico (drift_penalty)
# Igual a LAMBDA_DOMINANCE: pesa equilíbrio e preservação de identidade na mesma
# escala — coerente com o NSGA-II, que trata os dois como objetivos sem ponderação.
# O AG escalar dá UM ponto do trade-off; o mapa completo vem do NSGA-II. (Era 6.0,
# que prendia o AG no canônico e impedia balancear — ver docs/10, item V1.)
LAMBDA_DOMINANCE = (
    1.0  # peso da penalidade de dominância em matchups (dominance_penalty)
)
# Banda de decisividade por-luta do dominance_penalty (margem |score − 0.5|,
# em que score = 0.5 + 0.5·HP_frac do vencedor). A luta ideal não é nem blowout
# nem decidida no fio: o vencedor fecha com ~10-20% de HP de folga.
#   MATCHUP_THRESHOLD (teto) → acima disso a luta é decisiva demais (blowout)
#   MATCHUP_FLOOR     (piso)  → abaixo disso a luta é fina demais (quase-empate)
# Banda saudável = [MATCHUP_FLOOR, MATCHUP_THRESHOLD]. Cega à direção (não codifica
# quem deveria vencer — o ciclo continua métrica post-hoc).
MATCHUP_THRESHOLD = 0.10  # ⟺ vencedor fecha com ~20% de HP
MATCHUP_FLOOR = 0.05      # ⟺ vencedor fecha com ~10% de HP

# ── Paralelismo ──────────────────────────────────────────────────────────────

N_WORKERS = None  # None = todos os núcleos da CPU; 1 = desativa paralelismo

# ── Simulação — Campo ────────────────────────────────────────────────────────

FIELD_SIZE = 100  # tamanho do campo em unidades
INITIAL_DISTANCE = 50  # distância inicial entre os lutadores
WALL_CORNER_THRESHOLD = 10  # distância da parede para considerar o lutador encurralado

# ── Simulação — Persistência de ação ─────────────────────────────────────────

ACTION_PERSISTENCE_SUBTICKS = 10  # após escolher uma ação por soft policy, ela é mantida por este número de sub-ticks
# isso simula a inércia e o momentum do combate, dando mais peso à decisão

HESITATION_RATE = 0.10  # prob. por tick de "hesitar": mesmo num ramo determinístico
# (ATTACK / ADVANCE forçado), com esta prob. o personagem sorteia uma ação da
# distribuição PONDERADA (w_agg, w_ret, w_def) em vez da ação ótima. Modela o
# player não executar sempre o ótimo (variância de execução). 0.0 = combate
# determinístico nos ramos (reproduz o comportamento sem hesitação).
# PROVISÓRIO — calibrar (ver docs/10, Fase 4): maior ε que mantém todo gene acima
# do piso binomial e tira o WR do bimodal.

# ── Simulação — Resolução temporal ────────────────────────────────────────────

TICK_SCALE = 5  # resolução sub-tick para cooldown e stun
# cooldown e stun são multiplicados por este fator antes de round()
# → 5× mais valores discretos possíveis, eliminando platôs do GA

STUN_CAP_MULTIPLIER = 0.6  # cap de stun = multiplier × cooldown do atacante
# < 1.0 garante que o defensor sai do stun ANTES do atacante poder bater
# de novo, abrindo uma janela livre para agir (atacar/recuar/defender).
# Isso quebra o soft-perma-lock que existia em 1.0, em que stun ≈ cooldown
# fazia o defensor reentrar no stun assim que saía. Mantém stun relevante
# (60% do CD ainda é alto), mas não chaina indefinidamente.

# ── Simulação — Decisão ──────────────────────────────────────────────────────

MAX_TICKS = 500 * TICK_SCALE  # duração máxima ajustada à resolução
DEFEND_DAMAGE_REDUCTION = 0.4  # multiplicador de dano recebido ao defender (40%)

# ── Bounds dos genes ─────────────────────────────────────────────────────────

ATTRIBUTE_BOUNDS = [
    (300.0, 400.0),  # hp
    (10.0, 20.0),  # damage
    (1.0, 5.0),  # attack_cooldown
    (5.0, 20.0),  # range
    (1.0, 5.0),  # speed
    (0.0, 0.30),  # defense
    (0.0, 5.0),  # stun
    (0.0, 3.0),  # knockback
    (0, 10),  # recovery (sub-ticks subtraídos do stun recebido)
]

# Atributos cujo gene representa unidades inteiras. Mutações continuam gaussianas
# em escala contínua (preservando gradiente do AG ao longo de gerações), mas o
# valor armazenado é arredondado em clip() para o int mais próximo. Isso
# elimina o platô multiplicativo de recovery — cada unidade subtrai 1 sub-tick
# de stun, então a função fitness vê um efeito visível por unidade.
INTEGER_ATTRIBUTES = {8}  # índice de RECOVERY

WEIGHT_BOUNDS = [
    (0.0, 1.0),
    (0.0, 1.0),
    (0.0, 1.0),
]

ATTRIBUTE_NAMES = [
    "hp",
    "damage",
    "attack_cooldown",
    "range",
    "speed",
    "defense",
    "stun",
    "knockback",
    "recovery",
]
WEIGHT_NAMES = ["w_retreat", "w_defend", "w_aggressiveness"]

# ── NSGA-II ─────────────────────────────────────────────────────────────────

NSGA2_POP_SIZE = POPULATION_SIZE
NSGA2_GENERATIONS = MAX_GENERATIONS
NSGA2_OBJECTIVES = ["dominance_penalty", "drift_penalty"]
