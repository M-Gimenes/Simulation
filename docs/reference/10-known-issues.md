# 10 — Pontos em aberto

O que **ainda está aberto** no sistema: as pendências e os limites conhecidos, para que
nenhum deles seja descoberto por acidente na hora de escrever. Não é histórico — a
trajetória das decisões (que problema cada mudança resolveu) vive em
[`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md), e o estado atual
do sistema nos docs 01–09.

---

## 1. Pendências acionáveis

**Nenhuma aberta.** A última — «o AG escalar não é ótimo na própria função», aberta em
2026-09-22 — foi **fechada em 2026-09-23** pela adoção do braço híbrido.

Em resumo: `dominance` é amostrado e `drift` não, e depois da geração ~31 a seleção
escalar gasta a pressão em ruído; a linhagem de drift mínimo morre na geração 7. Repartir
o **mesmo** orçamento entre uma fase de Pareto e uma escalar recupera a identidade sem
custo em equilíbrio — drift 0,1663 contra 0,2473 e τ +0,5215 contra +0,2811 (efeito
grande), com `dominance` e hard-counters imóveis (Â₁₂ 0,51 e 0,49). Achado e números em
[`../thesis/07-findings-and-limitations.md`](../thesis/07-findings-and-limitations.md),
decisão em [`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md).

Sobrou uma **pergunta declarada, não uma pendência**: qual o melhor split. O 0,5 veio do
desempate de simplicidade do critério de escolha, porque no sweep em orçamento reduzido
nenhum braço passou no filtro de equilíbrio e a ordenação entre splits não transferiu.
Afirmar que 0,5 é o melhor exigiria um sweep no orçamento inteiro — o que está medido é
que **este** split não cobra equilíbrio pela identidade que entrega.

**Fechada em 2026-09-22: o ciclo autoral era medido numa resolução em que não funcionava.**
`cycle_edges_kept` e `circular_triads` saíram do `baselines` (200 lutas por par, onde a
direção de cada aresta de um roster equilibrado é sorteio) para
`src.experiments.cycle_structure`, que roda 16 × 1000 lutas por par, conta só arestas
**decididas** e compara grupos pela taxa. É o passo 17 da bateria. Achado e números em
[`../thesis/07-findings-and-limitations.md`](../thesis/07-findings-and-limitations.md);
decisão em [`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md), «O ciclo
saiu do `baselines`».

O resto da instrumentação está fechado: a bateria de 2026-09-21 rodou sobre o motor atual (CRN por luta,
timers com resto acumulado) e o protocolo completo (os dois controles, manchete no
`scalar_optimum` com relação de Pareto, concordância de ranking, validação externa com
regras perturbadas, sensibilidade nos 11 genes, validador com empate contra a asserção,
digest de medição). `py -m src.tests.test_provenance` sai com tudo *atual* ou *braço de
experimento*, os artefatos órfãos foram tirados do git, e os números de
[`../status/HANDOFF.md`](../status/HANDOFF.md) §2, do `docs/thesis/` e do `CLAUDE.md` são
os dela.

Fora essa, não há pendência de instrumentação. O que resta é **redação**
([`../status/HANDOFF.md`](../status/HANDOFF.md) §4).

**Os cinco consertos adiados foram feitos em 2026-09-22/23**, junto da re-execução que o
braço híbrido exigiu — era exatamente a condição que eles esperavam ("a próxima mudança
que já exija re-rodar"). Ficam registrados aqui porque a razão de terem esperado é a
lição, não o conserto em si: **editar `src/engine/` troca o `engine_digest` e marca todo o
`results/` como obsoleto**, e nenhum deles mudava um número de execução com semente.

> **Isso deixou de ser argumento e virou medição (2026-09-23).** Comparados gene a gene
> contra a bateria anterior, **40 de 40 execuções com semente** — 20 do AG escalar e 20 do
> NSGA-II — produziram indivíduos **bit a bit idênticos**. Nenhum número de identidade
> mudou na re-execução; o que mudou foi só o que `MULTI_RUN_SIMS` mede. Ver
> [`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md), «A política de
> adiar conserto inerte foi verificada».

1. **`ga.run(seed=None)` e `nsga2.run(seed=None)` não reavaliavam os elites** — a
   invalidação estava dentro do `if seed is not None`, então um elite com avaliação de
   sorte nunca regredia à média. Corrigido: a invalidação vale com e sem semente.
