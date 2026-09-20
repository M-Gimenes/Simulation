# Retomada — estado do projeto

Este arquivo é o retrato do **agora**: o que está feito, o que falta e os resultados da
última bateria. Não é histórico. A trajetória das decisões (que problema cada mudança
resolveu, com os números) vive em
[`docs/thesis/04-design-decisions.md`](../thesis/04-design-decisions.md); o registro de
trabalho das sessões anteriores, no git (a última versão longa deste arquivo é
`git show 42918a9:HANDOFF.md`).

- Como o sistema funciona: [`docs/reference/`](../reference/README.md).
- Pendências e limites do sistema: [`docs/reference/10-known-issues.md`](../reference/10-known-issues.md).
- A auditoria de coerência e o que dela segue aberto: [`docs/status/REVIEW.md`](REVIEW.md).

---

## 0. Comece por aqui

1. **O ambiente não sobe sozinho.** `.venv/` é gitignored e o Python do sistema (3.14)
   não tem `numpy`/`numba`/`scipy`. Rode `setup.ps1` antes de qualquer coisa.
2. **`results/` está COMPLETO, mas OBSOLETO — e os números VÃO MUDAR.** Depois da
   bateria de 2026-09-18 o motor mudou (§3): o CRN passou a semear **cada luta** e os
   timers passaram a carregar o resto (período do cooldown e stun exatos em média) — os
   dois trocam todos os números. E o protocolo ganhou os dois controles, a manchete no
   `scalar_optimum`, a concordância de ranking e a validação externa com regras
   perturbadas. **Rodar `.\scripts\run_overnight.ps1`** (16 braços, ~1h40, + bateria de 16
   passos, ~6h12), conferir com `py -m src.tests.test_provenance`, **limpar os artefatos
   órfãos** (lista em [`10-known-issues`](../reference/10-known-issues.md) §1, passo 3) e
   então **reler tudo o que é resultado**: a §2 deste arquivo, o `docs/thesis/`, os
   números do `CLAUDE.md` e as conclusões dos três sweeps.
3. **A base experimental está definida, e falta rodá-la.** Motor e fitness calibrados, os
   três sweeps exploratórios feitos, e — depois da auditoria do zero de 2026-09-18 — os
   controles que isolam o efeito do método (`λ_drift = 0`, AG sem semente canônica) dentro
   da bateria. A pergunta que a próxima bateria responde de fato: se o equilíbrio preserva
   a identidade **funcional** — na leitura preliminar, não preserva (§3).
4. **O que falta, depois da bateria:** a **redação** (§4) — a começar pelo `values.tex`,
   inteiramente obsoleto.

## 1. O modelo em quatro eixos

| eixo | do que é feito | estado |
|---|---|---|
| **Espaço** | range, speed, knockback, posição, campo, colisão | ✅ coerente — dois canais de ação, colisão, regra de impasse |
| **Tempo** | cooldown, stun, persistência da intenção | ✅ coerente — os timers carregam o resto entre golpes (período e stun exatos em média); a persistência é 5 sub-ticks = 1 tick = o período do atacante mais rápido, então quem tem `cooldown=1` e sorteia GUARDA abre mão de exatamente **uma** janela |
| **Recurso** | hp, damage, DEFEND, grab_power | ✅ coerente — o agarrão é o counter da guarda |
| **Política** | 3 pesos, amostragem proporcional | contínua, e a escala dos pesos não contamina a identidade (`drift_genes` reescala); segue **cega ao estado**: não olha HP, distância nem se o oponente está stunado — limite declarado |

## 2. Resultados da bateria (2026-09-18, n = 20) — sob rotação, persistência 5 e drift invariante

> ⚠️ **Estes números são de ANTES do CRN por luta e da correção dos timers (§3), que trocam
> todos os sorteios.** A próxima bateria os substitui. Esta seção precisa ser reescrita
> contra ela — tabelas, leituras e as conclusões dos sweeps —, e nada daqui deve ser citado
> até lá. **Quatro leituras desta seção foram corrigidas** pela auditoria do zero de
> 2026-09-18 e estão marcadas no lugar (ver [`thesis/04`](../thesis/04-design-decisions.md),
> "Leituras corrigidas").

