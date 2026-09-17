# Retomada — estado do projeto em 2026-09-17

Este arquivo é o retrato do **agora**. O histórico (levantamento de 2026-09-09, rodada
de metodologia, auditoria de coerência e reforma do combate de 2026-09-10) está no git;
o que segue é o estado depois de fechar os **passos 2 a 8 da ordem** — itens A, B, E, C,
H, R, a **bateria completa** com `results/` regenerado, e o **item F** (família de Holm).

- Pauta da auditoria, com o que foi verificado e o que segue aberto: [`REVIEW.md`](REVIEW.md).
- **Ordem de execução do que falta:** [`REVIEW.md` §8](REVIEW.md).
- Auditoria do combate, com os números antes/depois: [`docs/reference/11-combat-review.md`](docs/reference/11-combat-review.md).
- Pontos em aberto do sistema: [`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md).
- Trajetória das decisões: [`docs/tcc/04-caminhos-e-decisoes.md`](docs/tcc/04-caminhos-e-decisoes.md).

---

## 0. Comece por aqui

1. **O ambiente não sobe sozinho.** `.venv/` é gitignored e o Python do sistema (3.14)
   não tem `numpy`/`numba`/`scipy`. Rode `setup.ps1` antes de qualquer coisa.
2. **`results/` está ATUAL e COMPLETO** — bateria de 2026-09-17, sob o motor final
   (rotação do stream, persistência 5, drift invariante à escala dos pesos), com os quatro
   rótulos de `external_validation` no mesmo corte. Números em §3. Dois headlines: a
   degradação entre o número de dentro do laço e o de fora caiu de **21× para 1,2×** no AG
   e de **8,2× para 1,1×** no NSGA-II; e o roster do AG escalar é o **primeiro do projeto
   a sair ROBUSTO** da validação externa (0/10 counters em 10 condições).
3. **A agenda de calibração ([`REVIEW.md` §9](REVIEW.md)) está FECHADA** — os sete itens
   decididos com evidência. Quatro mantiveram o valor vigente com justificativa escrita;
   três mudaram e obrigaram a esta regeneração. Detalhe em §1c, §1d e no
   [`docs/tcc/04`](docs/tcc/04-caminhos-e-decisoes.md).
4. **O que falta, em ordem:** os itens de §4 — instrumentação (`converged_at` por
   semente, snapshot de config nos artefatos) e os experimentos decididos e não rodados
   (sweep de `LAMBDA_DRIFT`, n = 20). Depois a **redação**, passo 9 do
   [`REVIEW.md` §8](REVIEW.md): `values.tex` (inteiramente obsoleto) e as seis referências
   estatísticas ausentes dos três `.bib`.

> ✅ **Os quatro rótulos de `external_validation` estão no mesmo corte** (2026-09-17).
> Os três que faltavam (`_canonical`, `_evolved`, `_nsga2_knee_point`) foram regerados —
> e o `_evolved` mudou o resultado principal, ver §3.

## 1. O que foi feito em 2026-09-16 — passos 2 a 7 (A, B, E, C, H, R + bateria)

### (A) Identidade: duas réguas, uma de cada lado da linha premissa/resposta

A discussão que destravou o item foi conceitual, não de código: *"o AG não devia ter
influência em preservar identidade, senão a pergunta do TCC fica circular"*. A
preocupação é válida como princípio mas mirava o alvo errado — e a resposta virou a
**linha que organiza o projeto inteiro**, agora registrada no topo do `CLAUDE.md`:

> **O fitness pode codificar a PREMISSA, nunca a RESPOSTA.**
> "O Zoner é definido por alcance" é premissa (dado da FGC, anterior à pergunta de
> equilíbrio). "O Zoner deve vencer o Grappler" é resposta. Daí a assimetria: identidade
> **é** termo do fitness, o ciclo de vantagens **não é**.

Três argumentos fecham a questão: (i) o projeto já tinha identidade no fitness por
decisão explícita (`LAMBDA_DRIFT = 1.0`, *"penalized but never hard-constrained"*);
(ii) penalidade não é restrição — com ela ligada o run inteiro, o AG **mesmo assim**
destruiu a identidade (8/21 no validador), então ter o termo não pré-determina a
resposta; (iii) tirar drift do fitness mataria o braço NSGA-II inteiro, porque uma
fronteira de Pareto precisa de dois objetivos.

O problema real era outro: **os dois instrumentos discordavam sobre o que "identidade"
significa**. Arquitetura adotada:

| régua | o que mede | onde vive |
|---|---|---|
| identidade **estrutural** | os genes continuam reconhecíveis | `drift_penalty`, **no fitness** |
| identidade **funcional** | o personagem continua *jogando* como ele mesmo | Layer 3 + ciclo, **post-hoc** |

Mudanças no código:
- **Normalização pelo range do bound**, `(x − lo)/(hi − lo)` em vez de `x/hi`, no fitness,
  na Layer 2 do validador e no `drift_table` — uma definição só de "normalizado".
- **`ArchetypeDefinition.defining_genes`** (campo congelado novo): os genes em que cada
  arquétipo ocupa um extremo por design, espelhando as asserções inter da Layer 1. Pesam
  `DRIFT_DEFINING_WEIGHT = 3.0` no drift contra 1.0 dos demais.
- O `drift_table` marca os definidores com ★ e mostra o peso por gene; o validador
  declara na própria docstring que as Layers 1-2 ficaram **parcialmente endógenas**.
- `test_fitness` ganhou cobertura do drift: canônico zera, definidor pesa exatamente
  3× (razão dos quadrados), desvio fica em [0,1], nomes em `defining_genes` são válidos.

**O que isso conserta, medido.** A ordenação por drift agora bate com a do validador —
e quem conserta é a **normalização**: sob `x/hi` o AG dava 0,2607, *abaixo* do
`best_dominance` (0,2709), invertendo 8/21 contra 11/21. A ponderação alarga a margem
(scores do validador re-medidos após a correção — a Layer 2 usa a mesma normalização, e
a auditoria de 2026-09-10 registrou 20/16/13/7 sob a convenção antiga):

| variante | knee (19/21) | ideal (16/21) | best_dom (11/21) | AG (8/21) | ordem bate? |
|---|---|---|---|---|---|
| `x/hi` uniforme | 0,0885 | 0,1554 | 0,2709 | 0,2607 | **não** |
| range, uniforme | 0,1302 | 0,2062 | 0,3245 | 0,3417 | sim |
| range, ponderada | 0,1279 | 0,2054 | 0,3150 | 0,3579 | sim |

### (B) Equilíbrio: o piso de decisividade virou guarda de degenerescência

`MATCHUP_FLOOR` foi de **0,10 para 0,02**. A premissa por trás do piso ("abaixo dele é
quase-empate, luta que não aconteceu") **não vale no motor reformado**: medido, **100%
das lutas terminam em KO** em 70 pares, incluindo rosters aleatórios. `D` baixo nunca é
"a luta não aconteceu" — é KO no fio, a melhor luta possível. O piso punia exatamente o
desfecho que o projeto quer, e empurrava contra o termo primário.

| regime | `D` |
|---|---|
| degenerado (HP máx / dano mín / GUARDA total; 0% KO, timeout com HP idêntico) | ≤ 0,008 |
| espelho puro dos 5 canônicos (par equilibrado por construção) | 0,020 – 0,033 |
| pares reais (70 pares medidos) | ≥ 0,045 |

0,02 é a base da faixa do espelho — abaixo do que dois personagens **idênticos**
produzem. Efeito isolado: a 0,10 o piso penalizava 5/10, 5/10 e 3/10 pares nos três
indivíduos evoluídos; a 0,02 penaliza **0/10 em todos**.

Segunda metade do item: `_dominance_penalty` devolve um **`DominanceTerms`**
(`global_term`, `cap_term`, `decis_term`) guardado no `FitnessDetail`. O `multi_run`
grava os três por semente e agregados; o `compare_algorithms` imprime a decomposição
lado a lado. É **descritiva** e fica fora da bateria de Mann-Whitney de propósito —
acrescentar métricas ali inflaria a correção de Holm (item F).

### O achado que sobrevive a tudo isso

AG curto sob o fitness novo (pop 120, 25 gerações, 80 sims/par, seed 42, serial):

```
dominance = 0,0896   (global 0,0816 | cap 0,0160 | decis 0,0000)
drift     = 0,2973
WR global [43,7% … 56,1%]          WR por par: 34% … 66%
decisividade por par: 0,045 … 0,072
validador: estrutural 7/17 · completo 10/21
```

O piso parou de morder (`decis_term` = 0,0000 exato). O `cap_term` **voltou a morder**
(0,0160) — a reforma do combate abriu espaço para vantagem par-a-par, que é o que o cap
regula; o sweep de `MATCHUP_WR_CAP` voltou a fazer sentido, fica para a calibração (H).

E o principal: **o AG continua trocando identidade por equilíbrio**, com as falhas
caindo exatamente sobre os genes definidores (os 3 do Rushdown, os 3 do Zoner, 3 dos 4
do Turtle). A régua ficou afiada; a resposta em λ_drift = λ_dom = 1,0 **não mudou**.
Isso é o achado, não o bug — e é a evidência de que o termo de identidade não
pré-determina nada. O mapa do trade-off (fronteira do NSGA-II, e possivelmente um sweep
de `LAMBDA_DRIFT`) é onde a resposta da tese vive.

> Ressalva: run curto, uma semente. Não é resultado publicável — é sanity do fitness
> novo. Os números da tese saem da bateria do passo 7.

### (E) Convergência: o gate virou o próprio critério, e a confirmação virou real

Duas correções no mesmo item.

**O gate era insatisfazível por construção.** `dominance_penalty <= 1e-9`, sendo que
`global_term` é uma RMS sobre contagens discretas — com 600 lutas por personagem, o
menor valor não-nulo é `(1/600)/0,5/√5 ≈ 0,0015`. Não há continuum entre 0 e isso, então
`1e-9` significava **exatamente zero**. `converged` era `False` sempre e todo o ramo de
confirmação era código morto descrito na metodologia. Agora o gate é
`roster_balanced(best_detail)` — o mesmo predicado da confirmação, sobre a avaliação que
já está em mãos. Subir para um escalar calibrado manteria uma versão branda do defeito:
o composto inclui o `decis_term`, que **não faz parte da definição de convergência**.

`roster_balanced` é novo em `fitness.py` e virou a fonte única da definição de
equilíbrio do projeto — consumida pela convergência do AG e pelo veredito por semente do
`multi_run`, que tinha uma cópia inline.

**Achado novo: a confirmação não confirmava nada.** `ga.run` fazia `set_seed_base(seed)`
e `evaluate_detail_n` resseta ao mesmo base — a "reavaliação independente" rodava 200
sims em vez de 150 **no mesmo stream de RNG**. CRN é o certo para *seleção* e errado
para *validação*. Medido no indivíduo que convergia:

| stream | equilibrado? | bonecos em banda | counters duros |
|---|---|---|---|
| treino (42) — o que a confirmação usava | **sim** | 5/5 | 0 |
| 9999 / 10000 / 10001 / 10002 | não | 5/5 | 1–2 |

O que quebra é sempre o par-a-par, nunca a WR global. A confirmação passou a usar
`seed + CONVERGENCE_SEED_OFFSET` (100000). **Convergir agora significa que o equilíbrio
sobrevive a um stream que o AG nunca viu**, e o `best_detail` devolvido é medição fora da
amostra. Efeito medido no mesmo run curto: o gate dispara **16×** em 60 gerações e a
confirmação rejeita **as 16** — o ajuste ao stream, quantificado.

Cobertura nova: `src/tests/test_ga.py` (7º smoke test) fecha o contrato — as réguas do
`roster_balanced`, o fato de arestas de ciclo não reprovarem, e a confirmação usando
stream diferente e restaurando o base do treino.

### (C) NSGA-II: o seed canônico era imortal e comia metade da fronteira

O diagnóstico anterior ("colapso de pressão seletiva no front0") **estava errado**. A
causa é uma assimetria entre os dois objetivos: **`drift` tem piso 0 e o piso é
alcançável** — o canônico *é* a referência, drift exatamente 0,0000 — enquanto o piso de
`dominance` não é. Dominar `(1,2418, 0,0000)` exigiria `drift < 0`, que não existe. O
seed canônico é portanto **imortal no rank 0**, por pior que seja o equilíbrio dele, e a
mesma proteção vale para a vizinhança de drift ~0. O crowding não limpa: ele só poda
quando um front **transborda** a população, e front0 (78) nunca passou de 120.

Medido, única diferença sendo a população inicial (pop 120, 60 gerações, 80 sims, seed 42):

| | com seed canônico | sem seed canônico |
|---|---|---|
| min `dominance` da fronteira | 0,2233 (estagnado) | **0,0896** (ainda caindo) |
| pontos com `dominance ≥ 1.0` | **40/78** | 1/44 |
| front0 na geração 50 | 89/120 | 31/120 |
| drift coberto | [0,000, 0,161] | [0,124, 0,300] |

Metade da fronteira eram rosters tão desequilibrados quanto o canônico intocado, comendo
um terço da população **e um terço do esforço reprodutivo** — e a fronteira nunca chegava
na faixa de drift ~0,29 onde moram as soluções equilibradas.

**Correção:** o NSGA-II inicia com população 100% aleatória. No **AG escalar o mesmo seed
ajuda e fica** — lá o fitness é um número só, o canônico é ruim nele e some depois de
doar genes (medido: com seed drift 0,2874, sem 0,3365, mesmo dominance). A assimetria é
deliberada e está declarada.

**Verificado no orçamento real (150 gerações):** a nuvem **não reaparece** — 0/49 pontos
com `dominance ≥ 1.0`, nenhum imortal. O min drift desce sozinho (0,2934 → 0,0804),
porque o NSGA-II seleciona por drift baixo, mas os pontos chegam lá **com dominance
razoável**. O acúmulo vinha do seed, não da dinâmica: nenhum mecanismo novo é preciso. Se
reaparecer em outro regime, a ordem de intervenção é supressão de duplicatas →
ε-dominância (Laumanns et al. 2002) → NSGA-II com restrições (Deb 2002 §VI).

**Novo representante `scalar_optimum`** (parte (c) do item): mínimo de
`LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift`, a mesma função que o escalar otimiza.
A comparação usava `ideal_point`, que minimiza a norma **L2** — comparável errado. É o
único ponto do NSGA-II que lê os `LAMBDA_*`, e é reporting, não busca.

**Resultado final, orçamentos iguais** (pop 120, 150 gerações, 80 sims, seed 42):

| | dominance | drift | L1 |
|---|---|---|---|
| AG escalar | **0,0088** | 0,2856 | 0,2945 |
| `scalar_optimum` da fronteira | 0,0481 | 0,1634 | **0,2115** |

A alegação "o ponto do escalar domina a fronteira" **caiu**: ele domina 3 de 49 pontos,
nenhum o domina, e o NSGA-II agora vence o escalar **na própria função que o escalar
otimiza**. A frase "o escalar é *um ponto* do trade-off que o NSGA-II mapeia" segue não
sendo literalmente verdadeira, mas por outro motivo: o escalar alcança dominance 0,0088,
**abaixo de toda a faixa da fronteira**, então fica *além* da ponta dela — não fora por
sub-convergência. Cada um alcança uma parte diferente do trade-off, nenhum sub-convergido.

E um bônus para o item (E): nessa mesma rodada de 150 gerações o AG **parou por
convergência**, com o critério confirmado num stream que ele nunca viu. O critério novo é
alcançável — só exige convergência de verdade.

### (H) Nenhuma métrica do projeto tinha piso

O item era "recalibrar os canônicos para o ciclo existir". Ele **não é isso** — e o
diagnóstico vale para muito além do ciclo.

**Por que calibrar o ciclo é perseguir uma loteria.** O ciclo canônico é um torneio
**regular**: cada arquétipo vence exatamente 2 e perde 2. Existem **24** torneios
regulares rotulados em 5 vértices, então acertar o rótulo específico é 1/24 ≈ 4,2%; e
como cada aresta é cara-ou-coroa, o acaso já entrega 5/10. O alvo é inatingível **como
evidência**, independentemente de ser atingível como valor.

**O achado maior.** Todas as métricas de identidade eram lidas contra o **teto**, como se
o piso fosse zero. Medido com 13 rosters nulos (5 espelhos + 8 aleatórios):

| métrica | piso médio | pior nulo | teto |
|---|---|---|---|
| validador (L1-L3) | ~6,8/21 | **12/21** | 21/21 |
| `drift_penalty` | 0,408 aleatório · 0,326 espelho | 0,326 | 0,000 |
| arestas do ciclo | 5/10 | 8/10 | 10/10 |

Um roster **aleatório** tirou 12/21 no validador. Cinco personagens **idênticos** tiram
7–10/21, porque asserção de ranking com empate se resolve por ordem de índice. E entre
drift 0,287 (evoluído) e 0,326 (todos idênticos) há **0,04** — a régua central da tese
quase não distingue preservação de aniquilação.

**Ferramenta nova:** `src/tools/baselines.py` monta canônico + 5 espelhos + N aleatórios
e reporta cada métrica como `posição = (valor − piso)/(teto − piso)`, com o **pior nulo**
e um **p-valor empírico**. O piso é distribuição, não ponto. Cobertura em
`src/tests/test_baselines.py` (8º smoke test).

**Veredito nos indivíduos existentes:**

| indivíduo | identidade | equilíbrio |
|---|---|---|
| `results.json` (motor antigo) | **no piso** — p = 0,46 / 0,38 / 0,23; ciclo 4/10 abaixo do acaso | — |
| AG sob motor/fitness novos | **~30% acima do piso**, p ≈ 0,08 (sugestivo, não estabelecido) | **99%** do trivialmente alcançável |

**O espelho responde à objeção que estava em aberto.** Cinco idênticos são a solução
trivial de equilíbrio e equilibram *melhor* que o evoluído (dominance 0,02–0,05 contra
0,049). "Por que não deixar todos iguais?" agora tem resposta numérica, e os cantos
degenerados podem ser marcados no gráfico da fronteira.

**O que substitui o ciclo:** tríades circulares (Kendall & Babington Smith 1940), escala
0 (ordem estrita) · 2,5 (acaso) · 5 (máximo). O máximo **é** o torneio regular, que **é**
equilíbrio global perfeito — um roster estritamente transitivo teria WRs 100/75/50/25/0,
incompatível com todos perto de 50%. Logo **equilíbrio global não é achatamento: ele
força não-transitividade**. Demonstrável, sem depender de autoria. O AG novo dá 3,0
tríades com pares em 34%–66% (arestas decididas). Coberto por teste: o ciclo **invertido**
dá 0/10 arestas e ainda 5 tríades — a estrutura sobrevive à troca de rótulos, que é
exatamente por que o rótulo não é o achado.

**Os canônicos não precisam de recalibração.** Eles não precisam realizar o ciclo nem ser
equilibrados — serem desequilibrados é o ponto de partida do problema. O que faltava era
piso contra o qual lê-los.

### (R) O agarrão: um gene fechou três lacunas

`grab_power`, 8º atributo, ∈ [0, 1] — a **fração da guarda quebrada**. Contra alvo em
`DEFEND` o multiplicador do dano vira `defend_red + grab_power` (soma simples — ver o
bloco do agarrão em `combat.py`): 0,6× em `grab = 0`, 1,0× no ponto neutro 0,40 e
**1,6× no teto**.

Três escolhas de desenho, todas deliberadas:
- **mesmo alcance e mesmo cooldown** do ataque normal;
- **efeito nenhum contra quem não está defendendo** — é isso que o torna um *counter* e
  não um golpe superior: vale contra quem bloqueia, é peso morto contra quem pressiona;
- **nunca supera um golpe limpo** — no teto apenas iguala. Anula a vantagem de defender,
  não a inverte.

E por ser uma **condicional na resolução** em vez de uma ação escolhida, o modelo de dois
canais fica intacto: nada de `w_grab` nem quarta postura.

**A régua é o ponto neutro.** O multiplicador do dano contra quem defende é
`defend_red + grab_power`, então o neutro fica em `1 − defend_red = 0,40`: abaixo dele
defender ainda compensa, acima **defender é pior que não defender**.

| arquétipo | `grab_power` | multiplicador |
|---|---|---|
| Zoner | 0,05 | 0,65× |
| Turtle | 0,15 | 0,75× |
| Rushdown | 0,20 | 0,80× |
| Combo Master | 0,30 | 0,90× |
| **Grappler** | **0,90** | **1,50×** — único acima do neutro |

**Medido** (`test_combat`, alvo sempre em guarda): dano por golpe **16,2 → 43,2** ao
varrer `grab_power` de 0 a 1, exatamente o golpe limpo no neutro 0,40, e diferença
**exatamente zero** contra alvo que não defende.

| sintoma | estado |
|---|---|
| eixo Recurso sem contrapartida | ✅ defender deixou de ser grátis |
| Layer 3 com 4 asserções para 5 arquétipos | ✅ Grappler ganhou `guard_break`; validador **23/23** no canônico |
| aresta "Grappler vence Turtle" sem mecanismo | ⚠️ parcial — ver abaixo |
| Grappler com um único gene definidor | ✅ agora `damage` + `grab_power` |

**A ressalva honesta:** o Grappler vence o Turtle em 100% no canônico, mas **já vencia
antes** do agarrão — o Turtle canônico perde para todo mundo (WR global 0%). A mecânica
agora existe e dá ao AG uma alavanca para realizar a aresta **por mérito**; se o ciclo
emerge disso é pergunta para a bateria, não coisa fechada aqui. O contador de arestas
segue em 5/10 no canônico, que é o piso do acaso — ver (H).

O item que mais ganhou com isso foi o (A): a Layer 3 é **a régua independente de
identidade** do projeto, e ela estava incompleta.

**Custo pago:** 8º atributo propagado por bounds, canônicos, drift, validador, viewers e
testes. Os testes que repetiam a aridade (`== 10 genes`, `== 12 asserções`) passaram a
**derivar das tabelas** — o próximo gene não os quebra.

### Critério de parada: os dois algoritmos param por orçamento

O AG **não para mais cedo**. `converged_at` e `stagnated_at` viraram eventos registrados
e a execução vai sempre até `MAX_GENERATIONS`.

O NSGA-II não tem como parar pelo critério do escalar: *"o roster está equilibrado?"* não
se pergunta a uma **fronteira**, que de propósito contém pontos desequilibrados e fiéis —
e perguntar a um representante faz a resposta depender de escolha arbitrária. Parar o
escalar mais cedo tornaria a comparação ambígua: "melhor" ficaria indistinguível de "usou
menos orçamento".

Com os dois em orçamento fixo ganha-se duas coisas: a comparação vira **qualidade sob
orçamento igual**, e `converged_at` vira um segundo eixo, de **velocidade**, que não
existia. Na primeira execução completa com o motor novo (seed 42): **convergiu na geração
11**, estagnou na 106, rodou as 150.

Custo medido da mudança: 1 geração ≈ 1,18s na config real (pop 300, 150 sims, 8 workers),
então uma execução do AG ≈ 3 min, do NSGA-II ≈ 6 min, e a bateria de 10 sementes × 2
algoritmos ≈ 90 min.

## 1b. Passo 8 — item (F): a família de Holm estava inflada

`n_chars_balanced` dá **5/5 nas 20 execuções** (10 por algoritmo). Amostra conjunta
constante ⇒ `mannwhitneyu` devolve `p = nan`, porque a correção de empates zera o
denominador. Isso não é um teste — mas entrava na família de Holm como se fosse, e o
multiplicador virava **4 em vez de 3**. Cada métrica na família **encarece todas as
outras**; uma sem variação cobra pedágio sem contrapartida.

Segundo defeito, silencioso: `_holm` ordenava os p-valores com um `nan` dentro. Toda
comparação com `nan` é falsa, então a posição dele dependia do algoritmo de ordenação —
saía certo por sorte.

**Correção.** `_is_degenerate` monta a família pela variância da amostra **conjunta**.
O critério é objetivo e decidido pelos dados, então é declarável **antes** do teste —
não é escolha de família feita depois de ver os p-valores, que seria o problema oposto.
E é a amostra conjunta de propósito: `ga` constante em 5 contra `nsga2` constante em 3
é a diferença mais forte possível, não degenerescência. A métrica excluída segue
reportada como **descritiva**, com a nota do porquê; `family_size` e
`excluded_from_family` vão gravados no artefato. `_holm` passou a **levantar
`ValueError`** ao receber `nan` — o filtro a montante garante que nunca dispare.

| família | `drift_penalty` (p bruto 0,0257 · Â₁₂ 0,80, efeito grande) |
|---|---|
| 4 métricas (antes) | 0,1030 |
| **3 — a correta, hoje** | **0,0772** |
| 2 (só os dois objetivos) | 0,0515 |

**O achado NÃO virou significativo, e isso é o ponto.** Nem a família mínima possível
chega lá: para em 0,0515, acima de α por 0,0015. Não havia prêmio em escolher a família
menor, o que é exatamente o que torna o conserto defensável — é correção, não resultado.

A leitura para a tese: **efeito grande (Â₁₂ = 0,80), direção consistente, não
significativo a n = 10 sementes.** O que resolveria é poder amostral — item (7) da
agenda de calibração, e ele é **aditivo**.

> Correção de registro: o `REVIEW.md` §6 citava `n_hard_counters` saindo com
> `p_Holm = 0,0495` ("significativo por 0,0005"). Era da bateria **anterior**. Na de
> 2026-09-16 essa métrica dá `p = 0,968`, Â₁₂ = 0,49, desprezível. O texto foi
> reescrito com os números de hoje.

Cobertura nova: `src/tests/test_compare_algorithms.py` (**9º smoke test**) — o critério
de degenerescência ser da amostra conjunta, o `nan` recusado em vez de ordenado por
sorte, o custo de cada métrica na família, e o fato de que filtrar não fabrica
significância.

> **Nota de ambiente:** o `.venv` tinha `numpy`/`numba`/`matplotlib` mas **não**
> `scipy`, que está pinado no `requirements.txt` e é o que o `compare_algorithms`
> importa. Instalado nesta sessão (`scipy==1.18.1`). Se o ambiente for recriado, o
> `setup.ps1` cobre.

## 1c. Agenda de calibração — itens (1) e (2) fechados, sem mudar número

Os dois foram **mantidos**, com a justificativa que faltava escrita no `config.py`.
Como nenhum valor mudou, **`results/` continua válido**.

### (1) `DOMINANCE_DECIS_WEIGHT = 0.5` — a premissa do item estava errada

"O termo está morto" vinha de `decis_term = 0,0000` em 10/10 sementes — mas isso é
medido **só nos indivíduos finais**. Uma guarda que lê 0 no fim é uma guarda que
funcionou: a busca saiu da região ruim. Medido em 18 rosters × 10 pares:

| roster | `decis_term` | pares fora da banda |
|---|---|---|
| **canônico** — que *é* a geração 0 do AG escalar | **0,2834** | 5/10 acima do TETO |
| 8 aleatórios | 0,1005 – 0,6596 | 3–9/10 acima do TETO |
| espelho do Zoner — a solução trivial | 0,1282 | **10/10 abaixo do PISO** |
| 4 evoluídos | 0,0000 | 0/10 |

57/180 pares estouram o teto; `D` chega a **0,4903** contra teto 0,20. As duas metades
disparam e pegam coisas distintas: o teto pega blowout, o piso pega a **solução
trivial** — o espelho, exatamente o roster contra o qual a tese argumenta.

> Ressalva: a evidência sustenta que o termo **opera**; não calibra o peso 0,5 contra
> alternativas. Isso seria um sweep, e nada pede um.

**Correção de registro colhida junto:** o comentário do `MATCHUP_FLOOR` afirmava que
0,02 fica "abaixo do que dois personagens idênticos produzem". Falso — o espelho do
Zoner dá `D ∈ [0,016, 0,019]`, e a faixa dos espelhos é bem mais larga do que estava
registrado (Zoner 0,016–0,019 · Turtle 0,027–0,032 · Rushdown 0,030–0,035 · CM
0,045–0,052 · Grappler 0,074–0,088). O piso é abaixo de todo par de personagens
**distintos**, e morde 0/10 nos quatro evoluídos. Comentário corrigido.

### (2) `MATCHUP_WR_CAP = 0.15` — âncora de domínio + margem de ruído

A grade de matchup da FGC é dita em inteiros: 5-5, 6-4, 7-3, 8-2 — em `|WR − 0.5|`,
0,00 · 0,10 · 0,20 · 0,30. **6-4 é vantagem saudável, 7-3 é counter**, então o cap tem
de permitir 0,10 e barrar 0,20.

O que decide entre os candidatos é o ruído: limiar colado num ponto da grade vira
cara-ou-coroa. Com σ ≈ 0,040 em p = 0,6:

| cap | limiar | 6-4 real dispara à toa | 7-3 real é capturado |
|---|---|---|---|
| 0,10 | 0,60 | **50,0%** | 99,6% |
| **0,15** | 0,65 | **10,6%** | **90,9%** |
| 0,20 | 0,70 | 0,6% | **50,0%** |

0,15 é o ponto médio da única lacuna que importa. Subir `SIMS_PER_MATCHUP` (item 3)
estreita as duas caudas **sem mover o cap** — os itens são independentes.

Não houve sweep de propósito: o cap **é** a definição de "counter duro", e defini-lo
pelo que o motor produz seria a mesma circularidade que mantém o ciclo fora do fitness.

## 1d. Agenda — item (4) fechado; (6) e (7) medidos, execução em bundle

### (4) Canônicos — **finais**

"Melhor valor" não existe aqui por construção: os canônicos são a **premissa**, não uma
variável a otimizar. Ajustá-los para "ficarem melhores" seria mexer na premissa para obter
a resposta. O critério só pode ser **coerência** — e o que faltava era escrevê-lo:

| # | exigência | medido |
|---|---|---|
| 1 | internamente coerentes | validador **23/23** |
| 2 | distintos entre si | 10 distâncias par-a-par ≥ **0,3221** (mín. CM × Grappler) |
| 3 | desequilibrados — o ponto de partida | `dominance` **1,2690**; Turtle 0,0%, Rushdown 99,6% |

E o que **não** se exige, com a razão: realizar o ciclo (loteria de 1/24 — item H) e ser
equilibrado (seria o problema resolvido de graça).

**Duas limitações declaradas.** (a) **5 dos 55 genes estão colados no bound, 4 deles
definidores** — Rushdown `attack_cooldown` = 1,0 e `speed` = 5,0; Turtle `hp` = 450,
`attack_cooldown` = 5,0 e `damage` = 15,0. É intencional, mas esses genes **só podem
driftar para dentro**: a identidade do Rushdown e da Turtle é assimetricamente protegida
num sentido e erodível no outro, e o `drift_penalty` não distingue os casos. (b) Os
canônicos **são** a referência do drift — mudá-los invalidaria todo número de drift já
medido, o que por si é razão forte para congelar agora que passam.

### (6) Escala dos pesos — 7,5%, não 55%

O número antes registrado (55% no Turtle) vinha de uma conta **confundida por escala**:
comparava distância no espaço bruto com distância no normalizado. Medição exata — escalar
os 3 pesos por `k > 0` não muda nada no combate, então o drift que some ao escolher o
melhor `k` é cobrança por diferença indistinguível:

| arquétipo | drift real | drift mín(k) | k ótimo | % desperdiçado |
|---|---|---|---|---|
| **Rushdown** | 0,3302 | 0,2804 | 0,654 | **15,1%** |
| Combo Master | 0,2957 | 0,2694 | 0,581 | 8,9% |
| Turtle | 0,3560 | 0,3394 | 0,702 | 4,7% |
| Grappler | 0,2516 | 0,2498 | 1,193 | 0,7% |
| Zoner | 0,0356 | 0,0356 | 0,992 | 0,2% |
| **MÉDIA** | **0,2539** | **0,2349** | | **7,5%** |

Os `k` ótimos de 0,58–0,70 dizem o que houve: o AG **inflou a escala dos pesos** e o drift
cobrou pela inflação. Atenua em parte que o artefato afeta também os modelos nulos, então
cancela na leitura de *posição*; não cancela no drift absoluto.

### (7) Sementes — **n = 20**

Poder medido (4000 réplicas, dois normais separados por 1,190σ = Â₁₂ 0,80, critério
`3 × p < 0,05`): **n=10 → 44,4%** · n=15 → 73,1% · **n=20 → 85,9%** · n=30 → 97,3%.

n = 20 é o menor que passa de 80%. Com os 10 atuais o experimento tem **menos de 50%** de
chance de detectar um efeito grande que provavelmente existe — "não significativo" ali diz
mais sobre a amostra que sobre os algoritmos. "Aditivo" vale no sentido estatístico (as
sementes 42–51 são determinísticas), **não** no de compute: `multi_run` não tem resume.

## 2. A leitura macro do modelo — 4 eixos, 1 ainda incoerente

| eixo | do que é feito | estado |
|---|---|---|
| **Espaço** | range, speed, knockback, posição, campo, colisão | ✅ coerente após M1+M1b+M2 |
| **Tempo** | cooldown, stun, persistência da intenção | ✅ coerente após M3 + item (5): a persistência caiu para **5 sub-ticks** = 1 tick = o cooldown mínimo, então quem tem `cooldown=1` e sorteia GUARDA abre mão de exatamente **uma** janela |
| **Recurso** | hp, damage, DEFEND, grab_power | ✅ coerente após (R) — o agarrão é o counter da guarda |
| **Política** | 3 pesos, amostragem proporcional | contínua; a degenerescência de escala deixou de contaminar a identidade (item 6 — `drift_genes` reescala), mas segue **cega ao estado**: não olha HP, distância nem se o oponente está stunado |

## 3. Resultados da bateria (2026-09-17) — sob rotação, persistência 5 e drift invariante

`results/` está **atual e coerente**. Bateria: AG e NSGA-II na seed 42, `multi_run` com
10 sementes × 2 algoritmos, `compare_algorithms`, `external_validation` e `baselines`
com 30 nulos.

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

> ⚠️ **Esta tabela foi corrigida em 2026-09-17.** A versão anterior lia "21× → 1,1×", mas
> comparava o **AG** de uma bateria com o **NSGA-II** da outra: a `external_validation`
> regenera só o rótulo que recebe, e a primeira passada da bateria rodou apenas
> `--nsga2 best_dominance`. O `_evolved` que estava no disco era da bateria de 16/09 —
> `git status` limpo e mtime recente (do checkout) não denunciavam nada. Com os quatro
> rótulos no mesmo corte, a comparação pareada é a de cima, e **ficou mais forte**: os dois
> algoritmos caem de degradação grande para ~1×. Registrado como pendência de
> instrumentação em [`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md)
> §1.2 — enquanto os artefatos não gravarem a config que os produziu, a defesa é rodar os
> quatro rótulos sempre.

