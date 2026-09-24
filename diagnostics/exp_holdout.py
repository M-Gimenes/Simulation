"""O equilíbrio de um braço sobrevive fora do stream? Reavalia cada roster com
`sims` lutas por par em vários streams nunca vistos e reporta média, desvio e
quantos pares saem da banda de counter — a mesma pergunta da validação externa,
barata o bastante para rodar sobre os braços de diagnóstico."""
import functools
import json
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor

from src.engine import fitness as F
from src.engine.individual import Individual

BASES = [810000 + 31 * k for k in range(4)]


def measure(genes, base, sims):
    F.set_seed_base(base)
    d = F.evaluate_detail_n(Individual._from_genes(genes), sims)
    return (d.dominance_penalty, d.drift_penalty,
            sum(F.is_hard_counter(w) for w in d.matchup_winrates.values()),
            F.roster_balanced(d))


def rosters(spec):
    kind, name = spec.split(":", 1)
    if kind == "arm":
        return [(r["seed"], r["genes"]) for r in json.load(open(f"diagnostics/data/{name}.json"))]
    art = json.load(open(f"results/{name}.json"))
    if "representatives" in art["per_seed"][0]:
        return [(r["seed"], r["representatives"]["scalar_optimum"]["genes"]) for r in art["per_seed"]]
    return [(r["seed"], r["genes"]) for r in art["per_seed"]]


if __name__ == "__main__":
    sims = int(sys.argv[1])
    out = {}
    for spec in sys.argv[2].split(","):
        rs = rosters(spec)
        rs = [r for r in rs if r[0] <= 46]
        agg = []
        for seed, genes in rs:
            with ProcessPoolExecutor(8) as ex:
                res = list(ex.map(functools.partial(measure, genes, sims=sims), BASES))
            dom = [x[0] for x in res]
            agg.append((seed, st.mean(dom), st.stdev(dom), res[0][1],
                        st.mean(x[2] for x in res), sum(x[3] for x in res)))
            print(f"  {spec:24} seed {seed}: dom {st.mean(dom):.4f} ±{st.stdev(dom):.4f} "
                  f"drift {res[0][1]:.4f} hc {st.mean(x[2] for x in res):.2f} "
                  f"bal {sum(x[3] for x in res)}/{len(BASES)}", flush=True)
        print(f"{spec:24} MEDIA: dom {st.mean(a[1] for a in agg):.4f} "
              f"drift {st.mean(a[3] for a in agg):.4f} "
              f"soma {st.mean(a[1] + a[3] for a in agg):.4f} "
              f"hc {st.mean(a[4] for a in agg):.2f} "
              f"bal {sum(a[5] for a in agg)}/{len(agg) * len(BASES)}\n", flush=True)
        out[spec] = agg
    json.dump(out, open(f"diagnostics/data/holdout_{sims}.json", "w"))