`results/` está **atual e coerente**. Bateria: AG e NSGA-II na seed 42, `multi_run` com
**20 sementes** × 2 algoritmos, `compare_algorithms`, os quatro rótulos de
`external_validation`, `sensitivity_analysis` e `baselines` com 30 nulos.

A bateria de 2026-09-18 **estende** a de 2026-09-17 em vez de substituí-la: as sementes
42–51 reproduziram bit a bit as 10 anteriores, nos dois algoritmos, e os artefatos da seed
42 (`single_run/ga.json`, `single_run/nsga2.json`, as validações externas, os nulos) saíram
idênticos. Por isso as tabelas de degradação, de validação externa e de modelos nulos
abaixo seguem valendo como estavam; o que muda é o agregado, que ganhou 10 sementes.

### O resultado que domina todos os outros: o número de dentro do laço virou honesto

`dominance` medido **durante a busca** contra o mesmo indivíduo medido em **10 condições
independentes** (`external_validation`, seeds 10000+, 500 sims/matchup):

| | AG escalar: dentro → fora | degradação | NSGA-II `best_dominance`: dentro → fora | degradação |
|---|---|---|---|---|
| **bateria 2026-09-16** | 0,0039 → 0,0804 ± 0,0158 | **21×** | 0,0140 → 0,1148 ± 0,0074 | **8,2×** |
| **bateria 2026-09-17** | 0,0153 → **0,0178 ± 0,0065** | **1,2×** | 0,0483 → **0,0545 ± 0,0108** | **1,1×** |

Era o objetivo declarado da rotação, e o efeito é maior do que o A/B previa — nos **dois**
algoritmos. Antes, o equilíbrio reportado era em boa parte ajuste a uma realização do RNG;
agora o número medido durante a busca **é** o número que sobrevive fora dela.

### Agregado (20 sementes, reavaliação independente na seed 9999)

Média ± desvio sobre as 20 execuções; o NSGA-II representado pelo `best_dominance`.

| | dominance | drift | hard-counters | roster equilibrado | bonecos em banda |
|---|---|---|---|---|---|
| **AG escalar** | **0,0436** ± 0,0177 | 0,2503 ± 0,0413 | **0,40** ± 0,68 | **14/20** (70%) | 5/5 em 20/20 |
| **NSGA-II** | 0,0703 ± 0,0508 | **0,1757** ± 0,0449 | 1,75 ± 1,59 | 4/20 (20%) | 5/5 em 20/20 |

Cada um ocupa um extremo nítido do trade-off, e **as três métricas da família de Holm
seguem significativas a n = 20**, todas com efeito grande:

| métrica | mediana AG | mediana NSGA-II | p (Holm) | Â₁₂ | a n = 10: p (Holm) · Â₁₂ | vencedor |
|---|---|---|---|---|---|---|
| `dominance_penalty` | 0,0387 | 0,0599 | **0,0123** | 0,27 | 0,0257 · 0,20 | AG escalar |
| `drift_penalty` | 0,2526 | 0,1816 | **0,00007** | 0,89 | 0,0030 · 0,94 | NSGA-II |
| hard-counters/execução | 0 | 1 | **0,0018** | 0,21 | 0,0110 · 0,14 | AG escalar |

(Na bateria de 2026-09-16, nenhuma era significativa e o melhor p era 0,0772.)

**O que o n = 20 acrescentou ao n = 10.** A conclusão não mudou e os p caíram, como se
espera ao dobrar a amostra. Mas os três Â₁₂ **andaram na direção de 0,5** (0,20 → 0,27,
0,94 → 0,89, 0,14 → 0,21): as 10 sementes novas foram mais favoráveis ao NSGA-II —
nas sementes 52–61 ele fez 1,1 counter por execução contra 2,4 nas 42–51, e 3/10 rosters
equilibrados contra 1/10. O efeito medido a n = 10 estava **inflado**, como é típico de
amostra pequena; o de n = 20 é a estimativa a citar, e ele continua grande nos três.