### Agregado (10 sementes, reavaliação independente na seed 9999)

| | dominance | drift | hard-counters | bonecos em banda |
|---|---|---|---|---|
| **AG escalar** | **0,0387** (±0,0137) | 0,2598 | **0,40** ± 0,66 | 5/5 em 10/10 |
| **NSGA-II** | 0,0660 (±0,0630) | **0,1695** (±0,0319) | 2,40 ± 1,80 | 5/5 em 10/10 |

**A relação entre os dois se inverteu, e para melhor.** Na bateria anterior o NSGA-II
vencia em dominance (0,0541 contra 0,0701) e os dois ficavam próximos em tudo. Agora
cada um ocupa um extremo nítido do trade-off — e é a primeira vez que **as três métricas
da família de Holm saem significativas**, todas com efeito grande:

| métrica | p (Holm) | Â₁₂ | vencedor |
|---|---|---|---|
| `dominance_penalty` | **0,0257** | 0,20 | AG escalar |
| `drift_penalty` | **0,0030** | 0,94 | NSGA-II |
| hard-counters/execução | **0,0110** | 0,14 | AG escalar |

(Na bateria anterior, nenhuma era significativa e o melhor p era 0,0772.)

A decomposição diz **de onde** vem a diferença: `global_term` 0,0375 contra 0,0470 —
próximos —, mas `cap_term` **0,0000 contra 0,0497**. O NSGA-II não está globalmente
desequilibrado; ele tem **counters duros**. Essa é a leitura correta, e o composto
sozinho a esconderia.

