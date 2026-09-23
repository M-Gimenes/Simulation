"""O ciclo autoral medido na resolução que ele exige. As arestas de um roster
equilibrado têm margem mediana ~0,026; a 200 lutas (σ = 0,035) a direção de cada uma é
cara-ou-coroa, então `cycle_edges_kept` do `baselines.json` mede ruído, não ciclo. Aqui
cada par roda 16 × 1000 lutas (σ = 0,0040) e cada aresta sai classificada como decidida
ou indecisa — para o alvo, o canônico, as 20 sementes do AG e os nulos que dão o piso."""
import functools
import json
import statistics as st

from concurrent.futures import ProcessPoolExecutor
import random as _random

from src.engine.archetypes import ARCHETYPES, ARCHETYPE_ORDER
from src.engine.individual import Individual

from diagnostics.exp_cycle_edges import EDGES, NAME, edge_wrs

BASES = [940000 + 53 * k for k in range(16)]
SIMS = 1000
SIGMA = (0.25 / (SIMS * len(BASES))) ** 0.5


def measure(genes):
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(functools.partial(edge_wrs, genes, sims=SIMS), BASES))
    return [st.mean(r[k] for r in res) for k in range(len(EDGES))]


def summarize(wrs):
    kept = sum(w > 0.5 for w in wrs)
    decided = [w for w in wrs if abs(w - 0.5) > 2 * SIGMA]
    return {"kept": kept, "decided": len(decided),
            "kept_and_decided": sum(w > 0.5 + 2 * SIGMA for w in wrs),
            "median_margin": st.median(abs(w - 0.5) for w in wrs), "wrs": wrs}


def groups():
    ga = json.load(open("results/multi_run/multi_run_ga.json"))
    _random.seed(7)
    randoms = [[c.genes() for c in Individual.random().characters] for _ in range(30)]
    mirrors = [[list(ARCHETYPES[a].initial_attributes) + list(ARCHETYPES[a].initial_weights)] * 5
               for a in ARCHETYPE_ORDER]
    return {
        "alvo (single_run/ga.json)": [[c.genes() for c in Individual.from_results().characters]],
        "canônico": [[c.genes() for c in Individual.from_canonical().characters]],
        "AG escalar (20 sementes)": [r["genes"] for r in ga["per_seed"]],
        "aleatórios (30)": randoms,
        "espelhos (5)": mirrors,
    }


if __name__ == "__main__":
    print(f"  {SIMS} lutas × {len(BASES)} sorteios = {SIMS * len(BASES)} por par  →  "
          f"σ = {SIGMA:.4f}, decidida = |WR−0,5| > {2 * SIGMA:.4f}\n")
    print(f"  {'grupo':26} {'mantidas':>9} {'decididas':>10} {'mantidas E decididas':>21} "
          f"{'margem mediana':>15}")
    out = {}
    for label, rosters in groups().items():
        recs = [summarize(measure(g)) for g in rosters]
        out[label] = recs
        f = lambda k: st.mean(r[k] for r in recs)
        print(f"  {label:26} {f('kept'):8.2f}/10 {f('decided'):9.2f}/10 "
              f"{f('kept_and_decided'):20.2f}/10 {f('median_margin'):15.4f}")
    json.dump({"sigma": SIGMA, "sims_total": SIMS * len(BASES),
               "edges": [[NAME[w], NAME[l]] for w, l in EDGES], "groups": out},
              open("diagnostics/data/cycle_final.json", "w"))
