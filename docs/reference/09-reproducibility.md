# 09 — Execução e reprodutibilidade

## Ambiente

Dependências pinadas em `requirements.txt`. `numba` é obrigatório — JIT-compila o
loop de combate (~150× sobre Python puro); a primeira chamada compila (~2.5s),
depois fica em cache.

```powershell
.\setup.ps1                 # cria .venv e instala tudo
.\setup.ps1 -Recreate       # apaga .venv e refaz do zero
```

No Windows use `py` (não `python`/`python3`). Scripts emitem Unicode
(box-drawing): via pipe do bash use `PYTHONIOENCODING=utf-8` ou passe `--quiet`.

## Rodar

```bash
py main.py                                      # AG escalar  → results/results.json
py main.py --algorithm nsga2 --seed 42 --quiet  # NSGA-II      → results/nsga2_results.json
```

Tools e tests rodam como módulo a partir da raiz — ver [08-tools.md](08-tools.md).

## Saídas

| Arquivo | Origem |
|---|---|
| `results/results.json` | `py main.py` (AG escalar) |
| `results/nsga2_results.json` | `py main.py --algorithm nsga2` |
| `results/plots/nsga2/<timestamp>/` | plots da fronteira |

## Reprodutibilidade ✅

O `--seed` torna os experimentos reprodutíveis. O combate sorteia com
`np.random.random()` dentro de `@njit`, e o RNG interno do Numba só é semeável de
dentro de um `@njit` — por isso `combat.seed_combat(s)` (uma função `@njit`) é a
única forma correta; `np.random.seed()`/`random.seed()` do Python **não** afetam o
combate.

Como funciona:

- **Semeadura reset-ao-base / Common Random Numbers** (`fitness.set_seed_base`):
  quando há seed, **toda** avaliação reseta o RNG do combate ao mesmo `seed_base`
  antes do round-robin. Todo indivíduo é avaliado sob o mesmo stream de RNG → a
  diferença de fitness reflete **genes, não sorteio** (CRN), tornando a seleção
  menos enganada e a paisagem mais lisa. Reprodutível independente de qual worker
  a avalia ou do agendamento do `ProcessPoolExecutor` (o seed-base é propagado aos
  workers via `initializer`).
  - *Antes:* `crc32(genes) XOR seed_base` (hash-por-genes). Era reprodutível, mas
    congelava o ruído MC numa função descontínua dos genes — cada indivíduo via um
    stream diferente, anulando a redução de variância do CRN.
  - *Caveat conhecido (aceito, não corrigido):* o alinhamento CRN é perfeito só até
    o 1º matchup; como cada luta consome um nº variável de sorteios, a posição do
    stream diverge entre indivíduos nos matchups seguintes. Ainda assim é muito
    melhor que seeds independentes por indivíduo. Alinhamento perfeito exigiria
    semear por `(base, matchup_idx, sim_idx)` — fora de escopo.
- **`ga.run`/`nsga2.run`** semeiam `random`, `np.random` e `seed_combat` no início
  e definem o seed-base. Sem seed → entropia (não reprodutível, por escolha).
- **`sensitivity_analysis`** usa `seed_combat(seed)` no pareamento +σ/−σ → os dois
  compartilham os mesmos sorteios (common random numbers), e a redução de variância
  agora funciona de fato.
- **`analyze_matchups --seed`** semeia o combate também.

Verificado empiricamente: determinismo por-indivíduo, seeds-base distintos dão
fitness distinta, e paralelo == serial (propagação aos workers).