### Por que o NSGA-II "piorou" em dominance — e por que não é regressão

O hipervolume ficou **igual** (1,8090 ± 0,0445 contra 1,8084 antes): a fronteira não
perdeu qualidade, ela **se deslocou**. A causa é assimetria entre os dois objetivos:

> **`drift` é determinístico** — função pura dos genes, sem RNG. **`dominance` é o único
> objetivo estocástico.** A rotação torna a dominância mais cara de otimizar e não toca
> no drift. A fronteira segue alcançando a ponta fiel (que não depende do stream) e
> **retrai na ponta equilibrada**, que antes era alcançada explorando uma realização
> específica. O hipervolume não muda porque a fronteira se redistribui no mesmo envelope.

E `best_dominance` é, por definição, o extremo de baixa dominância — quando essa ponta
retrai, o representante piora. **A piora é a correção.**

### Contra os modelos nulos (melhor do AG, 30 nulos)

| métrica | valor | piso médio | pior nulo | posição | p |
|---|---|---|---|---|---|
| validador (L1-L3) | 13/23 | 6,37 | 10 | 40% | **< 0,03** |
| validador (L1+L2) | 12/18 | 5,43 | 9 | 52% | **< 0,03** |
| `drift_penalty` | 0,218 | 0,409 | 0,327 | 47% | **< 0,03** |
| `dominance_penalty` | 0,026 | 1,136 | 0,025 | **102%** | 0,06 |
| arestas do ciclo | 4/10 | 5,0 | 8 | **−20%** | 0,97 |

