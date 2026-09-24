"""
Curvas de convergência do AG escalar (metodologia 1.1): a trajetória de otimização
geração a geração, lida do `results/single_run/ga.json` — o histórico já está no
artefato, então o plot não re-roda o AG.

Dois painéis, porque as duas perguntas são diferentes:
  1. `best / mean / worst fitness` — o AG melhora, e a população acompanha o melhor?
  2. `dominance_penalty` × `drift_penalty` do melhor — os dois termos evoluem um contra
     o outro? É o trade-off da pergunta de pesquisa, visto ao longo da busca.

A geração de `converged_at` entra como linha vertical: é o primeiro disparo do gate que
sobreviveu à confirmação num stream que o AG nunca viu. Sob rotação do stream o fitness
**flutua** entre gerações por desenho (cada geração é avaliada num stream diferente), e
é por isso que não existe evento de estagnação — a curva não é monotônica, e não deve
ser lida como se fosse.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.engine.paths import GA_RESULTS_PATH, PROJECT_ROOT, SINGLE_RUN_DIR

GA_PLOTS_DIR = SINGLE_RUN_DIR / "plots"


def save_plots(history: list, converged_at: Optional[int], seed: int, outdir: Path) -> None:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    gens = [h["gen"] for h in history]
    fig, (ax_fit, ax_obj) = plt.subplots(
        2, 1, figsize=(8, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1]}
    )

    ax_fit.plot(gens, [h["best_fitness"] for h in history],
                color="tab:green", lw=1.6, label="melhor")
    ax_fit.plot(gens, [h["mean_fitness"] for h in history],
                color="tab:blue", lw=1.2, alpha=0.8, label="média")
    ax_fit.plot(gens, [h["worst_fitness"] for h in history],
                color="tab:red", lw=1.0, alpha=0.5, label="pior")
    ax_fit.set_ylabel("fitness  (0 = ótimo)")
    ax_fit.set_title(f"AG escalar — trajetória de otimização (seed {seed})")

    ax_obj.plot(gens, [h["dominance_penalty"] for h in history],
                color="tab:red", lw=1.6, label="dominance_penalty")
    ax_obj.plot(gens, [h["drift_penalty"] for h in history],
                color="tab:blue", lw=1.6, label="drift_penalty")
    ax_obj.set_xlabel("geração")
    ax_obj.set_ylabel("penalidade do melhor")

    for ax in (ax_fit, ax_obj):
        if converged_at is not None:
            ax.axvline(converged_at, color="black", ls="--", lw=1.0, alpha=0.7,
                       label=f"convergiu (g{converged_at})")
        ax.grid(alpha=0.3)
        ax.legend(loc="best", fontsize=8)

    fig.tight_layout()
    fig.savefig(outdir / "ga_convergence.png", dpi=120)
    plt.close(fig)


def save_plots_from_results(path: Path = GA_RESULTS_PATH,
                            outdir: Path = GA_PLOTS_DIR) -> Path:
    """Plota a partir do artefato gravado — a única forma usada, inclusive pelo
    `main.py` logo depois de salvar. Assim a curva sai do mesmo `history` que o JSON
    carrega, sem uma segunda serialização para manter em sincronia."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    save_plots(data["history"], data.get("converged_at"), data["seed"], outdir)
    return Path(outdir) / "ga_convergence.png"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Curvas de convergência do AG escalar, a partir de single_run/ga.json")
    parser.add_argument("--results", default=str(GA_RESULTS_PATH),
                        help=f"artefato de origem (default: {GA_RESULTS_PATH.name})")
    parser.add_argument("--outdir", default=str(GA_PLOTS_DIR),
                        help="diretório de saída")
    args = parser.parse_args()

    out = save_plots_from_results(Path(args.results), Path(args.outdir)).resolve()
    print(f"Salvo em {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
