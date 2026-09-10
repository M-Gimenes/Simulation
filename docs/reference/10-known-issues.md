# 10 — Pontos em aberto

O que **ainda está aberto** no sistema, em 2026-09-10. Não é histórico: a trajetória
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
isso é afirmado, não medido. Ressalva de método: o AG escalar com
`LAMBDA_DRIFT = LAMBDA_DOMINANCE = 1.0` minimiza a **soma** (L1) dos dois objetivos,
enquanto o representante `ideal_point` da fronteira minimiza a **norma euclidiana**
(L2). São pontos diferentes da mesma fronteira; ao comparar escalar × NSGA-II, o
representante usado precisa ser declarado (o `multi_run` grava
`nsga2_representative`, default `best_dominance`).

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
- **Grappler sem asserção comportamental.** A Layer 3 do validador tem 4 asserções
  para 5 arquétipos: o combate não modela grab/throw, então a identidade do Grappler
  não tem expressão comportamental distinta do corpo-a-corpo do Rushdown. Registrado
  no relatório do validador, fora do denominador. Achado honesto, não bug.
- **Alinhamento CRN imperfeito depois do 1º matchup.** Toda avaliação reseta o RNG do
  combate ao mesmo seed-base, mas cada luta consome um número variável de sorteios —
  a posição do stream diverge entre indivíduos nos matchups seguintes. Muito melhor
  que seeds independentes; alinhamento perfeito exigiria semear por
  `(base, matchup_idx, sim_idx)`. Detalhe em
  [09-reproducibility.md](09-reproducibility.md).

## 3. Estado dos artefatos em `results/`

O commit `3e64bbd` (28/06) mudou de uma vez `MATCHUP_WR_CAP` (0.20→0.15), os bounds
de dano ([10,20]→[15,30]), os danos canônicos dos 5 arquétipos e
`DEFEND_DAMAGE_REDUCTION` (0.5→0.6). Artefatos gerados **antes** dele descrevem um
sistema que não existe mais — e os dois `multi_run` publicados nos artigos eram
exatamente esse caso.

Todos os artefatos em `results/` foram **regerados em 2026-09-10** com o código
atual, com a bateria completa:

```bash
py main.py --seed 42                                    # results.json (agora com seed + history)
py main.py --algorithm nsga2 --seed 42                  # nsga2_results.json + plots
py -m src.tools.multi_run --algorithm both              # multi_run_ga.json + multi_run_nsga2.json
py -m src.tools.compare_algorithms                      # comparison_ga_vs_nsga2.json
py -m src.tools.external_validation                     # canônico
py -m src.tools.external_validation --nsga2 best_dominance
py -m src.tools.external_validation --nsga2 knee_point
py -m src.tools.external_validation --evolved
py -m src.tools.sensitivity_analysis                    # sensitivity_analysis.json
```

**Regra:** ao mexer em `config.py`, nos canônicos ou no motor de combate, todo
`results/` fica obsoleto de uma vez — não há versionamento parcial. Rode a bateria
inteira antes de citar qualquer número.

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
- **Simplificação do combate** — fora `defense`, `recovery`, hesitação e
  encurralamento; `stun` virou fração do cooldown; decisão virou intenção→execução.
- **Persistência dos artefatos** — `results.json` grava semente, condição de parada,
  objetivos e `history`, no mesmo contrato do `nsga2_results.json`; o
  `sensitivity_analysis` grava a matriz Δ WR.
- **Teste estatístico entre algoritmos** — `compare_algorithms` (Mann-Whitney U +
  Â₁₂ + Holm-Bonferroni) fecha o item que faltava do 1.1.
