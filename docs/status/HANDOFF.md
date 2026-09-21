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
2. **`results/` está COMPLETO e ATUAL.** A bateria de 2026-09-21 (16 passos, 6h59) rodou
   sobre o motor atual, com os dois controles; `py -m src.tests.test_provenance` marca
   tudo como *atual* ou *braço de experimento*. **Os números da §2 são os citáveis.**
3. **O sistema está fechado.** Motor e fitness calibrados, os três sweeps feitos, os
   controles que isolam o método medidos. Não há pendência de instrumentação nem de
   experimento.
4. **O que falta é a redação** (§4) — a começar pelo `values.tex`, inteiramente obsoleto.
   Agora existem números definitivos para preenchê-lo.

## 1. O modelo em quatro eixos

| eixo | do que é feito | estado |
|---|---|---|
| **Espaço** | range, speed, knockback, posição, campo, colisão | ✅ coerente — dois canais de ação, colisão, regra de impasse |
| **Tempo** | cooldown, stun, persistência da intenção | ✅ coerente — os timers carregam o resto entre golpes (período e stun exatos em média); a persistência é 5 sub-ticks = 1 tick = o período do atacante mais rápido, então quem tem `cooldown=1` e sorteia GUARDA abre mão de exatamente **uma** janela |
| **Recurso** | hp, damage, DEFEND, grab_power | ✅ coerente — o agarrão é o counter da guarda |
| **Política** | 3 pesos, amostragem proporcional | contínua, e a escala dos pesos não contamina a identidade (`drift_genes` reescala); segue **cega ao estado** e, medido, **quase invisível ao equilíbrio** — os três pesos ocupam o fundo do ranking de sensibilidade (§2), e só o drift puxa a política de volta ao canônico |

## 2. Resultados da bateria (2026-09-21, n = 20)

Bateria: NSGA-II e AG escalar com **20 sementes** (42–61), `compare_algorithms` no
`scalar_optimum` (manchete) e no `best_dominance`, os **dois braços de controle** com a
mesma amostra e o mesmo orçamento, os indivíduos da seed 42, os quatro rótulos de
`external_validation`, `sensitivity_analysis` e `baselines` com 35 nulos.

### O resultado que domina todos os outros: o controle `λ_drift = 0`

É o contrafactual da pergunta de pesquisa — equilibrar **sem** o termo de identidade —, e
responde as duas metades de uma vez.

| | AG (λ_drift = 1) | controle λ_drift = 0 | p (Holm) | Â₁₂ |
|---|---|---|---|---|
| `dominance_penalty` | **0,0399** | 0,0534 | **0,038** | 0,30 |
| hard-counters/execução | 0 | 0 | 0,763 | 0,54 |
| `drift_penalty` | **0,2473** | 0,4055 | **1,1 × 10⁻⁵** | 0,00 |
| validador estrutural (L1+L2) | **11** | 6 | **0,00042** | 0,98 |
| validador comportamental (L3) | **3** | 1 | **0,0044** | 0,85 |
| concordância de ranking (τ) | **0,2811** | −0,0304 | **0,00067** | 0,87 |

(medianas sobre as 20 execuções; Wilcoxon pareado + Holm, família de 6 — `bonecos em
banda` sai por ser constante, 5/5 em todas as execuções dos dois braços)

**Tirar o termo de drift piora o equilíbrio e zera a identidade.** Cinco das seis
métricas separam a favor do braço *com* o termo: as quatro de identidade com efeito
grande, e o próprio `dominance` com efeito médio. Só os hard-counters empatam (os dois
braços fazem ~0,2–0,3 por execução). Na média das 20 execuções o braço λ = 0 dá
τ = **+0,007 ± 0,151** — o acaso com três casas decimais — contra +0,259 ± 0,159 do AG.

A leitura: **a identidade não custa equilíbrio — melhora.** O trade-off que o sweep de λ
mostra existe, mas o joelho está longe o bastante de λ = 1,0 para que o termo saia de
graça; e neste orçamento ele ainda ajuda a busca, provavelmente por manter os cinco
diferenciados enquanto o equilíbrio é procurado.

> Sob o Mann-Whitney **não-pareado** (o teste anterior) essa primeira linha dava
> p_Holm = 0,063, "sem diferença". O desenho é pareado por construção — as mesmas
> sementes fixam população inicial, operadores e streams nos dois braços —, e o teste
> passou a ser o Wilcoxon pareado; o não-pareado segue impresso ao lado, como robustez.
> Ver [`thesis/04`](../thesis/04-design-decisions.md), "O teste passou a ser o pareado".

