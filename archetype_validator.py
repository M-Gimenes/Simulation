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
