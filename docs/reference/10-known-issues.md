# 10 — Pontos em aberto

O que **ainda está aberto** no sistema, em 2026-09-17 — depois de fechar a agenda de
calibração ([`../../REVIEW.md`](../../REVIEW.md) §9) e regenerar a bateria completa sob o
motor final. Não é histórico: a trajetória das decisões (que problema cada mudança
resolveu) vive em [`../tcc/04-caminhos-e-decisoes.md`](../tcc/04-caminhos-e-decisoes.md),
e o estado atual do sistema nos docs 01–09. Aqui ficam só as pendências e os limites
conhecidos, para que nenhum deles seja descoberto por acidente na hora de escrever.

---

## 1. Pendências acionáveis

O que **poderia ser feito e não foi** — separado dos limites estruturais da §2, que são
escopo declarado e não pendência.

### 1.1 Experimentos decididos ou levantados, nunca executados

| Experimento | Estado |
|---|---|
| **Sweep de `LAMBDA_DRIFT`** | nunca feito; o mais urgente da lista |
| **Pesos 1,0 / 0,5 / 0,5 dos três termos do dominance** | nunca variados |
| **`MULTI_RUN_N_SEEDS`: n = 20** | **decidido** com curva de poder, rodando em 10 |
| **Elitismo 10% + torneio 3** | nunca variados ("valores usuais") |

O **sweep de `LAMBDA_DRIFT`** é o que sustentaria a afirmação de que o AG escalar é *um
ponto* do trade-off que o NSGA-II mapeia — hoje isso é afirmado, não medido. E a medição
de orçamento igual (pop 120, 150 gerações, 80 sims, seed 42) mostra que a afirmação, na
forma literal, é **falsa**: o escalar chega a `dominance` 0,0088 / drift 0,2856
(L1 0,2945), abaixo de toda a faixa da fronteira ([0,0346, 0,9585]), então ele fica
**fora** dela — passado o extremo de baixa dominância, não sobre ele (domina 3 de 49
pontos; nenhum o domina). Ao mesmo tempo o `scalar_optimum` da fronteira chega a L1
**0,2115**, ou seja o NSGA-II vence na função que o escalar otimiza. Cada algoritmo
alcança uma parte diferente do trade-off e nenhum está sub-convergido — é essa a leitura
honesta, e o sweep é o que a transformaria numa curva em vez de dois pontos.

O instrumento para comparar configurações já existe e não precisa ser construído:
**hipervolume por configuração** ([06-nsga2.md](06-nsga2.md)), `multi_run` para agregar N
execuções e `compare_algorithms` para o teste estatístico ([08-tools.md](08-tools.md)).
O que falta é rodar. Ao comparar escalar × NSGA-II o representante usado precisa ser
declarado (o `multi_run` grava `nsga2_representative`, default `best_dominance`); o
comparável correto para o escalar é o `scalar_optimum`, não o `ideal_point` (L2).

**Sobre o n = 20:** a decisão está fechada com evidência — simulação de poder com 4000
réplicas, dois normais separados por 1,190σ (a separação que produz Â₁₂ = 0,80), critério
Holm com família 3, dá **44,4%** de poder a n = 10 contra **85,9%** a n = 20. Com os 10
atuais o experimento tem menos de 50% de chance de detectar um efeito **grande** que
provavelmente existe. Não foi executado por custo: `multi_run` **não tem resume**, então
`--n-seeds 20` re-roda as 20 (~180 min, não +90). É aditivo no sentido estatístico — as
sementes 42–51 são determinísticas e nada do que já foi medido se perde.

### 1.2 Instrumentação

Os dois itens que estavam aqui — carimbo de proveniência nos artefatos e marcos de
convergência por semente — foram **fechados em 2026-09-17**; ver §4. O que resta:

- **O pool de processos é recriado a cada geração.** `fitness.evaluate_population` (e o
  equivalente no `nsga2.py`) instancia um `ProcessPoolExecutor` novo por geração, então o
  custo de spawn escala com o nº de workers. Medido nesta máquina, uma geração de 300
  indivíduos: 1w 4,56s | 4w 1,66s | **8w 1,28s** | 12w 1,41s | 16w 1,62s | 20w 1,91s |
  28w 2,77s. Com o default (`None` → 28 núcleos) os processos carregando llvmlite
  estouravam o limite de commit do Windows (`WinError 1455`), daí `N_WORKERS = 8` fixo —
  valor **específico desta máquina**. Um pool persistente teria ganho provável grande, mas
  exige propagar mudanças de `_SEED_BASE` para workers vivos: plumbing de
  reprodutibilidade, e a rotação do stream por geração torna isso mais delicado, não menos.