### O segundo controle: a semente canônica não explica nada

| | AG | controle sem semente | p (Holm) |
|---|---|---|---|
| `dominance_penalty` | 0,0399 | 0,0403 | 0,818 |
| hard-counters | 0 | 0 | 0,818 |
| `drift_penalty` | **0,2473** | 0,2703 | **0,0073** |
| validador estrutural | 11 | 10,5 | 0,306 |
| validador comportamental | 3 | 2 | 0,593 |
| τ | 0,2811 | 0,1931 | 0,387 |

Separa **só no drift**, e por pouco. A semente canônica dá uma dianteira estrutural
modesta e nada mais: a diferença entre os dois algoritmos **não** é inicialização.

### Agregado (20 sementes, reavaliação independente na seed 9999)

Média ± desvio; o NSGA-II representado pelo `scalar_optimum` (a manchete).

| | dominance | drift | hard-counters | roster equilibrado | L1+L2 | L3 | τ |
|---|---|---|---|---|---|---|---|
| **AG escalar** | **0,0412** ± 0,0150 | 0,2495 ± 0,0273 | **0,30** ± 0,47 | **14/20** (70%) | 11,5 ± 2,2 | 2,45 ± 1,00 | +0,259 ± 0,159 |
| **NSGA-II** | 0,0902 ± 0,0393 | **0,1484** ± 0,0233 | 3,00 ± 1,49 | 0/20 (0%) | **15,5** ± 1,1 | **3,65** ± 1,18 | **+0,521** ± 0,120 |
| controle λ = 0 | 0,0523 ± 0,0142 | 0,4089 ± 0,0353 | 0,25 ± 0,55 | 16/20 (80%) | 5,7 ± 2,0 | 0,90 ± 0,97 | +0,007 ± 0,151 |
| controle sem semente | 0,0434 ± 0,0197 | 0,2759 ± 0,0298 | 0,20 ± 0,41 | 16/20 (80%) | 10,4 ± 1,9 | 2,00 ± 0,97 | +0,172 ± 0,149 |

Os dois algoritmos ocupam extremos nítidos e **as seis métricas da família são
significativas, todas com efeito grande** — o AG ganha as duas de equilíbrio, o NSGA-II
as quatro de identidade:

| métrica | mediana AG | mediana NSGA-II | p (Holm) | Â₁₂ | vencedor |
|---|---|---|---|---|---|
| `dominance_penalty` | 0,0399 | 0,0796 | 0,00013 | 0,10 | AG escalar |
| hard-counters/execução | 0 | 3 | 0,00034 | 0,03 | AG escalar |
| `drift_penalty` | 0,2473 | 0,1445 | 1,1 × 10⁻⁵ | 1,00 | NSGA-II |
| validador estrutural (L1+L2) | 11 | 15 | 0,00034 | 0,05 | NSGA-II |
| validador comportamental (L3) | 3 | 4 | 0,0027 | 0,24 | NSGA-II |
| concordância de ranking (τ) | 0,2811 | 0,5430 | 0,00013 | 0,09 | NSGA-II |

`bonecos em banda` fica fora da família nas quatro comparações: **5/5 em todas as
execuções de todos os braços**. Equilibrar os cinco globalmente deixou de discriminar
qualquer coisa — o que discrimina são os pares.

Contra o `best_dominance` (leitura secundária) as mesmas seis, nas mesmas direções, um
pouco mais fracas: `dominance` p_Holm = 0,0029, hard-counters 0 contra 2, τ 0,2811 contra
0,5072. Nenhum representante da fronteira chega perto do AG no critério completo —
rosters equilibrados por representante: `best_dominance` 2/20, `scalar_optimum` 0/20,
`knee_point` 0/20, `ideal_point` 0/20, `best_drift` 0/20, contra **14/20** do AG.

**A decomposição diz de onde vem a diferença.** O AG vence nos dois termos, mas por
margens muito diferentes — `global_term` **0,0397 contra 0,0490**, `cap_term` **0,0030
contra 0,0807**. Globalmente os dois equilibram parecido; o NSGA-II perde por deixar par
passar do teto. O `decis_term` fica em 0,0000 nos dois (0,0017 ± 0,0072 no NSGA-II).

**Relação de Pareto por semente** (descritiva, fora da família): **18/20 mutuamente
não-dominados**, o AG dominando um ponto da fronteira na seed 48 e sendo dominado na
seed 60. O ponto do escalar fica *além* da ponta de baixa dominância da fronteira —
compra equilíbrio com um drift que a fronteira não oferece.

Hipervolume 0,3954 ± 0,0114 (ref. (1,3; 0,4)), CV 2,9%; spacing 0,0118 ± 0,0033.

