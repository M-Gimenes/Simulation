"""
Smoke tests do NSGA-II.
Rode com: py test_nsga2.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from individual import Individual
from config import NSGA2_POP_SIZE, NSGA2_GENERATIONS, NSGA2_OBJECTIVES


def test_individual_has_nsga2_fields():
    ind = Individual.from_canonical()
    assert ind.objectives is None, "objectives deve iniciar como None"
    assert ind.rank is None,       "rank deve iniciar como None"
    assert ind.crowding is None,   "crowding deve iniciar como None"


def test_individual_clone_copies_nsga2_fields():
    ind = Individual.from_canonical()
    ind.objectives = (0.1, 0.2, 0.3)
    ind.rank = 2
    ind.crowding = 1.5
    clone = ind.clone()
    assert clone.objectives == (0.1, 0.2, 0.3)
    assert clone.rank == 2
    assert clone.crowding == 1.5
    # Alterar o clone não afeta original
    clone.rank = 99
    assert ind.rank == 2


def test_config_constants_exist():
    from config import POPULATION_SIZE, MAX_GENERATIONS
    assert NSGA2_POP_SIZE == POPULATION_SIZE
    assert NSGA2_GENERATIONS == MAX_GENERATIONS
    assert NSGA2_OBJECTIVES == ["balance_error", "matchup_dominance_penalty", "drift_penalty"]


import random
from fitness import evaluate_objectives


def test_evaluate_objectives_returns_3tuple():
    random.seed(0)
    ind = Individual.from_canonical()
    objs = evaluate_objectives(ind)
    assert isinstance(objs, tuple), "deve retornar tupla"
    assert len(objs) == 3,          "deve ter 3 objetivos"
    for o in objs:
        assert isinstance(o, float), f"objetivo deve ser float, recebeu {type(o)}"
        assert 0.0 <= o <= 1.0,       f"objetivo fora de [0,1]: {o}"


def test_evaluate_objectives_caches_on_individual():
    random.seed(0)
    ind = Individual.from_canonical()
    assert ind.objectives is None
    objs = evaluate_objectives(ind)
    assert ind.objectives == objs, "objectives deve ser cacheado no indivíduo"
    # Segunda chamada retorna o cacheado sem reavaliar
    second = evaluate_objectives(ind)
    assert second is ind.objectives


if __name__ == "__main__":
    test_individual_has_nsga2_fields()
    test_individual_clone_copies_nsga2_fields()
    test_config_constants_exist()
    test_evaluate_objectives_returns_3tuple()
    test_evaluate_objectives_caches_on_individual()
    print("Task 2 — OK")
