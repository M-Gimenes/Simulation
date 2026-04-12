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