### O número de dentro do laço continua honesto

`dominance` medido **durante a busca** contra o mesmo indivíduo (seed 42) medido em 10
condições independentes (`external_validation`, seeds 10000+, 5000 lutas por par):

| | dentro → fora | degradação |
|---|---|---|
| bateria 2026-09-16 (sem rotação) | 0,0039 → 0,0804 | **21×** |
| bateria 2026-09-21 | 0,0251 → **0,0373** | **1,5×** |

A rotação do stream por geração fez o que prometia, e o efeito persiste sob o CRN por
luta: o número reportado durante a busca **é** essencialmente o número que sobrevive fora
dela.

### Contra os modelos nulos (melhor do AG, seed 42; 35 nulos)

| métrica | valor | piso médio | melhor nulo | teto | posição | p |
|---|---|---|---|---|---|---|
| validador (L1-L3) | 17/23 | 6,00 | 10 | 23 | 65% | **< 0,03** |
| validador (L1+L2) | 14/18 | 5,03 | 9 | 18 | 69% | **< 0,03** |
| validador (L3) | 3/5 | 0,97 | 3 | 5 | 50% | **0,03** |
| concordância (τ) | 0,314 | −0,039 | 0,316 | 1,00 | 34% | 0,06 |
| `drift_penalty` | 0,236 | 0,409 | 0,327 | 0,000 | 42% | **< 0,03** |
| arestas do ciclo | 5/10 | 5,00 | 7 | 10 | 0% | 0,63 |
| `dominance_penalty` | 0,031 | 1,146 | 0,024 | 0,057 | 102% | 0,06 |

Três leituras:

1. **A identidade estrutural supera todos os nulos** (drift, L1+L2, p < 0,03) — como se
   espera de réguas parcialmente endógenas: o `drift_penalty` está no fitness e as
   Layers 1-2 medem o mesmo eixo. Vencer nulos não otimizados aqui é quase garantido, e
   por isso o controle λ = 0 é a evidência que conta, não esta tabela.
2. **A identidade funcional está acima do acaso, mas por margem estreita neste
   indivíduo.** L3 3/5 **empata com o melhor nulo** (p = 0,03) e τ = 0,314 fica um fio
   *abaixo* dele (0,316, p = 0,06). Num único roster contra 35 nulos a resolução não dá
   para concluir; sobre 20 sementes contra o controle λ = 0, dá — e separa com efeito
   grande. **É uma correção da leitura preliminar de 2026-09-18**, que dava a identidade
   funcional no piso (L3 1/5, p = 0,74; τ = 0,19).
3. **O ciclo autoral não é realizado** — 5/10 arestas, exatamente o piso, posição 0%.
   Não é falha: o ciclo nunca esteve no fitness, e o próprio canônico só realiza 6/10
   dele. O objetivo é cego à direção por construção.

O `dominance` do evoluído (0,031) fica **no nível dos espelhos** (0,024–0,116, média
0,057) — tão equilibrado quanto a simetria perfeita, dentro do ruído a 200 lutas, nunca
"mais equilibrado". O espelho é a solução trivial; o que a separa do evoluído é o drift.

### Validação externa — os quatro rótulos

10 sementes inéditas agrupadas em 5000 lutas por par, veredito pelo IC de Wilson.

| indivíduo | replicação | robustez a regras | `dominance` fora |
|---|---|---|---|
| canônico | FRÁGIL | 0/8 robustas | 1,2771 |
| **AG escalar** | **ROBUSTO** | **4/8 robustas · 2 inconclusivas · 2 frágeis** | **0,0373** |
| NSGA-II `scalar_optimum` | FRÁGIL | 0/8 robustas | — |
| NSGA-II `knee_point` | FRÁGIL | 0/8 robustas | — |

**O AG escalar é o único dos quatro que replica.** Na condição de treino, cinco bonecos
em banda e nenhum par fora da banda de counter, com as WR espalhadas — equilíbrio com
arestas decididas, não achatamento. As duas regras que o quebram são `FIELD_SIZE = 80`
(campo menor: Zoner × Turtle vai a 68,8%) e `ACTION_PERSISTENCE_SUBTICKS = 6` (Combo
Master × Turtle a 69,4% e a Turtle cai a 39,3% global). Ambas mexem em quanto espaço e
quanto compromisso a política tem — coerente com o limite declarado de a política ser
fixa e cega ao estado.

### Convergência

- **Convergiu em 20/20 sementes**, sempre confirmado num stream que o AG nunca viu, na
  geração **31,3 ± 13,2** (13 a 56). A seed 42 converge na 31.
