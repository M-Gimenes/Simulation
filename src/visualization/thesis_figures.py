"""
Figuras de dados da monografia, lidas dos artefatos da bateria — nada é re-rodado.

Cada figura sai como PDF vetorial em `overleaf/TCC/figuras/`, no tamanho em que entra
no texto (largura útil da página A4 com as margens da ABNT), em Arial, para casar com
a fonte do documento, e com vírgula decimal. As cores seguem o braço, e não a figura:
AG escalar, híbrido e NSGA-II têm a mesma cor em todas, e os controles ficam em cinza,
porque são referência e não objeto da comparação.

    figuras/confrontos.pdf     matriz de taxas de vitória: canônico × AG escalar
    figuras/convergencia.pdf   P_dom e P_drift do melhor elenco, geração a geração
    figuras/fronteira.pdf      fronteiras do NSGA-II e os pontos dos braços escalares
    figuras/metricas.pdf       as seis métricas da família de testes, por braço
    figuras/sensibilidade.pdf  Δ WR por gene contra o piso de ruído medido

Uso:
    py -m src.visualization.thesis_figures
"""
from __future__ import annotations

import json
import random
import statistics
from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter, MaxNLocator

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES
from src.engine.paths import (
    BASELINES_PATH,
    CONTROLS_DIR,
    CYCLE_PATH,
    MULTI_RUN_GA_PATH,
    MULTI_RUN_NSGA2_PATH,
    PROJECT_ROOT,
    SENSITIVITY_PATH,
)

FIGURES_DIR = PROJECT_ROOT / "overleaf" / "TCC" / "figuras"
TEXT_WIDTH_IN = 16.0 / 2.54

INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

ARM_COLORS = {
    "AG escalar": "#2a78d6",
    "NSGA-II": "#eb6834",
    "Híbrido": "#1baf7a",
    "Controle λ = 0": "#52514e",
    "Controle sem semente": "#a3a19a",
}
DIVERGING = LinearSegmentedColormap.from_list(
    "vitoria", ["#b3312f", "#e34948", "#f0efec", "#2a78d6", "#1c5cab"])

SHORT_NAMES = ["Zoner", "Rushdown", "Combo M.", "Grappler", "Turtle"]


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _decimal_comma(value: float, _pos=None) -> str:
    text = f"{value:g}"
    return text.replace(".", ",")


def _style() -> None:
    plt.rcParams.update({
        "font.family": "Arial",
        "font.size": 8.5,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_SECONDARY,
        "axes.titlesize": 9,
        "axes.titlecolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
    })


def _comma_axes(*axes, x: bool = True, y: bool = True) -> None:
    for ax in axes:
        if x:
            ax.xaxis.set_major_formatter(FuncFormatter(_decimal_comma))
        if y:
            ax.yaxis.set_major_formatter(FuncFormatter(_decimal_comma))


def _save(fig, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  {path.relative_to(PROJECT_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# Matriz de confrontos
# ─────────────────────────────────────────────────────────────────────────────


def _matchup_matrix(edge_winrates: Sequence[float], edges: List[List[str]]) -> List[List[float]]:
    """Taxa de vitória da linha contra a coluna, a partir das arestas do ciclo."""
    names = [ARCHETYPES[aid].name for aid in ARCHETYPE_ORDER]
    matrix = [[float("nan")] * 5 for _ in range(5)]
    for (winner, loser), wr in zip(edges, edge_winrates):
        i, j = names.index(winner), names.index(loser)
        matrix[i][j] = wr
        matrix[j][i] = 1.0 - wr
    return matrix


def figure_matchups(cycle: dict) -> None:
    edges = cycle["edges"]
    canonical = _matchup_matrix(cycle["groups"]["canônico"][0]["edge_winrates"], edges)
    evolved_runs = [_matchup_matrix(r["edge_winrates"], edges) for r in cycle["groups"]["AG escalar"]]
    evolved = [[statistics.fmean(run[i][j] for run in evolved_runs) if i != j else float("nan")
                for j in range(5)] for i in range(5)]

    fig, axes = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN, 3.1), sharey=True)
    for ax, matrix, title in ((axes[0], canonical, "(a) Elenco canônico"),
                              (axes[1], evolved, "(b) AG escalar, média de 20 execuções")):
        image = ax.imshow(matrix, cmap=DIVERGING, vmin=0.0, vmax=1.0)
        ax.grid(False)
        ax.set_xticks(range(5), SHORT_NAMES, rotation=30, ha="right")
        ax.set_yticks(range(5), SHORT_NAMES)
        ax.tick_params(axis="y", labelleft=ax is axes[0])
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_title(title, loc="left")
        for i in range(5):
            for j in range(5):
                if i == j:
                    continue
                value = matrix[i][j]
                ink = "white" if abs(value - 0.5) > 0.3 else INK
                ax.text(j, i, f"{100 * value:.0f}", ha="center", va="center", color=ink, fontsize=8)
    bar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.02)
    bar.set_label("taxa de vitória da linha contra a coluna")
    bar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{100 * v:.0f}%"))
    bar.outline.set_visible(False)
    _save(fig, "confrontos.pdf")


