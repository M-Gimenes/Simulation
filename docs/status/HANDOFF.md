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
2. **`results/` está COMPLETO e ATUAL.** A bateria de 2026-09-23 (19 passos) rodou
   sobre o motor atual, com os dois controles; `py -m src.tests.test_provenance` marca
   tudo como *atual* ou *braço de experimento*. **Os números da §2 são os citáveis.**
3. **O sistema está fechado.** Motor e fitness calibrados, os três sweeps refeitos sobre
   o motor atual (2026-09-23, 47,8 min), os controles que isolam o método medidos, o
   híbrido adotado. `test_provenance`: 18 artefatos atuais, 24 braços de experimento,
   **zero obsoletos**.
4. **O híbrido foi adotado (2026-09-23), e ele responde o achado do AG escalar.** A
   escalarização direta perde a linhagem fiel sob avaliação ruidosa — `dominance` é
   amostrado e `drift` não, e depois da geração ~31 a seleção gasta a pressão em sorte.
   Repartir o **mesmo** orçamento entre 75 gerações de NSGA-II e 75 do AG escalar:
   `drift` 0,1663 contra 0,2473, τ **+0,5215 contra +0,2811**, Layer 3 4 contra 3, todas
   com efeito grande — e **as duas métricas de equilíbrio não se movem** (Â₁₂ 0,51 e 0,49,
   16/20 rosters equilibrados nos dois). Entra como passos 18–19 da bateria e como
   **contribuição de método**. Detalhe em
   [`../thesis/07-findings-and-limitations.md`](../thesis/07-findings-and-limitations.md)
   e [04](../thesis/04-design-decisions.md).
5. **O que falta é a redação** (§4) — a começar pelo `values.tex`, inteiramente obsoleto.
   Agora existem números definitivos para preenchê-lo.

## 1. O modelo em quatro eixos

| eixo | do que é feito | estado |
|---|---|---|
| **Espaço** | range, speed, knockback, posição, campo, colisão | ✅ coerente — dois canais de ação, colisão, regra de impasse |
| **Tempo** | cooldown, stun, persistência da intenção | ✅ coerente — os timers carregam o resto entre golpes (período e stun exatos em média); a persistência é 5 sub-ticks = 1 tick = o período do atacante mais rápido, então quem tem `cooldown=1` e sorteia GUARDA abre mão de exatamente **uma** janela |
| **Recurso** | hp, damage, DEFEND, grab_power | ✅ coerente — o agarrão é o counter da guarda |
| **Política** | 3 pesos, amostragem proporcional | contínua, e a escala dos pesos não contamina a identidade (`drift_genes` reescala); segue **cega ao estado** e, medido, **quase invisível ao equilíbrio** — os três pesos ocupam o fundo do ranking de sensibilidade (§2), e só o drift puxa a política de volta ao canônico |

## 2. Resultados da bateria (2026-09-23, n = 20)

> **Esta é a bateria de 2026-09-23**, 19 passos. Ela re-executa a de 2026-09-21 sobre o
> motor com os cinco consertos adiados aplicados e com `MULTI_RUN_SIMS` = 1000 (era 200),
> e acrescenta dois passos: `cycle_structure` e o braço **híbrido**.
>
> **Os indivíduos são os mesmos.** Comparados gene a gene, 40 de 40 execuções com semente
> saíram bit a bit idênticas às da bateria anterior — os consertos de motor são inertes,
> como o `10-known-issues` afirmava e agora está medido. Logo **nenhum número de
> identidade mudou** (drift, validador, τ). O que mudou foi só o que a régua mede: tudo
> que deriva de `dominance`. Duas leituras viraram de lado por causa disso, e as duas
> estão marcadas com ⚠ abaixo.
>
> A bateria anterior está versionada em
> [`results_previous/2026-09-21/`](../../results_previous/README.md) — não é citável, mas
> é o que sustenta cada nota de revisão "a 200 lutas dava X".

Bateria: NSGA-II e AG escalar com **20 sementes** (42–61), `compare_algorithms` no
`scalar_optimum` (manchete) e no `best_dominance`, os **dois braços de controle** com a
mesma amostra e o mesmo orçamento, os indivíduos da seed 42, os quatro rótulos de
`external_validation`, `sensitivity_analysis` e `baselines` com 35 nulos.

