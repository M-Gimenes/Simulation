# 09 — Execução e reprodutibilidade

## Ambiente

Dependências pinadas em `requirements.txt`. `numba` é obrigatório — JIT-compila o
loop de combate (~150× sobre Python puro); a primeira chamada compila (~2.5s),
depois fica em cache.

```powershell
.\scripts\setup.ps1                 # cria .venv e instala tudo
.\scripts\setup.ps1 -Recreate       # apaga .venv e refaz do zero
```

No Windows use `py` (não `python`/`python3`). Scripts emitem Unicode
(box-drawing): via pipe do bash use `PYTHONIOENCODING=utf-8` ou passe `--quiet`.

## Rodar

```bash
py main.py                                      # AG escalar  → results/single_run/ga.json
py main.py --algorithm nsga2 --seed 42 --quiet  # NSGA-II      → results/single_run/nsga2.json
```

Tools e tests rodam como módulo a partir da raiz — ver [08-tools.md](08-tools.md). A
bateria completa e os sweeps rodam pelos scripts da raiz (`run_battery.ps1`,
`run_sweeps.ps1`, `run_overnight.ps1`) — ver o `README.md`.

## Saídas

| Arquivo | Origem |
|---|---|
| `results/single_run/ga.json` | `py main.py` (AG escalar) |
| `results/single_run/nsga2.json` | `py main.py --algorithm nsga2` |
| `results/single_run/plots/<timestamp>/` | plots da fronteira |
| `results/multi_run/multi_run_<algo>.json` | `py -m src.experiments.multi_run` (a bateria) |
| `results/controls/multi_run_ga_<desvio>.json` | braços de controle (amostra e orçamento do protocolo, um fator de desenho trocado) |
| `results/exploratory/multi_run_ga_<desvios>.json` | braços de sweep (`run_sweeps.ps1`) |
| `results/multi_run/comparison_ga_vs_nsga2.json` | `py -m src.experiments.compare_algorithms` (manchete: `scalar_optimum` + relação de Pareto) |
| `results/multi_run/comparison_ga_vs_nsga2_<rep>.json` | `py -m src.experiments.compare_algorithms --nsga2-representative <rep>` |
| `results/controls/comparison_ga_vs_<braço>.json` | `py -m src.experiments.compare_algorithms --control <artefato>` |
| `results/external_validation/external_validation_<label>.json` | `py -m src.experiments.external_validation` |
| `results/sensitivity/sensitivity_analysis.json` | `py -m src.experiments.sensitivity_analysis` |
| `results/baselines/baselines.json` | `py -m src.experiments.baselines` |

### O que cada artefato de execução registra

Os dois algoritmos gravam o **mesmo contrato** (`ga.save_results` e
`nsga2.save_results`): o que basta para reproduzir a execução e reconstruir a
trajetória sem re-rodar.

| Campo | `single_run/ga.json` (AG) | `single_run/nsga2.json` |
|---|---|---|
| `provenance` | ✓ | ✓ |
| `algorithm`, `seed`, `generations_run` | ✓ | ✓ |
| `history` (uma entrada por geração) | fitness melhor/média/pior + dominance + drift + tempo | tamanhos das frentes + amplitude da frente 0 + tempo |
| marcos | `stop_reason`, `converged_at`, `convergence_gate_fired`, `convergence_rejected` | — (orçamento fixo, sem critério de convergência) |
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
| `measurement` | só nos artefatos das ferramentas de `src/experiments/`: o módulo da ferramenta, os módulos de medição que ela usa e o digest do código deles |
| `overrides` | só em braços de experimento: o valor usado e o do `config.py` |

Por que existe: mexer em `config.py`, nos canônicos ou no motor invalida `results/`
inteiro de uma vez, e sem carimbo um artefato obsoleto é **indistinguível** de um atual
— `git status` fica limpo (o JSON velho segue versionado) e o mtime é o do *checkout*,
não o da geração. A falha não aparece como erro, aparece como um número plausível.

Seis decisões de projeto, cada uma contra um modo de falha:

- **As constantes são enumeradas de `config.py`, não listadas à mão** — uma lista curada
  apodrece em silêncio, e a próxima constante adicionada ficaria invisível ao carimbo.
- **O código do motor entra por digest, não só as constantes** — mudança de motor é, em
  geral, *código*, e um carimbo só de constantes diria "atual" com o motor diferente.
