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

print("test_action_log_structure ...", end=" ", flush=True)
test_action_log_structure()
print("OK")
