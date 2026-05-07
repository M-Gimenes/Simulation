"""
Análise detalhada dos 10 matchups canônicos: N combates por matchup, médias das estatísticas.

Uso:
    py analyze_matchups.py                       # todos os matchups (canônico)
    py analyze_matchups.py zoner grappler        # matchup específico
    py analyze_matchups.py --evolved             # usa melhor indivíduo do AG
    py analyze_matchups.py --nsga2 [REP]         # usa representante do NSGA-II
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from archetypes import ARCHETYPE_ALIASES, ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from character import Character
from combat import (
    Action,
    FighterState,
    TimerSnapshot,
    _choose_action,
    _decrement_stale_timers,
    _resolve_attack,
)
from config import FIELD_SIZE, INITIAL_DISTANCE, MAX_TICKS, TICK_SCALE
from individual import Individual


ANALYZE_SIMS = 500

# Bandas de classificação aplicadas à WR do vencedor canônico do par:
#   ≥ DOMINANCE_THRESHOLD  → canônico vence demais
#   ≥ BALANCED_THRESHOLD   → canônico OK (50-60%)
#   <  BALANCED_THRESHOLD  → canônico violado / muito fraco
DOMINANCE_THRESHOLD = 0.60
BALANCED_THRESHOLD = 0.50

ACTION_KEYS: Tuple[Action, ...] = (Action.ATTACK, Action.ADVANCE, Action.RETREAT, Action.DEFEND)
NUMERIC_FIELDS: Tuple[str, ...] = (
    "hits_landed",
    "damage_dealt",
    "stun_applied",
    "stun_ticks_applied",
    "ticks_stunned",
    "ticks_in_cooldown",
    "ticks_out_of_range",
    "ticks_in_range",
    "knockback_taken",
)


# ─────────────────────────────────────────────────────────────────────────────
# Estatísticas (uma luta ou média de N lutas — mesma estrutura)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FighterStats:
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
    action_counts: Dict[int, float] = field(
        default_factory=lambda: {int(a): 0.0 for a in ACTION_KEYS}
    )

    @property
    def hp_lost(self) -> float:
        return self.hp_start - self.hp_end

    @property
    def hp_lost_pct(self) -> float:
        return self.hp_lost / self.hp_start if self.hp_start > 0 else 0.0


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
        return min(self.distances, default=0.0)


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
    stats: Tuple[FighterStats, FighterStats]
    n_sims: int


# ─────────────────────────────────────────────────────────────────────────────
# Simulação instrumentada (1 luta)
# ─────────────────────────────────────────────────────────────────────────────


def _initial_positions() -> List[float]:
    return [
        (FIELD_SIZE - INITIAL_DISTANCE) / 2.0,
        (FIELD_SIZE + INITIAL_DISTANCE) / 2.0,
    ]


def _clamp_position(p: float) -> float:
    return max(0.0, min(FIELD_SIZE, p))


def _apply_movement(pos: List[float], i: int, action: Action, speed: float) -> None:
    direction = 1.0 if pos[i] < pos[1 - i] else -1.0
    sign = 1.0 if action == Action.ADVANCE else -1.0
    pos[i] = _clamp_position(pos[i] + direction * sign * speed)


def _apply_knockback(pos: List[float], def_idx: int, att_idx: int, kb: float) -> None:
    direction = 1.0 if pos[def_idx] >= pos[att_idx] else -1.0
    pos[def_idx] = _clamp_position(pos[def_idx] + direction * kb)


def _winner_index(fighters: List[FighterState], hp_max: Tuple[float, float]) -> int:
    alive_a, alive_b = fighters[0].is_alive, fighters[1].is_alive
    if alive_a and not alive_b:
        return 0
    if alive_b and not alive_a:
        return 1
    a_pct = fighters[0].hp / hp_max[0]
    b_pct = fighters[1].hp / hp_max[1]
    return 0 if a_pct >= b_pct else 1


def _record_choice_phase(
    fighters: List[FighterState],
    pos: List[float],
    distance: float,
    stats: Tuple[FighterStats, FighterStats],
) -> List[Optional[Action]]:
    actions: List[Optional[Action]] = []
    for i, f in enumerate(fighters):
        if f.is_stunned:
            stats[i].ticks_stunned += 1
            actions.append(None)
            continue
        a = _choose_action(f, fighters[1 - i], distance, pos[i])
        actions.append(a)
        stats[i].action_counts[int(a)] += 1
        if not f.attack_ready:
            stats[i].ticks_in_cooldown += 1
    return actions


def _record_range_phase(
    fighters: List[FighterState],
    distance: float,
    stats: Tuple[FighterStats, FighterStats],
) -> None:
    for i, f in enumerate(fighters):
        in_range = distance <= f.character.range_
        stats[i].ticks_in_range += int(in_range)
        stats[i].ticks_out_of_range += int(not in_range)


def _resolve_attacks_phase(
    fighters: List[FighterState],
    pos: List[float],
    actions: List[Optional[Action]],
    stats: Tuple[FighterStats, FighterStats],
) -> None:
    distance = abs(pos[1] - pos[0])
    defending = [a == Action.DEFEND for a in actions]

    for att_idx in range(2):
        if actions[att_idx] != Action.ATTACK or not fighters[att_idx].attack_ready:
            continue
        def_idx = 1 - att_idx
        dmg, stun, kb = _resolve_attack(
            attacker=fighters[att_idx].character,
            defender_state=fighters[def_idx],
            defender_is_defending=defending[def_idx],
            distance=distance,
        )
        if dmg <= 0:
            continue

        fighters[def_idx].hp = max(0.0, fighters[def_idx].hp - dmg)
        stats[att_idx].hits_landed += 1
        stats[att_idx].damage_dealt += dmg

        if stun > fighters[def_idx].stun_remaining:
            fighters[def_idx].stun_remaining = stun
            stats[att_idx].stun_applied += 1
            stats[att_idx].stun_ticks_applied += stun

        if kb > 0:
            _apply_knockback(pos, def_idx, att_idx, kb)
            stats[def_idx].knockback_taken += 1

        fighters[att_idx].cooldown_remaining = round(
            fighters[att_idx].character.attack_cooldown * TICK_SCALE
        )


def analyze_combat(char_a: Character, char_b: Character) -> MatchupResult:
    fighters = [
        FighterState(character=char_a, hp=char_a.hp),
        FighterState(character=char_b, hp=char_b.hp),
    ]
    pos = _initial_positions()
    stats: Tuple[FighterStats, FighterStats] = (
        FighterStats(name=char_a.archetype.name, hp_start=char_a.hp),
        FighterStats(name=char_b.archetype.name, hp_start=char_b.hp),
    )
    distances: List[float] = []
    end_tick = MAX_TICKS

    for tick in range(MAX_TICKS):
        distance = abs(pos[1] - pos[0])
        distances.append(distance)

        if not fighters[0].is_alive or not fighters[1].is_alive:
            end_tick = tick
            break

        actions = _record_choice_phase(fighters, pos, distance, stats)
        _record_range_phase(fighters, distance, stats)

        for i in range(2):
            if actions[i] in (Action.ADVANCE, Action.RETREAT):
                _apply_movement(pos, i, actions[i], fighters[i].character.speed / TICK_SCALE)

        snapshots = [TimerSnapshot.of(f) for f in fighters]
        _resolve_attacks_phase(fighters, pos, actions, stats)
        for f, snap in zip(fighters, snapshots):
            _decrement_stale_timers(f, snap)

    stats[0].hp_end = max(0.0, fighters[0].hp)
    stats[1].hp_end = max(0.0, fighters[1].hp)

    winner = _winner_index(fighters, (char_a.hp, char_b.hp))
    ko = not (fighters[0].is_alive and fighters[1].is_alive)
    return MatchupResult(
        name_a=char_a.archetype.name,
        name_b=char_b.archetype.name,
        winner=winner,
        ticks=end_tick,
        ko=ko,
        stats=stats,
        distances=distances,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agregação de N lutas
# ─────────────────────────────────────────────────────────────────────────────


def _accumulate_stats(target: FighterStats, src: FighterStats) -> None:
    target.hp_end += src.hp_end
    for fname in NUMERIC_FIELDS:
        setattr(target, fname, getattr(target, fname) + getattr(src, fname))
    for k in ACTION_KEYS:
        target.action_counts[int(k)] += src.action_counts[int(k)]


def _scale_stats(target: FighterStats, n: int) -> None:
    target.hp_end /= n
    for fname in NUMERIC_FIELDS:
        setattr(target, fname, getattr(target, fname) / n)
    for k in ACTION_KEYS:
        target.action_counts[int(k)] /= n


def analyze_combat_multi(
    char_a: Character, char_b: Character, n: int = ANALYZE_SIMS
) -> AveragedMatchupResult:
    avg: Tuple[FighterStats, FighterStats] = (
        FighterStats(name=char_a.archetype.name, hp_start=char_a.hp),
        FighterStats(name=char_b.archetype.name, hp_start=char_b.hp),
    )
    wins_a = total_ko = 0
    total_ticks = total_avg_dist = total_min_dist = 0.0

    for _ in range(n):
        r = analyze_combat(char_a, char_b)
        if r.winner == 0:
            wins_a += 1
        total_ticks += r.ticks
        total_ko += int(r.ko)
        total_avg_dist += r.avg_distance
        total_min_dist += r.min_distance
        for i in range(2):
            _accumulate_stats(avg[i], r.stats[i])

    for i in range(2):
        _scale_stats(avg[i], n)

    return AveragedMatchupResult(
        name_a=char_a.archetype.name,
        name_b=char_b.archetype.name,
        winrate_a=wins_a / n,
        wins_a=wins_a,
        avg_ticks=total_ticks / n,
        ko_rate=total_ko / n,
        avg_distance=total_avg_dist / n,
        min_distance=total_min_dist / n,
        stats=avg,
        n_sims=n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inferência: vencedor canônico, IC Wilson, classificação por bandas
# ─────────────────────────────────────────────────────────────────────────────


def expected_winner(id_a: ArchetypeID, id_b: ArchetypeID) -> Optional[ArchetypeID]:
    """Vencedor canônico do par segundo `beats` em archetypes.py."""
    if id_b in ARCHETYPES[id_a].beats:
        return id_a
    if id_a in ARCHETYPES[id_b].beats:
        return id_b
    return None


def wilson_ci(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """IC95% Wilson score — preciso para N pequeno e proporções extremas."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def classify_canonical_wr(canon_wr: Optional[float]) -> Tuple[str, str]:
    """Classifica matchup pela WR do vencedor canônico:
       ≥60% ⬆ canônico muito forte | 50-60% ✓ OK | <50% ✗ muito fraco / violado."""
    if canon_wr is None:
        return ("?", "sem canônico esperado")
    if canon_wr >= DOMINANCE_THRESHOLD:
        return ("⬆", "canônico muito forte (≥60%)")
    if canon_wr >= BALANCED_THRESHOLD:
        return ("✓", "canônico OK (50-60%)")
    return ("✗", "canônico muito fraco (<50%)")