# ─────────────────────────────────────────────────────────────────────────────
# Convergência
# ─────────────────────────────────────────────────────────────────────────────


def _quantile_bands(histories: List[List[float]]):
    generations = len(histories[0])
    medians, lows, highs = [], [], []
    for g in range(generations):
        values = sorted(h[g] for h in histories)
        q1, q2, q3 = statistics.quantiles(values, n=4)
        lows.append(q1)
        medians.append(q2)
        highs.append(q3)
    return medians, lows, highs


def figure_convergence(ga: dict, control: dict, hybrid: dict) -> None:
    fig, (ax_dom, ax_drift) = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN, 2.7))
    arms = (
        ("AG escalar", ga, 0, "-"),
        ("Controle λ = 0", control, 0, "--"),
        ("Híbrido", hybrid, hybrid["n_generations"] - len(hybrid["per_seed"][0]["history"]), "-"),
    )
    for label, artifact, offset, style in arms:
        color = ARM_COLORS[label]
        for ax, key in ((ax_dom, "dominance_penalty"), (ax_drift, "drift_penalty")):
            histories = [[h[key] for h in r["history"]] for r in artifact["per_seed"]]
            medians, lows, highs = _quantile_bands(histories)
            gens = [offset + g for g in range(len(medians))]
            ax.fill_between(gens, lows, highs, color=color, alpha=0.15, linewidth=0)
            ax.plot(gens, medians, color=color, lw=1.8, ls=style, label=label)

    converged = statistics.fmean(r["converged_at"] for r in ga["per_seed"])
    for ax in (ax_dom, ax_drift):
        ax.axvline(converged, color=INK_MUTED, lw=0.8, ls=":")
        ax.set_xlabel("geração")
        ax.set_xlim(0, ga["n_generations"])
    ax_dom.text(converged + 2, 1.0, "convergência média\ndo AG escalar", color=INK_SECONDARY,
                fontsize=7.5, va="top")
    ax_dom.set_yscale("log")
    ax_dom.set_ylabel(r"$P_{\mathrm{dom}}$ do melhor elenco (escala log.)")
    ax_dom.set_title("(a) Equilíbrio", loc="left")
    ax_drift.set_ylabel(r"$P_{\mathrm{drift}}$ do melhor elenco")
    ax_drift.set_title("(b) Identidade estrutural", loc="left")
    _comma_axes(ax_drift)
    ax_dom.yaxis.set_major_formatter(FuncFormatter(_decimal_comma))
    handles, labels = ax_drift.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "convergencia.pdf")


# ─────────────────────────────────────────────────────────────────────────────
# Fronteira de Pareto
# ─────────────────────────────────────────────────────────────────────────────


