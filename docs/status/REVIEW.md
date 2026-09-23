# Revisão de coerência do sistema

Auditoria passo a passo de cada etapa do sistema, para verificar se as escolhas são
coerentes entre si e com a pergunta de pesquisa. Aberta em 2026-09-10, executada item a
item com uma medição para cada afirmação, e **fechada**: dos ~50 itens auditados, restam
abertos só os da §2, quase todos limites estruturais declarados como escopo.

Este arquivo guarda o resultado da auditoria, não o percurso dela. O porquê de cada
decisão, com os números, está em [`docs/thesis/04-design-decisions.md`](../thesis/04-design-decisions.md); o estado atual do
sistema, em [`docs/reference/`](../reference/README.md). A pauta completa, item a item,
com as medições de cada verificação, está no git: `git show 42918a9:REVIEW.md`.

---

## 1. As incongruências que a auditoria achou

Achados que **não** estavam na pauta original ou que a contradiziam. Todos resolvidos.

| # | Incongruência | Resolução | Onde está o porquê (thesis/04) |
|---|---|---|---|
| **M1** | Recuar era forfeit de dano: o `knockback` tinha derivada **negativa** e o Zoner perdia 100% independentemente de range e knockback | dois canais de ação: a intenção governa a postura, o ataque é regra de resolução | A reforma do combate |
| **M2** | Sem colisão: os corpos se atravessavam 134× por luta, anulando `range` no clinch | `_apply_movement` com movimento simultâneo e parada no ponto de encontro | A reforma do combate |
| **M3** | `stun` arredondado tinha 4 níveis efetivos para atacante rápido — gene categórico | timer contínuo (insuficiente — ver Z2) | A reforma do combate |
| **D** | KO duplo/timeout empatado premiava sempre o lado A, e o round-robin fixa o índice menor como A | empate como terceiro desfecho | A reforma do combate |
| **A** | O AG escalar equilibra **destruindo a identidade** e nenhum dos dois medidores de identidade acusava | drift normalizado pelo range e ponderado pelos genes definidores; duas réguas (estrutural no fitness, funcional post-hoc). O fenômeno permanece — é o achado | A régua de identidade |
| **B** | "O AG vence em `dominance_penalty`" não era "o AG equilibra melhor" — a diferença estava no piso de decisividade | piso rebaixado a guarda de degenerescência; decomposição do dominance reportada | O piso de decisividade |
| **C** | O ponto do AG escalar dominava a fronteira do NSGA-II | causa: o seed canônico era imortal no NSGA-II; população inicial aleatória | A população inicial do NSGA-II |
| **E** | O gate de convergência era inalcançável **por construção** (o termo é quantizado) | gate = o próprio predicado `roster_balanced`; confirmação em stream que o AG nunca viu | O critério de parada do AG |
| **F** | Holm rodava sobre 4 métricas, uma delas degenerada (`p = nan`) | família montada pela variância da amostra conjunta; `_holm` recusa `nan` | A família de testes estatísticos |
| **G** | A sensibilidade usava dois critérios de corte incompatíveis, e o piso de ruído estava subdimensionado | piso medido sob hipótese nula, critério único, `--evolved` | Os modelos nulos |
| **H** | O ciclo canônico não era realizado nem pelo próprio canônico | o problema era geral: **nenhuma** métrica tinha piso — modelos nulos | Os modelos nulos |
| **H′** | E a contagem de arestas era medida a 200 lutas/par, onde a direção de cada aresta de um roster equilibrado é sorteio (2026-09-22) | métrica movida para `src.experiments.cycle_structure`, 16.000 lutas/par, só arestas decididas | O ciclo saiu do `baselines` |
| **R** | Eixo Recurso sem counter: DEFEND sem custo, e o grab ausente era a identidade do Grappler e uma aresta do ciclo | `grab_power`, 8º atributo | O agarrão / quebra de guarda |

A agenda de calibração que veio depois — as sete constantes rotuladas "provisório" —
também está fechada: quatro mantiveram o valor com justificativa escrita, três mudaram
(ver "As constantes provisórias, fechadas com evidência" no thesis/04).

### 1b. A auditoria do zero (2026-09-18)

Uma segunda revisão, feita **sem contexto prévio** — lendo código e artefatos como um leitor
externo —, achou o que a primeira não viu. Todos resolvidos; o porquê e os números de cada
um estão no thesis/04, a partir de "A auditoria do zero".