## 2. Limites estruturais do método (decisões, não bugs)

Nenhum destes é defeito de implementação — são fronteiras do que o sistema mede.
Precisam aparecer explicitamente na Discussão, não só em Trabalhos Futuros.

- **O equilíbrio é condicionado a uma política fixa.** Os pesos `w_*` *são* a
  política: os personagens não aprendem, e ninguém procura exploits contra o roster
  evoluído. Se existir uma estratégia dominante que a política sorteada não visita, o
  equilíbrio medido não a enxerga. É o item 2.1 (coevolução) de
  [`../tcc/08-metodologias-da-literatura.md`](../tcc/08-metodologias-da-literatura.md),
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
  virou uma corrida de DPS quase determinística e a resposta é íngreme em espelho —
  amplitude a ±1σ de mutação: `range` **92,5%**, `attack_cooldown` 65,1%, `damage` 55,5%,
  `hp` 43,6%; 71% dos matchups de indivíduos **aleatórios** ficam saturados (WR fora de
  [5%, 95%]). O contraponto é medido: o AG lida bem com a inclinação — leva o
  `dominance_penalty` de 1,236 a 0,250 com os 5 bonecos em WR global [48,7%, 52,0%] e
  espalhamento real por par. Gradiente forte com solução potencialmente frágil é a
  descrição correta do regime; amortecer (variância no dano, mais sims) é trabalho futuro.
- **O veredito da validação externa é binário.** O roster só é ROBUSTO se **nenhum** par
  virar hard-counter em **nenhuma** das 10 condições — 100 oportunidades de falhar. Está
  declarado como escolha conservadora, e na bateria de 2026-09-17 ele **discrimina**: o AG
  escalar passa limpo (0/10 pares) e o `best_dominance` do NSGA-II reprova por um único
  par. O que um quantificador fracionário ("par fora da banda em > X% das condições")
  mudaria é o **relato**, não o veredito — o par que reprova o `best_dominance` sai fora em
  **9 das 10** condições (Grappler × Turtle, 63,6%–69,0%), então qualquer limiar razoável
  reprova igual. O ganho da fração seria distinguir um par consistentemente fora de um par
  que escapa uma vez por acaso; hoje os dois casos são relatados do mesmo jeito.
- **Alinhamento CRN imperfeito depois do 1º matchup.** Toda avaliação reseta o RNG do
  combate ao mesmo seed-base, mas cada luta consome um número variável de sorteios —
  a posição do stream diverge entre indivíduos nos matchups seguintes. Muito melhor
  que seeds independentes; alinhamento perfeito exigiria semear por
  `(base, matchup_idx, sim_idx)`. Detalhe em
  [09-reproducibility.md](09-reproducibility.md).

## 3. Estado dos artefatos em `results/`

> ✅ **`results/` está ATUAL e COMPLETO** — bateria de 2026-09-17, sob o motor final
> (rotação do stream por geração, `ACTION_PERSISTENCE_SUBTICKS = 5`, drift invariante à
> escala dos pesos), com os quatro rótulos de `external_validation` fechados no mesmo
> corte. Números no [`../../HANDOFF.md`](../../HANDOFF.md) §3.

**Regra que continua valendo:** ao mexer em `config.py`, nos canônicos ou no motor, todo
`results/` fica obsoleto **de uma vez** — não há versionamento parcial (§1.2) — e a
bateria inteira precisa rodar antes de qualquer número ser citado. A bateria completa:

```bash
py main.py --seed 42                                    # results.json
py main.py --algorithm nsga2 --seed 42                  # nsga2_results.json + plots
py -m src.tools.multi_run --algorithm both              # multi_run_{ga,nsga2}.json
py -m src.tools.compare_algorithms                      # comparison_ga_vs_nsga2.json
py -m src.tools.external_validation                     # canônico
py -m src.tools.external_validation --evolved           # AG escalar
py -m src.tools.external_validation --nsga2 best_dominance
py -m src.tools.external_validation --nsga2 knee_point
py -m src.tools.sensitivity_analysis --evolved          # sensitivity_analysis.json
py -m src.tools.baselines --evolved                     # baselines.json
```

Levou 1h24 na última vez.

