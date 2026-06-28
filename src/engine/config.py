"""
Configurações globais do sistema.
Todos os hiperparâmetros do AG e da simulação de combate estão aqui.
"""

# ── AG — População e critérios de parada ────────────────────────────────────

POPULATION_SIZE = 300
ELITE_SIZE = int(POPULATION_SIZE * 0.1)  # indivíduos preservados por elitismo por geração
MAX_GENERATIONS = 150  # limite de gerações
STAGNATION_LIMIT = 30  # gerações sem melhoria > 0.001 antes de parar
GLOBAL_CONVERGENCE_THRESHOLD = 0.10   # convergência: |WR global − 0.5| máx por personagem (ninguém domina o roster)
MATCHUP_CONVERGENCE_THRESHOLD = 0.10  # banda de matchup "apertado" — métrica SECUNDÁRIA de reporting (tools).
# A convergência do AG (C2) não usa mais isto: usa GLOBAL_CONVERGENCE_THRESHOLD (boneco) + MATCHUP_WR_CAP (counter duro).

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
MATCHUP_THRESHOLD = 0.20  # ⟺ vencedor fecha com ~20% de HP
MATCHUP_FLOOR = 0.10      # ⟺ vencedor fecha com ~10% de HP

# Pesos dos três componentes do dominance_penalty (formulação C2 — equilíbrio
# GLOBAL, não por-matchup; ver C2_HANDOFF.md). Todos cegos à direção (nenhum
# codifica quem deveria vencer — o ciclo de vantagens segue métrica post-hoc).
#
#   PRIMÁRIO  — balanço GLOBAL por personagem: |WR_global − 0.5| → 0. Garante que
#               nenhum boneco domina o roster, mas NÃO força cada par a 50%. Um
#               boneco a 50% global pode vencer 2 e perder 2 — é o espaço em que o
#               ciclo de vantagens pode existir. (Antes o termo primário era WR
#               por-matchup, que empurrava TODO par a 50% e, por construção,
#               destruía o ciclo.)
#   SECUNDÁRIO (teto) — hard-counter por par: pune |WR_par − 0.5| acima de
#               MATCHUP_WR_CAP. Mantém as arestas do ciclo como VANTAGENS, não como
#               counters esmagadores (ex.: 100×0).
#   SECUNDÁRIO (qualidade) — decisividade por luta fora da banda saudável. Guarda
#               contra blowout (toda luta um massacre, mesmo com WR equilibrada).
DOMINANCE_GLOBAL_WEIGHT = 1.0
DOMINANCE_CAP_WEIGHT = 0.5
DOMINANCE_DECIS_WEIGHT = 0.5

# Meia-banda do hard-counter: um par é "counter duro" (penalizado pelo termo de teto
# e barrado na convergência) quando |WR − 0.5| > MATCHUP_WR_CAP, i.e. fora de
# [0.20, 0.80]. Dentro da banda, o par é vantagem de ciclo, não desbalanço.
# PROVISÓRIO — calibrar (0.25→[0.25,0.75] mais rígido; 0.35→[0.15,0.85] mais permissivo).
MATCHUP_WR_CAP = 0.20

# ── Paralelismo ──────────────────────────────────────────────────────────────

N_WORKERS = None  # None = todos os núcleos da CPU; 1 = desativa paralelismo

# ── Simulação — Campo ────────────────────────────────────────────────────────

FIELD_SIZE = 100  # tamanho do campo em unidades
INITIAL_DISTANCE = 50  # distância inicial entre os lutadores

# ── Simulação — Persistência de ação ─────────────────────────────────────────

ACTION_PERSISTENCE_SUBTICKS = 10  # após escolher uma intenção por soft policy, ela é mantida por este número de sub-ticks
# isso simula a inércia e o momentum do combate, dando mais peso à decisão

# ── Simulação — Resolução temporal ────────────────────────────────────────────

TICK_SCALE = 5  # resolução sub-tick para cooldown e stun
# cooldown e stun são multiplicados por este fator antes de round()
# → 5× mais valores discretos possíveis, eliminando platôs do GA

