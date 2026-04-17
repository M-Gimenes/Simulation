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


if __name__ == "__main__":
    test_individual_has_nsga2_fields()
    test_individual_clone_copies_nsga2_fields()
    test_config_constants_exist()
    print("Task 1 — OK")
