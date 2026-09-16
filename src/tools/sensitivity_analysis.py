"""
Análise de sensibilidade — Δ WR por (arquétipo × atributo) ao perturbar genes em ±σ.

Responde "o AG enxerga este gene?": um gene cujo deslocamento de ±σ não move a WR não
tem gradiente de seleção. Usa pareamento de seeds — `seed_combat` fixa o mesmo stream
antes de `+σ` e `−σ` (common random numbers), isolando o efeito do gene do sorteio.

**O piso é medido, não estimado.** A versão anterior imprimia um piso binomial
analítico (`√(0.25/4·sims)`) que nem sequer entrava na classificação — ela usava
limiares fixos (≥5% visível, <3% neutro), então havia *dois critérios incompatíveis na
mesma tabela*. Pior, o piso analítico era o desvio de **uma** proporção, enquanto o
número classificado é uma **diferença** entre duas WRs.

Agora o piso é medido (`--null-reps`): o |Δ WR| entre duas avaliações do **mesmo roster,
sem perturbação nenhuma**, sob seeds diferentes. O Δ verdadeiro aí é zero por
construção, então tudo que aparece é ruído de amostragem — exatamente na grandeza que a
tabela classifica. É um piso **conservador**: a medição real usa CRN pareado e tem menos
ruído que isso, e superestimar o piso torna a classificação mais exigente, que é o lado
seguro. A classificação inteira sai desse número — critério único.

(As seeds precisam ser diferentes nas duas metades do par nulo: com a mesma seed e
perturbação zero as duas avaliações são bit-idênticas e o Δ sai exatamente 0, o que não
mediria nada.)

**Onde medir importa.** No canônico o roster é saturado (Rushdown ~100%, Turtle ~0%):
com a WR presa no teto, perturbar um gene não muda nada e quase tudo sai "neutro" — isso
é efeito de teto, não neutralidade. Use `--evolved` ou `--nsga2` para medir num roster
equilibrado, que é onde a afirmação "o AG enxerga o cromossomo" precisa valer.

Uso:
    py -m src.tools.sensitivity_analysis                  # canônico (saturado — ver acima)
    py -m src.tools.sensitivity_analysis --evolved        # roster equilibrado do AG
    py -m src.tools.sensitivity_analysis --nsga2 scalar_optimum
    py -m src.tools.sensitivity_analysis --sims 500 --null-reps 5
    py -m src.tools.sensitivity_analysis --workers 1
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from typing import List, Sequence, Tuple

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.combat import seed_combat
from src.engine.config import (
    ATTRIBUTE_BOUNDS,
    ATTRIBUTE_MUTATION_SIGMA,
    ATTRIBUTE_NAMES,
    N_WORKERS,
)
from src.engine.fitness import evaluate_detail_n
from src.engine.individual import Individual
from src.engine.paths import PROJECT_ROOT, SENSITIVITY_DIR, SENSITIVITY_PATH

Genes = Tuple[Tuple[float, ...], ...]
# (genes, personagem, atributo, sinal, magnitude do deslocamento, sims, seed).
# O sinal é campo próprio, não o sinal da magnitude: no par nulo a magnitude é 0 e as
# duas metades precisam continuar distinguíveis.
Task = Tuple[Genes, int, int, int, float, int, int]

NULL_REPS_DEFAULT = 3


def _genes_of(ind: Individual) -> Genes:
    return tuple(tuple(c.genes()) for c in ind.characters)


def _individual_from(genes: Genes) -> Individual:
    ind = Individual.from_canonical()
    for char, g in zip(ind.characters, genes):
        char.load_genes(list(g))
    return ind


def _eval_task(task: Task) -> float:
    genes, char_idx, attr_idx, sign, magnitude, sims, seed = task

    seed_combat(seed)  # mesmo seed em +σ e −σ → mesmos sorteios (common random numbers)
    ind = _individual_from(genes)
    char = ind.characters[char_idx]
    lo, hi = ATTRIBUTE_BOUNDS[attr_idx]
    delta = sign * magnitude
    char.attributes[attr_idx] = max(lo, min(hi, char.attributes[attr_idx] + delta))
    char.clip()
    ind.invalidate_fitness()

    detail = evaluate_detail_n(ind, sims=sims)
    return detail.winrates[char_idx]


def _classify(magnitude: float, floor: float) -> str:
    """Critério ÚNICO, ancorado no piso medido. Abaixo do que o ruído sozinho produz,
    o gene é indistinguível de nada; o dobro disso é o que chamamos de visível."""
    if magnitude <= floor:
        return "✗ neutro"
    if magnitude <= 2 * floor:
        return "~ borderline"
    return "✓ visível"


def _build_tasks(genes: Genes, sigmas: Sequence[float], sims: int, base_seed: int,
                 negative_seed_shift: int = 0) -> List[Task]:
    """`negative_seed_shift` != 0 quebra o pareamento de CRN de propósito — é o que a
    medição do piso usa (ver `_measure_noise_floor`)."""
    tasks: List[Task] = []
    for i in range(len(ARCHETYPE_ORDER)):
        for j in range(len(ATTRIBUTE_NAMES)):
            seed = base_seed + i * 100 + j
            tasks.append((genes, i, j, +1, sigmas[j], sims, seed))
            tasks.append((genes, i, j, -1, sigmas[j], sims, seed + negative_seed_shift))
    return tasks


def _run(tasks: List[Task], workers: int) -> List[float]:
    if workers == 1 or len(tasks) == 1:
        return [_eval_task(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_eval_task, tasks))


def _deltas_from(tasks: List[Task], results: List[float]) -> List[List[float]]:
    deltas = [[0.0] * len(ATTRIBUTE_NAMES) for _ in range(len(ARCHETYPE_ORDER))]
    for (_, char_idx, attr_idx, sign, _, _, _), wr in zip(tasks, results):
        deltas[char_idx][attr_idx] += sign * wr
    return deltas


def _measure_noise_floor(genes: Genes, sims: int, base_seed: int, reps: int,
                         workers: int) -> Tuple[float, float]:
    """Piso de ruído MEDIDO: |Δ WR| entre duas avaliações do MESMO roster, sem
    perturbação nenhuma, sob seeds diferentes.

    Por que seeds diferentes: com perturbação zero e o mesmo seed as duas avaliações
    são bit-idênticas e o Δ sai exatamente 0 — não mediria nada. Quebrando o pareamento
    obtém-se o ruído de amostragem de uma *diferença* entre duas WRs, que é exatamente a
    grandeza classificada na tabela.

    É um piso **conservador**: a medição real usa CRN pareado, que reduz o ruído abaixo
    disto. Superestimar o piso torna a classificação mais exigente — o lado seguro.

    Devolve `(máximo, média)`. O piso é o **máximo**: o maior efeito que a ausência de
    efeito conseguiu produzir."""
    zeros = [0.0] * len(ATTRIBUTE_NAMES)
    magnitudes: List[float] = []
    for rep in range(reps):
        tasks = _build_tasks(genes, zeros, sims, base_seed + 10_000 * (rep + 1),
                             negative_seed_shift=7919)   # primo: descola os streams
        deltas = _deltas_from(tasks, _run(tasks, workers))
        magnitudes += [abs(d) for row in deltas for d in row]
    return max(magnitudes), sum(magnitudes) / len(magnitudes)


def _load_individual(args: argparse.Namespace) -> Tuple[Individual, str]:
    if args.nsga2:
        return Individual.from_nsga2(representative=args.nsga2), f"NSGA-II ({args.nsga2})"
    if args.evolved:
        return Individual.from_results(), "EVOLUÍDO (results.json)"
    return Individual.from_canonical(), "CANÔNICO (saturado — ver docstring)"


def _save(args, label: str, sigmas: Sequence[float], deltas: List[List[float]],
          col_means: List[float], floor: float, floor_mean: float) -> None:
    """Grava a matriz Δ WR para que a tabela de sensibilidade tenha artefato
    (o console é volátil; a tabela é citada na validação metodológica)."""
    data = {
        "individual": label,
        "sims_per_matchup": args.sims,
        "sigma_mult": args.sigma_mult,
        "seed": args.seed,
        "null_reps": args.null_reps,
        "sigmas": dict(zip(ATTRIBUTE_NAMES, sigmas)),
        "noise_floor_measured": floor,
        "noise_floor_mean": floor_mean,
        "delta_wr": {
            ARCHETYPES[aid].name: dict(zip(ATTRIBUTE_NAMES, deltas[i]))
            for i, aid in enumerate(ARCHETYPE_ORDER)
        },
        "mean_abs_delta_wr": dict(zip(ATTRIBUTE_NAMES, col_means)),
        "classification": {
            attr: _classify(m, floor) for attr, m in zip(ATTRIBUTE_NAMES, col_means)
        },
    }
    SENSITIVITY_DIR.mkdir(parents=True, exist_ok=True)
    with open(SENSITIVITY_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print()
    print(f"  Salvo em {SENSITIVITY_PATH.relative_to(PROJECT_ROOT)}")


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--evolved", action="store_true",
                        help="mede no melhor indivíduo do AG (results.json)")
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
    sigmas = [
        ATTRIBUTE_MUTATION_SIGMA * (hi - lo) * args.sigma_mult
        for lo, hi in ATTRIBUTE_BOUNDS
    ]
    n_chars, n_attrs = len(ARCHETYPE_ORDER), len(ATTRIBUTE_NAMES)
    tasks = _build_tasks(genes, sigmas, args.sims, args.seed)

    print("─" * 80)
    workers_label = "serial" if args.workers == 1 else f"{args.workers} workers"
    print(f"  Análise de sensibilidade — {label}")
    print(f"  {args.sims} sims/matchup, σ × {args.sigma_mult}, {workers_label}")
    print(f"  {len(tasks)} avaliações ({n_chars} arquétipos × {n_attrs} atributos × 2 direções)")
    print("─" * 80)

    deltas = _deltas_from(tasks, _run(tasks, args.workers))

    for i, aid in enumerate(ARCHETYPE_ORDER):
        name = ARCHETYPES[aid].name
        for j, attr_name in enumerate(ATTRIBUTE_NAMES):
            print(f"  {name:14} {attr_name:18} σ={sigmas[j]:>6.2f}  Δ={deltas[i][j]:+.1%}")
        print()

    # ── Matriz ────────────────────────────────────────────────────────────────

    print("═" * 80)
    print("  Matriz |Δ WR|  (linha = arquétipo perturbado, coluna = atributo)")
    print("═" * 80)
    header = f"  {'':14}" + "".join(f"{n[:6]:>8}" for n in ATTRIBUTE_NAMES) + f"  {'média':>7}"
    print(header)
    print("  " + "─" * (len(header) - 2))

    col_means = [0.0] * n_attrs
    for i, aid in enumerate(ARCHETYPE_ORDER):
        row = [abs(d) for d in deltas[i]]
        print(f"  {ARCHETYPES[aid].name:14}"
              + "".join(f"{v:>8.1%}" for v in row)
              + f"  {sum(row)/n_attrs:>7.1%}")
        for j in range(n_attrs):
            col_means[j] += row[j] / n_chars

    print("  " + "─" * (len(header) - 2))
    print(f"  {'média':14}" + "".join(f"{m:>8.1%}" for m in col_means))

    # ── Piso medido e ranking ─────────────────────────────────────────────────

    print()
    print("═" * 80)
    print("  Ranking de sensibilidade — atributos por |Δ WR| médio")
    print("═" * 80)

    if args.null_reps > 0:
        print(f"  Medindo o piso de ruído: {args.null_reps} repetições com perturbação "
              f"ZERO...")
        floor, floor_mean = _measure_noise_floor(
            genes, args.sims, args.seed, args.null_reps, args.workers
        )
        print(f"  Piso MEDIDO: |Δ| máx {floor:.1%} · médio {floor_mean:.1%} "
              f"sobre {args.null_reps * n_chars * n_attrs} células sem perturbação.")
        print(f"  (|Δ| entre duas avaliações do MESMO roster sob seeds diferentes — o Δ")
        print(f"   verdadeiro é zero, então tudo que aparece é ruído de amostragem.")
        print(f"   Piso conservador: a medição real usa CRN pareado e tem menos ruído.)")
    else:
        floor = floor_mean = 0.0
        print("  Piso de ruído DESLIGADO (--null-reps 0) — classificação sem âncora.")
    print()

    for name, m in sorted(zip(ATTRIBUTE_NAMES, col_means), key=lambda x: x[1], reverse=True):
        print(f"    {name:18} {m:>6.1%}  {_classify(m, floor)}")
    print()
    print(f"  ✗ neutro ≤ {floor:.1%} (piso)   ~ borderline ≤ {2*floor:.1%}   ✓ visível acima")

    _save(args, label, sigmas, deltas, col_means, floor, floor_mean)


if __name__ == "__main__":
    main()
