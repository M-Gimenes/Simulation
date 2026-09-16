# 10 — Pontos em aberto

O que **ainda está aberto** no sistema, em 2026-09-10 (fim do dia, depois da
auditoria de coerência e da reforma do motor de combate). Não é histórico: a trajetória
das decisões (que problema cada mudança resolveu) vive em
[`../tcc/04-caminhos-e-decisoes.md`](../tcc/04-caminhos-e-decisoes.md), e o estado
atual do sistema nos docs 01–09. Aqui ficam só as pendências e os limites conhecidos,
para que nenhuma delas seja descoberta por acidente na hora de escrever.

---

## 1. 🔴 Calibração declarada provisória e nunca feita

Quatro parâmetros estão marcados no código e nos docs como *provisórios, a calibrar*,
e nenhum experimento no repositório varia qualquer um deles:

| Parâmetro | Valor atual | O que a escolha decide |
|---|---|---|
| `MATCHUP_WR_CAP` | 0.15 | quão dura uma aresta do ciclo pode ser antes de virar hard-counter |
| canônicos re-tunados (HP, dano, stun) | ver [03-archetypes.md](03-archetypes.md) | o ponto de partida e a régua do `drift_penalty` |
| `ACTION_PERSISTENCE_SUBTICKS` | 10 | quanto de comprometimento/momentum o combate tem |
| `TICK_SCALE` | 5 | resolução sub-tick de cooldown/stun/movimento |

O instrumento para comparar configurações já existe e não precisa ser construído:
**hipervolume por configuração** ([06-nsga2.md](06-nsga2.md)), `multi_run` para
agregar N execuções e `compare_algorithms` para o teste estatístico
([08-tools.md](08-tools.md)). O que falta é rodar.

Na mesma prateleira, e nunca feito: o **sweep de `LAMBDA_DRIFT`**. É ele que
demonstraria que o AG escalar é *um ponto* do trade-off que o NSGA-II mapeia — hoje
isso é afirmado, não medido.

A ressalva de método que existia aqui — "o escalar minimiza a soma (L1) enquanto o
`ideal_point` minimiza a norma euclidiana (L2), são pontos diferentes" — **virou código
em 2026-09-16**: `select_representatives` passou a extrair `scalar_optimum`, o mínimo de
`LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift`, que é o comparável correto. O
`ideal_point` (L2) continua lá, agora como um ponto geométrico entre outros. Ao comparar
escalar × NSGA-II o representante usado ainda precisa ser declarado (o `multi_run` grava
`nsga2_representative`, default `best_dominance`).

Medição mais recente, orçamentos iguais (pop 120, 150 gerações, 80 sims, seed 42): o
escalar chega a `dominance` 0,0088 / drift 0,2856 (L1 0,2945) e o `scalar_optimum` da
fronteira a 0,0481 / 0,1634 (L1 **0,2115**) — o NSGA-II vence na função que o escalar
otimiza, e o ponto do escalar fica **fora** da fronteira, abaixo do extremo de dominance
dela. Nenhum dos dois domina o outro de forma relevante (o escalar domina 3 de 49
pontos; nenhum ponto o domina).

## 2. 🟡 Limites estruturais do método (decisões, não bugs)

Nenhum destes é defeito de implementação — são fronteiras do que o sistema mede.
Precisam aparecer explicitamente na Discussão, não só em Trabalhos Futuros.

- **O equilíbrio é condicionado a uma política fixa.** Os pesos `w_*` *são* a
  política: os personagens não aprendem, e ninguém procura exploits contra o roster
  evoluído. Se existir uma estratégia dominante que a política sorteada não visita, o
  equilíbrio medido não a enxerga. É o item 2.1 (coevolução) de
  [`../tcc/08-metodologias-da-literatura.md`](../tcc/08-metodologias-da-literatura.md),
  decidido como trabalho futuro — decisão legítima, mas **é a objeção mais forte ao
  resultado**.
- **Crossover só por bloco de personagem.** Recombinação de genes *dentro* de um
  personagem depende 100% da mutação; o crossover só troca personagens inteiros entre
  indivíduos. Limita a exploração fina do espaço.
- **Round-robin uniforme.** Todos os 10 pares pesam igual. Não modela matchmaking
  real (jogadores escolhendo matchups favoráveis), então "equilíbrio" aqui é
  equilíbrio sob confronto uniforme.