- **`config.py` fica fora do digest de código** porque seus valores vão gravados um a um:
  "`MATCHUP_WR_CAP` foi de 0,15 para 0,20" é acionável, "o hash mudou" não é.
- **O código de medição entra por artefato.** Um número post-hoc — o placar do validador,
  a posição entre piso e teto, o veredito da validação externa — sai de código fora do
  motor. Cada ferramenta passa o próprio módulo ao `stamp(tool=...)`, e o carimbo guarda
  o digest dele e de todo módulo de `src/` fora de `src/engine/` que ele importa,
  transitivamente (`provenance.measurement_modules`, derivado das importações — não uma
  lista à mão). Mudar as asserções do validador invalida o `baselines.json` e o
  `multi_run`, e só eles. O preço: uma mudança cosmética num módulo de medição também
  invalida os artefatos que dependem dele.
- **`N_WORKERS` não entra** — cada luta é semeada a partir do seed-base, então o resultado
  independe de quantos workers avaliam. Carimbá-lo faria uma mudança inócua invalidar a
  bateria, e um alarme que dispara à toa deixa de ser lido.
- **`MULTI_RUN_N_SEEDS` também não** — é só o tamanho da amostra do `multi_run`, que o
  artefato dele grava no corpo (`n_seeds`, `seeds`); nenhum outro artefato depende dela.
  Uma constante excluída nunca diverge, nem num artefato carimbado quando ela ainda
  entrava.

**A verificação acontece sozinha.** `Individual.from_results` e `Individual.from_nsga2`
chamam `warn_if_stale` — os dois construtores são o gargalo por onde toda ferramenta
carrega um indivíduo evoluído, então checar num só lugar impede que a próxima tool nasça
sem a checagem. O aviso diz o que mudou, não só que mudou:

```
  ⚠ ARTEFATO OBSOLETO — 'single_run/ga.json' não descreve o sistema atual:
      · o CÓDIGO do motor mudou desde a geração
      · ACTION_PERSISTENCE_SUBTICKS: 10 → 5
      gerado em 2026-09-17T14:20:14-03:00
```

Um **braço de experimento** (sweep ou controle) não é artefato obsoleto:
`Divergence.is_experiment_arm` vale quando a divergência é inteiramente explicada pelos
`overrides` que o próprio artefato declarou. Qualquer diferença fora disso (motor,
canônicos, código de medição, outra constante) o devolve a obsoleto.
`py -m src.tests.test_provenance` lista o estado de todo artefato em `results/`.

**Ler avisa; gravar recusa.** Quem só inspeciona um artefato (`report`, `analyze_matchups`,
viewers) recebe o aviso e segue. Quem **grava** um artefato novo a partir de outro —
`compare_algorithms` a partir dos `multi_run`; `external_validation`, `baselines` e
`sensitivity_analysis` a partir de `single_run/*.json` — chama `provenance.refuse_if_stale`
(via `require_current=True` nos construtores de `Individual`), que levanta
`StaleArtifactError`. O motivo: o artefato novo sai carimbado com a configuração
**vigente**; aceitar entrada de outra configuração produziria um número de outro sistema
que se declara atual, e o aviso impresso na leitura não fica no arquivo. Um controle é
aceito pelo `compare_algorithms` (`allow_experiment_arm=True`) quando a divergência é
exatamente o override que ele declara.

Três regras de operação, cada uma aprendida com uma falha registrada no
[thesis/04](../thesis/04-design-decisions.md):

- **Re-carimbar é operação de um artefato por vez**, sob os mesmos overrides que o
  produziram: `stamp()` lê os overrides do processo que chama, então aplicado em lote
  reescreve a proveniência de todos com a configuração de quem roda o lote. É também por
  isso que a configuração do experimento (`pop_size`, `n_generations`, `lambda_drift`,
  `lambda_dominance`, `selection`) vai gravada no **corpo** do artefato, e não só no carimbo.
- **Carimbo retroativo só por reprodução do próprio artefato**, nunca por inferência
  ("é função determinística de outros dois"). Na prática, regerar é rodar a bateria.