def classify_global_wr(wr: float) -> Tuple[str, str]:
    """WR global de um personagem — alvo ~50% num ciclo balanceado (vence 2, perde 2)."""
    if wr >= DOMINANCE_THRESHOLD:
        return ("⬆", "Forte demais (≥60%)")
    if wr >= 1.0 - DOMINANCE_THRESHOLD:
        return ("=", "Equilibrado (40-60%)")
    return ("⬇", "Fraco (<40%)")


# ─────────────────────────────────────────────────────────────────────────────
# Registro consolidado por matchup
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MatchupRecord:
    id_a: ArchetypeID
    id_b: ArchetypeID
    name_a: str
    name_b: str
    wins_a: int
    n_sims: int
    canonical_id: Optional[ArchetypeID]

    @property
    def wr_a(self) -> float:
        return self.wins_a / self.n_sims if self.n_sims else 0.0

    def wr_of(self, aid: ArchetypeID) -> float:
        return self.wr_a if aid == self.id_a else 1.0 - self.wr_a

    @property
    def canonical_wr(self) -> Optional[float]:
        if self.canonical_id is None:
            return None
        return self.wr_of(self.canonical_id)

    @property
    def canonical_ci(self) -> Tuple[float, float]:
        if self.canonical_id == self.id_b:
            return wilson_ci(self.n_sims - self.wins_a, self.n_sims)
        return wilson_ci(self.wins_a, self.n_sims)

    @property
    def status(self) -> Tuple[str, str]:
        return classify_canonical_wr(self.canonical_wr)


