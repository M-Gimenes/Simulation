"""
Smoke test dos operadores genéticos.
Rode com: py -m src.tests.test_operators
"""

import random
random.seed(42)

from src.engine.individual import Individual
from src.engine.operators import tournament_selection, crossover, mutate, next_generation
from src.engine.config import (
    ATTRIBUTE_BOUNDS,
    ELITE_RATE,
    POPULATION_SIZE,
    TOURNAMENT_SIZE,
    WEIGHT_BOUNDS,
)

# Elites no orçamento default: a taxa aplicada ao tamanho da população.
ELITES = round(POPULATION_SIZE * ELITE_RATE)


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
    assert all(lo <= a <= hi for a, (lo, hi) in zip(char.attributes, ATTRIBUTE_BOUNDS)), \
        "Atributo fora do bound após mutação"
    assert all(lo <= w <= hi for w, (lo, hi) in zip(char.weights, WEIGHT_BOUNDS)), \
        "Peso fora do bound após mutação"

# Com rate=1.0, ao menos alguns genes devem ter mudado
n_attrs   = len(ATTRIBUTE_BOUNDS) * len(ind.characters)
n_weights = len(WEIGHT_BOUNDS)    * len(ind.characters)

changed_attrs   = sum(1 for i, c in enumerate(ind.characters)
                      for j, a in enumerate(c.attributes)
                      if a != original_attrs[i][j])
changed_weights = sum(1 for i, c in enumerate(ind.characters)
                      for j, w in enumerate(c.weights)
                      if w != original_weights[i][j])

print(f"  Atributos modificados: {changed_attrs}/{n_attrs}")
print(f"  Pesos modificados:     {changed_weights}/{n_weights}")
assert changed_attrs > 0 and changed_weights > 0, "Nenhum gene foi mutado"
print("  ✓ Mutação aplicada dentro dos bounds, fitness invalidado")


# ── 4. next_generation ──────────────────────────────────────────────────────

separator("Geração seguinte (sem combates)")
pop = make_pop(POPULATION_SIZE)
new_gen = next_generation(pop)

assert len(new_gen) == POPULATION_SIZE, f"Tamanho incorreto: {len(new_gen)}"

# Elites devem ter fitness preservado
sorted_pop = sorted(pop, key=lambda x: x.fitness, reverse=True)
elite_fitnesses = {ind.fitness for ind in sorted_pop[:ELITES]}
new_evaluated = [ind for ind in new_gen if ind.is_evaluated]
assert len(new_evaluated) == ELITES, f"Esperado {ELITES} elites, got {len(new_evaluated)}"

# Filhos não devem ter fitness
children = [ind for ind in new_gen if not ind.is_evaluated]
assert len(children) == POPULATION_SIZE - ELITES

print(f"  Tamanho da nova geração: {len(new_gen)} ✓")
print(f"  Elites preservados:      {len(new_evaluated)}/{ELITES} ✓")
print(f"  Filhos sem fitness:      {len(children)} ✓")


# ── Elitismo é FRAÇÃO, não contagem ──────────────────────────────────────────

separator("elite_count: elitismo é 10% do tamanho REAL da população")

from src.engine.operators import elite_count

assert elite_count(POPULATION_SIZE) == ELITES, (
    f"elite_count({POPULATION_SIZE})={elite_count(POPULATION_SIZE)}, esperado {ELITES} "
    f"({ELITE_RATE:.0%} de {POPULATION_SIZE})"
)
print(f"  pop={POPULATION_SIZE} (default): {elite_count(POPULATION_SIZE)} elites "
      f"= {ELITE_RATE:.0%} ✓")

# O bug que isto conserta: com a contagem ABSOLUTA (30), uma população reduzida
# ficava com elitismo de 25% (pop 120) ou 100% (pop 30) — aí a geração seguinte é só
# clones e o AG para de buscar, em silêncio e produzindo números plausíveis.
for n in (120, 40, 12):
    e = elite_count(n)
    taxa_busca = (n - e) / n
    assert e < n, f"pop={n}: elitismo tomou a população inteira ({e}/{n})"
    assert abs(e / n - ELITE_RATE) < 0.05, f"pop={n}: elitismo {e/n:.0%}, esperado ~{ELITE_RATE:.0%}"
    print(f"  pop={n:>3}: {e:>2} elites -> {n - e:>3} filhos ({taxa_busca:.0%} de busca real) ✓")

# A geração seguinte de uma população reduzida precisa ter filhos DE VERDADE.
pequena = [Individual.random() for _ in range(12)]
for i, ind in enumerate(pequena):
    ind.fitness = -float(i)
nova = next_generation(pequena)
filhos = [ind for ind in nova if not ind.is_evaluated]
assert len(nova) == 12, f"tamanho não preservado: {len(nova)}"
assert len(filhos) == 12 - elite_count(12), "a população reduzida não gerou filhos"
print(f"  pop=12 real: {len(filhos)} filhos gerados (com a contagem absoluta seriam 0) ✓")


# ── Seleção como estado de processo (braços do sweep) ────────────────────────

separator("set_selection: elitismo e torneio variam sem editar o config")

from src.engine.operators import get_selection, set_selection

assert get_selection() == (ELITE_RATE, TOURNAMENT_SIZE), (
    f"estado inicial {get_selection()} não veio do config "
    f"({ELITE_RATE}, {TOURNAMENT_SIZE})"
)
print(f"  estado inicial == config ({ELITE_RATE:g}, {TOURNAMENT_SIZE}) ✓")

# O modo de falha que isto cobre: `from .config import ELITE_RATE` congela o valor no
# import, então um braço do sweep rodaria no valor do arquivo sem sintoma nenhum.
set_selection(0.30, 7)
assert get_selection() == (0.30, 7), f"set_selection não pegou: {get_selection()}"
assert elite_count(100) == 30, f"elite_count ignorou a taxa do braço: {elite_count(100)}"
grande = [Individual.random() for _ in range(40)]
for i, ind in enumerate(grande):
    ind.fitness = -float(i)
vencedor = tournament_selection(grande)
assert vencedor.fitness is not None
print(f"  taxa 0,30 -> elite_count(100) = {elite_count(100)}; torneio 7 aceito ✓")

# O braço "sem elitismo" precisa ser MESMO sem elitismo: arredondar para 1 o
# descaracterizaria, e ele existe justamente para mostrar o que o elitismo segura.
set_selection(0.0, TOURNAMENT_SIZE)
assert elite_count(300) == 0, f"taxa 0 preservou {elite_count(300)} elites"
sem_elite = next_generation(pequena)
assert all(not ind.is_evaluated for ind in sem_elite), "taxa 0 ainda clonou alguém"
assert len(sem_elite) == 12
print("  taxa 0,0: nenhum elite preservado, geração 100% de filhos ✓")

set_selection(ELITE_RATE, TOURNAMENT_SIZE)
assert elite_count(POPULATION_SIZE) == ELITES, "o default não voltou"
print(f"  restaurado para o default ({ELITE_RATE:g}, {TOURNAMENT_SIZE}) ✓")


separator("Todos os testes de operadores passaram ✓")
