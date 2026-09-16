"""
Smoke test da função de fitness.
Rode com: py -m src.tests.test_fitness
"""

from src.engine.individual import Individual
from src.engine.fitness import (
    _archetype_deviation,
    canonical_genes,
    drift_weights,
    evaluate,
    evaluate_detail,
    evaluate_population,
)
from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import DRIFT_DEFINING_WEIGHT, GENE_BOUNDS, GENE_NAMES


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

print(f"\n  drift_penalty     = {detail.drift_penalty:.4f}")
print(f"  dominance_penalty = {detail.dominance_penalty:.4f}")
print(f"  fitness           = {detail.fitness:.4f}")
# fitness = -(LAMBDA_DRIFT*drift + LAMBDA_DOMINANCE*dom); drift∈[0,~1], dom∈[0,~2] (C2)
assert -4.0 < detail.fitness <= 0.0, f"Fitness fora do range: {detail.fitness}"
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


# ── 2. Drift: identidade estrutural ponderada ────────────────────────────────

separator("Drift — canônico zera, gene definidor pesa mais")

assert detail.drift_penalty == 0.0, (
    f"Canônico deve ter drift exatamente 0, deu {detail.drift_penalty}"
)
print("  ✓ drift_penalty do canônico = 0")

# Todo nome em defining_genes tem de ser um gene real (pega typo na declaração).
for aid in ARCHETYPE_ORDER:
    for gene in ARCHETYPES[aid].defining_genes:
        assert gene in GENE_NAMES, f"{ARCHETYPES[aid].name}: gene inexistente {gene!r}"
print("  ✓ defining_genes de todos os arquétipos são genes válidos")

# Mesmo deslocamento normalizado: gene definidor tem de custar mais que os outros.
# Zoner: `range` é definidor, `speed` não.
zoner   = ARCHETYPES[ARCHETYPE_ORDER[0]]
i_def   = GENE_NAMES.index(zoner.defining_genes[0])
i_plain = next(i for i, n in enumerate(GENE_NAMES) if n not in zoner.defining_genes)
FRACTION = 0.2   # fração do range do bound deslocada em cada caso

def _deviation_moving(gene_index: int) -> float:
    char  = Individual.from_canonical().get(zoner.id)
    lo, hi = GENE_BOUNDS[gene_index]
    genes = char.genes()
    genes[gene_index] = canonical_genes(zoner)[gene_index] - FRACTION * (hi - lo)
    char.load_genes(genes)
    char.clip()
    return _archetype_deviation(char)

dev_def, dev_plain = _deviation_moving(i_def), _deviation_moving(i_plain)
ratio = (dev_def / dev_plain) ** 2   # desvios entram ao quadrado na RMS
print(f"  mover {GENE_NAMES[i_def]:<10} ({FRACTION:.0%} do range) → desvio {dev_def:.4f}")
print(f"  mover {GENE_NAMES[i_plain]:<10} ({FRACTION:.0%} do range) → desvio {dev_plain:.4f}")
assert abs(ratio - DRIFT_DEFINING_WEIGHT) < 1e-9, (
    f"Gene definidor deve pesar {DRIFT_DEFINING_WEIGHT}× ao quadrado, deu {ratio:.4f}"
)
print(f"  ✓ gene definidor pesa exatamente {DRIFT_DEFINING_WEIGHT}× (razão dos quadrados)")

# Clip mantém todo gene dentro do bound → |desvio normalizado| ≤ 1 → drift ≤ 1.
import random as _random
_random.seed(1)
for _ in range(20):
    rand = Individual.random()
    for char in rand.characters:
        dev = _archetype_deviation(char)
        assert 0.0 <= dev <= 1.0, f"desvio fora de [0,1]: {dev}"
print("  ✓ desvio permanece em [0, 1] para 100 personagens aleatórios")

# Pesos: um por gene, e só os definidores acima de 1.0.
for aid in ARCHETYPE_ORDER:
    arch = ARCHETYPES[aid]
    w    = drift_weights(arch)
    assert len(w) == len(GENE_NAMES)
    for name, wi in zip(GENE_NAMES, w):
        expected = DRIFT_DEFINING_WEIGHT if name in arch.defining_genes else 1.0
        assert wi == expected, f"{arch.name}/{name}: peso {wi}, esperado {expected}"
print("  ✓ vetor de pesos consistente com defining_genes nos 5 arquétipos")


# ── 3. Cache de fitness ──────────────────────────────────────────────────────

separator("Cache: não reavalia indivíduo já avaliado")
ind2 = Individual.from_canonical()
assert not ind2.is_evaluated
f1 = evaluate(ind2)
assert ind2.is_evaluated
f2 = evaluate(ind2)   # deve retornar cached sem recalcular
assert f1 == f2
print(f"  ✓ Cache funcionando (fitness={f1:.4f})")


# ── 4. Invalidação de fitness ────────────────────────────────────────────────

separator("Invalidação após mutação simulada")
ind2.invalidate_fitness()
assert not ind2.is_evaluated
print("  ✓ Fitness invalidado corretamente")


# ── 5. Indivíduo aleatório ───────────────────────────────────────────────────

separator("Fitness de indivíduo aleatório")
import random
random.seed(0)
rand_ind = Individual.random()
f = evaluate(rand_ind)
print(f"  fitness = {f:.4f}")
assert rand_ind.is_evaluated
print("  ✓ Indivíduo aleatório avaliado sem crash")


# ── 6. evaluate_population ──────────────────────────────────────────────────

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
