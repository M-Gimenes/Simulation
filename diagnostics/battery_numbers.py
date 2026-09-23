"""Todo número que os docs citam, extraído dos artefatos — para atualizar a redação
contra o disco em vez de contra a memória.

Não é ferramenta do protocolo: não grava nada e não entra no carimbo. Existe porque uma
bateria nova troca ~80 números espalhados por 20 arquivos .md, e atualizá-los à mão é
exatamente como se introduz um número errado que depois ninguém acha.

Uso:  py -m diagnostics.battery_numbers
"""

import json
import statistics as st
from pathlib import Path

from src.engine.paths import RESULTS_DIR

W = 78


def _load(rel):
    p = RESULTS_DIR / rel
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def head(title):
    print(f"\n{'═' * W}\n  {title}\n{'═' * W}")


def med(runs, field):
    return st.median(r[field] for r in runs)


def mean_sd(runs, field):
    xs = [r[field] for r in runs]
    return st.mean(xs), (st.stdev(xs) if len(xs) > 1 else 0.0)


def per_seed(art, rep=None):
    if art is None:
        return []
    if rep:
        return [dict(r["representatives"][rep], seed=r["seed"]) for r in art["per_seed"]]
    return art["per_seed"]


def arm_block(label, runs):
    if not runs:
        print(f"  {label:<26} (ausente)")
        return
    cells = []
    for field, fmt in [("dominance_penalty", ".4f"), ("drift_penalty", ".4f"),
                       ("n_hard_counters", ".2f"), ("validator_structural", ".1f"),
                       ("validator_behavioral", ".2f"), ("rank_agreement", "+.3f")]:
        m, s = mean_sd(runs, field)
        cells.append(f"{m:{fmt}}±{s:.3f}")
    bal = sum(r["roster_balanced"] for r in runs)
    print(f"  {label:<26} " + "  ".join(f"{c:>14}" for c in cells) + f"  bal {bal}/{len(runs)}")


def _metrics(d):
    """Uma métrica constante na amostra conjunta sai da família e não tem teste — ela
    aparece com p e Â₁₂ nulos, e imprimir `None` formatado quebraria."""
    for m in d["metrics"]:
        sig = "*" if m.get("significant") else " "
        p = f"{m['p_holm']:.2e}" if m.get("p_holm") is not None else "  (fora)"
        a12 = f"{m['a12_a_vs_b']:.2f}" if m.get("a12_a_vs_b") is not None else "  —"
        print(f"    {sig} {m['metric']:<24} {m['median_a']:>9.4f} vs {m['median_b']:>9.4f}"
              f"   p_holm {p:>9}   Â₁₂ {a12}   {m.get('effect_magnitude', '')}")


