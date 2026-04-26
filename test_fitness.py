"""
Smoke test da função de fitness.
Rode com: python test_fitness.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from individual import Individual
from fitness import evaluate, evaluate_detail, evaluate_population
from archetypes import ARCHETYPE_ORDER, ARCHETYPES


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# ── 1. Indivíduo canônico ────────────────────────────────────────────────────

separator("Fitness do indivíduo canônico")
ind = Individual.from_canonical()
detail = evaluate_detail(ind)

for i, aid in enumerate(ARCHETYPE_ORDER):
    name = ARCHETYPES[aid].name
    print(f"  {name:15s}  winrate={detail.winrates[i]:.1%}")

print(f"\n  specialization_penalty = {detail.specialization_penalty:.4f}")
print(f"  dominance_penalty      = {detail.dominance_penalty:.4f}")
print(f"  fitness                = {detail.fitness:.4f}")
# Nova fórmula: fitness = -(LAMBDA_SPECIALIZATION*spec + LAMBDA_DRIFT*drift + LAMBDA_DOMINANCE*dom)
# Máxima penalidade com lambdas padrão (0.2 + 0.0 + 1.0): fitness >= -1.2
assert -2.0 < detail.fitness <= 0.0, f"Fitness fora do range: {detail.fitness}"
print("  ✓ Fitness dentro do range esperado")

# Matriz de matchup direto
n = len(ARCHETYPE_ORDER)
names = [ARCHETYPES[aid].name[:6] for aid in ARCHETYPE_ORDER]
col_w = 7
print(f"\n  {'':12s}" + "".join(f"{name:>{col_w}}" for name in names))
print(f"  {'':12s}" + "─" * (col_w * n))
for i, aid in enumerate(ARCHETYPE_ORDER):
    row = f"  {ARCHETYPES[aid].name:<12s}"
    for j in range(n):
        if i == j:
            row += f"{'—':>{col_w}}"
        else:
            key = (min(i, j), max(i, j))
            wr = detail.matchup_winrates.get(key, 0.0)
            if i > j:
                wr = 1.0 - wr
            row += f"{wr:>{col_w-1}.0%} "
    print(row)
print(f"\n  (células: WR da linha contra a coluna)")
assert len(detail.matchup_winrates) == 10, "Devem existir C(5,2)=10 matchups"
print("  ✓ matchup_winrates contém os 10 pares esperados")


# ── 2. Cache de fitness ──────────────────────────────────────────────────────

separator("Cache: não reavalia indivíduo já avaliado")
ind2 = Individual.from_canonical()
assert not ind2.is_evaluated
f1 = evaluate(ind2)
assert ind2.is_evaluated
f2 = evaluate(ind2)   # deve retornar cached sem recalcular
assert f1 == f2
print(f"  ✓ Cache funcionando (fitness={f1:.4f})")


# ── 3. Invalidação de fitness ────────────────────────────────────────────────

separator("Invalidação após mutação simulada")
ind2.invalidate_fitness()
assert not ind2.is_evaluated
print("  ✓ Fitness invalidado corretamente")


# ── 4. Indivíduo aleatório ───────────────────────────────────────────────────

separator("Fitness de indivíduo aleatório")
import random
random.seed(0)
rand_ind = Individual.random()
f = evaluate(rand_ind)
print(f"  fitness = {f:.4f}")
assert rand_ind.is_evaluated
print("  ✓ Indivíduo aleatório avaliado sem crash")


# ── 5. evaluate_population ──────────────────────────────────────────────────

if __name__ == '__main__':
    separator("evaluate_population (5 indivíduos)")
    pop = [Individual.random() for _ in range(5)]
    evaluate_population(pop)
    assert all(ind.is_evaluated for ind in pop)
    fitnesses = [ind.fitness for ind in pop]
    print(f"  Fitnesses: {[f'{f:.3f}' for f in fitnesses]}")
    print("  ✓ Todos os indivíduos avaliados")

    separator("Todos os testes de fitness passaram ✓")
else:
    separator("Todos os testes de fitness passaram ✓")