- **O carimbo não cobre argumentos de linha de comando.** Um artefato gerado com
  `--n-random 8` ou `--n-seeds 10` sai carimbado como atual, porque a config não mudou. A
  defesa é o default de cada ferramenta ser o valor do protocolo (`baselines` com 30
  nulos, `multi_run` com 20 sementes) e o corpo do artefato gravar os parâmetros da
  execução (`n_random`, `n_seeds`, `sims_per_matchup`).

## Reprodutibilidade

O `--seed` torna os experimentos reprodutíveis. O combate sorteia com
`np.random.random()` dentro de `@njit`, e o RNG interno do Numba só é semeável de
dentro de um `@njit` — por isso `combat.seed_combat(s)` (uma função `@njit`) é a
única forma correta; `np.random.seed()`/`random.seed()` do Python **não** afetam o
combate.

Como funciona:

- **Common Random Numbers, uma semente por luta** (`fitness.set_seed_base` +
  `fitness.fight_seed`): quando há seed-base, cada luta do round-robin é semeada por
  `fight_seed(seed_base, par, luta)` (misturado por SplitMix64). A luta *k* do par *m*
  recebe os mesmos sorteios em todo indivíduo avaliado sob o mesmo seed-base, não importa
  quanto as lutas anteriores consumiram → a diferença de fitness reflete **genes, não
  sorteio**, e a seleção é menos enganada. `test_fitness` cobre o contrato: mudar um gene
  do Zoner deixa os 6 pares sem ele bit a bit iguais. O pareamento acaba **dentro** da
  luta: quando um gene muda o que acontece nela, o resto da luta se desenrola diferente —
  é o ruído que sobra (ver [10-known-issues.md](10-known-issues.md) §2).
- **Reprodutível independente do paralelismo.** O pool de processos é persistente, e o
  estado do pai (`RuntimeState` — seed-base, λ, pesos do dominance e as regras do combate)
  viaja com **cada tarefa**, então um worker vivo nunca avalia sob o seed-base de uma
  geração anterior nem sob as regras de outra condição. Verificado: paralelo == serial,
  inclusive com o pool vivo atravessando trocas de seed-base, de pesos e de regras
  (`test_provenance`).
- **O stream MUDA a cada geração** (`fitness.generation_seed(base, geração)` =
  `base × GENERATION_SEED_STRIDE + geração`), e é a fonte única do protocolo,
  consumida pelos **dois** algoritmos. O CRN vale **dentro** da geração, não através
  delas: sem a troca, a população teria o orçamento inteiro para se ajustar a **uma**
  realização do RNG. É o mesmo princípio da confirmação de convergência — CRN serve para
  **seleção**, não para validação. Medições em [thesis/04](../thesis/04-design-decisions.md).
  - *Custo:* quem sobrevive foi medido no stream anterior e tem de ser reavaliado —
    ~1,8× no AG escalar (os elites) e **~2× no NSGA-II**, onde a ordenação por
    dominância compara pais e filhos no mesmo conjunto combinado e objetivos de
    streams diferentes não são comparáveis.
  - *Famílias de sementes, sem colisão:* bateria 42+ → streams 42000+; sweeps 1000+ →
    streams 1000000+ (disjuntas da bateria: a amostra que escolhe uma configuração não é
    a que a avalia); validação do `multi_run` 9999; validação externa 10000+;
    confirmação de convergência `generation_seed + 100000`.
  - *Consequência declarada:* o fitness flutua entre gerações por troca de stream, e por
    isso não há evento de estagnação (o "melhor fitness histórico" seria o máximo de
    valores ruidosos). `converged_at` não sofre — a convergência testa o predicado
    `roster_balanced`, não o valor do fitness.
- **`ga.run`/`nsga2.run`** semeiam `random`, `np.random` e `seed_combat` no início
  e definem o seed-base. Sem seed → entropia (não reprodutível, por escolha).
- **`sensitivity_analysis`** avalia os dois lados da janela sob o mesmo seed-base
  (`set_seed_base`), então cada luta dos dois recebe os mesmos sorteios.
- **O combate é determinístico dado o sorteio de intenção.** Cooldown e stun viram
  sub-ticks inteiros por difusão de erro (resto acumulado), sem segundo gerador — ver
  [04-combat-model.md](04-combat-model.md#timers).
- **`analyze_matchups --seed`**, `fingerprint` e a Layer 3 do validador semeiam o combate
  uma vez (`seed_combat`) e rodam as lutas em sequência: medem comportamento de **um**
  roster, sem comparação pareada entre indivíduos.
