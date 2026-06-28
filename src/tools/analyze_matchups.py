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

import numpy as np

from src.engine.archetypes import ARCHETYPE_ALIASES, ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from src.engine.character import Character
from src.engine.combat import Action, seed_combat, simulate_combat_traced
from src.engine.config import MATCHUP_FLOOR, MATCHUP_THRESHOLD, MATCHUP_WR_CAP
from src.engine.fitness import character_balanced, is_hard_counter
from src.engine.individual import Individual


ANALYZE_SIMS = 1000

# Bandas de reporting (cegas à direção), espelhando os limiares do fitness C2:
#   • WR GLOBAL por personagem (headline): equilibrado em [40%, 60%] via
#     `character_balanced` (0.5 ± GLOBAL_CONVERGENCE_THRESHOLD) — ninguém domina o roster.
#   • WR POR PAR (secundário): só marca ✗ quando o par é COUNTER DURO
#     (`is_hard_counter`: |WR − 50%| > MATCHUP_WR_CAP, fora de [30%, 70%]); dentro do
#     teto é aresta de ciclo permitida, não desbalanço.
# O ciclo canônico (quem "deveria" vencer) é reportado à parte como anotação descritiva.
BAL_LO = 0.5 - MATCHUP_WR_CAP    # piso do teto de counter (30%)
BAL_HI = 0.5 + MATCHUP_WR_CAP    # teto do teto de counter (70%)

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
    "defend_forced",
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
    defend_forced: float = 0.0   # DEFEND por encurralamento (RECUAR sem espaço)
    action_counts: Dict[int, float] = field(
        default_factory=lambda: {int(a): 0.0 for a in ACTION_KEYS}
    )

    @property
    def defend_chosen(self) -> float:
        """DEFEND vindo de GUARDA (intenção de absorver), separado do forçado por
        encurralamento. É a métrica de identidade defensiva real (Turtle)."""
        return self.action_counts[int(Action.DEFEND)] - self.defend_forced

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
    decisiveness: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Extração de estatísticas a partir do CombatTrace
# ─────────────────────────────────────────────────────────────────────────────


