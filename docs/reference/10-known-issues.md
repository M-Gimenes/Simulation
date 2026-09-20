# 10 — Pontos em aberto

O que **ainda está aberto** no sistema: as pendências e os limites conhecidos, para que
nenhum deles seja descoberto por acidente na hora de escrever. Não é histórico — a
trajetória das decisões (que problema cada mudança resolveu) vive em
[`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md), e o estado atual
do sistema nos docs 01–09.

---

## 1. Pendências acionáveis

**Uma só: rodar a bateria.** Depois da bateria de 2026-09-18 o motor mudou (CRN por luta,
timers com resto acumulado) e o protocolo também (controles, manchete no
`scalar_optimum` com relação de Pareto, concordância de ranking, validação externa com
regras perturbadas, sensibilidade nos 11 genes, validador com empate contra a asserção,
digest de medição). Até a próxima bateria, `results/` lê "obsoleto" e os números citados
em `docs/status/HANDOFF.md` §2, no `docs/thesis/` e no `CLAUDE.md` são de antes. Sequência:

1. `.\scripts\run_overnight.ps1` — os 16 braços de sweep (sementes 1000–1004) e a bateria
   completa de 16 passos, com os dois controles (~6h12 a bateria, ~1h40 os sweeps).
2. `py -m src.tests.test_provenance` — tudo deve sair como *atual* ou *braço de
   experimento*.
3. Tirar do git os artefatos que a bateria nova **não** regrava, porque o nome ou o destino
   mudou: os 16 braços antigos de `results/exploratory/` (sem `seed1000` no nome),
   `results/multi_run/comparison_ga_vs_nsga2_scalar_optimum.json` (o `scalar_optimum`
   virou a manchete, e o secundário agora é `_best_dominance`),
   `results/external_validation/external_validation_nsga2_best_dominance.json` (a bateria
   valida o `scalar_optimum` e o `knee_point`) e o diretório de plot da fronteira anterior
   em `results/single_run/plots/`.
4. Reler cada resultado contra a bateria nova: as tabelas do HANDOFF §2, os achados do
   `thesis/` — em especial os **preliminares** de 2026-09-18 (identidade funcional no
   piso, política invisível ao equilíbrio) —, os números do `CLAUDE.md` e as conclusões
   dos três sweeps (joelho em λ = 1,0, secundários indispensáveis, elitismo 10% /
   torneio 3). E ler, pela primeira vez, as duas comparações contra os controles.

Não há pendência de instrumentação.

## 2. Limites estruturais do método (decisões, não bugs)

Nenhum destes é defeito de implementação — são fronteiras do que o sistema mede.
Precisam aparecer explicitamente na Discussão, não só em Trabalhos Futuros.

- **O equilíbrio é condicionado a uma política fixa.** Os pesos `w_*` *são* a
  política: os personagens não aprendem, e ninguém procura exploits contra o roster
  evoluído. Se existir uma estratégia dominante que a política sorteada não visita, o
  equilíbrio medido não a enxerga. É o item 2.1 (coevolução) de
  [`../thesis/08-literature-methods.md`](../thesis/08-literature-methods.md),
  decidido como trabalho futuro — decisão legítima, mas **é a objeção mais forte ao
  resultado**.
- **A política é cega ao estado.** A intenção não depende de HP, distância, cooldown
  do oponente nem de o oponente estar stunado: "estratégia" no modelo é uma mistura fixa
  de três posturas, mantida por `ACTION_PERSISTENCE_SUBTICKS`. É o commitment pretendido,
  mas nenhum arquétipo tem plano.
- **Crossover só por bloco de personagem.** Recombinação de genes *dentro* de um
  personagem depende 100% da mutação; o crossover só troca personagens inteiros entre
  indivíduos. Limita a exploração fina do espaço.
- **Round-robin uniforme.** Todos os 10 pares pesam igual. Não modela matchmaking
  real (jogadores escolhendo matchups favoráveis), então "equilíbrio" aqui é
  equilíbrio sob confronto uniforme.
- **Genes de recurso são hipersensíveis.** Com o ataque como regra de resolução, a luta
  é uma corrida de DPS quase determinística e a resposta é íngreme em espelho —
  amplitude a ±1σ de mutação: `range` **92,5%**, `attack_cooldown` 65,1%, `damage` 55,5%,
  `hp` 43,6%; 71% dos matchups de indivíduos **aleatórios** ficam saturados (WR fora de
  [5%, 95%]). O AG lida bem com a inclinação, mas gradiente forte com solução
  potencialmente frágil é a descrição correta do regime; amortecer (variância no dano,
  mais sims) é trabalho futuro.
- **A política é o que o AG menos enxerga pelo equilíbrio.** Na sensibilidade com o passo
  da mutação (preliminar, no evoluído da bateria anterior), `w_retreat` e `w_defend` ficam
  abaixo do piso de ruído, `w_aggressiveness`, `speed` e `knockback` no limiar. O único
  gradiente que puxa a política de volta ao canônico é o do drift. A análise é local, e
  muda com o indivíduo.
- **As réguas funcionais não são independentes do fitness.** A Layer 3 e a concordância de
  ranking são *held-out* — o fitness não referencia comportamento —, mas cada asserção da
  Layer 3 é consequência quase direta de um gene definidor. E a Layer 3 são 5 bits; a
  concordância existe para dar resolução, não independência.
- **O pareamento CRN acaba dentro da luta.** Com uma semente por luta, dois indivíduos
  recebem os mesmos sorteios em cada luta; mas quando um gene muda o que acontece numa
  luta, o resto dela se desenrola diferente e os sorteios seguintes caem em estados
  diferentes. É o ruído que sobra na comparação, e é por isso que semear por luta melhorou
  o sinal só 1,0–1,3×. Sincronizar os sorteios por instante (sub-tick × lado) atacaria
  isso, com ganho não medido; fica como trabalho futuro.
- **Os sweeps rodam em orçamento reduzido** (pop 120 × 60 gerações, ~16% do custo, 5
  sementes por braço). O que se pede deles é **ordenar configurações do mesmo algoritmo**,
  e essa ordenação transfere de orçamento; número citável e comparação **entre
  algoritmos** não transferem — o projeto tem um contraexemplo medido, em que a ordem AG ×
  NSGA-II inverte entre pop 120 e pop 300. E a n = 5, diferenças pequenas entre braços não
  se separam do ruído: os sweeps estabelecem o que é indispensável e o que nada supera,
  não ótimos.

## 3. Estado dos artefatos em `results/`

> ⚠️ **`results/` está COMPLETO, mas OBSOLETO** — ver §1. Os números são os da bateria
> de 2026-09-18 com **n = 20**; a próxima bateria os **substitui**.

**Regra:** ao mexer em `config.py`, nos canônicos ou no motor, todo `results/` fica
obsoleto **de uma vez**; ao mexer no código de uma ferramenta de medição, ficam obsoletos
os artefatos que dependem dela. O carimbo de proveniência
([09-reproducibility.md](09-reproducibility.md)) *detecta* um artefato fora de data, não
o regenera, e a bateria inteira precisa rodar antes de qualquer número ser citado:

```bash
py -m src.experiments.multi_run --algorithm both            # multi_run_{ga,nsga2}.json
py -m src.experiments.compare_algorithms                      # comparison_ga_vs_nsga2.json (scalar_optimum)
py -m src.experiments.compare_algorithms --nsga2-representative best_dominance
py -m src.experiments.multi_run --algorithm ga --lambda-drift 0      # controls/
py -m src.experiments.multi_run --algorithm ga --no-canonical-seed   # controls/
py -m src.experiments.compare_algorithms --control results/controls/multi_run_ga_drift0_dom1.json
py -m src.experiments.compare_algorithms --control results/controls/multi_run_ga_unseeded.json
py main.py --seed 42                                    # single_run/ga.json
py main.py --algorithm nsga2 --seed 42                  # single_run/nsga2.json + plots
py -m src.experiments.external_validation                     # canônico
py -m src.experiments.external_validation --evolved           # AG escalar
py -m src.experiments.external_validation --nsga2 scalar_optimum
py -m src.experiments.external_validation --nsga2 knee_point
py -m src.experiments.sensitivity_analysis --evolved          # sensitivity_analysis.json
py -m src.experiments.baselines --evolved                     # baselines.json
```

`run_battery.ps1` é essa bateria, em passos retomáveis (`-From N`) — cada passo salva seu
artefato, porque o `multi_run` não tem resume. `-WhatIf` lista os passos e o custo. Os
sweeps (`run_sweeps.ps1`) vêm **antes** dela: implementar um braço mexe no motor, e os 16
braços compartilham o braço default para sair do mesmo digest.

**Verificação pós-bateria:** `py -m src.tests.test_provenance` lista o estado de cada
artefato. Os braços do sweep e os controles devem sair como *braço de experimento*, o resto
como *atual*; qualquer *obsoleto* significa que algo mudou no meio da bateria.

Três armadilhas que já morderam:

- **A `external_validation` regenera só o rótulo que recebe.** Rodar os quatro rótulos,
  sempre — um deles já atravessou uma troca de motor inteira e acabou numa tabela
  comparando o AG de uma bateria com o NSGA-II de outra. Desde 2026-09-18 ela recusa um
  `single_run/*.json` obsoleto, então esse caminho específico fecha com erro.
- **Carimbo retroativo por inferência.** Só vale reproduzindo o próprio artefato; um
  artefato já levou o carimbo de atual sem ter sido regerado.
- **Default de ferramenta mais barato que o protocolo.** O carimbo registra a config, não
  os argumentos de linha de comando. Os defaults de `baselines` (30 nulos) e `multi_run`
  (20 sementes) são o protocolo por isso, e o `multi_run` grava fora do caminho da bateria
  qualquer execução com amostra ou sims fora do protocolo.

## 4. Encerrado (para não reabrir por engano)

Resolvido e verificado; o raciocínio e os números estão em
[`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md).

**Fitness e critérios:**

- `specialization_penalty` removido — escalar e NSGA-II otimizam os mesmos 2 eixos.
- Objetivo só-decisividade era cego à WR — a WR voltou como termo primário.
- WR por-matchup forçava equilíbrio plano, incompatível com o ciclo — substituída pela WR
  **global** por personagem (formulação C2).
- `LAMBDA_DRIFT` 6,0 → 1,0, e o sweep de λ confirmou 1,0 como o joelho da curva.
- Drift normalizado pelo range do bound e ponderado pelos `defining_genes`; invariante à
  escala dos pesos comportamentais (`fitness.drift_genes`).
- `MATCHUP_FLOOR` 0,10 → 0,02: o piso de decisividade virou guarda de degenerescência.
- Pesos 1,0 / 0,5 / 0,5 do dominance mantidos: os secundários são carga estrutural.
- `MATCHUP_WR_CAP = 0,15` mantido, ancorado na grade de matchup da FGC.
- Gate de convergência = o próprio predicado `roster_balanced`, com confirmação num stream
  que o AG nunca viu.
- Orçamento fixo nos dois algoritmos; convergência é evento registrado. O evento de
  estagnação foi removido (media a catraca do ruído sob a rotação do stream).
- Família de Holm montada pela variância da amostra conjunta; `_holm` recusa `nan`.
- Piso da sensibilidade medido sob hipótese nula, com `--evolved` / `--nsga2`.
- Modelos nulos (`baselines.py`) dão piso, teto, posição e p-valor a toda métrica post-hoc.
- Validação externa: replicação e robustez a regras perturbadas, cada uma com 5000 lutas
  por par e veredito pelo IC contra a banda.
- Validador: empate conta contra a asserção; pesos comparados como probabilidade de
  intenção. Concordância de ranking comportamental (τ) como régua funcional contínua.
- Sensibilidade nos 11 genes, janela de 2σ que desliza para dentro do bound, piso na
  mesma estatística do ranking.
- Representantes geométricos do NSGA-II (joelho, ideal) com objetivos normalizados; o
  ideal mede a distância ao ponto utópico.
- Hipervolume com referência ancorada nos modelos nulos, (1,3; 0,4).
- Controles na bateria: AG com `λ_drift = 0` e AG sem semente canônica.
- Manchete da comparação: `scalar_optimum`, com a relação de Pareto por semente; família
  de Holm fixa, de 7 métricas, a mesma em toda comparação.
- `MATCHUP_FLOOR = 0,02` mantido, com a justificativa corrigida (a defesa contra a solução
  trivial é o drift).

**Motor de combate:**

- Reforma de 2026-09-10 (avanço incondicional, ataque exclusivo, atravessamento, stun
  arredondado), empate como terceiro desfecho e regra de impasse — números em
  [11-combat-review.md](11-combat-review.md).
- Simplificação: fora `defense`, `recovery` e hesitação; `stun` é fração do cooldown.
- `grab_power`: o eixo Recurso ganhou counter, o Grappler ganhou assinatura na Layer 3.
  *Segue como pergunta para a bateria:* se o AG realiza a aresta "Grappler vence Turtle"
  **por mérito** — no canônico ela vale, mas o Turtle canônico perde para todos.
- `ACTION_PERSISTENCE_SUBTICKS` 10 → 5 (1 tick = o período do atacante mais rápido).
- Timers com resto acumulado: período do cooldown exato em média (era um sub-tick acima do
  nominal) e stun contínuo em média (era `ceil`, com 4 níveis em cooldown 1).
- Regras do combate como estado de processo (`CombatRules`), levadas aos workers.
- Canônicos declarados finais.

**Protocolo e infraestrutura:**

- Stream de avaliação rotacionado por geração (`generation_seed`), nos dois laços.
- CRN com uma semente por luta (`fight_seed`).
- n = 20 sementes, default do `multi_run`, fora do carimbo.
- Elitismo 10% / torneio 3 testados e mantidos.
- Carimbo de proveniência em todo artefato, com aviso de obsoleto ao carregar, recusa de
  entrada obsoleta em quem grava um artefato a partir de outro, e digest do código de
  medição por artefato.
- `multi_run` roteia por todo desvio do protocolo: bateria, `controls/` ou `exploratory/`.
- Sementes dos sweeps (1000+) disjuntas das da bateria (42+).
- Marcos de convergência (`converged_at`, contadores do gate) por semente no `multi_run`.
- Pool de processos persistente, com o estado do pai viajando em cada tarefa.
- `compare_algorithms`: Mann-Whitney U + Â₁₂ + Holm-Bonferroni.