# ── Simulação — Decisão ──────────────────────────────────────────────────────

MAX_TICKS = 500 * TICK_SCALE  # duração máxima ajustada à resolução
DEFEND_DAMAGE_REDUCTION = 0.4  # multiplicador de dano recebido ao defender (40%)

# ── Bounds dos genes ─────────────────────────────────────────────────────────

ATTRIBUTE_BOUNDS = [
    (250.0, 450.0),  # hp
    (10.0, 20.0),    # damage
    (1.0, 5.0),      # attack_cooldown
    (5.0, 20.0),     # range
    (1.0, 5.0),      # speed
    (0.0, 0.6),      # stun (fração do cooldown; bound < 1 garante stun < cooldown_subticks)
    (0.0, 3.0),      # knockback
]

WEIGHT_BOUNDS = [
    (0.0, 1.0),
    (0.0, 1.0),
    (0.0, 1.0),
]

ATTRIBUTE_NAMES = ["hp", "damage", "attack_cooldown", "range", "speed", "stun", "knockback"]
WEIGHT_NAMES = ["w_retreat", "w_defend", "w_aggressiveness"]

# ── NSGA-II ─────────────────────────────────────────────────────────────────

NSGA2_POP_SIZE = POPULATION_SIZE
NSGA2_GENERATIONS = MAX_GENERATIONS
NSGA2_OBJECTIVES = ["dominance_penalty", "drift_penalty"]
# Ponto de referência do hipervolume (item 1.2 da metodologia): canto dos PIORES
# valores possíveis de (dominance_penalty, drift_penalty). dominance_penalty ≤ ~2.0
# (soma dos 3 termos no pior caso: GLOBAL·1 + CAP·1 + DECIS·1 = 1.0 + 0.5 + 0.5);
# drift_penalty ≤ ~1.0 (distância euclidiana normalizada média). Fixo entre execuções
# para que o HV seja comparável.
HYPERVOLUME_REFERENCE = (2.0, 1.0)

# ── Multi-run — N execuções independentes + estatística agregada ─────────────
# Item 1.1 da metodologia (Eiben & Smith 2015; Deb 2001): um EA é estocástico, então
# uma seed é uma amostra, não um resultado. A agregação roda o algoritmo sobre
# MULTI_RUN_N_SEEDS sementes consecutivas a partir de MULTI_RUN_SEED_START e reporta
# média ± desvio das penalidades, success rate por matchup e WR por personagem.
# Para escalar o experimento, basta aumentar MULTI_RUN_N_SEEDS.

MULTI_RUN_SEED_START = 42  # primeira semente; as execuções usam 42, 43, ..., 42+N-1
MULTI_RUN_N_SEEDS = 10     # número de execuções independentes a agregar
# Semente de validação independente do treino: o melhor indivíduo de cada execução é
# reavaliado sob ESTE mesmo stream de RNG (Common Random Numbers entre execuções), o
# que desacopla a métrica reportada da semente em que o indivíduo foi treinado.
MULTI_RUN_VALIDATION_SEED = 9999
MULTI_RUN_SIMS = SIMS_CONVERGENCE_CHECK  # simulações por matchup na reavaliação independente

# ── Validação externa ao fitness (estilo Ludi — Browne & Maire 2010) ─────────
# Item 3.2 da metodologia: confirmar o equilíbrio de UM indivíduo fixo sob condições
# que o AG nunca otimizou — K sementes de avaliação totalmente novas (fora do range
# de treino 42.. e da seed de validação do multi_run 9999), cada uma com mais sims
# para um intervalo de confiança apertado. Blinda contra overfitting ao fitness:
# um equilíbrio robusto sobrevive ao ruído fora do laço; um frágil não.

EXTERNAL_VALIDATION_SEED_START = 10000  # primeira semente de avaliação (independente do treino)
EXTERNAL_VALIDATION_N_SEEDS = 10        # nº de condições de avaliação independentes
EXTERNAL_VALIDATION_SIMS = 500          # sims/matchup por condição (> treino, p/ CI apertado)