| # | Incongruência | Resolução | Onde está o porquê (thesis/04) |
|---|---|---|---|
| **Z1** | Período do cooldown `round(5c) + 1`, não `round(5c)` — o argumento "persistência = cooldown mínimo" apoiado num número errado | timers com resto acumulado; o sub-tick do golpe conta no período | Os timers passaram a carregar o resto |
| **Z2** | O stun "contínuo" de M3 ainda era categórico (`ceil`): 4 efeitos em cooldown 1 | resto acumulado também no stun | idem |
| **Z3** | Validador resolvia empate pelo índice (espelho = 4/13 da Layer 1 de graça) e comparava pesos crus | empate contra a asserção; pesos como probabilidade de intenção | O validador parou de dar asserções por empate |
| **Z4** | A régua funcional (Layer 3) era de 5 bits e estava no piso (1/5, p = 0,74); a leitura "supera os nulos" vinha das réguas endógenas | concordância de ranking comportamental (τ); Layer 3 lida separada. Na bateria de 2026-09-21 a régua funcional saiu do piso (L3 3/5, τ 0,31) e mostrou que quem responde é o **controle**, não os nulos | A identidade funcional ganhou uma régua contínua / A identidade funcional saiu do piso |
| **Z5** | Nada isolava o efeito do método: nulos não otimizados; AG × NSGA-II confundia algoritmo com inicialização | controles `λ_drift = 0` e sem semente, n = 20, na bateria | Os controles |
| **Z6** | Manchete no `best_dominance` (o extremo da fronteira); escolha adiada para depois de ver os resultados | manchete `scalar_optimum` decidida antes; relação de Pareto por semente; família de 7 fixa | A manchete da comparação passou ao `scalar_optimum` |
| **Z7** | Validação externa só trocava a semente; veredito ficava mais severo com K | replicação + robustez a regras perturbadas; veredito pelo IC | A validação externa separou replicação de robustez |
| **Z8** | `stagnated_at` media a catraca do ruído | removido | O `stagnated_at` saiu |
| **Z9** | HV saturado em 90% da área; joelho e ideal dependiam da unidade | referência (1,3; 0,4); objetivos normalizados | O hipervolume… / O joelho e o ideal… |
| **Z10** | Sensibilidade sem os pesos, com janela cortada no bound e piso de outra estatística | 11 genes, janela deslizante, piso na estatística certa | A sensibilidade passou a cobrir os pesos |
| **Z11** | `compare_algorithms` e as ferramentas derivadas carimbavam como atual o que vinha de entrada obsoleta; código de medição fora do digest; `--n-seeds` gravava por cima da bateria | `refuse_if_stale`; digest de medição por artefato; roteamento por todo desvio | A proveniência passou a recusar entrada velha |
| **Z12** | Sweeps nas sementes da bateria | sementes 1000–1004 | Os sweeps saíram das sementes da bateria |
| **Z13** | Quatro leituras da bateria de 2026-09-18 sem sustentação (102% do espelho, tríades a 200 lutas, "loteria de 1/24", identidade acima dos nulos) | corrigidas nos docs | Leituras corrigidas |

## 2. O que segue aberto

**Limites estruturais, declarados como escopo** — a auditoria perguntou se cada um
precisava de conserto, e a decisão foi declará-los na Discussão. Detalhe em
[`docs/reference/10-known-issues.md`](../reference/10-known-issues.md) §2:

- **Equilíbrio condicionado a uma política fixa** — os pesos `w_*` *são* a política, e
  ninguém procura exploits contra o roster evoluído. É a objeção mais forte ao resultado;
  a coevolução fica como trabalho futuro.
- **A política é cega ao estado** — a intenção não olha HP, distância nem se o oponente
  está stunado.
- **Crossover só por bloco de personagem** — recombinação intra-personagem depende 100% da
  mutação.
- **Round-robin uniforme** — os 10 pares pesam igual; não modela matchmaking.
- **Hipersensibilidade dos genes de recurso** — com o ataque como regra de resolução, a
  luta é uma corrida de DPS quase determinística; amortecer é trabalho futuro.

**A pergunta que a bateria de 2026-09-21 respondeu:**

- **A identidade funcional sobrevive ao equilíbrio?** Sim, parcialmente, e a evidência é o
  controle. A leitura preliminar (Layer 3 e τ no piso) **não se confirmou**: L3 3/5 e
  τ = 0,31 no indivíduo da seed 42. Contra os 35 nulos um único roster não tem resolução
  (L3 empata com o melhor nulo, τ fica um fio abaixo); contra o braço `λ_drift = 0`, sobre
  20 execuções de cada lado, as duas réguas separam com efeito grande (p_Holm 0,0044 e
  0,00067 na bateria de 2026-09-23) — e o braço sem o termo dá τ = +0,007, o acaso. Segue valendo que o AG quase
  não enxerga a política pelo equilíbrio: os três pesos ocupam o fundo do ranking de
  sensibilidade.

