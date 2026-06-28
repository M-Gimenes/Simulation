"""
Simulação de combate tick a tick 1v1.

Toda a lógica de combate vive em uma única função JIT-compilada pelo Numba.
Há duas variantes que compartilham a mesma estrutura:

    _simulate_combat_jit         — fast path sem rastreio; usado pelo fitness
    _simulate_combat_traced_jit  — escreve estado tick-a-tick em arrays NumPy

API pública:
    simulate_combat(char_a, char_b)          -> CombatResult
    simulate_combat_detailed(char_a, char_b) -> (CombatResult, ActionLog)
    simulate_combat_traced(char_a, char_b)   -> CombatTrace

Tools que precisam instrumentar a luta (viewer, web_viewer, analyze_matchups)
consomem `CombatTrace` em vez de reimplementar o loop em Python — eliminando a
fonte tradicional de divergência entre Python e JIT.

Reprodutibilidade: o JIT usa o RNG interno do Numba, que é **independente** do
`np.random` de nível Python e só pode ser semeado de dentro de um `@njit`. Use
`seed_combat(s)` para torná-lo reprodutível — semear `np.random`/`random` no
Python NÃO afeta o combate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Tuple

import numpy as np
from numba import njit

from .character import Character
from .config import (
    ACTION_PERSISTENCE_SUBTICKS,
    DEFEND_DAMAGE_REDUCTION,
    FIELD_SIZE,
    INITIAL_DISTANCE,
    MAX_TICKS,
    TICK_SCALE,
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


@dataclass
class CombatTrace:
    """
    Registro tick-a-tick de uma luta. Todas as arrays têm shape (T, 2) onde T é
    o número de ticks até o término (`end_tick`). Coluna 0 = personagem A, 1 = B.

    Para arrays "_dealt" e "_applied", o índice da coluna identifica o ATACANTE
    (i.e. damage_dealt[t, 0] é o dano que A causou em B no tick t).
    """
    winner: int
    end_tick: int
    ko: bool
    hp_max: Tuple[float, float]

    pos:             np.ndarray  # (T, 2) float — após movimento + knockback
    hp:              np.ndarray  # (T, 2) float — após dano
    action:          np.ndarray  # (T, 2) int   — Action ou -1 se stunned
    cooldown:        np.ndarray  # (T, 2) int   — ao final do tick
    stun:            np.ndarray  # (T, 2) int   — ao final do tick
    damage_dealt:    np.ndarray  # (T, 2) float — coluna i = dano de i no oponente
    stun_applied:    np.ndarray  # (T, 2) int   — sub-ticks de stun aplicados pelo atacante
    knockback_dealt: np.ndarray  # (T, 2) float — knockback aplicado pelo atacante


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
    field_size, initial_distance,
    max_ticks, tick_scale,
    defend_red, persist,
):
    a_hp_max = a_attrs[0]; a_dmg = a_attrs[1]; a_cd = a_attrs[2]
    a_range = a_attrs[3]; a_speed = a_attrs[4]; a_stun = a_attrs[5]; a_kb = a_attrs[6]
    a_wret = a_w[0]; a_wdef = a_w[1]; a_wagg = a_w[2]

    b_hp_max = b_attrs[0]; b_dmg = b_attrs[1]; b_cd = b_attrs[2]
    b_range = b_attrs[3]; b_speed = b_attrs[4]; b_stun = b_attrs[5]; b_kb = b_attrs[6]
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
            if not in_range:
                action_a = 1               # ADVANCE — neutral game (aproxima)
                persist_a = 0
            else:
                if persist_a == 0:
                    tot = a_wagg + a_wret + a_wdef
                    if tot <= 0.0:
                        commit_a = 2       # GUARDA (fallback)
                    else:
                        r = np.random.random() * tot
                        if r < a_wagg:
                            commit_a = 0   # FRENTE
                        elif r < a_wagg + a_wret:
                            commit_a = 1   # RECUAR
                        else:
                            commit_a = 2   # GUARDA
                    persist_a = persist
                persist_a -= 1
                if commit_a == 0:                      # FRENTE
                    action_a = 0 if cd_rem_a == 0 else 1   # ATTACK senão ADVANCE (pressão)
                elif commit_a == 1:                    # RECUAR
                    step = a_speed / tick_scale
                    can_back = (pos_a - step >= 0.0) if pos_a < pos_b else (pos_a + step <= field_size)
                    action_a = 2 if can_back else 3        # RETREAT senão DEFEND (encurralado)
                else:                                  # GUARDA
                    action_a = 3
            active_ticks[0] += 1
            action_counts[0, action_a] += 1

        if stun_rem_b > 0:
            action_b = -1
        else:
            in_range = distance <= b_range
            if not in_range:
                action_b = 1
                persist_b = 0
            else:
                if persist_b == 0:
                    tot = b_wagg + b_wret + b_wdef
                    if tot <= 0.0:
                        commit_b = 2
                    else:
                        r = np.random.random() * tot
                        if r < b_wagg:
                            commit_b = 0
                        elif r < b_wagg + b_wret:
                            commit_b = 1
                        else:
                            commit_b = 2
                    persist_b = persist
                persist_b -= 1
                if commit_b == 0:
                    action_b = 0 if cd_rem_b == 0 else 1
                elif commit_b == 1:
                    step = b_speed / tick_scale
                    can_back = (pos_b - step >= 0.0) if pos_b < pos_a else (pos_b + step <= field_size)
                    action_b = 2 if can_back else 3
                else:
                    action_b = 3
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
            dmg = a_dmg
            if action_b == 3:
                dmg *= defend_red
            stun_t = round(a_stun * round(a_cd * tick_scale))  # fração × cooldown_subticks; < cooldown por bound

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
            dmg = b_dmg
            if action_a == 3:
                dmg *= defend_red
            stun_t = round(b_stun * round(b_cd * tick_scale))  # fração × cooldown_subticks; < cooldown por bound

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


# ─────────────────────────────────────────────────────────────────────────────
# Núcleo JIT — variante com rastreio tick-a-tick
# ─────────────────────────────────────────────────────────────────────────────
#
# Mesmo loop e mesmas regras do `_simulate_combat_jit`; a única diferença é que
# o estado relevante de cada tick é gravado em arrays NumPy. Tools que precisam
# instrumentar a luta consomem essas arrays em vez de reimplementar o loop.


@njit(cache=True)
def _simulate_combat_traced_jit(
    a_attrs, a_w, b_attrs, b_w,
    field_size, initial_distance,
    max_ticks, tick_scale,
    defend_red, persist,
):
    a_hp_max = a_attrs[0]; a_dmg = a_attrs[1]; a_cd = a_attrs[2]
    a_range = a_attrs[3]; a_speed = a_attrs[4]; a_stun = a_attrs[5]; a_kb = a_attrs[6]
    a_wret = a_w[0]; a_wdef = a_w[1]; a_wagg = a_w[2]

    b_hp_max = b_attrs[0]; b_dmg = b_attrs[1]; b_cd = b_attrs[2]
    b_range = b_attrs[3]; b_speed = b_attrs[4]; b_stun = b_attrs[5]; b_kb = b_attrs[6]
    b_wret = b_w[0]; b_wdef = b_w[1]; b_wagg = b_w[2]

    hp_a = a_hp_max
    hp_b = b_hp_max
    pos_a = (field_size - initial_distance) / 2.0
    pos_b = (field_size + initial_distance) / 2.0

    stun_rem_a = 0; stun_rem_b = 0
    cd_rem_a = 0; cd_rem_b = 0
    commit_a = -1; commit_b = -1
    persist_a = 0; persist_b = 0

    pos_arr      = np.zeros((max_ticks, 2), dtype=np.float64)
    hp_arr       = np.zeros((max_ticks, 2), dtype=np.float64)
    action_arr   = np.full((max_ticks, 2), -1, dtype=np.int64)
    cd_arr       = np.zeros((max_ticks, 2), dtype=np.int64)
    stun_arr     = np.zeros((max_ticks, 2), dtype=np.int64)
    dmg_dealt    = np.zeros((max_ticks, 2), dtype=np.float64)
    stun_dealt   = np.zeros((max_ticks, 2), dtype=np.int64)
    kb_dealt     = np.zeros((max_ticks, 2), dtype=np.float64)

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
            if not in_range:
                action_a = 1               # ADVANCE — neutral game (aproxima)
                persist_a = 0
            else:
                if persist_a == 0:
                    tot = a_wagg + a_wret + a_wdef
                    if tot <= 0.0:
                        commit_a = 2       # GUARDA (fallback)
                    else:
                        r = np.random.random() * tot
                        if r < a_wagg:
                            commit_a = 0   # FRENTE
                        elif r < a_wagg + a_wret:
                            commit_a = 1   # RECUAR
                        else:
                            commit_a = 2   # GUARDA
                    persist_a = persist
                persist_a -= 1
                if commit_a == 0:                      # FRENTE
                    action_a = 0 if cd_rem_a == 0 else 1   # ATTACK senão ADVANCE (pressão)
                elif commit_a == 1:                    # RECUAR
                    step = a_speed / tick_scale
                    can_back = (pos_a - step >= 0.0) if pos_a < pos_b else (pos_a + step <= field_size)
                    action_a = 2 if can_back else 3        # RETREAT senão DEFEND (encurralado)
                else:                                  # GUARDA
                    action_a = 3

        if stun_rem_b > 0:
            action_b = -1
        else:
            in_range = distance <= b_range
            if not in_range:
                action_b = 1
                persist_b = 0
            else:
                if persist_b == 0:
                    tot = b_wagg + b_wret + b_wdef
                    if tot <= 0.0:
                        commit_b = 2
                    else:
                        r = np.random.random() * tot
                        if r < b_wagg:
                            commit_b = 0
                        elif r < b_wagg + b_wret:
                            commit_b = 1
                        else:
                            commit_b = 2
                    persist_b = persist
                persist_b -= 1
                if commit_b == 0:
                    action_b = 0 if cd_rem_b == 0 else 1
                elif commit_b == 1:
                    step = b_speed / tick_scale
                    can_back = (pos_b - step >= 0.0) if pos_b < pos_a else (pos_b + step <= field_size)
                    action_b = 2 if can_back else 3
                else:
                    action_b = 3

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

        if action_a == 0 and cd_rem_a == 0 and distance <= a_range:
            dmg = a_dmg
            if action_b == 3:
                dmg *= defend_red
            stun_t = round(a_stun * round(a_cd * tick_scale))  # fração × cooldown_subticks; < cooldown por bound

            hp_b = hp_b - dmg
            if hp_b < 0.0:
                hp_b = 0.0
            applied = 0
            if stun_t > stun_rem_b:
                stun_rem_b = stun_t
                applied = stun_t
            kb_dir = 1.0 if pos_b >= pos_a else -1.0
            new_pos = pos_b + kb_dir * a_kb
            if new_pos < 0.0:
                new_pos = 0.0
            elif new_pos > field_size:
                new_pos = field_size
            pos_b = new_pos
            cd_rem_a = round(a_cd * tick_scale)

            dmg_dealt[tick, 0]  = dmg
            stun_dealt[tick, 0] = applied
            kb_dealt[tick, 0]   = a_kb

        if action_b == 0 and cd_rem_b == 0 and distance <= b_range:
            dmg = b_dmg
            if action_a == 3:
                dmg *= defend_red
            stun_t = round(b_stun * round(b_cd * tick_scale))  # fração × cooldown_subticks; < cooldown por bound

            hp_a = hp_a - dmg
            if hp_a < 0.0:
                hp_a = 0.0
            applied = 0
            if stun_t > stun_rem_a:
                stun_rem_a = stun_t
                applied = stun_t
            kb_dir = 1.0 if pos_a >= pos_b else -1.0
            new_pos = pos_a + kb_dir * b_kb
            if new_pos < 0.0:
                new_pos = 0.0
            elif new_pos > field_size:
                new_pos = field_size
            pos_a = new_pos
            cd_rem_b = round(b_cd * tick_scale)

            dmg_dealt[tick, 1]  = dmg
            stun_dealt[tick, 1] = applied
            kb_dealt[tick, 1]   = b_kb

        # ── Decremento de timers stale ───────────────────────────────────────
        if stun_rem_a <= pre_stun_a:
            stun_rem_a = max(0, stun_rem_a - 1)
        if cd_rem_a <= pre_cd_a:
            cd_rem_a = max(0, cd_rem_a - 1)
        if stun_rem_b <= pre_stun_b:
            stun_rem_b = max(0, stun_rem_b - 1)
        if cd_rem_b <= pre_cd_b:
            cd_rem_b = max(0, cd_rem_b - 1)

        # ── Snapshot do estado pós-tick ──────────────────────────────────────
        pos_arr[tick, 0]  = pos_a;       pos_arr[tick, 1]  = pos_b
        hp_arr[tick, 0]   = hp_a;        hp_arr[tick, 1]   = hp_b
        action_arr[tick, 0] = action_a;  action_arr[tick, 1] = action_b
        cd_arr[tick, 0]   = cd_rem_a;    cd_arr[tick, 1]   = cd_rem_b
        stun_arr[tick, 0] = stun_rem_a;  stun_arr[tick, 1] = stun_rem_b

    alive_a = hp_a > 0.0
    alive_b = hp_b > 0.0
    ko = 0 if (alive_a and alive_b) else 1
    if alive_a and not alive_b:
        winner = 0
    elif alive_b and not alive_a:
        winner = 1
    else:
        a_pct = hp_a / a_hp_max if a_hp_max > 0.0 else 0.0
        b_pct = hp_b / b_hp_max if b_hp_max > 0.0 else 0.0
        winner = 0 if a_pct >= b_pct else 1

    return (
        winner, end_tick, ko,
        pos_arr[:end_tick],
        hp_arr[:end_tick],
        action_arr[:end_tick],
        cd_arr[:end_tick],
        stun_arr[:end_tick],
        dmg_dealt[:end_tick],
        stun_dealt[:end_tick],
        kb_dealt[:end_tick],
    )


@njit(cache=True)
def _seed_jit(s):
    np.random.seed(s)


def seed_combat(seed: int) -> None:
    """Semeia o RNG interno do Numba — única forma de tornar o combate
    reprodutível. `np.random.seed`/`random.seed` no Python não afetam o JIT."""
    _seed_jit(int(seed) & 0x7FFFFFFF)


def _run_jit(char_a: Character, char_b: Character):
    return _simulate_combat_jit(
        np.asarray(char_a.attributes, dtype=np.float64),
        np.asarray(char_a.weights, dtype=np.float64),
        np.asarray(char_b.attributes, dtype=np.float64),
        np.asarray(char_b.weights, dtype=np.float64),
        float(FIELD_SIZE), float(INITIAL_DISTANCE),
        int(MAX_TICKS), float(TICK_SCALE),
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


def simulate_combat_traced(char_a: Character, char_b: Character) -> CombatTrace:
    """Roda o combate registrando estado tick-a-tick. Mais lento que
    `simulate_combat` por causa das alocações de array — usar apenas em tools."""
    winner, end_tick, ko, pos, hp, action, cd, stun, dmg, stun_d, kb = (
        _simulate_combat_traced_jit(
            np.asarray(char_a.attributes, dtype=np.float64),
            np.asarray(char_a.weights,    dtype=np.float64),
            np.asarray(char_b.attributes, dtype=np.float64),
            np.asarray(char_b.weights,    dtype=np.float64),
            float(FIELD_SIZE), float(INITIAL_DISTANCE),
            int(MAX_TICKS), float(TICK_SCALE),
            float(DEFEND_DAMAGE_REDUCTION), int(ACTION_PERSISTENCE_SUBTICKS),
        )
    )
    return CombatTrace(
        winner=int(winner),
        end_tick=int(end_tick),
        ko=bool(ko),
        hp_max=(float(char_a.hp), float(char_b.hp)),
        pos=pos,
        hp=hp,
        action=action,
        cooldown=cd,
        stun=stun,
        damage_dealt=dmg,
        stun_applied=stun_d,
        knockback_dealt=kb,
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
