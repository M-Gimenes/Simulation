"""
Análise detalhada dos 10 matchups canônicos: N combates por matchup, médias das estatísticas.

Uso:
    py analyze_matchups.py                       # todos os matchups (canônico)
    py analyze_matchups.py zoner grappler        # matchup específico
    py analyze_matchups.py --evolved             # usa melhor indivíduo do AG
    py analyze_matchups.py --nsga2 [REP]         # usa representante do NSGA-II
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from archetypes import ARCHETYPE_ALIASES, ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from character import Character
from combat import Action, FighterState, _choose_action, _resolve_attack
from config import FIELD_SIZE, INITIAL_DISTANCE, MAX_TICKS, TICK_SCALE
from individual import Individual


ANALYZE_SIMS = 500


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
    wins_a: int
    avg_ticks: float
    ko_rate: float
    avg_distance: float
    min_distance: float
    stats: Tuple[AveragedFighterStats, AveragedFighterStats]
    n_sims: int


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
        wins_a=wins_a,
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
# Vencedor canônico esperado (cycle FGC)
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


# ─────────────────────────────────────────────────────────────────────────────
# Inferência estatística sobre WR (IC Wilson score)
# ─────────────────────────────────────────────────────────────────────────────

def wilson_ci(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """IC95% de Wilson score para proporção binomial — preciso mesmo perto de 0 ou 1
    e para N pequeno, ao contrário da aproximação normal ingênua."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def classify_canonical(canonical_wr: Optional[float], ci: Tuple[float, float]) -> Tuple[str, str]:
    """Classifica matchup pela posição do IC95% da WR canônica em relação a 50%."""
    if canonical_wr is None:
        return ("?", "sem canônico esperado")
    lo, hi = ci
    if lo > 0.5:
        return ("✓", "canônico confirmado")
    if hi < 0.5:
        return ("✗", "canônico violado")
    return ("~", "balanceado (IC cruza 50%)")


def classify_global(ci: Tuple[float, float]) -> Tuple[str, str]:
    """Classifica WR global de um personagem em relação a 50%."""
    lo, hi = ci
    if lo > 0.5:
        return ("⬆", "Forte demais (WR > 50% confirmado)")
    if hi < 0.5:
        return ("⬇", "Fraco (WR < 50% confirmado)")
    return ("=", "Equilibrado")


# ─────────────────────────────────────────────────────────────────────────────
# Registro consolidado por matchup
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatchupRecord:
    """Resultado de uma matchup já anotado com inferência canônica."""
    id_a: ArchetypeID
    id_b: ArchetypeID
    name_a: str
    name_b: str
    wins_a: int
    n_sims: int
    canonical_id: Optional[ArchetypeID]
    canonical_wr: Optional[float]
    canonical_ci: Tuple[float, float]

    @property
    def status(self) -> Tuple[str, str]:
        return classify_canonical(self.canonical_wr, self.canonical_ci)


def build_record(id_a: ArchetypeID, id_b: ArchetypeID, r: AveragedMatchupResult) -> MatchupRecord:
    expected = EXPECTED_WINNER.get((id_a, id_b)) or EXPECTED_WINNER.get((id_b, id_a))
    if expected == id_a:
        canon_wins, canon_wr = r.wins_a, r.winrate_a
    elif expected == id_b:
        canon_wins, canon_wr = r.n_sims - r.wins_a, 1.0 - r.winrate_a
    else:
        canon_wins, canon_wr = r.wins_a, None
    return MatchupRecord(
        id_a=id_a, id_b=id_b,
        name_a=r.name_a, name_b=r.name_b,
        wins_a=r.wins_a, n_sims=r.n_sims,
        canonical_id=expected,
        canonical_wr=canon_wr,
        canonical_ci=wilson_ci(canon_wins, r.n_sims),
    )


def aggregate_wr(records: List[MatchupRecord], aid: ArchetypeID) -> Tuple[int, int]:
    """(wins, total_sims) do personagem somando todas as matchups onde participa."""
    wins = total = 0
    for r in records:
        if r.id_a == aid:
            wins += r.wins_a
            total += r.n_sims
        elif r.id_b == aid:
            wins += r.n_sims - r.wins_a
            total += r.n_sims
    return wins, total


# ─────────────────────────────────────────────────────────────────────────────
# Vistas de saída
# ─────────────────────────────────────────────────────────────────────────────

