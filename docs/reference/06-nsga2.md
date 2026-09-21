# 06 — NSGA-II (multi-objetivo)

Variante multi-objetivo do AG (Deb et al., 2002), em `src/engine/nsga2.py`.
Ativada com `py main.py --algorithm nsga2`. Compartilha simulação, fitness por
componente e operadores com o AG escalar.

## Objetivos

Otimiza **2 objetivos** simultaneamente, ambos minimizados, sem ponderação:

| Objetivo | Significado |
|---|---|
| `dominance_penalty` | desbalanço: balanço global por personagem (primário) + teto de hard-counter + decisividade, RMS — ver [05](05-genetic-algorithm.md) |
| `drift_penalty` | identidade estrutural: RMS ponderada dos desvios ao canônico, normalizados pelo range do bound — ver [05](05-genetic-algorithm.md) |

`evaluate_objectives` retorna `(dominance_penalty, drift_penalty)` em escala
bruta — os `LAMBDA_*` do fitness escalar são ignorados. O NSGA-II torna
**explícito** o trade-off que o AG escalar colapsa num peso fixo: exatamente a
tensão central do TCC entre equilíbrio e preservação de identidade.

## Algoritmo

Implementação padrão de Deb 2002:

1. **Dominância de Pareto** (`_dominates`): `a` domina `b` se não é pior em nenhum
   objetivo e é estritamente melhor em ao menos um.
2. **Fast non-dominated sort** (`fast_non_dominated_sort`): particiona a população
   em fronteiras por rank, trabalhando com índices (não `.index()` — clones do
   canônico têm conteúdo igual e quebrariam `.index()` silenciosamente).
3. **Crowding distance** (`crowding_distance_assignment`): densidade local por
   objetivo, normalizada pelo span; extremos recebem `inf` para serem sempre
   preservados.
4. **Seleção** (`nsga2_binary_tournament`): menor rank vence; empate decide por
   maior crowding.
5. **Geração (μ+λ)**: combina pais + filhos, re-ranqueia e seleciona os melhores
   `pop_size` por (rank, crowding). Essa combinação **é** o elitismo do NSGA-II.

Roda `NSGA2_GENERATIONS = 150` gerações fixas (fronteiras de Pareto não
"convergem" para um ponto — não há critério de parada antecipada).

### O stream de avaliação roda por geração — e aqui custa o dobro

O NSGA-II usa `fitness.generation_seed(seed, g)`, a **mesma** função do AG escalar:
protocolo de avaliação idêntico nos dois, senão a comparação entre eles confundiria
"algoritmo" com "forma de avaliar" (mecanismo em [09](09-reproducibility.md), números em
[thesis/04](../thesis/04-design-decisions.md)).

A diferença é o **custo**. No AG escalar só os elites chegam medidos no stream
anterior. Aqui, o passo (5) combina pais + filhos e re-ranqueia o conjunto inteiro —
e **objetivos medidos em streams diferentes não são comparáveis por dominância**: um
pai pareceria dominar um filho só por ter enfrentado sorteios mais favoráveis. Por
isso os pais são reavaliados junto no stream novo, **2×pop por geração em vez de
pop**, contra ~1,8× no escalar.

> Essa reavaliação **não é redundante**. Removê-la parece uma otimização óbvia (os
> pais "já foram avaliados") e quebraria a validade da fronteira em silêncio — o
> rank sairia de uma comparação entre medições incomparáveis. Está comentada no
> código pelo mesmo motivo.

### População inicial: aleatória, sem o seed canônico

Aqui o NSGA-II **diverge do AG escalar de propósito**. O escalar inicia com
`[canônico] + 299 aleatórios`; o NSGA-II inicia com `pop_size` aleatórios.

O motivo é uma assimetria entre os dois objetivos: **`drift` tem piso 0 e o piso é
alcançável** (o canônico *é* a referência, drift exatamente 0,0000), enquanto o piso de
`dominance` não é. Dominar `(dominance 1,2418, drift 0,0000)` exigiria `drift < 0`, que
não existe — então o canônico é **imortal no rank 0**, por pior que seja o equilíbrio
dele, e a mesma proteção se estende à vizinhança de drift ~0. O crowding não corrige:
ele só poda quando um front **transborda** a população. Com o seed, metade da fronteira
era de rosters tão desequilibrados quanto o canônico intocado.

