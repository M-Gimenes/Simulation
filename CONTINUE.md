# Continuar daqui: "o AG escalar perde na própria função" — investigação fechada

Sessões de 2026-09-22. Scripts e dados em `diagnostics/` (fora de `src/`, não entram no
carimbo de proveniência). **Ainda não foi anotado em `docs/thesis/`** além da correção
do 07 — ver "Próximos passos".

## O achado, em uma frase

O AG escalar resolve o equilíbrio por volta da geração 31 e passa as 120 gerações
restantes selecionando ruído, porque `dominance` é medido por amostragem e `drift` é
determinístico. Quem paga é a identidade. Um híbrido NSGA-II → AG escalar **com o mesmo
orçamento** entrega mais identidade *e* mais equilíbrio.

## Evidência

### 1. O AG perde na soma que ele mesmo otimiza
`dominance + drift` (λ = 1/1), bateria de 2026-09-21:
- no stream do laço, a fronteira do NSGA-II tem um ponto melhor em **20/20** sementes
  (medianas 0,2658 contra 0,2052);
- reavaliado na seed 9999, o `scalar_optimum` vence em **18/20**;
- a 1000 lutas × 8 streams (`data/noise.json`), vence em **5/5**.

Mas os dois continuam **mutuamente não-dominados em 18/20**: o ponto do AG fica *além*
da ponta de menor dominance da fronteira em **19/20** (0,017 contra 0,05). Ele não está
atrás da fronteira — está num extremo dela.

### 2. O mecanismo: assimetria de ruído entre os dois termos
`drift` é conta pura; `dominance` tem σ = 0,015–0,028 a 150 lutas (30 streams,
`data/noise.json`). Depois da geração ~31 o gradiente verdadeiro de `dominance` acabou e
sobra ruído ~60× maior que o ganho de drift por geração (0,0003).

Sobreajuste ao stream, medido (`dominance` no laço → reavaliado):

| braço | no laço | reavaliado | inflação |
|---|---|---|---|
| AG escalar | 0,0172 | 0,0399 | **2,58×** (pior em 19/20) |
| controle λ = 0 | 0,0184 | 0,0534 | **3,21×** |
| NSGA-II `scalar_optimum` | 0,0559 | 0,0796 | 1,52× |

Quanto mais a seleção se concentra no termo ruidoso, mais a execução compra sorte. O
gate de convergência conta o mesmo: dispara 70×, a confirmação fora do stream rejeita 50
(71%).

### 3. A linhagem fiel morre cedo
Réplica instrumentada da seed 42 (`data/base42.json`, reproduz o artefato bit a bit):
`pop_drift_min` vai de 0,0000 (g0–g2, o seed canônico) a 0,17 em **g7** e 0,24 em g20,
quando `dominance` ainda tinha 1,13 dos seus 1,35 pra entregar. Em g20 a população é um
aglomerado de largura 0,045 (min 0,2406 / mediana 0,2861) — não sobrou diversidade de
drift pra recombinar. No NSGA-II isso não acontece: `drift` é objetivo separado e sem
ruído, e o extremo de drift baixo fica protegido no rank 0 pela crowding infinita
(multi-objetivização, Knowles, Watson & Corne 2001).

### 4. Por que o AG não vê a política
`sensitivity_analysis`: piso de ruído medido 0,0346; `w_defend` 0,0288 e
`w_aggressiveness` 0,0300 ficam **abaixo** dele, `w_retreat` 0,0476 é borderline. O
equilíbrio não precifica os pesos — só o `drift` precifica, e o drift é voto vencido.
Resultado: P(avançar) do Rushdown cai de 0,857 (canônico) para 0,413 (AG), contra 0,484
no NSGA-II. `w_aggressiveness` é o gene de maior drift nos três braços.

## Os braços (orçamento da bateria, 300 × 150, sementes 42–46)

**Reavaliação a 1000 lutas/par em 4 sorteios novos** (`data/holdout_1000.json`) — a
200 lutas (`MULTI_RUN_SIMS`) o σ por medição é ~0,02, metade do próprio valor, e ranquear
braços nessa resolução inverte:

| braço | dom | hc | bal | drift | L1+2 | L3 | τ | soma |
|---|---|---|---|---|---|---|---|---|
| AG escalar | 0,0380 | 0,30 | 16/20 | 0,2396 | 12,2 | 2,40 | +0,284 | 0,2776 |
| NSGA-II `so` | 0,0835 | 3,50 | 0/20 | 0,1487 | 15,4 | 4,00 | +0,593 | 0,2322 |
| **`hybrid`** (NSGA-II 75 → AG 75, **orçamento igual**) | **0,0254** | **0,30** | 14/20 | **0,1664** | **15,2** | **4,40** | **+0,551** | **0,1918** |
| `from_nsga` (AG a partir do `scalar_optimum`, **2× orçamento**) | 0,0364 | 0,30 | 15/20 | 0,1492 | 15,0 | 4,00 | +0,606 | 0,1856 |
| `plus` (seleção μ+λ, só sementes 42–43) | — | 0 | 2/2 | 0,209 | 11,5 | 3,0 | +0,381 | — |

