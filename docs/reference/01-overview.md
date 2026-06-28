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
foram preservados após a evolução. A preservação **não é forçada**: o AG evolui
livremente e medimos o quanto cada personagem derivou do seu perfil inicial.

Equilíbrio com preservação e equilíbrio com homogeneização são **ambos
resultados cientificamente válidos** — comparar os dois cenários é o experimento
central.

## Decisão metodológica crítica — não forçar identidade no fitness

- Os valores canônicos dos arquétipos servem como **semente da população
  inicial** e como **baseline de medição de drift**, nunca como restrição rígida.
- O drift é penalizado via `LAMBDA_DRIFT` (AG escalar) ou exposto como objetivo
  de Pareto (NSGA-II), mas o AG diverge livremente.
- O **ciclo canônico de vantagens** (quem vence quem) **não é codificado em
  nenhuma penalidade** — é reportado *post-hoc* como métrica de avaliação.
- Por quê: codificar o ciclo no fitness tornaria a pergunta de pesquisa
  **circular** ("o AG preserva identidade quando eu pago para preservar").

Ver [10-known-issues.md](10-known-issues.md) para o status epistemológico do
ciclo (construção do autor, operacionalização entre várias defensáveis) e os
pontos em aberto.

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
(pergunta, escopo, limitações), em [tcc/](../tcc/README.md).
