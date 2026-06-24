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

- **Semeadura determinística por-indivíduo** (`fitness.set_seed_base`): quando há
  seed, cada avaliação semeia o combate a partir de `crc32(genes) XOR seed_base`.
  A fitness vira função determinística dos genes — reprodutível independente de
  qual worker a avalia ou do agendamento do `ProcessPoolExecutor` (o seed-base é
  propagado aos workers via `initializer`). Bônus: a reavaliação do mesmo
  indivíduo não tem ruído.
- **`ga.run`/`nsga2.run`** semeiam `random`, `np.random` e `seed_combat` no início
  e definem o seed-base. Sem seed → entropia (não reprodutível, por escolha).
- **`sensitivity_analysis`** usa `seed_combat(seed)` no pareamento +σ/−σ → os dois
  compartilham os mesmos sorteios (common random numbers), e a redução de variância
  agora funciona de fato.
- **`analyze_matchups --seed`** semeia o combate também.

Verificado empiricamente: determinismo por-indivíduo, seeds-base distintos dão
fitness distinta, e paralelo == serial (propagação aos workers).