No **AG escalar o mesmo seed ajuda** e por isso fica: lá o fitness é um número só, o
canônico é ruim nele e some da população depois de doar genes por crossover. As medições
das duas metades estão em [thesis/04](../thesis/04-design-decisions.md) ("A população
inicial do NSGA-II").

> **Ressalva.** Isto remove a causa aguda (drift = 0 de graça na geração 0), não a
> assimetria estrutural: o NSGA-II seleciona por drift baixo, então a população marcha
> para lá sozinha e o acúmulo pode reaparecer em horizontes longos. Se reaparecer, a
> lista de remédios em ordem de intervenção é: supressão de duplicatas → ε-dominância
> (Laumanns et al. 2002, um ponto por célula da grade de objetivos) → NSGA-II com
> restrições (Deb 2002 §VI, `dominance` acima de um limiar como inviável).

## Representantes da fronteira

`select_representatives` extrai 5 pontos da Pareto front final:

- **`best_dominance`** — mínimo em `dominance_penalty` (mais equilibrado, pode ter
  drift alto).
- **`best_drift`** — mínimo em `drift_penalty` (mais fiel ao canônico, pode ser
  desbalanceado).
- **`knee_point`** — ponto de máxima curvatura: mais distante (perpendicular) da
  reta que liga os dois extremos. O "melhor compromisso".
- **`ideal_point`** — mais próximo do **ponto utópico** da fronteira (o melhor valor de
  cada objetivo), em distância euclidiana.

O joelho e o ideal são geométricos, e por isso usam os objetivos **normalizados pela
amplitude da própria fronteira** (0 = o melhor valor dela naquele objetivo, 1 = o pior).
Em unidades cruas a escala de cada objetivo decidiria a geometria — `dominance` vai até
2,0 e drift fica em décimos. Normalizar mudou o `ideal_point` em 19 das 20 fronteiras da
bateria em que a mudança foi medida, e o `knee_point` em nenhuma; `test_nsga2` cobre a
invariância à unidade.
- **`scalar_optimum`** — mínimo de `LAMBDA_DOMINANCE·dominance + LAMBDA_DRIFT·drift`,
  isto é, o ponto da fronteira que **o AG escalar deveria ter encontrado**. É o único
  lugar do NSGA-II que olha os `LAMBDA_*`, e é reporting, não busca.

  Por que ele existe: a afirmação "o escalar é *um ponto* do trade-off que o NSGA-II
  mapeia" só é testável contra o ponto que minimiza a **mesma** função que o escalar
  otimiza. O `ideal_point` é geométrico e cego aos λ, então é outro ponto — com os
  LAMBDA iguais, `scalar_optimum` é o mínimo **L1** em unidades cruas. Medido no orçamento
  de produção, a afirmação não vale literalmente: o ponto do escalar fica **além** da
  ponta de baixa dominância da fronteira, e os dois são mutuamente não-dominados em
  **18 das 20 sementes** da bateria de 2026-09-21 (o AG domina um ponto da fronteira numa
  semente e é dominado em outra).

  No teste entre algoritmos (n = 20) o NSGA-II entra pelo **`scalar_optimum`**
  (`multi_run.HEADLINE_REPRESENTATIVE`) — o único ponto comparável ao escalar; decidido
  antes da bateria, pelo método. Como o `multi_run` grava os cinco representantes de cada
  semente, a comparação contra outro ponto sai de `compare_algorithms
  --nsga2-representative best_dominance`, sem re-rodar o NSGA-II. E a **relação de Pareto
  por semente** — o ponto do AG contra a fronteira inteira — não depende de representante
  nenhum ([08-tools.md](08-tools.md)).

## Métricas de qualidade da fronteira (item 1.2 da metodologia)

Comparar fronteiras "no olho" não escala (Deb 2001/2002). Em `src/engine/pareto_metrics.py`:

- **`hypervolume_2d(front, ref)`** — área da região dominada pela fronteira em
  relação ao ponto de referência `HYPERVOLUME_REFERENCE = (1.3, 0.4)`, ancorado nos
  modelos nulos: `dominance` ≈ a do canônico (o equilíbrio de partida) e drift ≈ o do
  espelho (identidade zero). Um ponto com equilíbrio pior que o de partida, ou identidade
  pior que a de cinco cópias, fica fora da área. Captura convergência *e* espalhamento
  num único número; **maior é melhor**. Decomposição em faixas verticais sobre a escada
  não-dominada: `Σ (x_{i+1} − x_i)·(r1 − y_i)`, com `x_{n+1} = r0`. Com a referência
  anterior, (2,0; 1,0) — os máximos teóricos —, o HV saturava em 90% da área e mal
  separava uma fronteira de outra (coeficiente de variação 2,0% entre sementes, contra
  2,9% com a atual: **0,3954 ± 0,0114** na bateria de 2026-09-21; spacing 0,0118 ± 0,0033).
- **`spacing(front)`** — desvio-padrão (Schott) da distância Manhattan de cada ponto
  ao vizinho mais próximo. Mede a **uniformidade** da distribuição; **menor é melhor**.

O ponto de referência é fixo para que o HV seja comparável entre execuções e
configurações. `main.py` imprime ambos ao fim do run; `nsga2_plots` os anota no plot;
`multi_run` os calcula por seed e reporta média ± desvio (ver [08-tools.md](08-tools.md)).

## Saída

`save_results` grava `results/single_run/nsga2.json` (fronteira completa, os 5
representantes com genes e objetivos, e histórico por geração). Plots em
`results/single_run/plots/<timestamp>/` via `nsga2_plots.save_plots` (ver
[08-tools.md](08-tools.md)) — anotados com hipervolume e spacing. Representantes
consumidos por tools via `Individual.from_nsga2(representative=...)`.
