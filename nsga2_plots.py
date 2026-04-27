"""
Visualização da fronteira de Pareto do NSGA-II (2 objetivos).

Gera 1 scatter 2D: dominance_penalty × drift_penalty.
Os 4 representantes são destacados.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nsga2 import NSGAResult

_AXIS_LABEL = {0: "dominance_penalty", 1: "drift_penalty"}

_REP_STYLE = {
    "best_dominance": {"marker": "o", "color": "tab:red",    "label": "Melhor dominância"},
    "best_drift":     {"marker": "o", "color": "tab:blue",   "label": "Melhor drift"},
    "knee_point":     {"marker": "^", "color": "black",      "label": "Knee point"},
    "ideal_point":    {"marker": "*", "color": "tab:orange", "label": "Ideal point"},
}


def save_plots(result: NSGAResult, outdir: str, plot_3d: bool = False) -> None:
    """Gera o scatter 2D da fronteira de Pareto em `outdir`. `plot_3d` é ignorado."""
    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6))

    xs = [ind.objectives[0] for ind in result.pareto_front]
    ys = [ind.objectives[1] for ind in result.pareto_front]
    ax.scatter(xs, ys, alpha=0.4, s=30, color="tab:blue", label="Fronteira de Pareto")

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
    fig.savefig(os.path.join(outdir, "pareto_front.png"), dpi=120)
    plt.close(fig)
