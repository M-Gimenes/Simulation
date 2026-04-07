"""
Simulação de combate tick a tick entre dois personagens.

Campo: 100 unidades, distância inicial 50 (config.INITIAL_DISTANCE).
Resolução simultânea — ambos escolhem e executam ação no mesmo tick.

Fluxo por tick:
  1. Decrementam cooldown_remaining e stun_remaining de cada lutador.
  2. Cada lutador escolhe ação via softmax scoring.
     (personagem stunado perde a ação)
  3. Movimento aplicado (ADVANCE / RETREAT) — ambos alteram a distância.
  4. Ataques resolvidos simultaneamente.
     Após acertar, o atacante entra em cooldown por round(cooldown/10) ticks.
  5. Verificação de vitória.

Cooldown como attack speed (determinístico):
  Após atacar, o personagem fica bloqueado por round(cooldown/10) ticks.
  Durante o cooldown, me_hit = 0 nos scores → o personagem evita escolher ATTACK.

Condições de vitória:
  - KO: HP chega a 0.
  - Timer: ao esgotar MAX_TICKS, vence quem tem maior HP percentual.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from character import Character
from config import (
    INITIAL_DISTANCE,
    MAX_DISTANCE,
    MAX_TICKS,
    MIN_DISTANCE,
    SCORE_TEMPERATURE,
)


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
# Softmax e amostragem
# ─────────────────────────────────────────────────────────────────────────────


def _softmax(
    scores: List[float], temperature: float = SCORE_TEMPERATURE
) -> List[float]:
    """
    Softmax numericamente estável com temperatura.

    Temperatura controla o quão decisiva é a escolha:
      - T=1.0 → padrão; scores ~0.25 resultam em distribuição quase uniforme,
                os pesos w_* mal se diferenciam.
      - T=0.1 → scores divididos por 0.1, distribuição concentrada no melhor;
                comportamento alinha com a identidade do arquétipo (w_* importam).
      - T→0   → argmax determinístico.
    """
    scaled = [s / temperature for s in scores]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def _sample(probs: List[float]) -> int:
    """Amostra um índice proporcional às probabilidades."""
    r = random.random()
    cumulative = 0.0
    for i, p in enumerate(probs):
        cumulative += p
        if r <= cumulative:
            return i
    return len(probs) - 1


# ─────────────────────────────────────────────────────────────────────────────
# Sistema de decisão — Softmax Scoring (MD §Simulação de Combate)
# ─────────────────────────────────────────────────────────────────────────────


def _choose_action(
    me_state: FighterState,
    enemy_state: FighterState,
    distance: float,
) -> int:
    """
    Escolhe ação via softmax scoring situacional.

    Todos os atributos de dano/defesa são normalizados (÷100) para escala 0–1.
    Os scores modelam o valor esperado de cada ação na situação atual,
    ponderados pelos pesos comportamentais (w_*) do personagem.

    Definições:
        me_hit    = in_range * ready
        enemy_hit = in_range * ready * (not stunned)   ← inimigo stunado não ameaça
        my_dmg    = me_hit * dmg_me
        raw_risk  = enemy_hit * dmg_en * (1 - def_me)  ← risco após defesa passiva

    ATTACK:  score = w_attack  * me_hit    * (my_dmg - raw_risk)
             Positivo = troca favorável. Negativo = desincentiva atacar.

    ADVANCE: score = w_advance * (1 - me_hit) * (closing_net + w_aggressiveness)
             closing_net = dmg_me - dmg_en*(1-def_me)  (lucro esperado ao chegar em range)
             w_aggressiveness = drive inato de fechar distância independente do perigo.

    RETREAT: score = w_retreat * enemy_hit * (raw_risk - my_dmg)
             Positivo = inimigo domina a troca → faz sentido criar distância.

    DEFEND:  score = w_defend  * enemy_hit * (raw_risk * 0.8)
             raw_risk * 0.8 = poupança extra do bloqueio ativo vs defesa passiva.
             Diferencia-se de RETREAT: ficar e absorver vs recuar — personagens
             com alta defesa e w_defend preferem absorver; runners preferem recuar.
    """
    me    = me_state.character
    enemy = enemy_state.character

    # Dano e defesa normalizados (0–1)
    dmg_me = me.damage    / 100.0
    dmg_en = enemy.damage / 100.0
    def_me = me.defense   / 100.0

    # Flags de alcance
    in_range_me = 1.0 if distance <= me.range_    else 0.0
    in_range_en = 1.0 if distance <= enemy.range_ else 0.0

    # Disponibilidade — cooldown determinístico; inimigo stunado não ataca
    ready_me = 1.0 if me_state.attack_ready                                    else 0.0
    ready_en = 1.0 if (enemy_state.attack_ready and not enemy_state.is_stunned) else 0.0

    me_hit    = in_range_me * ready_me
    enemy_hit = in_range_en * ready_en

    # Estimativas de dano para este tick
    my_dmg   = me_hit    * dmg_me
    raw_risk = enemy_hit

    # ATTACK — vale quando a troca líquida é favorável.
    # Se em cooldown, score fortemente negativo: ATTACK nunca deve ser escolhido
    # (evita ticks desperdiçados onde a ação é "selecionada" mas não executada).
    if not me_state.attack_ready:
        score_attack = -1e9
    else:
        score_attack = me.w_attack * me_hit

    # ADVANCE — lucratividade de fechar + agressividade inata.
    # Se já está em range, avançar mais não tem utilidade — penaliza fortemente
    # para evitar que o personagem desperdice ticks se movendo quando poderia atacar.
    if in_range_me:
        score_advance = -1e9
    else:
        score_advance = me.w_advance * (1.0 - me_hit) * (me.w_aggressiveness)

    # RETREAT — quão perigosa é a troca atual (inimigo domina → foge)
    score_retreat = me.w_retreat * enemy_hit * (1 - me_hit)

    # DEFEND — poupança extra do bloqueio ativo (além da defesa passiva)
    score_defend = me.w_defend * enemy_hit * (1 - me_hit)

    probs = _softmax([score_attack, score_advance, score_retreat, score_defend])
    return _sample(probs)


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
    Retorna (dano_causado, stun_ticks_aplicados, knockback_unidades).
    Retorna (0, 0, 0) se fora de alcance.

    Dano (MD):
        normal:     damage * (1 - defense/100)
        defendendo: damage * (1 - defense/100) * 0.2

    Stun:
        round(attacker.stun/10 * (1 - defender.recovery/100))

    Knockback:
        attacker.knockback / 10  unidades
    """
    if distance > attacker.range_:
        return 0.0, 0, 0.0

    def_factor = 1.0 - defender_state.character.defense / 100.0
    dmg = attacker.damage * def_factor
    if defender_is_defending:
        dmg *= 0.2

    stun_ticks = max(
        0,
        round(
            (attacker.stun / 10.0) * (1.0 - defender_state.character.recovery / 100.0)
        ),
    )

    # Cap de stun: nunca pode exceder o cooldown do próprio atacante.
    # Garante que o defensor fica livre no mesmo tick em que o atacante pode
    # atacar de novo — evita loops de stun onde o oponente nunca age.
    # cooldown alto = ataca rápido → wait_ticks = round((100 - cd) / 10)
    attacker_cooldown_ticks = round((100.0 - attacker.cooldown) / 10.0)
    stun_ticks = min(stun_ticks, attacker_cooldown_ticks)

    knockback_units = attacker.knockback / 10.0

    return dmg, stun_ticks, knockback_units