### O controle `λ_drift = 0`: o contrafactual da pergunta de pesquisa

Equilibrar **sem** o termo de identidade. Responde as duas metades de uma vez — e desde
2026-09-23 responde **assimetricamente**, que é o ponto desta seção.

| | AG (λ_drift = 1) | controle λ_drift = 0 | p (Holm) | Â₁₂ |
|---|---|---|---|---|
| `dominance_penalty` | 0,0355 | 0,0432 | 0,059 | 0,30 (médio) |
| hard-counters/execução | 0 | 0 | 0,180 | 0,57 |
| `drift_penalty` | **0,2473** | 0,4055 | **1,1 × 10⁻⁵** | 0,00 |
| validador estrutural (L1+L2) | **11** | 6 | **0,00042** | 0,98 |
| validador comportamental (L3) | **3** | 1 | **0,0044** | 0,85 |
| concordância de ranking (τ) | **0,2811** | −0,0304 | **0,00067** | 0,87 |

(medianas sobre as 20 execuções; Wilcoxon pareado + Holm, família de 6 — `bonecos em
banda` sai por ser constante, 5/5 em todas as execuções dos dois braços)

**O que é sólido: tirar o termo de drift zera a identidade.** As quatro réguas separam com
efeito grande e p_Holm entre 1,1 × 10⁻⁵ e 0,0044. Na média das 20 execuções o braço λ = 0
dá τ = **+0,007 ± 0,151** — o acaso com três casas decimais — contra +0,259 ± 0,159 do AG.
Este é o achado que responde à pergunta de pesquisa, e ele não dependeu de resolução:
os genes são idênticos aos da bateria anterior, e os números de identidade também.

**O que NÃO é sólido, e mudou de status em 2026-09-23: o efeito no equilíbrio.**

> ⚠ **Correção.** A bateria anterior media a reavaliação a 200 lutas por par e dava
> `dominance` 0,0399 contra 0,0534, **p_Holm = 0,038 — significativo**, sustentando a
> frase "a identidade não custa equilíbrio, **melhora**". A 1000 lutas, com os **mesmos
> indivíduos** (genes bit a bit idênticos), a mesma linha dá 0,0355 contra 0,0432,
> **p_Holm = 0,059 — não significativo**.
>
> O que sobrevive: a **direção** (o braço com o termo equilibra melhor), o **tamanho de
> efeito** (Â₁₂ = 0,30, médio, inalterado) e o **p bruto** (0,0296, ainda abaixo de 0,05).
> O que cai é a sobrevivência à correção de Holm sobre a família de 6.
>
> Por que mudou: o braço λ = 0 é o mais ruidoso dos dois (inflação dentro→fora do laço de
> 3,21× contra 2,58× na medição antiga), então a régua grossa o penalizava mais. Parte da
> diferença que a 200 lutas parecia efeito era **a medida errando contra o braço mais
> ruidoso**. A frase honesta agora é: *"tirar o termo de identidade está associado a pior
> equilíbrio, com efeito médio que não alcança significância"* — não *"piora o
> equilíbrio"*.

A leitura que fica: **a identidade não custa equilíbrio.** Isso é o que os dados sustentam
— o trade-off que o sweep de λ mostra existe, mas o joelho está longe o bastante de
λ = 1,0 para que o termo saia de graça. O que **não** se pode mais afirmar é que ele
*melhora* o equilíbrio.

> Sob o Mann-Whitney **não-pareado** a mesma linha dá p_Holm = 0,0337 bruto; o desenho é
> pareado por construção — as mesmas sementes fixam população inicial, operadores e
> streams nos dois braços —, e o teste é o Wilcoxon pareado, com o não-pareado impresso ao
> lado como robustez. Ver [`thesis/04`](../thesis/04-design-decisions.md), "O teste passou
> a ser o pareado".

### O terceiro braço: o híbrido NSGA-II → AG escalar

Mesmo orçamento do AG escalar, repartido: 75 gerações de NSGA-II, 75 de escalar.

| | AG escalar | híbrido | p (Holm) | Â₁₂ |
|---|---|---|---|---|
| `dominance_penalty` | 0,0355 | 0,0287 | 1,00 | 0,51 (desprezível) |
| hard-counters | 0 | 0 | 1,00 | 0,49 (desprezível) |
| `drift_penalty` | 0,2473 | **0,1663** | **1,1 × 10⁻⁵** | 0,97 |
| validador L1+L2 | 11 | **15** | **0,0026** | 0,12 |
| validador L3 | 3 | **4** | **0,0058** | 0,24 |
| concordância τ | 0,2811 | **0,5215** | **0,00084** | 0,15 |

