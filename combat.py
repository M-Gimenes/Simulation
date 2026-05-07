"""
Simulação de combate tick a tick 1v1.

O loop principal é JIT-compilado pelo Numba (`_simulate_combat_jit`) — speedup
~150× sobre Python puro. Os helpers em Python (`_choose_action`, `_resolve_attack`,
`_decrement_stale_timers`, `_soft_policy`) permanecem porque são reutilizados
por scripts que reimplementam o loop com instrumentação extra
(`analyze_matchups.py`, `viewer.py`, `web_viewer.py`).

API pública:
    simulate_combat(char_a, char_b)          -> CombatResult
    simulate_combat_detailed(char_a, char_b) -> (CombatResult, ActionLog)

Reprodutibilidade: o JIT usa `np.random`. Quem precisar de seed estável deve
semear `random` (helpers em Python) **e** `np.random` (JIT) no nível superior.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Optional, Tuple

import numpy as np
from numba import njit

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
# Tipos públicos
# ─────────────────────────────────────────────────────────────────────────────


class Action(IntEnum):
    ATTACK = 0
    ADVANCE = 1
    RETREAT = 2
    DEFEND = 3


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
# Estado mutável usado pelos helpers em Python (analyze_matchups, viewers)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FighterState:
    character: Character
    hp: float
    stun_remaining: int = 0
    cooldown_remaining: int = 0
    committed_action: Optional[Action] = None
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
    def of(cls, fighter: FighterState) -> "TimerSnapshot":
        return cls(stun=fighter.stun_remaining, cooldown=fighter.cooldown_remaining)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers em Python puro (reusados por loops instrumentados externos)
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
    me: FighterState, enemy: FighterState, distance: float, pos_me: float
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


# ─────────────────────────────────────────────────────────────────────────────
# Núcleo JIT — loop tick a tick compilado
# ─────────────────────────────────────────────────────────────────────────────
#
# O JIT sempre rastreia (action_counts, active_ticks, stun_applied) — o
# overhead é negligenciável e elimina a duplicação de implementações.
# Constantes de config viram args (não globais) para que mudanças em config.py
# se propaguem sem invalidar o cache.
#
# Códigos de ação: -1=stunned, 0=ATTACK, 1=ADVANCE, 2=RETREAT, 3=DEFEND
# Retorno: (winner, end_tick, ko, hp_a, hp_b, action_counts, active_ticks, stun_applied)


@njit(cache=True)
def _simulate_combat_jit(
    a_attrs, a_w, b_attrs, b_w,
    field_size, initial_distance, wall_corner,
    max_ticks, tick_scale, stun_cap_mult,
    defend_red, persist,
):
    a_hp_max = a_attrs[0]; a_dmg = a_attrs[1]; a_cd = a_attrs[2]
    a_range = a_attrs[3]; a_speed = a_attrs[4]; a_def = a_attrs[5]
    a_stun = a_attrs[6]; a_kb = a_attrs[7]; a_rec = a_attrs[8]
    a_wret = a_w[0]; a_wdef = a_w[1]; a_wagg = a_w[2]

    b_hp_max = b_attrs[0]; b_dmg = b_attrs[1]; b_cd = b_attrs[2]
    b_range = b_attrs[3]; b_speed = b_attrs[4]; b_def = b_attrs[5]
    b_stun = b_attrs[6]; b_kb = b_attrs[7]; b_rec = b_attrs[8]
    b_wret = b_w[0]; b_wdef = b_w[1]; b_wagg = b_w[2]

    hp_a = a_hp_max
    hp_b = b_hp_max
    pos_a = (field_size - initial_distance) / 2.0
    pos_b = (field_size + initial_distance) / 2.0

    stun_rem_a = 0; stun_rem_b = 0
    cd_rem_a = 0; cd_rem_b = 0
    commit_a = -1; commit_b = -1
    persist_a = 0; persist_b = 0

    action_counts = np.zeros((2, 4), dtype=np.int64)
    active_ticks = np.zeros(2, dtype=np.int64)
    stun_applied = np.zeros(2, dtype=np.int64)

    end_tick = max_ticks

    for tick in range(max_ticks):
        if hp_a <= 0.0 or hp_b <= 0.0:
            end_tick = tick
            break

        distance = abs(pos_b - pos_a)

        # ── Escolha de ações ─────────────────────────────────────────────────
        if stun_rem_a > 0:
            action_a = -1
        else:
            in_range = distance <= a_range
            cornered = (pos_a < wall_corner) or (pos_a > field_size - wall_corner)
            if in_range and cd_rem_a == 0:
                action_a = 0
                persist_a = 0
            elif (not in_range) or cornered:
                action_a = 1
                persist_a = 0
            elif persist_a > 0 and commit_a >= 0:
                action_a = commit_a
                persist_a -= 1
            else:
                tot = a_wagg + a_wret + a_wdef
                if tot <= 0.0:
                    action_a = 3
                else:
                    r = np.random.random() * tot
                    if r < a_wagg:
                        action_a = 1
                    elif r < a_wagg + a_wret:
                        action_a = 2
                    else:
                        action_a = 3
                commit_a = action_a
                persist_a = persist
            active_ticks[0] += 1
            action_counts[0, action_a] += 1

        if stun_rem_b > 0:
            action_b = -1
        else:
            in_range = distance <= b_range
            cornered = (pos_b < wall_corner) or (pos_b > field_size - wall_corner)
            if in_range and cd_rem_b == 0:
                action_b = 0
                persist_b = 0
            elif (not in_range) or cornered:
                action_b = 1
                persist_b = 0
            elif persist_b > 0 and commit_b >= 0:
                action_b = commit_b
                persist_b -= 1
            else:
                tot = b_wagg + b_wret + b_wdef
                if tot <= 0.0:
                    action_b = 3
                else:
                    r = np.random.random() * tot
                    if r < b_wagg:
                        action_b = 1
                    elif r < b_wagg + b_wret:
                        action_b = 2
                    else:
                        action_b = 3
                commit_b = action_b
                persist_b = persist
            active_ticks[1] += 1
            action_counts[1, action_b] += 1

        # ── Movimento ────────────────────────────────────────────────────────
        if action_a == 1 or action_a == 2:
            spd = a_speed / tick_scale
            d = 1.0 if pos_a < pos_b else -1.0
            sign = 1.0 if action_a == 1 else -1.0
            new_pos = pos_a + d * sign * spd
            if new_pos < 0.0:
                new_pos = 0.0
            elif new_pos > field_size:
                new_pos = field_size
            pos_a = new_pos

        if action_b == 1 or action_b == 2:
            spd = b_speed / tick_scale
            d = 1.0 if pos_b < pos_a else -1.0
            sign = 1.0 if action_b == 1 else -1.0
            new_pos = pos_b + d * sign * spd
            if new_pos < 0.0:
                new_pos = 0.0
            elif new_pos > field_size:
                new_pos = field_size
            pos_b = new_pos

        # ── Snapshot dos timers antes dos ataques (decrement-stale) ──────────
        pre_stun_a = stun_rem_a; pre_stun_b = stun_rem_b
        pre_cd_a = cd_rem_a; pre_cd_b = cd_rem_b

        # ── Resolução de ataques ─────────────────────────────────────────────
        distance = abs(pos_b - pos_a)

        # A → B
        if action_a == 0 and cd_rem_a == 0 and distance <= a_range:
            dmg = a_dmg * (1.0 - b_def)
            if action_b == 3:
                dmg *= defend_red
            if dmg > 0.0:
                stun_t = round(a_stun * tick_scale) - int(b_rec)
                if stun_t < 0:
                    stun_t = 0
                cap = round(stun_cap_mult * a_cd * tick_scale)
                if stun_t > cap:
                    stun_t = cap

                hp_b = hp_b - dmg
                if hp_b < 0.0:
                    hp_b = 0.0
                if stun_t > stun_rem_b:
                    stun_rem_b = stun_t
                stun_applied[0] += stun_t
                kb_dir = 1.0 if pos_b >= pos_a else -1.0
                new_pos = pos_b + kb_dir * a_kb
                if new_pos < 0.0:
                    new_pos = 0.0
                elif new_pos > field_size:
                    new_pos = field_size
                pos_b = new_pos
                cd_rem_a = round(a_cd * tick_scale)

        # B → A
        if action_b == 0 and cd_rem_b == 0 and distance <= b_range:
            dmg = b_dmg * (1.0 - a_def)
            if action_a == 3:
                dmg *= defend_red
            if dmg > 0.0:
                stun_t = round(b_stun * tick_scale) - int(a_rec)
                if stun_t < 0:
                    stun_t = 0
                cap = round(stun_cap_mult * b_cd * tick_scale)
                if stun_t > cap:
                    stun_t = cap

                hp_a = hp_a - dmg
                if hp_a < 0.0:
                    hp_a = 0.0
                if stun_t > stun_rem_a:
                    stun_rem_a = stun_t
                stun_applied[1] += stun_t
                kb_dir = 1.0 if pos_a >= pos_b else -1.0
                new_pos = pos_a + kb_dir * b_kb
                if new_pos < 0.0:
                    new_pos = 0.0
                elif new_pos > field_size:
                    new_pos = field_size
                pos_a = new_pos
                cd_rem_b = round(b_cd * tick_scale)

        # ── Decremento de timers stale ───────────────────────────────────────
        if stun_rem_a <= pre_stun_a:
            stun_rem_a = max(0, stun_rem_a - 1)
        if cd_rem_a <= pre_cd_a:
            cd_rem_a = max(0, cd_rem_a - 1)
        if stun_rem_b <= pre_stun_b:
            stun_rem_b = max(0, stun_rem_b - 1)
        if cd_rem_b <= pre_cd_b:
            cd_rem_b = max(0, cd_rem_b - 1)

    # ── Determinar vencedor ──────────────────────────────────────────────────
    alive_a = hp_a > 0.0
    alive_b = hp_b > 0.0

    if alive_a and not alive_b:
        return 0, end_tick, 1, hp_a, hp_b, action_counts, active_ticks, stun_applied
    if alive_b and not alive_a:
        return 1, end_tick, 1, hp_a, hp_b, action_counts, active_ticks, stun_applied

    ko = 0 if (alive_a and alive_b) else 1
    a_pct = hp_a / a_hp_max if a_hp_max > 0.0 else 0.0
    b_pct = hp_b / b_hp_max if b_hp_max > 0.0 else 0.0
    winner = 0 if a_pct >= b_pct else 1
    return winner, end_tick, ko, hp_a, hp_b, action_counts, active_ticks, stun_applied


def _run_jit(char_a: Character, char_b: Character):
    return _simulate_combat_jit(
        np.asarray(char_a.attributes, dtype=np.float64),
        np.asarray(char_a.weights, dtype=np.float64),
        np.asarray(char_b.attributes, dtype=np.float64),
        np.asarray(char_b.weights, dtype=np.float64),
        float(FIELD_SIZE), float(INITIAL_DISTANCE), float(WALL_CORNER_THRESHOLD),
        int(MAX_TICKS), float(TICK_SCALE), float(STUN_CAP_MULTIPLIER),
        float(DEFEND_DAMAGE_REDUCTION), int(ACTION_PERSISTENCE_SUBTICKS),
    )


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────


def simulate_combat(char_a: Character, char_b: Character) -> CombatResult:
    winner, ticks, ko, hp_a, hp_b, _, _, _ = _run_jit(char_a, char_b)
    return CombatResult(
        winner=int(winner),
        ticks=int(ticks),
        ko=bool(ko),
        hp_remaining=(float(hp_a), float(hp_b)),
    )


def simulate_combat_detailed(
    char_a: Character, char_b: Character
) -> Tuple[CombatResult, ActionLog]:
    winner, ticks, ko, hp_a, hp_b, action_counts, active_ticks, stun_applied = (
        _run_jit(char_a, char_b)
    )
    result = CombatResult(
        winner=int(winner),
        ticks=int(ticks),
        ko=bool(ko),
        hp_remaining=(float(hp_a), float(hp_b)),
    )
    log = ActionLog(
        action_counts=(
            {int(a): int(action_counts[0, int(a)]) for a in Action},
            {int(a): int(action_counts[1, int(a)]) for a in Action},
        ),
        active_ticks=(int(active_ticks[0]), int(active_ticks[1])),
        stun_applied=(int(stun_applied[0]), int(stun_applied[1])),
    )
    return result, log
