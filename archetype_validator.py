"""
Diagnóstico de identidade de arquétipo.

Executa 28 asserções em 4 camadas sobre qualquer Individual
(canônico ou evoluído) e imprime relatório pass/fail.

Uso standalone:
    py archetype_validator.py
"""

from __future__ import annotations

from dataclasses import dataclass, field      # field used in Task 5+
from itertools import combinations            # used in Task 5 (_collect_stats)
from typing import Dict, List, Tuple          # Tuple used in Task 3+

from archetypes import ARCHETYPE_ORDER, ArchetypeID
from combat import Action, ActionLog, CombatResult, simulate_combat_detailed
from config import ATTRIBUTE_BOUNDS, SIMS_PER_MATCHUP
from individual import Individual


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArchetypeCheck:
    archetype:     ArchetypeID
    layer:         str   # "structural_inter" | "structural_intra" | "behavioral" | "outcome"
    description:   str
    passed:        bool
    actual_rank:   int   # 1 = highest value; 0 = N/A (intra assertions)
    expected_rank: int   # 1 = should be highest; 5 = should be lowest; 0 = N/A


@dataclass
class CharacterStats:
    """Stats agregados de um personagem sobre todos os combates do round-robin."""
    action_counts:   Dict[Action, int]  # Action → total de ticks nessa ação
    active_ticks:    int                # total de ticks não-stunados
    wins:            int
    n_combats:       int
    ko_wins:         int
    hp_pct_on_wins:  List[float]        # HP% restante em cada vitória
    ticks_on_wins:   List[int]          # duração do combate em cada vitória
    stun_applied:    int                # total de stun bruto aplicado (proxy de pressão)

    @property
    def aggression_rate(self) -> float:
        atk = self.action_counts.get(Action.ATTACK, 0) + self.action_counts.get(Action.ADVANCE, 0)
        return atk / self.active_ticks if self.active_ticks > 0 else 0.0

    @property
    def defend_rate(self) -> float:
        return self.action_counts.get(Action.DEFEND, 0) / self.active_ticks if self.active_ticks > 0 else 0.0

    @property
    def retreat_rate(self) -> float:
        return self.action_counts.get(Action.RETREAT, 0) / self.active_ticks if self.active_ticks > 0 else 0.0

    @property
    def ko_rate(self) -> float:
        return self.ko_wins / self.wins if self.wins > 0 else 0.0

    @property
    def avg_hp_pct_on_win(self) -> float:
        return sum(self.hp_pct_on_wins) / len(self.hp_pct_on_wins) if self.hp_pct_on_wins else 0.0

    @property
    def avg_ticks_on_win(self) -> float:
        return sum(self.ticks_on_wins) / len(self.ticks_on_wins) if self.ticks_on_wins else 0.0

    @property
    def avg_stun_applied(self) -> float:
        return self.stun_applied / self.n_combats if self.n_combats > 0 else 0.0


@dataclass
class ArchetypeValidationReport:
    checks: List[ArchetypeCheck]
    passed: int
    total:  int

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    def failures(self) -> List[ArchetypeCheck]:
        return [c for c in self.checks if not c.passed]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de ranking
# ─────────────────────────────────────────────────────────────────────────────

def _rank_desc(values: List[float]) -> List[int]:
    """
    Retorna rank para cada valor (1 = maior). Empates recebem ranks consecutivos
    pela posição original (sort estável).
    """
    ranks = [0] * len(values)
    for rank_pos, orig_idx in enumerate(
        sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    ):
        ranks[orig_idx] = rank_pos + 1
    return ranks


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Structural inter-character
# ─────────────────────────────────────────────────────────────────────────────

