"""
Simulação de combate tick a tick entre dois personagens.

Campo: 100 unidades, distância inicial 50 (config.INITIAL_DISTANCE).
Resolução simultânea — ambos escolhem e executam ação no mesmo tick.

Fluxo por tick:
  1. Cada lutador escolhe ação via softmax scoring.
     (personagem stunado perde a ação)
  2. Movimento aplicado (ADVANCE / RETREAT) — ambos alteram a distância.
  3. Ataques resolvidos simultaneamente.
     Após atacar, o atacante entra em cooldown por round(attack_cooldown) ticks.
  4. Decrementam cooldown_remaining e stun_remaining — apenas timers não recém-setados.
  5. Verificação de vitória.

Attack cooldown e stun (determinísticos):
  O decremento ocorre no FINAL do tick, após os ataques.
  Timers recém-definidos por um ataque NÃO são decrementados no mesmo tick.
  Isso garante que cooldown=1 e stun=1 são valores mínimos significativos:
    - cooldown=1 → atacante fica bloqueado por 1 tick (ataca a cada 2 ticks)
    - stun=1     → alvo perde exatamente 1 tick de ação

Condições de vitória:
  - KO: HP chega a 0.
  - Timer: ao esgotar MAX_TICKS, vence quem tem maior HP percentual.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from character import Character
from config import (
    ACTION_EPSILON,
    DAMAGE_VARIANCE,
    FIELD_SIZE,
    INITIAL_DISTANCE,
    MAX_TICKS,
    RETREAT_ZONE_FACTOR,
    STUN_CAP_MULTIPLIER,
    TICK_SCALE,
    WALL_CORNER_THRESHOLD,
)

_USE_EPSILON = ACTION_EPSILON > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Ações
# ─────────────────────────────────────────────────────────────────────────────


class Action:
    ATTACK = 0
    ADVANCE = 1
    RETREAT = 2
    DEFEND = 3


# ─────────────────────────────────────────────────────────────────────────────
# Estado interno de um lutador
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FighterState:
    character: Character
    hp: float
    stun_remaining: int = 0
    cooldown_remaining: int = 0  # ticks até poder atacar novamente

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


# ─────────────────────────────────────────────────────────────────────────────
# Resultado do combate
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CombatResult:
    winner: int  # 0 = char_a, 1 = char_b
    ticks: int  # duração do combate
    ko: bool  # True = KO, False = timer
    hp_remaining: Tuple[float, float]  # HP final de cada lutador

    @property
    def loser(self) -> int:
        return 1 - self.winner


# ─────────────────────────────────────────────────────────────────────────────
# Sistema de decisão — Prioridade
# ─────────────────────────────────────────────────────────────────────────────


def _choose_action(
    me_state: FighterState,
    enemy_state: FighterState,
    distance: float,
    pos_me: float = 50.0,
) -> int:
    """
    Escolhe ação via sistema de prioridade.

    Modela um jogador experiente: decisões determinísticas baseadas no estado atual.
    Os pesos w_* controlam limiares comportamentais — não probabilidades.

    Prioridades:
      1. ATTACK  — sempre que possível (em range + pronto).
      2. Sob ameaça (inimigo pronto e se aproximando, sem poder contra-atacar):
           w_aggressiveness >= 0.7 → ADVANCE  (pressiona mesmo sob risco)
           w_retreat > w_defend    → RETREAT  (kite / criar distância)
           w_defend  >= w_retreat  → DEFEND   (absorver e punir na oportunidade)
      3. ADVANCE — fora de range ou encurralado (crossing).
      4. DEFEND  — default: em range, em cooldown, sem ameaça ativa.

    Pesos relevantes por decisão:
      w_aggressiveness : separa quem pressiona (>=0.7) de quem recua/absorve (<0.7)
      w_retreat / w_defend : escolha defensiva quando ameaçado e sem poder atacar
    """
    me    = me_state.character
    enemy = enemy_state.character

    in_range_me = distance <= me.range_
    ready_me    = me_state.attack_ready
    ready_en    = enemy_state.attack_ready and not enemy_state.is_stunned

    can_hit  = in_range_me and ready_me
    cornered = pos_me < WALL_CORNER_THRESHOLD or pos_me > FIELD_SIZE - WALL_CORNER_THRESHOLD

    # Zona de ameaça proativa: inimigo se aproximando e pronto para atacar
    zone     = RETREAT_ZONE_FACTOR * enemy.range_
    in_threat = ready_en and distance < zone

    # ── Ação por prioridade ───────────────────────────────────────────────────
    # Modela um jogador experiente: decisões determinísticas baseadas em situação.
    # w_* controlam limiares, não probabilidades. Mesmo estado → mesma ação.

    # 1. Atacar — prioridade máxima
    if can_hit:
        return Action.ATTACK

    # 2. Resposta à ameaça (inimigo pronto e se aproximando, não consigo contra-atacar)
    if in_threat:
        if me.w_aggressiveness > me.w_retreat and me.w_aggressiveness > me.w_defend:
            return Action.ADVANCE   # instinto ofensivo supera os defensivos
        if me.w_retreat > me.w_defend:
            return Action.RETREAT   # kite / criar distância
        return Action.DEFEND        # absorver e esperar oportunidade

    # 3. Fechar distância (ou crossing se encurralado)
    if not in_range_me or cornered:
        return Action.ADVANCE

    # 4. Default: em range, em cooldown, sem ameaça — aguarda próximo ataque
    return Action.DEFEND


# ─────────────────────────────────────────────────────────────────────────────
# Resolução de ataque
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_attack(
    attacker: Character,
    defender_state: FighterState,
    defender_is_defending: bool,
    distance: float,
) -> Tuple[float, int, float]:
    """
    Resolve um ataque. Chamado apenas quando o atacante está com attack_ready=True.
    Retorna (dano_causado, stun_sub_ticks_aplicados, knockback_unidades).
    Retorna (0, 0, 0) se fora de alcance.

    Stun e cooldown usam TICK_SCALE para resolução sub-tick:
      stun_sub   = round(stun * TICK_SCALE * (1 - recovery))
      cooldown   = round(attack_cooldown * TICK_SCALE)
    """
    if distance > attacker.range_:
        return 0.0, 0, 0.0

    def_factor = 1.0 - defender_state.character.defense  # defense já em 0–1
    variance   = random.uniform(1.0 - DAMAGE_VARIANCE, 1.0 + DAMAGE_VARIANCE)
    dmg = attacker.damage * def_factor * variance
    if defender_is_defending:
        dmg *= 0.2

    stun_ticks = max(
        0,
        round(attacker.stun * TICK_SCALE * (1.0 - defender_state.character.recovery)),
    )

    # Cap de stun: limita a STUN_CAP_MULTIPLIER × cooldown do atacante.
    # Com multiplier=2, permite 1 hit extra durante stun (combo chaining).
    stun_ticks = min(stun_ticks, round(STUN_CAP_MULTIPLIER * attacker.attack_cooldown * TICK_SCALE))

    knockback_units = attacker.knockback  # escala natural: unidades de campo

    return dmg, stun_ticks, knockback_units


# ─────────────────────────────────────────────────────────────────────────────
# Simulação principal
# ─────────────────────────────────────────────────────────────────────────────


def simulate_combat(char_a: Character, char_b: Character) -> CombatResult:
    """
    Simula um combate tick a tick entre char_a (índice 0) e char_b (índice 1).

    Campo com paredes em 0 e FIELD_SIZE. Cada lutador tem posição absoluta.
    Crossing automático: quando o avanço ultrapassa o oponente, o lutador
    aparece do outro lado — a direção de avanço/recuo inverte no tick seguinte.
    Knockback empurra o defensor na direção correta (para longe do atacante).
    """
    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    # Posições absolutas: lutador 0 começa à esquerda, lutador 1 à direita
    pos = [
        (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,   # = 25.0
        (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,   # = 75.0
    ]
    end_tick = MAX_TICKS

    for tick in range(MAX_TICKS):

        distance = abs(pos[1] - pos[0])

        # ── Verificação antecipada de KO ──────────────────────────────────
        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            break

        # ── Fase 1: Escolha de ação ───────────────────────────────────────
        # Personagem stunado perde a ação neste tick.
        # Com probabilidade ACTION_EPSILON, executa ação aleatória (erro de execução).
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            elif _USE_EPSILON and random.random() < ACTION_EPSILON:
                actions.append(random.randint(0, 3))
            else:
                actions.append(_choose_action(fighters[i], fighters[1 - i], distance, pos[i]))

        # ── Fase 2: Movimento ─────────────────────────────────────────────
        # direction = +1 se está à esquerda do oponente (avança para direita)
        #           = -1 se está à direita (avança para esquerda)
        for i in range(2):
            if actions[i] not in (Action.ADVANCE, Action.RETREAT):
                continue
            # Movimento por sub-tick: preserva a relação original entre
            # velocidade e cooldown dividindo pela resolução temporal.
            speed = fighters[i].character.speed / TICK_SCALE
            direction = 1.0 if pos[i] < pos[1 - i] else -1.0
            if actions[i] == Action.ADVANCE:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] + direction * speed))
            else:  # RETREAT
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] - direction * speed))

        # ── Fase 3: Ataques simultâneos ───────────────────────────────────
        distance = abs(pos[1] - pos[0])  # recalcula após movimento
        defending = [a == Action.DEFEND for a in actions]

        # Salva timers pré-ataque: apenas valores existentes antes desta fase
        # são elegíveis para decremento — timers recém-setados ficam intactos.
        pre_stun_0 = fighters[0].stun_remaining
        pre_stun_1 = fighters[1].stun_remaining
        pre_cd_0   = fighters[0].cooldown_remaining
        pre_cd_1   = fighters[1].cooldown_remaining

        for attacker_idx in range(2):
            if actions[attacker_idx] != Action.ATTACK:
                continue
            if not fighters[attacker_idx].attack_ready:
                continue

            defender_idx = 1 - attacker_idx
            dmg, stun, kb = _resolve_attack(
                attacker=fighters[attacker_idx].character,
                defender_state=fighters[defender_idx],
                defender_is_defending=defending[defender_idx],
                distance=distance,
            )

            if dmg > 0:
                fighters[defender_idx].hp = max(0.0, fighters[defender_idx].hp - dmg)

                if stun > fighters[defender_idx].stun_remaining:
                    fighters[defender_idx].stun_remaining = stun

                # Knockback: empurra o defensor para longe do atacante
                kb_dir = 1.0 if pos[defender_idx] >= pos[attacker_idx] else -1.0
                pos[defender_idx] = max(0.0, min(FIELD_SIZE, pos[defender_idx] + kb_dir * kb))

                # Cooldown só é setado em hit — ataque fora de range não desperdiça cooldown
                fighters[attacker_idx].cooldown_remaining = round(
                    fighters[attacker_idx].character.attack_cooldown * TICK_SCALE
                )

        # ── Fase 4: Decrementar timers ────────────────────────────────────
        # Só decrementa timers que não foram recém-setados por um ataque neste tick.
        # Timers aumentados pelo ataque (current > pre) ficam intactos até o próximo tick.
        f0, f1 = fighters
        if f0.stun_remaining <= pre_stun_0:
            f0.stun_remaining = max(0, f0.stun_remaining - 1)
        if f0.cooldown_remaining <= pre_cd_0:
            f0.cooldown_remaining = max(0, f0.cooldown_remaining - 1)
        if f1.stun_remaining <= pre_stun_1:
            f1.stun_remaining = max(0, f1.stun_remaining - 1)
        if f1.cooldown_remaining <= pre_cd_1:
            f1.cooldown_remaining = max(0, f1.cooldown_remaining - 1)

    # ── Condição de vitória ───────────────────────────────────────────────────

    hp_a = max(0.0, fighters[0].hp)
    hp_b = max(0.0, fighters[1].hp)

    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
        return CombatResult(
            winner=winner, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b)
        )

    if not fighters[0].is_alive:
        return CombatResult(
            winner=1, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b)
        )

    if not fighters[1].is_alive:
        return CombatResult(
            winner=0, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b)
        )

    winner = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
    return CombatResult(
        winner=winner, ticks=MAX_TICKS, ko=False, hp_remaining=(hp_a, hp_b)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Simulação detalhada — para diagnóstico de arquétipo
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ActionLog:
    """
    Contagem de ações e stun por lutador em um único combate.

    stun_applied: stun bruto acumulado por atacante (soma de stun retornado por
    _resolve_attack em cada hit). Conta o valor antes de verificar absorção por
    stun_remaining existente — proxy de pressão, não de stun efetivamente sofrido.
    Suficiente para ranking ordinal (Combo Master lidera pelo stun alto no atributo).
    """
    action_counts: Tuple[Dict[Action, int], Dict[Action, int]]  # (fighter_0, fighter_1)
    active_ticks:  Tuple[int, int]                         # ticks não-stunados por lutador
    stun_applied:  Tuple[int, int]                         # stun total aplicado por lutador


def simulate_combat_detailed(
    char_a: Character, char_b: Character
) -> Tuple[CombatResult, ActionLog]:
    """
    Idêntico a simulate_combat mas registra distribuição de ações e stun aplicado.
    Usado exclusivamente pelo archetype_validator — não altera o pipeline de fitness.
    """
    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    pos = [
        (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,
        (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,
    ]
    end_tick = MAX_TICKS

    action_counts = [
        {Action.ATTACK: 0, Action.ADVANCE: 0, Action.RETREAT: 0, Action.DEFEND: 0},
        {Action.ATTACK: 0, Action.ADVANCE: 0, Action.RETREAT: 0, Action.DEFEND: 0},
    ]
    active_ticks = [0, 0]
    stun_applied = [0, 0]

    for tick in range(MAX_TICKS):
        distance = abs(pos[1] - pos[0])

        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            break

        # ── Fase 1: Escolha de ação ─────────────────────────────────────────────────
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            elif _USE_EPSILON and random.random() < ACTION_EPSILON:
                a = random.randint(0, 3)
                actions.append(a)
                active_ticks[i] += 1
                action_counts[i][a] += 1
            else:
                a = _choose_action(fighters[i], fighters[1 - i], distance, pos[i])
                actions.append(a)
                active_ticks[i] += 1
                action_counts[i][a] += 1

        # ── Fase 2: Movimento ───────────────────────────────────────────────────────
        for i in range(2):
            if actions[i] not in (Action.ADVANCE, Action.RETREAT):
                continue
            speed = fighters[i].character.speed / TICK_SCALE
            direction = 1.0 if pos[i] < pos[1 - i] else -1.0
            if actions[i] == Action.ADVANCE:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] + direction * speed))
            else:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] - direction * speed))

        # ── Fase 3: Ataques simultâneos ─────────────────────────────────────────────
        distance = abs(pos[1] - pos[0])  # recalcula após movimento
        defending = [a == Action.DEFEND for a in actions]

        pre_stun_0 = fighters[0].stun_remaining
        pre_stun_1 = fighters[1].stun_remaining
        pre_cd_0   = fighters[0].cooldown_remaining
        pre_cd_1   = fighters[1].cooldown_remaining

        for attacker_idx in range(2):
            if actions[attacker_idx] != Action.ATTACK:
                continue
            if not fighters[attacker_idx].attack_ready:
                continue

            defender_idx = 1 - attacker_idx
            dmg, stun, kb = _resolve_attack(
                attacker=fighters[attacker_idx].character,
                defender_state=fighters[defender_idx],
                defender_is_defending=defending[defender_idx],
                distance=distance,
            )

            if dmg > 0:
                fighters[defender_idx].hp = max(0.0, fighters[defender_idx].hp - dmg)

                if stun > fighters[defender_idx].stun_remaining:
                    fighters[defender_idx].stun_remaining = stun
                stun_applied[attacker_idx] += stun

                kb_dir = 1.0 if pos[defender_idx] >= pos[attacker_idx] else -1.0
                pos[defender_idx] = max(0.0, min(FIELD_SIZE, pos[defender_idx] + kb_dir * kb))

                fighters[attacker_idx].cooldown_remaining = round(
                    fighters[attacker_idx].character.attack_cooldown * TICK_SCALE
                )

        # ── Fase 4: Decrementar timers ──────────────────────────────────────────────
        f0, f1 = fighters
        if f0.stun_remaining <= pre_stun_0:
            f0.stun_remaining = max(0, f0.stun_remaining - 1)
        if f0.cooldown_remaining <= pre_cd_0:
            f0.cooldown_remaining = max(0, f0.cooldown_remaining - 1)
        if f1.stun_remaining <= pre_stun_1:
            f1.stun_remaining = max(0, f1.stun_remaining - 1)
        if f1.cooldown_remaining <= pre_cd_1:
            f1.cooldown_remaining = max(0, f1.cooldown_remaining - 1)

    hp_a = max(0.0, fighters[0].hp)
    hp_b = max(0.0, fighters[1].hp)

    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
        result = CombatResult(winner=winner, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    elif not fighters[0].is_alive:
        result = CombatResult(winner=1, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    elif not fighters[1].is_alive:
        result = CombatResult(winner=0, ticks=end_tick, ko=True, hp_remaining=(hp_a, hp_b))
    else:
        winner = 0 if fighters[0].hp_pct >= fighters[1].hp_pct else 1
        result = CombatResult(winner=winner, ticks=MAX_TICKS, ko=False, hp_remaining=(hp_a, hp_b))

    log = ActionLog(
        action_counts=(action_counts[0], action_counts[1]),
        active_ticks=(active_ticks[0], active_ticks[1]),
        stun_applied=(stun_applied[0], stun_applied[1]),
    )
    return result, log
