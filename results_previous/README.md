# Baterias anteriores

Artefatos de baterias **superadas**, guardados porque a documentação afirma coisas sobre
elas. Não são citáveis: o que se cita é sempre `results/`, a bateria vigente.

> **Por que isto está versionado.** O projeto inteiro é construído sobre a ideia de que
> todo número é rastreável até o artefato que o produziu (`src/engine/provenance.py`). Os
> docs carregam ~85 afirmações da forma *"a 200 lutas esta linha dava X; a 1000 dá Y"* —
> e a metade **X** de cada uma só existe aqui. Apagar estes artefatos transformaria todas
> elas em asserções que ninguém pode conferir, o que é exatamente o que o carimbo de
> proveniência existe para impedir.

## `2026-09-21/`

A bateria de 16 passos, com `MULTI_RUN_SIMS = 200`. Superada pela de 2026-09-23 (19
passos, `MULTI_RUN_SIMS = 1000`, mais o braço híbrido).

**Os indivíduos das duas são os mesmos.** Comparados gene a gene, 40 de 40 execuções com
semente saíram bit a bit idênticas — os cinco consertos de motor aplicados entre as duas
eram inertes, como o `10-known-issues` afirmava e esta comparação mediu. Logo, tudo que
difere entre `2026-09-21/` e `results/` é efeito **só** da resolução da reavaliação.

É por isso que estes artefatos são úteis: eles isolam uma variável. Reproduzir a
verificação:

```bash
py -c "
import json
for algo, rep in [('ga', None), ('nsga2', 'scalar_optimum')]:
    a = json.load(open(f'results/multi_run/multi_run_{algo}.json', encoding='utf-8'))
    b = json.load(open(f'results_previous/2026-09-21/multi_run/multi_run_{algo}.json', encoding='utf-8'))
    genes = lambda r: r['representatives'][rep]['genes'] if rep else r['genes']
    iguais = sum(genes(x) == genes(y) for x, y in zip(a['per_seed'], b['per_seed']))
    print(f'{algo}: {iguais}/20 idênticos')
"
```

**O que mudou, e é o que os docs citam:** a identidade não se moveu (drift, validador e τ
saem dos genes e de `IDENTITY_BEHAVIORAL_SIMS`, intocado); o `dominance` mediano do AG
caiu de 0,0399 para 0,0355, os rosters equilibrados subiram de 14/20 para 16/20, e o
controle `λ_drift = 0` deixou de separar em equilíbrio (p_Holm 0,038 → 0,059). Leitura
completa em [`../docs/thesis/04-design-decisions.md`](../docs/thesis/04-design-decisions.md),
«A política de adiar conserto inerte foi verificada» e «`MULTI_RUN_SIMS` saiu de
`SIMS_CONVERGENCE_CHECK`».

**Carimbo.** Estes artefatos se declaram **obsoletos** contra a configuração vigente, e
devem mesmo — `MULTI_RUN_SIMS` e o `engine_digest` mudaram. `src.tests.test_provenance`
não os varre: ele olha só `results/`.

Os logs de execução foram descartados (são acompanhamento de uma noite, não artefato —
mesma razão de `results/logs/` ser gitignored).
