"""Single source of filesystem paths. All paths derive from PROJECT_ROOT,
so scripts work regardless of the current working directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RESULTS_DIR = PROJECT_ROOT / "results"
PLOTS_DIR = RESULTS_DIR / "plots"

GA_RESULTS_PATH = RESULTS_DIR / "results.json"
NSGA2_RESULTS_PATH = RESULTS_DIR / "nsga2_results.json"
NSGA2_PLOTS_DIR = PLOTS_DIR / "nsga2"
