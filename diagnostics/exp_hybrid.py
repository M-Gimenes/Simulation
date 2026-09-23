"""Híbrido com ORÇAMENTO IGUAL: NSGA-II por `g1` gerações, depois AG escalar por
`g2` gerações partindo da fronteira final — com `g1 + g2 = MAX_GENERATIONS`.

É o teste que separa "a decomposição em Pareto ajuda" de "o `from_nsga` só usou o
dobro do orçamento". A fase 2 continua o stream de avaliação em `generation_seed(seed,
g1 + g)`, então nenhuma geração reavalia um stream que a fase 1 já viu.
"""
import json
import sys

from src.engine import nsga2
from src.engine.config import POPULATION_SIZE, MAX_GENERATIONS

from diagnostics.exp_diag import run


def hybrid(seed, split=0.5, pop_size=POPULATION_SIZE, gens=MAX_GENERATIONS, carry="front"):
    g1 = int(gens * split)
    g2 = gens - g1
    res = nsga2.run(seed=seed, pop_size=pop_size, n_generations=g1, verbose=False)
    front = res.pareto_front
    init = front[:pop_size] if carry == "front" else [res.representatives[carry]]
    print(f"  [hybrid {seed}] fase 1: {g1} gens NSGA-II, fronteira {len(front)} pts "
          f"-> init {len(init)}", flush=True)
    out = run(seed, pop_size=pop_size, gens=g2, init=init, gen_offset=g1,
              log=f"hybrid {seed}")
    out.update(split=split, g1=g1, g2=g2, carry=carry, front_size=len(front))
    return out


if __name__ == "__main__":
    out_path = sys.argv[1]
    seeds = [int(s) for s in sys.argv[2].split(",")]
    kw = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    results = []
    for s in seeds:
        r = hybrid(s, **kw)
        results.append(r)
        print(f"hybrid seed {s}: reeval dom {r['reeval']['dom']:.4f} "
              f"drift {r['reeval']['drift']:.4f} "
              f"sum {r['reeval']['dom']+r['reeval']['drift']:.4f} hc {r['reeval']['hc']} "
              f"bal {r['reeval']['balanced']} ({r['elapsed']:.0f}s)", flush=True)
        json.dump(results, open(out_path, "w"))
