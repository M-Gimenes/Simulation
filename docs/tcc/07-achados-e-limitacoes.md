# 07 — Achados, limitações e o que falta

**Entra em**: Resultados / Discussão / Limitações.

## Achados

- **O modelo representa bem os arquétipos** (revisão do combate,
  [`../11-combat-review.md`](../reference/11-combat-review.md)): comportamento distinto e
  on-concept — Rushdown rusha, Turtle muralha, Zoner kita; DEFEND/RETREAT e
  espaçamento são usados de forma significativa. **Achado positivo** — o modelo não é
  uma caixa-preta arbitrária; os pesos produzem identidade comportamental visível.
- **O ciclo canônico não é trivialmente preservado em modo determinístico:** sem combo
  chaining / variância, muitos matchups ficam binários (100/0) e o ciclo desestabiliza.
  Interpretação (ver [02](02-ciclo-canonico.md)): a estrutura FGC depende parcialmente
  de mecânicas estocásticas que foram removidas — é **achado, não falha**.
- **`LAMBDA_DRIFT` alto prende o AG no canônico** (V1): com 6.0, o melhor indivíduo
  ficava colado no canônico (drift ≈ 0) e desbalanceado, porque mover-se custava ~6× o
  ganho em equilíbrio. Daí a decisão de `LAMBDA_DRIFT = 1.0` e o foco no NSGA-II (ver
  [04](04-caminhos-e-decisoes.md)).
- **Recovery evolutivamente neutro:** mecanicamente funciona (Turtle com recovery alta
  resiste ao stun), mas drifta para o piso 0 — porque, em lutas que são blowouts,
  resistir ao stun **não muda o desfecho**, então não há pressão seletiva. Hipótese a
  testar: pode voltar a importar quando as lutas ficarem apertadas. Confirmar com
  sensibilidade ([05](05-validacao-metodologica.md)).

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
- **Gerar a base**: rodar o AG (λ=1.0) e o **NSGA-II completo**, e demonstrar com a
  fronteira + dossiês que a reformulação do objetivo produz lutas apertadas / WR
  graduado (eventualmente uma *sweep* de `LAMBDA_DRIFT` no escalar).
- **Calibrar a hesitação** (ε) à luz da base.
- (Os instrumentos de leitura — `report`, `drift_table` com diferenciação,
  `fingerprint`, validador — já estão prontos.)
