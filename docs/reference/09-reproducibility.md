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
| `provenance` | ✓ | ✓ |
| `algorithm`, `seed`, `generations_run` | ✓ | ✓ |
| `history` (uma entrada por geração) | fitness melhor/média/pior + dominance + drift + tempo | tamanhos das frentes + amplitude da frente 0 + tempo |
| condição de parada | `stop_reason`, `converged`, `stagnated` | — (roda `NSGA2_GENERATIONS` fixas) |
| solução | `best_individual` (genes) + `fitness` + `objectives` | `pareto_front` + `representatives` (genes + objetivos) |

Sem `--seed`, o campo `seed` é `null` e a execução **não** é reproduzível — é a
escolha explícita de rodar sob entropia.

### `provenance` — o carimbo que faz um JSON velho se denunciar

**Todos** os artefatos da tabela acima carregam um bloco `provenance`
(`src/engine/provenance.py`), primeiro campo do JSON:

| Chave | O que é |
|---|---|
| `generated_at` | timestamp local com fuso |
| `fingerprint` | hash único de constantes + premissa + motor |
| `config` | **toda** constante pública de `config.py`, valor a valor |
| `archetypes_digest` | genes canônicos + `defining_genes` + `beats` |
| `engine_digest` | digest do código de `src/engine/` |

Por que existe: mexer em `config.py`, nos canônicos ou no motor invalida `results/`
inteiro de uma vez, e sem carimbo um artefato obsoleto é **indistinguível** de um atual
— `git status` fica limpo (o JSON velho segue versionado) e o mtime é o do *checkout*,
não o da geração. Em 2026-09-17 foi assim que três artefatos de `external_validation`
atravessaram uma troca de motor inteira, e o efeito chegou à tabela de resultados como
um número plausível.

Cinco decisões de projeto, cada uma contra um modo de falha:

- **As constantes são enumeradas de `config.py`, não listadas à mão** — uma lista curada
  apodrece em silêncio, e a próxima constante adicionada ficaria invisível ao carimbo.
- **O código do motor entra por digest, não só as constantes** — o incidente não foi
  mudança de constante: `grab_power`, a colisão e a rotação do stream são *código*.
- **`config.py` fica fora do digest de código** porque seus valores vão gravados um a um:
  "`MATCHUP_WR_CAP` foi de 0,15 para 0,20" é acionável, "o hash mudou" não é.
- **`N_WORKERS` não entra** — a avaliação resemeia ao `_SEED_BASE` antes de cada
  round-robin, então o resultado independe de quantos workers avaliam. Carimbá-lo faria
  uma mudança inócua invalidar a bateria, e um alarme que dispara à toa deixa de ser lido.
- **`MULTI_RUN_N_SEEDS` também não** — é só o tamanho da amostra do `multi_run`, que o
  artefato dele grava no corpo (`n_seeds`, `seeds`); nenhum outro artefato depende dela.
  Uma constante excluída nunca diverge, nem num artefato carimbado quando ela ainda
  entrava — senão excluí-la invalidaria a bateria que a exclusão existe para proteger.

**A verificação acontece sozinha.** `Individual.from_results` e `Individual.from_nsga2`
chamam `warn_if_stale` — os dois construtores são o gargalo por onde toda ferramenta
carrega um indivíduo evoluído, então checar num só lugar impede que a próxima tool nasça
sem a checagem. O aviso diz o que mudou, não só que mudou:

```
  ⚠ ARTEFATO OBSOLETO — 'results.json' não descreve o sistema atual:
      · o CÓDIGO do motor mudou desde a geração
      · ACTION_PERSISTENCE_SUBTICKS: 10 → 5
      gerado em 2026-09-17T14:20:14-03:00
```

