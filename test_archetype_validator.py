import sys, os
sys.path.insert(0, os.getcwd())

# ── Task 1 ────────────────────────────────────────────────────────────────────

def test_action_log_structure():
    from combat import simulate_combat_detailed, Action
    from individual import Individual

    canon = Individual.from_canonical()
    chars = canon.characters
    result, log = simulate_combat_detailed(chars[0], chars[1])

    # Both fighters logged
    assert len(log.action_counts) == 2
    assert len(log.active_ticks) == 2
    assert len(log.stun_applied) == 2

    # All four actions present as keys
    for counts in log.action_counts:
        assert set(counts.keys()) == {Action.ATTACK, Action.ADVANCE, Action.RETREAT, Action.DEFEND}

    # Sum of action counts equals active ticks for each fighter
    for i in range(2):
        assert sum(log.action_counts[i].values()) == log.active_ticks[i]

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
    from archetype_validator import ArchetypeCheck, CharacterStats, ArchetypeValidationReport
    from archetypes import ArchetypeID
    from combat import Action

    check = ArchetypeCheck(
        archetype=ArchetypeID.RUSHDOWN,
        layer="structural_inter",
        description="speed = highest",
        passed=True,
        actual_rank=1,
        expected_rank=1,
    )
    assert check.passed

    stats = CharacterStats(
        action_counts={Action.ATTACK: 10, Action.ADVANCE: 20, Action.RETREAT: 5, Action.DEFEND: 15},
        active_ticks=50,
        wins=3,
        n_combats=4,
        ko_wins=2,
        hp_pct_on_wins=[0.8, 0.6, 0.7],
        ticks_on_wins=[100, 150, 120],
        stun_applied=8,
    )
    assert abs(stats.aggression_rate - 0.60) < 1e-9   # (10+20)/50
    assert abs(stats.defend_rate     - 0.30) < 1e-9   # 15/50
    assert abs(stats.retreat_rate    - 0.10) < 1e-9   # 5/50
    assert abs(stats.ko_rate         - 2/3)  < 1e-9   # 2/3
    assert abs(stats.avg_hp_pct_on_win - 0.7)          < 1e-9
    assert abs(stats.avg_ticks_on_win  - 370/3)        < 1e-9
    assert abs(stats.avg_stun_applied  - 2.0)          < 1e-9  # 8/4

    report = ArchetypeValidationReport(checks=[check], passed=1, total=1)
    assert report.score == 1.0
    assert report.failures() == []

print("test_datastructures ...", end=" ", flush=True)
test_datastructures()
print("OK")
