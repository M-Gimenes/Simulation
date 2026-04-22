"""
Diagnóstico de identidade de arquétipo.

Executa 20 asserções em 2 camadas sobre qualquer Individual
(canônico ou evoluído) e imprime relatório pass/fail.

Uso:
    py archetype_validator.py                        # canônico
    py archetype_validator.py --evolved              # usa melhor indivíduo do AG (results.json)
    py archetype_validator.py --nsga2                # usa knee_point do NSGA-II
    py archetype_validator.py --nsga2 best_balance   # usa representante específico do NSGA-II
    py archetype_validator.py --nsga2 best_matchup
    py archetype_validator.py --nsga2 best_drift
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from archetypes import ARCHETYPE_ORDER, ArchetypeID
from config import ATTRIBUTE_BOUNDS
from individual import Individual


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArchetypeCheck:
    archetype:     ArchetypeID
    layer:         str   # "structural_inter" | "structural_intra"
    description:   str
    passed:        bool
    actual_rank:   int   # 1 = highest value; 0 = N/A (intra assertions)
    expected_rank: int   # 1 = should be highest; 5 = should be lowest; 0 = N/A


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
# Orquestração
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(individual: Individual) -> ArchetypeValidationReport:
    """Executa as 20 asserções e retorna o relatório completo."""
    chars  = individual.characters
    checks: List[ArchetypeCheck] = []

    checks.extend(_check_structural_inter(chars))
    checks.extend(_check_structural_intra(chars))

    passed = sum(1 for c in checks if c.passed)
    return ArchetypeValidationReport(checks=checks, passed=passed, total=len(checks))


# ─────────────────────────────────────────────────────────────────────────────
# Formatação do relatório
# ─────────────────────────────────────────────────────────────────────────────

_LAYER_LABELS = {
    "structural_inter": "LAYER 1 — Structural (inter-character)",
    "structural_intra": "LAYER 2 — Structural (intra-character, normalized)",
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
    import argparse
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Validador de identidade de arquétipo")
    parser.add_argument("--evolved", action="store_true",
                        help="Usa o melhor indivíduo salvo em results.json (default: canônico)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="Usa representante do NSGA-II (knee_point|best_balance|best_matchup|best_drift). Default: knee_point")
    args = parser.parse_args()

    if args.nsga2:
        ind = Individual.from_nsga2(representative=args.nsga2)
        print(f"Validando indivíduo NSGA-II ({args.nsga2})...\n")
    elif args.evolved:
        ind = Individual.from_results()
        print("Validando indivíduo evoluído (results.json)...\n")
    else:
        ind = Individual.from_canonical()
        print("Validando indivíduo canônico...\n")

    report = run_validation(ind)
    print_report(report)
