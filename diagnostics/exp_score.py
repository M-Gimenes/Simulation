import json, sys, glob, statistics as st
from src.experiments.multi_run import _roster_record
from src.engine.individual import Individual
from src.engine.config import MULTI_RUN_SIMS
if __name__ == "__main__":
    S = sys.argv[1]
    for name in sys.argv[2].split(","):
        rows = []
        for r in json.load(open(f"{S}/{name}.json")):
            rec = _roster_record(Individual._from_genes(r["genes"]), MULTI_RUN_SIMS)
            rows.append(rec)
            print(f"{name:9} {r['seed']}: dom {rec['dominance_penalty']:.4f} drift {rec['drift_penalty']:.4f} hc {rec['n_hard_counters']} bal {rec['roster_balanced']} L12 {rec['validator_structural']} L3 {rec['validator_behavioral']} tau {rec['rank_agreement']:+.3f}", flush=True)
        json.dump(rows, open(f"{S}/{name}_scored.json", "w"))
