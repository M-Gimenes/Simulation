# Revisão de coerência do sistema — pauta

Roteiro da revisão passo a passo de cada etapa do sistema, para verificar se as
escolhas são coerentes entre si e com a pergunta de pesquisa. Aberto em 2026-09-10,
depois de fechar as correções do `HANDOFF.md`.

Não é lista de bugs — é **lista de escolhas a auditar**. Cada item traz o que já foi
observado (fato) separado do que ainda precisa ser decidido (pergunta). Pontos que já
sabemos estar em aberto no sistema seguem em
[`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md); aqui fica o
percurso da auditoria.

**Como usar:** percorrer as etapas na ordem (o de baixo depende do de cima). Ao fechar
um item, registrar a decisão no doc de referência do tema e marcar aqui.

---

## 1. Ambiente e execução

- [ ] **Pool de processos recriado a cada geração.** *Fato:* `fitness.evaluate_population`
  (e o equivalente em `nsga2.py`) cria um `ProcessPoolExecutor` novo por geração, então
  o custo de spawn escala com o nº de workers. Medido nesta máquina, uma geração de 300
  indivíduos: 1w 4,56s | 4w 1,66s | **8w 1,28s** | 12w 1,41s | 16w 1,62s | 20w 1,91s |
  28w 2,77s. Com o default (`None` → 28 núcleos) os processos carregando llvmlite
  estouravam o limite de commit do Windows (`WinError 1455`). Mitigado fixando
  `N_WORKERS = 8`. *Pergunta:* vale trocar por um pool persistente? Ganho provável
  grande, mas exige propagar mudanças de `_SEED_BASE` para workers vivos — plumbing de
  reprodutibilidade.
- [ ] **`N_WORKERS = 8` é específico desta máquina.** *Pergunta:* deixar fixo e
  documentado (hoje), ou derivar de `os.cpu_count()` com teto?
- [ ] **Alinhamento CRN imperfeito depois do 1º matchup.** *Fato:* cada luta consome um
  nº variável de sorteios, então a posição do stream diverge entre indivíduos nos
  matchups seguintes. *Pergunta:* aceitar (documentado) ou semear por
  `(base, matchup_idx, sim_idx)`?

## 2. Simulação de combate

- [ ] **`TICK_SCALE = 5` e `ACTION_PERSISTENCE_SUBTICKS = 10` são provisórios.** Nunca
  foram variados em experimento. *Pergunta:* qual evidência justifica esses valores?
  Note o acoplamento: a invariante "stun < cooldown" depende de
  `round(stun_bound × TICK_SCALE) < round(cd_min × TICK_SCALE)` — com `TICK_SCALE = 1`
  ela quebra.
- [ ] **Uma intenção dura 10 sub-ticks = 2 ticks lógicos.** *Pergunta:* isso é
  comprometimento suficiente para o efeito pretendido (momentum), ou o valor foi
  escolhido por conveniência?
- [ ] **Grappler sem mecânica própria.** *Fato:* o combate não modela grab/throw, então
  o Grappler é "corpo-a-corpo com mais dano" e a Layer 3 do validador tem 4 asserções
  para 5 arquétipos. *Pergunta:* aceitar como limitação declarada (posição atual) ou o
  modelo precisa de uma mecânica que dê expressão comportamental a ele?
- [ ] **Sem encurralamento.** RETREAT recua até a borda e vira DEFEND. *Pergunta:* o
  `forced_defend` do trace é suficiente para separar defesa escolhida de forçada nas
  métricas de identidade?

## 3. Representação: genes, arquétipos, canônicos

- [ ] **Canônicos re-tunados são provisórios.** HP, dano e stun dos 5 foram reajustados
  ao novo modelo e nunca calibrados. *Pergunta:* qual o critério para dizer que um
  conjunto canônico está bom? Ele é simultaneamente semente inicial e régua do
  `drift_penalty` — mudá-lo move as duas coisas ao mesmo tempo.
- [ ] **Turtle no teto do bound de HP (450).** *Pergunta:* um canônico colado no bound
  limita a exploração do AG num lado só; é intencional?
- [ ] **Normalização do drift usa `x / hi`** (fração do máximo do bound), não
  `(x − lo) / (hi − lo)`. *Pergunta:* a escolha é deliberada? Ela faz genes com `lo`
  alto (ex.: HP, mín 250) parecerem menos deslocados do que estão.

## 4. Fitness e dados

- [ ] **O gate de convergência do AG é inalcançável na prática.** *Fato:* `ga.run`
  só testa convergência quando `dominance_penalty <= 1e-9`; na execução seed 42 o
  mínimo em 150 gerações foi **0,0052** — seis ordens de grandeza acima do gate. O AG
  para sempre por estagnação ou teto de gerações, e o ramo de confirmação
  (`SIMS_CONVERGENCE_CHECK`, `character_balanced`, `is_hard_counter`) nunca executa.
  *Pergunta:* o gate deveria ser um limiar calibrado (ex.: o próprio
  `GLOBAL_CONVERGENCE_THRESHOLD`), ou o critério de parada por convergência deve sair?
  Do jeito que está, `converged` é sempre `False` — e é um critério descrito na
  metodologia.
- [x] **`dominance_penalty` abaixo do piso de ruído: há ajuste ao stream, mas o
  equilíbrio sobrevive.** *Fato:* com 150 sims/matchup o desvio binomial da WR global
  (600 lutas) é ~2%, o que daria um `global_term` da ordem de 0,03 — e o AG chegou a
  0,0076 no laço, indicando adaptação à realização específica do RNG fixada pelo CRN.
  Fora do laço (`external_validation`, sementes 10000+, 500 sims) o mesmo indivíduo dá
  **0,0279 ± 0,0062**: degrada ~3,7×, mas mantém 5/5 bonecos em banda em todas as 10
  condições e **0/10** hard-counters — veredito **ROBUSTO**. *Conclusão:* o ajuste ao
  stream existe e precisa ser declarado, mas não é o que sustenta o resultado. Reportar
  sempre o número **fora** do laço.
- [ ] **`MATCHUP_WR_CAP = 0.15` provisório.** Define o que é "counter duro" e portanto
  quanto do ciclo de vantagens cabe no espaço permitido. *Pergunta:* há justificativa
  de domínio (FGC) para 15 pontos percentuais, ou é preciso um sweep?
- [ ] **Pesos 1.0 / 0.5 / 0.5 dos três termos do dominance.** Nunca variados.
  *Pergunta:* o que muda na fronteira ao mexer neles?
- [ ] **A análise de sensibilidade mede no ponto errado do espaço.** *Fato:* ela roda
  fixa no **canônico** (`Individual.from_canonical()` está hardcoded em `_eval_task`, o
  tool não tem `--evolved`/`--nsga2`), e o canônico é saturado — Rushdown ganha 100% de
  tudo, Turtle 0,1%, 10/10 hard-counters. Com a WR presa no teto, perturbar um gene não
  muda nada, e o resultado é que **6 dos 7 atributos saem classificados como "neutros"**
  (só `attack_cooldown`, 5,6%, passa do piso de 1,8%). Isso é **efeito de teto**, não
  neutralidade de gene. *Pergunta:* a tabela precisa ser medida também num indivíduo
  equilibrado (evoluído / knee) para sustentar a afirmação "o AG enxerga o cromossomo";
  do jeito que está, ela sustenta o contrário do que se quer afirmar.
- [ ] **`SIMS_PER_MATCHUP = 150` vs as bandas de decisão.** Ruído binomial por matchup
  ~4% contra um cap de 15%. *Pergunta:* a margem é confortável o bastante, ou o número
  de sims precisa subir para o cap significar o que diz?

## 5. AG escalar e NSGA-II

- [ ] **Escalar e NSGA-II não param pelo mesmo critério.** O AG tem convergência +
  estagnação + teto; o NSGA-II roda `NSGA2_GENERATIONS` fixas. *Pergunta:* a assimetria
  é intencional? Ela afeta a comparação entre os dois.
- [ ] **Qual ponto da fronteira representa o NSGA-II na comparação.** *Fato novo:* com
  a bateria de 2026-09-10, o AG escalar **vence** o `best_dominance` do NSGA-II em
  `dominance_penalty` (mediana 0,066 vs 0,129; p_Holm = 0,018; Â₁₂ = 0,12, efeito grande)
  e em hard-counters por execução (0 vs 3; p_Holm = 0,049), sem diferença significativa
  em `drift_penalty`. Isso torna a escolha do representante decisiva para a leitura.
  *Fato:* o AG escalar com `LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1.0` minimiza a **soma** (L1) dos dois
  objetivos; o representante `ideal_point` minimiza a **norma euclidiana** (L2); e o
  `multi_run` compara contra `best_dominance` (um **extremo** da fronteira). São três
  pontos diferentes. *Pergunta:* qual é o comparável correto? Se o argumento é "o
  escalar é um ponto da fronteira que o NSGA-II mapeia", o comparável é o ponto de
  mínimo L1 — que hoje não é extraído.
- [ ] **Sweep de `LAMBDA_DRIFT` nunca feito.** É a demonstração de que o escalar é *um
  ponto* do trade-off. Hoje isso é afirmado, não medido.
- [ ] **Crossover só por bloco de personagem.** Recombinação intra-personagem depende
  100% da mutação. *Pergunta:* limitação aceita e declarada, ou vale testar um crossover
  de gene?
- [ ] **Elitismo de 10% + torneio 3.** Nunca variados. *Pergunta:* precisam de
  justificativa além de "valores usuais"?

## 6. Protocolo experimental e artefatos

- [ ] **Round-robin uniforme.** Os 10 pares pesam igual; não modela matchmaking.
  *Pergunta:* declarar como escopo (posição atual) basta?
- [ ] **Equilíbrio condicionado a uma política fixa.** Os pesos `w_*` *são* a política;
  ninguém procura exploit contra o roster evoluído. É a objeção mais forte ao resultado.
  *Pergunta:* precisa aparecer na Discussão com que peso?
- [ ] **10 sementes é suficiente?** `MULTI_RUN_N_SEEDS = 10`. Com Mann-Whitney e n=10 o
  SciPy usa a aproximação assintótica (conservadora). *Pergunta:* subir para 20-30
  mudaria as conclusões, e o custo é aceitável (~3,8 min por execução)?
- [ ] **Referências de estatística fora do `.bib`.** Derrac et al. 2011, Arcuri & Briand
  2011 e Vargha & Delaney 2000 são citadas nos docs e no código, mas **não estão** em
  `overleaf/TCC/bibliografia.bib`.
- [ ] **O veredito da validação externa é binário e sensível a ruído.** *Fato:* o roster
  só é ROBUSTO se **nenhum** par virar hard-counter em **nenhuma** das 10 condições — 100
  oportunidades de falhar. O `best_dominance` do NSGA-II tem 5/5 bonecos robustos e
  apenas 1/10 pares que trip em alguma condição, e ainda assim sai FRÁGIL. *Pergunta:* o
  quantificador "em alguma condição" é o certo, ou o veredito deveria ser uma fração
  (ex.: par fora da banda em >X% das condições)?
- [ ] **`results/` não tem versionamento parcial.** Mexer em `config.py`, nos canônicos
  ou no motor invalida tudo de uma vez. *Pergunta:* vale gravar um snapshot da config
  dentro de cada artefato, para que um JSON antigo se denuncie sozinho?
