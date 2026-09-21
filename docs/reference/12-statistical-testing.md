# Teste estatístico da comparação AG × NSGA-II

Doc **didático** do aparato estatístico usado em `src/experiments/compare_algorithms.py`:
Mann-Whitney U, Â₁₂ de Vargha-Delaney e a **correção de Holm-Bonferroni**. O foco é o
Holm — é a peça menos óbvia e a que mais decide o que pode ser afirmado na tese.

Os outros docs descrevem *o que o sistema faz*. Este explica *por que a comparação é
feita assim*, do zero. Para a descrição operacional do tool, ver
[08-tools.md](08-tools.md); para o lugar disso na metodologia da tese, ver
[`../thesis/05-methodological-validation.md`](../thesis/05-methodological-validation.md).

---

## 1. O problema que o teste resolve

O `multi_run` roda cada algoritmo em N sementes (20 na bateria) e devolve média ± desvio.
Suponha que saia isto:

```
AG escalar   drift_penalty  0,2535 ± 0,0354
NSGA-II      drift_penalty  0,2038 ± 0,0486
```

O NSGA-II tem média menor. **Isso não é um resultado.** Cada execução do AG é
estocástica — muda a semente, mudam os números. Duas perguntas diferentes se escondem
aí:

1. **A diferença existe**, ou as duas amostras são o mesmo fenômeno visto com ruído?
   → responde o **teste de hipótese** (Mann-Whitney U), que devolve um `p`.
2. **A diferença é grande o bastante para importar?**
   → responde o **tamanho de efeito** (Â₁₂), e essa pergunta é independente da primeira.

Um `p` pequeno com efeito minúsculo é uma diferença real e irrelevante. Um efeito
grande com `p` grande é um indício forte que a amostra não sustenta. As duas medidas
são reportadas sempre juntas, e é por isso que a tabela do tool tem as duas colunas.

### Mann-Whitney U, em uma frase

Teste **não-paramétrico** para duas amostras independentes: junta os 40 valores (20 de
cada algoritmo), ordena, e pergunta se os do AG tendem a ficar sistematicamente acima
ou abaixo dos do NSGA-II. Não assume normalidade — o que importa aqui, porque as
métricas são limitadas por baixo em 0 e as inteiras (hard-counters) empatam muito.

### Â₁₂ de Vargha-Delaney, em uma frase

`Â₁₂ = P(uma execução do AG dar valor maior que uma do NSGA-II)`, com empates valendo
meio. **0,5 = nenhum efeito.** Os limiares em `|Â₁₂ − 0,5|` são de Vargha & Delaney
(2000) e estão em `_effect_magnitude`: `< 0,06` desprezível · `< 0,14` pequeno ·
`< 0,21` médio · resto grande.

É uma medida bonita porque se lê direto: Â₁₂ = 0,80 quer dizer *"pegue uma execução de
cada ao acaso — em 80% das vezes o AG dá o valor maior"*. Sem unidade, sem depender da
escala da métrica.

---

## 2. Por que corrigir: o efeito de olhar em muitos lugares

Aqui começa o Holm.

Um teste a α = 0,05 aceita **5% de chance de falso positivo** — de gritar "diferença!"
quando não há nenhuma. Esse é o preço combinado de antemão, e é aceitável.

Agora rode **quatro** testes. Se não houver diferença nenhuma em lugar nenhum, qual a
chance de pelo menos um sair "significativo" por puro acaso?

| testes (k) | chance de ao menos um falso positivo |
|---|---|
| 1 | 5,0% |
| 2 | 9,8% |
| 3 | 14,3% |
| **4** | **18,5%** |
| 10 | 40,1% |
| 20 | 64,2% |

(São `1 − 0,95^k`, sob independência. As métricas do projeto **não** são independentes —
saem das mesmas execuções — então esses números são ilustrativos, não exatos para o
nosso caso. Voltaremos a isso em §8.)

