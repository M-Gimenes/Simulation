# 08 — Ferramentas

Em `src/tools/`. Todas rodam como módulo a partir da raiz (`py -m src.tools.<nome>`)
e operam sobre o canônico, o melhor do AG (`--evolved`) ou um representante do
NSGA-II (`--nsga2 [rep]`).

## `report` — dossiê do indivíduo (porta de entrada)

**Um comando** que compõe os tools de avaliação num relatório único: cabeçalho de
fitness (fitness, drift_penalty, dominance_penalty) + matchups (equilíbrio) + drift
de genes + diferenciação (homogeneização) + fingerprint (comportamento) + validador
(estrutura). Não duplica lógica — chama as funções dos outros tools.

```bash
py -m src.tools.report --evolved    # dossiê completo do melhor do AG
py -m src.tools.report --nsga2 best_dominance
```

Os tools abaixo continuam rodando isolados (pra quando você quer só um ângulo), e
os de propósito diferente (`sensitivity_analysis`, `viewer`, `nsga2_plots`) ficam
**fora** do dossiê.

## `analyze_matchups`

Roda os 10 matchups (ou um par específico) com N simulações cada e reporta
estatísticas, matriz de WR e resumos.

```bash
py -m src.tools.analyze_matchups                       # todos, canônico, N=1000
py -m src.tools.analyze_matchups rushdown zoner        # par específico
py -m src.tools.analyze_matchups --evolved --n 50      # indivíduo evoluído
py -m src.tools.analyze_matchups --nsga2 knee_point    # representante do Pareto
py -m src.tools.analyze_matchups --seed 42             # ver ressalva de seed abaixo
```

Saídas: estatísticas por luta (hits, dano, stun, ticks em/fora de range, mix de
ações, KO-rate, duração, distância), **matriz 5×5** de WR e dois resumos:

- **Equilíbrio** (cego à direção): um matchup é equilibrado quando
  `|WR − 50%| ≤ MATCHUP_THRESHOLD`, i.e. dentro de `[40%, 60%]` — a mesma faixa
  que o AG não penaliza. Consistente com o agregado global.
- **Ciclo canônico** (descritivo, não pass/fail): o favorito observado bate com o
  vencedor esperado pelo ciclo? `→ mantido` / `↯ invertido`. O ciclo é métrica
  *post-hoc*, nunca alvo.

## `drift_table`

Decompõe o `drift_penalty` por personagem e por gene: canônico vs evoluído, Δ
absoluto e Δ normalizado (mesma normalização do fitness — atributos por máximo do
bound, pesos crus). O desvio por personagem (`deviation_i`) vem de
`fitness._archetype_deviation`, então é idêntico ao que entra no `drift_penalty`;
a média dos 5 é o próprio `drift_penalty`. Mostra **o preço pago** pela evolução —
a visão que faltava do trade-off central da tese.

```bash
py -m src.tools.drift_table              # canônico (sanity — drift ≈ 0)
py -m src.tools.drift_table --evolved    # melhor do AG
py -m src.tools.drift_table --nsga2 knee_point
```

Complementa o `archetype_validator`: o validator checa **ordem** (Turtle ainda é o
mais defensivo?), a tabela de drift mede **distância** (o quanto cada gene se moveu).
No fim, reporta a **diferenciação** (distância média par-a-par dos 5 vs a do
canônico, como `ratio`): `ratio ~1` = os 5 seguem distintos; `< 1` = homogeneização
(convergiram entre si). É o medidor direto do eixo *homogeneização* da tese.

## `fingerprint`

Retrato de **como cada personagem joga**, agregado sobre seus 4 matchups: mix de
ações (ATK/ADV/RET/DEF), % do tempo fora de range (espaçamento) e % stunado.
Mostra canônico vs evoluído + Δ (em pontos percentuais) por personagem. Mede
identidade **comportamental** (o Zoner evoluído ainda kita?) — o terceiro ângulo,
junto da estrutural (`archetype_validator`) e da de genes (`drift_table`).

```bash
py -m src.tools.fingerprint              # canônico (baseline, Δ=0)
py -m src.tools.fingerprint --evolved    # evoluído vs canônico
py -m src.tools.fingerprint --nsga2 knee_point
```

## `archetype_validator`

20 asserções estruturais de identidade (sem rodar combate):

- **Layer 1 — inter (14):** rankings entre os 5 personagens (Rushdown tem maior
  speed e menor cooldown, Zoner tem maior range, Turtle tem maior hp/defense/
  recovery, etc.).
- **Layer 2 — intra (6):** comparações normalizadas dentro de um personagem
  (`norm(range) > norm(speed)` no Zoner, etc.). Normalização = fração do máximo
  `x/hi` (mesma convenção do `fitness`).

São verificações de **ranking ordinal**, não de magnitude. **Limitação:** não
detectam homogeneização funcional — se todos convergirem para valores próximos
mas o Zoner ainda tiver o maior range por uma fração, as asserções passam. O
anti-homogeneização real é o `drift_penalty`.

```bash
py -m src.tools.archetype_validator [--evolved | --nsga2 [rep]]
```

## `sensitivity_analysis`

Para cada (arquétipo, atributo), perturba o gene em ±σ e mede `Δ WR`. Atributos
com `|Δ|` médio abaixo do piso binomial são genes "neutros" (drift por random
walk, sem pressão seletiva).

```bash
py -m src.tools.sensitivity_analysis --sims 500 --workers 1
```

> ⚠️ A redução de variância por pareamento de seeds descrita no docstring **não
> está funcionando** — o combate roda no RNG do Numba, que ignora `random.seed`.
> Ver [09-reproducibility.md](09-reproducibility.md) e
> [10-known-issues.md](10-known-issues.md).

## `viewer` / `web_viewer`

Visualizadores de uma luta, consumindo `CombatTrace`:

```bash
py -m src.tools.viewer          # ASCII no terminal
py -m src.tools.web_viewer      # browser interativo em localhost:8080
```

## `nsga2_plots`

Plot 2D da fronteira de Pareto (dominance × drift) com os 4 representantes
destacados. Chamado automaticamente por `py main.py --algorithm nsga2`; salva em
`results/plots/nsga2/<timestamp>/pareto_front.png`.