- Convergir não é terminar equilibrado: das 20 convergidas, **14** terminam com o roster
  equilibrado na reavaliação.
- **O gate disparou 70 vezes e a confirmação recusou 50 (71%)** — ~3 de cada 4 vezes em
  que o roster parece equilibrado sob o stream de treino, ele não sobrevive a um stream
  inédito. É o que a rotação por geração existe para combater, e a taxa é a mesma nos
  controles (67% e 63%).

### Sensibilidade (indivíduo da seed 42, 11 genes, janela 2σ)

Piso de ruído **medido na mesma estatística que é classificada**: máx 3,5%, médio 1,8%.

| gene | \|Δ WR\| médio | veredito |
|---|---|---|
| `range` | 30,8% | ✓ visível |
| `damage` | 26,2% | ✓ |
| `attack_cooldown` | 25,7% | ✓ |
| `hp` | 23,9% | ✓ |
| `grab_power` | 18,6% | ✓ |
| `stun` | 10,4% | ✓ |
| `w_retreat` | 4,8% | ~ limiar |
| `knockback` | 4,3% | ~ limiar |
| `speed` | 3,5% | ~ limiar |
| `w_aggressiveness` | 3,0% | ✗ neutro |
| `w_defend` | 2,9% | ✗ neutro |

**Os três pesos de política ocupam o fundo do ranking**, dois deles abaixo do piso. Na
escala da mutação o AG praticamente não enxerga a política através do equilíbrio — o
único gradiente que a puxa de volta ao canônico é o do drift. `knockback` e `speed`
seguem no limiar. A análise é local: mede a paisagem em volta de um indivíduo.

### Sweep de λ — λ = 1,0 confirmado, e agora dominante

5 braços × 5 sementes a pop 120 × 60 (16% do custo), sementes 1000–1004, disjuntas da
bateria. Orçamento reduzido ordena configurações; não dá número citável.

| λ_drift | dominance | drift | counters | L1+L2 | τ | conv |
|---|---|---|---|---|---|---|
| 0,25 | 0,0620 | 0,3773 | 1,2 | 5,4 | +0,018 | 80% |
| 0,5 | 0,0648 | 0,3462 | 1,2 | 5,2 | −0,050 | 80% |
| **1,0** | **0,0600** | **0,2448** | 0,8 | **10,2** | **+0,415** | 80% |
| 2,0 | 0,1979 | 0,1395 | 3,8 | 15,0 | +0,601 | 20% |
| 4,0 | 0,3581 | 0,0902 | 7,8 | 15,8 | +0,716 | 0% |

O formato é o mesmo de antes — `dominance` plano em 0,060–0,065 até λ = 1,0 e explodindo
depois —, mas a conclusão ficou mais forte: **λ = 1,0 não empata com os λ menores, ele os
domina**. Mesmo `dominance`, drift 0,10–0,13 melhor, e τ dez vezes maior. Abaixo de 1,0 o
AG paga identidade sem comprar equilíbrio.

### Sweep dos pesos do dominance — os secundários seguem indispensáveis

| pesos g/cap/decis | global_term | cap_term | decis_term | drift | counters | roster eq. |
|---|---|---|---|---|---|---|
| 1 / 2 / 0,5 | 0,0482 | **0,0027** | 0,0082 | 0,3481 | **0,2** | 80% |
| 1 / 1 / 1 | 0,0437 | 0,0036 | 0,0000 | 0,3008 | **0,2** | 80% |
| **1 / 0,5 / 0,5** | 0,0512 | 0,0176 | 0,0000 | **0,2448** | 0,8 | 20% |
| 1 / 0,5 / 0 | 0,0462 | 0,1212 | 0,0000 | 0,2479 | 2,2 | 20% |
| 1 / 0 / 0 | **0,0275** | 0,7921 | 0,2668 | 0,1564 | **8,8** | 0% |

**`1/0/0` continua sendo a falsificação.** Sem os secundários o AG atinge o melhor
`global_term` de todos (0,0275 — é a única coisa que resta a otimizar) e entrega 8,8 dos
10 pares como counter duro: os cinco na banda global, toda luta um massacre. É o
*blowout-coinflip* que a formulação C2 previa.

**E o `decis_term` não é inerte.** Removê-lo sozinho (1 / 0,5 / 0) leva os counters de
0,8 a 2,2 e **piora o próprio `cap_term`**, de 0,0176 para 0,1212. Ler 0,0000 no
indivíduo final é o termo tendo funcionado.

