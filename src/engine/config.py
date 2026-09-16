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

# Deslocamento do stream de RNG usado na CONFIRMAÇÃO de convergência do AG.
# O laço avalia todo indivíduo sob o mesmo stream (Common Random Numbers), o que é
# correto para SELEÇÃO — a diferença de fitness reflete genes, não sorteio. Mas
# reavaliar no mesmo stream não confirma nada: mede a MESMA realização do RNG com mais
# amostras, e o gate não pode discordar da confirmação. Somando este offset à semente
# de treino, cada execução é confirmada contra o próprio hold-out independente.
# Escolhido para não colidir com nenhuma outra família de sementes do projeto
# (treino 42+, MULTI_RUN_VALIDATION_SEED 9999, EXTERNAL_VALIDATION_SEED_START 10000+).
CONVERGENCE_SEED_OFFSET = 100000

# ── Fitness: pesos do AG escalar ─────────────────────────────────────────────
# fitness = -(LAMBDA_DRIFT·drift_penalty + LAMBDA_DOMINANCE·dominance_penalty).

LAMBDA_DRIFT = 1.0       # peso do desvio arquetípico (drift_penalty)
LAMBDA_DOMINANCE = 1.0   # peso do desbalanço de matchups (dominance_penalty)

# ── Fitness: identidade estrutural (drift) ───────────────────────────────────
# O drift é uma RMS PONDERADA dos desvios normalizados por range do bound. Genes
# listados em `ArchetypeDefinition.defining_genes` pesam DRIFT_DEFINING_WEIGHT× os
# demais: mover o range do Zoner custa mais que mover o stun dele. É declaração de
# PREMISSA (o que o arquétipo é), não de resposta — o fitness segue cego a quem
# vence quem. Peso 1.0 desliga a ponderação e volta ao drift uniforme.

DRIFT_DEFINING_WEIGHT = 3.0

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

# Banda de decisividade, em margem |score − 0.5|.
#
# O TETO é o guarda real: acima dele toda luta do par é massacre (vencedor fecha
# ~40% de HP), o que passa despercebido pelo termo global se os massacres se
# alternam entre os dois lados.
#
# O PISO é só guarda de DEGENERESCÊNCIA, e por isso mora bem abaixo da faixa de
# operação. Com o motor reformado toda luta termina em KO (medido: 100% em 70
# pares, incluindo rosters aleatórios), então D baixo não é "luta que não
# aconteceu" — é KO no fio, que é a melhor luta possível, não um defeito. Faixas
# medidas: roster degenerado (dano mín/HP máx/GUARDA, 0% KO, timeout com HP
# idêntico) D ≤ 0.008; espelho puro dos 5 canônicos D 0.020–0.033; pares reais
# D ≥ 0.045. O piso fica na base da faixa do espelho: abaixo dela um par de
# personagens DISTINTOS decide menos que dois personagens idênticos.

MATCHUP_FLOOR = 0.02       # piso: guarda de degenerescência (não morde em operação normal)
MATCHUP_THRESHOLD = 0.20   # teto: acima é blowout (vencedor fecha ~40% HP)

# ── Paralelismo ──────────────────────────────────────────────────────────────
# `evaluate_population` cria um pool novo a cada geração, então o custo de spawn
# escala com o nº de workers e, passado o ótimo, domina o ganho de paralelismo.
# Medido nesta máquina (28 núcleos lógicos), uma geração de 300 indivíduos:
#   1w 4.56s | 4w 1.66s | 8w 1.28s | 12w 1.41s | 16w 1.62s | 20w 1.91s | 28w 2.77s
# Com 28 (o default `None`) além de mais lento, os 28 processos carregando llvmlite
# estouravam o limite de commit do Windows (WinError 1455). O resultado não depende
# do nº de workers — a semeadura reset-ao-base é propagada aos workers (verificado:
# fitness idêntica em todas as contagens acima).

N_WORKERS = 8   # None = todos os núcleos da CPU; 1 = avaliação serial

# ── Simulação de combate ─────────────────────────────────────────────────────

FIELD_SIZE = 100                  # tamanho do campo (unidades)
INITIAL_DISTANCE = 50             # distância inicial entre lutadores
TICK_SCALE = 5                    # resolução sub-tick de cooldown/stun/movimento (mais granularidade = menos platôs no AG)
MAX_TICKS = 500 * TICK_SCALE      # duração máxima de uma luta
DEFEND_DAMAGE_REDUCTION = 1 - 0.4     # multiplicador no dano recebido ao defender
ACTION_PERSISTENCE_SUBTICKS = 10  # sub-ticks que uma intenção sorteada é mantida (inércia/momentum)

# ── Bounds e nomes dos genes ─────────────────────────────────────────────────
# 8 atributos + 3 pesos por personagem; todos contínuos. Semântica e calibração

ATTRIBUTE_BOUNDS = [
    (250.0, 450.0),  # hp
    (15.0, 30.0),    # damage (flat; só reduzido por DEFEND)
    (1.0, 5.0),      # attack_cooldown (ticks entre ataques; menor = mais rápido)
    (5.0, 20.0),     # range (< INITIAL_DISTANCE)
    (1.0, 5.0),      # speed
    (0.0, 0.6),      # stun — fração do cooldown do atacante; bound < 1 garante stun < cooldown
    (0.0, 3.0),      # knockback
    (0.0, 1.0),      # grab_power — soma ao multiplicador de dano contra alvo em guarda
                     # (0.6+grab): 0 = guarda plena, 0.4 = guarda anulada, 1.0 = guarda punida (1.6×)
]

WEIGHT_BOUNDS = [
    (0.0, 1.0),  # w_retreat
    (0.0, 1.0),  # w_defend
    (0.0, 1.0),  # w_aggressiveness
]

ATTRIBUTE_NAMES = ["hp", "damage", "attack_cooldown", "range", "speed", "stun", "knockback",
                   "grab_power"]
WEIGHT_NAMES = ["w_retreat", "w_defend", "w_aggressiveness"]

# Os 10 genes do personagem na ordem de `Character.genes()` — fonte única para
# quem precisa percorrer genes por nome/bound (drift, tabela de drift, validador).
GENE_NAMES = ATTRIBUTE_NAMES + WEIGHT_NAMES
GENE_BOUNDS = ATTRIBUTE_BOUNDS + WEIGHT_BOUNDS

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