# (archetype_id, attr_name, expected_rank, description)
# expected_rank=1 → deve ter o maior valor entre os 5 personagens
# expected_rank=5 → deve ter o menor valor entre os 5 personagens
_INTER_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.RUSHDOWN,     "speed",             1, "speed = highest (closes distance first)"),
    (ArchetypeID.RUSHDOWN,     "attack_cooldown",   5, "attack_cooldown = lowest (fastest attacker)"),
    (ArchetypeID.RUSHDOWN,     "w_aggressiveness",  1, "w_aggressiveness = highest (never retreats)"),
    (ArchetypeID.ZONER,        "range_",            1, "range = highest (controls space from afar)"),
    (ArchetypeID.ZONER,        "knockback",         1, "knockback = highest (pushes enemies out of range)"),
    (ArchetypeID.ZONER,        "w_retreat",         1, "w_retreat = highest (kites when threatened)"),
    (ArchetypeID.COMBO_MASTER, "stun",              1, "stun = highest (lockdown — chains combos)"),
    (ArchetypeID.GRAPPLER,     "damage",            1, "damage = highest (burst punish at close range)"),
    (ArchetypeID.TURTLE,       "recovery",          1, "recovery = highest (most resistant to stun)"),
    (ArchetypeID.TURTLE,       "speed",             5, "speed = lowest (slowest — compensates with durability)"),
    (ArchetypeID.TURTLE,       "attack_cooldown",   1, "attack_cooldown = highest (patient, punishes mistakes)"),
    (ArchetypeID.TURTLE,       "hp",                1, "hp = highest (living wall)"),
    (ArchetypeID.TURTLE,       "defense",           1, "defense = highest (absorbs maximum damage)"),
    (ArchetypeID.TURTLE,       "w_defend",          1, "w_defend = highest (absorbs instead of retreating)"),
]


def _check_structural_inter(chars) -> List[ArchetypeCheck]:
    arch_to_idx = {c.archetype.id: i for i, c in enumerate(chars)}
    checks = []
    for arch_id, attr_name, expected_rank, description in _INTER_ASSERTIONS:
        values = [getattr(c, attr_name) for c in chars]
        ranks  = _rank_desc(values)
        idx    = arch_to_idx[arch_id]
        actual = ranks[idx]
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="structural_inter",
            description=description,
            passed=(actual == expected_rank),
            actual_rank=actual,
            expected_rank=expected_rank,
        ))
    return checks


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Structural intra-character (normalized comparisons)
# ─────────────────────────────────────────────────────────────────────────────

# Mapa de nome de propriedade → (lo, hi) dos ATTRIBUTE_BOUNDS
_ATTR_BOUNDS: Dict[str, Tuple[float, float]] = dict(zip(
    ["hp", "damage", "attack_cooldown", "range_", "speed", "defense", "stun", "knockback", "recovery"],
    ATTRIBUTE_BOUNDS,
))


def _norm(char, attr_name: str) -> float:
    """Normaliza o atributo para [0, 1] usando os bounds globais."""
    lo, hi = _ATTR_BOUNDS[attr_name]
    return (getattr(char, attr_name) - lo) / (hi - lo)


# (archetype_id, attr_a, attr_b, description)
# Asserção: norm(attr_a) > norm(attr_b) para o personagem do arquétipo dado
_INTRA_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.ZONER,        "range_",  "speed",    "norm(range) > norm(speed) — space control over mobility"),
    (ArchetypeID.RUSHDOWN,     "speed",   "range_",   "norm(speed) > norm(range) — closes gap, not ranged"),
    (ArchetypeID.GRAPPLER,     "hp",      "speed",    "norm(hp) > norm(speed) — durability over mobility"),
    (ArchetypeID.TURTLE,       "defense", "damage",   "norm(defense) > norm(damage) — punishes errors, not pressures"),
    (ArchetypeID.COMBO_MASTER, "stun",    "knockback","norm(stun) > norm(knockback) — holds, doesn't push"),
    (ArchetypeID.COMBO_MASTER, "speed",   "range_",   "norm(speed) > norm(range) — closes distance for combos"),
]


