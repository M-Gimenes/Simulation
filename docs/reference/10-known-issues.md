# 10 — Auditoria, pontos em aberto e backlog

Relatório da auditoria de **2026-06-23** (revisão completa do código após período
afastado). Severidade decrescente. Itens marcados ✅ já foram corrigidos nesta
rodada; os demais ficam registrados para decisão.

## 🔴 Metodologia — em aberto (peso de decisão)

### V1 — `LAMBDA_DRIFT=6.0` prende o AG escalar no canônico (achado da validação)
Rodando o AG escalar com o novo objetivo (seed 42, 150 gen), o melhor indivíduo
ficou **colado no canônico**: `drift_penalty = 0.013` (Combo Master = exatamente
canônico), e 8/10 matchups ainda blowout. Causa: com `LAMBDA_DRIFT=6.0` vs
`LAMBDA_DOMINANCE=1.0`, mover-se para aproximar as lutas custa ~6× mais do que
ganha em dominância — o AG prefere ficar canônico e desbalanceado. **A
reformulação do objetivo (A) está correta, mas o peso do drift impede o AG
escalar de usá-la.**

**Encaminhado e demonstrado (2026-06-24):** `LAMBDA_DRIFT` baixado para **1.0**
(igual ao dominance) — soltou o AG escalar. A demonstração, porém, **revelou que o
objetivo só-decisividade não balanceava** (ver D1 abaixo): produzia lutas apertadas
mas WR desequilibrada. Resolvido reintroduzindo a WR como termo primário do
`dominance_penalty`. Após isso, AG escalar e `best_dominance` ficam ~8/10 matchups
em 40-60% de WR. Opcional remanescente: sweep de `LAMBDA_DRIFT` para mapear o
trade-off no escalar.

### Calibração de `HESITATION_RATE` — pendente
A hesitação (variância de player) entrou com ε provisório **0.10**. Falta a
calibração formal (varredura): maior ε que mantém todo gene acima do piso binomial
(via `sensitivity_analysis`, agora confiável) **e** tira o WR do bimodal. A
[revisão do combate](11-combat-review.md) sugere que a hesitação é menos crítica
do que se pensava — a alavanca real é o objetivo por-luta. **Decisão a revisitar:**
medir o efeito marginal da hesitação após o objetivo e talvez reduzir/zerar ε.

## ✅ Corrigido em 2026-06-24

### D1 — `dominance_penalty` só-decisividade era cego à WR
A versão que media apenas **decisividade por-luta numa banda** [0.05, 0.10] tinha um
furo: é **cega à frequência de vitória**. Um matchup 100%×0% fechando sempre com
~15% HP dá `D ≈ 0.075` (dentro da banda) → penalidade **zero**. Empírico:
`best_dominance` dava `dominance_penalty = 0.0000`, 10/10 lutas "sadias", mas **0/10
matchups equilibrados** (Grappler 92%, Turtle 8%). A hipótese "luta apertada ⟹ WR
~50%" foi **falsificada** — ver [11-combat-review.md](11-combat-review.md).
**Corrigido:** WR voltou como termo **primário** (`|WR−0.5|/0.5` contínuo,
`DOMINANCE_WR_WEIGHT=1.0`); decisividade rebaixada a regularizador secundário
(`DOMINANCE_DECIS_WEIGHT=0.5`, guarda contra blowout-coinflip). `best_dominance`
passou a 8/10 matchups em 40-60% WR. Ver [05](05-genetic-algorithm.md).

### D2 — semeadura hash-por-genes anulava o CRN
A semeadura `crc32(genes) XOR base` era reprodutível mas dava a cada indivíduo um
stream de RNG diferente — congelava o ruído MC numa função descontínua dos genes,
anulando a redução de variância dos Common Random Numbers. **Corrigido:** toda
avaliação reseta ao mesmo `_SEED_BASE` (CRN) — mesma reprodutibilidade, paisagem
mais lisa. Caveat de alinhamento documentado em
[09-reproducibility.md](09-reproducibility.md).

## ✅ Corrigido nesta rodada

