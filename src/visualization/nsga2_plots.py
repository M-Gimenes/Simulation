"""
Plot 2D da fronteira de Pareto do NSGA-II (dominance × drift) com os 5 representantes
destacados.

**Representantes coincidem, e isso tem de aparecer.** Nada impede dois critérios de
escolherem o mesmo ponto da fronteira — na seed 42 o `scalar_optimum` cai exatamente no
`best_dominance`, e o `ideal_point` no `knee_point`. Desenhados no mesmo tamanho, o
segundo cobre o primeiro e a legenda passa a citar um marcador que não está na figura.
Os marcadores são desenhados **aninhados**, do maior para o menor em cada posição
ocupada, e a caixa de anotação lista as coincidências: quem lê a figura vê os cinco.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from src.engine.config import HYPERVOLUME_REFERENCE
from src.engine.nsga2 import NSGAResult
from src.engine.paths import NSGA2_PLOTS_DIR, NSGA2_RESULTS_PATH, PROJECT_ROOT
from src.engine.pareto_metrics import hypervolume_2d, spacing

_AXIS_LABEL = {0: "dominance_penalty", 1: "drift_penalty"}

# A ordem aqui é a de desenho quando vários caem no mesmo ponto: o primeiro leva o
# marcador maior, e os seguintes aninham por cima.
_REP_STYLE = {
    "best_dominance": {"marker": "o", "color": "tab:red",    "label": "Melhor dominância"},
    "best_drift":     {"marker": "o", "color": "tab:blue",   "label": "Melhor drift"},
    "knee_point":     {"marker": "^", "color": "black",      "label": "Knee point"},
    "ideal_point":    {"marker": "*", "color": "tab:orange", "label": "Ideal point"},
    "scalar_optimum": {"marker": "D", "color": "tab:green",  "label": "Ótimo escalar"},
}
_NESTED_SIZES = (260, 150, 90, 55, 35)
# A legenda usa proxies de tamanho fixo: o tamanho do marcador na figura codifica o
# aninhamento, não a identidade, e herdado dele o ícone da legenda ficaria enorme.
_LEGEND_MARKER_SIZE = 7


def save_plots(result: NSGAResult, outdir: Path) -> Path:
    """Da execução em memória — o caminho que o `main.py` usa."""
    return _render(
        [ind.objectives for ind in result.pareto_front],
        {name: tuple(ind.objectives) for name, ind in result.representatives.items()},
        outdir,
    )


def save_plots_from_results(path: Path = NSGA2_RESULTS_PATH,
                            outdir: Path = NSGA2_PLOTS_DIR) -> Path:
    """Do artefato gravado — redesenha a figura sem re-rodar o NSGA-II (7 min)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _render(
        [tuple(p["objectives"]) for p in data["pareto_front"]],
        {name: tuple(r["objectives"]) for name, r in data["representatives"].items()},
        outdir,
    )


def _render(objs: Sequence[Tuple[float, float]],
            representatives: Dict[str, Tuple[float, float]],
            outdir: Path) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6))

    hv = hypervolume_2d(list(objs), HYPERVOLUME_REFERENCE)
    sp = spacing(list(objs))

    ax.scatter([o[0] for o in objs], [o[1] for o in objs],
               alpha=0.4, s=30, color="tab:blue")

    # Agrupa por posição: quem divide um ponto é desenhado aninhado, do maior ao menor.
    at_point: Dict[Tuple[float, float], List[str]] = {}
    for name in _REP_STYLE:
        if name in representatives:
            at_point.setdefault(representatives[name], []).append(name)

    for point, names in at_point.items():
        for depth, name in enumerate(names):
            style = _REP_STYLE[name]
            ax.scatter(
                point[0], point[1],
                marker=style["marker"], color=style["color"],
                s=_NESTED_SIZES[min(depth, len(_NESTED_SIZES) - 1)],
                edgecolors="black", linewidths=1.2, zorder=10 + depth,
            )

    note = f"hipervolume = {hv:.4f}\nspacing = {sp:.4f}\nref = {HYPERVOLUME_REFERENCE}"
    coincident = [names for names in at_point.values() if len(names) > 1]
    for names in coincident:
        note += "\n" + " = ".join(_REP_STYLE[n]["label"] for n in names)
    ax.text(
        0.97, 0.97, note,
        transform=ax.transAxes, ha="right", va="top", fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7, edgecolor="gray"),
    )

    ax.set_xlabel(_AXIS_LABEL[0])
    ax.set_ylabel(_AXIS_LABEL[1])
    ax.set_title("Fronteira de Pareto — dominância vs drift de arquétipo")
    handles = [Line2D([], [], linestyle="none", marker="o", color="tab:blue", alpha=0.4,
                      markersize=_LEGEND_MARKER_SIZE - 1, label="Fronteira de Pareto")]
    handles += [
        Line2D([], [], linestyle="none", marker=style["marker"],
               markerfacecolor=style["color"], markeredgecolor="black",
               markersize=_LEGEND_MARKER_SIZE, label=style["label"])
        for name, style in _REP_STYLE.items() if name in representatives
    ]
    ax.legend(handles=handles, loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = outdir / "pareto_front.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fronteira de Pareto do NSGA-II, a partir de single_run/nsga2.json")
    parser.add_argument("--results", default=str(NSGA2_RESULTS_PATH),
                        help=f"artefato de origem (default: {NSGA2_RESULTS_PATH.name})")
    parser.add_argument("--outdir", default=str(NSGA2_PLOTS_DIR),
                        help="diretório de saída")
    args = parser.parse_args()

    out = save_plots_from_results(Path(args.results), Path(args.outdir)).resolve()
    print(f"Salvo em {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
