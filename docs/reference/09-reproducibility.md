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
| `results/multi_run/multi_run_<algo>.json` | `py -m src.tools.multi_run` |
| `results/multi_run/comparison_ga_vs_nsga2.json` | `py -m src.tools.compare_algorithms` |
| `results/external_validation/external_validation_<label>.json` | `py -m src.tools.external_validation` |
| `results/sensitivity/sensitivity_analysis.json` | `py -m src.tools.sensitivity_analysis` |

### O que cada artefato de execução registra

Os dois algoritmos gravam o **mesmo contrato** (`ga.save_results` e
`nsga2.save_results`): o que basta para reproduzir a execução e reconstruir a
trajetória sem re-rodar.

| Campo | `results.json` (AG) | `nsga2_results.json` |
|---|---|---|
| `algorithm`, `seed`, `generations_run` | ✓ | ✓ |
| `history` (uma entrada por geração) | fitness melhor/média/pior + dominance + drift + tempo | tamanhos das frentes + amplitude da frente 0 + tempo |
| condição de parada | `stop_reason`, `converged`, `stagnated` | — (roda `NSGA2_GENERATIONS` fixas) |
| solução | `best_individual` (genes) + `fitness` + `objectives` | `pareto_front` + `representatives` (genes + objetivos) |

Sem `--seed`, o campo `seed` é `null` e a execução **não** é reproduzível — é a
escolha explícita de rodar sob entropia.

## Reprodutibilidade ✅

O `--seed` torna os experimentos reprodutíveis. O combate sorteia com
`np.random.random()` dentro de `@njit`, e o RNG interno do Numba só é semeável de
dentro de um `@njit` — por isso `combat.seed_combat(s)` (uma função `@njit`) é a
única forma correta; `np.random.seed()`/`random.seed()` do Python **não** afetam o
combate.

Como funciona:

- **Semeadura reset-ao-base / Common Random Numbers** (`fitness.set_seed_base`):
  quando há seed, **toda** avaliação reseta o RNG do combate ao mesmo `seed_base`
  antes do round-robin. Todo indivíduo de uma mesma geração é avaliado sob o mesmo
  stream de RNG → a diferença de fitness reflete **genes, não sorteio** (CRN),
  tornando a seleção menos enganada e a paisagem mais lisa. Reprodutível
  independente de qual worker a avalia ou do agendamento do `ProcessPoolExecutor`
  (o seed-base é propagado aos workers via `initializer`).
- **O stream MUDA a cada geração** (`fitness.generation_seed(base, geração)` =
  `base × GENERATION_SEED_STRIDE + geração`), e é a fonte única do protocolo,
  consumida pelos **dois** algoritmos. O CRN vale **dentro** da geração, não através
  delas. Motivo: com `set_seed_base` chamado uma vez só, todas as gerações corriam
  sobre **uma** realização do RNG, e a população tinha o orçamento inteiro para se
  ajustar a ela — medido, o `dominance` de dentro do laço saía 4,14× melhor que o de
  streams inéditos. Com a rotação a razão cai para 2,20 (5/5 sementes, Wilcoxon
  p = 0,0312) e o roster equilibrado sobrevive a stream inédito em 4,8 de 5 casos
  contra 2,6 (também 5/5, p = 0,0312). É o mesmo princípio que já governava a
  confirmação de convergência: CRN serve para **seleção**, não para validação — nem
  para deixar a busca inteira fitar um stream só.
  - *Custo:* quem sobrevive foi medido no stream anterior e tem de ser reavaliado —
    ~1,8× no AG escalar (os elites) e **~2× no NSGA-II**, onde a ordenação por
    dominância compara pais e filhos no mesmo conjunto combinado e objetivos de
    streams diferentes não são comparáveis.
  - *Famílias de sementes, sem colisão:* treino 42+ → streams 42000+; validação do
    `multi_run` 9999; validação externa 10000+; confirmação de convergência
    `generation_seed + 100000`.
  - *Consequência declarada:* o fitness flutua entre gerações por troca de stream,
    então o contador de estagnação reseta por ruído e **`stagnated_at` fica menos
    confiável**. `converged_at` não sofre — a convergência testa o predicado
    `roster_balanced`, não o valor do fitness.
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
