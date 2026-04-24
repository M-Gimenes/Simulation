"""
Simulação de combate tick a tick entre dois personagens.

Campo: 100 unidades, distância inicial 50 (config.INITIAL_DISTANCE).
Resolução simultânea — ambos escolhem e executam ação no mesmo tick.

Fluxo por tick:
  1. Cada lutador escolhe ação via sistema de prioridade.
     Personagem stunado perde a ação.
  2. Movimento aplicado (ADVANCE / RETREAT).
  3. Ataques resolvidos simultaneamente.
  4. Timers decrementados — apenas timers não recém-setados neste tick.

Semântica dos timers:
  O decremento ocorre no FINAL do tick, após os ataques.
  Timers recém-definidos por um ataque NÃO são decrementados no mesmo tick.
  cooldown=1 → atacante fica bloqueado por 1 tick (ataca a cada 2 ticks).
  stun=1     → alvo perde exatamente 1 tick de ação.

Condições de vitória:
  KO: HP chega a 0.
  Timer: ao esgotar MAX_TICKS, vence quem tem maior HP percentual.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from character import Character
from config import (
    ACTION_EPSILON,
    DAMAGE_VARIANCE,
    DEFEND_DAMAGE_REDUCTION,
    FIELD_SIZE,
    INITIAL_DISTANCE,
    MAX_TICKS,
    RETREAT_ZONE_FACTOR,
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
    """Captura os timers de um lutador antes da fase de ataque."""

    stun: int
    cooldown: int

    @classmethod
    def of(cls, fighter: FighterState) -> TimerSnapshot:
        return cls(stun=fighter.stun_remaining, cooldown=fighter.cooldown_remaining)


@dataclass
class CombatResult:
    winner: int  # 0 = char_a, 1 = char_b
    ticks: int
    ko: bool  # True = KO, False = timer
    hp_remaining: Tuple[float, float]

    @property
    def loser(self) -> int:
        return 1 - self.winner


@dataclass
class ActionLog:
    """
    Distribuição de ações e stun por lutador em um único combate.
    stun_applied é o stun bruto gerado — proxy de pressão, não de stun efetivamente sofrido.
    """

    action_counts: Tuple[Dict[int, int], Dict[int, int]]
    active_ticks: Tuple[int, int]
    stun_applied: Tuple[int, int]


# ─────────────────────────────────────────────────────────────────────────────
# Internos do loop
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ActionTracker:
    """Acumula estatísticas de ações durante o combate para produzir um ActionLog."""

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


def _choose_action(
    me_state: FighterState,
    enemy_state: FighterState,
    distance: float,
    pos_me: float = 50.0,
) -> Action:
    """
    Prioridades (maior para menor):
      1. ATTACK  — em range e pronto.
      2. Sob ameaça (inimigo em range, pronto, não stunado):
           w_aggressiveness dominante → ADVANCE
           w_retreat > w_defend       → RETREAT
           caso contrário             → DEFEND
      3. ADVANCE — fora de range ou encurralado.
      4. DEFEND  — aguarda cooldown sem ameaça ativa.
    """
    me = me_state.character
    enemy = enemy_state.character

    in_range_me = distance <= me.range_
    ready_me = me_state.attack_ready
    ready_en = (
        enemy_state.attack_ready
        and not enemy_state.is_stunned
        and distance <= enemy.range_
    )

    can_hit = in_range_me and ready_me
    cornered = (
        pos_me < WALL_CORNER_THRESHOLD or pos_me > FIELD_SIZE - WALL_CORNER_THRESHOLD
    )
    in_threat = ready_en and distance < RETREAT_ZONE_FACTOR * enemy.range_

    if can_hit:
        return Action.ATTACK

    if in_threat:
        if me.w_aggressiveness > me.w_retreat and me.w_aggressiveness > me.w_defend:
            return Action.ADVANCE
        if me.w_retreat > me.w_defend:
            return Action.RETREAT
        return Action.DEFEND

    if not in_range_me or cornered:
        return Action.ADVANCE

    return Action.DEFEND


def _resolve_attack(
    attacker: Character,
    defender_state: FighterState,
    defender_is_defending: bool,
    distance: float,
) -> Tuple[float, int, float]:
    """
    Retorna (damage, stun_sub_ticks, knockback). Retorna (0, 0, 0) se fora de range.
    Stun em sub-ticks: round(stun * TICK_SCALE * (1 - recovery)).
    """
    if distance > attacker.range_:
        return 0.0, 0, 0.0

    variance = random.uniform(1.0 - DAMAGE_VARIANCE, 1.0 + DAMAGE_VARIANCE)
    dmg = attacker.damage * (1.0 - defender_state.character.defense) * variance
    if defender_is_defending:
        dmg *= DEFEND_DAMAGE_REDUCTION

    stun_ticks = max(
        0, round(attacker.stun * TICK_SCALE * (1.0 - defender_state.character.recovery))
    )
    # Cap: STUN_CAP_MULTIPLIER × cooldown do atacante.
    # Com multiplier=2 permite 1 hit extra durante o stun (combo chaining).
    stun_ticks = min(
        stun_ticks, round(STUN_CAP_MULTIPLIER * attacker.attack_cooldown * TICK_SCALE)
    )

    return dmg, stun_ticks, attacker.knockback


def _tick_timers(fighter: FighterState, snapshot: TimerSnapshot) -> None:
    """Decrementa apenas timers que não foram recém-setados por um ataque neste tick."""
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

    # Ambos vivos (timer) ou ambos mortos no mesmo tick — desempate por HP%
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
        else:
            if ACTION_EPSILON > 0.0 and random.random() < ACTION_EPSILON:
                a = random.choice(list(Action))
            else:
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
        _tick_timers(fighter, snapshot)


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
    """Registra distribuição de ações e stun aplicado. Usado pelo archetype_validator."""
    result, log = _run_combat_loop(char_a, char_b, track_actions=True)
    return result, log