A decomposição diz **de onde** vem a diferença, e a n = 20 a leitura ficou mais nítida:
`global_term` **0,0375 contra 0,0382** — praticamente iguais (a n = 10 eram 0,0375 contra
0,0470) —, e `cap_term` **0,0000 contra 0,0357**. **Toda** a vantagem do AG em dominance
vem de counters duros. Globalmente, os dois equilibram o roster igual; o NSGA-II perde
porque deixa pares passarem do teto. O composto sozinho esconderia isso.

### Por que o NSGA-II "piorou" em dominance — e por que não é regressão

O hipervolume ficou **igual** — 1,8081 ± 0,0370 a n = 20, 1,8090 ± 0,0470 a n = 10, 1,8084
na bateria de 2026-09-16: a fronteira não perdeu qualidade, ela **se deslocou**. A causa é assimetria entre os dois objetivos:

> **`drift` é determinístico** — função pura dos genes, sem RNG. **`dominance` é o único
> objetivo estocástico.** A rotação torna a dominância mais cara de otimizar e não toca
> no drift. A fronteira segue alcançando a ponta fiel (que não depende do stream) e
> **retrai na ponta equilibrada**, que antes era alcançada explorando uma realização
> específica. O hipervolume não muda porque a fronteira se redistribui no mesmo envelope.

E `best_dominance` é, por definição, o extremo de baixa dominância — quando essa ponta
retrai, o representante piora. **A piora é a correção.**

### Contra os modelos nulos (melhor do AG, 30 nulos)

> ⚠️ **O passo das `baselines` na bateria rodou com 8 nulos aleatórios, não 30.** O `run_battery.ps1`
> chamava `baselines --evolved` sem `--n-random`, e o default do tool era 8 — a resolução
> do p caiu de < 0,03 para < 0,08 sem nenhum erro. Corrigido em 2026-09-18 na fonte:
> `N_RANDOM_DEFAULT` passou a 30, o valor do protocolo, e o artefato foi regerado — saiu
> **idêntico** ao de 2026-09-17. A tabela abaixo é a dele.

| métrica | valor | piso médio | pior nulo | posição | p |
|---|---|---|---|---|---|
| validador (L1-L3) | 13/23 | 6,37 | 10 | 40% | **< 0,03** |
| validador (L1+L2) | 12/18 | 5,43 | 9 | 52% | **< 0,03** |
| `drift_penalty` | 0,218 | 0,409 | 0,327 | 47% | **< 0,03** |
| `dominance_penalty` | 0,026 | 1,136 | 0,025 | **102%** | 0,06 |
| arestas do ciclo | 4/10 | 5,0 | 8 | **−20%** | 0,97 |
| validador (L3), lido separado | 1/5 | ~1 | 3 | — | **0,74** |

Três leituras — **corrigidas em 2026-09-18**:

1. ~~A identidade supera TODOS os nulos nos três eixos (p < 0,03).~~ Supera nas réguas
   **estruturais** — drift (no fitness) e Layers 1-2 (endógenas), onde vencer nulos não
   otimizados é quase garantido. Na régua **funcional** isolada, a Layer 3 dá 1/5 com
   p = 0,74: no piso. (A concordância de ranking, medida depois, dá τ = 0,19, p = 0,14.)
2. ~~102% do espelho, mais equilibrado que a solução trivial (0,026 contra 0,025).~~ 0,026 é
   *maior* que 0,025. O `dominance` do evoluído fica **no nível** dos espelhos (0,025–0,037,
   fora o do Zoner) — o piso de ruído a 200 lutas. Leitura certa: tão equilibrado quanto a
   simetria perfeita, dentro do ruído.
