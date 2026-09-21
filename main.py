"""
Ponto de entrada do experimento.
Rode com: py main.py [--algorithm ga|nsga2] [--seed N] [--quiet] [--log-every N]
"""

import argparse
import datetime

from src.engine.config import MAX_GENERATIONS, POPULATION_SIZE
from src.engine.ga import run as run_ga, save_results as save_ga_results
from src.engine.paths import GA_RESULTS_PATH, NSGA2_PLOTS_DIR, NSGA2_RESULTS_PATH, PROJECT_ROOT
from src.engine.provenance import override_budget


def parse_args():
    parser = argparse.ArgumentParser(description="AG para balanceamento de personagens")
    parser.add_argument("--algorithm", choices=["ga", "nsga2"], default="ga",
                        help="Algoritmo evolutivo (default: ga)")
    parser.add_argument("--seed",      type=int, default=None, help="Semente aleatória")
    parser.add_argument("--quiet",     action="store_true",    help="Suprime log por geração")
    parser.add_argument("--log-every", type=int, default=1,    help="Loga a cada N gerações (só AG)")
    parser.add_argument("--pop", type=int, default=POPULATION_SIZE,
                        help=f"Tamanho da população (default: {POPULATION_SIZE})")
    parser.add_argument("--generations", type=int, default=MAX_GENERATIONS,
                        help=f"Gerações (default: {MAX_GENERATIONS})")
    return parser.parse_args()


def _main_ga(args):
    from src.visualization.ga_plots import save_plots_from_results as save_ga_plots_from_results

    override_budget(args.pop, args.generations, "ga")
    result = run_ga(
        seed=args.seed,
        verbose=not args.quiet,
        log_every=args.log_every,
        pop_size=args.pop,
        n_generations=args.generations,
    )

    GA_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_ga_results(result, GA_RESULTS_PATH)
    plot = save_ga_plots_from_results(GA_RESULTS_PATH)

    d = result.best_detail
    print(f"\nParada: {result.stop_reason} (geração {result.generation})")
    print(f"fitness={result.best.fitness:+.4f}  dom={d.dominance_penalty:.4f}  drift={d.drift_penalty:.4f}")
    print(f"Salvo em {GA_RESULTS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Curvas de convergência em {plot.relative_to(PROJECT_ROOT)}")
    print("→ py -m src.analysis.report --evolved")


def _main_nsga2(args):
    from src.engine.config import HYPERVOLUME_REFERENCE
    from src.engine.nsga2 import run as run_nsga2, save_results
    from src.engine.pareto_metrics import hypervolume_2d, spacing
    from src.visualization.nsga2_plots import save_plots

    override_budget(args.pop, args.generations, "nsga2")
    result = run_nsga2(seed=args.seed, verbose=not args.quiet,
                       pop_size=args.pop, n_generations=args.generations)

    NSGA2_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_results(result, NSGA2_RESULTS_PATH)
    print(f"\nFronteira salva em {NSGA2_RESULTS_PATH.relative_to(PROJECT_ROOT)}  ({len(result.pareto_front)} indivíduos)")

    objs = [ind.objectives for ind in result.pareto_front]
    hv = hypervolume_2d(objs, HYPERVOLUME_REFERENCE)
    sp = spacing(objs)
    print(f"Hipervolume (ref={HYPERVOLUME_REFERENCE}): {hv:.4f}  |  spacing: {sp:.4f}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = NSGA2_PLOTS_DIR / timestamp
    save_plots(result, outdir)
    print(f"Plots salvos em {outdir.relative_to(PROJECT_ROOT)}")

    print("\n=== Representantes da fronteira ===\n")
    for name, ind in result.representatives.items():
        dom, drift = ind.objectives
        print(f"  {name:15s}  dom={dom:.4f}  drift={drift:.4f}")
    print("\n→ py -m src.analysis.report --nsga2 [knee_point|best_dominance|best_drift|ideal_point]")


def main():
    args = parse_args()
    if args.algorithm == "ga":
        _main_ga(args)
    else:
        _main_nsga2(args)


if __name__ == "__main__":
    main()
