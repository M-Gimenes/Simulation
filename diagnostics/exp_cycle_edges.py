"""WR de cada aresta do ciclo autoral, aresta por aresta, a alta resolução — para o
canônico e para as 20 sementes do AG. Responde "quais arestas o equilíbrio quebra",
que a contagem agregada esconde."""
import functools
import json
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor

from src.engine import fitness as F
from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER
from src.engine.individual import Individual

BASES = [930000 + 41 * k for k in range(3)]
EDGES = [(w, l) for w in ARCHETYPE_ORDER for l in ARCHETYPES[w].beats]
NAME = {a: ARCHETYPES[a].name for a in ARCHETYPE_ORDER}


def edge_wrs(genes, base, sims):
    F.set_seed_base(base)
    d = F.evaluate_detail_n(Individual._from_genes(genes), sims)
    wr = {}
    for (i, j), w in d.matchup_winrates.items():
        wr[(ARCHETYPE_ORDER[i], ARCHETYPE_ORDER[j])] = w
    return [wr[(w, l)] if (w, l) in wr else 1 - wr[(l, w)] for w, l in EDGES]


def measure(genes, sims):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(functools.partial(edge_wrs, genes, sims=sims), BASES))
    return [st.mean(r[k] for r in res) for k in range(len(EDGES))]


if __name__ == "__main__":
    sims = int(sys.argv[1])
    canon = measure([c.genes() for c in Individual.from_canonical().characters], sims)
    ga = json.load(open("results/multi_run/multi_run_ga.json"))
    per_seed = [measure(r["genes"], sims) for r in ga["per_seed"]]
    sigma = (0.25 / (sims * len(BASES))) ** 0.5
    print(f"  {sims} lutas × {len(BASES)} sorteios → σ por aresta ≈ {sigma:.4f}; "
          f"'decidida' = |WR−0,5| > 2σ = {2 * sigma:.3f}\n")
    print(f"  {'aresta canônica':30} {'canônico':>9} {'AG (n=20)':>20} {'mantida':>9} {'decidida':>9}")
    for k, (w, l) in enumerate(EDGES):
        v = [s[k] for s in per_seed]
        m, sd = st.mean(v), st.stdev(v)
        kept = sum(x > 0.5 for x in v)
        dec = sum(abs(x - 0.5) > 2 * sigma for x in v)
        print(f"  {NAME[w] + ' > ' + NAME[l]:30} {canon[k]:9.3f} {m:12.3f} ±{sd:.3f} "
              f"{kept:6d}/20 {dec:8d}/20")
    tot = [sum(s[k] > 0.5 for k in range(len(EDGES))) for s in per_seed]
    print(f"\n  arestas mantidas por semente: média {st.mean(tot):.2f}/10  "
          f"min {min(tot)}  max {max(tot)}  (canônico {sum(x > 0.5 for x in canon)}/10)")
    json.dump({"canonical": canon, "per_seed": per_seed,
               "edges": [[NAME[w], NAME[l]] for w, l in EDGES]},
              open(f"diagnostics/data/cycle_edges_{sims}.json", "w"))
