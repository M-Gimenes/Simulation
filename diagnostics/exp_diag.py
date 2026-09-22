"""Harness de diagnóstico: réplica instrumentada do laço do AG escalar (ga.run) com
variantes. Não toca no código do projeto — importa o motor e reimplementa só o laço."""
import functools
import json
import random
import statistics as st
import sys
import time

import numpy as np

from src.engine import fitness as F
from src.engine import operators as O
from src.engine.combat import seed_combat
from src.engine.config import MULTI_RUN_VALIDATION_SEED, SIMS_PER_MATCHUP, MULTI_RUN_SIMS
from src.engine.individual import Individual


def detail_worker(ind, sims):
    d = F.evaluate_detail_n(ind, sims)
    t = d.dominance_terms
    return (d.fitness, d.dominance_penalty, d.drift_penalty, t.global_term, t.cap_term)


def evaluate_all(pop, sims):
    res = F.parallel_map(functools.partial(detail_worker, sims=sims), pop)
    for ind, r in zip(pop, res):
        ind.fitness = r[0]
        ind.objectives = (r[1], r[2])
        ind._terms = (r[3], r[4])


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def gen_stats(pop, gen):
    srt = sorted(pop, key=lambda i: i.fitness, reverse=True)
    best = srt[0]
    top = srt[: max(1, len(pop) // 10)]
    dr = [i.objectives[1] for i in pop]
    dm = [i.objectives[0] for i in pop]
    return {
        "gen": gen,
        "best_fit": best.fitness, "best_dom": best.objectives[0], "best_drift": best.objectives[1],
        "best_cap": best._terms[1],
        "pop_drift_med": st.median(dr), "pop_drift_p10": q(dr, 0.1), "pop_drift_min": min(dr),
        "pop_dom_med": st.median(dm), "pop_dom_p10": q(dm, 0.1),
        "top10_drift": st.mean(i.objectives[1] for i in top),
        "top10_dom": st.mean(i.objectives[0] for i in top),
        "mean_fit": st.mean(i.fitness for i in pop),
    }


def make_offspring(parents, n):
    out = []
    while len(out) < n:
        c = O.crossover(O.tournament_selection(parents), O.tournament_selection(parents))
        O.mutate(c)
        out.append(c)
    return out


def run(seed, pop_size=300, gens=150, survivor="generational", init=None, sims=SIMS_PER_MATCHUP,
        canonical=True, log=None):
    random.seed(seed); np.random.seed(seed); seed_combat(seed)
    F.set_seed_base(F.generation_seed(seed, 0))
    if init is None:
        seeded = [Individual.from_canonical()] if canonical else []
        pop = seeded + [Individual.random() for _ in range(pop_size - len(seeded))]
    else:
        pop = [i.clone() for i in init] + [Individual.random() for _ in range(pop_size - len(init))]
    evaluate_all(pop, sims)
    hist = []
    offspring = []
    t0 = time.time()
    for gen in range(gens):
        if survivor == "plus" and offspring:
            pop = sorted(pop, key=lambda i: i.fitness, reverse=True)[:pop_size]
        hist.append(gen_stats(pop, gen))
        if log and gen % 25 == 0:
            h = hist[-1]
            print(f"  [{log}] gen {gen} best dom {h['best_dom']:.4f} drift {h['best_drift']:.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        if survivor == "generational":
            pop = O.next_generation(pop)
        else:
            offspring = make_offspring(pop, pop_size)
            pop = pop + offspring
        F.set_seed_base(F.generation_seed(seed, gen + 1))
        for ind in pop:
            ind.invalidate_fitness()
        evaluate_all(pop, sims)
    if survivor == "plus":
        pop = sorted(pop, key=lambda i: i.fitness, reverse=True)[:pop_size]
    best = max(pop, key=lambda i: i.fitness)
    in_loop = best.objectives
    F.set_seed_base(MULTI_RUN_VALIDATION_SEED)
    d = F.evaluate_detail_n(best, MULTI_RUN_SIMS)
    hc = sum(F.is_hard_counter(w) for w in d.matchup_winrates.values())
    return {
        "seed": seed, "survivor": survivor, "gens": gens, "sims": sims,
        "in_loop": in_loop,
        "reeval": {"dom": d.dominance_penalty, "drift": d.drift_penalty,
                   "global": d.dominance_terms.global_term, "cap": d.dominance_terms.cap_term,
                   "hc": hc, "balanced": F.roster_balanced(d)},
        "genes": [c.genes() for c in best.characters],
        "history": hist, "elapsed": time.time() - t0,
    }


def nsga_point(seed, rep="scalar_optimum"):
    n = json.load(open("results/multi_run/multi_run_nsga2.json"))
    r = next(p for p in n["per_seed"] if p["seed"] == seed)
    return Individual._from_genes(r["representatives"][rep]["genes"])


if __name__ == "__main__":
    kind, out = sys.argv[1], sys.argv[2]
    seeds = [int(s) for s in sys.argv[3].split(",")]
    kw = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    results = []
    for s in seeds:
        if kind == "from_nsga":
            r = run(s, init=[nsga_point(s)], log=f"{kind} {s}", **kw)
        else:
            r = run(s, log=f"{kind} {s}", **kw)
        results.append(r)
        print(f"{kind} seed {s}: reeval dom {r['reeval']['dom']:.4f} drift {r['reeval']['drift']:.4f} "
              f"sum {r['reeval']['dom']+r['reeval']['drift']:.4f} hc {r['reeval']['hc']} "
              f"bal {r['reeval']['balanced']} ({r['elapsed']:.0f}s)", flush=True)
        json.dump(results, open(out, "w"))
