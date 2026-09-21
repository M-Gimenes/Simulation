"""
Hiperparâmetros do AG e da simulação de combate — single source.
Tabela comentada completa e notas de calibração em docs/reference/07-configuration.md.
"""

import os

# ── AG: população e parada ───────────────────────────────────────────────────

POPULATION_SIZE = 300
# Elitismo é uma FRAÇÃO da população, não uma contagem: `operators.elite_count` a aplica
# sobre o tamanho REAL. Uma contagem absoluta faria uma execução de orçamento reduzido
# herdar 30 elites e o elitismo efetivo saltar de 10% para 25% (pop 120) ou 100% (pop 30)
# — o AG deixaria de buscar, em silêncio e produzindo números plausíveis.
ELITE_RATE = 0.10
MAX_GENERATIONS = 150
# A população inicial do AG escalar leva o roster canônico (o resto é aleatório). A do
# NSGA-II nasce 100% aleatória — lá o canônico seria imortal no rank 0 (ver
# `nsga2.run`). Desligar isto é o braço de controle que separa algoritmo de inicialização.
GA_CANONICAL_SEED = True
# Convergência do AG (C2) = balanço global (abaixo) + ausência de hard-counter
# (MATCHUP_WR_CAP, na seção de fitness).
GLOBAL_CONVERGENCE_THRESHOLD = 0.10        # |WR global − 0.5| máx por personagem (ninguém domina o roster)

# ── AG: operadores ───────────────────────────────────────────────────────────

TOURNAMENT_SIZE = 3              # candidatos por seleção por torneio — SÓ o AG escalar;
                                 # o NSGA-II usa torneio binário por rank + crowding
MUTATION_RATE = 0.05            # probabilidade de mutação por gene
ATTRIBUTE_MUTATION_SIGMA = 0.1   # sigma da mutação, como fração do range do atributo
WEIGHT_MUTATION_SIGMA = 0.025    # idem para os pesos (menor = mais inércia)

# ── Fitness: simulações ──────────────────────────────────────────────────────

SIMS_PER_MATCHUP = 150         # simulações por matchup no round-robin
SIMS_CONVERGENCE_CHECK = 200   # simulações extras para confirmar convergência

# Deslocamento do stream de RNG usado na CONFIRMAÇÃO de convergência do AG.
# Dentro de uma geração o laço avalia todo indivíduo sob o mesmo stream (Common Random
# Numbers), o que é correto para SELEÇÃO — a diferença de fitness reflete genes, não
# sorteio. Mas reavaliar no mesmo stream não confirma nada: mede a MESMA realização do
# RNG com mais amostras, e o gate não pode discordar da confirmação. Somando este offset
# ao stream da geração, cada confirmação roda num stream que o AG nunca viu.
# Escolhido para não colidir com nenhuma outra família de sementes do projeto
# (streams de treino `seed·GENERATION_SEED_STRIDE + geração`, MULTI_RUN_VALIDATION_SEED
# 9999, EXTERNAL_VALIDATION_SEED_START 10000+).
#
# INVARIANTE que a escolha pressupõe: a confirmação da semente `s` roda em
# `s·STRIDE + geração + OFFSET`, e o treino da semente `s'` em `s'·STRIDE + geração`.
# As duas famílias só ficam disjuntas enquanto `s' != s + OFFSET/STRIDE`, isto é,
# enquanto nenhuma semente de treino for `s + 100`. Com as famílias em uso — bateria
# 42–61 e sweeps 1000–1004 — a folga é grande, mas quem acrescentar uma semente de
# treino precisa conferir que ela não cai a exatamente 100 de outra já em uso.
CONVERGENCE_SEED_OFFSET = 100000

# Stream de avaliação POR GERAÇÃO (ver `fitness.generation_seed`).
#
# O laço avalia toda uma geração sob os mesmos sorteios — CRN, uma semente por luta,
# para que a diferença de fitness entre indivíduos reflita genes e não sorteio — e TROCA
# de stream a cada geração. Sem a troca, as MAX_GENERATIONS inteiras correm sobre UMA
# realização do RNG e a população se ajusta a ela: medido (5 sementes, 60 gerações), a
# razão entre o `dominance` de dentro do laço e o de fora cai de 4,14 para 2,20 com a
# rotação, melhorando em 5/5 sementes (ver docs/thesis/04).
#
# `seed * STRIDE + geração` com geração < STRIDE garante que duas sementes de treino
# nunca compartilhem stream, e as famílias de treino — bateria 42000+, sweeps 1000000+
# — não colidem com nenhuma outra do projeto (validação 9999, externa 10000+,
# confirmação +100000).
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

# O `decis_term` sai 0.0000 nos indivíduos FINAIS de todas as sementes, nos dois
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
# (lutas que acabam sem vencedor de fato).

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
# O piso fica acima do roster degenerado e abaixo de todo par de personagens DISTINTOS:
# não morde nenhum dos quatro rosters evoluídos. Dos cinco espelhos, pega só o do Zoner
# (dois Zoners idênticos se afastando é o caso menos decidido que o motor produz) — os
# outros quatro passam. Logo o piso NÃO é a defesa contra a solução trivial de
# equilíbrio (cinco cópias do mesmo personagem): essa defesa é o `drift_penalty`, que
# cobra a perda de identidade de qualquer espelho.