def build_record(id_a: ArchetypeID, id_b: ArchetypeID, r: AveragedMatchupResult) -> MatchupRecord:
    return MatchupRecord(
        id_a=id_a,
        id_b=id_b,
        name_a=r.name_a,
        name_b=r.name_b,
        wins_a=r.wins_a,
        n_sims=r.n_sims,
        canonical_id=expected_winner(id_a, id_b),
    )


def aggregate_wr(records: List[MatchupRecord], aid: ArchetypeID) -> Tuple[int, int]:
    """(wins, total_sims) somando todas as matchups onde `aid` participa."""
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
# Saída — barra ASCII e blocos de impressão
# ─────────────────────────────────────────────────────────────────────────────


def _bar(v: float, w: int = 20) -> str:
    filled = max(0, min(w, int(v * w)))
    return "█" * filled + "░" * (w - filled)


def _diagnose(r: AveragedMatchupResult) -> List[str]:
    total = max(r.avg_ticks, 1.0)
    issues: List[str] = []
    for s in r.stats:
        oor = s.ticks_out_of_range / total
        stunned = s.ticks_stunned / total
        kb = s.knockback_taken / total
        ret = s.action_counts[int(Action.RETREAT)] / total
        if oor > 0.50:
            issues.append(f"  [!] {s.name}: {oor:.0%} dos ticks fora de range → dificuldade de fechar distância")
        if stunned > 0.30:
            issues.append(f"  [!] {s.name}: stunado em {stunned:.0%} dos ticks → lockdown severo")
        if kb > 0.10:
            issues.append(f"  [!] {s.name}: knockback sofrido em {kb:.0%} dos ticks → expulso de range repetidamente")
        if ret > 0.20:
            issues.append(f"  [!] {s.name}: recuando em {ret:.0%} dos ticks")
        if s.hits_landed < 1.0:
            issues.append(f"  [!!] {s.name}: média de hits quase zero — raramente acerta")
        atk_eff = s.action_counts[int(Action.ATTACK)] / max(s.ticks_in_range, 1.0)
        if s.ticks_in_range > 0 and atk_eff < 0.20:
            issues.append(f"  [!] {s.name}: apenas {atk_eff:.0%} dos ticks em range usados para atacar")
    return issues


