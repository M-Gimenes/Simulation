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
| **M3** | `stun` arredondado tinha 4 níveis efetivos para atacante rápido — gene categórico | timer contínuo | A reforma do combate |
| **D** | KO duplo/timeout empatado premiava sempre o lado A, e o round-robin fixa o índice menor como A | empate como terceiro desfecho | A reforma do combate |
| **A** | O AG escalar equilibra **destruindo a identidade** e nenhum dos dois medidores de identidade acusava | drift normalizado pelo range e ponderado pelos genes definidores; duas réguas (estrutural no fitness, funcional post-hoc). O fenômeno permanece — é o achado | A régua de identidade |
| **B** | "O AG vence em `dominance_penalty`" não era "o AG equilibra melhor" — a diferença estava no piso de decisividade | piso rebaixado a guarda de degenerescência; decomposição do dominance reportada | O piso de decisividade |
| **C** | O ponto do AG escalar dominava a fronteira do NSGA-II | causa: o seed canônico era imortal no NSGA-II; população inicial aleatória | A população inicial do NSGA-II |
| **E** | O gate de convergência era inalcançável **por construção** (o termo é quantizado) | gate = o próprio predicado `roster_balanced`; confirmação em stream que o AG nunca viu | O critério de parada do AG |
| **F** | Holm rodava sobre 4 métricas, uma delas degenerada (`p = nan`) | família montada pela variância da amostra conjunta; `_holm` recusa `nan` | A família de testes estatísticos |
| **G** | A sensibilidade usava dois critérios de corte incompatíveis, e o piso de ruído estava subdimensionado | piso medido sob hipótese nula, critério único, `--evolved` | Os modelos nulos |
| **H** | O ciclo canônico não era realizado nem pelo próprio canônico (5/10 = acaso) | o problema era geral: **nenhuma** métrica tinha piso — modelos nulos | Os modelos nulos |
| **R** | Eixo Recurso sem counter: DEFEND sem custo, e o grab ausente era a identidade do Grappler e uma aresta do ciclo | `grab_power`, 8º atributo | O agarrão / quebra de guarda |

A agenda de calibração que veio depois — as sete constantes rotuladas "provisório" —
também está fechada: quatro mantiveram o valor com justificativa escrita, três mudaram
(ver "As constantes provisórias, fechadas com evidência" no thesis/04).

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
| 13 | **bateria** — `run_battery.ps1` (n = 20) | poder estatístico: 44,4% → 85,9% | ✅ 2026-09-18: as três métricas de Holm significativas |
| 14 | **pendências do known-issues** — default de sementes fora do carimbo, pool persistente, contagem no veredito externo, CRN por luta | o CRN por luta muda todos os sorteios | ✅ 2026-09-18; falta re-rodar sweeps + bateria (`run_overnight.ps1`) e reler todos os resultados |
