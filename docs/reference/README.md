# Referência técnica

Referência do sistema, separada por tema e **atualizada conforme o código atual**
(`src/engine`). Para instruções de trabalho com o repositório, ver `CLAUDE.md` (raiz);
para instalação e execução rápida, ver o `README.md` da raiz. Material de redação da
tese fica em [`../thesis/`](../thesis/README.md).

## Mapa

| Doc | Conteúdo |
|---|---|
| [01-overview.md](01-overview.md) | Pergunta de pesquisa, diferencial acadêmico, as duas camadas, escopo |
| [02-architecture.md](02-architecture.md) | Layout do código, convenções, modelo de dados, orquestração |
| [03-archetypes.md](03-archetypes.md) | Os 5 arquétipos, valores canônicos, pesos, ciclo de vantagens |
| [04-combat-model.md](04-combat-model.md) | Simulação tick a tick: os dois canais (postura e ataque), intenção, colisão, stun/knockback/agarrão, vitória |
| [05-genetic-algorithm.md](05-genetic-algorithm.md) | AG escalar: indivíduo, fitness (drift e dominance C2), operadores, convergência, stream por geração |
| [06-nsga2.md](06-nsga2.md) | NSGA-II multi-objetivo: dominância, crowding, representantes |
| [07-configuration.md](07-configuration.md) | Tabela completa de hiperparâmetros (`config.py`) |
| [08-tools.md](08-tools.md) | Ferramentas de análise, validação, estatística e visualização |
| [09-reproducibility.md](09-reproducibility.md) | Execução, saídas, carimbo de proveniência e reprodutibilidade (CRN por luta) |
| [10-known-issues.md](10-known-issues.md) | Pontos em aberto: a pendência de regerar resultados, os limites estruturais do método, o estado dos artefatos |
| [11-combat-review.md](11-combat-review.md) | Auditoria do modelo de combate (2026-09-10): os defeitos, as correções e o veredito |
| [12-statistical-testing.md](12-statistical-testing.md) | Didático: Mann-Whitney, Â₁₂ e a correção de Holm-Bonferroni |

## Convenção

- Descrevem o **estado atual** do código. Quando uma decisão de design mudar, o doc
  do tema correspondente deve ser atualizado.
- Decisões em aberto ou com peso metodológico ficam em
  [10-known-issues.md](10-known-issues.md), não diluídas nos docs descritivos.