def print_result(r: AveragedMatchupResult) -> None:
    a, b = r.stats
    total = max(r.avg_ticks, 1.0)
    wr_a = r.winrate_a
    wr_b = 1.0 - wr_a

    print(f"\n{'━' * 66}")
    print(f"  {a.name:15s}  vs  {b.name}  (n={r.n_sims})")
    print(
        f"  WR: {a.name}={wr_a:.0%}  {b.name}={wr_b:.0%}"
        f"  |  avg {r.avg_ticks:.0f} ticks  |  KO={r.ko_rate:.0%}"
        f"  |  dist avg={r.avg_distance:.1f}  min={r.min_distance:.1f}"
    )
    print(f"{'─' * 66}")

    for s in (a, b):
        ac = s.action_counts
        print(f"\n  {s.name}")
        print(
            f"    HP perdido  : {s.hp_lost:5.0f}/{s.hp_start:.0f}"
            f"  [{_bar(s.hp_lost_pct)}] {s.hp_lost_pct:.0%}"
        )
        print(
            f"    Hits/Dano   : {s.hits_landed:.1f} hits  {s.damage_dealt:.0f} dmg"
            f"  |  stun aplicado: {s.stun_applied:.1f}x ({s.stun_ticks_applied:.1f} ticks)"
            f"  |  kb sofrido: {s.knockback_taken:.1f}x"
        )
        print(f"    Stunado     : {s.ticks_stunned:.1f}/{total:.0f} ticks ({s.ticks_stunned / total:.0%})")
        print(
            f"    Fora de range: {s.ticks_out_of_range:.1f}/{total:.0f}"
            f" ({s.ticks_out_of_range / total:.0%})"
            f"  |  Em range: {s.ticks_in_range:.1f}/{total:.0f}"
            f" ({s.ticks_in_range / total:.0%})"
        )
        print(
            f"    Ações (média): "
            f"ATK={ac[int(Action.ATTACK)]:.1f} "
            f"ADV={ac[int(Action.ADVANCE)]:.1f} "
            f"RET={ac[int(Action.RETREAT)]:.1f} "
            f"DEF={ac[int(Action.DEFEND)]:.1f}"
        )

    issues = _diagnose(r)
    if issues:
        print("\n  Diagnósticos:")
        for iss in issues:
            print(iss)


def print_matrix_view(records: List[MatchupRecord], ids: List[ArchetypeID]) -> None:
    """Matriz 5×5: WR(linha vs coluna) com símbolo de status + agregado global."""
    idx: Dict[Tuple[ArchetypeID, ArchetypeID], MatchupRecord] = {
        (r.id_a, r.id_b): r for r in records
    }
    abbr = {aid: ARCHETYPES[aid].name[:4] for aid in ids}

    print("\n" + "═" * 78)
    print("  MATRIZ DE MATCHUPS — WR(linha vs coluna)  |  ⬆ ≥60%   ✓ 50-60%   ✗ <50%")
    print("═" * 78 + "\n")

    print(" " * 16 + "".join(f"  {abbr[aid]:^4s}  " for aid in ids) + "  | Global")
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
            wr_row = rec.wr_of(row_id)
            line += f" {wr_row:>4.0%} {rec.status[0]} "
        wins, total = aggregate_wr(records, row_id)
        if total > 0:
            line += f"  | {wins / total:>4.0%}"
        print(line)