Com 4 métricas, quase 1 em 5 baterias produz um "achado" que é ruído. E o problema fica
pior porque a tentação é reportar o que deu significativo e omitir o resto — aí a taxa
real de erro deixa de ser 5% e ninguém consegue saber qual é.

O nome disso é **taxa de erro por família** (*family-wise error rate*, FWER): a
probabilidade de ao menos um falso positivo no **conjunto** de testes. Uma correção de
múltiplas comparações é um procedimento que segura a FWER em α, não importa quantos
testes você rode.

---

## 3. Bonferroni: a versão crua

A ideia mais simples possível: se você vai rodar `k` testes e quer que o conjunto todo
erre no máximo 5% das vezes, exija de cada teste individual `α/k`.

Equivalente e mais prático: **multiplique cada `p` por `k`** e continue comparando com
α. Um `p` de 0,02 em 3 testes vira 0,06 — não passa mais.

Funciona, é trivial de provar, e vale sob **qualquer** dependência entre os testes.
O defeito é ser **conservador**: perde poder: diferenças reais deixam de ser detectadas.
Especialmente quando `k` cresce.

---

## 4. Holm: a versão sequencial

Holm (1979) dá a **mesma garantia** de FWER que Bonferroni, mas exige menos. A sacada é
não cobrar o mesmo preço de todo mundo: só o **menor** `p` precisa vencer a barra cheia.

### O procedimento

1. Ordene os `p` do **menor para o maior**.
2. Multiplique o menor por `k`, o segundo por `k−1`, o terceiro por `k−2`… — ou seja,
   cada um pelo **número de testes que ainda restam**, ele incluído.
3. **Force a monotonicidade**: nenhum ajustado pode ficar abaixo de um ajustado
   anterior. (Se o segundo saiu menor que o primeiro, ele sobe para o valor do primeiro.)
4. Corte o que passar de 1,0.

A intuição do passo 2: quando você já examinou o menor `p` e ele não passou, o
procedimento para — não há mais o que rejeitar. Se ele passou, sobrou um problema com
`k−1` testes, e é **esse** o multiplicador do próximo. O preço vai barateando conforme
os testes vão sendo resolvidos.

O passo 3 existe porque sem ele o procedimento poderia rejeitar uma hipótese com `p`
maior e não rejeitar uma com `p` menor — incoerente.

> **Holm nunca é pior que Bonferroni.** Para o menor `p` os dois cobram exatamente o
> mesmo (`×k`); dali para cima Holm cobra menos. É o que se chama de *uniformemente
> mais poderoso*, e é por isso que não existe razão para usar Bonferroni puro.

### Exemplo trabalhado — os números reais da bateria de 2026-09-16

Família de 3, p brutos vindos do Mann-Whitney:

| rank | métrica | `p` bruto | multiplicador | `p × mult` | ajustado (após monotonicidade) |
|---|---|---|---|---|---|
| 0 | `drift_penalty` | 0,0257 | ×3 | 0,0772 | **0,0772** |
| 1 | `dominance_penalty` | 0,3075 | ×2 | 0,6150 | **0,6150** |
| 2 | `n_hard_counters` | 0,9683 | ×1 | 0,9683 | **0,9683** |

Compare com Bonferroni na mesma família (tudo ×3): 0,0772 · 0,9225 · 1,0000. Idêntico
no primeiro, mais frouxo nos outros dois — exatamente a propriedade descrita acima.

Neste caso a monotonicidade não precisou agir (os valores já saíram crescentes), mas o
código a aplica sempre via `running_max`.

---

## 5. A família — a decisão que ninguém vê

Repare que o multiplicador é `k` = **tamanho da família**. E a família é uma
**escolha**: o conjunto de testes sobre o qual você decidiu controlar o erro conjunto.

Isso tem uma consequência desconfortável: **cada métrica que entra encarece todas as
outras.** O mesmo `p` bruto de `drift_penalty` (0,0257) sai assim:

| tamanho da família | `p` ajustado |
|---|---|
| 2 | 0,0515 |
| **3 — a da bateria de 2026-09-16** | **0,0772** |
| 4 | 0,1030 |
| 5 | 0,1287 |