def _check_structural_intra(chars) -> List[ArchetypeCheck]:
    arch_to_char = {c.archetype.id: c for c in chars}
    checks = []
    for arch_id, attr_a, attr_b, description in _INTRA_ASSERTIONS:
        char   = arch_to_char[arch_id]
        norm_a = _norm(char, attr_a)
        norm_b = _norm(char, attr_b)
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="structural_intra",
            description=description,
            passed=(norm_a > norm_b),
            actual_rank=0,
            expected_rank=0,
        ))
    return checks


# ─────────────────────────────────────────────────────────────────────────────
# Coleta de stats simulados
# ─────────────────────────────────────────────────────────────────────────────

def _collect_stats(individual: Individual, n_sims: int) -> List[CharacterStats]:
    """
    Executa round-robin completo com simulate_combat_detailed.
    Retorna uma lista de CharacterStats na ordem de individual.characters.
    """
    chars = individual.characters
    n     = len(chars)

    stats = [
        CharacterStats(
            action_counts={Action.ATTACK: 0, Action.ADVANCE: 0, Action.RETREAT: 0, Action.DEFEND: 0},
            active_ticks=0,
            wins=0,
            n_combats=0,
            ko_wins=0,
            hp_pct_on_wins=[],
            ticks_on_wins=[],
            stun_applied=0,
        )
        for _ in range(n)
    ]

    for i, j in combinations(range(n), 2):
        for _ in range(n_sims):
            result, log = simulate_combat_detailed(chars[i], chars[j])

            # Atualiza stats de ação para ambos os lutadores
            for fighter_pos, char_idx in ((0, i), (1, j)):
                s = stats[char_idx]
                for action, count in log.action_counts[fighter_pos].items():
                    s.action_counts[action] += count
                s.active_ticks += log.active_ticks[fighter_pos]
                s.stun_applied += log.stun_applied[fighter_pos]
                s.n_combats    += 1

            # Atualiza stats de resultado para o vencedor
            winner_char_idx = i if result.winner == 0 else j
            winner_hp = result.hp_remaining[result.winner]
            winner_hp_pct = winner_hp / chars[winner_char_idx].hp

            sw = stats[winner_char_idx]
            sw.wins += 1
            if result.ko:
                sw.ko_wins += 1
            sw.hp_pct_on_wins.append(winner_hp_pct)
            sw.ticks_on_wins.append(result.ticks)

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Behavioral
# ─────────────────────────────────────────────────────────────────────────────

# (archetype_id, metric_name, expected_rank, description)
_BEHAVIORAL_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.RUSHDOWN, "aggression_rate", 1, "aggression_rate = highest (always closing/attacking)"),
    (ArchetypeID.TURTLE,   "defend_rate",     1, "defend_rate = highest (absorb-first strategy)"),
    (ArchetypeID.ZONER,    "retreat_rate",    1, "retreat_rate = highest (kiting — creates distance)"),
]


def _check_behavioral(stats: List[CharacterStats]) -> List[ArchetypeCheck]:
    arch_to_idx = {arch_id: i for i, arch_id in enumerate(ARCHETYPE_ORDER)}
    checks = []
    for arch_id, metric, expected_rank, description in _BEHAVIORAL_ASSERTIONS:
        values = [getattr(s, metric) for s in stats]
        ranks  = _rank_desc(values)
        idx    = arch_to_idx[arch_id]
        actual = ranks[idx]
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="behavioral",
            description=description,
            passed=(actual == expected_rank),
            actual_rank=actual,
            expected_rank=expected_rank,
        ))
    return checks


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Outcome
# ─────────────────────────────────────────────────────────────────────────────

# (archetype_id, metric_name, expected_rank, description)
_OUTCOME_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.GRAPPLER,     "ko_rate",            1, "ko_rate = highest (burst damage — finishes enemies)"),
    (ArchetypeID.TURTLE,       "avg_hp_pct_on_win",  1, "avg_hp_pct_on_win = highest (absorbs damage cleanly)"),
    (ArchetypeID.RUSHDOWN,     "avg_ticks_on_win",   5, "avg_ticks_on_win = lowest (overwhelms fast)"),
    (ArchetypeID.TURTLE,       "avg_ticks_on_win",   1, "avg_ticks_on_win = highest (wins by attrition)"),
    (ArchetypeID.COMBO_MASTER, "avg_stun_applied",   1, "avg_stun_applied = highest (lockdown identity)"),
]