def figure_front(ga: dict, nsga2: dict, hybrid: dict, control: dict, baselines: dict) -> None:
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN, 3.6))
    for record in nsga2["per_seed"]:
        front = sorted(record["front_objectives"])
        ax.step([p[0] for p in front], [p[1] for p in front], where="post",
                color=AXIS, lw=0.7, zorder=1)
    ax.plot([], [], color=AXIS, lw=0.9, label="Fronteiras do NSGA-II (20 execuções)")

    scalar_optimum = [min(r["front_objectives"], key=lambda p: p[0] + p[1]) for r in nsga2["per_seed"]]
    series = (
        ("Controle λ = 0", [r["in_loop_objectives"] for r in control["per_seed"]], "x"),
        ("NSGA-II", scalar_optimum, "s"),
        ("AG escalar", [r["in_loop_objectives"] for r in ga["per_seed"]], "o"),
        ("Híbrido", [r["in_loop_objectives"] for r in hybrid["per_seed"]], "^"),
    )
    labels = {"NSGA-II": "NSGA-II, scalar_optimum"}
    for label, points, marker in series:
        filled = marker != "x"
        ax.scatter([p[0] for p in points], [p[1] for p in points], s=26, marker=marker,
                   color=ARM_COLORS[label], edgecolors="white" if filled else None,
                   linewidths=0.6 if filled else 1.2, zorder=3, label=labels.get(label, label))

    canonical = next(r for r in baselines["references"] if r["label"] == "canônico")
    ax.scatter([canonical["dominance_penalty"]], [canonical["drift_penalty"]], marker="*", s=90,
               color=INK, zorder=4, label="Elenco canônico")
    ref_dom, ref_drift = 1.3, 0.4
    ax.plot([ref_dom, ref_dom], [0, ref_drift], color=INK_MUTED, lw=0.8, ls="--")
    ax.plot([0.008, ref_dom], [ref_drift, ref_drift], color=INK_MUTED, lw=0.8, ls="--")
    ax.text(ref_dom * 0.97, ref_drift + 0.006, "referência do hipervolume", color=INK_MUTED,
            fontsize=7.5, ha="right", va="bottom")

    ax.set_xscale("log")
    ax.set_xlim(0.008, 1.6)
    ax.set_ylim(-0.01, 0.46)
    ax.set_xlabel(r"$P_{\mathrm{dom}}$ (desequilíbrio, escala log.)")
    ax.set_ylabel(r"$P_{\mathrm{drift}}$ (desvio de identidade)")
    _comma_axes(ax)
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.62))
    _save(fig, "fronteira.pdf")


# ─────────────────────────────────────────────────────────────────────────────
# Métricas por braço
# ─────────────────────────────────────────────────────────────────────────────

METRIC_PANELS = (
    ("dominance_penalty", r"(a) $P_{\mathrm{dom}}$ (menor é melhor)", "dominance_penalty"),
    ("n_hard_counters", "(b) Hard counters (menor é melhor)", None),
    ("drift_penalty", r"(c) $P_{\mathrm{drift}}$ (menor é melhor)", "drift_penalty"),
    ("validator_structural", "(d) Validador, Camadas 1-2 (de 18)", "validator_structural"),
    ("validator_behavioral", "(e) Validador, Camada 3 (de 5)", "validator_behavioral"),
    ("rank_agreement", r"(f) Concordância $\tau$", "rank_agreement"),
)


