# 04 — Caminhos e decisões de design

**Entra em**: Metodologia (justificativa das escolhas) e Discussão.

> A **trajetória** das decisões — que problema cada mudança resolveu. Não é a
> descrição do estado atual (isso é [`../04-combat-model.md`](../reference/04-combat-model.md) e
> [`../05`](../reference/05-genetic-algorithm.md)); é o **raciocínio** que levou até ele.
> Mostrar essa evolução evidencia que o sistema foi refinado para fechar problemas
> concretos, não montado arbitrariamente.

Cada item: **problema → mudança → resultado.**

## Estocasticidade do combate

- **Variância de dano e ação aleatória uniforme, removidas.** Problema: `DAMAGE_VARIANCE`
  (±20%/hit) e `ACTION_EPSILON` (ação uniforme aleatória/tick) eram **ruído operacional**
  — afogavam o sinal das mutações abaixo do piso de ruído binomial, e a ação uniforme
  ignorava os pesos (um Turtle "atacava à toa"). Mudança: removidas; a única fonte de
  estocasticidade passou a ser a **soft-policy** (escolha ponderada pelos pesos).
  Resultado: cada peso ganhou efeito contínuo e mensurável.
- **Princípio destilado:** estocasticidade só onde modela **incerteza estratégica**
  (a escolha do jogador), não ruído de execução.
- **Hesitação reintroduzida (depois).** Problema: querer um "fator de player" sem
  recair no ruído uniforme. Mudança: hesitação **ponderada pelos mesmos pesos**, com ε
  pequeno. Resultado: variância de player que respeita a identidade. *Nuance da
  revisão:* o combate já tinha bastante ruído (a soft-policy dispara muito); o
  determinismo estava no **desfecho**, não na falta de ruído — então a hesitação é
  menos crítica do que se pensava (ver [07](07-achados-e-limitacoes.md)).

## Calibração das mecânicas (fechar exploits do AG)

- **Bounds apertados.** Problema: o AG explorava o espaço para vencer de formas
  degeneradas. Mudança: HP 500→400 (eliminou "tanque acima do Turtle"), defense
  0.5→0.30 (defesa absurda), knockback 5→3 (zoning trivial por expulsão), recovery
  float→inteiro `[0,10]` (stun-immunity). Resultado: cada aperto fechou um modo de
  exploit específico.
- **Stun cap < 1.0** (`STUN_CAP_MULTIPLIER = 0.6`). Problema: stun ≈ cooldown gerava
  perma-lockdown (vencer por travar o oponente, não por dano). Mudança: stun
  estritamente menor que o cooldown do atacante. Resultado: sempre há uma janela livre
  entre hits — quebra o lock degenerado.
- **Recovery: multiplicativo → inteiro subtrativo.** Problema: a forma `stun × (1 −
  recovery)` criava platôs de arredondamento — mutações pequenas eram invisíveis ao
  AG. Mudança: inteiro que subtrai sub-ticks diretamente. Resultado: efeito visível por
  unidade de gene.
- **`TICK_SCALE`.** Problema: timers discretos (cooldown ∈ {1..5}) criavam platôs no
  landscape de fitness. Mudança: resolução sub-tick. Resultado: landscape mais suave.

## Reprodutibilidade (achado de auditoria)

- **Problema:** o combate sorteia com `np.random` **dentro do JIT (Numba)**, cujo RNG é
  independente do `np.random` do Python — então semear no Python (como se fazia) **não
  reproduzia** nada, e o pareamento de seeds da análise de sensibilidade estava
  silenciosamente quebrado. Mudança: `seed_combat()` (`@njit`) + **reset ao seed-base
  (Common Random Numbers)** — toda avaliação reseta o RNG do combate ao mesmo seed-base.
  Resultado: experimentos com `--seed` reprodutíveis, e todo indivíduo avaliado sob o
  mesmo stream → a diferença de fitness reflete genes, não sorteio (paisagem mais lisa).
  *(Uma versão intermediária semeava por hash-dos-genes — reprodutível, mas dava a cada
  indivíduo um stream diferente, anulando o CRN; substituída.)* Detalhe em
  [05](05-validacao-metodologica.md) e [`../09`](../reference/09-reproducibility.md).

## A reformulação do objetivo (a decisão maior)

- **Problema:** com combate quase-determinístico, o WR é **bimodal** (0/1). Otimizar WR
  = otimizar um objetivo sem gradiente; além disso, "ganhar 55% sempre com 100% de
  vida" não é uma luta equilibrada — é um coin-flip entre dois blowouts.
- **Caminho A (margem):** trocar o objetivo de WR para **decisividade por-luta numa
  banda** — dá gradiente mesmo no determinismo e recompensa lutas *apertadas* (não
  blowout nem decididas no fio).
- **Caminho B (variância de player):** a hesitação, para que o desfecho deixe de ser
  determinístico.
- **Por que os dois (A habilita B):** a revisão mostrou que o ruído já existente não
  flipa desfechos porque as lutas são blowouts; quando o **A** aproxima as lutas, o
  ruído **passa** a flipar → WR graduado emerge. Então A é a alavanca; B é
  complemento/realismo. Interpretação completa em [03](03-formulacao-do-fitness.md).
- **Correção (A sozinho não bastou — hipótese falsificada):** medindo o `best_dominance`
  do NSGA-II com o objetivo só-decisividade, ele dava `dominance_penalty = 0` e 10/10
  lutas na banda, mas **0/10 matchups equilibrados** (Grappler 92%, Turtle 8%). A
  decisividade é **cega à frequência de vitória** — um lado pode vencer sempre por
  margem fina. A hipótese "luta apertada ⟹ WR ~50%" foi **falsificada**. Mudança: a WR
  voltou como termo **primário** do `dominance_penalty` (`|WR−0.5|/0.5` contínuo), com a
  decisividade rebaixada a regularizador **secundário** (guarda contra blowout-coinflip).
  Resultado: `best_dominance` passou a ~8/10 matchups em 40-60% de WR. A objeção original
  ao WR (bimodal) deixou de valer: soft-policy + hesitação o tornam graduado.

## Pesos do fitness

- **`LAMBDA_DRIFT` 6.0 → 1.0.** Problema: com 6.0, mover-se para equilibrar custava ~6×
  o ganho em dominância — o AG escalar ficava **preso ao canônico** (drift ≈ 0) e
  desbalanceado (achado V1). Mudança: 1.0, igual ao dominance. Resultado: o AG é livre
  para usar o objetivo reformulado; e fica **simétrico ao NSGA-II** (que não pondera).
- **`specialization_penalty` removido.** Problema: media spread *intra*-personagem, não
  diferenciação *entre* arquétipos (cinco builds idênticos passariam) — não fazia o que
  o nome diz, era redundante com o drift, e dava ao escalar um 3º termo que o NSGA-II
  não tem. Mudança: removido. Resultado: o AG escalar otimiza **os mesmos dois eixos do
  NSGA-II**; "os 5 ainda são distintos?" virou métrica **post-hoc** (diferenciação
  par-a-par), não termo forçado — coerente com a não-circularidade do ciclo.