def print_matrix_view(records: List[MatchupRecord], ids: List[ArchetypeID]) -> None:
    """Matriz 5×5 — WR(linha vs coluna) com símbolo de aderência ao canônico
    + agregado global por personagem na última coluna."""
    idx: Dict[Tuple[ArchetypeID, ArchetypeID], MatchupRecord] = {}
    for r in records:
        idx[(r.id_a, r.id_b)] = r

    abbr = {aid: ARCHETYPES[aid].name[:4] for aid in ids}

    print("\n" + "═" * 78)
    print("  MATRIZ DE MATCHUPS — WR(linha vs coluna)  |  ✓ canônico  ✗ violado  ~ balanceado")
    print("═" * 78)
    print()

    header = " " * 16 + "".join(f"  {abbr[aid]:^4s}  " for aid in ids) + "  | Global"
    print(header)
    print(" " * 16 + "─" * (8 * len(ids) + 11))

    for row_id in ids:
        line = f"  {ARCHETYPES[row_id].name:<14s}"
        for col_id in ids:
            if row_id == col_id:
                line += "  ────  "
                continue
            rec = idx.get((row_id, col_id)) or idx.get((col_id, row_id))
            if rec is None:
                line += "    —   "
                continue
            wr_row = rec.wins_a / rec.n_sims if rec.id_a == row_id else 1.0 - rec.wins_a / rec.n_sims
            sym = rec.status[0]
            line += f" {wr_row:>4.0%} {sym} "
        wins, total = aggregate_wr(records, row_id)
        if total > 0:
            line += f"  | {wins/total:>4.0%}"
        print(line)


def print_aggregate_view(records: List[MatchupRecord], ids: List[ArchetypeID]) -> None:
    """WR global por personagem (todas as matchups onde participa)."""
    print("\n" + "═" * 78)
    print("  WR GLOBAL — agregado por personagem")
    print("═" * 78)
    print(f"\n  {'Personagem':14s}  {'Vitórias':>11s}  {'WR':>5s}  {'IC95%':>14s}   Status")
    print(f"  {'─'*76}")

    for aid in ids:
        wins, total = aggregate_wr(records, aid)
        if total == 0:
            continue
        ci = wilson_ci(wins, total)
        sym, lbl = classify_global(ci)
        print(
            f"  {ARCHETYPES[aid].name:14s}  {f'{wins}/{total}':>11s}"
            f"  {wins/total:>5.0%}  [{ci[0]:>3.0%}, {ci[1]:>3.0%}]   {sym} {lbl}"
        )


def print_canonical_summary(records: List[MatchupRecord], n_per_matchup: int) -> None:
    """Tabela detalhada por matchup com WR do canônico, IC95% e classificação."""
    print("\n" + "═" * 78)
    print(f"  RESUMO POR MATCHUP — N={n_per_matchup} sims, IC95% via Wilson score")
    print("═" * 78)
    print(f"\n  {'Matchup':30s}  {'Canônico':14s}  {'WR':>5s}  {'IC95%':>14s}   Status")
    print(f"  {'─'*76}")

    counts = {"✓": 0, "~": 0, "✗": 0, "?": 0}
    for r in records:
        sym, lbl = r.status
        counts[sym] += 1
        canonical_name = ARCHETYPES[r.canonical_id].name if r.canonical_id else "—"
        wr_str = f"{r.canonical_wr:.0%}" if r.canonical_wr is not None else "—"
        ci_str = f"[{r.canonical_ci[0]:.0%}, {r.canonical_ci[1]:.0%}]"
        print(
            f"  {r.name_a + ' vs ' + r.name_b:30s}  {canonical_name:14s}"
            f"  {wr_str:>5s}  {ci_str:>14s}   {sym} {lbl}"
        )

    total = len(records)
    print(f"\n  ✓ Canônico confirmado:         {counts['✓']}/{total}   (IC95% inteiramente acima de 50%)")
    print(f"  ~ Estatisticamente balanceado: {counts['~']}/{total}   (IC95% cruza 50% — winner instável)")
    print(f"  ✗ Canônico violado:            {counts['✗']}/{total}   (IC95% inteiramente abaixo de 50%)")
    if counts["?"]:
        print(f"  ? Sem canônico esperado:       {counts['?']}/{total}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

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

    records: List[MatchupRecord] = []
    for id_a, id_b in pairs:
        r = analyze_combat_multi(chars[id_a], chars[id_b], n=args.n)
        print_result(r)
        records.append(build_record(id_a, id_b, r))

    if len(records) > 1:
        print_matrix_view(records, ARCHETYPE_ORDER)
        print_aggregate_view(records, ARCHETYPE_ORDER)
    print_canonical_summary(records, args.n)


if __name__ == "__main__":
    main()
