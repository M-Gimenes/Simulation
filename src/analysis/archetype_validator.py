"""
Diagnóstico de identidade de arquétipo — 23 asserções: 18 estruturais
(13 inter + 5 intra, Layers 1-2, determinísticas nos genes) + 5 comportamentais
(Layer 3, roda combate; `--n 0` desliga e deixa só as estruturais) — e, junto da
Layer 3, a **concordância de ranking comportamental** (τ de Kendall, contínua).

**Independência dos instrumentos.** As Layers 1-2 medem identidade ESTRUTURAL — o
mesmo eixo que o `drift_penalty` otimiza (os `defining_genes` de cada arquétipo
espelham as asserções inter da Layer 1), então elas são parcialmente endógenas: um
score alto aqui em parte reflete a penalidade ter funcionado. A Layer 3 e a
concordância medem identidade FUNCIONAL — como o personagem joga — e nada no fitness
referencia comportamento. Não são causalmente isoladas: comportamento é consequência
dos genes que o fitness move (o stun infligido vem do gene de stun, a guarda quebrada do
`grab_power`). São *held-out* — o fitness não as vê —, não independentes.

As asserções são um bit cada: o personagem é o 1º naquela métrica ou não é, e ficar em
2º por um fio conta igual a ficar em 5º. A concordância de ranking usa as 5 posições em
todas as métricas do perfil e é contínua, com 0 = acaso e 1 = a ordem do canônico.

Uso:
    py -m src.analysis.archetype_validator
    py -m src.analysis.archetype_validator --evolved
    py -m src.analysis.archetype_validator --nsga2 [knee_point|best_dominance|best_drift|ideal_point|scalar_optimum]
    py -m src.analysis.archetype_validator --n 0    # só estrutural (18 asserções)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ArchetypeID
from src.engine.combat import seed_combat
from src.engine.config import ATTRIBUTE_BOUNDS, ATTRIBUTE_NAMES, WEIGHT_NAMES
from src.engine.individual import Individual
from src.analysis.analyze_matchups import BEHAVIORAL_KEYS, behavioral_profile

Profile = Dict[ArchetypeID, Dict[str, float]]


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
    # τ médio contra o canônico (ver `rank_agreement`); só existe quando a Layer 3 roda.
    rank_agreement: Optional[float] = None

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    def failures(self) -> List[ArchetypeCheck]:
        return [c for c in self.checks if not c.passed]

    def passed_in(self, *layers: str) -> int:
        return sum(1 for c in self.checks if c.layer in layers and c.passed)

    def total_in(self, *layers: str) -> int:
        return sum(1 for c in self.checks if c.layer in layers)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de ranking
# ─────────────────────────────────────────────────────────────────────────────

def _rank_against(values: List[float], idx: int, expected_rank: int) -> int:
    """Posição de `values[idx]` em ordem decrescente, com o EMPATE contado contra a
    asserção.

    Um valor empatado com outros ocupa uma faixa de posições; devolve-se a ponta da
    faixa mais distante da esperada. Assim "o de maior alcance" só passa se for
    estritamente o maior. Resolver o empate pela ordem do índice (o que um `sorted`
    estável faria) daria asserções de graça a quem vem primeiro no roster: cinco
    personagens idênticos passariam em 4 das 13 asserções da Layer 1 sem ter
    identidade nenhuma."""
    value = values[idx]
    above = sum(1 for j, v in enumerate(values) if j != idx and v > value)
    tied  = sum(1 for j, v in enumerate(values) if j != idx and v == value)
    best, worst = 1 + above, 1 + above + tied
    return worst if abs(worst - expected_rank) >= abs(best - expected_rank) else best


def _gene_value(char, name: str) -> float:
    """Valor do gene na forma em que ele age no combate. Atributos, como estão. Os
    pesos comportamentais, como PROBABILIDADE de intenção — só a razão entre eles
    muda o combate, então comparar o valor cru entre personagens seria comparar uma
    escala que não tem efeito nenhum (a mesma razão de `fitness.drift_genes`)."""
    if name in WEIGHT_NAMES:
        return char.intention_probabilities()[WEIGHT_NAMES.index(name)]
    return getattr(char, name)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Structural inter-character
# ─────────────────────────────────────────────────────────────────────────────

_INTER_ASSERTIONS: List[Tuple] = [
    (ArchetypeID.RUSHDOWN,     "speed",             1, "speed = highest (closes distance first)"),
    (ArchetypeID.RUSHDOWN,     "attack_cooldown",   5, "attack_cooldown = lowest (fastest attacker)"),
    (ArchetypeID.RUSHDOWN,     "w_aggressiveness",  1, "P(FRENTE) = highest (never retreats)"),
    (ArchetypeID.ZONER,        "range_",            1, "range = highest (controls space from afar)"),
    (ArchetypeID.ZONER,        "knockback",         1, "knockback = highest (pushes enemies out of range)"),
    (ArchetypeID.ZONER,        "w_retreat",         1, "P(RECUAR) = highest (kites when threatened)"),
    (ArchetypeID.COMBO_MASTER, "stun",              1, "stun = highest (lockdown — chains combos)"),
    (ArchetypeID.GRAPPLER,     "damage",            1, "damage = highest (burst punish at close range)"),
    (ArchetypeID.GRAPPLER,     "grab_power",        1, "grab_power = highest (grab is the canonical counter to blocking)"),
    (ArchetypeID.TURTLE,       "speed",             5, "speed = lowest (slowest — compensates with durability)"),
    (ArchetypeID.TURTLE,       "attack_cooldown",   1, "attack_cooldown = highest (patient, punishes mistakes)"),
    (ArchetypeID.TURTLE,       "hp",                1, "hp = highest (living wall)"),
    (ArchetypeID.TURTLE,       "w_defend",          1, "P(GUARDA) = highest (absorbs instead of retreating)"),
]


def _check_structural_inter(chars) -> List[ArchetypeCheck]:
    arch_to_idx = {c.archetype.id: i for i, c in enumerate(chars)}
    checks = []
    for arch_id, attr_name, expected_rank, description in _INTER_ASSERTIONS:
        values = [_gene_value(c, attr_name) for c in chars]
        actual = _rank_against(values, arch_to_idx[arch_id], expected_rank)
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

# `range` é `range_` como propriedade do Character (evita a keyword).
_ATTR_BOUNDS: Dict[str, Tuple[float, float]] = {
    (f"{name}_" if name == "range" else name): bounds
    for name, bounds in zip(ATTRIBUTE_NAMES, ATTRIBUTE_BOUNDS)
}


def _norm(char, attr_name: str) -> float:
    # Mesma convenção do fitness (fitness.gene_drift): fração do RANGE do bound,
    # não do máximo — normalizar por `hi` subestima genes de `lo` alto. Convenção
    # única do projeto para "normalizado".
    lo, hi = _ATTR_BOUNDS[attr_name]
    return (getattr(char, attr_name) - lo) / (hi - lo)


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
    (ArchetypeID.GRAPPLER,     "guard_break",    1, "guard_break = highest (arranca dano pela guarda alheia)"),
]


def _check_behavioral(profile: Dict[ArchetypeID, Dict[str, float]]) -> List[ArchetypeCheck]:
    ids = ARCHETYPE_ORDER
    checks = []
    for arch_id, metric, expected_rank, description in _BEHAVIORAL_ASSERTIONS:
        values = [profile[aid][metric] for aid in ids]
        actual = _rank_against(values, ids.index(arch_id), expected_rank)
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
# Concordância de ranking comportamental (identidade funcional, contínua)
# ─────────────────────────────────────────────────────────────────────────────


def _kendall_tau_b(x: List[float], y: List[float]) -> float:
    """τ-b de Kendall: concordância entre duas ordens, corrigida para empates.
    1 = mesma ordem, −1 = ordem invertida, 0 = sem relação. Sem pares ordenáveis em
    alguma das duas (todos empatados), não há ordem a comparar: 0."""
    concordant = discordant = tied_x = tied_y = 0
    n = len(x)
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0:
                tied_x += 1
            if dy == 0:
                tied_y += 1
            if dx != 0 and dy != 0:
                if (dx > 0) == (dy > 0):
                    concordant += 1
                else:
                    discordant += 1
    pairs = n * (n - 1) // 2
    denom = math.sqrt((pairs - tied_x) * (pairs - tied_y))
    return (concordant - discordant) / denom if denom > 0 else 0.0


def rank_agreement(profile: Profile, reference: Profile) -> float:
    """Quanto a ORDEM dos 5 personagens em cada métrica comportamental repete a do
    roster de referência (o canônico): τ-b de Kendall por métrica, na média.

    Mede identidade funcional sem depender de uma asserção escrita à mão: não pergunta
    "o Zoner é o que luta mais longe?", pergunta se a ordem inteira — quem avança mais,
    quem guarda mais, quem trava mais, … — continua a do canônico. É relativa ao roster
    nos dois lados, então um deslocamento que afeta todos igual (oponentes mais lentos,
    lutas mais longas) não conta como perda de identidade."""
    taus = [
        _kendall_tau_b([reference[aid][key] for aid in ARCHETYPE_ORDER],
                       [profile[aid][key] for aid in ARCHETYPE_ORDER])
        for key in BEHAVIORAL_KEYS
    ]
    return sum(taus) / len(taus)


_CANONICAL_PROFILES: Dict[Tuple[int, int], Profile] = {}


def canonical_profile(n: int, seed: int) -> Profile:
    """O perfil comportamental do canônico sob `(n, seed)` — a referência da
    concordância, medida nas mesmas condições do roster comparado."""
    key = (n, seed)
    if key not in _CANONICAL_PROFILES:
        seed_combat(seed)
        _CANONICAL_PROFILES[key] = behavioral_profile(Individual.from_canonical(), n)
    return _CANONICAL_PROFILES[key]


# ─────────────────────────────────────────────────────────────────────────────
# Orquestração
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(
    individual: Individual, behavioral_n: int = 0, seed: int = 42
) -> ArchetypeValidationReport:
    """Valida identidade estrutural (Layers 1-2, sempre) e — se `behavioral_n>0` —
    funcional (Layer 3 e concordância de ranking, rodando `behavioral_n` sims/matchup
    sob `seed`)."""
    chars  = individual.characters
    checks: List[ArchetypeCheck] = []

    checks.extend(_check_structural_inter(chars))
    checks.extend(_check_structural_intra(chars))

    agreement = None
    if behavioral_n > 0:
        seed_combat(seed)
        profile = behavioral_profile(individual, behavioral_n)
        checks.extend(_check_behavioral(profile))
        agreement = rank_agreement(profile, canonical_profile(behavioral_n, seed))

    passed = sum(1 for c in checks if c.passed)
    return ArchetypeValidationReport(checks=checks, passed=passed, total=len(checks),
                                     rank_agreement=agreement)


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

    if report.rank_agreement is not None:
        print(f"\nCONCORDÂNCIA DE RANKING COMPORTAMENTAL (τ de Kendall médio vs canônico): "
              f"{report.rank_agreement:+.3f}")
        print("  1 = mesma ordem do canônico em todas as métricas · 0 = acaso · −1 = invertida")

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
                        help="Usa o melhor indivíduo salvo em single_run/ga.json (default: canônico)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="knee_point",
                        help="Usa representante do NSGA-II (knee_point|best_dominance|best_drift|ideal_point|scalar_optimum)")
    parser.add_argument("--n", type=int, default=200,
                        help="Sims/matchup da Layer 3 comportamental (0 = só estrutural)")
    parser.add_argument("--seed", type=int, default=42, help="Semente do combate da Layer 3")
    args = parser.parse_args()

    if args.nsga2:
        ind = Individual.from_nsga2(representative=args.nsga2)
        print(f"Validando indivíduo NSGA-II ({args.nsga2})...\n")
    elif args.evolved:
        ind = Individual.from_results()
        print("Validando indivíduo evoluído (single_run/ga.json)...\n")
    else:
        ind = Individual.from_canonical()
        print("Validando indivíduo canônico...\n")

    report = run_validation(ind, behavioral_n=args.n, seed=args.seed)
    print_report(report)
