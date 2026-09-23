# Estado: a investigação do AG escalar fechou (2026-09-23)

Este arquivo era o registro de uma investigação em aberto. Ela terminou, e o achado virou
braço do protocolo. **O conteúdo está nos docs**, não aqui:

- **O achado e os números** — [`docs/thesis/07-findings-and-limitations.md`](docs/thesis/07-findings-and-limitations.md),
  §«O AG escalar não é ótimo na própria função» e §«O híbrido responde o achado do AG escalar».
- **As decisões** — [`docs/thesis/04-design-decisions.md`](docs/thesis/04-design-decisions.md):
  o desenho do híbrido, a adoção, os cinco consertos adiados, `MULTI_RUN_SIMS`, e a
  verificação de que a política de adiar conserto inerte estava certa.
- **Os números citáveis** — [`docs/status/HANDOFF.md`](docs/status/HANDOFF.md) §2.

## O que a noite de 2026-09-22/23 produziu

**1. O AG escalar não é ótimo na própria função, e o motivo é ruído.** `dominance` é
amostrado (desvio 0,015–0,028 a 150 lutas), `drift` é exato. Passada a geração ~31 o
gradiente verdadeiro do `dominance` acabou mas o ruído não — e ele é ~60× maior que o
ganho de drift por geração. A linhagem de drift mínimo morre na **geração 7**.

**2. O híbrido conserta isso, e foi adotado.** NSGA-II 75 gerações → AG escalar 75, mesmo
orçamento total. Contra o AG escalar, n = 20, pareado: drift 0,1663 contra 0,2473,
τ **+0,5215 contra +0,2811**, L1+2 15 contra 11, L3 4 contra 3 — todas com efeito grande
—, e **as duas métricas de equilíbrio não se movem** (Â₁₂ 0,51 e 0,49; 16/20 rosters
equilibrados nos dois). Preço: velocidade (converge na geração 98 contra 31).

**3. `MULTI_RUN_SIMS` 200 → 1000, e isso derrubou uma afirmação da tese.** O controle
`λ_drift = 0` dizia que tirar a identidade **piora** o equilíbrio (p_Holm = 0,038). Com a
régua fina e os **mesmos indivíduos**: p_Holm = 0,059, não significativo. Direção e
efeito (Â₁₂ = 0,30) intactos. O braço λ = 0 é o mais ruidoso, e régua grossa penaliza mais
quem tem mais ruído — o teste pareado, por ter mais poder, foi justamente o que
transformou viés de medição em significância.

**4. Os consertos de motor são comprovadamente inertes.** 40 de 40 execuções com semente
produziram genes bit a bit idênticos aos da bateria anterior. Nenhum número de identidade
mudou; só o que a régua mede.

**5. O ciclo autoral saiu do `baselines` para experimento próprio**
(`src.experiments.cycle_structure`, 16.000 lutas por par). A 200 lutas a contagem media
ruído. O veredito não mudou de sinal — 105 de 186 arestas decididas na direção autoral
(56,5%, p = 0,091) contra 49,7% dos nulos — mas deixou de ser ruído e virou teste. E
apareceu o achado que a resolução escondia: **o canônico também não tem um ciclo** (6/10,
com as 4 que quebra invertidas por completo; 1,00 de 5 tríades circulares — hierarquia).

## O que segue aberto

Nada de instrumentação. Em [`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md):

- **um conserto adiado** — separar medição de impressão no `analyze_matchups`, que hoje
  faz uma edição cosmética obsoletar a bateria inteira;
- **uma pergunta declarada** — qual o melhor split do híbrido. O 0,5 veio de desempate de
  simplicidade; medi-lo exigiria um sweep no orçamento inteiro;
- os **limites estruturais** (política fixa e cega ao estado, crossover por bloco, …), que
  são escopo declarado e vão para a Discussão.

O que falta é **redação** — [`docs/status/HANDOFF.md`](docs/status/HANDOFF.md) §4.

## `diagnostics/`

Scripts da investigação, fora de `src/` e sem carimbo de proveniência. Os que ainda
servem: `battery_numbers.py` (extrai do disco todo número que os docs citam — usar sempre
que uma bateria nova sair), `exp_holdout.py` (reavalia um braço a N lutas em sorteios
novos) e `exp_diag.py` (réplica instrumentada do laço). Os `exp_cycle*.py` viraram
`src/experiments/cycle_structure.py` e ficam só como rastro.
