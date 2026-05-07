# Pontos importantes para o TCC

> **Propósito**: depósito vivo de pontos que **devem aparecer** em alguma seção da
> tese (introdução, metodologia, resultados, discussão, etc.) — anotados no
> momento em que surgem para não se perderem. Não é redação final, é matéria-prima.
>
> Cada ponto tem: **(a)** onde mora na estrutura da tese, **(b)** o que precisa
> ser dito, **(c)** observações/dúvidas em aberto.
>
> **Status atual**: sistema ainda em refinamento. Nem todo ponto aqui é
> conclusão fechada — alguns são decisões metodológicas, outros são achados
> preliminares, outros são perguntas em aberto que precisam de mais experimento.

---

## 1. Pergunta de pesquisa & escopo

**Vai em**: Introdução, Objetivos.

**Pergunta central:**

> Um Algoritmo Genético consegue atingir balanço competitivo entre 5 arquétipos
> distintos sem destruir suas identidades funcionais?

**Decisão metodológica crítica — não forçar identidade no fitness:**

- Os valores canônicos dos arquétipos servem como **seed inicial** e como
  **baseline de medição de drift**, não como restrições rígidas.
- O AG evolui livremente. Drift é penalizado via `LAMBDA_DRIFT`, mas nunca
  hard-constrained.
- O **ciclo canônico de vantagens** (quem vence quem — Rushdown > Zoner, etc.)
  **não é codificado em nenhuma penalidade**. É métrica post-hoc.
- Por quê: codificar o ciclo no fitness tornaria a pergunta de pesquisa
  circular ("o AG preserva identidade quando eu pago ele pra preservar").

**Em aberto**: até onde o AG pode se afastar do canônico antes de perder
identidade reconhecível? Esse é parte do que o experimento deve responder.

---

## 2. Arquitetura do sistema

**Vai em**: Metodologia (descrição do sistema).

**Duas camadas independentes:**

- **Combate** (`combat.py`): simulação tick a tick, determinística exceto pela
  política probabilística de resposta a ameaça (soft policy). Sem variância
  de dano. Sem combo chaining.
- **AG** (`ga.py`, `nsga2.py`, `fitness.py`): orquestra round-robin (10 matchups
  × 100 sims) e produz fitness escalar (AG clássico) ou Pareto front (NSGA-II).

**Genes**: 5 personagens × 12 genes = 60 genes por indivíduo.

- 9 atributos numéricos por personagem (HP, dano, cd, range, speed, defense,
  stun, knockback, recovery)
- 3 pesos comportamentais (w_retreat, w_defend, w_aggressiveness)

**Decisão importante**: cromossomo é o **conjunto** de 5 personagens, não cada
personagem isolado. Razão: WR de qualquer personagem depende dos outros 4
simultaneamente — não faz sentido evoluir um personagem sozinho.

---

## 3. Decisões de design do combate

**Vai em**: Metodologia (modelo de combate).

### Estocasticidade

A estocasticidade do combate vem de **uma única fonte**: a política
probabilística da resposta a ameaça (soft policy — ver seção abaixo). Todas
as outras decisões e o cálculo do dano são determinísticos.

**Removidas:**

- `DAMAGE_VARIANCE` (era 0.20, ±20% por hit). Reduzia o sinal das mutações
  abaixo do piso de ruído binomial. Combat agora determinístico no dano:
  `damage × (1 - defense)`.
- `ACTION_EPSILON` (era 0.20, prob. de ação aleatória uniforme por tick).
  Era ruído uniforme aplicado em todos os ticks. Existia para gerar
  distribuição contínua de WR sobre N simulações, mas com soft policy a
  estocasticidade já vem da própria política do agente — `ACTION_EPSILON`
  ficou redundante e contaminava a interpretação do comportamento.

**Justificativa metodológica**: estocasticidade é desejável **só onde modela
incerteza estratégica relevante** (escolha do jogador entre alternativas).
Ruído uniforme nas ações ou variância no dano por hit são ruídos operacionais
que prejudicam o AG sem trazer realismo proporcional.

### Soft policy na resposta a ameaça

Quando o inimigo pode acertar o personagem agora (`distance ≤ enemy.range_`
+ `enemy.attack_ready` + não stunado), a ação é sorteada via `random.choices`:

```
P(ADVANCE) ∝ w_aggressiveness
P(RETREAT) ∝ w_retreat
P(DEFEND)  ∝ w_defend
```

**Antes** (hard policy): comparações duras `>` entre os pesos. Cada peso
funcionava como gene **categórico** — só importava qual era o maior, e
mutações pequenas com `WEIGHT_MUTATION_SIGMA=0.02` raramente cruzavam o
threshold entre dois pesos, então a maioria das mutações nos pesos era
invisível pro AG (gradient flat).

**Depois** (soft policy): cada peso tem efeito contínuo. Um Δ no peso vira
Δ proporcional na probabilidade da ação. O AG passa a ter gradiente em todo
o domínio dos pesos, não só nas fronteiras.

