"""Single source of filesystem paths. All paths derive from PROJECT_ROOT,
so scripts work regardless of the current working directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RESULTS_DIR = PROJECT_ROOT / "results"
PLOTS_DIR = RESULTS_DIR / "plots"

GA_RESULTS_PATH = RESULTS_DIR / "results.json"
NSGA2_RESULTS_PATH = RESULTS_DIR / "nsga2_results.json"
NSGA2_PLOTS_DIR = PLOTS_DIR / "nsga2"

MULTI_RUN_DIR = RESULTS_DIR / "multi_run"
MULTI_RUN_GA_PATH = MULTI_RUN_DIR / "multi_run_ga.json"
MULTI_RUN_NSGA2_PATH = MULTI_RUN_DIR / "multi_run_nsga2.json"

EXTERNAL_VALIDATION_DIR = RESULTS_DIR / "external_validation"
