"""
Análise detalhada tick-a-tick dos 10 matchups canônicos.
Identifica padrões de desbalanceamento no combate.

Uso: py analyze_matchups.py
     py analyze_matchups.py zoner grappler   (matchup específico)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from archetypes import ARCHETYPE_ALIASES, ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from character import Character
from combat import Action, FighterState, _choose_action, _resolve_attack
from config import ACTION_EPSILON, FIELD_SIZE, INITIAL_DISTANCE, MAX_TICKS
from individual import Individual


ACTION_NAMES = {Action.ATTACK: "ATK", Action.ADVANCE: "ADV",
                Action.RETREAT: "RET", Action.DEFEND: "DEF"}


# ─────────────────────────────────────────────────────────────────────────────
# Estrutura de resultado
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FighterStats:
    name: str
    hp_start: float
    hp_end: float = 0.0
    hits_landed: int = 0
    damage_dealt: float = 0.0
    stun_applied: int = 0
    stun_ticks_applied: int = 0
    ticks_stunned: int = 0
    ticks_in_cooldown: int = 0
    ticks_out_of_range: int = 0
    ticks_in_range: int = 0
    knockback_taken: int = 0
    action_counts: dict = field(default_factory=lambda: {0: 0, 1: 0, 2: 0, 3: 0})

    @property
    def hp_lost_pct(self) -> float:
        return (self.hp_start - self.hp_end) / self.hp_start


@dataclass
class MatchupResult:
    name_a: str
    name_b: str
    winner: int
    ticks: int
    ko: bool
    stats: Tuple[FighterStats, FighterStats]
    distances: List[float] = field(default_factory=list)

    @property
    def winner_name(self) -> str:
        return self.stats[self.winner].name

    @property
    def avg_distance(self) -> float:
        return sum(self.distances) / len(self.distances) if self.distances else 0.0

    @property
    def min_distance(self) -> float:
        return min(self.distances) if self.distances else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Simulação instrumentada
# ─────────────────────────────────────────────────────────────────────────────

def analyze_combat(char_a: Character, char_b: Character, seed: int = 42) -> MatchupResult:
    import random
    random.seed(seed)

    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    pos = [
        (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,
        (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,
    ]
    stats = [
        FighterStats(name=char_a.archetype.name, hp_start=char_a.hp),
        FighterStats(name=char_b.archetype.name, hp_start=char_b.hp),
    ]
    distances: List[float] = []
    end_tick = MAX_TICKS

    for tick in range(MAX_TICKS):
        distance = abs(pos[1] - pos[0])
        distances.append(distance)

        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            break

        # Fase 1: escolha de ação
        actions: List[Optional[int]] = []
        for i in range(2):
            if fighters[i].is_stunned:
                stats[i].ticks_stunned += 1
                actions.append(None)
                continue
            if random.random() < ACTION_EPSILON:
                a = random.randint(0, 3)
            else:
                a = _choose_action(fighters[i], fighters[1 - i], distance, pos[i])
            actions.append(a)
            stats[i].action_counts[a] += 1
            if not fighters[i].attack_ready:
                stats[i].ticks_in_cooldown += 1

        # Rastreia range antes de mover
        for i in range(2):
            if distance <= fighters[i].character.range_:
                stats[i].ticks_in_range += 1
            else:
                stats[i].ticks_out_of_range += 1

        # Fase 2: movimento
        for i in range(2):
            if actions[i] not in (Action.ADVANCE, Action.RETREAT):
                continue
            direction = 1.0 if pos[i] < pos[1 - i] else -1.0
            if actions[i] == Action.ADVANCE:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] + direction * fighters[i].character.speed))
            else:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] - direction * fighters[i].character.speed))

        # Fase 3: ataques
        distance = abs(pos[1] - pos[0])
        defending = [a == Action.DEFEND for a in actions]
        pre_stun = [f.stun_remaining for f in fighters]
        pre_cd   = [f.cooldown_remaining for f in fighters]

        for att_idx in range(2):
            if actions[att_idx] != Action.ATTACK:
                continue
            if not fighters[att_idx].attack_ready:
                continue
            def_idx = 1 - att_idx
            dmg, stun, kb = _resolve_attack(
                attacker=fighters[att_idx].character,
                defender_state=fighters[def_idx],
                defender_is_defending=defending[def_idx],
                distance=distance,
            )
            if dmg > 0:
                fighters[def_idx].hp = max(0.0, fighters[def_idx].hp - dmg)
                stats[att_idx].hits_landed += 1
                stats[att_idx].damage_dealt += dmg
                if stun > fighters[def_idx].stun_remaining:
                    fighters[def_idx].stun_remaining = stun
                    stats[att_idx].stun_applied += 1
                    stats[att_idx].stun_ticks_applied += stun
                if kb > 0:
                    kb_dir = 1.0 if pos[def_idx] >= pos[att_idx] else -1.0
                    pos[def_idx] = max(0.0, min(FIELD_SIZE, pos[def_idx] + kb_dir * kb))
                    stats[def_idx].knockback_taken += 1
                fighters[att_idx].cooldown_remaining = round(fighters[att_idx].character.attack_cooldown)

        # Fase 4: decrementa timers
        for i, f in enumerate(fighters):
            if f.stun_remaining <= pre_stun[i]:
                f.stun_remaining = max(0, f.stun_remaining - 1)
            if f.cooldown_remaining <= pre_cd[i]:
                f.cooldown_remaining = max(0, f.cooldown_remaining - 1)

    hp_a = max(0.0, fighters[0].hp)
    hp_b = max(0.0, fighters[1].hp)
    stats[0].hp_end = hp_a
    stats[1].hp_end = hp_b

    if not fighters[0].is_alive and not fighters[1].is_alive:
        winner = 0 if (hp_a / char_a.hp) >= (hp_b / char_b.hp) else 1
    elif not fighters[0].is_alive:
        winner = 1
    elif not fighters[1].is_alive:
        winner = 0
    else:
        winner = 0 if (hp_a / char_a.hp) >= (hp_b / char_b.hp) else 1

    ko = not fighters[0].is_alive or not fighters[1].is_alive
    return MatchupResult(
        name_a=char_a.archetype.name, name_b=char_b.archetype.name,
        winner=winner, ticks=end_tick, ko=ko,
        stats=(stats[0], stats[1]), distances=distances,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Impressão
# ─────────────────────────────────────────────────────────────────────────────

def _bar(v: float, w: int = 20) -> str:
    filled = int(v * w)
    return "█" * filled + "░" * (w - filled)


def print_result(r: MatchupResult) -> None:
    a, b = r.stats
    total = max(r.ticks, 1)

    print(f"\n{'━'*66}")
    print(f"  {a.name:15s}  vs  {b.name}")
    print(f"  Vencedor: {r.winner_name}  |  {r.ticks} ticks  |  {'KO' if r.ko else 'Timer'}"
          f"  |  dist avg={r.avg_distance:.1f}  min={r.min_distance:.1f}")
    print(f"{'─'*66}")

    for s in (a, b):
        hp_lost = s.hp_start - s.hp_end
        ac = s.action_counts
        print(f"\n  {s.name}")
        print(f"    HP perdido  : {hp_lost:5.0f}/{s.hp_start:.0f}  [{_bar(s.hp_lost_pct)}] {s.hp_lost_pct:.0%}")
        print(f"    Hits/Dano   : {s.hits_landed} hits  {s.damage_dealt:.0f} dmg"
              f"  |  stun aplicado: {s.stun_applied}x ({s.stun_ticks_applied} ticks)"
              f"  |  kb sofrido: {s.knockback_taken}x")
        print(f"    Stunado     : {s.ticks_stunned}/{total} ticks ({s.ticks_stunned/total:.0%})")
        print(f"    Fora de range: {s.ticks_out_of_range}/{total} ({s.ticks_out_of_range/total:.0%})"
              f"  |  Em range: {s.ticks_in_range}/{total} ({s.ticks_in_range/total:.0%})")
        print(f"    Ações       : ATK={ac[0]} ADV={ac[1]} RET={ac[2]} DEF={ac[3]}")

    # Diagnósticos automáticos
    issues = []
    for i, s in enumerate((a, b)):
        if s.ticks_out_of_range / total > 0.50:
            issues.append(f"  [!] {s.name}: {s.ticks_out_of_range/total:.0%} dos ticks fora de range → dificuldade de fechar distância")
        if s.ticks_stunned / total > 0.30:
            issues.append(f"  [!] {s.name}: stunado em {s.ticks_stunned/total:.0%} dos ticks → lockdown severo")
        if s.knockback_taken / total > 0.10:
            issues.append(f"  [!] {s.name}: knockback sofrido em {s.knockback_taken/total:.0%} dos ticks → expulso de range repetidamente")
        if s.action_counts[Action.RETREAT] / total > 0.20:
            issues.append(f"  [!] {s.name}: recuando em {s.action_counts[Action.RETREAT]/total:.0%} dos ticks")
        if s.hits_landed == 0:
            issues.append(f"  [!!] {s.name}: ZERO hits — nunca acertou o inimigo")
        if s.hits_landed > 0 and s.ticks_in_range > 0:
            hit_rate = s.hits_landed / (s.ticks_in_range / round(s.name and 1))
            attack_efficiency = s.action_counts[Action.ATTACK] / max(s.ticks_in_range, 1)
            if attack_efficiency < 0.20:
                issues.append(f"  [!] {s.name}: apenas {attack_efficiency:.0%} dos ticks em range usados para atacar")

    if issues:
        print(f"\n  Diagnósticos:")
        for iss in issues:
            print(iss)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_WINNER = {
    (ArchetypeID.ZONER,        ArchetypeID.GRAPPLER):     ArchetypeID.ZONER,
    (ArchetypeID.ZONER,        ArchetypeID.TURTLE):        ArchetypeID.ZONER,
    (ArchetypeID.RUSHDOWN,     ArchetypeID.ZONER):         ArchetypeID.RUSHDOWN,
    (ArchetypeID.RUSHDOWN,     ArchetypeID.COMBO_MASTER):  ArchetypeID.RUSHDOWN,
    (ArchetypeID.COMBO_MASTER, ArchetypeID.TURTLE):        ArchetypeID.COMBO_MASTER,
    (ArchetypeID.COMBO_MASTER, ArchetypeID.ZONER):         ArchetypeID.COMBO_MASTER,
    (ArchetypeID.GRAPPLER,     ArchetypeID.COMBO_MASTER):  ArchetypeID.GRAPPLER,
    (ArchetypeID.GRAPPLER,     ArchetypeID.RUSHDOWN):      ArchetypeID.GRAPPLER,
    (ArchetypeID.TURTLE,       ArchetypeID.RUSHDOWN):      ArchetypeID.TURTLE,
    (ArchetypeID.TURTLE,       ArchetypeID.GRAPPLER):      ArchetypeID.TURTLE,
}

NAME_TO_ID = ARCHETYPE_ALIASES


def main() -> None:
    canon = Individual.from_canonical()
    chars = {c.archetype.id: c for c in canon.characters}

    if len(sys.argv) == 3:
        try:
            id_a = NAME_TO_ID[sys.argv[1].lower()]
            id_b = NAME_TO_ID[sys.argv[2].lower()]
        except KeyError:
            print(f"Nomes disponíveis: {', '.join(sorted(NAME_TO_ID.keys()))}")
            return
        pairs = [(id_a, id_b)]
    else:
        ids = ARCHETYPE_ORDER
        pairs = [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]

    print("\n" + "═" * 66)
    print("  ANÁLISE DE MATCHUPS CANÔNICOS  (seed=42, 1 combate cada)")
    print("═" * 66)

    summary = []
    for id_a, id_b in pairs:
        r = analyze_combat(chars[id_a], chars[id_b])
        print_result(r)

        winner_id = id_a if r.winner == 0 else id_b
        key_fwd, key_rev = (id_a, id_b), (id_b, id_a)
        expected = EXPECTED_WINNER.get(key_fwd) or EXPECTED_WINNER.get(key_rev)
        correct = (winner_id == expected) if expected else None
        summary.append((r.name_a, r.name_b, r.winner_name, correct, r.ticks))

    print("\n" + "═" * 66)
    print("  RESUMO")
    print("═" * 66)
    ok_count = sum(1 for *_, ok, _ in summary if ok)
    for na, nb, wn, ok, ticks in summary:
        tag = "✓" if ok else ("✗" if ok is False else "?")
        print(f"  {tag}  {na:15s} vs {nb:15s}  →  {wn:15s}  ({ticks} ticks)")
    print(f"\n  Matchups corretos: {ok_count}/{len(summary)}")


if __name__ == "__main__":
    main()
