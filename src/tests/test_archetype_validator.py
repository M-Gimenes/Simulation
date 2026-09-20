"""
Smoke tests do archetype_validator.
Rode com: py -m src.tests.test_archetype_validator
"""

# ── Task 1 ────────────────────────────────────────────────────────────────────

def test_action_log_structure():
    from src.engine.combat import simulate_combat_detailed, Action
    from src.engine.individual import Individual

    canon = Individual.from_canonical()
    chars = canon.characters
    result, log = simulate_combat_detailed(chars[0], chars[1])

    # Both fighters logged
    assert len(log.stance_counts) == 2
    assert len(log.attacks) == 2
    assert len(log.active_ticks) == 2
    assert len(log.stun_applied) == 2

    # All three stances present as keys (o ataque não é postura: é regra de resolução)
    for counts in log.stance_counts:
        assert set(counts.keys()) == {Action.ADVANCE, Action.RETREAT, Action.DEFEND}

    # Sum of stance counts equals active ticks for each fighter
    for i in range(2):
        assert sum(log.stance_counts[i].values()) == log.active_ticks[i]
        assert 0 <= log.attacks[i] <= log.active_ticks[i]

    # Active ticks positive (both fighters acted at some point)
    assert log.active_ticks[0] > 0
    assert log.active_ticks[1] > 0

    # Stun applied is non-negative
    assert log.stun_applied[0] >= 0
    assert log.stun_applied[1] >= 0

    # Stun tracking: at least one fighter applied stun during a KO combat
    if result.ko:
        assert log.stun_applied[0] > 0 or log.stun_applied[1] > 0

print("test_action_log_structure ...", end=" ", flush=True)
test_action_log_structure()
print("OK")

# ── Task 2 ────────────────────────────────────────────────────────────────────

def test_datastructures():
    from src.analysis.archetype_validator import ArchetypeCheck, ArchetypeValidationReport
    from src.engine.archetypes import ArchetypeID

    check = ArchetypeCheck(
        archetype=ArchetypeID.RUSHDOWN,
        layer="structural_inter",
        description="speed = highest",
        passed=True,
        actual_rank=1,
        expected_rank=1,
    )
    assert check.passed

    report = ArchetypeValidationReport(checks=[check], passed=1, total=1)
    assert report.score == 1.0
    assert report.failures() == []

print("test_datastructures ...", end=" ", flush=True)
test_datastructures()
print("OK")

# ── Task 3 ────────────────────────────────────────────────────────────────────

def test_structural_inter_canonical():
    from src.analysis.archetype_validator import _INTER_ASSERTIONS, _check_structural_inter
    from src.engine.individual import Individual

    canon = Individual.from_canonical()
    checks = _check_structural_inter(canon.characters)

    assert len(checks) == len(_INTER_ASSERTIONS)
    assert all(c.layer == "structural_inter" for c in checks)

    # Todas passam nos valores canônicos atuais
    failed = [c for c in checks if not c.passed]
    assert failed == [], f"Unexpected failures: {[(c.archetype, c.description) for c in failed]}"

print("test_structural_inter_canonical ...", end=" ", flush=True)
test_structural_inter_canonical()
print("OK")

# ── Task 4 ────────────────────────────────────────────────────────────────────

def test_structural_intra_canonical():
    from src.analysis.archetype_validator import _INTRA_ASSERTIONS, _check_structural_intra
    from src.engine.individual import Individual

    canon = Individual.from_canonical()
    checks = _check_structural_intra(canon.characters)

    assert len(checks) == len(_INTRA_ASSERTIONS)
    assert all(c.layer == "structural_intra" for c in checks)

    # Todas passam nos valores canônicos
    failed = [c for c in checks if not c.passed]
    assert failed == [], f"Unexpected failures: {[c.description for c in failed]}"

print("test_structural_intra_canonical ...", end=" ", flush=True)
test_structural_intra_canonical()
print("OK")

# ── Task 5 ────────────────────────────────────────────────────────────────────

