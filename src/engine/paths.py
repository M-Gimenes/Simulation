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
MULTI_RUN_COMPARISON_PATH = MULTI_RUN_DIR / "comparison_ga_vs_nsga2.json"

# Execuções EXPLORATÓRIAS — as que desviam do default em λ, em orçamento, ou nos dois —
# ficam fora dos paths acima, que são a bateria (e o que o `compare_algorithms` lê).
# Duas razões, e a segunda é a que machuca: misturá-las convidaria o próximo leitor a
# agregar configurações diferentes como se fossem repetições da mesma; e uma execução
# barata gravando em `multi_run_ga.json` **apagaria** horas de bateria em silêncio.
EXPLORATORY_DIR = MULTI_RUN_DIR / "exploratory"

EXTERNAL_VALIDATION_DIR = RESULTS_DIR / "external_validation"

BASELINES_PATH = RESULTS_DIR / "baselines.json"

SENSITIVITY_DIR = RESULTS_DIR / "sensitivity"
SENSITIVITY_PATH = SENSITIVITY_DIR / "sensitivity_analysis.json"