- ~~**Grappler sem asserção comportamental — e o eixo Recurso sem counter.**~~
  **Resolvido em 2026-09-16** pelo gene `grab_power` (ver
  [04-combat-model.md](04-combat-model.md#grab)). Era uma lacuna só produzindo quatro
  sintomas: o eixo Recurso sem contrapartida (DEFEND não tinha custo), a Layer 3 com 4
  asserções para 5 arquétipos, a aresta "Grappler vence Turtle" sem mecanismo, e o
  Grappler com um único gene definidor. O validador vai a **23/23** no canônico.
  *Fica em aberto:* que o AG realize a aresta do ciclo **por mérito** — no canônico o
  Grappler vence o Turtle em 100%, mas já vencia antes, porque o Turtle canônico perde
  para todos.
- **A política é cega ao estado.** A intenção não depende de HP, distância, cooldown
  do oponente nem de o oponente estar stunado: "estratégia" no modelo é uma mistura fixa
  de três posturas, mantida por `ACTION_PERSISTENCE_SUBTICKS`. É o commitment pretendido,
  mas nenhum arquétipo tem plano. Ver [`../../REVIEW.md`](../../REVIEW.md) §2.
- **Alinhamento CRN imperfeito depois do 1º matchup.** Toda avaliação reseta o RNG do
  combate ao mesmo seed-base, mas cada luta consome um número variável de sorteios —
  a posição do stream diverge entre indivíduos nos matchups seguintes. Muito melhor
  que seeds independentes; alinhamento perfeito exigiria semear por
  `(base, matchup_idx, sim_idx)`. Detalhe em
  [09-reproducibility.md](09-reproducibility.md).

## 3. Estado dos artefatos em `results/`

> 🔴 **Todo o `results/` está OBSOLETO desde 2026-09-10.** A reforma do motor de combate
> daquele dia (dois canais de ação, colisão, timer de stun contínuo, empate como terceiro
> desfecho — ver [11-combat-review.md](11-combat-review.md)) mudou o simulador. Nenhum
> número em `results/` descreve o sistema atual, e o `values.tex` dos dois artigos
> tampouco.

**Não regenerar a bateria ainda.** Mexer no motor ou no fitness invalida `results/`
inteiro de uma vez — não há versionamento parcial —, e ainda faltam decisões que mudam
número: a régua de identidade (A), a formulação do `dominance_penalty` (B), o gate de
convergência (E) e a recalibração dos canônicos (H). A bateria é o **passo 7** da ordem
em [`../../REVIEW.md`](../../REVIEW.md) §8; rodá-la antes disso é trabalho jogado fora.

Quando chegar a vez, a bateria completa é:

```bash
py main.py --seed 42                                    # results.json
py main.py --algorithm nsga2 --seed 42                  # nsga2_results.json + plots
py -m src.tools.multi_run --algorithm both              # multi_run_{ga,nsga2}.json
py -m src.tools.compare_algorithms                      # comparison_ga_vs_nsga2.json
py -m src.tools.external_validation                     # canônico
py -m src.tools.external_validation --nsga2 best_dominance
py -m src.tools.external_validation --nsga2 knee_point
py -m src.tools.external_validation --evolved
py -m src.tools.sensitivity_analysis                    # sensitivity_analysis.json
```

Levou 1h24 na última vez. **Regra:** ao mexer em `config.py`, nos canônicos ou no motor,
todo `results/` fica obsoleto de uma vez — rode a bateria inteira antes de citar
qualquer número.

## 4. Encerrado (para não reabrir por engano)

Resolvido e verificado; o raciocínio completo está em
[`../tcc/04-caminhos-e-decisoes.md`](../tcc/04-caminhos-e-decisoes.md):

- **Reprodutibilidade da seed** — o RNG do Numba é interno; `seed_combat()` é a única
  forma de semeá-lo, e a semeadura reset-ao-base dá Common Random Numbers.
- **`specialization_penalty` removido** — não media diferenciação entre arquétipos e
  quebrava a simetria com o NSGA-II. Escalar e NSGA-II otimizam os mesmos 2 eixos.
- **Objetivo só-decisividade era cego à WR** — hipótese "luta apertada ⟹ WR ~50%"
  falsificada empiricamente; a WR voltou como termo primário.
- **WR por-matchup forçava equilíbrio plano** — incompatível com o ciclo por
  construção; substituída pela WR **global** por personagem (formulação C2).
- **`LAMBDA_DRIFT` 6.0 → 1.0** — com 6.0 o AG escalar ficava colado no canônico.
- **Simplificação do combate** — fora `defense`, `recovery` e hesitação; `stun` virou
  fração do cooldown. (A decisão "intenção→execução" foi por sua vez substituída pelo
  modelo de dois canais em 2026-09-10, e o encurralamento voltou a existir com a
  colisão — ver [11-combat-review.md](11-combat-review.md).)
- **Persistência dos artefatos** — `results.json` grava semente, condição de parada,
  objetivos e `history`, no mesmo contrato do `nsga2_results.json`; o
  `sensitivity_analysis` grava a matriz Δ WR.
- **Teste estatístico entre algoritmos** — `compare_algorithms` (Mann-Whitney U +
  Â₁₂ + Holm-Bonferroni) fecha o item que faltava do 1.1.
- **Reforma do motor de combate (2026-09-10)** — quatro defeitos medidos e corrigidos:
  o avanço incondicional fora do alcance (que matava o espaçamento e invertia o sinal do
  knockback), a exclusividade entre atacar e recuar (que impedia zonear), o
  atravessamento dos corpos e o stun arredondado. Mais o empate como terceiro desfecho,
  que eliminou o viés do lado A, e a regra de impasse, que eliminou a estagnação.
  Números antes/depois em [11-combat-review.md](11-combat-review.md).