Três leituras:

1. **A identidade supera TODOS os 30 rosters sem estrutura nos três eixos** (p < 0,03 em
   cada). E melhorou sobre a bateria anterior: drift 0,254 → 0,218, L1+L2 11/18 → 12/18.
2. **O equilíbrio chegou a 102% do espelho** — o roster evoluído é *mais* equilibrado que
   a solução trivial de cinco personagens idênticos (0,026 contra 0,025 do melhor
   espelho), mantendo identidade bem acima do piso. Era 94% na bateria anterior. Essa é a
   resposta numérica direta à objeção "por que não deixar todos iguais?".
3. **O ciclo autoral não é realizado** — 4/10 arestas, *abaixo* do acaso (5/10), p = 0,97.
   Já era esperado desde o item H (acertar o rótulo específico é loteria de 1/24). O que
   **é** resultado são as **tríades circulares em 4,0** (acaso 2,5 · máximo 5) com as WR
   por par espalhadas em 43%–55%, ou seja, arestas decididas: a **não-transitividade
   emergiu**, ainda que não no rótulo autoral.

### Validação externa — os quatro rótulos, mesmo corte

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
critério o AG passa limpo. A questão sobre trocá-lo por uma fração segue aberta no
[`REVIEW.md`](REVIEW.md) §6, agora sem o argumento de que ele seria severo demais para
qualquer roster.