def print_aggregate_view(records: List[MatchupRecord], ids: List[ArchetypeID]) -> None:
    print("\n" + "═" * 78)
    print("  WR GLOBAL — agregado por personagem")
    print("═" * 78)
    print(f"\n  {'Personagem':14s}  {'Vitórias':>11s}  {'WR':>5s}  {'IC95%':>14s}   Status")
    print(f"  {'─' * 76}")

    for aid in ids:
        wins, total = aggregate_wr(records, aid)
        if total == 0:
            continue
        wr = wins / total
        lo, hi = wilson_ci(wins, total)
        sym, lbl = classify_global_wr(wr)
        print(
            f"  {ARCHETYPES[aid].name:14s}  {f'{wins}/{total}':>11s}"
            f"  {wr:>5.0%}  [{lo:>3.0%}, {hi:>3.0%}]   {sym} {lbl}"
        )


def print_canonical_summary(records: List[MatchupRecord], n_per_matchup: int) -> None:
    print("\n" + "═" * 78)
    print(f"  RESUMO POR MATCHUP — N={n_per_matchup} sims  (status pela WR do canônico)")
    print(f"  ⬆ ≥60% canônico muito forte   ✓ 50-60% OK   ✗ <50% canônico muito fraco")
    print("═" * 78)
    print(f"\n  {'Matchup':30s}  {'Canônico':14s}  {'WR':>5s}  {'IC95%':>14s}   Status")
    print(f"  {'─' * 76}")

    counts: Dict[str, int] = {"⬆": 0, "✓": 0, "✗": 0, "?": 0}
    for r in records:
        sym, lbl = r.status
        counts[sym] += 1
        canon_name = ARCHETYPES[r.canonical_id].name if r.canonical_id else "—"
        wr_str = f"{r.canonical_wr:.0%}" if r.canonical_wr is not None else "—"
        lo, hi = r.canonical_ci
        ci_str = f"[{lo:.0%}, {hi:.0%}]"
        print(
            f"  {r.name_a + ' vs ' + r.name_b:30s}  {canon_name:14s}"
            f"  {wr_str:>5s}  {ci_str:>14s}   {sym} {lbl}"
        )

    total = len(records)
    print(f"\n  ⬆ Canônico muito forte (≥60%): {counts['⬆']}/{total}")
    print(f"  ✓ Canônico OK         (50-60%): {counts['✓']}/{total}")
    print(f"  ✗ Canônico muito fraco  (<50%): {counts['✗']}/{total}")
    if counts["?"]:
        print(f"  ? Sem canônico esperado:        {counts['?']}/{total}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (results.json)"
    return Individual.from_canonical(), "CANÔNICO"


def _resolve_pairs(matchup_args: List[str]) -> List[Tuple[ArchetypeID, ArchetypeID]]:
    if len(matchup_args) == 2:
        try:
            id_a = ARCHETYPE_ALIASES[matchup_args[0].lower()]
            id_b = ARCHETYPE_ALIASES[matchup_args[1].lower()]
        except KeyError:
            raise SystemExit(
                f"Nomes disponíveis: {', '.join(sorted(ARCHETYPE_ALIASES.keys()))}"
            )
        return [(id_a, id_b)]
    ids = ARCHETYPE_ORDER
    return [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Análise detalhada de matchups (média de N combates)"
    )
    parser.add_argument(
        "matchup", nargs="*",
        help="Par de arquétipos (ex: rushdown zoner). Omita para todos.",
    )
    parser.add_argument(
        "--evolved", action="store_true",
        help="Usa o melhor indivíduo salvo em results.json (default: canônico)",
    )
    parser.add_argument(
        "--nsga2", metavar="REP", nargs="?", const="knee_point",
        help="Usa representante do NSGA-II "
             "(knee_point|best_balance|best_matchup|best_drift). Default: knee_point",
    )
    parser.add_argument(
        "--n", type=int, default=ANALYZE_SIMS, metavar="N",
        help=f"Número de simulações por matchup (default: {ANALYZE_SIMS})",
    )
    parser.add_argument(
        "--seed", type=int, default=None, metavar="S",
        help="Semente para reprodutibilidade (omita para randomness natural)",
    )
    return parser


def main() -> None:
    args = _build_argparser().parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    ind, label = _load_individual(args)
    chars = {c.archetype.id: c for c in ind.characters}
    pairs = _resolve_pairs(args.matchup)

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