> ⚠️ **A pegadinha que já mordeu.** A `external_validation` regenera **só o rótulo que
> recebe**. Na primeira passada da bateria de 2026-09-17 só `_nsga2_best_dominance` foi
> rodado, e os outros três atravessaram uma troca de motor inteira sem que nada acusasse:
> `git status` limpo (os JSONs velhos seguem versionados) e mtime recente (é do checkout,
> não da geração). O efeito não foi cosmético — a tabela de degradação do `HANDOFF` acabou
> comparando o AG de uma bateria com o NSGA-II de outra. Fechado rodando os quatro, e a
> **causa-raiz** foi fechada no mesmo dia pelo carimbo de proveniência (§4): hoje um
> artefato fora de data se denuncia ao ser carregado. Rodar os quatro rótulos continua
> sendo a prática certa — o carimbo detecta, não regenera.

## 4. Encerrado (para não reabrir por engano)

Resolvido e verificado; o raciocínio completo está em
[`../tcc/04-caminhos-e-decisoes.md`](../tcc/04-caminhos-e-decisoes.md).

**Fitness e critérios (2026-09-16):**

- **`specialization_penalty` removido** — não media diferenciação entre arquétipos e
  quebrava a simetria com o NSGA-II. Escalar e NSGA-II otimizam os mesmos 2 eixos.
- **Objetivo só-decisividade era cego à WR** — hipótese "luta apertada ⟹ WR ~50%"
  falsificada empiricamente; a WR voltou como termo primário.
- **WR por-matchup forçava equilíbrio plano** — incompatível com o ciclo por
  construção; substituída pela WR **global** por personagem (formulação C2).
- **`LAMBDA_DRIFT` 6.0 → 1.0** — com 6.0 o AG escalar ficava colado no canônico.
- **Drift normalizado por `x / hi`** → `(x − lo)/(hi − lo)`, e ponderado pelos
  `defining_genes` (`DRIFT_DEFINING_WEIGHT = 3.0`). A normalização por range conserta a
  **ordenação** de identidade entre indivíduos; o peso alarga a margem.