### Convergência e estagnação

O AG da seed 42 **convergiu na geração 39** (confirmado num stream que nunca viu) e
`stagnated_at` ficou **`None`** — o que confirma a consequência que eu havia declarado
sem medir: sob rotação o fitness flutua entre gerações por troca de stream, o contador de
estagnação reseta por ruído e o evento não dispara.

> ⚠️ **Ressalva: isto ainda é n = 1.** O `multi_run` **passou a gravar** `converged_at` e
> `stagnated_at` por semente em 2026-09-17 (agregados em `convergence`: taxa + geração
> média entre as que convergiram), mas a bateria atual é anterior a essa mudança — os
> artefatos em `results/multi_run/` não têm os campos. A medição sobre as 10 sementes sai
> na próxima regeneração; até lá, "convergiu na geração 39" segue valendo só para a
> seed 42.

## 4. Itens ainda abertos

Inventário completo e comentado em
[`docs/reference/10-known-issues.md`](docs/reference/10-known-issues.md); aqui o resumo.

**Experimentos decididos ou levantados, nunca executados** (§1.1 do known-issues):

- **Sweep de `LAMBDA_DRIFT`** — o mais urgente. É o que transformaria "o escalar é um
  ponto do trade-off" de afirmação em curva. Hoje, na forma literal, a afirmação é falsa:
  o ponto do escalar cai **fora** da fronteira, passado o extremo de baixa dominância.
