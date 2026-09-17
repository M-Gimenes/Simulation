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

# Stream de avaliação POR GERAÇÃO (ver `fitness.generation_seed`).
#
# O laço avalia toda uma geração sob o mesmo stream — CRN, para que a diferença de
# fitness entre indivíduos reflita genes e não sorteio — e TROCA de stream a cada
# geração. Sem a troca, as MAX_GENERATIONS inteiras correm sobre UMA realização do
# RNG e a população se ajusta a ela: medido (60 gerações, 3 sementes), a razão entre
# o `dominance` de dentro do laço e o de fora era ~3×, e caiu para ~1,25× com a
# rotação — o número de dentro do laço passa a ser quase honesto. O equilíbrio REAL
# (medido fora) também melhora, porque o AG deixa de poder comprar equilíbrio
# explorando acidentes de uma realização específica.
#
# `seed * STRIDE + geração` com geração < STRIDE garante que duas sementes de treino
# nunca compartilhem stream, e a família (42000+) não colide com nenhuma outra do
# projeto (validação 9999, externa 10000+, confirmação +100000).
GENERATION_SEED_STRIDE = 1000

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

# O `decis_term` sai 0.0000 nos indivíduos FINAIS das 10 sementes, nos dois
# algoritmos — o que NÃO quer dizer que o termo seja morto. Ele é uma GUARDA, e uma
# guarda que lê 0 no fim é uma guarda que funcionou: a busca saiu da região ruim.
# Medido em 18 rosters (canônico + 5 espelhos + 8 aleatórios + 4 evoluídos), 180 pares:
#
#   canônico (= geração 0 do AG escalar)   decis 0.2834   5/10 pares acima do TETO
#   8 aleatórios                           decis 0.10–0.66  3–9/10 acima do TETO
#   espelho Zoner (solução trivial)        decis 0.1282  10/10 abaixo do PISO
#   4 evoluídos                            decis 0.0000   0/10
#
# 57/180 pares estouram o teto e o D observado chega a 0.49, contra teto 0.20 — a
# guarda opera bem dentro da faixa real, não fora dela. E as duas metades pegam coisas
# distintas: o teto pega blowout (canônico, aleatórios), o piso pega degenerescência
# (o espelho, que é a solução trivial de equilíbrio).

# Meia-banda do hard-counter: par é counter duro se |WR − 0.5| > MATCHUP_WR_CAP.
#
# ANCORADO NA GRADE DA FGC. Matchup chart de jogo de luta é dito em inteiros —
# 5-5, 6-4, 7-3, 8-2 — que em |WR − 0.5| são 0.00, 0.10, 0.20, 0.30. O consenso de
# domínio é que 6-4 é vantagem saudável (existe em todo jogo) e 7-3 é counter. Logo
# o cap tem de PERMITIR 0.10 e BARRAR 0.20.
#
# O valor não pode cair EM CIMA de um ponto da grade: com ruído binomial de medição,
# um limiar colado num valor legítimo vira cara-ou-coroa. Medido (n = SIMS_PER_MATCHUP,
# σ ≈ 0.040 em p = 0.6):
#
#   cap    limiar   6-4 real dispara à toa   7-3 real é capturado
#   0.10    0.60            50.0%                    99.6%
#   0.15    0.65            10.6%                    90.9%
#   0.20    0.70             0.6%                    50.0%
#
# 0.15 é o ponto médio da única lacuna que importa (entre 6-4 e 7-3) e o único valor
# que não reprova sistematicamente um 6-4 legítimo nem deixa passar metade dos 7-3.
# Subir sims estreita as duas caudas sem mover o cap — ver SIMS_PER_MATCHUP.
MATCHUP_WR_CAP = 0.15

