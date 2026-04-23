"""
Análise detalhada tick-a-tick dos 10 matchups canônicos.
Executa N combates por matchup e apresenta médias das estatísticas.

Uso:
    py analyze_matchups.py                           # todos os matchups (canônico)
    py analyze_matchups.py zoner grappler            # matchup específico
    py analyze_matchups.py --evolved                 # usa melhor indivíduo do AG (results.json)
    py analyze_matchups.py --nsga2                   # usa knee_point do NSGA-II
    py analyze_matchups.py --nsga2 best_balance      # usa representante específico do NSGA-II
    py analyze_matchups.py --nsga2 best_matchup
    py analyze_matchups.py --nsga2 best_drift
    py analyze_matchups.py --n 50                    # número de simulações por matchup
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from archetypes import ARCHETYPE_ALIASES, ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from character import Character
from combat import Action, FighterState, _choose_action, _resolve_attack
from config import ACTION_EPSILON, FIELD_SIZE, INITIAL_DISTANCE, MAX_TICKS, TICK_SCALE
from individual import Individual


ANALYZE_SIMS = 30


# ─────────────────────────────────────────────────────────────────────────────
# Estrutura de resultado de uma luta
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
# Estrutura de resultado agregado (N combates)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AveragedFighterStats:
    name: str
    hp_start: float
    hp_end: float = 0.0
    hits_landed: float = 0.0
    damage_dealt: float = 0.0
    stun_applied: float = 0.0
    stun_ticks_applied: float = 0.0
    ticks_stunned: float = 0.0
    ticks_in_cooldown: float = 0.0
    ticks_out_of_range: float = 0.0
    ticks_in_range: float = 0.0
    knockback_taken: float = 0.0
    action_counts: dict = field(default_factory=lambda: {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0})

    @property
    def hp_lost_pct(self) -> float:
        return (self.hp_start - self.hp_end) / self.hp_start


@dataclass
class AveragedMatchupResult:
    name_a: str
    name_b: str
    winrate_a: float
    avg_ticks: float
    ko_rate: float
    avg_distance: float
    min_distance: float
    stats: Tuple[AveragedFighterStats, AveragedFighterStats]
    n_sims: int

    @property
    def winner_name(self) -> str:
        return self.name_a if self.winrate_a >= 0.5 else self.name_b

    @property
    def winner_wr(self) -> float:
        return self.winrate_a if self.winrate_a >= 0.5 else 1.0 - self.winrate_a


# ─────────────────────────────────────────────────────────────────────────────
# Simulação instrumentada (luta única)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_combat(char_a: Character, char_b: Character) -> MatchupResult:
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

        for i in range(2):
            if distance <= fighters[i].character.range_:
                stats[i].ticks_in_range += 1
            else:
                stats[i].ticks_out_of_range += 1

        for i in range(2):
            if actions[i] not in (Action.ADVANCE, Action.RETREAT):
                continue
            direction = 1.0 if pos[i] < pos[1 - i] else -1.0
            speed = fighters[i].character.speed / TICK_SCALE
            if actions[i] == Action.ADVANCE:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] + direction * speed))
            else:
                pos[i] = max(0.0, min(FIELD_SIZE, pos[i] - direction * speed))

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
                fighters[att_idx].cooldown_remaining = round(fighters[att_idx].character.attack_cooldown * TICK_SCALE)

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
# Análise agregada (N combates)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_combat_multi(char_a: Character, char_b: Character, n: int = ANALYZE_SIMS) -> AveragedMatchupResult:
    wins_a = 0
    total_ticks = 0.0
    total_ko = 0
    total_avg_dist = 0.0
    total_min_dist = 0.0

    avg_stats = [
        AveragedFighterStats(name=char_a.archetype.name, hp_start=char_a.hp),
        AveragedFighterStats(name=char_b.archetype.name, hp_start=char_b.hp),
    ]

    for _ in range(n):
        r = analyze_combat(char_a, char_b)
        if r.winner == 0:
            wins_a += 1
        total_ticks += r.ticks
        total_ko += int(r.ko)
        total_avg_dist += r.avg_distance
        total_min_dist += r.min_distance

        for i, s in enumerate(r.stats):
            avg_stats[i].hp_end += s.hp_end
            avg_stats[i].hits_landed += s.hits_landed
            avg_stats[i].damage_dealt += s.damage_dealt
            avg_stats[i].stun_applied += s.stun_applied
            avg_stats[i].stun_ticks_applied += s.stun_ticks_applied
            avg_stats[i].ticks_stunned += s.ticks_stunned
            avg_stats[i].ticks_in_cooldown += s.ticks_in_cooldown
            avg_stats[i].ticks_out_of_range += s.ticks_out_of_range
            avg_stats[i].ticks_in_range += s.ticks_in_range
            avg_stats[i].knockback_taken += s.knockback_taken
            for k in range(4):
                avg_stats[i].action_counts[k] += s.action_counts[k]

    for i in range(2):
        avg_stats[i].hp_end /= n
        avg_stats[i].hits_landed /= n
        avg_stats[i].damage_dealt /= n
        avg_stats[i].stun_applied /= n
        avg_stats[i].stun_ticks_applied /= n
        avg_stats[i].ticks_stunned /= n
        avg_stats[i].ticks_in_cooldown /= n
        avg_stats[i].ticks_out_of_range /= n
        avg_stats[i].ticks_in_range /= n
        avg_stats[i].knockback_taken /= n
        for k in range(4):
            avg_stats[i].action_counts[k] /= n

    return AveragedMatchupResult(
        name_a=char_a.archetype.name,
        name_b=char_b.archetype.name,
        winrate_a=wins_a / n,
        avg_ticks=total_ticks / n,
        ko_rate=total_ko / n,
        avg_distance=total_avg_dist / n,
        min_distance=total_min_dist / n,
        stats=tuple(avg_stats),
        n_sims=n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Impressão
# ─────────────────────────────────────────────────────────────────────────────

def _bar(v: float, w: int = 20) -> str:
    filled = int(v * w)
    return "█" * filled + "░" * (w - filled)


def print_result(r: AveragedMatchupResult) -> None:
    a, b = r.stats
    total = max(r.avg_ticks, 1)
    wr_a = r.winrate_a
    wr_b = 1.0 - wr_a

    print(f"\n{'━'*66}")
    print(f"  {a.name:15s}  vs  {b.name}  (n={r.n_sims})")
    print(f"  WR: {a.name}={wr_a:.0%}  {b.name}={wr_b:.0%}"
          f"  |  avg {r.avg_ticks:.0f} ticks  |  KO={r.ko_rate:.0%}"
          f"  |  dist avg={r.avg_distance:.1f}  min={r.min_distance:.1f}")
    print(f"{'─'*66}")

    for s in (a, b):
        hp_lost = s.hp_start - s.hp_end
        ac = s.action_counts
        print(f"\n  {s.name}")
        print(f"    HP perdido  : {hp_lost:5.0f}/{s.hp_start:.0f}  [{_bar(s.hp_lost_pct)}] {s.hp_lost_pct:.0%}")
        print(f"    Hits/Dano   : {s.hits_landed:.1f} hits  {s.damage_dealt:.0f} dmg"
              f"  |  stun aplicado: {s.stun_applied:.1f}x ({s.stun_ticks_applied:.1f} ticks)"
              f"  |  kb sofrido: {s.knockback_taken:.1f}x")
        print(f"    Stunado     : {s.ticks_stunned:.1f}/{total:.0f} ticks ({s.ticks_stunned/total:.0%})")
        print(f"    Fora de range: {s.ticks_out_of_range:.1f}/{total:.0f} ({s.ticks_out_of_range/total:.0%})"
              f"  |  Em range: {s.ticks_in_range:.1f}/{total:.0f} ({s.ticks_in_range/total:.0%})")
        print(f"    Ações (média): ATK={ac[0]:.1f} ADV={ac[1]:.1f} RET={ac[2]:.1f} DEF={ac[3]:.1f}")

    issues = []
    for s in (a, b):
        if s.ticks_out_of_range / total > 0.50:
            issues.append(f"  [!] {s.name}: {s.ticks_out_of_range/total:.0%} dos ticks fora de range → dificuldade de fechar distância")
        if s.ticks_stunned / total > 0.30:
            issues.append(f"  [!] {s.name}: stunado em {s.ticks_stunned/total:.0%} dos ticks → lockdown severo")
        if s.knockback_taken / total > 0.10:
            issues.append(f"  [!] {s.name}: knockback sofrido em {s.knockback_taken/total:.0%} dos ticks → expulso de range repetidamente")
        if s.action_counts[Action.RETREAT] / total > 0.20:
            issues.append(f"  [!] {s.name}: recuando em {s.action_counts[Action.RETREAT]/total:.0%} dos ticks")
        if s.hits_landed < 1.0:
            issues.append(f"  [!!] {s.name}: média de hits quase zero — raramente acerta")
        attack_efficiency = s.action_counts[Action.ATTACK] / max(s.ticks_in_range, 1)
        if s.ticks_in_range > 0 and attack_efficiency < 0.20:
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
    import argparse
    parser = argparse.ArgumentParser(description="Análise detalhada de matchups (média de N combates)")
    parser.add_argument("matchup", nargs="*",
                        help="Par de arquétipos (ex: rushdown zoner). Omita para todos.")
    parser.add_argument("--evolved", action="store_true",
                        help="Usa o melhor indivíduo salvo em results.json (default: canônico)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="Usa representante do NSGA-II (knee_point|best_balance|best_matchup|best_drift). Default: knee_point")
    parser.add_argument("--n", type=int, default=ANALYZE_SIMS, metavar="N",
                        help=f"Número de simulações por matchup (default: {ANALYZE_SIMS})")
    parser.add_argument("--seed", type=int, default=None, metavar="S",
                        help="Semente para reprodutibilidade (omita para randomness natural)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.nsga2:
        ind = Individual.from_nsga2(representative=args.nsga2)
        label = f"NSGA-II ({args.nsga2})"
    elif args.evolved:
        ind = Individual.from_results()
        label = "EVOLUÍDO (results.json)"
    else:
        ind = Individual.from_canonical()
        label = "CANÔNICO"
    chars = {c.archetype.id: c for c in ind.characters}

    if len(args.matchup) == 2:
        try:
            id_a = NAME_TO_ID[args.matchup[0].lower()]
            id_b = NAME_TO_ID[args.matchup[1].lower()]
        except KeyError:
            print(f"Nomes disponíveis: {', '.join(sorted(NAME_TO_ID.keys()))}")
            return
        pairs = [(id_a, id_b)]
    else:
        ids = ARCHETYPE_ORDER
        pairs = [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]

    print("\n" + "═" * 66)
    print(f"  ANÁLISE DE MATCHUPS — {label}  ({args.n} combates cada, médias)")
    print("═" * 66)

    summary = []
    for id_a, id_b in pairs:
        r = analyze_combat_multi(chars[id_a], chars[id_b], n=args.n)
        print_result(r)

        winner_id = id_a if r.winrate_a >= 0.5 else id_b
        key_fwd, key_rev = (id_a, id_b), (id_b, id_a)
        expected = EXPECTED_WINNER.get(key_fwd) or EXPECTED_WINNER.get(key_rev)
        correct = (winner_id == expected) if expected else None
        summary.append((r.name_a, r.name_b, r.winner_name, r.winner_wr, correct, int(r.avg_ticks)))

    print("\n" + "═" * 66)
    print("  RESUMO")
    print("═" * 66)
    ok_count = sum(1 for *_, ok, _ in summary if ok)
    for na, nb, wn, wr, ok, ticks in summary:
        tag = "✓" if ok else ("✗" if ok is False else "?")
        print(f"  {tag}  {na:15s} vs {nb:15s}  →  {wn:15s}  WR={wr:.0%}  (~{ticks} ticks)")
    print(f"\n  Matchups corretos: {ok_count}/{len(summary)}")


if __name__ == "__main__":
    main()
