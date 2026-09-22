import functools, json, statistics as st, sys
from src.engine import fitness as F
from src.engine.individual import Individual
from src.engine.config import SIMS_PER_MATCHUP

def w(ind, base, sims):
    F.set_seed_base(base)
    d = F.evaluate_detail_n(ind, sims)
    return d.dominance_penalty, d.drift_penalty, d.dominance_terms.global_term, d.dominance_terms.cap_term

if __name__ == "__main__":
    g = json.load(open("results/multi_run/multi_run_ga.json")); n = json.load(open("results/multi_run/multi_run_nsga2.json"))
    out = {}
    for s in [42, 43, 44, 45, 46]:
        ga = Individual._from_genes(next(p for p in g["per_seed"] if p["seed"] == s)["genes"])
        ns = Individual._from_genes(next(p for p in n["per_seed"] if p["seed"] == s)["representatives"]["scalar_optimum"]["genes"])
        for lab, ind in [("ga", ga), ("nsga", ns)]:
            for sims in [SIMS_PER_MATCHUP, 1000]:
                bases = [700000 + 17 * k for k in range(30 if sims == SIMS_PER_MATCHUP else 8)]
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor(8) as ex:
                    r = list(ex.map(functools.partial(w, ind, sims=sims), bases))
                dom = [x[0] for x in r]
                out[f"{s}-{lab}-{sims}"] = r
                print(f"seed {s} {lab:4} sims {sims:4}: dom mean {st.mean(dom):.4f} sd {st.stdev(dom):.4f} min {min(dom):.4f} | drift {r[0][1]:.4f} | glob {st.mean(x[2] for x in r):.4f} cap {st.mean(x[3] for x in r):.4f}", flush=True)
    json.dump(out, open(sys.argv[1], "w"))