Daí vem o risco metodológico: se você escolher a família **depois** de olhar os
p-valores, está fabricando o resultado. Cortar métricas até o seu achado passar de α
é uma forma clássica de *p-hacking*, e é indefensável mesmo quando cada corte
individual parece razoável.

**A regra do projeto**, para não cair nisso: a família é **fixa e declarada antes da
bateria** — `METRICS`, 7 métricas: equilíbrio (`dominance_penalty`, hard-counters, bonecos
em banda) e identidade (`drift_penalty`, validador estrutural, validador comportamental,
concordância de ranking), as duas metades da pergunta de pesquisa — e é a **mesma em toda
comparação** (AG × NSGA-II e AG × cada controle). A única exclusão é por um **critério
objetivo, decidido pelos dados e declarável antes do teste** — `_is_degenerate`. Nenhum
julgamento entra depois de ver os p-valores.

Até a bateria de 2026-09-18 a família eram as 4 primeiras (3 depois da exclusão); as
métricas de identidade entraram quando a comparação passou a responder também "o método
preserva identidade?" — antes da bateria que as mede. Na bateria de 2026-09-21 a família
é de **6** nas quatro comparações (`n_chars_balanced` sai por degenerescência), e o
multiplicador só muda um veredito em quatro comparações: em AG × NSGA-II os seis p brutos
vão de 0,0037 a 6,8 × 10⁻⁸ e os seis sobrevivem a Holm; no controle `λ_drift = 0` o único
que a correção derruba é `dominance_penalty` (p bruto 0,032 → p_Holm 0,063), e derrubar
esse é exatamente o ponto — o braço sem drift **não** compra equilíbrio; no controle sem
semente, o drift passa (0,0071 → 0,043) e o resto não chega perto nem sem correção.

---

## 6. O caso degenerado: quando não existe teste

A métrica `n_chars_balanced` (quantos dos 5 personagens ficam em banda) deu **5 em
todas as execuções** de todos os braços — 20 de 20 na bateria de 2026-09-16 e, na de
2026-09-21, 80 de 80 somando AG, NSGA-II e os dois controles.

Mann-Whitney devolve `p = nan`. Não é bug: o teste compara postos, e com todos os
valores empatados a correção de empates zera o denominador da variância. Não há
variação para atribuir a lugar nenhum. **Não é um teste que deu "sem diferença" — é a
ausência de um teste.**

Só que esse não-teste estava entrando na família assim mesmo, e o multiplicador virava
**4 em vez de 3**. Uma métrica sem informação nenhuma cobrando pedágio das outras.

### O critério é da amostra **conjunta**

Detalhe fácil de errar: a degenerescência é das 2·n execuções juntas, **não** de cada
amostra separada.

| AG | NSGA-II | degenerada? | por quê |
|---|---|---|---|
| `[5,5,…,5]` | `[5,5,…,5]` | **sim** | nada varia em lugar nenhum |
| `[5,5,…,5]` | `[3,3,…,3]` | **não** | cada uma é constante, mas a separação entre elas é **perfeita** — a diferença mais forte que existe |

Por isso `_is_degenerate` testa `len(set(sample_a + sample_b)) == 1`.

### E o `nan` tinha um segundo defeito, silencioso

`_holm` ordena os p-valores. Toda comparação com `nan` é **falsa** — `nan < x`,
`nan > x` e `nan == x` são todas `False` — então a posição dele no vetor ordenado
passava a depender de detalhes do algoritmo de ordenação. Saía certo por sorte.

Hoje `_holm` **levanta `ValueError`** ao ver um `nan`, em vez de ordenar por acaso. O
filtro a montante garante que nunca dispare; a exceção existe para que o contrato seja
verificado e não apenas esperado.

A métrica excluída **continua sendo reportada**, como descritiva, com a nota do porquê —
e é um resultado forte por si só: os dois algoritmos e os dois controles põem os 5
personagens em banda em 100% das execuções, inclusive o braço sem termo de identidade.
Equilibrar os cinco globalmente deixou de discriminar qualquer coisa neste sistema; o que
discrimina são os pares. Só não é um resultado **comparativo**.

