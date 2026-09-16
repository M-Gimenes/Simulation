# Retomada — estado do projeto em 2026-09-16

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
2. **`results/` está ATUAL** — bateria completa de 2026-09-16, sob o motor e o fitness
   de hoje. É a primeira vez desde 2026-09-10 que os artefatos podem ser citados. Mas
   veja o item 4: eles congelam por omissão sete constantes ainda provisórias.
3. **O passo 8 (item F) fechou** — a família de Holm do `compare_algorithms` foi
   corrigida e o tool re-rodado sobre os artefatos existentes. Não regenerou nada: o
   `comparison_ga_vs_nsga2.json` é o único arquivo que mudou. Detalhe em §1b.
4. **O próximo passo não é um item da ordem — é a agenda de calibração
   ([`REVIEW.md` §9](REVIEW.md)):** sete constantes ainda rotuladas "provisório", agora
   com a evidência que a bateria produziu. Todas mudam número, então fechar qualquer uma
   obriga a regenerar `results/` de novo. Resumo em §3.

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
| **Tempo** | cooldown, stun, persistência da intenção | ✅ coerente após M3. Ressalva: a persistência (10 sub-ticks) é **maior que o cooldown mínimo** (5), então quem tem `cooldown=1` e sorteia GUARDA abre mão de duas janelas de ataque |
| **Recurso** | hp, damage, DEFEND, grab_power | ✅ coerente após (R) — o agarrão é o counter da guarda |
| **Política** | 3 pesos, amostragem proporcional | contínua, mas **cega ao estado** (não olha HP, distância nem se o oponente está stunado) e com degenerescência de escala (só a razão importa) |

## 3. Resultados da bateria e o que decidir agora

A bateria completa rodou em 2026-09-16: AG e NSGA-II na seed 42, `multi_run` com 10
sementes × 2 algoritmos, `compare_algorithms`, `external_validation` e `baselines` com
30 rosters nulos. `results/` está atual.

**Agregado (10 sementes, reavaliação independente):**

| | dominance | drift | global | cap | decis | counters/exec | roster eq. |
|---|---|---|---|---|---|---|---|
| AG escalar | 0,0666 ± 0,0265 | 0,2535 ± 0,0354 | 0,0537 | 0,0259 | **0,0000** | 0,90 ± 0,7 | 30% |
| NSGA-II | 0,0567 ± 0,0255 | 0,2038 ± 0,0486 | 0,0461 | 0,0201 | **0,0000** | 1,30 ± 1,6 | 50% |

Os 5 bonecos ficam em banda em **100% das sementes** nos dois algoritmos.

**Contra os modelos nulos** (melhor do AG, 30 nulos): a identidade fica acima de **todos**
os rosters sem estrutura nos três eixos — validador 13/23 (`p < 0,03`), 11/18
(`p < 0,03`), drift 0,254 (`p < 0,03`); equilíbrio em **94%** do trivialmente alcançável;
ciclo em 5/10, exatamente o acaso (`p = 0,71`). Tríades circulares **4,0** com pares em
27%–62% — arestas decididas, contagem válida.

### O que decidir: a agenda de calibração (`REVIEW.md` §9)

Sete constantes seguem rotuladas "provisório", e a bateria congelou os valores de hoje
por omissão. O levantamento completo, com a evidência de cada uma, está em
[`REVIEW.md` §9](REVIEW.md). Em uma linha cada:

1. ✅ **`DOMINANCE_DECIS_WEIGHT`** — **fechado, mantido em 0,5.** A premissa ("o termo
   está morto") era erro de amostra: 0,0000 é medido só nos indivíduos **finais**. Ver §1c.
2. ✅ **`MATCHUP_WR_CAP = 0.15`** — **fechado, mantido.** Âncora: ponto médio entre 6-4
   (vantagem) e 7-3 (counter) na grade da FGC. Ver §1c.
3. **`SIMS_PER_MATCHUP = 150`** — o ajuste ao stream é de **21×** (0,0039 dentro do laço
   contra 0,0804 fora), e `Zoner × Turtle` sai em 28,2% ± 1,9% fora do laço: um counter
   sistemático que 150 sims não enxergaram. Veredito externo: **FRÁGIL**. **Aberto.**
4. ✅ **Canônicos** — **fechado: declarados finais.** Critério de aceitação escrito
   (coerentes 23/23 · distintos ≥ 0,32 · desequilibrados = o ponto de partida), e o que
   NÃO se exige, com a razão. Duas limitações declaradas — ver §1d.
5. **`ACTION_PERSISTENCE_SUBTICKS = 10`** — maior que o cooldown mínimo (5); a
   sensibilidade no evoluído põe `speed` e `stun` **abaixo** do piso medido. **Aberto** —
   exige uma rodada de sensibilidade para decidir.
6. 📏 **Escala dos pesos comportamentais** — **medido: 7,5%** do drift médio é cobrado por
   diferença behaviouralmente nula (não os "55%" antes registrados — aquela conta estava
   confundida por escala). Pior caso Rushdown 15,1%. Conserto exige regenerar → **bundle
   com (3)**. Ver §1d.
7. 📏 **`MULTI_RUN_N_SEEDS = 10`** — com o (F) fechado, o único achado da bateria (NSGA-II
   com drift menor, Â₁₂ = 0,80, p bruto **0,026**) melhorou para p_Holm **0,0772** e
   **ainda não é significativo**. Mesmo a família mínima para em 0,0515. O gargalo é
   poder amostral, e subir sementes é **aditivo**: as 10 atuais continuam valendo.

O passo 8 (item **F**) está **fechado** — ver §1b. Não regenerou nada: só o
`comparison_ga_vs_nsga2.json` mudou. Os itens **(1), (2) e (4)** da agenda fecharam sem
mudar número, então `results/` segue válido (§1c, §1d). Os itens **(3), (5), (6) e (7)**
seguem abertos e **os três primeiros mudam número** — devem ser executados numa
regeneração só.

## 4. Itens menores ainda abertos

- **(C)** assimetria dos critérios de parada entre os dois algoritmos (acima).
- **(H)** resolução do p-valor empírico nos baselines (acima).
- **§5** degenerescência de escala nos pesos comportamentais: a intenção é sorteada
  proporcionalmente a `(w_agg, w_ret, w_def)`, então só a **razão** importa para o
  combate — mas o drift mede os valores absolutos. Parte do eixo de identidade mede algo
  que o simulador não enxerga.
- **§2** a persistência da intenção (10 sub-ticks) é maior que o cooldown mínimo (5), então
  quem tem `cooldown = 1` e sorteia GUARDA abre mão de duas janelas de ataque.
- **§5** a política é **cega ao estado**: não olha HP, distância nem se o oponente está
  stunado.

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