def test_run_validation_canonical():
    from src.analysis.archetype_validator import (
        _INTER_ASSERTIONS, _INTRA_ASSERTIONS, run_validation,
    )
    from src.engine.individual import Individual

    canon  = Individual.from_canonical()
    report = run_validation(canon)

    n_structural = len(_INTER_ASSERTIONS) + len(_INTRA_ASSERTIONS)
    assert report.total == n_structural
    assert report.passed == n_structural  # todas as estruturais passam no canônico
    assert 0.0 <= report.score <= 1.0
    assert len(report.failures()) == report.total - report.passed

print("test_run_validation_canonical ...", end=" ", flush=True)
test_run_validation_canonical()

print("OK")

# ── Empate não dá asserção de graça ──────────────────────────────────────────

def test_ties_count_against_the_assertion():
    """Cinco personagens idênticos não têm "o de maior alcance". Resolver o empate pela
    ordem do índice aprovava 4 das 13 asserções da Layer 1 em qualquer espelho — piso
    inflado por um detalhe de implementação."""
    from src.analysis.archetype_validator import _check_structural_inter, _rank_against
    from src.engine.archetypes import ARCHETYPE_ORDER
    from src.experiments.baselines import mirror_roster

    assert _rank_against([3.0, 1.0, 2.0], 0, 1) == 1          # estritamente o maior
    assert _rank_against([3.0, 3.0, 2.0], 0, 1) == 2          # empatado no topo
    assert _rank_against([1.0, 1.0, 2.0], 0, 3) == 2          # empatado no fundo
    for aid in ARCHETYPE_ORDER:
        checks = _check_structural_inter(mirror_roster(aid).characters)
        assert not any(c.passed for c in checks), (aid, [c.description for c in checks if c.passed])

print("test_ties_count_against_the_assertion ...", end=" ", flush=True)
test_ties_count_against_the_assertion()
print("OK")

# ── Pesos valem pela razão, não pela escala ──────────────────────────────────

def test_weight_scale_is_invisible():
    """Multiplicar os 3 pesos de um personagem por k > 0 não muda o combate — logo não
    pode mudar o veredito da Layer 1 (mesma razão de `fitness.drift_genes`)."""
    from src.analysis.archetype_validator import _check_structural_inter
    from src.engine.individual import Individual

    base = [c.passed for c in _check_structural_inter(Individual.from_canonical().characters)]
    for k in (0.1, 3.0):
        scaled = Individual.from_canonical()
        scaled.characters[0].weights = [w * k for w in scaled.characters[0].weights]
        assert [c.passed for c in _check_structural_inter(scaled.characters)] == base, k

print("test_weight_scale_is_invisible ...", end=" ", flush=True)
test_weight_scale_is_invisible()
print("OK")

# ── Concordância de ranking comportamental ───────────────────────────────────

def test_rank_agreement_scale():
    """τ-b de Kendall: 1 na mesma ordem, −1 invertida, e empate não conta a favor."""
    from src.analysis.archetype_validator import _kendall_tau_b, rank_agreement
    from src.analysis.analyze_matchups import BEHAVIORAL_KEYS
    from src.engine.archetypes import ARCHETYPE_ORDER

    assert _kendall_tau_b([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) == 1.0
    assert _kendall_tau_b([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == -1.0
    assert _kendall_tau_b([1, 1, 1, 1, 1], [1, 2, 3, 4, 5]) == 0.0, "sem ordem, sem concordância"

    profile = {aid: {key: float(i) for key in BEHAVIORAL_KEYS}
               for i, aid in enumerate(ARCHETYPE_ORDER)}
    reversed_profile = {aid: {key: -value for key, value in metrics.items()}
                        for aid, metrics in profile.items()}
    assert rank_agreement(profile, profile) == 1.0
    assert rank_agreement(reversed_profile, profile) == -1.0

print("test_rank_agreement_scale ...", end=" ", flush=True)
test_rank_agreement_scale()
print("OK")
print("\nAll tests passed.")