`hybrid` contra o AG escalar, por semente: melhor em `dominance` **4/5**, em drift
**5/5**, em τ **5/5**, empate em hard counters (0,30 × 0,30) e em elencos equilibrados
(14/20 × 16/20, dentro do ruído). **Com o mesmo orçamento, ele quase domina o AG.**

`g300` (300 gerações) não chegou a rodar; a trajetória de `base42.json` prevê ~0,19 de
drift, ou seja o dobro do orçamento comprando o que o híbrido compra de graça.

## Conclusão

1. **O trade-off que a bateria reporta é um teto do custo da identidade, não o custo
   real.** Parte do que se lê como "o AG troca identidade por equilíbrio" é falha de
   busca sob avaliação ruidosa.
2. **A escalarização direta é frágil sob avaliação amostrada** quando um dos termos tem
   ruído e o outro não. A decomposição em Pareto age como proteção da linhagem fiel.
3. **O ciclo de vantagens não é realizado — e a métrica mudou de casa.** A contagem a 200
   lutas por par media ruído: margem mediana das arestas 0,048 contra σ = 0,035, e os
   espelhos (estrutura zero por construção) marcavam 5,40/10 "mantidas" com 1,00/10
   decididas. Saiu do `baselines` para `src/experiments/cycle_structure.py` (16 × 1000
   lutas por par, σ = 0,0040, passo 17 da bateria), contando só arestas **decididas**: o AG
   mantém **105 de 186 — 56,5%, binomial p = 0,091**, contra 49,7% dos 30 nulos
   (p = 0,128, Â₁₂ = 0,63). **Indistinguível do acaso**, com inclinação fraca e não
   significativa na direção autoral. E o canônico realiza 6/10 com as 4 arestas que quebra
   **invertidas por completo** (0,000–0,006): hierarquia (1,00 de 5 tríades), não ciclo. A
   estrutura cíclica nunca existiu no motor. O campo `beats` fica: é premissa declarada e a
   parte verificável da não-circularidade.

## Próximos passos

1. **`MULTI_RUN_SIMS = 200` é baixo demais.** A reavaliação custa 10 pares × 200 = 2.000
   lutas por semente, contra 67.500.000 da execução. Subir para 1000 é ~gratuito e
   afia todo número por semente da bateria. **Fazer isso antes de qualquer braço novo.**
2. **Selecionar o híbrido nas sementes 1000–1004**, não nas 42–46. O número acima foi
   medido na amostra da bateria, o que viola o protocolo do projeto ("a amostra que
   escolhe uma configuração não é a que avalia"). Varrer o split (25/50, 50/50, 75/25) e
   o que carregar para a fase 2 (fronteira inteira × `scalar_optimum`).
3. **Só então rodar a bateria (n = 20)** com o braço escolhido e comparar com
   `compare_algorithms`.
4. **Registrar**: `docs/thesis/04` (decisão, formato problema → mudança → resultado),
   `docs/thesis/07` (achado), `docs/thesis/09` (valores), `CLAUDE.md` (Key Design
   Decisions) e `docs/reference/`.

## Arquivos

- `diagnostics/exp_diag.py`: réplica instrumentada do `ga.run` (`survivor=plus`, `gens`,
  `sims`, `init`, `gen_offset`).
- `diagnostics/exp_hybrid.py`: híbrido NSGA-II → AG escalar com orçamento repartido.
- `diagnostics/exp_holdout.py`: reavaliação de qualquer braço a N lutas em sorteios novos.
- `diagnostics/exp_cycle*.py`: os protótipos que viraram
  `src/experiments/cycle_structure.py` — mantidos só como rastro da investigação.
- `diagnostics/exp_noise.py`: ruído do `dominance` por indivíduo (150 e 1000 lutas).
- `diagnostics/exp_score.py`: réguas de identidade nos indivíduos dos braços.
- `diagnostics/summary.py`: a tabela consolidada de todos os braços.
- `diagnostics/per_seed_analysis.py`: arestas do ciclo, drift por personagem e objetivo
  escalar por semente (precisa de `PYTHONPATH=.`).
- `diagnostics/data/*.json`: saídas.

## Já corrigido

- `docs/thesis/07-findings-and-limitations.md` — dizia que o escalar vence na própria
  função (número de uma bateria anterior); agora traz o 20/20 medido.
- `src/analysis/analyze_matchups.py` — a coluna `WR` virou `WR★` com legenda: o número é
  a WR do favorito canônico do par, não a do lado esquerdo.
