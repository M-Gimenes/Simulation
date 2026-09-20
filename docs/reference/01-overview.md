# 01 — Visão geral

**Equilíbrio Competitivo e Preservação de Identidade Arquetípica em Jogos de
Luta: uma Abordagem por Algoritmos Genéticos Multi-objetivo**
Matheus Gimenes de Souza — Bacharelado em Sistemas de Informação — Ifes Campus
Cachoeiro de Itapemirim.

## Pergunta central

> É possível atingir equilíbrio competitivo entre personagens de arquétipos
> distintos usando Algoritmos Genéticos, **sem** que o processo destrua suas
> identidades funcionais?

## Diferencial acadêmico

Propor e validar uma forma de **medir quantitativamente** se os arquétipos
foram preservados após a evolução — e **o preço** dessa preservação: quanto
equilíbrio se compra por unidade de identidade perdida.

Equilíbrio com preservação e equilíbrio com homogeneização são **ambos
resultados cientificamente válidos** — comparar os dois cenários é o experimento
central.

## Decisão metodológica crítica — o fitness codifica a premissa, nunca a resposta

- **Premissa** é o que cada arquétipo **é**: os valores canônicos e os
  `defining_genes`. Ela **entra** no fitness, como penalidade de desvio
  (`drift_penalty`, via `LAMBDA_DRIFT` no AG escalar, objetivo de Pareto no NSGA-II).
- **Penalidade não é restrição**: o AG é livre para trocar identidade por equilíbrio,
  e troca — o termo existe e pode perder. Os canônicos também servem de semente da
  população inicial do AG escalar.
- **Resposta** é quem vence quem, e se equilíbrio e identidade são compatíveis. O
  **ciclo canônico de vantagens** **não é codificado em nenhuma penalidade** — é
  reportado *post-hoc*, descritivo, junto da identidade funcional (comportamento:
  Layer 3 do validador e concordância de ranking comportamental com o canônico).
- **Controles**: o AG com `LAMBDA_DRIFT = 0` mede quanto da identidade o termo de drift
  segura, e o AG sem a semente canônica separa algoritmo de inicialização na comparação
  com o NSGA-II.
- Por quê: codificar a resposta no fitness tornaria a pergunta de pesquisa
  **circular**.

O status epistemológico do ciclo (construção do autor, uma operacionalização entre
várias defensáveis) está em [thesis/02-canonical-cycle.md](../thesis/02-canonical-cycle.md).

## As duas camadas

O sistema tem duas camadas independentes que o AG orquestra:

1. **Simulação de combate** ([04-combat-model.md](04-combat-model.md)) —
   simulação tick a tick 1v1, determinística exceto por uma única fonte de
   estocasticidade (o sorteio de intenção ponderado pelos pesos). Vive inteiramente
   em funções JIT do Numba.
2. **Algoritmo genético** ([05-genetic-algorithm.md](05-genetic-algorithm.md) e
   [06-nsga2.md](06-nsga2.md)) — orquestra round-robin entre os 5 personagens,
   produz fitness escalar (AG clássico) ou fronteira de Pareto (NSGA-II).

A unidade de evolução é o **conjunto dos 5 personagens** (um por arquétipo), não
um personagem isolado — o winrate de qualquer personagem depende dos outros 4
simultaneamente.

## Escopo e limitações

- O modelo de combate é uma simplificação de FGCs reais: não modela frames de
  startup/recovery por golpe, mix-ups, neutral game, oclusão, etc.
- 5 arquétipos é suficiente para um ciclo; FGCs reais têm 10+.
- O round-robin assume todos os arquétipos jogados igualmente — não modela
  matchmaking onde jogadores escolhem matchups favoráveis.

Detalhes em [10-known-issues.md](10-known-issues.md) e, para a redação da tese
(pergunta, escopo, limitações), em [thesis/](../thesis/README.md).
