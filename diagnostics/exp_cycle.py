"""Estrutura do torneio de matchups a alta resolução: tríades circulares, arestas do
ciclo autoral e quanto as arestas estão DECIDIDAS — as três juntas, porque tríade com
aresta indecisa é sorteio. Inclui os espelhos como piso de ruído: eles têm estrutura
real ZERO por construção, então a tríade que eles marcam é o que o ruído produz."""
import functools
import json
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from math import comb

from src.engine import fitness as F
from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER
from src.engine.individual import Individual

BASES = [920000 + 37 * k for k in range(3)]
EDGES = [(w, l) for w in ARCHETYPE_ORDER for l in ARCHETYPES[w].beats]


def structure(genes, base, sims):
    F.set_seed_base(base)
    d = F.evaluate_detail_n(Individual._from_genes(genes), sims)
    wr = {}
    wins = {a: 0.0 for a in ARCHETYPE_ORDER}
    for (i, j), w in d.matchup_winrates.items():
        a, b = ARCHETYPE_ORDER[i], ARCHETYPE_ORDER[j]
        wr[(a, b)] = w
        if w > 0.5:
            wins[a] += 1
        elif w < 0.5:
            wins[b] += 1
        else:
            wins[a] += 0.5
            wins[b] += 0.5
    triads = comb(5, 3) - sum(v * (v - 1) / 2 for v in wins.values())
    margins = sorted(abs(v - 0.5) for v in wr.values())
    kept = sum((wr[(w, l)] if (w, l) in wr else 1 - wr[(l, w)]) > 0.5 for w, l in EDGES)
    return triads, kept, st.median(margins), margins[0], margins[-1]


def rosters(spec):
    kind, name = spec.split(":", 1)
    if kind == "arm":
        return [(r["seed"], r["genes"]) for r in json.load(open(f"diagnostics/data/{name}.json"))]
    if kind == "mirror":
        out = []
        for aid in ARCHETYPE_ORDER:
            d = ARCHETYPES[aid]
            out.append((aid, [list(d.initial_attributes) + list(d.initial_weights)] * 5))
        return out
    if kind == "random":
        import random
        random.seed(int(name))
        return [(k, [c.genes() for c in Individual.random().characters]) for k in range(30)]
    if kind == "canonical":
        return [("canon", [c.genes() for c in Individual.from_canonical().characters])]
    art = json.load(open(f"results/{name}.json"))
    if "representatives" in art["per_seed"][0]:
        return [(r["seed"], r["representatives"]["scalar_optimum"]["genes"]) for r in art["per_seed"]]
    return [(r["seed"], r["genes"]) for r in art["per_seed"]]


if __name__ == "__main__":
    sims = int(sys.argv[1])
    print(f"  {sims} lutas/par, {len(BASES)} sorteios novos. Tríades: 0 = ordem estrita, "
          f"2,5 = torneio aleatório, 5 = máximo.\n")
    print(f"  {'braço':22} {'tríades':>9} {'arestas':>9} {'|WR-.5| med':>12} {'min':>7} {'max':>7}")
    for spec in sys.argv[2].split(","):
        rs = [r for r in rosters(spec) if not isinstance(r[0], int) or r[0] <= 46]
        acc = []
        for seed, genes in rs:
            with ProcessPoolExecutor(8) as ex:
                res = list(ex.map(functools.partial(structure, genes, sims=sims), BASES))
            acc.append([st.mean(x[k] for x in res) for k in range(5)])
        f = lambda k: st.mean(a[k] for a in acc)
        print(f"  {spec.split(':')[-1]:22} {f(0):9.2f} {f(1):8.2f}/10 {f(2):12.3f} "
              f"{f(3):7.3f} {f(4):7.3f}")