# Banda de decisividade, em margem |score − 0.5|.
#
# O TETO é o guarda real: acima dele toda luta do par é massacre (vencedor fecha
# ~40% de HP), o que passa despercebido pelo termo global se os massacres se
# alternam entre os dois lados.
#
# O PISO é só guarda de DEGENERESCÊNCIA, e por isso mora abaixo da faixa de
# operação. Com o motor reformado toda luta termina em KO (medido: 100% em 70
# pares, incluindo rosters aleatórios), então D baixo não é "luta que não
# aconteceu" — é KO no fio, que é a melhor luta possível, não um defeito.
#
# Faixas medidas (2026-09-16, sims=MULTI_RUN_SIMS, seed=MULTI_RUN_VALIDATION_SEED):
#   roster degenerado (dano mín/HP máx/GUARDA, 0% KO, timeout com HP idêntico) ≤ 0.008
#   espelhos dos 5 canônicos   Zoner 0.016–0.019 · Rushdown 0.030–0.035 ·
#                              Turtle 0.027–0.032 · CM 0.045–0.052 · Grappler 0.074–0.088
#   rosters evoluídos          0.044–0.178
#
# O piso morde 10/10 pares no espelho do Zoner e 0/10 em todo o resto — inclusive
# 0/10 nos quatro rosters evoluídos. É o comportamento pretendido: dois Zoners
# idênticos se afastando é o caso MENOS decidido que o motor produz, e o espelho é
# justamente a solução trivial de equilíbrio (identidade zero) contra a qual a tese
# argumenta. Não é "abaixo de todo espelho" — é abaixo de todo par de personagens
# DISTINTOS.

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
# Sub-ticks que uma intenção sorteada é mantida (inércia/momentum).
#
# 5 = exatamente 1 tick (TICK_SCALE) e exatamente o cooldown mínimo. A 10 havia
# incoerência: quem tem `attack_cooldown = 1` e sorteia GUARDA abria mão de DUAS
# janelas de ataque, não uma.
#
# E a medição concorda com a coerência. Sensibilidade no indivíduo evoluído (600
# sims, piso medido com 12 repetições), razão sinal/ruído por gene — a 5 melhora em
# 8/8, e `speed`/`stun` quase dobram:
#
#   gene              persist=5   persist=10   ganho        piso medido: 3.5% (p=5)
#   range                  8.86         5.82    +52%                     4.9% (p=10)
#   attack_cooldown        5.80         4.22    +37%
#   damage                 4.97         3.59    +38%
#   hp                     4.43         3.55    +25%
#   grab_power             2.26         1.73    +30%
#   speed                  2.03         1.12    +81%
#   stun                   1.94         1.08    +80%
#   knockback              0.74         0.57    +30%
#
# Persistência alta paga DUAS vezes: menos decisões independentes por luta significa
# sinal menor E piso de ruído maior (o desfecho tem mais variância).
ACTION_PERSISTENCE_SUBTICKS = 5

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
# nº de execuções independentes a agregar.
# DECIDIDO: 20. Poder medido por simulação (4000 réplicas, Â₁₂ = 0.80, critério
# `3 × p < 0.05` com a família de Holm corrigida): n=10 → 44.4% · n=15 → 73.1% ·
# n=20 → 85.9% · n=30 → 97.3%. n=20 é o menor que passa do patamar de 80%.
# Mantido em 10 NESTA rodada por custo (a bateria dobra); as sementes 42..51 são
# determinísticas, então subir para 20 depois reproduz estas 10 exatamente.
MULTI_RUN_N_SEEDS = 10
MULTI_RUN_VALIDATION_SEED = 9999  # seed comum de reavaliação (CRN): desacopla a métrica da seed de treino
MULTI_RUN_SIMS = SIMS_CONVERGENCE_CHECK  # sims/matchup na reavaliação independente

# ── Validação externa ao fitness (estilo Ludi — Browne & Maire 2010) ─────────

EXTERNAL_VALIDATION_SEED_START = 10000  # primeira semente de avaliação (independente do treino)
EXTERNAL_VALIDATION_N_SEEDS = 10        # nº de condições de avaliação independentes
EXTERNAL_VALIDATION_SIMS = 500          # sims/matchup por condição (> treino, p/ CI apertado)