**Troca identidade grande por equilíbrio nenhum.** As duas de equilíbrio não se movem
(16/20 rosters equilibrados nos dois braços, hard-counters 0,20 contra 0,25 por execução)
e as quatro de identidade separam com efeito grande. Contra o NSGA-II: mesma identidade
(drift 0,1708 contra 0,1484; τ +0,484 contra +0,521; Layer 3 **3,70 contra 3,65**) com
**0,25 hard-counters contra 2,80** e **16/20 equilibrados contra 0/20**.

**O preço é velocidade.** Converge na geração **98,3 ± 20,2** contra 31,3 ± 13,2 do
escalar, com 81% dos disparos do gate recusados contra 71% — as 75 primeiras gerações são
de Pareto e não perseguem o predicado de equilíbrio. O sobreajuste ao stream cai para
**1,67×** contra 1,80× do escalar, na direção que o mecanismo prevê.

**Ressalva:** o split 0,5 veio do desempate de simplicidade do critério, não de evidência
— no sweep em orçamento reduzido nenhum braço passou no filtro de equilíbrio e a ordenação
entre splits não transferiu. Afirmar que 0,5 é o *melhor* split exige um sweep no
orçamento inteiro, que não foi feito.

### O segundo controle: a semente canônica não explica nada

| | AG | controle sem semente | p (Holm) |
|---|---|---|---|
| `dominance_penalty` | 0,0355 | 0,0264 | 0,985 |
| hard-counters | 0 | 0 | 0,828 |
| `drift_penalty` | **0,2473** | 0,2703 | **0,0073** |
| validador estrutural | 11 | 10,5 | 0,305 |
| validador comportamental | 3 | 2 | 0,593 |
| τ | 0,2811 | 0,1931 | 0,386 |

Separa **só no drift**, e por pouco. A semente canônica dá uma dianteira estrutural
modesta e nada mais: a diferença entre os dois algoritmos **não** é inicialização.

### Agregado (20 sementes, reavaliação independente na seed 9999)

Média ± desvio; o NSGA-II representado pelo `scalar_optimum` (a manchete).

| | dominance | drift | hard-counters | roster equilibrado | L1+L2 | L3 | τ |
|---|---|---|---|---|---|---|---|
| **AG escalar** | **0,0334** ± 0,0132 | 0,2495 ± 0,0273 | **0,20** ± 0,41 | **16/20** (80%) | 11,5 ± 2,2 | 2,45 ± 1,00 | +0,259 ± 0,159 |
| **NSGA-II** | 0,0779 ± 0,0334 | **0,1484** ± 0,0233 | 2,80 ± 1,61 | 0/20 (0%) | **15,4** ± 1,1 | 3,65 ± 1,18 | **+0,521** ± 0,120 |
| **híbrido** | 0,0352 ± 0,0190 | 0,1708 ± 0,0280 | 0,25 ± 0,55 | **16/20** (80%) | 14,8 ± 1,9 | **3,70** ± 1,34 | +0,484 ± 0,148 |
| controle λ = 0 | 0,0413 ± 0,0130 | 0,4089 ± 0,0353 | 0,05 ± 0,22 | 19/20 (95%) | 5,7 ± 2,0 | 0,90 ± 0,97 | +0,007 ± 0,151 |
| controle sem semente | 0,0334 ± 0,0193 | 0,2759 ± 0,0298 | 0,10 ± 0,31 | 18/20 (90%) | 10,3 ± 1,9 | 2,00 ± 0,97 | +0,172 ± 0,149 |

Os dois algoritmos ocupam extremos nítidos e **as seis métricas da família são
significativas, todas com efeito grande** — o AG ganha as duas de equilíbrio, o NSGA-II
as quatro de identidade:

| métrica | mediana AG | mediana NSGA-II | p (Holm) | Â₁₂ | vencedor |
|---|---|---|---|---|---|
| `dominance_penalty` | 0,0355 | 0,0759 | 9,5 × 10⁻⁵ | 0,07 | AG escalar |
| hard-counters/execução | 0 | 3 | 0,00034 | 0,03 | AG escalar |
| `drift_penalty` | 0,2473 | 0,1445 | 1,1 × 10⁻⁵ | 1,00 | NSGA-II |
| validador estrutural (L1+L2) | 11 | 15 | 0,00034 | 0,05 | NSGA-II |
| validador comportamental (L3) | 3 | 4 | 0,0027 | 0,24 | NSGA-II |
| concordância de ranking (τ) | 0,2811 | 0,5430 | 0,00011 | 0,09 | NSGA-II |

`bonecos em banda` fica fora da família nas quatro comparações: **5/5 em todas as
execuções de todos os braços**. Equilibrar os cinco globalmente deixou de discriminar
qualquer coisa — o que discrimina são os pares.

Contra o `best_dominance` (leitura secundária) as mesmas seis, nas mesmas direções, um
pouco mais fracas: `dominance` 0,0355 contra 0,0551 (p_Holm = 0,0034), hard-counters 0
contra 2, τ 0,2811 contra 0,5072. Nenhum representante da fronteira chega perto do AG no critério completo —
rosters equilibrados por representante: `best_dominance` 4/20, `scalar_optimum` 0/20,
`knee_point` 0/20, `ideal_point` 0/20, `best_drift` 0/20, contra **16/20** do AG.

**A decomposição diz de onde vem a diferença.** O AG vence nos dois termos, mas por
margens muito diferentes — `global_term` **0,0318 contra 0,0401**, `cap_term` **0,0032
contra 0,0736**. Globalmente os dois equilibram parecido; o NSGA-II perde por deixar par
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
| bateria 2026-09-21 (200 lutas) | 0,0251 → 0,0373 | 1,5× |
| bateria 2026-09-23 (1000 lutas) | 0,0251 → **0,0456** | **1,8×** |

A rotação do stream por geração fez o que prometia: a degradação caiu de 21× para a casa
de 1–3×.

> **Correção (2026-09-22): a linha acima é da seed 42, e ela é a 2ª semente mais favorável
> das 20.** A conclusão "o número de dentro do laço é essencialmente o de fora" **não**
> transfere para a amostra. Medido nas 20 sementes (razão reavaliação / dentro do laço):
> mediana **2,59×** a 200 lutas e **1,80×** a 1000 (a régua grossa também inflava esta
> razão), e a seed 42 é das mais favoráveis das 20. Não é artefato de medição: é viés de seleção (o número do laço é o mínimo de 300
> indivíduos num stream) somado ao ruído residual do `dominance`. O que sobrevive da
> afirmação é o **ganho** da rotação (de 21× para ~2×), não a igualdade dentro/fora.
> Ao citar, usar o número de fora e a razão da amostra, nunca a de uma semente. Mecanismo
> em [`../thesis/07-findings-and-limitations.md`](../thesis/07-findings-and-limitations.md)
> §«O AG escalar não é ótimo na própria função».

### Contra os modelos nulos (melhor do AG, seed 42; 35 nulos)

| métrica | valor | piso médio | melhor nulo | teto | posição | p |
|---|---|---|---|---|---|---|
| validador (L1-L3) | 17/23 | 6,00 | 10 | 23 | 65% | **< 0,03** |
| validador (L1+L2) | 14/18 | 5,03 | 9 | 18 | 69% | **< 0,03** |
| validador (L3) | 3/5 | 0,97 | 3 | 5 | 50% | **0,03** |
| concordância (τ) | 0,314 | −0,039 | 0,316 | 1,00 | 34% | 0,06 |
| `drift_penalty` | 0,236 | 0,409 | 0,327 | 0,000 | 42% | **< 0,03** |
| `dominance_penalty` | 0,046 | 1,143 | 0,011 | 0,033 | 99% | 0,11 |

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
3. **O equilíbrio do evoluído está no nível do espelho, ligeiramente abaixo.**
   `dominance` 0,046 contra 0,033 dos espelhos (posição 99%, p = 0,11). A 200 lutas a
   mesma linha dava 0,031 contra 0,057 e **posição 102%**, sugerindo que o evoluído
   equilibrava *melhor* que a simetria perfeita — o que nunca fez sentido e era artefato
   de resolução: cinco cópias idênticas são perfeitamente equilibradas por construção, e
   era o ruído de 200 lutas que as penalizava. A leitura certa é *"tão equilibrado quanto
   a simetria perfeita, dentro do ruído"*, e é o que responde à objeção "por que não
   deixar os cinco iguais?" — a resposta está na identidade, não no equilíbrio.