2. **`archetypes.NUM_ARCHETYPES` era constante morta** — removida.
3. **O docstring de `_confirm_convergence`** dizia `seed + CONVERGENCE_SEED_OFFSET` quando
   o código usa o stream da geração corrente + o offset — mais forte do que o texto dizia.
4. **`src/analysis/analyze_matchups.py` misturava medição e impressão** dentro do digest
   de medição da bateria, e trocar o texto de uma legenda obsoletava `multi_run`,
   `baselines` e a validação externa de uma vez. *(Pendente: a extração ainda não foi
   feita — ver abaixo.)*
5. **`MULTI_RUN_SIMS` 200 → 1000** — a 200 o desvio do `dominance` de um mesmo roster é
   0,015–0,028, da ordem do próprio valor evoluído. Feito.

**Ainda aberto (item 4):** separar medição de impressão no `analyze_matchups`. As funções
que medem identidade (`behavioral_profile`, `BEHAVIORAL_KEYS`, `expected_winner`,
`wilson_ci`) continuam no mesmo módulo das que imprimem as tabelas do CLI, então **nenhuma
edição cosmética nesse arquivo é segura** — ela obsoleta a bateria. O conserto é extrair as
funções de medição para um módulo sem impressão. Junto dele vai a coluna `WR` do resumo
por matchup, que mostra a WR do favorito canônico do par e não a do lado esquerdo, e cujo
rótulo ainda engana.

Se o motor ou o `config.py` mudarem de novo, a sequência é a de sempre: rodar
`.\scripts\run_overnight.ps1` (os 16 braços de sweep nas sementes 1000–1004, depois a
bateria de 17 passos), conferir com `py -m src.tests.test_provenance` e reler cada número
contra a bateria nova — §3 detalha.

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
  é uma corrida de DPS quase determinística e a resposta é íngreme. Na sensibilidade de
  2026-09-21, uma janela de 2σ de mutação move a WR média em `range` **30,8%**, `damage`
  26,2%, `attack_cooldown` 25,7% e `hp` 23,9%, contra um piso de ruído de 3,5% — sinal
  sobre ruído de 7× a 9×, uma ordem de grandeza acima dos genes de política. E
  **30 dos 30 rosters aleatórios** dos modelos nulos têm ao menos um par saturado (WR fora
  de [5%, 95%]). O AG lida bem com a inclinação, mas gradiente forte com solução
  potencialmente frágil é a descrição correta do regime; amortecer (variância no dano,
  mais sims) é trabalho futuro.
- **A política é o que o AG menos enxerga pelo equilíbrio.** Na sensibilidade da bateria
  de 2026-09-21 (11 genes, janela 2σ, piso medido em 3,5%), **os três pesos ocupam o fundo
  do ranking**: `w_defend` 2,9% e `w_aggressiveness` 3,0% abaixo do piso, `w_retreat` 4,8%
  no limiar — ao lado de `knockback` 4,3% e `speed` 3,5% —, contra `range` 30,8% no topo.
  O único gradiente que puxa a política de volta ao canônico é o do drift, e o controle
  `λ_drift = 0` mostra o que acontece sem ele: τ = +0,007, o acaso. A análise é local, e
  muda com o indivíduo.
- **O drift pesa as cinco identidades com exigência diferente.** `defining_genes` tem 1
  gene no Combo Master e 4 na Turtle; com peso 3,0 nos definidores e a RMS normalizada
  pela soma, isso é 23% do peso num caso e 63% no outro. O `drift_penalty` de dois
  personagens não é, a rigor, a mesma régua — comparar drift **entre** arquétipos exige
  essa ressalva.
- **O piso da sensibilidade é o máximo das nulas, e depende de quantas.** Com
  `--null-reps 3` são 33 nulas e o piso (3,5%) fica perto do percentil 97; com mais
  réplicas ele subiria, e genes no limiar (`speed`, `knockback`, `w_retreat`) poderiam
  mudar de classe. A escolha do máximo é deliberada (conservadora), mas o número só é
  citável com o `reps` ao lado.
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

> ✅ **`results/` está COMPLETO e ATUAL** — os números são os da bateria de 2026-09-21
> com **n = 20**, sobre o motor e o protocolo atuais.

**Regra:** ao mexer em `config.py`, nos canônicos ou no motor, todo `results/` fica
obsoleto **de uma vez**; ao mexer no código de uma ferramenta de medição, ficam obsoletos
os artefatos que dependem dela. O carimbo de proveniência
([09-reproducibility.md](09-reproducibility.md)) *detecta* um artefato fora de data, não
o regenera, e a bateria inteira precisa rodar de novo antes de qualquer número voltar a
ser citável:

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