3. **O ciclo autoral não é realizado** — 4/10 arestas. ~~Loteria de 1/24~~: o motivo real é
   que o próprio canônico só realiza 6/10 dele. ~~Tríades em 4,0 com pares em 43%–55%,
   arestas decididas~~: a 200 lutas esse espalhamento é o do puro ruído (espelhos chegam a
   4,0). A evidência de pares decididos é a da validação externa (5000 lutas por par: os 10
   pares com |z| ≥ 3,6, torneio regular) — e a intransitividade é em boa parte implicada
   pelo objetivo.

### Validação externa — os quatro rótulos, mesmo corte

> Sob o desenho antigo (10 sementes, veredito "counter em alguma condição"). A validação
> externa agora separa replicação de robustez a regras perturbadas, com veredito pelo IC
> de 5000 lutas por par, e a bateria valida o `scalar_optimum` no lugar do
> `best_dominance`.

| indivíduo | `dominance` fora | drift | bonecos robustos | counters | veredito |
|---|---|---|---|---|---|
| canônico | 1,2762 ± 0,0024 | 0,0000 | 1/5 | 9/10 | FRÁGIL |
| **AG escalar** | **0,0178 ± 0,0065** | 0,2178 | **5/5** | **0/10** | **ROBUSTO** |
| NSGA-II `best_dominance` | 0,0545 ± 0,0108 | 0,2004 | 5/5 | 1/10 | FRÁGIL |
| NSGA-II `knee_point` | 0,2496 ± 0,0194 | 0,1082 | 5/5 | 9/10 | FRÁGIL |

**O AG escalar é o primeiro roster do projeto a passar o veredito.** 5/5 bonecos em banda
nas 10 condições, **nenhum** par virando counter duro em nenhuma delas, com as WR por par
espalhadas em [42,0%, 57,8%] — equilíbrio com arestas decididas, não achatamento. Na
bateria anterior esse mesmo rótulo dava 3/10 counters.

