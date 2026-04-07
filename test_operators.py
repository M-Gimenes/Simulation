"""
Smoke test dos operadores genéticos.
Rode com: python test_operators.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import random
random.seed(42)

from individual import Individual
from operators import tournament_selection, crossover, mutate, next_generation
from config import ELITE_SIZE, POPULATION_SIZE


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# Cria população com fitness sintético para testar sem rodar combates
def make_pop(n: int) -> list:
    pop = [Individual.random() for _ in range(n)]
    for i, ind in enumerate(pop):
        ind.fitness = float(i) / n   # fitness crescente artificial
    return pop


# ── 1. Torneio ───────────────────────────────────────────────────────────────

separator("Seleção por torneio")
pop = make_pop(20)
best = max(pop, key=lambda x: x.fitness)

# Com k=20, o torneio deve sempre retornar o melhor
winner = tournament_selection(pop, k=20)
assert winner is best, "Torneio com k=pop não retornou o melhor"

# Distribuição de seleção: melhores devem ser escolhidos mais frequentemente
counts = {id(ind): 0 for ind in pop}
for _ in range(1000):
    sel = tournament_selection(pop, k=3)
    counts[id(sel)] += 1

top5_ids = {id(ind) for ind in sorted(pop, key=lambda x: x.fitness, reverse=True)[:5]}
top5_wins = sum(counts[i] for i in top5_ids)
print(f"  Top-5 foram selecionados {top5_wins}/1000 vezes ({top5_wins/10:.1f}%)")
assert top5_wins > 500, "Torneio não está priorizando melhores indivíduos"
print("  ✓ Torneio com pressão seletiva correta")


# ── 2. Cruzamento ────────────────────────────────────────────────────────────

separator("Cruzamento por bloco")
p1 = Individual.from_canonical()
p2 = Individual.random()
p1.fitness = 0.8
p2.fitness = 0.6

child = crossover(p1, p2)

assert len(child) == 5, "Filho deve ter 5 personagens"
assert child.fitness is None, "Filho não deve ter fitness definido"

# Cada personagem do filho deve ser cópia de p1 ou p2 (mesmo arquétipo)
for i in range(5):
    from_p1 = child[i].attributes == p1[i].attributes and child[i].weights == p1[i].weights
    from_p2 = child[i].attributes == p2[i].attributes and child[i].weights == p2[i].weights
    assert from_p1 or from_p2, f"Personagem {i} não veio de nenhum pai"

# Crossover não deve alterar os pais
child[0].attributes[0] = 999.0
assert p1[0].attributes[0] != 999.0, "Crossover afetou o pai 1"
assert p2[0].attributes[0] != 999.0, "Crossover afetou o pai 2"

print("  ✓ Filho herda blocos completos dos pais")
print("  ✓ Pais não foram modificados")


# ── 3. Mutação ───────────────────────────────────────────────────────────────

separator("Mutação gaussiana")
ind = Individual.from_canonical()
ind.fitness = 0.5
original_attrs = [list(c.attributes) for c in ind.characters]
original_weights = [list(c.weights) for c in ind.characters]

mutate(ind, mutation_rate=1.0)   # 100% de chance → todos os genes mutam

assert ind.fitness is None, "Mutação deve invalidar fitness"

# Todos os genes devem estar dentro dos bounds
for char in ind.characters:
    assert all(0.0 <= a <= 100.0 for a in char.attributes), "Atributo fora do bound após mutação"
    assert all(0.0 <= w <= 1.0   for w in char.weights),    "Peso fora do bound após mutação"

# Com rate=1.0, ao menos alguns genes devem ter mudado
changed_attrs   = sum(1 for i, c in enumerate(ind.characters)
                      for j, a in enumerate(c.attributes)
                      if a != original_attrs[i][j])
changed_weights = sum(1 for i, c in enumerate(ind.characters)
                      for j, w in enumerate(c.weights)
                      if w != original_weights[i][j])

print(f"  Atributos modificados: {changed_attrs}/45")
print(f"  Pesos modificados:     {changed_weights}/25")
assert changed_attrs > 0 and changed_weights > 0, "Nenhum gene foi mutado"
print("  ✓ Mutação aplicada dentro dos bounds, fitness invalidado")


# ── 4. next_generation ──────────────────────────────────────────────────────

separator("Geração seguinte (sem combates)")
pop = make_pop(POPULATION_SIZE)
new_gen = next_generation(pop)

assert len(new_gen) == POPULATION_SIZE, f"Tamanho incorreto: {len(new_gen)}"

# Elites devem ter fitness preservado
sorted_pop = sorted(pop, key=lambda x: x.fitness, reverse=True)
elite_fitnesses = {ind.fitness for ind in sorted_pop[:ELITE_SIZE]}
new_evaluated = [ind for ind in new_gen if ind.is_evaluated]
assert len(new_evaluated) == ELITE_SIZE, f"Esperado {ELITE_SIZE} elites, got {len(new_evaluated)}"

# Filhos não devem ter fitness
children = [ind for ind in new_gen if not ind.is_evaluated]
assert len(children) == POPULATION_SIZE - ELITE_SIZE

print(f"  Tamanho da nova geração: {len(new_gen)} ✓")
print(f"  Elites preservados:      {len(new_evaluated)}/{ELITE_SIZE} ✓")
print(f"  Filhos sem fitness:      {len(children)} ✓")


separator("Todos os testes de operadores passaram ✓")