4. **O ciclo autoral não é realizado — e a linha dele saiu desta tabela.** A métrica
   mudou de casa em 2026-09-22: a 200 lutas por par a direção de cada aresta de um roster
   equilibrado é sorteio (margem mediana 0,048 contra σ = 0,035), e os espelhos — estrutura
   de torneio zero por construção — marcavam 5,40/10 "mantidas" com 1,00/10 decididas.
   Agora sai de `results/cycle/cycle_structure.json`
   (`src.experiments.cycle_structure`, 16 × 1000 lutas por par, σ = 0,0040, passo 17 da
   bateria), contando só arestas **decididas**:

   | grupo | n | mantidas | decididas | mantidas **E** decididas | tríades |
   |---|---|---|---|---|---|
   | canônico | 1 | 6,00/10 | 10,00/10 | 6,00/10 | **1,00** |
   | AG escalar | 20 | 5,60/10 | 9,30/10 | 5,25/10 | 3,71 |
   | NSGA-II | 20 | 4,95/10 | 9,85/10 | 4,90/10 | 4,17 |
   | espelhos (ruído) | 5 | 5,40/10 | **1,00/10** | 0,60/10 | 2,59 |
   | aleatórios (piso) | 30 | 4,97/10 | 10,00/10 | 4,97/10 | 0,40 |

   **Veredito:** o AG mantém **105 de 186 arestas decididas — 56,5%, binomial p = 0,091**;
   os nulos ficam em 49,7% (p = 0,128, Â₁₂ = 0,63). Nem "destruído" nem "preservado":
   **indistinguível do acaso**, com inclinação fraca e não significativa na direção
   autoral. Não é falha — o ciclo nunca esteve no fitness.

   **E o canônico também não tem um ciclo:** realiza 6/10, com as 4 arestas que quebra
   invertidas por completo (0,000–0,006) — o Rushdown ganha de todos, a Turtle perde para
   todos. Tríades 1,00 de 5: hierarquia, não pedra-papel-tesoura. A estrutura cíclica não
   foi destruída pelo equilíbrio, **nunca existiu no motor**. Detalhe em
   [04](../thesis/04-design-decisions.md), «O ciclo saiu do `baselines`».

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
- Convergir não é terminar equilibrado: das 20 convergidas, **16** terminam com o roster
  equilibrado na reavaliação. *(Eram 14 a 200 lutas por par — dois dos "não equilibrados"
  eram ruído da régua, não desequilíbrio.)*
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
| 0,25 | 0,0408 | 0,3773 | 1,2 | 5,4 | +0,018 | 80% |
| 0,5 | 0,0444 | 0,3462 | 0,4 | 5,2 | −0,050 | 80% |
| **1,0** | **0,0415** | **0,2448** | 0,4 | **10,2** | **+0,415** | 80% |
| 2,0 | 0,1829 | 0,1395 | 4,2 | 15,0 | +0,601 | 20% |
| 4,0 | 0,3561 | 0,0902 | 7,8 | 15,8 | +0,716 | 0% |

O formato é o mesmo de antes — `dominance` plano em 0,041–0,044 até λ = 1,0 e explodindo
depois —, mas a conclusão ficou mais forte: **λ = 1,0 não empata com os λ menores, ele os
domina**. Mesmo `dominance`, drift 0,10–0,13 melhor, e τ dez vezes maior. Abaixo de 1,0 o
AG paga identidade sem comprar equilíbrio.

### Sweep dos pesos do dominance — os secundários seguem indispensáveis

| pesos g/cap/decis | global_term | cap_term | decis_term | drift | counters | roster eq. |
|---|---|---|---|---|---|---|
| 1 / 2 / 0,5 | 0,0413 | **0,0000** | 0,0043 | 0,3481 | **0,0** | 100% |
| 1 / 1 / 1 | 0,0304 | **0,0000** | 0,0000 | 0,3008 | **0,0** | 100% |
| **1 / 0,5 / 0,5** | 0,0398 | 0,0034 | 0,0000 | **0,2448** | 0,4 | 60% |
| 1 / 0,5 / 0 | 0,0308 | 0,1188 | 0,0000 | 0,2479 | 2,6 | 20% |
| 1 / 0 / 0 | **0,0230** | 0,7970 | 0,2689 | 0,1564 | **8,6** | 0% |

