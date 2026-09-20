"""
Análise de sensibilidade — Δ WR por (arquétipo × gene) ao deslocar cada gene em 2σ.

Responde "o AG enxerga este gene?": um gene cujo deslocamento na escala da mutação não
move a WR não tem gradiente de seleção. Cobre os 11 genes — os 8 atributos e os 3 pesos
comportamentais —, cada um com o σ que a mutação usa nele. Usa pareamento de seeds: os
dois lados da janela são avaliados sob o mesmo seed-base, então cada luta dos dois recebe
os mesmos sorteios (common random numbers, uma semente por luta — ver
`fitness.fight_seed`), isolando o efeito do gene do sorteio.

**A janela tem sempre 2σ.** O deslocamento vai de `x − σ` a `x + σ`; se isso sai do
bound, a janela DESLIZA para dentro dele, mantendo a largura. Cortá-la no bound mediria,
num gene encostado no limite (o `attack_cooldown` do Rushdown, o `stun` do Combo
Master), um deslocamento de σ contra 2σ dos outros — e o gene pareceria menos visível só
por estar na borda.

**O piso é medido, e na mesma estatística que é classificada.** O número classificado
de cada gene é a média, sobre os 5 personagens, de |Δ WR|. O piso (`--null-reps`) roda
exatamente isso sob a hipótese nula — janela de largura ZERO, os dois lados sob seeds
diferentes — e fica com o maior valor que o ruído sozinho produziu nessa estatística. Um
piso tirado de células isoladas seria de outra grandeza: a média de 5 |Δ| varia bem
menos que uma célula só.

(As seeds precisam ser diferentes nos dois lados do par nulo: com a mesma seed e
deslocamento zero as duas avaliações são bit-idênticas e o Δ sai exatamente 0. Quebrar o
pareamento deixa o piso conservador — a medição real usa CRN pareado e tem menos ruído —,
e superestimar o piso torna a classificação mais exigente, que é o lado seguro.)

**Onde medir importa.** No canônico o roster é saturado (Rushdown ~100%, Turtle ~0%):
com a WR presa no teto, deslocar um gene não muda nada e quase tudo sai "neutro" — isso
é efeito de teto, não neutralidade. Use `--evolved` ou `--nsga2` para medir num roster
equilibrado, que é onde a afirmação "o AG enxerga o cromossomo" precisa valer.

Uso:
    py -m src.experiments.sensitivity_analysis                  # canônico (saturado — ver acima)
    py -m src.experiments.sensitivity_analysis --evolved        # roster equilibrado do AG
    py -m src.experiments.sensitivity_analysis --nsga2 scalar_optimum
    py -m src.experiments.sensitivity_analysis --sims 500 --null-reps 5
    py -m src.experiments.sensitivity_analysis --workers 1
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from typing import List, Sequence, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.config import (
    ATTRIBUTE_BOUNDS,
    ATTRIBUTE_MUTATION_SIGMA,
    GENE_BOUNDS,
    GENE_NAMES,
    N_WORKERS,
    WEIGHT_BOUNDS,
    WEIGHT_MUTATION_SIGMA,
)
from src.engine.fitness import evaluate_detail_n, set_seed_base
from src.engine.individual import Individual
from src.engine.paths import PROJECT_ROOT, SENSITIVITY_DIR, SENSITIVITY_PATH
from src.engine.provenance import stamp

Genes = Tuple[Tuple[float, ...], ...]
# (genes, personagem, gene, valor do gene nesta avaliação, sims, seed)
Task = Tuple[Genes, int, int, float, int, int]

NULL_REPS_DEFAULT = 3
N_GENES = len(GENE_NAMES)


def _genes_of(ind: Individual) -> Genes:
    return tuple(tuple(c.genes()) for c in ind.characters)


def _individual_from(genes: Genes) -> Individual:
    ind = Individual.from_canonical()
    for char, g in zip(ind.characters, genes):
        char.load_genes(list(g))
    return ind


def mutation_sigmas(sigma_mult: float = 1.0) -> List[float]:
    """O σ da mutação em cada um dos 11 genes, na ordem de `GENE_NAMES`."""
    return (
        [ATTRIBUTE_MUTATION_SIGMA * (hi - lo) * sigma_mult for lo, hi in ATTRIBUTE_BOUNDS]
        + [WEIGHT_MUTATION_SIGMA * (hi - lo) * sigma_mult for lo, hi in WEIGHT_BOUNDS]
    )


def window(value: float, sigma: float, bounds: Tuple[float, float]) -> Tuple[float, float]:
    """`(x − σ, x + σ)`, deslizada para dentro do bound sem perder a largura 2σ."""
    lo, hi = bounds
    low, high = value - sigma, value + sigma
    if high > hi:
        low, high = low - (high - hi), hi
    if low < lo:
        low, high = lo, high + (lo - low)
    return low, high


def _eval_task(task: Task) -> float:
    genes, char_idx, gene_idx, value, sims, seed = task
    set_seed_base(seed)   # mesmo seed nos dois lados → mesmos sorteios (CRN)
    ind = _individual_from(genes)
    char = ind.characters[char_idx]
    shifted = char.genes()
    shifted[gene_idx] = value
    char.load_genes(shifted)
    return evaluate_detail_n(ind, sims=sims).winrates[char_idx]


def _classify(magnitude: float, floor: float) -> str:
    """Critério ÚNICO, ancorado no piso medido. Abaixo do que o ruído sozinho produz,
    o gene é indistinguível de nada; o dobro disso é o que chamamos de visível."""
    if magnitude <= floor:
        return "✗ neutro"
    if magnitude <= 2 * floor:
        return "~ borderline"
    return "✓ visível"


def _build_tasks(genes: Genes, sigmas: Sequence[float], sims: int, base_seed: int,
                 high_side_seed_shift: int = 0) -> List[Task]:
    """Dois lados por (personagem, gene): o alto primeiro, o baixo depois.
    `high_side_seed_shift` != 0 quebra o pareamento de CRN de propósito — é o que a
    medição do piso usa (ver `_measure_noise_floor`)."""
    tasks: List[Task] = []
    for i in range(len(ARCHETYPE_ORDER)):
        for j in range(N_GENES):
            seed = base_seed + i * 100 + j
            low, high = window(genes[i][j], sigmas[j], GENE_BOUNDS[j])
            tasks.append((genes, i, j, high, sims, seed + high_side_seed_shift))
            tasks.append((genes, i, j, low, sims, seed))
    return tasks


def _run(tasks: List[Task], workers: int) -> List[float]:
    if workers == 1 or len(tasks) == 1:
        return [_eval_task(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_eval_task, tasks))


def _deltas_from(results: List[float]) -> List[List[float]]:
    """Δ WR = WR(alto) − WR(baixo), por personagem × gene."""
    pairs = iter(zip(results[0::2], results[1::2]))
    return [[high - low for high, low in (next(pairs) for _ in range(N_GENES))]
            for _ in range(len(ARCHETYPE_ORDER))]


def column_means(deltas: List[List[float]]) -> List[float]:
    """A estatística classificada: por gene, a média sobre os personagens de |Δ WR|."""
    return [sum(abs(row[j]) for row in deltas) / len(deltas) for j in range(N_GENES)]


def _measure_noise_floor(genes: Genes, sims: int, base_seed: int, reps: int,
                         workers: int) -> Tuple[float, float]:
    """Piso de ruído MEDIDO, na estatística que a tabela classifica: a média sobre os
    personagens de |Δ WR| com janela de largura ZERO, os dois lados sob seeds
    diferentes. O Δ verdadeiro é zero por construção, então tudo que aparece é ruído.

    Devolve `(máximo, média)` sobre as `reps × 11` médias nulas. O piso é o **máximo**:
    o maior efeito que a ausência de efeito conseguiu produzir."""
    zeros = [0.0] * N_GENES
    nulls: List[float] = []
    for rep in range(reps):
        tasks = _build_tasks(genes, zeros, sims, base_seed + 10_000 * (rep + 1),
                             high_side_seed_shift=7919)   # primo: descola os streams
        nulls += column_means(_deltas_from(_run(tasks, workers)))
    return max(nulls), sum(nulls) / len(nulls)


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return (Individual.from_nsga2(representative=args.nsga2, require_current=True),
                f"NSGA-II ({args.nsga2})")
    if args.evolved:
        return Individual.from_results(require_current=True), "EVOLUÍDO (single_run/ga.json)"
    return Individual.from_canonical(), "CANÔNICO (saturado — ver docstring)"


def _save(args, label: str, sigmas: Sequence[float], deltas: List[List[float]],
          means: List[float], floor: float, floor_mean: float) -> None:
    """Grava a matriz Δ WR para que a tabela de sensibilidade tenha artefato
    (o console é volátil; a tabela é citada na validação metodológica)."""
    data = {
        "individual": label,
        "sims_per_matchup": args.sims,
        "sigma_mult": args.sigma_mult,
        "seed": args.seed,
        "null_reps": args.null_reps,
        "sigmas": dict(zip(GENE_NAMES, sigmas)),
        "noise_floor_measured": floor,
        "noise_floor_mean": floor_mean,
        "delta_wr": {
            ARCHETYPES[aid].name: dict(zip(GENE_NAMES, deltas[i]))
            for i, aid in enumerate(ARCHETYPE_ORDER)
        },
        "mean_abs_delta_wr": dict(zip(GENE_NAMES, means)),
        "classification": {
            gene: _classify(m, floor) for gene, m in zip(GENE_NAMES, means)
        },
    }
    SENSITIVITY_DIR.mkdir(parents=True, exist_ok=True)
    with open(SENSITIVITY_PATH, "w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(tool=__spec__.name), **data}, fh, indent=2, ensure_ascii=False)
    print()
    print(f"  Salvo em {SENSITIVITY_PATH.relative_to(PROJECT_ROOT)}")


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--evolved", action="store_true",
                        help="mede no melhor indivíduo do AG (single_run/ga.json)")
    parser.add_argument("--nsga2", metavar="REP", nargs="?", const="scalar_optimum",
                        help="mede num representante do NSGA-II (knee_point|"
                             "best_dominance|best_drift|ideal_point|scalar_optimum)")
    parser.add_argument("--sims", type=int, default=200)
    parser.add_argument("--sigma-mult", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--null-reps", type=int, default=NULL_REPS_DEFAULT,
                        help=f"repetições da medição do piso de ruído "
                             f"(default: {NULL_REPS_DEFAULT}; 0 desliga)")
    # Default = N_WORKERS, não None: com todos os núcleos os processos carregando
    # llvmlite estouram o limite de commit do Windows (WinError 1455) — ver config.py.
    parser.add_argument("--workers", type=int, default=N_WORKERS)
    return parser


def main() -> None:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    args = _build_argparser().parse_args()

    individual, label = _load_individual(args)
    genes = _genes_of(individual)
    sigmas = mutation_sigmas(args.sigma_mult)
    n_chars = len(ARCHETYPE_ORDER)
    tasks = _build_tasks(genes, sigmas, args.sims, args.seed)

    print("─" * 80)
    workers_label = "serial" if args.workers == 1 else f"{args.workers} workers"
    print(f"  Análise de sensibilidade — {label}")
    print(f"  {args.sims} sims/matchup, janela 2σ (σ da mutação × {args.sigma_mult}), "
          f"{workers_label}")
    print(f"  {len(tasks)} avaliações ({n_chars} arquétipos × {N_GENES} genes × 2 lados)")
    print("─" * 80)

    deltas = _deltas_from(_run(tasks, args.workers))

    for i, aid in enumerate(ARCHETYPE_ORDER):
        name = ARCHETYPES[aid].name
        for j, gene in enumerate(GENE_NAMES):
            print(f"  {name:14} {gene:18} σ={sigmas[j]:>6.3f}  Δ={deltas[i][j]:+.1%}")
        print()

    # ── Matriz ────────────────────────────────────────────────────────────────

    print("═" * 104)
    print("  Matriz |Δ WR|  (linha = arquétipo perturbado, coluna = gene)")
    print("═" * 104)
    header = f"  {'':14}" + "".join(f"{n[:7]:>8}" for n in GENE_NAMES)
    print(header)
    print("  " + "─" * (len(header) - 2))
    for i, aid in enumerate(ARCHETYPE_ORDER):
        print(f"  {ARCHETYPES[aid].name:14}" + "".join(f"{abs(d):>8.1%}" for d in deltas[i]))
    means = column_means(deltas)
    print("  " + "─" * (len(header) - 2))
    print(f"  {'média':14}" + "".join(f"{m:>8.1%}" for m in means))

    # ── Piso medido e ranking ─────────────────────────────────────────────────

    print()
    print("═" * 80)
    print("  Ranking de sensibilidade — genes por |Δ WR| médio")
    print("═" * 80)

    if args.null_reps > 0:
        print(f"  Medindo o piso de ruído: {args.null_reps} repetições com janela ZERO...")
        floor, floor_mean = _measure_noise_floor(
            genes, args.sims, args.seed, args.null_reps, args.workers
        )
        print(f"  Piso MEDIDO: máx {floor:.1%} · médio {floor_mean:.1%} sobre "
              f"{args.null_reps * N_GENES} médias nulas (mesma estatística do ranking).")
        print("  (Média sobre os personagens de |Δ WR| entre duas avaliações do MESMO")
        print("   roster sob seeds diferentes — o Δ verdadeiro é zero, então tudo que")
        print("   aparece é ruído. Conservador: a medição real usa CRN pareado.)")
    else:
        floor = floor_mean = 0.0
        print("  Piso de ruído DESLIGADO (--null-reps 0) — classificação sem âncora.")
    print()

    for gene, m in sorted(zip(GENE_NAMES, means), key=lambda x: x[1], reverse=True):
        print(f"    {gene:18} {m:>6.1%}  {_classify(m, floor)}")
    print()
    print(f"  ✗ neutro ≤ {floor:.1%} (piso)   ~ borderline ≤ {2*floor:.1%}   ✓ visível acima")

    _save(args, label, sigmas, deltas, means, floor, floor_mean)


if __name__ == "__main__":
    main()
