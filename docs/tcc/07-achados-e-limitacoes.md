# 07 — Achados, limitações e o que falta

**Entra em**: Resultados / Discussão / Limitações.

## Achados

- **O modelo representa bem os arquétipos** (revisão do combate,
  [`../11-combat-review.md`](../reference/11-combat-review.md)): comportamento distinto e
  on-concept — Rushdown rusha, Turtle muralha, Zoner kita; DEFEND/RETREAT e
  espaçamento são usados de forma significativa. **Achado positivo** — o modelo não é
  uma caixa-preta arbitrária; os pesos produzem identidade comportamental visível.
- **O ciclo canônico não é trivialmente preservado em modo determinístico (baseline):**
  sem combo chaining / variância, muitos matchups do canônico ficam binários (100/0).
  Interpretação (ver [02](02-ciclo-canonico.md)): a estrutura FGC depende parcialmente
  de mecânicas estocásticas que foram removidas — é **achado, não falha**. *Cuidado*:
  distinguir esta quebra **do baseline** da quebra **pós-balanceamento** — esta última
  era forçada pelo objetivo antigo (WR por-matchup) e deixou de ser sob a reformulação
  **C2** (ver abaixo e [02](02-ciclo-canonico.md)).
- **`LAMBDA_DRIFT` alto prende o AG no canônico** (V1): com 6.0, o melhor indivíduo
  ficava colado no canônico (drift ≈ 0) e desbalanceado, porque mover-se custava ~6× o
  ganho em equilíbrio. Daí a decisão de `LAMBDA_DRIFT = 1.0` e o foco no NSGA-II (ver
  [04](04-caminhos-e-decisoes.md)).
- **`recovery` era evolutivamente neutro → removido (2026-06-27):** o gene funcionava
  mecanicamente (Turtle resistia a stun), mas drifava para o piso 0 — em lutas que são
  blowouts, resistir ao stun **não muda o desfecho**, logo não havia pressão seletiva.
  Foi um dos motivos para **removê-lo** do modelo (junto de `defense`) na simplificação
  do combate. O achado vira ilustração ("um gene sem efeito no desfecho não é
  otimizado"), não uma pendência.

## Limitações conhecidas

- O modelo de combate é uma **simplificação** de FGCs reais — sem frames de
  startup/recovery por golpe, mix-ups, neutral game, oclusão.
- **5 arquétipos** bastam para um ciclo; FGCs reais têm 10+.
- O fitness combina identidade e equilíbrio numa **soma ponderada** (escalar) ou
  **Pareto 2D** (NSGA-II) — outras formulações do trade-off são possíveis.
- O **round-robin** assume todos os arquétipos jogados igualmente — não modela
  matchmaking onde jogadores escolhem matchups favoráveis.

## O que ainda falta (para fechar a base experimental)

Backlog técnico detalhado em [`../10-known-issues.md`](../reference/10-known-issues.md). Em
termos de tese, falta:
- **Calibrar e re-rodar tudo (passo de maior retorno):** o motor de combate e o
  objetivo mudaram (simplificação + reformulação **C2**), então **todas as rodadas
  anteriores estão invalidadas** — os números históricos (ex.: "`best_dominance` 8/10
  matchups") foram gerados sob o modelo antigo e **não devem ser citados**. Calibrar
  os provisórios (`MATCHUP_WR_CAP`, bound/valores de `stun`-fração, canônicos
  re-tunados, `ACTION_PERSISTENCE_SUBTICKS`) e então executar `multi_run` (10+ seeds),
  `external_validation` e a fronteira/HV, e **interpretar**. A infraestrutura de
  agregação (item 1.1) já está pronta.
- (O reporting já foi **realinhado** ao headline C2 — `analyze_matchups`, `multi_run`
  e `external_validation` reportam WR **global** por personagem + hard-counters; ver
  [`../reference/10-known-issues.md`](../reference/10-known-issues.md). Falta só
  **executar** com a calibração final.)
- **Os instrumentos já estão prontos:** leitura por indivíduo (`report`, `drift_table`
  com diferenciação, `fingerprint`, validador), agregação estatística (`multi_run`,
  item 1.1), qualidade de fronteira (`pareto_metrics`, item 1.2) e robustez fora do
  laço (`external_validation`, item 3.2). Ver o status completo em
  [08-metodologias-da-literatura.md](08-metodologias-da-literatura.md).
