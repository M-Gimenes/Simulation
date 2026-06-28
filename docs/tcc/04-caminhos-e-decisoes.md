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
- **Hesitação reintroduzida e depois removida.** Foi reintroduzida (variância de
  player ponderada pelos pesos, ε pequeno) e mais tarde (2026-06-27) **removida**:
  a revisão mostrou que o combate já tinha ruído de sobra (a soft-policy dispara
  muito) e que o determinismo estava no **desfecho**, não na falta de ruído. Manter
  uma 2ª fonte estocástica só adicionava um hiperparâmetro a calibrar sem retorno
  claro. **Estado atual:** a única fonte de estocasticidade é o **sorteio de
  intenção** (mantido por `ACTION_PERSISTENCE_SUBTICKS`).
- **Modelo de combate simplificado para intenção → execução (2026-06-27).**
  Problema: o modelo tinha 4 prioridades hierárquicas + hesitação, e genes
  (`defense`, `recovery`) cujo efeito era difícil de calibrar. Mudança: cada tick
  vira **(1) sorteio de uma intenção** (`FRENTE/RECUAR/GUARDA`, ponderada pelos
  pesos, quando em range) e **(2) execução** dela; `defense` e `recovery` removidos;
  `stun` virou **fração** do cooldown do atacante. Resultado: menos parâmetros,
  invariantes garantidas por bound (stun < cooldown) e identidade ainda expressa
  pelos pesos. Estado atual em [`../reference/04-combat-model.md`](../reference/04-combat-model.md).

## Calibração das mecânicas (fechar exploits do AG)

- **Bounds apertados.** Problema: o AG explorava o espaço para vencer de formas
  degeneradas. Mudança: HP reduzido (eliminou "tanque absurdo"), knockback 5→3
  (zoning trivial por expulsão). Resultado: cada aperto fechou um modo de exploit.
  *(Os bounds de `defense` e `recovery` deixaram de existir quando esses genes foram
  removidos — abaixo.)*
- **`defense` e `recovery` removidos (2026-06-27).** Problema: dois genes cujo efeito
  era difícil de tornar visível à seleção sem platôs de arredondamento (recovery
  drifou pro piso — era evolutivamente neutro), e que adicionavam dimensões ao
  cromossomo sem ganho claro de identidade. Mudança: dano virou **flat** (só DEFEND
  reduz) e o stun bruto é aplicado direto. Resultado: modelo mais enxuto (7
  atributos), sem o gene neutro.
- **Stun: cap explícito → fração do cooldown.** Problema: stun ≈ cooldown gerava
  perma-lockdown (vencer por travar o oponente, não por dano). Solução inicial: um
  `STUN_CAP_MULTIPLIER = 0.6` capando o stun. Mudança final (2026-06-27): representar
  o `stun` **diretamente como fração** do cooldown do atacante (∈ [0, 0.6]) — a
  invariante "stun < cooldown" passa a ser garantida pelo **bound do gene**, sem
  constante de cap. Resultado: sempre há janela livre entre hits, com um parâmetro a
  menos.
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
  A objeção original ao WR (bimodal) deixou de valer: o sorteio de intenção o torna
  graduado.
- **Reformulação C2 — WR global em vez de por-matchup (2026-06-27, a correção mais
  recente):** Problema: o primário "WR por-matchup" tem como ótimo *todo par a 50%* —
  equilíbrio **plano**, que por construção é **incompatível com o ciclo de vantagens**
  (um ciclo exige que pares tenham vencedor). O objetivo, portanto, **forçava** a
  quebra do ciclo, e atribuí-la a "mecânicas omitidas" estaria errado para o indivíduo
  balanceado. Observação que originou a correção: a WR sempre quis medir o **global do
  boneco** (50% global é compatível com vencer 2 e perder 2). Mudança: o primário
  virou a **WR global por personagem** (`|WR_global − 0.5|`, RMS sobre os 5), mais um
  **teto de hard-counter** (`MATCHUP_WR_CAP`, mantém arestas como vantagens dentro de
  `[0.30, 0.70]`) e a decisividade inalterada. Resultado: o ciclo passa a ser
  **expressável**; "ele emerge das identidades preservadas?" vira o achado real, e C2
  é robusto ao próprio fracasso (se o plano dominar mesmo com espaço, é achado honesto,
  não artefato). Interpretação em [03](03-formulacao-do-fitness.md) e
  [02](02-ciclo-canonico.md). **Pesos/cap provisórios — a calibrar.**

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