No `best_dominance` o único counter é **Grappler × Turtle a 66,7% ± 1,7%**, que é uma
**aresta canônica do ciclo** ("grab é o counter canônico ao bloqueio"): o roster realiza a
aresta autoral, apenas 1,7 p.p. acima do teto de 65%, e reprova por isso. Vale como
calibração do próprio veredito — o quantificador binário ("counter em ALGUMA das 10
condições", 100 oportunidades de falhar) é severo, mas **discrimina**: com o mesmo
critério o AG passa limpo. O veredito ficou binário, e desde 2026-09-18 o relato traz
**em quantas** condições cada par vira counter: Grappler × Turtle em 9/10 no
`best_dominance` — sistemático, não tropeço de amostragem —, e no `knee_point` sete pares
em 9–10/10 ao lado de dois esporádicos (4/10 e 6/10).

### Sweep de λ (2026-09-17) — orçamento reduzido, λ = 1,0 confirmado

5 braços × 5 sementes a **pop 120 × 60 gerações** (16% do custo, 25 min). Artefatos em
`results/exploratory/`; a bateria em `results/multi_run/` não foi tocada.

| λ_drift | peso rel. do dominance | dominance | drift | counters | convergiu |
|---|---|---|---|---|---|
| 0,25 | 4× | **0,0425** ± 0,0107 | 0,3681 | 0,4 | 100% |
| 0,5 | 2× | 0,0483 ± 0,0189 | 0,3740 | 0,6 | 100% |
| **1,0** | 1× | 0,0485 ± 0,0187 | 0,2982 | 0,6 | 80% |
| 2,0 | ½× | 0,1891 ± 0,1648 | 0,1763 | 4,0 | 40% |
| 4,0 | ¼× | 0,3365 ± 0,0803 | **0,0971** | 7,8 | 0% |

**Só a razão entre os dois λ importa** (a seleção é por torneio, ordinal), então variar
`λ_drift` com `λ_dominance` fixo em 1,0 percorre a família inteira. O trade-off é
monotônico — drift cai 3,8×, dominance sobe 7,9× —, mas o achado é o **formato**:
`dominance` fica plano em ~0,048 até λ = 1,0 e só então explode. λ = 1,0 é o **último ponto
onde identidade sai de graça**; contra λ = 0,25 entrega drift 0,070 melhor por dominance
0,006 pior. E λ = 4,0 reproduz a patologia que os docs atribuíam ao antigo λ = 6,0: drift
0,0971 (quase canônico) com 7,8 de 10 pares virando counter duro.

**Nada mudou no `config.py`, e nada precisava mudar** — o sweep testou o valor vigente, não
buscou um novo. O ganho é que λ = 1,0 deixou de ser escolha por eliminação.

> **O ajuste ao stream, agora quantificado.** Os contadores do gate deram, sobre **62
> disparos em 25 execuções**, taxa de recusa de **67% a 83%** (75% · 67% · 73% · 83% por
> braço). Ou seja: **~3 de cada 4 vezes em que o roster parece equilibrado sob o stream de
> treino, ele não sobrevive a um stream inédito.** É o que a rotação por geração existe para
> combater, medido sobre amostra e não sobre a anedota de n = 1 abaixo.

### Sweep dos pesos do dominance (2026-09-17) — os secundários são indispensáveis

Mesmo orçamento reduzido, 5 braços × 5 sementes. **A comparação é pelos TERMOS**, não pelo
`dominance_penalty` — os pesos o definem.

| pesos g/cap/decis | global_term | cap_term | decis_term | drift | counters | conv |
|---|---|---|---|---|---|---|
| 1 / 2 / 0,5 | 0,0455 | **0,0000** | 0,0000 | 0,3372 | 0,2 | 100% |
| 1 / 1 / 1 | 0,0484 | 0,0108 | 0,0000 | 0,3470 | 0,2 | 100% |
| **1 / 0,5 / 0,5** | 0,0454 | 0,0063 | 0,0000 | 0,2982 | 0,6 | 80% |
| 1 / 0,5 / 0 | 0,0534 | 0,1440 | 0,0569 | 0,2454 | 3,2 | 40% |
| 1 / 0 / 0 | **0,0170** | **0,9030** | 0,3114 | 0,1548 | **10,0** | 0% |

**`1/0/0` é a falsificação.** Sem os secundários o AG atinge o **melhor `global_term` de
todos** (0,0170 — é a única coisa que resta a otimizar) e entrega **10/10 counters duros em
5/5 sementes**: os cinco na banda global, toda luta um massacre. É o *blowout-coinflip* que
a formulação C2 previa como razão de existir do cap — era raciocínio, agora é medida.

**E o `decis_term` não é inerte.** Removê-lo sozinho triplica os counters (0,6 → 3,2), leva
a convergência de 80% para 40% e **piora o próprio `cap_term`** (0,0063 → 0,1440). Ler
0,0000 no indivíduo final é o termo tendo funcionado.

**`config.py` inalterado:** subir o cap para 2,0 melhora counters e convergência ao custo de
drift, mas a n = 5 (0,6 ± 0,5 contra 0,2 ± 0,4) não se distingue de ruído.

Os braços de λ e de pesos foram **re-rodados** em 2026-09-18, junto dos de elitismo/torneio,
para que os 16 saíssem do mesmo digest de motor — e reproduziram bit a bit, semente a
semente, os de 2026-09-17. A refatoração do `operators.py` que o sweep seguinte exigiu não
mudou comportamento.

### Sweep de elitismo / torneio (2026-09-18) — 10% / 3 mantidos

Mesmo orçamento reduzido (pop 120 × 60, 5 sementes). Os dois só existem no AG escalar — o
NSGA-II seleciona por rank de Pareto e torneio binário —, então só ele roda.

| braço | global_term | cap_term | drift | counters | roster eq. | convergiu |
|---|---|---|---|---|---|---|
| elitismo 0 | 0,0593 | 0,0076 | 0,2746 | 1,4 ± 1,3 | 2/5 | 80% |
| elitismo 5% | **0,0391** | 0,0111 | 0,2723 | 1,0 ± 1,0 | 2/5 | 60% |
| **elitismo 10% · torneio 3** | 0,0454 | **0,0063** | 0,2982 | **0,6 ± 0,5** | 2/5 | 80% |
| elitismo 20% | 0,0473 | 0,0327 | 0,2736 | 1,6 ± 1,5 | 1/5 | 60% |
| elitismo 30% | 0,0516 | 0,0440 | 0,3136 | 1,8 ± 1,3 | 1/5 | 60% |
| torneio 2 | 0,0439 | 0,0884 | **0,2411** | 2,0 ± 2,9 | 2/5 | 40% |
| torneio 5 | 0,0528 | 0,1049 | 0,2575 | 2,2 ± 1,9 | 1/5 | 20% |
| torneio 7 | 0,0459 | 0,0886 | 0,2786 | 2,2 ± 3,3 | 1/5 | 60% |

**Nenhum braço domina o default.** Ele tem o menor número de counters e o menor `cap_term`
dos oito; as alternativas ganham um pouco de drift e pagam em counters. Mas a n = 5 nada
disso se separa do ruído — os desvios de counters chegam a 3,3 —, e o torneio ainda dá um
padrão **não monotônico** (3 melhor que 2 e que 5, 5 igual a 7), que é mais a cara de ruído
do que de um ótimo de pressão seletiva. O braço sem elitismo, o informativo, mostra pouco:
`global_term` piora de 0,0454 para 0,0593, o pior dos oito, e o resto fica dentro do ruído.

**`config.py` inalterado.** O que o sweep estabelece é que 10% / 3 deixam de ser "valores de
manual" e passam a "testados neste problema, sem braço que os supere" — não que sejam o
ótimo.

### Convergência e estagnação — agora sobre 20 sementes

A n = 20 o eixo de velocidade deixou de ser anedota:

- **Convergiu em 20/20 sementes** (sempre confirmado num stream que o AG nunca viu), na
  geração **34,8 ± 17,1** (18 a 75). A seed 42 converge na 39.
- ~~Estagnou em 10/20, na geração 99,5 ± 21,2.~~ O evento media a catraca do ruído (o
  "melhor fitness histórico" sob rotação do stream é o máximo de valores ruidosos) e foi
  **removido** em 2026-09-18.
- Convergir não é terminar equilibrado: das 20 sementes convergidas, **14** terminam com o
  roster equilibrado na reavaliação.
- **O gate disparou 70 vezes e a confirmação recusou 50 (71%)**, dentro da faixa de 67%–83%
  medida nos braços do sweep — agora no orçamento de produção.

### Sensibilidade — a primeira medição sobre o indivíduo atual

> Sob o desenho antigo (8 atributos, janela cortada no bound, piso de uma célula). A
> análise agora cobre os 11 genes com janela de 2σ e o piso na estatística classificada;
> a leitura preliminar sob o desenho novo está na §3.

> ⚠️ **O `sensitivity_analysis.json` versionado estava obsoleto e marcado como atual.** Era
> do indivíduo de 2026-09-16, sob persistência 10 (piso 7,9% — o número que o
> [`docs/thesis/04`](../thesis/04-design-decisions.md) registra para essa época), e recebeu o carimbo
> retroativo de 2026-09-17 junto com os demais. O carimbo foi justificado reproduzindo
> `single_run/ga.json` e `single_run/nsga2.json` e **inferindo** o resto ("função determinística
> desses dois mais o motor"). A inferência vale para quem foi regerado depois deles, e este
> não tinha sido. A bateria o regerou, e re-rodar deu resultado idêntico — a ferramenta é
> determinística; o arquivo é que era velho.

| gene | \|Δ WR\| (200 sims, 3 rep.) | \|Δ WR\| (600 sims, 12 rep.) | sinal/ruído (600) |
|---|---|---|---|
| `range` | 39,3% | 39,4% | 7,7 |
| `attack_cooldown` | 21,3% | 23,3% | 4,6 |
| `hp` | 19,1% | 20,0% | 3,9 |
| `damage` | 18,3% | 19,7% | 3,9 |
| `grab_power` | 11,0% | 9,8% | 1,9 |
| `stun` | 7,3% | 7,7% | 1,5 |
| `speed` | 7,1% | 5,9% | 1,2 |
| `knockback` | 6,7% | 5,5% | 1,1 |
| *piso de ruído (máx.)* | *5,7%* | *5,1%* | |

A medição de 600 sims foi feita à parte, para decidir o `knockback`; o artefato em
`results/` é o da bateria (200 sims). **Nenhum gene fica abaixo do piso** — mas `knockback`
e `speed` ficam **no limiar**, com sinal/ruído ~1,1. A limitação declarada muda de forma, não
some: era "`knockback` abaixo do piso"; no indivíduo atual é "`knockback` e `speed` no
limiar do piso". A análise é local — mede a paisagem em volta de um indivíduo —, e é por
isso que o `speed`, com sinal/ruído 2,0 no indivíduo em que se decidiu a persistência, aqui
fica no limiar.

## 3. O que mudou depois da bateria de 2026-09-18

Tudo testado e commitado; detalhe e números no
[`docs/thesis/04`](../thesis/04-design-decisions.md) (as últimas seções).

- **`MULTI_RUN_N_SEEDS = 20` e fora do carimbo.** A bateria rodava com `--n-seeds 20`
  sobre um default de 10; a constante só define o tamanho da amostra, que o corpo do
  artefato já grava, então saiu do carimbo como `N_WORKERS` e o default virou o protocolo.
- **Pool de processos persistente.** Recriado a cada geração, custava mais que a própria
  avaliação: **3,87 s → 1,04 s** por geração de 300. O `RuntimeState` viaja com cada
  tarefa, então um worker vivo nunca avalia sob estado velho. A seed 42 reproduziu **bit a
  bit** nos dois algoritmos — AG em 3,0 min contra 6,7, NSGA-II em 5,8 contra 9,7.
  `N_WORKERS = min(8, os.cpu_count())`.
- **CRN com uma semente por luta** (`fitness.fight_seed`). Pares sem o personagem
  alterado passam a sair bit a bit iguais entre dois indivíduos, mas o sinal de seleção
  melhora só 1,0–1,3×: o ruído que pesa está dentro das lutas do personagem alterado.
  Custo +13%. Mantido por decisão do autor; **muda todos os números**.
- **Validação externa com contagem.** O veredito segue binário; o relato diz em quantas
  das 10 condições cada par vira counter e cada boneco fica na banda.
- **Os cinco representantes do NSGA-II por semente.** O `multi_run` grava e reavalia os
  cinco, e `compare_algorithms --nsga2-representative scalar_optimum` compara o escalar com
  o comparável dele a n = 20, sem re-rodar o NSGA-II. A bateria faz isso no passo 4 (agora
  são 12). O representante padrão segue `best_dominance`.

### A auditoria do zero (2026-09-18)

Uma revisão sem contexto prévio achou afirmações do motor que o código não cumpria,
leituras que os números não sustentavam e buracos de protocolo. Tudo resolvido e testado
(11 smoke tests, 1 novo); o porquê e os números de cada item estão no
[`docs/thesis/04`](../thesis/04-design-decisions.md), a partir de "A auditoria do zero".

- **Motor:** timers com resto acumulado — o período do cooldown era `round(5c) + 1` e o stun
  `ceil(s)` (4 efeitos em cooldown 1; o stun do Rushdown evoluído dava 5 WR distintas em 31
  valores, agora 27). Regras do combate como estado de processo (`CombatRules`), levadas
  aos workers. **Muda todos os números.**
- **Validador:** empate conta contra a asserção (os espelhos ganhavam 4/13 da Layer 1 pelo
  índice); pesos comparados como probabilidade de intenção.
- **Nova régua funcional:** concordância de ranking comportamental (τ de Kendall),
  `IDENTITY_BEHAVIORAL_SIMS = 200`. Por semente no `multi_run`, nos nulos e no dossiê.
- **Controles na bateria:** AG com `λ_drift = 0` e AG sem semente canônica, n = 20, em
  `results/controls/`, comparados por `compare_algorithms --control`.
- **Comparação:** manchete no `scalar_optimum` (decidida antes da bateria), relação de
  Pareto por semente, família de Holm fixa de 7 métricas (equilíbrio + identidade).
- **Validação externa:** replicação e robustez a 8 regras perturbadas, 5000 lutas por par,
  veredito pelo IC.
- **Sensibilidade:** os 11 genes, janela de 2σ que desliza no bound, piso na estatística
  certa (0,037 contra 0,068 da regra antiga).
- **NSGA-II:** joelho e ideal com objetivos normalizados (o ideal mudou em 19/20
  fronteiras); hipervolume com referência (1,3; 0,4) ancorada nos nulos.
- **`stagnated_at` e `STAGNATION_LIMIT` removidos.**
- **Proveniência:** quem grava artefato a partir de outro recusa entrada obsoleta
  (`refuse_if_stale`); digest do código de medição por artefato; o `multi_run` roteia todo
  desvio do protocolo (antes um `--n-seeds 3` gravava por cima da bateria).
- **Sweeps** nas sementes 1000–1004, disjuntas da bateria.
- **Limpeza:** `ELITE_SIZE` removido, `generations_run` igual nos dois algoritmos, o
  `report` com os defaults do `baselines`, comentários desatualizados, imports sem uso.

**Leitura preliminar, a confirmar na bateria:** a identidade funcional do evoluído está no
piso (Layer 3 1/5, p = 0,74; τ = 0,19, p = 0,14), a política saiu embaralhada (o Rushdown
guarda mais do que avança) e, na escala da mutação, `w_retreat` e `w_defend` ficam abaixo do
piso de ruído da sensibilidade. Se a bateria confirmar, a resposta à pergunta de pesquisa é
que o equilíbrio preserva a identidade **estrutural** e não a **funcional** — e o controle
`λ_drift = 0` dirá quanto da estrutural é do termo de drift.

**Limites estruturais — escopo declarado, não conserto**
([`10-known-issues`](../reference/10-known-issues.md) §2): política fixa (a objeção mais
forte ao resultado) e cega ao estado; crossover só por bloco de personagem; round-robin
uniforme; hipersensibilidade dos genes de recurso; `knockback` e `speed` no limiar do piso
de ruído; o pareamento CRN acaba dentro da luta; sweeps em orçamento reduzido.

## 4. Aberto — redação

A monografia (`overleaf/TCC/`) está várias gerações de modelo atrás — `metodologia.tex`
descreve 9 atributos, `defense`/`recovery`, indivíduo de 60 genes, decisão por
prioridade, `specialization_penalty` e a formulação pré-C2 do `dominance_penalty`.
`main.tex` promete seis capítulos e existem quatro arquivos, com `conclusao.tex` em
branco. Decisão anterior: recomeçar do zero a partir de `overleaf/artigo-SBC/main.tex`,
que descreve o modelo melhor — **mas mesmo ele descreve um motor que não existe mais**
(ação única em vez de dois canais, sem colisão, sem empate).

O `values.tex` (idêntico nos dois artigos) está inteiramente obsoleto. Ao refazê-lo, a
macro do `dominance` do AG deve usar o número medido **fora** do laço, como as outras
células da mesma linha — a versão atual usa o de dentro, a única célula com vantagem de
proveniência.

Ponto para o texto: a macro `valAg = 7` assume o validador como resultado de identidade
enquanto o `drift_penalty` do mesmo indivíduo era lido como "identidade preservada a
0,26". Com as duas réguas nomeadas (estrutural no fitness, funcional post-hoc) a
contradição some — mas o texto precisa ser reescrito com essa distinção explícita.

Bibliografia: as referências estatísticas (Holm, Mann & Whitney, Derrac et al., Arcuri &
Briand, Vargha & Delaney) estão nos três `.bib`, junto de Laumanns, Kendall e Deb.