---

## 7. Como ler o resultado

A leitura da bateria de 2026-09-21 — n = 20 sementes, família de 6, NSGA-II representado
pelo `scalar_optimum` (a manchete):

```
dominance_penalty            p_Holm 3,6e-05   Â₁₂ 0,10 (grande)   AG escalar melhor
hard-counters                p_Holm 7,9e-07   Â₁₂ 0,03 (grande)   AG escalar melhor
drift_penalty                p_Holm 4,1e-07   Â₁₂ 1,00 (grande)   NSGA-II melhor
validador estrutural (L1+L2) p_Holm 4,1e-06   Â₁₂ 0,05 (grande)   NSGA-II melhor
validador comportamental (L3) p_Holm 0,0037   Â₁₂ 0,24 (grande)   NSGA-II melhor
concordância de ranking (τ)  p_Holm 2,6e-05   Â₁₂ 0,09 (grande)   NSGA-II melhor
```

Traduzindo: **as seis diferenças são significativas e grandes**, e se dividem exatamente
nas duas metades da pergunta — o AG ganha as duas métricas de equilíbrio, o NSGA-II as
quatro de identidade. Cada algoritmo ocupa um extremo do trade-off. O Â₁₂ lê-se como
probabilidade: sorteando uma execução de cada, a do AG tem drift maior em **100%** dos
casos (a separação é total: as duas amostras não se sobrepõem) e `dominance` maior em só
10%.

A leitura da bateria de 2026-09-16, sob o motor anterior, era outra — `drift_penalty` com
p_Holm 0,0772 e Â₁₂ 0,80: **efeito grande, direção consistente, não significativo a
n = 10**. É o caso que os erros de leitura abaixo descrevem.

Três erros de leitura a evitar:

- **"Não significativo" ≠ "não há diferença".** Significa que a amostra não permite
  descartar o acaso — não que o acaso seja a explicação. Com Â₁₂ = 0,80, o mais provável
  é que a diferença exista e falte poder para demonstrá-la.
- **"Significativo" ≠ "importante".** É por isso que o Â₁₂ está lá.
- **O `p` não é a probabilidade de a hipótese ser falsa.** É a probabilidade de observar
  uma diferença ao menos tão extrema *se não houvesse diferença nenhuma*. A confusão
  entre as duas é o erro mais comum com p-valores.

### O conserto da família não comprou significância — e isso é o ponto

Vale registrar porque é o que torna a correção defensável: nem a família mínima
concebível (2 métricas, só os dois objetivos do Pareto) leva o `drift` abaixo de α —
para em **0,0515**, acima por 0,0015. Não havia prêmio em escolher a família menor.

O gargalo era **poder amostral**, e o remédio foi subir o número de sementes para 20
(simulação de poder: 44,4% a n = 10 contra 85,9% a n = 20 — ver
[`../thesis/04-design-decisions.md`](../thesis/04-design-decisions.md)). Foi aditivo, como previsto — as sementes 42–51 reproduziram
bit a bit na bateria de n = 20.

### O que o n = 20 mostrou sobre o tamanho do efeito

Entre n = 10 e n = 20 (mesmo motor, bateria de 2026-09-17 contra a de 2026-09-18) os p
caíram, como se espera, e os três Â₁₂ **andaram na direção de 0,5**: 0,20 → 0,27 ·
0,94 → 0,89 · 0,14 → 0,21. É o padrão típico de amostra pequena: entre as amostras que
passam do limiar de significância, sobram mais as que sortearam um efeito maior que o
real. O efeito continua grande nos três, e o de n = 20 é a estimativa a citar.

A lição é sobre **tamanho de amostra**, não sobre estes números: as estimativas vigentes
são as da bateria de 2026-09-21 (§7), medidas sobre o motor corrigido e com a família de
6. Nela os Â₁₂ são ainda mais extremos (0,03 a 1,00), o que não contradiz o parágrafo
acima — a n = 20 fixo, um efeito maior é efeito maior, não inflação amostral.

