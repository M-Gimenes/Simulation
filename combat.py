"""
Simulação de combate tick a tick 1v1.

API pública:
    simulate_combat(char_a, char_b) -> CombatResult
    simulate_combat_detailed(char_a, char_b) -> (CombatResult, ActionLog)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from character import Character
from config import (
    ACTION_PERSISTENCE_SUBTICKS,
    DEFEND_DAMAGE_REDUCTION,
    FIELD_SIZE,
    INITIAL_DISTANCE,
    MAX_TICKS,
    STUN_CAP_MULTIPLIER,
    TICK_SCALE,
    WALL_CORNER_THRESHOLD,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tipos de dados
# ─────────────────────────────────────────────────────────────────────────────


class Action(IntEnum):
    ATTACK = 0
    ADVANCE = 1
    RETREAT = 2
    DEFEND = 3


@dataclass
class FighterState:
    character: Character
    hp: float
    stun_remaining: int = 0
    cooldown_remaining: int = 0
    committed_action: Optional["Action"] = None
    commitment_remaining: int = 0

    @property
    def hp_max(self) -> float:
        return self.character.hp

    @property
    def hp_pct(self) -> float:
        return self.hp / self.hp_max if self.hp_max > 0 else 0.0

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def is_stunned(self) -> bool:
        return self.stun_remaining > 0

    @property
    def attack_ready(self) -> bool:
        return self.cooldown_remaining == 0


@dataclass
class TimerSnapshot:
    stun: int
    cooldown: int

    @classmethod
    def of(cls, fighter: FighterState) -> TimerSnapshot:
        return cls(stun=fighter.stun_remaining, cooldown=fighter.cooldown_remaining)


@dataclass
class CombatResult:
    winner: int
    ticks: int
    ko: bool
    hp_remaining: Tuple[float, float]

    @property
    def loser(self) -> int:
        return 1 - self.winner


@dataclass
class ActionLog:
    action_counts: Tuple[Dict[int, int], Dict[int, int]]
    active_ticks: Tuple[int, int]
    stun_applied: Tuple[int, int]


# ─────────────────────────────────────────────────────────────────────────────
# Internos do loop
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ActionTracker:
    action_counts: List[Dict[int, int]] = field(
        default_factory=lambda: [{a: 0 for a in Action}, {a: 0 for a in Action}]
    )
    active_ticks: List[int] = field(default_factory=lambda: [0, 0])
    stun_applied: List[int] = field(default_factory=lambda: [0, 0])


@dataclass
class CombatState:
    fighters: List[FighterState]
    positions: List[float]
    end_tick: int = MAX_TICKS
    tracker: Optional[ActionTracker] = None


# ─────────────────────────────────────────────────────────────────────────────
# Lógica de combate
# ─────────────────────────────────────────────────────────────────────────────


def _soft_policy(char: Character) -> Action:
    weights = [char.w_aggressiveness, char.w_retreat, char.w_defend]
    if sum(weights) <= 0.0:
        return Action.DEFEND
    return random.choices(
        [Action.ADVANCE, Action.RETREAT, Action.DEFEND],
        weights=weights,
        k=1,
    )[0]


def _choose_action(
    me: FighterState,
    enemy: FighterState,
    distance: float,
    pos_me: float,
) -> Action:
    char = me.character
    in_my_range = distance <= char.range_

    if in_my_range and me.attack_ready:
        me.commitment_remaining = 0
        return Action.ATTACK

    cornered = pos_me < WALL_CORNER_THRESHOLD or pos_me > FIELD_SIZE - WALL_CORNER_THRESHOLD
    if not in_my_range or cornered:
        me.commitment_remaining = 0
        return Action.ADVANCE

    if me.commitment_remaining > 0 and me.committed_action is not None:
        me.commitment_remaining -= 1
        return me.committed_action

    me.committed_action = _soft_policy(char)
    me.commitment_remaining = ACTION_PERSISTENCE_SUBTICKS
    return me.committed_action


def _resolve_attack(
    attacker: Character,
    defender_state: FighterState,
    defender_is_defending: bool,
    distance: float,
) -> Tuple[float, int, float]:
    if distance > attacker.range_:
        return 0.0, 0, 0.0

    dmg = attacker.damage * (1.0 - defender_state.character.defense)
    if defender_is_defending:
        dmg *= DEFEND_DAMAGE_REDUCTION

    stun_ticks = max(
        0,
        round(attacker.stun * TICK_SCALE) - int(defender_state.character.recovery),
    )
    stun_ticks = min(
        stun_ticks, round(STUN_CAP_MULTIPLIER * attacker.attack_cooldown * TICK_SCALE)
    )

    return dmg, stun_ticks, attacker.knockback


def _decrement_stale_timers(fighter: FighterState, snapshot: TimerSnapshot) -> None:
    if fighter.stun_remaining <= snapshot.stun:
        fighter.stun_remaining = max(0, fighter.stun_remaining - 1)
    if fighter.cooldown_remaining <= snapshot.cooldown:
        fighter.cooldown_remaining = max(0, fighter.cooldown_remaining - 1)


def _winner_by_hp_pct(fighters: List[FighterState]) -> int:
    return 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1


def _combat_result(fighters: List[FighterState], end_tick: int) -> CombatResult:
    hp_a, hp_b = max(0.0, fighters[0].hp), max(0.0, fighters[1].hp)
    alive_a, alive_b = fighters[0].is_alive, fighters[1].is_alive

    if alive_a and not alive_b:
        return CombatResult(0, end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    if alive_b and not alive_a:
        return CombatResult(1, end_tick, ko=True, hp_remaining=(hp_a, hp_b))

    ko = not (alive_a and alive_b)
    return CombatResult(
        _winner_by_hp_pct(fighters), end_tick, ko=ko, hp_remaining=(hp_a, hp_b)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fases do combate
# ─────────────────────────────────────────────────────────────────────────────


def _init_combat_state(
    char_a: Character, char_b: Character, track_actions: bool
) -> CombatState:
    return CombatState(
        fighters=[
            FighterState(character=char_a, hp=char_a.hp),
            FighterState(character=char_b, hp=char_b.hp),
        ],
        positions=[
            (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,
            (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,
        ],
        tracker=ActionTracker() if track_actions else None,
    )


def _phase_choose_actions(state: CombatState) -> List[Optional[Action]]:
    distance = abs(state.positions[1] - state.positions[0])
    actions: List[Optional[Action]] = []
    for i in range(2):
        if state.fighters[i].is_stunned:
            actions.append(None)
            continue
        a = _choose_action(
            state.fighters[i],
            state.fighters[1 - i],
            distance,
            state.positions[i],
        )
        actions.append(a)
        if state.tracker:
            state.tracker.active_ticks[i] += 1
            state.tracker.action_counts[i][a] += 1
    return actions


def _phase_apply_movement(state: CombatState, actions: List[Optional[Action]]) -> None:
    for i in range(2):
        if actions[i] not in (Action.ADVANCE, Action.RETREAT):
            continue
        speed = state.fighters[i].character.speed / TICK_SCALE
        direction = 1.0 if state.positions[i] < state.positions[1 - i] else -1.0
        if actions[i] == Action.ADVANCE:
            state.positions[i] = max(
                0.0, min(FIELD_SIZE, state.positions[i] + direction * speed)
            )
        else:
            state.positions[i] = max(
                0.0, min(FIELD_SIZE, state.positions[i] - direction * speed)
            )


def _phase_resolve_attacks(state: CombatState, actions: List[Optional[Action]]) -> None:
    distance = abs(state.positions[1] - state.positions[0])
    defending = [a == Action.DEFEND for a in actions]

    for attacker_idx in range(2):
        if actions[attacker_idx] != Action.ATTACK:
            continue
        if not state.fighters[attacker_idx].attack_ready:
            continue

        defender_idx = 1 - attacker_idx
        dmg, stun, kb = _resolve_attack(
            attacker=state.fighters[attacker_idx].character,
            defender_state=state.fighters[defender_idx],
            defender_is_defending=defending[defender_idx],
            distance=distance,
        )

        if dmg > 0:
            state.fighters[defender_idx].hp = max(
                0.0, state.fighters[defender_idx].hp - dmg
            )

            if stun > state.fighters[defender_idx].stun_remaining:
                state.fighters[defender_idx].stun_remaining = stun
            if state.tracker:
                state.tracker.stun_applied[attacker_idx] += stun

            kb_dir = (
                1.0
                if state.positions[defender_idx] >= state.positions[attacker_idx]
                else -1.0
            )
            state.positions[defender_idx] = max(
                0.0, min(FIELD_SIZE, state.positions[defender_idx] + kb_dir * kb)
            )
            state.fighters[attacker_idx].cooldown_remaining = round(
                state.fighters[attacker_idx].character.attack_cooldown * TICK_SCALE
            )


def _phase_decrement_timers(
    fighters: List[FighterState], snapshots: List[TimerSnapshot]
) -> None:
    for fighter, snapshot in zip(fighters, snapshots):
        _decrement_stale_timers(fighter, snapshot)


def _build_output(state: CombatState) -> Tuple[CombatResult, Optional[ActionLog]]:
    result = _combat_result(state.fighters, state.end_tick)
    if state.tracker is None:
        return result, None
    t = state.tracker
    log = ActionLog(
        action_counts=(t.action_counts[0], t.action_counts[1]),
        active_ticks=(t.active_ticks[0], t.active_ticks[1]),
        stun_applied=(t.stun_applied[0], t.stun_applied[1]),
    )
    return result, log


def _run_combat_loop(
    char_a: Character,
    char_b: Character,
    *,
    track_actions: bool = False,
) -> Tuple[CombatResult, Optional[ActionLog]]:
    state = _init_combat_state(char_a, char_b, track_actions)

    for tick in range(MAX_TICKS):
        if not state.fighters[0].is_alive or not state.fighters[1].is_alive:
            state.end_tick = tick
            break

        actions = _phase_choose_actions(state)
        _phase_apply_movement(state, actions)
        pre_snapshots = [TimerSnapshot.of(f) for f in state.fighters]
        _phase_resolve_attacks(state, actions)
        _phase_decrement_timers(state.fighters, pre_snapshots)

    return _build_output(state)


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────


def simulate_combat(char_a: Character, char_b: Character) -> CombatResult:
    result, _ = _run_combat_loop(char_a, char_b)
    return result


def simulate_combat_detailed(
    char_a: Character, char_b: Character
) -> Tuple[CombatResult, ActionLog]:
    result, log = _run_combat_loop(char_a, char_b, track_actions=True)
    return result, log
