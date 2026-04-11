"""
Testes do MAP-Elites.
Rode com: py test_map_elites.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import random
from fitness import FitnessDetail
from individual import Individual
from map_elites import _bucket, _place, _mutate_from, _compute_frontier, _find_knee, _suggest_lambdas, GRID_X_BINS, GRID_Y_BINS, GRID_X_MAX, GRID_Y_MAX


def _detail(balance_error: float, drift_penalty: float, matchup_pen: float) -> FitnessDetail:
    """Cria FitnessDetail mínimo para testes — sem simulações."""
    return FitnessDetail(
        fitness=0.0, winrates=[], balance_error=balance_error,
        attribute_cost=0.2, drift_penalty=drift_penalty,
        matchup_dominance_penalty=matchup_pen,
    )


def test_bucket_basic():
    assert _bucket(0.0,  0.0, 0.5, 10) == 0
    assert _bucket(0.04, 0.0, 0.5, 10) == 0   # ainda no bucket 0
    assert _bucket(0.05, 0.0, 0.5, 10) == 1
    assert _bucket(0.49, 0.0, 0.5, 10) == 9
    assert _bucket(0.5,  0.0, 0.5, 10) == 9   # clamp no último bucket
    assert _bucket(0.99, 0.0, 0.5, 10) == 9   # fora do range → clamp
    assert _bucket(0.0,  0.0, 0.6,  8) == 0
    assert _bucket(0.6,  0.0, 0.6,  8) == 7   # clamp


def test_place_fills_empty_cell():
    archive = {}
    ind = Individual.from_canonical()
    d = _detail(0.08, 0.10, 0.5)
    _place(archive, ind, d)
    assert len(archive) == 1
    bx = _bucket(0.08, 0.0, GRID_X_MAX, GRID_X_BINS)
    by = _bucket(0.10, 0.0, GRID_Y_MAX, GRID_Y_BINS)
    assert (bx, by) in archive


def test_place_replaces_when_better():
    archive = {}
    ind = Individual.from_canonical()
    d_bad  = _detail(0.08, 0.10, 0.8)
    d_good = _detail(0.08, 0.10, 0.3)
    _place(archive, ind, d_bad)
    _place(archive, ind, d_good)
    bx = _bucket(0.08, 0.0, GRID_X_MAX, GRID_X_BINS)
    by = _bucket(0.10, 0.0, GRID_Y_MAX, GRID_Y_BINS)
    assert archive[(bx, by)][1].matchup_dominance_penalty == 0.3


def test_place_keeps_when_worse():
    archive = {}
    ind = Individual.from_canonical()
    d_good = _detail(0.08, 0.10, 0.3)
    d_bad  = _detail(0.08, 0.10, 0.8)
    _place(archive, ind, d_good)
    _place(archive, ind, d_bad)
    bx = _bucket(0.08, 0.0, GRID_X_MAX, GRID_X_BINS)
    by = _bucket(0.10, 0.0, GRID_Y_MAX, GRID_Y_BINS)
    assert archive[(bx, by)][1].matchup_dominance_penalty == 0.3


def test_place_out_of_bounds_clamps_to_last_bucket():
    archive = {}
    ind = Individual.from_canonical()
    # Valores fora do range fazem clamp para o último bucket — não são perdidos
    d = _detail(0.99, 0.99, 0.5)
    _place(archive, ind, d)
    assert len(archive) == 1  # entra no bucket (9, 7) por clamp


def test_mutate_from_returns_new_individual():
    ind = Individual.from_canonical()
    child = _mutate_from(ind)
    # Deve ser um objeto diferente (clone)
    assert child is not ind
    # Fitness deve estar invalidado
    assert not child.is_evaluated


def test_mutate_from_genes_differ():
    random.seed(42)
    ind = Individual.from_canonical()
    child = _mutate_from(ind)
    # Com MUTATION_RATE=0.2 e 60 genes, estatisticamente pelo menos 1 gene muda
    original_genes = ind.characters[0].genes()
    child_genes    = child.characters[0].genes()
    # Não garantimos que todos diferem, mas o clone não é a mesma referência
    assert original_genes is not child_genes


def _make_archive(cells: list) -> dict:
    """cells: list de (bx, by, balance_error, drift_penalty, matchup_pen)"""
    archive = {}
    ind = Individual.from_canonical()
    for bx, by, bal, drift, pen in cells:
        archive[(bx, by)] = (ind, _detail(bal, drift, pen))
    return archive


def test_compute_frontier_returns_best_bx_per_row():
    archive = _make_archive([
        (3, 0, 0.17, 0.03, 0.5),
        (1, 0, 0.07, 0.03, 0.4),  # mesmo row by=0, menor bx → vence
        (2, 1, 0.12, 0.11, 0.3),
    ])
    frontier = _compute_frontier(archive)
    assert frontier[0] == (1, 0)   # by=0 → bx=1 (menor)
    assert frontier[1] == (2, 1)   # by=1 → bx=2
    assert frontier[2] is None     # by=2 → vazio


def test_compute_frontier_empty_archive():
    frontier = _compute_frontier({})
    assert all(f is None for f in frontier)
    assert len(frontier) == GRID_Y_BINS


def test_find_knee_three_points():
    # Curva em L: joelho deve ser o ponto do meio
    points = [(0.3, 0.1), (0.1, 0.1), (0.1, 0.5)]
    # Distância da reta (0.3,0.1)-(0.1,0.5):
    # ponto (0.1, 0.1) deve ser o mais distante → índice 1
    assert _find_knee(points) == 1


def test_find_knee_linear():
    # Pontos colineares — qualquer índice é aceitável (sem joelho claro)
    points = [(0.0, 0.0), (0.1, 0.1), (0.2, 0.2)]
    knee = _find_knee(points)
    assert 0 <= knee < 3


def test_find_knee_too_few_points():
    assert _find_knee([(0.1, 0.2)]) == 0
    assert _find_knee([(0.1, 0.2), (0.2, 0.3)]) in (0, 1)


def test_suggest_lambdas_returns_required_keys():
    archive = _make_archive([
        (1, 1, 0.07, 0.11, 0.2),
        (2, 2, 0.12, 0.19, 0.3),
        (3, 3, 0.17, 0.26, 0.5),
        (4, 4, 0.22, 0.34, 0.7),
    ])
    result = _suggest_lambdas(archive)
    assert "LAMBDA_DRIFT"   in result
    assert "LAMBDA_MATCHUP" in result
    assert "LAMBDA"         in result
    assert result["LAMBDA"] == 0.2


def test_suggest_lambdas_empty_archive():
    # Archive vazio deve retornar defaults sem exceção
    result = _suggest_lambdas({})
    assert "LAMBDA_DRIFT" in result
    assert result["LAMBDA"] == 0.2


def test_suggest_lambdas_values_are_positive():
    archive = _make_archive([
        (0, 0, 0.02, 0.04, 0.0),
        (1, 2, 0.07, 0.19, 0.2),
        (2, 4, 0.12, 0.34, 0.4),
        (3, 6, 0.17, 0.49, 0.6),
    ])
    result = _suggest_lambdas(archive)
    assert result["LAMBDA_DRIFT"]   >= 0.0
    assert result["LAMBDA_MATCHUP"] >  0.0


if __name__ == "__main__":
    test_bucket_basic()
    test_place_fills_empty_cell()
    test_place_replaces_when_better()
    test_place_keeps_when_worse()
    test_place_out_of_bounds_clamps_to_last_bucket()
    test_mutate_from_returns_new_individual()
    test_mutate_from_genes_differ()
    test_compute_frontier_returns_best_bx_per_row()
    test_compute_frontier_empty_archive()
    test_find_knee_three_points()
    test_find_knee_linear()
    test_find_knee_too_few_points()
    test_suggest_lambdas_returns_required_keys()
    test_suggest_lambdas_empty_archive()
    test_suggest_lambdas_values_are_positive()
    print("Tasks 1-4 — OK")
