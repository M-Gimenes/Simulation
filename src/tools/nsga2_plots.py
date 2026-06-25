"""
Plot 2D da fronteira de Pareto do NSGA-II (dominance × drift) com 4 representantes destacados.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.engine.config import HYPERVOLUME_REFERENCE
from src.engine.nsga2 import NSGAResult
from src.engine.pareto_metrics import hypervolume_2d, spacing

_AXIS_LABEL = {0: "dominance_penalty", 1: "drift_penalty"}

_REP_STYLE = {
    "best_dominance": {"marker": "o", "color": "tab:red",    "label": "Melhor dominância"},
    "best_drift":     {"marker": "o", "color": "tab:blue",   "label": "Melhor drift"},
    "knee_point":     {"marker": "^", "color": "black",      "label": "Knee point"},
    "ideal_point":    {"marker": "*", "color": "tab:orange", "label": "Ideal point"},
}


def save_plots(result: NSGAResult, outdir: Path) -> None:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6))

    objs = [ind.objectives for ind in result.pareto_front]
    hv = hypervolume_2d(objs, HYPERVOLUME_REFERENCE)
    sp = spacing(objs)

    xs = [o[0] for o in objs]
    ys = [o[1] for o in objs]
    ax.scatter(xs, ys, alpha=0.4, s=30, color="tab:blue", label="Fronteira de Pareto")

    ax.text(
        0.97, 0.97,
        f"hipervolume = {hv:.4f}\nspacing = {sp:.4f}\nref = {HYPERVOLUME_REFERENCE}",
        transform=ax.transAxes, ha="right", va="top", fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7, edgecolor="gray"),
    )

    for name, ind in result.representatives.items():
        style = _REP_STYLE[name]
        ax.scatter(
            ind.objectives[0], ind.objectives[1],
            marker=style["marker"], color=style["color"],
            s=140, edgecolors="black", linewidths=1.2, label=style["label"], zorder=10,
        )

    ax.set_xlabel(_AXIS_LABEL[0])
    ax.set_ylabel(_AXIS_LABEL[1])
    ax.set_title("Fronteira de Pareto — dominância vs drift de arquétipo")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "pareto_front.png", dpi=120)
    plt.close(fig)