> ⚠️ **Re-carimbar NÃO é operação segura em massa.** `stamp()` lê os overrides **do
> processo que chama**, então aplicá-lo em lote sobre artefatos existentes reescreve a
> proveniência de todos com a configuração de quem está rodando o lote — e um braço de
> experimento perde exatamente o que o distinguia. Aconteceu em 2026-09-17: um re-carimbo
> em massa apagou o λ dos cinco braços do sweep, e os cinco passaram a afirmar o λ do
> `config.py`. Os dados nunca foram tocados, e a recuperação foi possível porque o **corpo**
> do artefato também carrega a configuração do experimento (`pop_size`, `n_generations`,
> `lambda_drift`, `lambda_dominance`) — é por isso que ela não vive só no carimbo. Regra:
> re-carimbe **um artefato de cada vez**, sob os mesmos overrides que o produziram.

> **Carimbo retroativo: só por reprodução do próprio artefato.** A bateria de 2026-09-17,
> anterior ao módulo, recebeu carimbo retroativo justificado reproduzindo bit a bit
> `results.json` e `nsga2_results.json` e **inferindo** o resto ("função determinística
> desses dois mais o motor"). A inferência falhou num: o `sensitivity_analysis.json` era de
> 2026-09-16, sob persistência 10, e levou o carimbo de atual. A bateria de 2026-09-18 é a
> primeira gerada inteira com o módulo, e nenhum artefato em `results/` carrega mais
> `provenance.backfilled`.

> **O que o carimbo não cobre: argumentos de linha de comando.** Ele grava a configuração do
> motor (`config.py`, canônicos, código), não os flags com que a ferramenta foi chamada.
> Um artefato gerado com `--n-random 8` ou `--n-seeds 10` sai carimbado como atual, porque
> **é** — a config não mudou. A defesa é o default de cada ferramenta ser o valor do
> protocolo e o corpo do artefato gravar os parâmetros da
> execução (`n_random`, `n_seeds`, `sims_per_matchup`). As duas ferramentas da bateria
> seguem a regra: `baselines` com 30 nulos, `multi_run` com 20 sementes.

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
  independente de qual worker a avalia ou do agendamento do `ProcessPoolExecutor`: o
  pool é persistente, e o estado do pai (`RuntimeState` — seed-base, λ, pesos do
  dominance) viaja com **cada tarefa**, então um worker vivo nunca avalia sob o
  seed-base de uma geração anterior.
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
  - **Uma semente por luta** (`fitness.fight_seed(seed_base, par, luta)`, misturada por
    SplitMix64): a luta *k* do par *m* recebe os mesmos sorteios em todo indivíduo
    avaliado sob o mesmo seed-base, não importa quanto as lutas anteriores consumiram.
    Com um stream único por avaliação, a primeira luta que durasse diferente em dois
    indivíduos deslocava a leitura de todas as seguintes, inclusive as de pares idênticos
    nos dois. Medido (roster evoluído × o mesmo com um gene a +σ, 40 seed-bases): num
    par sem o personagem alterado a diferença vai de DP 0,019 a **exatamente 0**, mas a
    diferença de fitness melhora só 1,0–1,3× — o ruído que resta é **dentro** das lutas
    do personagem alterado, onde a trajetória diverge e o resto da luta se desenrola
    diferente. Custo: +13% por avaliação. `test_fitness` cobre o contrato: mudar um gene
    do Zoner deixa os 6 pares sem ele bit a bit iguais.
- **`ga.run`/`nsga2.run`** semeiam `random`, `np.random` e `seed_combat` no início
  e definem o seed-base. Sem seed → entropia (não reprodutível, por escolha).
- **`sensitivity_analysis`** avalia +σ e −σ sob o mesmo seed-base (`set_seed_base`), então
  cada luta dos dois recebe os mesmos sorteios (common random numbers, uma semente por
  luta).
- **`analyze_matchups --seed`** semeia o combate também.

Verificado empiricamente: determinismo por-indivíduo, seeds-base distintos dão
fitness distinta, e paralelo == serial (propagação aos workers) — inclusive com o pool
vivo atravessando trocas de seed-base e de pesos (`test_provenance`).