**Trade-off conceitual**: estamos modelando "jogador que escolhe estratégia
mais provável" (hard) ou "jogador que oscila proporcionalmente entre
estratégias" (soft)? Optamos pela soft porque (a) dá gradiente ao AG,
(b) modela mistura comportamental real (jogador não é 100% consistente),
(c) os pesos passam a ser coerentes com sua medição via `drift_penalty`
(antes, drift media diferenças que o comportamento não exibia).

### Stun cap (combo chaining)

- `STUN_CAP_MULTIPLIER = 1.0`. Stun nunca excede o cooldown do atacante.
- Antes era 2.0 (permitia 1 hit extra durante o stun = combo chaining).
- O AG explorava 2.0 como estratégia degenerada: cooldown alto + stun alto
  gerava perma-lockdown — vencia matchups por lockdown, não por dano.

### Defesa

- `DEFEND_DAMAGE_REDUCTION = 0.4` (defender → recebe 40% do dano).
- Antes era 0.2 (recebia 20%). Defender era trivialmente ótimo, AG não
  evoluía `defense`/`recovery`.

### Recovery como inteiro subtrativo

- Recovery é um **inteiro em sub-ticks**, bounds `[0, 15]`.
- Cada unidade subtrai 1 sub-tick do stun recebido:
  `effective_stun = max(0, raw_stun - defender.recovery)`.
- Antes era multiplicativa (`stun × (1 - recovery_float)`). Pequenas mutações
  em recovery eram invisíveis após o `round()` — gene neutro.
- A representação interna continua float (mutação gaussiana é contínua),
  mas `clip()` arredonda o valor armazenado para int. Configurado via
  `INTEGER_ATTRIBUTES = {8}` em `config.py`.

### Outros parâmetros relevantes

- `TICK_SCALE = 5`: resolução sub-tick para cooldown e stun (21–25 valores
  discretos por gene, eliminando platôs).
- `MAX_TICKS = 500 × TICK_SCALE = 2500`: limite por combate.
- `DEFEND_DAMAGE_REDUCTION` e `STUN_CAP_MULTIPLIER` foram calibrados juntos —
  trocar um sem o outro pode reintroduzir modos degenerados.

---

## 4. Decisões de design do AG / fitness

**Vai em**: Metodologia (formulação do AG).

### Função de fitness escalar (AG clássico)

```
fitness = -(LAMBDA_SPECIALIZATION × specialization_penalty
          + LAMBDA_DRIFT          × drift_penalty
          + LAMBDA_DOMINANCE      × dominance_penalty)
```

Todos os termos em `[0, 1]`, todos minimizados.

| Termo                      | Peso | O que penaliza                           |
| -------------------------- | ---- | ---------------------------------------- |
| `specialization_penalty` | 0.2  | Builds homogêneas (max-min normalizado) |
| `drift_penalty`          | 6.0  | Distância euclidiana ao canônico       |
| `dominance_penalty`      | 1.0  | Dominância em matchups (RMS)            |

**`drift_penalty` com peso 6.0**: alto. Reflete o trade-off central da tese —
queremos balance, mas não a ponto de descaracterizar arquétipos.

### NSGA-II ignora os λ

**Importante mencionar**: `evaluate_objectives` retorna apenas
`(dominance_penalty, drift_penalty)` em escala bruta. O Pareto front é
calculado nessas duas dimensões sem ponderação. Mudar `LAMBDA_*` não afeta
o NSGA-II.

### Dominance penalty — direcionalmente cega

- Usa `|score - 0.5|`, não codifica qual lado deveria vencer cada matchup.
- Codificar o ciclo canônico aqui forçaria identidade → pergunta de pesquisa
  circular.

### HP-weighted scoring no dominance penalty

- O dominance opera sobre **`matchup_scores`** (HP-weighted), não WR binário.
- Em combates KO o score é 1.0/0.0 (igual ao WR).
- Em combates por timeout, o score é a fração de HP% — um stalemate 55/45
  entra como score≈0.55, não 1.0.
- Razão: matchups que estouram `MAX_TICKS` sem KO são essencialmente coin
  flips do ponto de vista binário. O AG recebia sinal binário sobre o que
  era ruído. Score contínuo elimina esse falso sinal.

---

## 5. Validação metodológica — análise de sensibilidade

**Vai em**: Metodologia (validação) e/ou Resultados.

**Pergunta**: o AG consegue *enxergar* todos os 9 atributos? Ou alguns deles
são neutros — drift puramente por random walk, sem pressão seletiva?

**Como medir**: `sensitivity_analysis.py`. Para cada (arquétipo, atributo),
perturbar o gene em ±σ e medir |Δ WR|.

**Limiar**: piso binomial com 100 sims/matchup ≈ 5%. Atributos com |Δ| médio
abaixo disso são genes neutros.

**Resultado preliminar** (canônico atual, sims=50): todos os atributos estão
acima do piso. Recovery (após mudança para int subtrativo) saltou de quase
neutro para 18% — confirma que o fix funcionou.

**Em aberto**: rodar com `sims=500` e indivíduos do Pareto (não só canônico)
para ter números defensáveis. Em alguns canônicos certos genes saturam (Zoner
em 0% global → toda perturbação dá Δ=0%).

---

## 6. Achados estruturais sobre o ambiente