def main():
    ga = _load("multi_run/multi_run_ga.json")
    ns = _load("multi_run/multi_run_nsga2.json")
    hy = None
    for p in (RESULTS_DIR / "controls").glob("multi_run_hybrid_*.json"):
        hy = json.loads(p.read_text(encoding="utf-8"))
    c0 = _load("controls/multi_run_ga_drift0_dom1.json")
    cu = _load("controls/multi_run_ga_unseeded.json")

    head("AGREGADO POR BRAÇO (média ± desvio sobre as sementes)")
    print(f"  {'braço':<26} " + "  ".join(f"{h:>14}" for h in
          ["dominance", "drift", "counters", "L1+L2", "L3", "τ"]))
    print("  " + "─" * (W - 2))
    arm_block("AG escalar", per_seed(ga))
    arm_block("NSGA-II scalar_optimum", per_seed(ns, "scalar_optimum"))
    arm_block("híbrido", per_seed(hy))
    arm_block("controle λ_drift = 0", per_seed(c0))
    arm_block("controle sem semente", per_seed(cu))

    if ga:
        head("MEDIANAS (o que o teste pareado reporta)")
        for label, runs in [("AG escalar", per_seed(ga)),
                            ("NSGA-II so", per_seed(ns, "scalar_optimum")),
                            ("híbrido", per_seed(hy)),
                            ("controle λ=0", per_seed(c0)),
                            ("controle s/semente", per_seed(cu))]:
            if not runs:
                continue
            print(f"  {label:<22} dom {med(runs,'dominance_penalty'):.4f}  "
                  f"drift {med(runs,'drift_penalty'):.4f}  "
                  f"hc {med(runs,'n_hard_counters'):.1f}  "
                  f"L1+2 {med(runs,'validator_structural'):.1f}  "
                  f"L3 {med(runs,'validator_behavioral'):.1f}  "
                  f"τ {med(runs,'rank_agreement'):+.4f}")

        head("CONVERGÊNCIA E AJUSTE AO STREAM (AG escalar)")
        conv = ga["aggregate"]["convergence"]
        print(f"  taxa {conv['converged_rate']:.0%}  geração média "
              f"{conv['converged_at']['mean']:.1f} ± {conv['converged_at']['std']:.1f}")
        print(f"  gate disparou {conv['gate_fired']}, confirmação recusou "
              f"{conv['gate_rejected']} ({conv['rejection_rate']:.0%})")
        rows = [(r["in_loop_objectives"][0], r["dominance_penalty"]) for r in ga["per_seed"]]
        ratios = [b / a for a, b in rows if a]
        print(f"  dominance no laço {st.median(r[0] for r in rows):.4f} → reavaliado "
              f"{st.median(r[1] for r in rows):.4f}   inflação mediana "
              f"{st.median(ratios):.2f}×  (pior em {sum(b > a for a, b in rows)}/{len(rows)})")
        if hy:
            hrows = [(r["in_loop_objectives"][0], r["dominance_penalty"]) for r in hy["per_seed"]]
            hr = [b / a for a, b in hrows if a]
            print(f"  híbrido: no laço {st.median(r[0] for r in hrows):.4f} → "
                  f"{st.median(r[1] for r in hrows):.4f}   inflação {st.median(hr):.2f}×")
            hconv = hy["aggregate"]["convergence"]
            print(f"  híbrido convergiu {hconv['converged_rate']:.0%} na geração "
                  f"{hconv['converged_at']['mean']:.1f}" if hconv["converged_at"] else "")

    head("COMPARAÇÕES (Wilcoxon pareado + Holm)")
    for rel, label in [("multi_run/comparison_ga_vs_nsga2.json", "AG × NSGA-II (scalar_optimum)"),
                       ("multi_run/comparison_ga_vs_nsga2_best_dominance.json", "AG × NSGA-II (best_dominance)"),
                       ("controls/comparison_ga_vs_ga_drift0_dom1.json", "AG × controle λ=0"),
                       ("controls/comparison_ga_vs_ga_unseeded.json", "AG × controle sem semente")]:
        d = _load(rel)
        if d is None:
            continue
        print(f"\n  {label}   (família de {d['family_size']})")
        _metrics(d)
    for p in (RESULTS_DIR / "controls").glob("comparison_ga_vs_hybrid*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        print(f"\n  AG × HÍBRIDO   (família de {d['family_size']})")
        _metrics(d)

    b = _load("baselines/baselines.json")
    if b:
        head("MODELOS NULOS (piso / pior nulo / teto / posição)")
        t = b["target"]
        for key, ref in b["floors_and_ceilings"].items():
            print(f"  {key:<24} alvo {t[key]:>8.3f}   piso {ref['piso']:>8.3f}   "
                  f"pior nulo {ref['piso_extremo']:>8.3f}   teto {ref['teto']:>8.3f}")

    cyc = _load("cycle/cycle_structure.json")
    if cyc:
        head(f"CICLO ({cyc['fights_per_pair']} lutas/par, decidida > {cyc['decided_threshold']:.4f})")
        for label, recs in cyc["groups"].items():
            f = lambda k: st.mean(r[k] for r in recs)
            print(f"  {label:<26} n={len(recs):<3} mantidas {f('kept'):.2f}/10  "
                  f"decididas {f('decided'):.2f}/10  ambas {f('kept_and_decided'):.2f}/10  "
                  f"tríades {f('circular_triads'):.2f}")
        t = cyc["falsification_test"]
        print(f"\n  teste: {t['kept_and_decided']}/{t['decided']} decididas na direção "
              f"autoral ({t['kept_rate']:.1%}), binomial p = {t['binomial_p']:.3f}")
        print(f"         nulos {t['null_kept_rate']:.1%}, p = {t['vs_nulls_p']:.3f}, "
              f"Â₁₂ = {t['vs_nulls_a12']:.2f}")

    head("VALIDAÇÃO EXTERNA")
    for p in sorted((RESULTS_DIR / "external_validation").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        from collections import Counter
        print(f"  {d['individual']:<28} replicação {d['replication_verdict']:<12} "
              f"robustez {dict(Counter(d['robustness_verdicts'].values()))}")

    s = _load("sensitivity/sensitivity_analysis.json")
    if s:
        head("SENSIBILIDADE")
        print(f"  piso de ruído medido: {s['noise_floor_measured']:.4f}")
        for k, v in sorted(s["mean_abs_delta_wr"].items(), key=lambda x: -x[1]):
            print(f"    {k:<20} {v:.4f}  {s['classification'].get(k, '')}")

    ch = _load("exploratory/hybrid_choice.json")
    if ch:
        head("ESCOLHA DO HÍBRIDO")
        for step in ch["decision_trail"]:
            print(f"  • {step}")
        if ch["chosen"]:
            c = ch["chosen"]
            print(f"\n  escolhido: split {c['split']:g} / {c['carry']}  "
                  f"(identidade batida: {', '.join(c['identity_beaten']) or 'nenhuma'})")


if __name__ == "__main__":
    main()