- **A1 — reprodutibilidade do seed.** `combat.seed_combat` (`@njit`) + semeadura
  determinística por-indivíduo (`fitness.set_seed_base`, `crc32(genes) XOR base`,
  propagada aos workers via `initializer`). `--seed` agora reproduz; o pareamento
  do `sensitivity_analysis` funciona. Verificado empiricamente. Ver
  [09-reproducibility.md](09-reproducibility.md).
- **C5 — ruído nos critérios de parada.** Resolvido de quebra pelo A1: a
  reavaliação do melhor indivíduo agora é determinística (mesma fitness), sem
  ruído de re-amostragem no `best_fitness`/estagnação.
- **Objetivo reformulado (A) + hesitação (B).** O `dominance_penalty` passou a ser
  **decisividade por-luta numa banda** [0.05, 0.10] (vencedor fecha 10-20% HP),
  cego à direção — dá gradiente em combate determinístico e penaliza tanto blowout
  quanto quase-empate. A hesitação ponderada (`HESITATION_RATE`) reintroduz
  variância de player. Ver [05](05-genetic-algorithm.md), [04](04-combat-model.md)
  e [11-combat-review.md](11-combat-review.md). *(Calibração do ε pendente — acima.)*
- **B1 — divergência de `stun_applied` entre as duas variantes JIT.**
  `_simulate_combat_jit` somava `stun_t` incondicionalmente; o traced só somava
  quando o stun era efetivamente imposto. Alinhado: agora ambos somam só quando
  aplicado.
- **B2 — flag `--plot-3d` morto.** Removido de `main.py` e o parâmetro
  `plot_3d` de `nsga2_plots.save_plots` (sobra de quando havia 3 objetivos).
- **C1 — imports mortos:** `copy`/`field`/`Tuple` em `character.py`,
  `copy`/`random` em `individual.py`.
- **C2 — type hint:** `objectives: Tuple[float, float, float]` → `Tuple[float, float]`.
- **C4 — naming:** `main.py` chamava o drift de `cost` no print → `drift`.
- **C3 — duas convenções de normalização.** Unificado: `archetype_validator._norm`
  passou a usar `x/hi` (fração do máximo), a mesma convenção do `fitness`. Neutro
  para o AG (validator é diagnóstico); canônico segue 20/20.
- **A2 — `specialization_penalty` removido.** Não media diferenciação entre
  arquétipos (era spread intra-personagem), era redundante com o `drift_penalty` e
  quebrava a simetria com o NSGA-II. Decisão (c): removido do fitness — o AG escalar
  agora otimiza `drift + dominance`, **os mesmos dois eixos do NSGA-II**. A ideia de
  "os 5 ainda são distintos?" fica para uma métrica **post-hoc** (diferenciação
  par-a-par, candidata a entrar na `drift_table`), não como termo de otimização.

## Direção — reflexões (não são erros)

- O ciclo canônico fora do fitness é **intencional e correto** para a pergunta de
  pesquisa (evita circularidade).
- **Crossover só por bloco de personagem:** recombinação fina de genes dentro de
  um personagem depende 100% da mutação. Legítimo, mas limita exploração — vale
  citar como decisão na metodologia.

## Dossiê de resultado por indivíduo — FEITO ✅

Três ângulos de identidade, todos implementados (além das matrizes de matchup que
cobrem o eixo *equilíbrio*):

1. ✅ **Tabela de drift por gene** (`src/tools/drift_table.py`): canônico vs
   evoluído por gene + desvio por personagem (= `drift_penalty`) + **diferenciação**
   par-a-par (homogeneização). Identidade de *genes* + eixo homogeneização.
2. ✅ **Fingerprint comportamental** (`src/tools/fingerprint.py`): mix de ações e
   espaçamento por personagem, canônico vs evoluído + Δ. Identidade *comportamental*.
3. ✅ **Validador estrutural** (`src/tools/archetype_validator.py`): invariantes de
   ranking. Identidade *estrutural*.

Calibração da hesitação (`HESITATION_RATE`) segue pendente (acima).

## Notas de manutenção

- A memória `project_archetype_validator` ("retomar Task 5 `_collect_stats`") está
  **desatualizada**: o validator está completo; a camada comportamental virou o tool
  `fingerprint` (feito).
