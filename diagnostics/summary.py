"""A tabela consolidada: cada braço nas 7 métricas do protocolo, sobre as mesmas
sementes. Lê os artefatos da bateria e os `*_scored.json` dos braços de diagnóstico."""
import json
import os
import statistics as st
import sys

R = "results"
D = "diagnostics/data"
COLS = [("dominance_penalty", "dom", ".4f"), ("drift_penalty", "drift", ".4f"),
        ("n_hard_counters", "hc", ".1f"), ("validator_structural", "L1+2", ".1f"),
        ("validator_behavioral", "L3", ".2f"), ("rank_agreement", "tau", "+.3f")]


def load_battery(seeds):
    g = json.load(open(f"{R}/multi_run/multi_run_ga.json"))
    n = json.load(open(f"{R}/multi_run/multi_run_nsga2.json"))
    c = json.load(open(f"{R}/controls/multi_run_ga_drift0_dom1.json"))
    u = json.load(open(f"{R}/controls/multi_run_ga_unseeded.json"))
    keep = lambda rs: [r for r in rs if r["seed"] in seeds]
    return {
        "AG escalar":  keep(g["per_seed"]),
        "NSGA-II so":  keep([dict(r["representatives"]["scalar_optimum"], seed=r["seed"])
                             for r in n["per_seed"]]),
        "ctrl λ=0":    keep(c["per_seed"]),
        "ctrl s/seed": keep(u["per_seed"]),
    }


def load_arm(name, seeds):
    p = f"{D}/{name}_scored.json"
    if not os.path.exists(p):
        return None
    rows = json.load(open(p))
    raw = json.load(open(f"{D}/{name}.json"))
    for row, r in zip(rows, raw):
        row["seed"] = r["seed"]
    return [r for r in rows if r["seed"] in seeds]


def show(label, rs):
    if not rs:
        return
    out = f"  {label:14s} n={len(rs):2d}"
    for key, _, fmt in COLS:
        out += f"  {st.mean(r[key] for r in rs):{fmt}}"
    out += f"   {sum(r['roster_balanced'] for r in rs)}/{len(rs)}"
    out += f"   {st.mean(r['dominance_penalty'] + r['drift_penalty'] for r in rs):.4f}"
    print(out)


if __name__ == "__main__":
    seeds = set(int(s) for s in sys.argv[1].split(",")) if len(sys.argv) > 1 else {42, 43, 44, 45, 46}
    arms = sys.argv[2].split(",") if len(sys.argv) > 2 else ["from_nsga", "plus", "g300", "hybrid"]
    print(f"\n  sementes {sorted(seeds)}")
    header = "  " + f"{'braço':14s} {'n':4s}" + "".join(f"  {lab:>6s}" for _, lab, _ in COLS)
    print(header + "    bal     soma")
    print("  " + "─" * (len(header) + 16))
    for label, rs in load_battery(seeds).items():
        show(label, rs)
    print()
    for name in arms:
        show(name, load_arm(name, seeds))
