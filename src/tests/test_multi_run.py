"""
Smoke test do roteamento de artefatos do `multi_run`.
Rode com: py -m src.tests.test_multi_run

O que precisa valer: só a execução inteiramente no protocolo grava nos caminhos da
bateria. Um desvio de amostra ou de orçamento vai para `exploratory/`; um desvio só de
desenho (λ, seleção, semente canônica, representante de topo), com a amostra e o
orçamento do protocolo, é um controle e vai para `controls/`. Sempre com o desvio no
nome. Uma execução barata que caísse no caminho da bateria apagaria horas de resultado
sem aviso.
"""

from src.engine.config import (
    DOMINANCE_CAP_WEIGHT,
    DOMINANCE_DECIS_WEIGHT,
    DOMINANCE_GLOBAL_WEIGHT,
    ELITE_RATE,
    GA_CANONICAL_SEED,
    LAMBDA_DOMINANCE,
    LAMBDA_DRIFT,
    MAX_GENERATIONS,
    MULTI_RUN_N_SEEDS,
    MULTI_RUN_SEED_START,
    MULTI_RUN_SIMS,
    POPULATION_SIZE,
    TOURNAMENT_SIZE,
)
from src.engine.paths import (CONTROLS_DIR, EXPLORATORY_DIR, MULTI_RUN_GA_PATH,
                              MULTI_RUN_NSGA2_PATH)
from src.experiments.multi_run import HEADLINE_REPRESENTATIVE, artifact_path


def _protocol(algorithm: str, **changes) -> dict:
    """O corpo de um artefato no protocolo, com `changes` aplicados."""
    body = {
        "algorithm":        algorithm,
        "pop_size":         POPULATION_SIZE,
        "n_generations":    MAX_GENERATIONS,
        "lambda_drift":     LAMBDA_DRIFT,
        "lambda_dominance": LAMBDA_DOMINANCE,
        "dominance_weights": {"global": DOMINANCE_GLOBAL_WEIGHT, "cap": DOMINANCE_CAP_WEIGHT,
                              "decis": DOMINANCE_DECIS_WEIGHT},
        "selection":        {"elite_rate": ELITE_RATE, "tournament_size": TOURNAMENT_SIZE},
        "seeds":            list(range(MULTI_RUN_SEED_START,
                                       MULTI_RUN_SEED_START + MULTI_RUN_N_SEEDS)),
        "sims_per_matchup": MULTI_RUN_SIMS,
    }
    if algorithm == "ga":
        body["canonical_seed"] = GA_CANONICAL_SEED
    else:
        body["nsga2_representative"] = HEADLINE_REPRESENTATIVE
    body.update(changes)
    return body


print("\n" + "─" * 60)
print("  Roteamento dos artefatos do multi_run")
print("─" * 60)

assert artifact_path(_protocol("ga")) == MULTI_RUN_GA_PATH
assert artifact_path(_protocol("nsga2")) == MULTI_RUN_NSGA2_PATH
print("  ✓ protocolo → caminhos da bateria")

five_seeds = list(range(MULTI_RUN_SEED_START, MULTI_RUN_SEED_START + 5))
deviations = {
    # (rótulo no nome, desvio, pasta esperada)
    "n5":           ({"seeds": five_seeds}, EXPLORATORY_DIR),
    "seed1000":     ({"seeds": list(range(1000, 1000 + MULTI_RUN_N_SEEDS))}, EXPLORATORY_DIR),
    "sims100":      ({"sims_per_matchup": 100}, EXPLORATORY_DIR),
    "pop120_gen60": ({"pop_size": 120, "n_generations": 60}, EXPLORATORY_DIR),
    "drift0_dom1":  ({"lambda_drift": 0.0}, CONTROLS_DIR),
    "tour5":        ({"selection": {"elite_rate": ELITE_RATE, "tournament_size": 5}},
                     CONTROLS_DIR),
    "unseeded":     ({"canonical_seed": not GA_CANONICAL_SEED}, CONTROLS_DIR),
}
seen = set()
for label, (change, folder) in deviations.items():
    path = artifact_path(_protocol("ga", **change))
    assert path.parent == folder, f"{label}: caiu em {path.parent.name}/, não em {folder.name}/"
    assert label in path.name, f"{label}: o desvio não está no nome ({path.name})"
    seen.add(path)
    print(f"  ✓ {label:<13} → {folder.name}/{path.name}")
assert len(seen) == len(deviations), "dois desvios diferentes gravariam no mesmo arquivo"

sweep_arm = artifact_path(_protocol("ga", lambda_drift=0.25, seeds=five_seeds))
assert sweep_arm.parent == EXPLORATORY_DIR, "desvio de desenho + amostra reduzida não é controle"
print(f"  ✓ desenho + amostra reduzida → exploratory/{sweep_arm.name} (não é controle)")

rep = artifact_path(_protocol("nsga2", nsga2_representative="knee_point"))
assert rep.parent == CONTROLS_DIR and "rep-knee_point" in rep.name
print(f"  ✓ outro representante de topo → controls/{rep.name}")

print("\n  ✓ nenhum desvio grava nos caminhos da bateria\n")