**Vai em**: Resultados ou Discussão.

### O ciclo canônico não é trivialmente preservado

Após remover combo chaining e variância de dano, **6/10** matchups canônicos
estão violados quando jogados com os valores canônicos atuais.

**Implicação**: o ciclo de FGCs (Rushdown > Zoner > Grappler > Rushdown, etc.)
**depende parcialmente de mecânicas estocásticas/de combo** que mascaram
desbalanceamentos determinísticos. Sem elas, o resultado de cada matchup
fica binário (100% ou 0%) e o ciclo desaba.

**Em aberto**: três caminhos possíveis pra discutir:

- (A) Aceitar como achado: "o ciclo canônico é fragil em modo determinístico".
- (B) Re-calibrar atributos canônicos para o novo regime.
- (C) Reintroduzir variância mínima (ex.: 5%) para testar até onde o ciclo
  emerge naturalmente.

### Stalemate em pareamentos lentos

Antes do fix de HP-weighted scoring, o matchup Zoner × Turtle terminava
500/500 sims em timeout (KO=0%), com decisão por HP%. WR ficava
essencialmente como coin flip. Agora o `dominance_penalty` opera sobre
HP-weighted scores, então stalemates entram como ~0.5 (sinal correto).

---

## 7. Hiperparâmetros e janela de evolução

**Vai em**: Metodologia (parâmetros experimentais).

| Parâmetro                   | Valor           | Justificativa                              |
| ---------------------------- | --------------- | ------------------------------------------ |
| `POPULATION_SIZE`          | 300             | —                                         |
| `MAX_GENERATIONS`          | 100             | —                                         |
| `STAGNATION_LIMIT`         | 50              | Para se não houver melhoria               |
| `SIMS_PER_MATCHUP`         | 100             | Erro padrão binomial ≈ 5% em WR=50%      |
| `MUTATION_RATE`            | 0.1             | Por gene                                   |
| `ATTRIBUTE_MUTATION_SIGMA` | 0.1 (× range)  | Exploração ampla                         |
| `WEIGHT_MUTATION_SIGMA`    | 0.02 (× range) | Inércia evolutiva — preserva estratégia |

**A diferença de σ entre atributos e pesos é deliberada**: pesos definem
comportamento de alto nível (estratégia); atributos definem capacidade.
Queremos explorar mais capacidades do que mudar de estratégia.

---

## 8. O que é métrica vs. o que é objetivo

**Vai em**: Metodologia ou Discussão (separar claramente).

| Métrica                                       | Otimizado?                | Onde aparece                       |
| ---------------------------------------------- | ------------------------- | ---------------------------------- |
| `dominance_penalty` (HP-weighted score, RMS) | sim                       | Fitness e NSGA-II                  |
| `drift_penalty` (distância euclidiana)      | sim                       | Fitness e NSGA-II                  |
| `specialization_penalty`                     | sim (só fitness escalar) | Fitness escalar                    |
| **WR binário por personagem**           | não                      | Relatório post-hoc, convergência |
| **Preservação do ciclo canônico**     | **não**            | Relatório post-hoc apenas         |
| **Sensibilidade dos atributos**          | não                      | Validação metodológica          |

A separação importa: a tese argumenta sobre o que o AG **pode otimizar** e o
que ele **não otimiza** (ciclo). O resultado científico está justamente em ver
o que emerge sem ser codificado.

---

## 9. Perguntas em aberto / a investigar

Lista viva — atualizar à medida que decisões forem tomadas.

- [ ] Rodar NSGA-II completo com a configuração atual (após todos os fixes
  de mecânica) e observar:
  - Quantos matchups canônicos ficam preservados nos representantes do Pareto?
  - Como o trade-off drift × dominance se comporta?
- [ ] Análise de sensibilidade com `sims=500` e individuals do Pareto, não só
  canônico — produzir tabela final pra tese.
- [ ] Decidir caminho A/B/C sobre o ciclo canônico em regime determinístico.
- [ ] Verificar se `LAMBDA_DRIFT=6.0` ainda faz sentido depois das outras
  mudanças, ou se vale rodar uma sweep (MAP-Elites).
- [ ] Documentar formalmente quais matchups são "stalemate-prone" (KO=0%).
- [ ] Considerar adicionar `cycle_violations` como 3º objetivo do NSGA-II.
  Decisão pendente — só faz sentido depois de ter resultado base no
  formato atual.

---

## 10. Limitações conhecidas (anotar pra discussão final)

**Vai em**: Limitações / Trabalhos futuros.

- O modelo de combate é uma simplificação grosseira de FGCs reais — não
  considera frames de startup/recovery por golpe, mix-ups, neutral game,
  posições oclusas, etc.
- 5 arquétipos é o suficiente pra ter um ciclo, mas FGCs reais têm 10+.
- O fitness mistura preservação de identidade (`drift`) e balance (`dominance`)
  numa soma ponderada (no AG escalar) ou Pareto 2D (NSGA-II) — outras
  formulações são possíveis.
- O round-robin assume todos os arquétipos jogados igualmente — não modela
  matchmaking real onde jogadores escolhem matchups favoráveis.