**Uma pergunta que não foi decidida:**

- **`forced_defend` é suficiente?** RETREAT sem espaço vira DEFEND, e o trace separa o
  forçado do escolhido — a Layer 3 do Turtle já usa só o DEFEND escolhido. A pergunta que
  resta é se o encurralamento, permanente desde a colisão, contamina outras métricas de
  comportamento: a distância média do Zoner cai quando ele é encurralado, e isso pode ser
  identidade falhando ou geometria.

**Redação:** o `values.tex` está inteiramente obsoleto, e a macro do `dominance` do AG usa o
número medido **dentro** do laço enquanto as outras células da mesma linha usam o de fora —
ver [`docs/status/HANDOFF.md`](HANDOFF.md) §4.

## 3. Ordem de execução

O critério foi **dependência**, não gravidade: cada camada condiciona a de cima. E uma
restrição dura — mexer no motor ou no fitness invalida `results/` inteiro, então tudo o
que muda número tinha de ser resolvido **antes** de uma única regeneração final.

| # | Bloco | Por que aqui | Estado |
|---|---|---|---|
| 0 | **Integridade do combate** (M1, M1b, M2, M3, impasse) | se alguma mecânica está quebrada, todo o resto mede um simulador errado | ✅ 2026-09-10 |
| 1 | **D** — empate no desempate | bug de camada de combate; muda todos os números | ✅ 2026-09-10 |
| 2 | **A** + **B** — o que é "identidade" e o que é "equilíbrio" no fitness | as duas decisões de design; mudam a função objetivo | ✅ 2026-09-16 |
| 3 | **E** — gate de convergência | o limiar depende da métrica definida em (2) | ✅ 2026-09-16 |
| 4 | **C** — sub-convergência do NSGA-II | diagnosticar com o fitness já definido, senão testa duas vezes | ✅ 2026-09-16 |
| 5 | **H** — modelos nulos (era "recalibrar canônicos p/ o ciclo existir") | o ciclo não podia ser evidência; o que faltava era piso em toda métrica | ✅ 2026-09-16 |
| 6 | **R** — guard break / grab | decisão registrada: só depois de A–C | ✅ 2026-09-16 |
| 7 | **bateria completa** — regenerar `results/` | um corte único, com tudo estabilizado | ✅ 2026-09-16 |
| 8 | **F**, **G** | camada de análise: não exigem re-rodar o AG | ✅ 2026-09-16 |
| 9 | **menores** (sujeira de código) + docs + `values.tex` | limpeza e sincronização final | menores ✅ 2026-09-16; bibliografia ✅ 2026-09-17; falta `values.tex` |
| 10 | **agenda de calibração** (sete constantes provisórias) + regeneração final | (1)–(7) fechados; bateria regenerada sob o motor final | ✅ 2026-09-16 |
| 11 | **instrumentação** — proveniência nos artefatos + marcos de convergência por semente | um artefato que não carrega a config que o produziu não se auto-verifica; e sem os marcos, "velocidade" é n = 1 | ✅ 2026-09-17 |
| 12 | **sweeps** de `LAMBDA_DRIFT`, pesos do dominance e elitismo/torneio, em orçamento reduzido | exploratório quer ORDENAÇÃO, e ordenação transfere de orçamento — ~10 min por braço | ✅ 2026-09-17/18: os três testaram o valor vigente e ele passou; `config.py` inalterado |
| 13 | **bateria** — `run_battery.ps1` (n = 20) | poder estatístico: 44,4% → 85,9% | ✅ 2026-09-21: as **seis** métricas de Holm significativas, com efeito grande |
| 14 | **pendências do known-issues** — default de sementes fora do carimbo, pool persistente, contagem no veredito externo, CRN por luta | o CRN por luta muda todos os sorteios | ✅ 2026-09-18 |
| 15 | **auditoria do zero** (Z1–Z13) — motor, instrumentos de identidade, controles, protocolo de comparação e de validação, proveniência | antes da bateria: o motor e o protocolo mudam o que ela mede | ✅ 2026-09-18; sweeps + bateria re-rodados, órfãos removidos e resultados relidos em ✅ 2026-09-21 |
