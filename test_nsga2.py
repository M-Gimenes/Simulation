"""
Smoke tests do NSGA-II.
Rode com: py test_nsga2.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import math
import random

from individual import Individual
from config import NSGA2_POP_SIZE, NSGA2_GENERATIONS, NSGA2_OBJECTIVES
from fitness import evaluate_objectives
from nsga2 import _dominates, fast_non_dominated_sort, crowding_distance_assignment


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



def _ind_with_obj(objs):
    """Helper: cria indivíduo canônico com objectives injetados (sem avaliar)."""
    ind = Individual.from_canonical()
    ind.objectives = tuple(objs)
    return ind


def test_dominates_strict():
    a = _ind_with_obj([0.1, 0.1, 0.1])
    b = _ind_with_obj([0.2, 0.2, 0.2])
    assert _dominates(a, b),       "a domina b (todos menores)"
    assert not _dominates(b, a)


def test_dominates_requires_strict_in_at_least_one():
    a = _ind_with_obj([0.1, 0.1, 0.1])
    b = _ind_with_obj([0.1, 0.1, 0.1])
    assert not _dominates(a, b), "igualdade em tudo não é dominação"
    assert not _dominates(b, a)


def test_dominates_fails_if_any_worse():
    a = _ind_with_obj([0.1, 0.3, 0.1])
    b = _ind_with_obj([0.2, 0.2, 0.2])
    assert not _dominates(a, b), "a é pior em f[1]"
    assert not _dominates(b, a), "b é pior em f[0] e f[2]"


def test_sort_single_pareto_layer():
    pop = [
        _ind_with_obj([0.1, 0.5, 0.5]),
        _ind_with_obj([0.5, 0.1, 0.5]),
        _ind_with_obj([0.5, 0.5, 0.1]),
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 1, "todos no mesmo rank"
    assert all(ind.rank == 0 for ind in pop)


def test_sort_multiple_layers():
    pop = [
        _ind_with_obj([0.1, 0.5, 0.5]),   # rank 0
        _ind_with_obj([0.5, 0.1, 0.5]),   # rank 0
        _ind_with_obj([0.5, 0.5, 0.1]),   # rank 0
        _ind_with_obj([0.6, 0.6, 0.6]),   # rank 1 (dominado por todos os 3)
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 2
    assert len(fronts[0]) == 3
    assert len(fronts[1]) == 1
    assert pop[3].rank == 1


def test_sort_divergent_dominated_sets():
    """
    Regressão: indivíduos da fronteira 0 dominam conjuntos diferentes.
    Se o sort usar `.index()` em vez de índices, este teste falha
    (porque Individual.__eq__ compara characters, que são iguais nos clones).
    """
    pop = [
        _ind_with_obj([0.1, 0.5, 0.5]),   # rank 0 — domina só ind3
        _ind_with_obj([0.5, 0.1, 0.5]),   # rank 0 — domina só ind4
        _ind_with_obj([0.5, 0.5, 0.1]),   # rank 0 — interior
        _ind_with_obj([0.2, 0.9, 0.9]),   # rank 1 — dominado só por ind0
        _ind_with_obj([0.9, 0.2, 0.9]),   # rank 1 — dominado só por ind1
    ]
    fronts = fast_non_dominated_sort(pop)
    assert len(fronts) == 2, f"esperado 2 fronteiras, obtido {len(fronts)}"
    assert len(fronts[0]) == 3
    assert len(fronts[1]) == 2, "ind3 e ind4 devem estar ambos no rank 1"
    assert pop[3].rank == 1
    assert pop[4].rank == 1


def test_crowding_assigns_inf_to_extremes():
    front = [
        _ind_with_obj([0.1, 0.5, 0.5]),
        _ind_with_obj([0.3, 0.3, 0.3]),
        _ind_with_obj([0.5, 0.1, 0.5]),
        _ind_with_obj([0.5, 0.5, 0.1]),
    ]
    crowding_distance_assignment(front)
    # Extremos em cada dimensão recebem inf.
    inf_count = sum(1 for ind in front if math.isinf(ind.crowding))
    assert inf_count >= 3, "extremos em cada objetivo recebem +inf"


def test_crowding_small_front_all_inf():
    # Fronteira com 2 pontos: ambos são extremos em todas as dimensões.
    front = [
        _ind_with_obj([0.1, 0.1, 0.1]),
        _ind_with_obj([0.9, 0.9, 0.9]),
    ]
    crowding_distance_assignment(front)
    assert math.isinf(front[0].crowding)
    assert math.isinf(front[1].crowding)


def test_crowding_middle_has_finite_value():
    # 3 pontos colineares em f[0]: meio tem valor finito, extremos tem inf.
    front = [
        _ind_with_obj([0.0, 0.5, 0.5]),
        _ind_with_obj([0.5, 0.5, 0.5]),
        _ind_with_obj([1.0, 0.5, 0.5]),
    ]
    crowding_distance_assignment(front)
    assert math.isinf(front[0].crowding)
    assert math.isinf(front[2].crowding)
    assert not math.isinf(front[1].crowding)
    assert front[1].crowding > 0


from operators import nsga2_binary_tournament
from nsga2 import select_representatives


def test_tournament_picks_lower_rank():
    a = _ind_with_obj([0.1, 0.1, 0.1]); a.rank = 0; a.crowding = 1.0
    b = _ind_with_obj([0.5, 0.5, 0.5]); b.rank = 2; b.crowding = 10.0
    random.seed(0)
    winner = nsga2_binary_tournament([a, b])
    assert winner is a


def test_tournament_breaks_tie_by_crowding():
    a = _ind_with_obj([0.1, 0.1, 0.1]); a.rank = 1; a.crowding = 5.0
    b = _ind_with_obj([0.2, 0.2, 0.2]); b.rank = 1; b.crowding = 1.0
    random.seed(0)
    winner = nsga2_binary_tournament([a, b])
    assert winner is a, "mesmo rank → vence maior crowding"


def test_tournament_stochastic_on_full_tie():
    a = _ind_with_obj([0.1, 0.1, 0.1]); a.rank = 1; a.crowding = 5.0
    b = _ind_with_obj([0.2, 0.2, 0.2]); b.rank = 1; b.crowding = 5.0
    wins_a = 0
    for s in range(200):
        random.seed(s)
        winner = nsga2_binary_tournament([a, b])
        if winner is a:
            wins_a += 1
    assert 60 < wins_a < 140, f"empate total não está aleatório o suficiente: {wins_a}/200"


def test_representatives_identifies_extremes():
    front = [
        _ind_with_obj([0.05, 0.50, 0.50]),   # menor f[0]
        _ind_with_obj([0.50, 0.05, 0.50]),   # menor f[1]
        _ind_with_obj([0.50, 0.50, 0.05]),   # menor f[2]
        _ind_with_obj([0.20, 0.20, 0.20]),   # interior
    ]
    reps = select_representatives(front)
    assert reps["best_balance"] is front[0]
    assert reps["best_matchup"] is front[1]
    assert reps["best_drift"]   is front[2]


def test_representatives_ideal_closest_to_origin():
    front = [
        _ind_with_obj([0.05, 0.50, 0.50]),   # dist ≈ 0.707
        _ind_with_obj([0.20, 0.20, 0.20]),   # dist ≈ 0.346 — mais perto
        _ind_with_obj([0.50, 0.50, 0.05]),   # dist ≈ 0.707
    ]
    reps = select_representatives(front)
    assert reps["ideal_point"] is front[1]


def test_representatives_knee_is_interior():
    # Fronteira em formato "L" — knee deve ser o ponto da curva, não os extremos.
    front = [
        _ind_with_obj([0.05, 0.95, 0.50]),   # extremo de f[0]
        _ind_with_obj([0.15, 0.15, 0.50]),   # joelho — mais distante do plano dos extremos
        _ind_with_obj([0.95, 0.05, 0.50]),   # extremo de f[1]
        _ind_with_obj([0.50, 0.50, 0.05]),   # extremo de f[2]
    ]
    reps = select_representatives(front)
    assert reps["knee_point"] is front[1]


def test_representatives_all_five_keys():
    front = [_ind_with_obj([0.1 * i, 0.2, 0.3]) for i in range(5)]
    reps = select_representatives(front)
    expected_keys = {"best_balance", "best_matchup", "best_drift", "knee_point", "ideal_point"}
    assert set(reps.keys()) == expected_keys


from nsga2 import run


def test_run_smoke_small_config():
    """Roda NSGA-II com configuração reduzida e valida shape dos resultados."""
    result = run(seed=42, pop_size=20, n_generations=3, verbose=False)

    # Fronteira final não-vazia
    assert len(result.pareto_front) > 0, "fronteira de Pareto vazia"
    # Todos os indivíduos da fronteira final têm rank=0
    assert all(ind.rank == 0 for ind in result.pareto_front)
    # Todos têm objectives avaliado
    assert all(ind.objectives is not None for ind in result.pareto_front)
    # 5 representantes distintos (ou pelo menos as 5 chaves existentes)
    reps = result.representatives
    assert set(reps.keys()) == {"best_balance", "best_matchup", "best_drift", "knee_point", "ideal_point"}
    # Histórico tem 3 entradas (n_generations)
    assert len(result.history) == 3


if __name__ == "__main__":
    test_individual_has_nsga2_fields()
    test_individual_clone_copies_nsga2_fields()
    test_config_constants_exist()
    test_evaluate_objectives_returns_3tuple()
    test_evaluate_objectives_caches_on_individual()
    test_dominates_strict()
    test_dominates_requires_strict_in_at_least_one()
    test_dominates_fails_if_any_worse()
    test_sort_single_pareto_layer()
    test_sort_multiple_layers()
    test_sort_divergent_dominated_sets()
    test_crowding_assigns_inf_to_extremes()
    test_crowding_small_front_all_inf()
    test_crowding_middle_has_finite_value()
    test_tournament_picks_lower_rank()
    test_tournament_breaks_tie_by_crowding()
    test_tournament_stochastic_on_full_tie()
    test_representatives_identifies_extremes()
    test_representatives_ideal_closest_to_origin()
    test_representatives_knee_is_interior()
    test_representatives_all_five_keys()
    test_run_smoke_small_config()
    print("Task 7 — OK")