MATCHUP_FLOOR = 0.02       # piso: guarda de degenerescência (não morde em operação normal)
MATCHUP_THRESHOLD = 0.20   # teto: acima é blowout (vencedor fecha ~40% HP)

# ── Paralelismo ──────────────────────────────────────────────────────────────
# Workers do pool persistente de `fitness.parallel_map`. Teto de 8: com todos os núcleos,
# os processos carregando llvmlite estouravam o limite de commit do Windows (WinError
# 1455), e acima de 8 o ganho some no ruído — medido numa geração de 300 indivíduos com o
# pool vivo: 8w 1.04s | 12w ~1.0s | 16w ~0.9s. Abaixo do teto, o nº de núcleos da
# máquina. O resultado não depende do nº de workers: cada luta é semeada a partir do
# `_SEED_BASE` (`fitness.fight_seed`), e o estado do pai viaja com cada tarefa.
# 1 = avaliação serial.

N_WORKERS = min(8, os.cpu_count() or 1)

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
# 8 atributos + 3 pesos por personagem. Semântica e calibração de cada um em
# docs/reference/03-archetypes.md e 04-combat-model.md.

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

# Os 11 genes do personagem na ordem de `Character.genes()` — fonte única para
# quem precisa percorrer genes por nome/bound (drift, tabela de drift, validador).
GENE_NAMES = ATTRIBUTE_NAMES + WEIGHT_NAMES
GENE_BOUNDS = ATTRIBUTE_BOUNDS + WEIGHT_BOUNDS

# ── NSGA-II ──────────────────────────────────────────────────────────────────

NSGA2_POP_SIZE = POPULATION_SIZE
NSGA2_GENERATIONS = MAX_GENERATIONS
NSGA2_OBJECTIVES = ["dominance_penalty", "drift_penalty"]  # objetivos Pareto, sem ponderação
# Ponto de referência do hipervolume, ancorado nos modelos nulos: `dominance` ≈ a do
# canônico (1,27 — o equilíbrio de partida) e `drift` ≈ o do espelho (0,38 — identidade
# zero). Um ponto com equilíbrio pior que o de partida ou identidade pior que a de cinco
# cópias fica fora da área, que é o que ele vale. Fixo, para o HV ser comparável entre
# execuções. O anterior, (2,0; 1,0) — os máximos teóricos —, ficava tão longe de toda
# fronteira real que o HV saturava em 90% da área e mal separava uma fronteira de outra.
HYPERVOLUME_REFERENCE = (1.3, 0.4)

# ── Multi-run: N execuções independentes + estatística agregada ──────────────

MULTI_RUN_SEED_START = 42         # primeira semente; execuções usam 42, 43, ..., 42+N−1
# nº de execuções independentes a agregar. Poder medido por simulação (4000 réplicas,
# Â₁₂ = 0.80, critério `3 × p < 0.05` com a família de Holm corrigida): n=10 → 44.4% ·
# n=15 → 73.1% · n=20 → 85.9% · n=30 → 97.3%. 20 é o menor que passa do patamar de 80%.
# Fora do carimbo de proveniência: define só o tamanho da amostra, que o artefato do
# `multi_run` grava no corpo.
MULTI_RUN_N_SEEDS = 20
MULTI_RUN_VALIDATION_SEED = 9999  # seed comum de reavaliação (CRN): desacopla a métrica da seed de treino
MULTI_RUN_SIMS = SIMS_CONVERGENCE_CHECK  # sims/matchup na reavaliação independente

# Sims/matchup do perfil comportamental que mede identidade FUNCIONAL (Layer 3 do
# validador e concordância de ranking) — no multi_run, nos modelos nulos e no dossiê.
# Medido em re-teste (mesmo roster, 3 seeds): a 120 a concordância do evoluído variava
# 0,19–0,28; a 200, 0,23–0,24. O canônico fica ≥ 0,97 nos dois.
IDENTITY_BEHAVIORAL_SIMS = 200

# ── Validação externa ao fitness (estilo Ludi — Browne & Maire 2010) ─────────

EXTERNAL_VALIDATION_SEED_START = 10000  # primeira semente de avaliação (independente do treino)
EXTERNAL_VALIDATION_N_SEEDS = 10        # sementes por condição, somadas numa amostra só
EXTERNAL_VALIDATION_SIMS = 500          # sims/matchup por semente → 5000 lutas por par

# Regras perturbadas: condições de combate que o AG nunca viu, uma constante por vez.
# Trocar a semente só replica a medição com mais amostra; é mudar a REGRA que testa se o
# equilíbrio sobrevive fora das condições exatas em que foi otimizado. Cada perturbação
# fica dentro do que o modelo sustenta: a distância inicial segue maior que todo alcance
# (20), e a redução da guarda desloca o ponto neutro do agarrão em ±0,05.
EXTERNAL_VALIDATION_RULE_PERTURBATIONS = [
    ("INITIAL_DISTANCE", 40.0), ("INITIAL_DISTANCE", 60.0),
    ("FIELD_SIZE", 80.0), ("FIELD_SIZE", 120.0),
    ("ACTION_PERSISTENCE_SUBTICKS", 4), ("ACTION_PERSISTENCE_SUBTICKS", 6),
    ("DEFEND_DAMAGE_REDUCTION", 0.55), ("DEFEND_DAMAGE_REDUCTION", 0.65),
]
