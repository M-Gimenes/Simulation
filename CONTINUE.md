# Continuar daqui: investigação "o AG escalar perde na própria função"

Sessão de 2026-09-22, interrompida no meio. Os scripts e os dados parciais estão em
`diagnostics/` (fora de `src/`, não são código do projeto e não entram no carimbo de
proveniência). **Ainda não foi anotado em `docs/thesis/`.** Isso fica para quando a
investigação fechar (ver "Próximos passos").

## Achado de partida (a partir dos artefatos da bateria de 2026-09-21)

- **O NSGA-II vence o AG escalar na função do próprio AG** (`dominance + drift`, λ = 1/1):
  - no mesmo stream do laço, a fronteira tem um ponto melhor em **20/20** sementes
    (mediana 0,205 contra 0,266);
  - reavaliado na seed 9999, o `scalar_optimum` vence em **18/20**;
  - com 1000 lutas × 8 streams (sementes 42–46, `data/noise.json`), vence em **5/5**,
    ex.: seed 42 com 0,213 contra 0,272.
- **`docs/thesis/07-findings-and-limitations.md:79` está desatualizado.** Ele diz que o
  escalar "vence na própria função", número de uma bateria anterior. Precisa ser corrigido.
- **Os hard counters do NSGA-II são sistemáticos.** Rushdown > Combo Master é invertido
  em 19/20 sementes e vira hard counter em 14/20; Combo Master > Grappler é mantido em
  só 3/20.
- **No AG, o ciclo fica em 4,8/10**, contra 5,25 no controle λ = 0 e um piso de 5.
- **A identidade se perde na política.** As probabilidades de intenção convergem para
  ~1/3 (a P(avançar) do Rushdown vai de 0,86 para 0,41), e o `grab_power` se espalha
  (Turtle de 0,15 para 0,51).
- **O drift por personagem segue o desequilíbrio do canônico.** Paga mais quem estava
  mais longe de 50%: Rushdown (0,34) e Turtle (0,30).
- **O resumo por matchup do `analyze_matchups` confunde.** A coluna "WR" mostra a WR do
  favorito canônico, não a do lado A. Vale trocar o rótulo.

## Trajetória do drift (`history` do AG + réplica instrumentada)

- **O drift do melhor ainda está caindo na geração 149 em 20/20 sementes.** Mediana:
  0,384 (g0) → 0,276 (g40) → 0,250 (g149), ~0,0003 por geração depois da g40.
- **Fase 1 (g0–30): só o equilíbrio manda.** O `dominance` do melhor vai de 0,68 a 0,03.
- **Colapso da diversidade de drift.** Na réplica instrumentada da seed 42
  (`data/base42.json`, reproduz o artefato bit a bit), o drift mínimo da população vai
  de 0,00 (o canônico) em g0 a **0,24 em g20**. A linhagem de drift baixo morre na fase 1.
  Depois disso a população inteira fica num aglomerado estreito: p10 → mediana do drift
  em ~0,005.
- **Ruído do `dominance` a 150 lutas: desvio de 0,015–0,028 para o mesmo indivíduo**
  (`data/noise.json`). Na fase 2 a seleção escalar vê diferenças de drift com relação
  sinal/ruído de ~0,25, e por isso o drift desce devagar.
- **Hipótese do mecanismo.** No NSGA-II o drift (sem ruído) é um objetivo separado, e o
  extremo de menor drift fica protegido no rank 0 pela crowding infinita, então a
  linhagem fiel nunca morre. É um caso de **multi-objetivização** (Knowles, Watson &
  Corne 2001) sob avaliação ruidosa.

## Intervenções (orçamento da bateria, 300 × 150, sementes 42–46: diagnóstico, não escolha de configuração)

| braço | resultado | estado |
|---|---|---|
| **`from_nsga`**: AG escalar com a população inicial = `scalar_optimum` do NSGA-II + aleatórios | seed 42: dom 0,018 / drift 0,164, 0 counters, equilibrado → **domina o AG (0,031 / 0,236) e o NSGA-II (0,075 / 0,160)**. 3 das 5 sementes terminam equilibradas; soma 0,16–0,21 contra 0,27–0,28 do AG | **completo** (`data/from_nsga.json`) |
| **`plus`**: seleção (μ+λ) no escalar, como a do NSGA-II | seed 42: dom 0,026 / drift 0,222 (soma 0,248 contra 0,267) — melhora pouco | **só seed 42**; faltam 43–46 |
| **`g300`**: 300 gerações | — | **não rodou** |

Leitura provisória: **a região "equilíbrio sem counters + drift baixo" existe, e o AG
escalar consegue se manter nela.** O que falha é a trajetória: a fase 1 mata a linhagem
fiel. A conclusão "a identidade custa equilíbrio" medida pelo AG é, em boa parte, falha
de busca, não trade-off da função. Ressalva: `from_nsga` usa o dobro de orçamento
(NSGA-II 150 + AG 150), então é um híbrido, não uma comparação com orçamento igual.

## Próximos passos

1. **Terminar os braços:**
   ```
   py -m diagnostics.exp_diag plus diagnostics/data/plus.json 43,44,45,46 "{\"survivor\":\"plus\"}"
   py -m diagnostics.exp_diag g300 diagnostics/data/g300.json 42,43,44,45,46 "{\"gens\":300}"
   ```
   Cada execução leva ~2 min (a `plus` ~4 min). `plus` sobrescreve o arquivo: salve a
   seed 42 antes, ou rode as 5 de novo.
2. **Medir a identidade dos braços** (validador, Layer 3, τ):
   `py -m diagnostics.exp_score diagnostics/data from_nsga,plus,g300`. Para comparar, as
   linhas de base das sementes 42–46 (AG e NSGA-II) estão no `multi_run_*.json`.
3. **Testar um híbrido com orçamento igual.** Exemplos: NSGA-II 75 gerações → AG 75, ou
   um AG escalar que proteja a linhagem de drift mínimo (arquivo/elite por drift).
   Selecionar configuração nas sementes 1000–1004 e só depois rodar a bateria.
4. **Decidir se isso muda o método.** Se o híbrido dominar os dois em n = 20, vira
   contribuição: "a escalarização direta perde a linhagem fiel sob ruído; a decomposição
   em Pareto seguida de refino escalar domina os dois". Depois registrar em
   `docs/thesis/04` (decisão), `07` (achado + corrigir a linha 79), `CLAUDE.md` (Key
   Design Decisions) e `docs/reference/`.

## Arquivos

- `diagnostics/exp_diag.py`: réplica instrumentada do `ga.run`, com as variantes
  `survivor=plus`, `gens`, `sims` e `init` (o `from_nsga`).
- `diagnostics/exp_noise.py`: ruído do `dominance` por indivíduo (150 e 1000 lutas).
- `diagnostics/exp_score.py`: réguas de identidade nos indivíduos dos braços.
- `diagnostics/per_seed_analysis.py`: arestas do ciclo, drift por personagem e objetivo
  escalar por semente, a partir dos `multi_run`. Precisa de `PYTHONPATH=.`.
- `diagnostics/data/*.json`: saídas.