def analyze_combat(char_a: Character, char_b: Character) -> MatchupResult:
    """Roda uma luta com rastreio JIT e deriva FighterStats do trace."""
    trace = simulate_combat_traced(char_a, char_b)
    chars = (char_a, char_b)
    stats = (
        FighterStats(name=char_a.archetype.name, hp_start=char_a.hp),
        FighterStats(name=char_b.archetype.name, hp_start=char_b.hp),
    )

    pos_a = trace.pos[:, 0]
    pos_b = trace.pos[:, 1]
    distances = np.abs(pos_b - pos_a).tolist()

    for i in (0, 1):
        actions = trace.action[:, i]
        stats[i].hp_end = float(trace.hp[-1, i]) if trace.end_tick > 0 else char_a.hp
        stats[i].ticks_stunned = float((actions == -1).sum())
        for act in ACTION_KEYS:
            stats[i].action_counts[int(act)] = float((actions == int(act)).sum())

        active = actions != -1
        in_range = np.abs(pos_b - pos_a) <= chars[i].range_
        stats[i].ticks_in_range = float((active & in_range).sum())
        stats[i].ticks_out_of_range = float((active & ~in_range).sum())

        cooldown_active = trace.cooldown[:, i] > 0
        stats[i].ticks_in_cooldown = float((active & cooldown_active).sum())

        dmg_dealt = trace.damage_dealt[:, i]
        stats[i].hits_landed = float((dmg_dealt > 0).sum())
        stats[i].damage_dealt = float(dmg_dealt.sum())

        stun_applied = trace.stun_applied[:, i]
        stats[i].stun_applied = float((stun_applied > 0).sum())
        stats[i].stun_ticks_applied = float(stun_applied.sum())

        stats[i].defend_forced = float(trace.forced_defend[:, i].sum())

        opp = 1 - i
        kb_taken = trace.knockback_dealt[:, opp]
        stats[i].knockback_taken = float((kb_taken > 0).sum())

    return MatchupResult(
        name_a=char_a.archetype.name,
        name_b=char_b.archetype.name,
        winner=trace.winner,
        ticks=trace.end_tick,
        ko=trace.ko,
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


def _fight_margin_score(r: MatchupResult) -> float:
    """Score por-luta ∈ [0,1] como margem (espelha fitness._fight_score). KO:
    0.5 + 0.5·(HP_frac do vencedor); timeout: fração de HP%."""
    sa, sb = r.stats
    if r.ko:
        if r.winner == 0:
            return 0.5 + 0.5 * (sa.hp_end / sa.hp_start if sa.hp_start > 0 else 0.0)
        return 0.5 - 0.5 * (sb.hp_end / sb.hp_start if sb.hp_start > 0 else 0.0)
    pi = sa.hp_end / sa.hp_start if sa.hp_start > 0 else 0.0
    pj = sb.hp_end / sb.hp_start if sb.hp_start > 0 else 0.0
    return pi / (pi + pj) if pi + pj > 0 else 0.5


def classify_decisiveness(d: float) -> Tuple[str, str]:
    """Banda saudável [MATCHUP_FLOOR, MATCHUP_THRESHOLD]: vencedor fecha 10-20% HP."""
    if d > MATCHUP_THRESHOLD:
        return ("⬆", "blowout")
    if d < MATCHUP_FLOOR:
        return ("⬇", "fino demais")
    return ("=", "luta sadia")


def analyze_combat_multi(
    char_a: Character, char_b: Character, n: int = ANALYZE_SIMS
) -> AveragedMatchupResult:
    avg: Tuple[FighterStats, FighterStats] = (
        FighterStats(name=char_a.archetype.name, hp_start=char_a.hp),
        FighterStats(name=char_b.archetype.name, hp_start=char_b.hp),
    )
    wins_a = total_ko = 0
    total_ticks = total_avg_dist = total_min_dist = decis_sum = 0.0

    for _ in range(n):
        r = analyze_combat(char_a, char_b)
        if r.winner == 0:
            wins_a += 1
        total_ticks += r.ticks
        total_ko += int(r.ko)
        total_avg_dist += r.avg_distance
        total_min_dist += r.min_distance
        decis_sum += abs(_fight_margin_score(r) - 0.5)
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
        decisiveness=decis_sum / n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Perfil comportamental por personagem (fonte única: fingerprint + validator)
# ─────────────────────────────────────────────────────────────────────────────

# Métricas do perfil comportamental médio por personagem (sobre seus 4 matchups).
# Frações em [0,1] (mix de ações / ticks); contagens são por luta / distância.
BEHAVIORAL_KEYS: Tuple[str, ...] = (
    "adv", "ret", "def_chosen", "def_forced",      # mix de ações (fração de ações)
    "oor", "stunned",                              # fração de ticks
    "atk_landed", "mean_dist", "stun_inflicted",   # por luta / distância média
)


def behavioral_profile(
    ind: Individual, n: int = ANALYZE_SIMS
) -> Dict[ArchetypeID, Dict[str, float]]:
    """Perfil comportamental médio por personagem, agregado sobre seus 4 matchups.

    Fonte ÚNICA consumida pelo `fingerprint` (retrato descritivo) e pela Layer 3
    do `archetype_validator` (asserções de identidade) — evita reimplementar a
    agregação em dois lugares. O DEFEND vem dividido em escolhido (GUARDA, via
    `FighterStats.defend_chosen`) e forçado (encurralamento, `defend_forced`),
    para que a identidade defensiva real não seja contaminada pela geometria.
    """
    chars = {c.archetype.id: c for c in ind.characters}
    ids = ARCHETYPE_ORDER
    agg = {aid: {k: 0.0 for k in BEHAVIORAL_KEYS} | {"_n": 0} for aid in ids}

    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            r = analyze_combat_multi(chars[ids[a]], chars[ids[b]], n=n)
            ticks = max(r.avg_ticks, 1.0)
            for idx, aid in ((0, ids[a]), (1, ids[b])):
                s = r.stats[idx]
                act = sum(s.action_counts.values()) or 1.0
                m = agg[aid]
                m["adv"]            += s.action_counts[int(Action.ADVANCE)] / act
                m["ret"]            += s.action_counts[int(Action.RETREAT)] / act
                m["def_chosen"]     += s.defend_chosen / act
                m["def_forced"]     += s.defend_forced / act
                m["oor"]            += s.ticks_out_of_range / ticks
                m["stunned"]        += s.ticks_stunned / ticks
                m["atk_landed"]     += s.hits_landed
                m["mean_dist"]      += r.avg_distance
                m["stun_inflicted"] += s.stun_ticks_applied
                m["_n"]             += 1

    for aid in ids:
        cnt = agg[aid].pop("_n") or 1
        for k in BEHAVIORAL_KEYS:
            agg[aid][k] /= cnt
    return agg


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


def classify_balance(wr: float) -> Tuple[str, str]:
    """Veredito do par, cego à direção: ✗ só quando o par é COUNTER DURO
    (`is_hard_counter`: |WR − 50%| > MATCHUP_WR_CAP, fora de [30%, 70%]); dentro do
    teto é aresta de ciclo permitida, não desbalanço. Simétrico em torno de 50%, então
    `wr` e `1 − wr` recebem a mesma classificação."""
    if is_hard_counter(wr):
        return ("✗", "counter duro")
    return ("=", "dentro do teto")


def classify_global_wr(wr: float) -> Tuple[str, str]:
    """WR global de um personagem — alvo ~50% num roster equilibrado (vence 2, perde 2).
    Equilibrado em [40%, 60%] (via `character_balanced`); acima domina, abaixo é fraco."""
    if character_balanced(wr):
        return ("=", "Equilibrado (40-60%)")
    if wr > 0.5:
        return ("⬆", "Forte demais (>60%)")
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
    decisiveness: float = 0.0

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
    def balance(self) -> Tuple[str, str]:
        """Equilíbrio do par, cego à direção (usa a WR de A — simétrico)."""
        return classify_balance(self.wr_a)

    @property
    def cycle(self) -> Tuple[str, str]:
        """Anotação descritiva post-hoc: o favorito observado concorda com o
        ciclo canônico? Não é pass/fail — o ciclo nunca é alvo do AG."""
        if self.canonical_id is None:
            return ("·", "par neutro")
        winner_name = ARCHETYPES[self.canonical_id].name
        loser_id = self.id_b if self.canonical_id == self.id_a else self.id_a
        loser_name = ARCHETYPES[loser_id].name
        if self.canonical_wr >= 0.5:
            return ("→", f"mantido ({winner_name})")
        return ("↯", f"invertido ({loser_name})")


def build_record(id_a: ArchetypeID, id_b: ArchetypeID, r: AveragedMatchupResult) -> MatchupRecord:
    return MatchupRecord(
        id_a=id_a,
        id_b=id_b,
        name_a=r.name_a,
        name_b=r.name_b,
        wins_a=r.wins_a,
        n_sims=r.n_sims,
        canonical_id=expected_winner(id_a, id_b),
        decisiveness=r.decisiveness,
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
        f"  |  decis={r.decisiveness:.3f} {classify_decisiveness(r.decisiveness)[0]}"
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
    print("  MATRIZ DE MATCHUPS — WR(linha vs coluna)  |  ⬆ >60%   = 40-60%   ⬇ <40%")
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
            line += f" {wr_row:>4.0%} {classify_global_wr(wr_row)[0]} "
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


def print_matchup_summary(records: List[MatchupRecord], n_per_matchup: int) -> None:
    print("\n" + "═" * 78)
    print(f"  RESUMO POR MATCHUP — N={n_per_matchup} sims")
    print(f"  decis = margem média da luta |score−0.5|  (0 = empate; 0.5 = esmaga;"
          f" 0.05 ≈ vencedor fecha com 10% HP)")
    print(f"  Luta (objetivo do AG): banda [{MATCHUP_FLOOR:.2f}, {MATCHUP_THRESHOLD:.2f}]"
          f" = sadia   ⬆ blowout (> {MATCHUP_THRESHOLD:.2f})   ⬇ fina demais (< {MATCHUP_FLOOR:.2f})")
    print(f"  Counter (cego à direção): = dentro do teto [{BAL_LO:.0%}, {BAL_HI:.0%}]"
          f"   ✗ counter duro (fora)")
    print(f"  Ciclo canônico (descritivo): → mantido   ↯ invertido")
    print("═" * 78)
    print(
        f"\n  {'Matchup':26s}  {'WR':>5s}  {'decis':>6s}  {'Luta':14s}"
        f"  {'Counter':8s}  Ciclo"
    )
    print(f"  {'─' * 82}")

    luta_counts: Dict[str, int] = {"=": 0, "⬆": 0, "⬇": 0}
    bal_counts:  Dict[str, int] = {"=": 0, "✗": 0}
    cyc_counts:  Dict[str, int] = {"→": 0, "↯": 0, "·": 0}
    for r in records:
        bsym, _   = r.balance
        csym, clbl = r.cycle
        lsym, llbl = classify_decisiveness(r.decisiveness)
        luta_counts[lsym] += 1
        bal_counts[bsym] += 1
        cyc_counts[csym] += 1
        wr_val = r.canonical_wr if r.canonical_wr is not None else r.wr_a
        print(
            f"  {r.name_a + ' vs ' + r.name_b:26s}  {wr_val:>5.0%}  {r.decisiveness:>6.3f}"
            f"  {lsym} {llbl:12s}  {bsym:8s}  {csym} {clbl}"
        )

    total = len(records)
    print(
        f"\n  Luta:   = {luta_counts['=']}/{total} sadias"
        f"   ⬆ {luta_counts['⬆']}/{total} blowout   ⬇ {luta_counts['⬇']}/{total} finas"
    )
    print(
        f"  Counter: = {bal_counts['=']}/{total} dentro do teto   ✗ {bal_counts['✗']}/{total} counters duros"
    )
    cyc_line = (
        f"  Ciclo:  → {cyc_counts['→']}/{total} mantidos   ↯ {cyc_counts['↯']}/{total} invertidos"
    )
    if cyc_counts["·"]:
        cyc_line += f"   · {cyc_counts['·']}/{total} neutros"
    print(cyc_line)


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
        seed_combat(args.seed)

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
    print_matchup_summary(records, args.n)


if __name__ == "__main__":
    main()