**`1/0/0` continua sendo a falsificação.** Sem os secundários o AG atinge o melhor
`global_term` de todos (0,0230 — é a única coisa que resta a otimizar) e entrega 8,6 dos
10 pares como counter duro: os cinco na banda global, toda luta um massacre. É o
*blowout-coinflip* que a formulação C2 previa.

**E o `decis_term` não é inerte.** Removê-lo sozinho (1 / 0,5 / 0) leva os counters de
0,4 a 2,6 e **piora o próprio `cap_term`**, de 0,0034 para 0,1188. Ler 0,0000 no
indivíduo final é o termo tendo funcionado.

**`config.py` inalterado.** Subir o peso do cap melhora counters e roster equilibrado ao
custo de ~0,06–0,10 de drift e de metade da concordância de ranking — a n = 5 e no
orçamento reduzido, a troca não se distingue de ruído, e o eixo que ela sacrifica é
justamente o da pergunta de pesquisa.

### Sweep de elitismo / torneio — 10% / 3 mantidos, por outra razão

| braço | global_term | cap_term | drift | counters | L1+L2 | τ |
|---|---|---|---|---|---|---|
| elitismo 0 | 0,0640 | 0,0074 | 0,2689 | 0,8 | 10,2 | +0,301 |
| elitismo 5% | 0,0377 | 0,0096 | 0,2890 | 0,6 | 9,0 | +0,238 |
| **elitismo 10% · torneio 3** | 0,0398 | 0,0034 | **0,2448** | 0,4 | 10,2 | **+0,415** |
| elitismo 20% | 0,0398 | 0,0087 | 0,2809 | 0,6 | 8,8 | +0,186 |
| elitismo 30% | 0,0320 | 0,0790 | 0,2848 | 1,6 | 8,6 | +0,204 |
| torneio 2 | 0,0401 | **0,0003** | 0,2637 | **0,2** | **10,8** | +0,356 |
| torneio 5 | 0,0309 | 0,0163 | 0,2913 | 0,6 | 7,8 | +0,172 |
| torneio 7 | 0,0324 | 0,0115 | 0,3402 | 0,6 | 7,0 | +0,047 |

**Nenhum braço domina o default, e com a régua fina ele ficou mais forte.** Tem o **melhor
drift e a melhor concordância de ranking** dos oito, e agora também o segundo menor
`cap_term` e o segundo menor número de counters — só o torneio 2 o supera nesses dois
(0,2 counter contra 0,4; `cap_term` 0,0003 contra 0,0034), e paga com drift pior
(0,2637 contra 0,2448) e τ menor (+0,356 contra +0,415). A n = 5 nada disso se separa do
ruído, e o torneio segue com padrão não monotônico. A afirmação continua sendo "testados,
nenhum braço os domina" — não "ótimos".

> A leitura de 2026-09-21 dizia que o default **não** tinha nem o menor `cap_term` nem o
> menor número de counters. Era a régua de 200 lutas: ela inflava o `cap_term` do default
> de 0,0034 para 0,0176 e os counters de 0,4 para 0,8, o bastante para três braços
> passarem à frente. Mesmos indivíduos, mesma conclusão de fundo — mas a razão pela qual
> o default se mantém voltou a ser a simples.

## 3. Limites estruturais

Escopo declarado, não conserto — lista completa em
[`10-known-issues`](../reference/10-known-issues.md) §2. Os que a bateria de 2026-09-21
reforçou:

- **A política é fixa e cega ao estado**, e é a objeção mais forte ao resultado. A
  bateria acrescenta duas evidências: os três pesos ocupam o fundo do ranking de
  sensibilidade (dois abaixo do piso de ruído), e as duas regras que quebram a robustez
  do AG são exatamente as que mexem em espaço e compromisso da política.
- **O ciclo de vantagens não é realizado** (105 de 186 arestas decididas, 56,5%,
  p = 0,091; nulos 49,7%, a 16.000 lutas por par). Consequência declarada de o objetivo ser
  cego à direção — e o próprio canônico realiza só 6/10, sendo uma hierarquia (1,00 de 5
  tríades) e não um ciclo.
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
