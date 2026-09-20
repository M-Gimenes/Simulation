"""Single source of filesystem paths. All paths derive from PROJECT_ROOT,
so scripts work regardless of the current working directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RESULTS_DIR = PROJECT_ROOT / "results"

# Uma pasta por produtor: quem gera o artefato decide onde ele mora.

# `main.py` — uma execução de cada algoritmo (seed 42 na bateria).
SINGLE_RUN_DIR = RESULTS_DIR / "single_run"
GA_RESULTS_PATH = SINGLE_RUN_DIR / "ga.json"
NSGA2_RESULTS_PATH = SINGLE_RUN_DIR / "nsga2.json"
NSGA2_PLOTS_DIR = SINGLE_RUN_DIR / "plots"

# `multi_run` + `compare_algorithms` — as N sementes da bateria e o teste entre algoritmos.
MULTI_RUN_DIR = RESULTS_DIR / "multi_run"
MULTI_RUN_GA_PATH = MULTI_RUN_DIR / "multi_run_ga.json"
MULTI_RUN_NSGA2_PATH = MULTI_RUN_DIR / "multi_run_nsga2.json"
MULTI_RUN_COMPARISON_PATH = MULTI_RUN_DIR / "comparison_ga_vs_nsga2.json"

# Execuções fora do protocolo ficam fora dos paths acima, que são a bateria (e o que o
# `compare_algorithms` lê por default). Duas razões, e a segunda é a que machuca:
# misturá-las convidaria o próximo leitor a agregar configurações diferentes como se
# fossem repetições da mesma; e uma execução barata gravando em `multi_run_ga.json`
# **apagaria** horas de bateria em silêncio.
#
# CONTROLES — mesma amostra e mesmo orçamento da bateria, com um desvio de DESENHO
# (λ, semente canônica, seleção, …). São citáveis: é o braço de controle da tese.
CONTROLS_DIR = RESULTS_DIR / "controls"
# EXPLORATÓRIOS — desviam na amostra ou no orçamento (os sweeps). Servem para ordenar
# configurações, não para número citável.
EXPLORATORY_DIR = RESULTS_DIR / "exploratory"

EXTERNAL_VALIDATION_DIR = RESULTS_DIR / "external_validation"

BASELINES_DIR = RESULTS_DIR / "baselines"
BASELINES_PATH = BASELINES_DIR / "baselines.json"

SENSITIVITY_DIR = RESULTS_DIR / "sensitivity"
SENSITIVITY_PATH = SENSITIVITY_DIR / "sensitivity_analysis.json"