- **`MULTI_RUN_N_SEEDS`: n = 20 decidido, rodando em 10** — 44,4% de poder contra 85,9%.
  Não executado por custo (~180 min, sem resume).
- **Pesos 1,0 / 0,5 / 0,5 do dominance** e **elitismo 10% / torneio 3** — nunca variados.

**Instrumentação — fechada em 2026-09-17** (§1.2 e §4 do known-issues):

- ✅ **Carimbo de proveniência em todo artefato** (`src/engine/provenance.py`): timestamp,
  `fingerprint`, toda constante de `config.py` valor a valor, digest dos canônicos e digest
  do código do motor. `Individual.from_results` / `from_nsga2` verificam ao carregar e
  avisam **o que** mudou. Os artefatos da bateria atual têm carimbo retroativo, justificado
  por reprodução bit-exata (`provenance.backfilled` explica dentro do JSON).
- ✅ **`converged_at` / `stagnated_at` por semente** no `multi_run`, agregados em
  `convergence` (taxa + geração média entre as que convergiram). A assimetria com o
  NSGA-II fica declarada: ele devolve `None` e a chave não aparece no agregado dele.
  **A medição sobre as N sementes ainda não foi feita** — entra na próxima bateria.
- Segue aberto: pool de processos recriado a cada geração; `N_WORKERS = 8` é específico
  desta máquina.