def _check_outcome(stats: List[CharacterStats]) -> List[ArchetypeCheck]:
    arch_to_idx = {arch_id: i for i, arch_id in enumerate(ARCHETYPE_ORDER)}
    checks = []
    for arch_id, metric, expected_rank, description in _OUTCOME_ASSERTIONS:
        values = [getattr(s, metric) for s in stats]
        ranks  = _rank_desc(values)
        idx    = arch_to_idx[arch_id]
        actual = ranks[idx]
        checks.append(ArchetypeCheck(
            archetype=arch_id,
            layer="outcome",
            description=description,
            passed=(actual == expected_rank),
            actual_rank=actual,
            expected_rank=expected_rank,
        ))
    return checks


# ─────────────────────────────────────────────────────────────────────────────
# Orquestração
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(
    individual: Individual,
    n_sims: int = SIMS_PER_MATCHUP,
) -> ArchetypeValidationReport:
    """Executa as 28 asserções e retorna o relatório completo."""
    chars  = individual.characters
    checks: List[ArchetypeCheck] = []

    # Camadas 1–2: apenas genes, sem simulação
    checks.extend(_check_structural_inter(chars))
    checks.extend(_check_structural_intra(chars))

    # Camadas 3–4: requerem simulação
    stats = _collect_stats(individual, n_sims)
    checks.extend(_check_behavioral(stats))
    checks.extend(_check_outcome(stats))

    passed = sum(1 for c in checks if c.passed)
    return ArchetypeValidationReport(checks=checks, passed=passed, total=len(checks))


# ─────────────────────────────────────────────────────────────────────────────
# Formatação do relatório
# ─────────────────────────────────────────────────────────────────────────────

_LAYER_LABELS = {
    "structural_inter": "LAYER 1 — Structural (inter-character)",
    "structural_intra": "LAYER 2 — Structural (intra-character, normalized)",
    "behavioral":       "LAYER 3 — Behavioral",
    "outcome":          "LAYER 4 — Outcome",
}
_ARCH_NAMES = {a: a.name.replace("_", " ").title() for a in ArchetypeID}
_LINE = "═" * 66


def print_report(report: ArchetypeValidationReport) -> None:
    print("ARCHETYPE VALIDATION REPORT")
    print(_LINE)

    current_layer = None
    current_arch  = None

    for check in report.checks:
        if check.layer != current_layer:
            current_layer = check.layer
            current_arch  = None
            print(f"\n{_LAYER_LABELS[current_layer]}")

        prefix = f"  {_ARCH_NAMES[check.archetype]:<14}" if check.archetype != current_arch else " " * 16
        current_arch = check.archetype

        symbol   = "✓" if check.passed else "✗"
        rank_str = ""
        if check.actual_rank != 0 and not check.passed:
            rank_str = f" (actual rank {check.actual_rank})"

        print(f"{prefix} {symbol} {check.description}{rank_str}")

    print()
    failures  = report.failures()
    score_pct = report.score * 100

    if not failures:
        print(f"SCORE: {report.passed}/{report.total} ({score_pct:.1f}%) — all assertions passed ✓")
    else:
        print(f"SCORE: {report.passed}/{report.total} ({score_pct:.1f}%) — {len(failures)} failure(s)")
        for f in failures:
            rank_str = f" (actual rank {f.actual_rank})" if f.actual_rank != 0 else ""
            print(f"  ✗ {_ARCH_NAMES[f.archetype]}: {f.description}{rank_str}")

    print(_LINE)


# ─────────────────────────────────────────────────────────────────────────────
# Entrada standalone
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    canon = Individual.from_canonical()
    print("Validating canonical individual...\n")
    report = run_validation(canon)
    print_report(report)
