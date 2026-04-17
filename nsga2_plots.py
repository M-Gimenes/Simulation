"""
Visualizações da fronteira de Pareto do NSGA-II.

Gera 3 projeções 2D obrigatoriamente e 1 scatter 3D opcional.
Os 5 representantes (extremos + knee + ideal) são destacados em todos os plots.
"""
from __future__ import annotations

import os
from typing import Optional

import matplotlib
matplotlib.use("Agg")   # backend sem display — seguro no Windows/CI
import matplotlib.pyplot as plt

from nsga2 import NSGAResult

# Indices dos objetivos: 0=balance, 1=matchup, 2=drift
_AXIS_LABEL = {0: "balance_error", 1: "matchup_dominance_penalty", 2: "drift_penalty"}

_REP_STYLE = {
    "best_balance": {"marker": "o", "color": "tab:blue",   "label": "Melhor balance"},
    "best_matchup": {"marker": "o", "color": "tab:red",    "label": "Melhor matchup"},
    "best_drift":   {"marker": "o", "color": "tab:green",  "label": "Melhor drift"},
    "knee_point":   {"marker": "^", "color": "black",      "label": "Knee point"},
    "ideal_point":  {"marker": "*", "color": "tab:orange", "label": "Ideal point"},
}


def _plot_projection(result: NSGAResult, i: int, j: int, out_path: str) -> None:
    """Projeção 2D da fronteira nos eixos i e j (0=bal, 1=mat, 2=drift)."""
    fig, ax = plt.subplots(figsize=(6, 5))
    xs = [ind.objectives[i] for ind in result.pareto_front]
    ys = [ind.objectives[j] for ind in result.pareto_front]
    ax.scatter(xs, ys, alpha=0.4, s=30, color="tab:blue", label="Fronteira de Pareto")

    for name, ind in result.representatives.items():
        style = _REP_STYLE[name]
        ax.scatter(
            ind.objectives[i], ind.objectives[j],
            marker=style["marker"], color=style["color"],
            s=140, edgecolors="black", linewidths=1.2, label=style["label"], zorder=10,
        )

    ax.set_xlabel(_AXIS_LABEL[i])
    ax.set_ylabel(_AXIS_LABEL[j])
    ax.set_title(f"Projeção {_AXIS_LABEL[i]} × {_AXIS_LABEL[j]}")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _plot_3d(result: NSGAResult, out_path: str) -> None:
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    xs = [ind.objectives[0] for ind in result.pareto_front]
    ys = [ind.objectives[1] for ind in result.pareto_front]
    zs = [ind.objectives[2] for ind in result.pareto_front]
    ax.scatter(xs, ys, zs, alpha=0.4, s=20, color="tab:blue", label="Fronteira de Pareto")

    for name, ind in result.representatives.items():
        style = _REP_STYLE[name]
        ax.scatter(
            ind.objectives[0], ind.objectives[1], ind.objectives[2],
            marker=style["marker"], color=style["color"],
            s=140, edgecolors="black", linewidths=1.2, label=style["label"],
        )

    ax.set_xlabel(_AXIS_LABEL[0])
    ax.set_ylabel(_AXIS_LABEL[1])
    ax.set_zlabel(_AXIS_LABEL[2])
    ax.set_title("Fronteira de Pareto — 3D")
    ax.legend(loc="best", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def save_plots(result: NSGAResult, outdir: str, plot_3d: bool = False) -> None:
    """Gera as 3 projeções 2D em `outdir` e, opcionalmente, o scatter 3D."""
    os.makedirs(outdir, exist_ok=True)
    _plot_projection(result, 0, 2, os.path.join(outdir, "proj_balance_drift.png"))
    _plot_projection(result, 0, 1, os.path.join(outdir, "proj_balance_matchup.png"))
    _plot_projection(result, 2, 1, os.path.join(outdir, "proj_drift_matchup.png"))
    if plot_3d:
        _plot_3d(result, os.path.join(outdir, "front_3d.png"))