**Limites estruturais — escopo declarado, não conserto** (§2): política fixa (a objeção
mais forte ao resultado) e **cega ao estado**; crossover só por bloco de personagem;
round-robin uniforme; hipersensibilidade dos genes de recurso; veredito binário da
validação externa; alinhamento CRN imperfeito depois do 1º matchup.

## 5. Aberto — redação

A monografia (`overleaf/TCC/`) está várias gerações de modelo atrás — `metodologia.tex`
descreve 9 atributos, `defense`/`recovery`, indivíduo de 60 genes, decisão por
prioridade, `specialization_penalty` e a formulação pré-C2 do `dominance_penalty`.
`main.tex` promete seis capítulos e existem quatro arquivos, com `conclusao.tex` em
branco. Decisão anterior: recomeçar do zero a partir de `overleaf/artigo-SBC/main.tex`,
que descreve o modelo melhor — **mas mesmo ele descreve um motor que não existe mais**
(ação única em vez de dois canais, sem colisão, sem empate).

O `values.tex` (idêntico nos dois artigos) está inteiramente obsoleto. Registrado também
em [`REVIEW.md`](REVIEW.md) §6: a macro do dominance do AG usa o número **dentro** do
laço enquanto as outras três células da mesma linha coincidem com os de fora — a única
célula com vantagem de proveniência é justamente a do AG.

Ponto novo para o texto: a macro `valAg = 7` assume o validador como resultado de
identidade enquanto o `drift_penalty` do mesmo indivíduo era lido como "identidade
preservada a 0,26". Com as duas réguas nomeadas (estrutural no fitness, funcional
post-hoc) a contradição some — mas o texto precisa ser reescrito com essa distinção
explícita.

Bibliografia: Derrac et al. 2011, Arcuri & Briand 2011 e Vargha & Delaney 2000 são
citadas nos docs e no código e **não estão** em nenhum dos três `.bib`.