**`config.py` inalterado.** Subir o peso do cap melhora counters e roster equilibrado ao
custo de ~0,06–0,10 de drift e de metade da concordância de ranking — a n = 5 e no
orçamento reduzido, a troca não se distingue de ruído, e o eixo que ela sacrifica é
justamente o da pergunta de pesquisa.

### Sweep de elitismo / torneio — 10% / 3 mantidos, por outra razão

| braço | global_term | cap_term | drift | counters | L1+L2 | τ |
|---|---|---|---|---|---|---|
| elitismo 0 | 0,0673 | **0,0063** | 0,2689 | 0,6 | 10,2 | +0,301 |
| elitismo 5% | **0,0400** | 0,0124 | 0,2890 | 0,6 | 9,0 | +0,238 |
| **elitismo 10% · torneio 3** | 0,0512 | 0,0176 | **0,2448** | 0,8 | 10,2 | **+0,415** |
| elitismo 20% | 0,0438 | 0,0195 | 0,2809 | 0,8 | 8,8 | +0,186 |
| elitismo 30% | 0,0447 | 0,0780 | 0,2848 | 1,8 | 8,6 | +0,204 |
| torneio 2 | 0,0515 | 0,0083 | 0,2637 | 0,6 | **10,8** | +0,356 |
| torneio 5 | 0,0410 | 0,0311 | 0,2913 | 1,2 | 7,8 | +0,172 |
| torneio 7 | 0,0448 | 0,0119 | 0,3402 | 0,8 | 7,0 | +0,047 |

**Nenhum braço domina o default, mas a razão mudou.** Na bateria anterior ele tinha o
menor `cap_term` e o menor número de counters dos oito; agora **não tem nem um nem
outro** — elitismo 0, elitismo 5% e torneio 2 fazem 0,6 counter contra 0,8, e três braços
têm `cap_term` menor. O que o default tem é o **melhor drift e a melhor concordância de
ranking** dos oito, e cada braço que o supera em counters paga nos dois. A n = 5 nada
disso se separa do ruído (os desvios de counters vão a 1,3), e o torneio segue com padrão
não monotônico. A afirmação continua sendo "testados, nenhum braço os domina" — não
"ótimos".

## 3. Limites estruturais

Escopo declarado, não conserto — lista completa em
[`10-known-issues`](../reference/10-known-issues.md) §2. Os que a bateria de 2026-09-21
reforçou:

- **A política é fixa e cega ao estado**, e é a objeção mais forte ao resultado. A
  bateria acrescenta duas evidências: os três pesos ocupam o fundo do ranking de
  sensibilidade (dois abaixo do piso de ruído), e as duas regras que quebram a robustez
  do AG são exatamente as que mexem em espaço e compromisso da política.
- **O ciclo de vantagens não é realizado** (5/10, o piso). Consequência declarada de o
  objetivo ser cego à direção.
- Crossover só por bloco de personagem; round-robin uniforme; genes de recurso
  hipersensíveis; `knockback` e `speed` no limiar do piso; o pareamento CRN acaba dentro
  da luta; sweeps em orçamento reduzido.

## 4. Aberto — redação

A monografia (`overleaf/TCC/`) está várias gerações de modelo atrás — `metodologia.tex`
descreve 9 atributos, `defense`/`recovery`, indivíduo de 60 genes, decisão por
prioridade, `specialization_penalty` e a formulação pré-C2 do `dominance_penalty`.
`main.tex` promete seis capítulos e existem quatro arquivos, com `conclusao.tex` em
branco. Decisão anterior: recomeçar do zero a partir de `overleaf/artigo-SBC/main.tex`,
que descreve o modelo melhor — **mas mesmo ele descreve um motor que não existe mais**
(ação única em vez de dois canais, sem colisão, sem empate).

O `values.tex` (idêntico nos dois artigos) está inteiramente obsoleto, e agora há números
definitivos para refazê-lo. Ao fazê-lo, a macro do `dominance` do AG deve usar o número
medido **fora** do laço (0,0373), como as outras células da mesma linha — a versão atual
usa o de dentro, a única célula com vantagem de proveniência.

Ponto para o texto: a macro `valAg = 7` assume o validador como resultado de identidade
enquanto o `drift_penalty` do mesmo indivíduo era lido como "identidade preservada a
0,26". Com as duas réguas nomeadas (estrutural no fitness, funcional post-hoc) a
contradição some — mas o texto precisa ser reescrito com essa distinção explícita.

Bibliografia: as referências estatísticas (Holm, Mann & Whitney, Derrac et al., Arcuri &
Briand, Vargha & Delaney) estão nos três `.bib`, junto de Laumanns, Kendall e Deb.
