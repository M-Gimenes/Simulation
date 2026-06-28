"""
Diagnóstico de identidade de arquétipo — 17 asserções estruturais (12 inter + 5 intra).

Uso:
    py archetype_validator.py
    py archetype_validator.py --evolved
    py archetype_validator.py --nsga2 [knee_point|best_dominance|best_drift|ideal_point]
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ArchetypeID
from src.engine.combat import seed_combat
from src.engine.config import ATTRIBUTE_BOUNDS
from src.engine.individual import Individual
from src.tools.analyze_matchups import behavioral_profile


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArchetypeCheck:
    archetype:     ArchetypeID
    layer:         str
    description:   str
    passed:        bool
    actual_rank:   int
    expected_rank: int


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
    ranks = [0] * len(values)
    for rank_pos, orig_idx in enumerate(
        sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    ):
        ranks[orig_idx] = rank_pos + 1
    return ranks


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Structural inter-character
# ─────────────────────────────────────────────────────────────────────────────

_INTER_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.RUSHDOWN,     "speed",             1, "speed = highest (closes distance first)"),
    (ArchetypeID.RUSHDOWN,     "attack_cooldown",   5, "attack_cooldown = lowest (fastest attacker)"),
    (ArchetypeID.RUSHDOWN,     "w_aggressiveness",  1, "w_aggressiveness = highest (never retreats)"),
    (ArchetypeID.ZONER,        "range_",            1, "range = highest (controls space from afar)"),
    (ArchetypeID.ZONER,        "knockback",         1, "knockback = highest (pushes enemies out of range)"),
    (ArchetypeID.ZONER,        "w_retreat",         1, "w_retreat = highest (kites when threatened)"),
    (ArchetypeID.COMBO_MASTER, "stun",              1, "stun = highest (lockdown — chains combos)"),
    (ArchetypeID.GRAPPLER,     "damage",            1, "damage = highest (burst punish at close range)"),
    (ArchetypeID.TURTLE,       "speed",             5, "speed = lowest (slowest — compensates with durability)"),
    (ArchetypeID.TURTLE,       "attack_cooldown",   1, "attack_cooldown = highest (patient, punishes mistakes)"),
    (ArchetypeID.TURTLE,       "hp",                1, "hp = highest (living wall)"),
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
# Layer 2 — Structural intra-character (normalized)
# ─────────────────────────────────────────────────────────────────────────────

_ATTR_BOUNDS: Dict[str, Tuple[float, float]] = dict(zip(
    ["hp", "damage", "attack_cooldown", "range_", "speed", "stun", "knockback"],
    ATTRIBUTE_BOUNDS,
))


def _norm(char, attr_name: str) -> float:
    # Mesma convenção do fitness (_archetype_deviation): fração do máximo do bound.
    # Unifica o "normalizado" do projeto numa única convenção (C3).
    _, hi = _ATTR_BOUNDS[attr_name]
    return getattr(char, attr_name) / hi


_INTRA_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.ZONER,        "range_",  "speed",    "norm(range) > norm(speed) — space control over mobility"),
    (ArchetypeID.RUSHDOWN,     "speed",   "range_",   "norm(speed) > norm(range) — closes gap, not ranged"),
    (ArchetypeID.GRAPPLER,     "hp",      "speed",    "norm(hp) > norm(speed) — durability over mobility"),
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
# Layer 3 — Behavioral (identidade funcional: como o personagem joga)
# ─────────────────────────────────────────────────────────────────────────────
#
# Asserções rank-entre-os-5 sobre o perfil comportamental médio (behavioral_profile),
# espelhando a Layer 1. Diferente das estruturais, exige rodar combate (estocástico):
# é opt-in via run_validation(behavioral_n>0).

_BEHAVIORAL_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.ZONER,        "mean_dist",      1, "mean_dist = highest (luta da maior distância)"),
    (ArchetypeID.RUSHDOWN,     "atk_landed",     1, "atk_landed = highest (mais ataques conectados/luta)"),
    (ArchetypeID.TURTLE,       "def_chosen",     1, "def_chosen = highest (absorve por opção, não encurralado)"),
    (ArchetypeID.COMBO_MASTER, "stun_inflicted", 1, "stun_inflicted = highest (lockdown do oponente)"),
]

# Sem asserção comportamental: o combate não modela grab/throw, então a identidade do
# Grappler não tem expressão comportamental distinta (sobrepõe ao corpo-a-corpo do
# Rushdown). Registrado no relatório, fora do denominador da Layer 3.
_BEHAVIORAL_NO_ASSERTION: Dict[ArchetypeID, str] = {
    ArchetypeID.GRAPPLER: "sem assinatura comportamental — mecânica de grab ausente",
}


def _check_behavioral(profile: Dict[ArchetypeID, Dict[str, float]]) -> List[ArchetypeCheck]:
    ids = ARCHETYPE_ORDER
    checks = []
    for arch_id, metric, expected_rank, description in _BEHAVIORAL_ASSERTIONS:
        values = [profile[aid][metric] for aid in ids]
        ranks  = _rank_desc(values)
        actual = ranks[ids.index(arch_id)]
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
# Orquestração
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(
    individual: Individual, behavioral_n: int = 0, seed: int = 42
) -> ArchetypeValidationReport:
    """Valida identidade estrutural (Layers 1-2, sempre) e — se `behavioral_n>0` —
    funcional (Layer 3, rodando `behavioral_n` sims/matchup sob `seed`)."""
    chars  = individual.characters
    checks: List[ArchetypeCheck] = []

    checks.extend(_check_structural_inter(chars))
    checks.extend(_check_structural_intra(chars))

    if behavioral_n > 0:
        seed_combat(seed)
        random.seed(seed)
        profile = behavioral_profile(individual, behavioral_n)
        checks.extend(_check_behavioral(profile))

    passed = sum(1 for c in checks if c.passed)
    return ArchetypeValidationReport(checks=checks, passed=passed, total=len(checks))


# ─────────────────────────────────────────────────────────────────────────────
# Formatação do relatório
# ─────────────────────────────────────────────────────────────────────────────

_LAYER_LABELS = {
    "structural_inter": "LAYER 1 — Structural (inter-character)",
    "structural_intra": "LAYER 2 — Structural (intra-character, normalized)",
    "behavioral":       "LAYER 3 — Behavioral (functional identity)",
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

    # Arquétipos sem asserção comportamental (ex.: Grappler) — fora do denominador.
    if any(c.layer == "behavioral" for c in report.checks):
        for arch_id, note in _BEHAVIORAL_NO_ASSERTION.items():
            print(f"  {_ARCH_NAMES[arch_id]:<14} • {note}")

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
                        help="Usa representante do NSGA-II (knee_point|best_dominance|best_drift|ideal_point)")
    parser.add_argument("--n", type=int, default=200,
                        help="Sims/matchup da Layer 3 comportamental (0 = só estrutural)")
    parser.add_argument("--seed", type=int, default=42, help="Semente do combate da Layer 3")
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

    report = run_validation(ind, behavioral_n=args.n, seed=args.seed)
    print_report(report)