# ─────────────────────────────────────────────────────────────────────────────
# Simulação principal
# ─────────────────────────────────────────────────────────────────────────────


def simulate_combat(char_a: Character, char_b: Character) -> CombatResult:
    """
    Simula um combate tick a tick entre char_a (índice 0) e char_b (índice 1).
    """
    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    distance = float(INITIAL_DISTANCE)
    end_tick = MAX_TICKS 

    for tick in range(MAX_TICKS):

        # ── Verificação antecipada de KO ──────────────────────────────────
        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            break

        # ── Fase 1: Decrementar timers ────────────────────────────────────
        for f in fighters:
            if f.stun_remaining > 0:
                f.stun_remaining -= 1
            if f.cooldown_remaining > 0:
                f.cooldown_remaining -= 1

        # ── Fase 2: Escolha de ação ───────────────────────────────────────
        # Personagem stunado perde a ação neste tick.
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                actions.append(None)
            else:
                action = _choose_action(fighters[i], fighters[1 - i], distance)
                actions.append(action)

        # ── Fase 3: Movimento ─────────────────────────────────────────────
        delta = 0.0
        for i in range(2):
            if actions[i] == Action.ADVANCE:
                delta -= (fighters[i].character.speed / 100.0) * 5.0
            elif actions[i] == Action.RETREAT:
                delta += (fighters[i].character.speed / 100.0) * 5.0
        distance = max(MIN_DISTANCE, min(MAX_DISTANCE, distance + delta))

        # ── Fase 4: Ataques simultâneos ───────────────────────────────────
        defending = [a == Action.DEFEND for a in actions]
        pending_knockback = 0.0

        for attacker_idx in range(2):
            if actions[attacker_idx] != Action.ATTACK:
                continue
            if not fighters[attacker_idx].attack_ready:
                continue  # cooldown não zerou ainda (edge case do softmax)

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

                pending_knockback += kb

            # Cooldown do atacante — dispara independente de acertar ou não
            # (o personagem tentou atacar: entra em recovery)
            # cooldown alto = ataca rápido → wait_ticks = round((100 - cd) / 10)
            fighters[attacker_idx].cooldown_remaining = round(
                (100.0 - fighters[attacker_idx].character.cooldown) / 10.0
            )

        if pending_knockback > 0:
            distance = min(MAX_DISTANCE, distance + pending_knockback)

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