- **Piso de decisividade descalibrado** — `MATCHUP_FLOOR` 0,10 → 0,02. A premissa ("D
  baixo = luta que não aconteceu") não vale no motor reformado: 100% das lutas terminam em
  KO. O piso virou guarda de degenerescência, e é o que pega o roster-espelho.
- **Gate de convergência inalcançável por construção** — o limiar escalar
  `dominance_penalty ≤ 1e-9` era insatisfazível porque `global_term` é quantizado. O gate
  virou o **próprio predicado** `roster_balanced`, e a confirmação passou a rodar num
  stream que o AG nunca viu.
- **Critério de parada assimétrico** — resolvido por **orçamento fixo nos dois**:
  convergência e estagnação viraram evento registrado (`converged_at` / `stagnated_at`),
  não parada. A comparação passou a ser qualidade sob orçamento igual.
- **Família de Holm inflada** — `n_chars_balanced` é constante na amostra conjunta e
  devolvia `p = nan`, entrando na família como se fosse um teste. A família passou a ser
  montada por variância da amostra conjunta, e `_holm` recusa `nan`.
- **Piso da sensibilidade subdimensionado e critério duplo** — o piso passou a ser
  **medido** sob hipótese nula (dois eval do mesmo roster, sem perturbação, seeds
  diferentes), na mesma grandeza que a tabela classifica (uma **diferença**, não uma
  proporção). O tool ganhou `--evolved` / `--nsga2`: medir no canônico saturado era efeito
  de teto, não neutralidade de gene.
- **Nenhuma métrica post-hoc tinha piso** — `baselines.py` mede o chão de cada métrica
  em modelos nulos (espelhos + aleatórios) e reporta `position` + p-valor empírico. O
  validador tem chão ~6,8/21 e um roster aleatório chega a 12/21; drift de espelho ~0,33;
  o ciclo canônico tem chão 5/10 porque cada aresta é cara-ou-coroa.

**Motor de combate:**

- **Reforma do motor (2026-09-10)** — quatro defeitos medidos e corrigidos: o avanço
  incondicional fora do alcance (que matava o espaçamento e invertia o sinal do
  knockback), a exclusividade entre atacar e recuar (que impedia zonear), o
  atravessamento dos corpos e o stun arredondado. Mais o empate como terceiro desfecho,
  que eliminou o viés do lado A, e a regra de impasse, que eliminou a estagnação.
  Números antes/depois em [11-combat-review.md](11-combat-review.md).
- **Simplificação do combate** — fora `defense`, `recovery` e hesitação; `stun` virou
  fração do cooldown.
- **Eixo Recurso sem counter, e o Grappler sem assinatura comportamental (2026-09-16)** —
  era uma lacuna só produzindo quatro sintomas: DEFEND não tinha custo, a Layer 3 tinha 4
  asserções para 5 arquétipos, a aresta "Grappler vence Turtle" não tinha mecanismo e o
  Grappler tinha um único gene definidor. Resolvido pelo gene `grab_power`
  ([04-combat-model.md](04-combat-model.md)); o validador vai a **23/23** no canônico.
  *Fica em aberto:* que o AG realize a aresta **por mérito** — no canônico o Grappler
  vence o Turtle em 100%, mas já vencia antes, porque o Turtle canônico perde para todos.

**Agenda de calibração (2026-09-16) — os sete itens fechados com evidência:**

- **`DOMINANCE_DECIS_WEIGHT = 0,5` mantido** — o termo lê 0,0000 nos indivíduos finais
  porque é uma **guarda que funcionou**, não um termo morto: o canônico lê 0,2834 com
  5/10 pares acima do teto, os aleatórios 0,10–0,66, e o piso pega o roster-espelho
  (10/10 pares abaixo).
- **`MATCHUP_WR_CAP = 0,15` mantido, com âncora de domínio** — a grade de matchup da FGC
  é 5-5 / 6-4 / 7-3 / 8-2, que em `|WR − 0,5|` são 0,00 / 0,10 / 0,20 / 0,30. O cap tem de
  permitir 6-4 e barrar 7-3, e **não** pode cair sobre um ponto da grade (ali é
  cara-ou-coroa sob ruído binomial). 0,15 é o ponto médio do único vão que importa.
- **Protocolo de avaliação: rotação do stream por geração** — `generation_seed(base, gen)`
  é a definição única, consumida pelos **dois** laços. CRN vale dentro da geração
  (correto para seleção), o stream muda entre gerações (impede ajuste a uma realização).
  `SIMS_PER_MATCHUP` fica em 150.
- **Canônicos declarados finais.**
- **`ACTION_PERSISTENCE_SUBTICKS` 10 → 5** — 5 é exatamente 1 tick e exatamente o cooldown
  mínimo; a 10 um personagem de `cooldown = 1` que sorteava GUARDA abria mão de **duas**
  janelas por acidente de escala. A medição concordou com o argumento de coerência: SNR
  melhor em **8/8** genes, e o piso de ruído caiu de 4,9% para 3,5%.
- **Drift invariante à escala dos pesos** — a intenção é sorteada *proporcionalmente* a
  `(w_agg, w_ret, w_def)`, então multiplicar os três por `k > 0` não muda nada no combate.
  `fitness.drift_genes` reescala os 3 pesos à soma canônica antes de comparar; sem isso o
  drift cobrava por um grau de liberdade invisível ao simulador (7,5% do drift médio,
  pior caso Rushdown 15,1%).
- **`MULTI_RUN_N_SEEDS`: n = 20 decidido** — rodando em 10 por custo; ver §1.1.

**Infraestrutura:**

- **Artefatos sem proveniência (2026-09-17)** — todo JSON de `results/` passou a carregar
  um bloco `provenance`: timestamp, `fingerprint`, **toda** constante de `config.py` valor
  a valor, digest dos canônicos e digest do código do motor. `Individual.from_results` e
  `from_nsga2` verificam e avisam **o que** mudou, não só que mudou — e são o gargalo por
  onde toda tool carrega um indivíduo evoluído, então a checagem não pode ser esquecida
  numa tool nova. Detalhe e as quatro decisões de projeto em
  [09-reproducibility.md](09-reproducibility.md).
- **Marcos de convergência por semente (2026-09-17)** — `multi_run` grava `converged_at` e
  `stagnated_at` no `per_seed` e agrega em `convergence` (taxa + geração média entre as
  que convergiram, sem imputar valor para as que não convergiram). Fecha o eixo de
  **velocidade** que o critério de parada prometia. A assimetria fica **declarada**: o
  NSGA-II não tem equivalente — "o roster está equilibrado?" não é pergunta que se faça a
  uma fronteira —, então ele devolve `(None, None)` e os campos não saem no agregado dele,
  em vez de zeros que alguém agregaria sem perceber.
- **Reprodutibilidade da seed** — o RNG do Numba é interno; `seed_combat()` é a única
  forma de semeá-lo, e a semeadura reset-ao-base dá Common Random Numbers.
- **Persistência dos artefatos** — `results.json` grava semente, condição de parada,
  objetivos e `history`, no mesmo contrato do `nsga2_results.json`; o
  `sensitivity_analysis` grava a matriz Δ WR.
- **Teste estatístico entre algoritmos** — `compare_algorithms` (Mann-Whitney U +
  Â₁₂ + Holm-Bonferroni) fecha o item que faltava do 1.1.