def figure_metrics(arms: Dict[str, dict], baselines: dict) -> None:
    rng = random.Random(0)
    fig, axes = plt.subplots(3, 2, figsize=(TEXT_WIDTH_IN, 6.9))
    labels = list(arms)
    short = {"Controle λ = 0": "λ = 0", "Controle sem semente": "Sem\nsemente",
             "AG escalar": "AG\nescalar", "Híbrido": "Híbrido", "NSGA-II": "NSGA-II"}
    floors = baselines["floors_and_ceilings"]
    for ax, (key, title, floor_key) in zip(axes.flat, METRIC_PANELS):
        for x, label in enumerate(labels):
            values = [r[key] for r in arms[label]["per_seed"]]
            jitter = [x + rng.uniform(-0.18, 0.18) for _ in values]
            ax.scatter(jitter, values, s=11, color=ARM_COLORS[label], alpha=0.8,
                       edgecolors="none", zorder=3)
            median = statistics.median(values)
            ax.plot([x - 0.3, x + 0.3], [median, median], color=INK, lw=1.6, zorder=4)
        if floor_key is not None:
            # Equilíbrio é lido contra a simetria perfeita (espelhos); identidade, contra o
            # acaso (aleatórios). O P_dom dos aleatórios (~1,3) achataria o painel.
            null = "espelho" if floor_key == "dominance_penalty" else "aleatorio"
            ax.axhline(floors[floor_key][null]["media"], color=INK_MUTED, lw=0.8, ls="--", zorder=2)
        ax.set_title(title, loc="left")
        ax.set_xticks(range(len(labels)), [short[label] for label in labels])
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="x", visible=False)
        _comma_axes(ax, x=False)
        if key in ("n_hard_counters", "validator_structural", "validator_behavioral"):
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0][0].set_yscale("log")
    axes[0][0].yaxis.set_major_formatter(FuncFormatter(_decimal_comma))
    fig.tight_layout(h_pad=1.6)
    _save(fig, "metricas.pdf")


# ─────────────────────────────────────────────────────────────────────────────
# Sensibilidade
# ─────────────────────────────────────────────────────────────────────────────

GENE_LABELS = {
    "hp": "pontos de vida", "damage": "dano", "attack_cooldown": "intervalo entre golpes",
    "range": "alcance", "speed": "velocidade", "stun": "atordoamento", "knockback": "repulsão",
    "grab_power": "agarrão", "w_retreat": "peso de RECUAR", "w_defend": "peso de GUARDA",
    "w_aggressiveness": "peso de FRENTE",
}


def figure_sensitivity(sensitivity: dict) -> None:
    floor = sensitivity["noise_floor_measured"]
    ranked = sorted(sensitivity["mean_abs_delta_wr"].items(), key=lambda item: item[1])
    fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN, 3.0))
    for y, (gene, value) in enumerate(ranked):
        color = "#2a78d6" if value > 2 * floor else "#86b6ef" if value > floor else AXIS
        ax.barh(y, value, height=0.62, color=color, zorder=3)
        ax.text(value + 0.004, y, f"{100 * value:.1f}".replace(".", ","), va="center",
                color=INK_SECONDARY, fontsize=7.5)
    ax.set_yticks(range(len(ranked)), [GENE_LABELS[gene] for gene, _ in ranked])
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    for multiple, style, text, side in ((1, "--", "piso de ruído", "right"), (2, ":", "2 × piso", "left")):
        ax.axvline(multiple * floor, color=INK_MUTED, lw=0.9, ls=style, zorder=2)
        offset = -0.003 if side == "right" else 0.003
        ax.text(multiple * floor + offset, len(ranked) - 0.45, text, color=INK_MUTED,
                fontsize=7.5, ha=side)
    ax.set_xlabel("variação média absoluta da taxa de vitória global (pontos percentuais)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{100 * v:.0f}"))
    ax.set_xlim(0, 0.35)
    _save(fig, "sensibilidade.pdf")


def main() -> None:
    _style()
    ga = _load(MULTI_RUN_GA_PATH)
    nsga2 = _load(MULTI_RUN_NSGA2_PATH)
    hybrid = _load(CONTROLS_DIR / "multi_run_hybrid_split0.5_front.json")
    control = _load(CONTROLS_DIR / "multi_run_ga_drift0_dom1.json")
    unseeded = _load(CONTROLS_DIR / "multi_run_ga_unseeded.json")
    baselines = _load(BASELINES_PATH)

    print("Figuras da monografia:")
    figure_matchups(_load(CYCLE_PATH))
    figure_convergence(ga, control, hybrid)
    figure_front(ga, nsga2, hybrid, control, baselines)
    figure_metrics({"Controle λ = 0": control, "Controle sem semente": unseeded,
                    "AG escalar": ga, "Híbrido": hybrid, "NSGA-II": nsga2}, baselines)
    figure_sensitivity(_load(SENSITIVITY_PATH))


if __name__ == "__main__":
    main()