---

## 8. O que Holm **não** faz

- **Não aumenta poder.** Só evita gastar o erro que você não tem. Corrigir sempre torna
  mais difícil achar algo — é o preço de poder confiar no que for achado.
- **Não conserta amostra pequena.** Ver §7.
- **Não exige independência entre os testes** — ao contrário do que a tabela de §2
  sugere. Holm e Bonferroni controlam a FWER sob **dependência arbitrária**, o que é
  bom para nós: as métricas saem das mesmas execuções e são correlacionadas. (Métodos
  mais poderosos, como Hochberg ou Hommel, exigem suposições de dependência que o
  projeto não tem como sustentar — por isso Holm.)
- **Não controla o que você não reportou.** Se você rodou 10 análises e reportou 3, a
  família honesta é 10. A correção só vale se a família for a verdade.
- **Não substitui o tamanho de efeito.** Ver §7.

---

## 9. Onde está no código

| peça | símbolo |
|---|---|
| α da bateria | `ALPHA` em `src/experiments/compare_algorithms.py` |
| a família | `METRICS` (idem) |
| critério de exclusão | `_is_degenerate` (idem) |
| procedimento de Holm | `_holm` (idem) |
| limiares do Â₁₂ | `_effect_magnitude` (idem) |
| Mann-Whitney | `scipy.stats.mannwhitneyu`, em `compare(a, b, label_a, label_b)` |
| o que torna dois artefatos comparáveis | `_PAIRED_FIELDS`: sementes, semente de validação, sims/matchup e orçamento |
| relação de Pareto por semente (descritiva) | `pareto_relation` |

`compare` é genérico: compara quaisquer dois artefatos do `multi_run` que passem no
pareamento — AG × NSGA-II ou AG × um controle. Os artefatos gravam `family_size` e
`excluded_from_family`, então dá para auditar a família de qualquer bateria sem re-rodar
nada.

Contrato coberto em `src/tests/test_compare_algorithms.py`: o critério ser da amostra
conjunta, o `nan` recusado em vez de ordenado por sorte, o custo de cada métrica na
família, o fato de que filtrar não fabrica significância, e as três relações de Pareto.

---

## 10. Para estudar

Ordem sugerida — do que explica o procedimento para o que justifica usá-lo aqui.

| referência | o que tem |
|---|---|
| **Holm, S. (1979).** *A simple sequentially rejective multiple test procedure.* Scandinavian Journal of Statistics 6(2), 65–70. | O artigo original. Curto, e a demonstração de que a FWER fica em α é seguível. |
| **Dunn, O. J. (1961).** *Multiple Comparisons Among Means.* JASA 56(293), 56–64. | A referência canônica do Bonferroni em comparações múltiplas. |
| **Derrac, J. et al. (2011).** *A practical tutorial on the use of nonparametric statistical tests…* Swarm and Evolutionary Computation 1(1), 3–18. | **O mais útil para o TCC.** Tutorial de testes não-paramétricos aplicado exatamente ao caso de comparar algoritmos evolutivos. |
| **Arcuri, A. & Briand, L. (2011).** *A practical guide for using statistical tests to assess randomized algorithms…* ICSE 2011. | Por que algoritmo estocástico exige múltiplas execuções + teste, e quantas execuções. |
| **Vargha, A. & Delaney, H. D. (2000).** *A Critique and Improvement of the CL Common Language Effect Size Statistics…* JEBS 25(2), 101–132. | De onde vem o Â₁₂ e os limiares de magnitude. |
| **Mann, H. B. & Whitney, D. R. (1947).** Annals of Mathematical Statistics 18(1), 50–60. | O teste original. |

> Holm, Derrac, Arcuri & Briand, Vargha & Delaney e Mann & Whitney estão nos três `.bib`
> do projeto (`overleaf/TCC/bibliografia.bib` e os dois `referencias.bib`); Dunn não está.
> Verificar cada entrada na fonte antes de citar.
