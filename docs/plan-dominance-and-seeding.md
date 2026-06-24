# Plano — Redesenho do `dominance_penalty` + semeadura CRN

> Doc de execução. Lista o que mudar, onde, e como validar. Apagar (ou mover para
> `docs/reference/`) depois de executado e documentado.

## Motivação (resumo)

O commit `3738396` trocou o `dominance_penalty` de **balanço de win rate** (`|WR − 0.5|`,
medido sobre o resultado binário de cada luta) para **decisividade por-luta** (margem
de HP do vencedor, banda `[0.05, 0.10]`). A nova métrica é **cega à frequência de
vitória**: um matchup em que um lado vence 100% das vezes fechando sempre com ~15% de
HP dá `decisividade ≈ 0.075` → dentro da banda → penalidade **zero**.

Sintoma (empírico, `report --nsga2 best_dominance`): `dominance_penalty = 0.0000`,
10/10 lutas "sadias", mas **0/10 matchups equilibrados** (Grappler 92%, Turtle 8%). O
NSGA-II minimizou o objetivo corretamente — o objetivo é que não corresponde mais a
equilíbrio.

A hipótese de design ("luta apertada em HP ⟹ WR ~50%") está **falsificada**: um
personagem pode vencer consistentemente por margem fina (luta apertada, vencedor
determinístico). A justificativa histórica para abandonar a WR ("jogo determinístico
não chega a 50%") não vale mais — soft-policy + `HESITATION_RATE` tornam a WR graduada,
logo com gradiente.

## Decisões travadas

1. **Trazer o balanço de WR de volta como termo PRIMÁRIO** do `dominance_penalty`.
2. **Manter a decisividade como termo SECUNDÁRIO** (qualidade de luta / guarda contra
   blowout-coinflip), com peso menor.
3. **WR contínuo** (`|WR − 0.5| / 0.5`, sem banda morta) — gradiente liso até 50%.
   **Decisividade mantém a banda** `[MATCHUP_FLOOR, MATCHUP_THRESHOLD]`.
4. **Manter 2 objetivos no NSGA-II** — combinar os dois termos dentro de
   `dominance_penalty`; a fronteira continua 2D `(dominance, drift)`.
5. **Trocar o seed hash-por-genes por reset-ao-base** (Common Random Numbers): mesma
   reprodutibilidade, paisagem mais lisa, comparações entre indivíduos com menos ruído.

---

## Mudança 1 — `dominance_penalty` (WR primária + decisividade secundária)

### Fórmula
Por matchup `(i, j)`:

```
wr_excess   = |WR_ij − 0.5| / 0.5                                  # contínuo, ∈ [0, 1]
decis_over  = max(0, D_ij − MATCHUP_THRESHOLD) / (0.5 − MATCHUP_THRESHOLD)
decis_under = max(0, MATCHUP_FLOOR − D_ij) / MATCHUP_FLOOR
decis_excess = decis_over + decis_under                            # ∈ [0, 1]

e_ij = DOMINANCE_WR_WEIGHT * wr_excess + DOMINANCE_DECIS_WEIGHT * decis_excess

dominance_penalty = sqrt( mean_over_10( e_ij² ) )
```

- `D_ij` = decisividade já computada (`matchup_decisiveness`, `_fight_score`).
- `WR_ij` = win rate direta já computada (`matchup_winrates`).
- Os dois dicts **já existem** em `_run_round_robin` — sem custo de simulação extra.

### `config.py`
Adicionar (na seção "Função de fitness", junto de `MATCHUP_THRESHOLD`/`FLOOR`):

```python
# Pesos dos dois componentes do dominance_penalty (ver docs/plan-... / 05-GA).
# WR é o objetivo primário de balanceamento (|WR-0.5| contínuo); a decisividade é
# regularizador secundário de qualidade de luta (guarda contra blowout-coinflip:
# 50% A esmaga / 50% B esmaga → WR 50% mas toda luta um massacre).
DOMINANCE_WR_WEIGHT = 1.0
DOMINANCE_DECIS_WEIGHT = 0.5
```

### `fitness.py`
- `_dominance_penalty(...)` passa a receber **os dois** dicts:
  `_dominance_penalty(matchup_winrates, matchup_decisiveness)`.
- Importar `DOMINANCE_WR_WEIGHT`, `DOMINANCE_DECIS_WEIGHT` do config.
- Atualizar a chamada em `evaluate_detail_n` (`fitness.py:192`).
- Manter `_fight_score` e `matchup_decisiveness` (decisividade ainda é usada).
- Atualizar o docstring do módulo e da função.

Esboço:
```python
def _dominance_penalty(matchup_winrates, matchup_decisiveness):
    over_scale = 0.5 - MATCHUP_THRESHOLD
    excesses = []
    for key in matchup_decisiveness:
        wr = matchup_winrates[key]
        d  = matchup_decisiveness[key]
        wr_excess   = abs(wr - 0.5) / 0.5
        decis_over  = max(0.0, d - MATCHUP_THRESHOLD) / over_scale
        decis_under = max(0.0, MATCHUP_FLOOR - d) / MATCHUP_FLOOR
        e = DOMINANCE_WR_WEIGHT * wr_excess + DOMINANCE_DECIS_WEIGHT * (decis_over + decis_under)
        excesses.append(e)
    return math.sqrt(sum(e * e for e in excesses) / len(excesses))
```

### Consequências a observar
- A **escala** do `dominance_penalty` muda → o trade-off do AG escalar (`LAMBDA_DRIFT`
  vs `LAMBDA_DOMINANCE`, hoje 1.0/1.0) e os valores absolutos da fronteira mudam.
  Não recalibrar às cegas; rodar primeiro e ver onde cai.
- O `best_dominance` deixará de chegar a 0.0 com WR desequilibrado — esse é o objetivo.

---

## Mudança 2 — Semeadura CRN (reset-ao-base em vez de hash-por-genes)

### O que muda em `fitness.py`
- Em `evaluate_detail_n` (`fitness.py:177-178`), trocar:
  ```python
  if _SEED_BASE is not None:
      seed_combat(_seed_for(individual))
  ```
  por:
  ```python
  if _SEED_BASE is not None:
      seed_combat(_SEED_BASE)
  ```
- **Remover** `_seed_for(individual)` (`fitness.py:56-61`) e o `import zlib`.
- Manter `set_seed_base` / `get_seed_base` / `_SEED_BASE` e o `initializer` do
  `ProcessPoolExecutor` (`fitness.py:242-243`) — a reprodutibilidade por-worker continua.

### Por que
- **Mantém** reprodutibilidade independente de worker/ordem (todo indivíduo reseta ao
  mesmo `_SEED_BASE` antes do round-robin).
- **Recupera Common Random Numbers**: indivíduos avaliados sob o mesmo stream de RNG →
  a diferença de fitness reflete genes, não sorteio → seleção menos enganada e paisagem
  mais lisa (o hash-por-genes congelava o ruído MC numa função descontínua dos genes).
- **Caveat conhecido (documentar, não corrigir agora):** o alinhamento CRN é perfeito
  só até o 1º matchup; como cada luta consome um nº variável de sorteios, a posição do
  stream diverge entre indivíduos nos matchups seguintes. Ainda assim é muito melhor que
  seeds independentes por indivíduo. Alinhamento perfeito exigiria semear por
  `(base, matchup_idx, sim_idx)` — fora de escopo deste plano.

---

## Ordem de execução

1. `config.py`: adicionar `DOMINANCE_WR_WEIGHT`, `DOMINANCE_DECIS_WEIGHT`.
2. `fitness.py`: reescrever `_dominance_penalty` (2 dicts) + atualizar chamada e imports.
3. `fitness.py`: aplicar a Mudança 2 (seed reset-ao-base, remover `_seed_for`/`zlib`).
4. Rodar smoke tests: `py -m src.tests.test_fitness` e `py -m src.tests.test_nsga2`.
5. Reexecutar:
   ```
   py main.py --seed 42 --quiet                    # GA escalar
   py main.py --algorithm nsga2 --seed 42 --quiet  # NSGA-II
   ```
6. Inspecionar:
   ```
   py -m src.tools.report --evolved
   py -m src.tools.report --nsga2
   py -m src.tools.report --nsga2 best_dominance
   py -m src.tools.report --nsga2 ideal_point
   ```
   **Critério de sucesso:** `best_dominance` agora tem mais matchups dentro de 40-60% de
   WR (coluna WR-bal) — a penalidade não é mais satisfeita por vitórias finas
   consistentes. Aceitar que `dominance_penalty` mudou de escala.

## Docs a atualizar (mesma tarefa, antes de encerrar — instrução do CLAUDE.md)

- `CLAUDE.md` — seção **Key Design Decisions** ("Two fitness terms" / descrição do
  `dominance_penalty`) e o resumo do combate (a métrica agora é WR primária + banda de
  decisividade secundária). Atualizar também a lista de hiperparâmetros "mais ajustados".
- `docs/reference/05-genetic-algorithm.md` — nova fórmula do `dominance_penalty`.
- `docs/reference/06-nsga2.md` — objetivo `dominance` redefinido.
- `docs/reference/07-configuration.md` — `DOMINANCE_WR_WEIGHT`, `DOMINANCE_DECIS_WEIGHT`.
- `docs/reference/09-reproducibility.md` — semeadura agora é reset-ao-base (CRN), não
  hash-por-genes; registrar o caveat de alinhamento.
- `docs/reference/11-combat-review.md` — registrar que a hipótese "luta apertada ⟹ WR
  ~50%" foi falsificada (evidência: `best_dominance` antigo) e por isso a WR voltou ao
  fitness.
- `docs/reference/10-known-issues.md` — fechar/atualizar o item correspondente.

## Em aberto (calibrar depois, não bloqueia)

- Valor de `DOMINANCE_DECIS_WEIGHT` (0.5 é chute inicial — ver se a decisividade some ou
  domina na fronteira).
- `HESITATION_RATE` (já marcado PROVISÓRIO no config) — revisitar junto, já que agora a
  WR volta a ser objetivo direto e a estocasticidade que graduava a WR fica mais crítica.
