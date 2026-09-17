"""
Smoke test do carimbo de proveniência.
Rode com: py -m src.tests.test_provenance

O que precisa valer, e por quê (ver docs/reference/09-reproducibility.md):
  · o carimbo é ESTÁVEL — se variasse entre chamadas, todo artefato nasceria "obsoleto"
    e o alarme seria descartado no primeiro dia;
  · o carimbo é SENSÍVEL — pega constante, canônico e código do motor, que são as três
    coisas que invalidam `results/`;
  · o carimbo é ESPECÍFICO — diz QUAL constante mudou, não só que algo mudou;
  · o carimbo é ENUMERADO de `config.py`, senão a próxima constante nasce invisível;
  · um BRAÇO de experimento (λ do sweep) não é confundido com artefato obsoleto — mas o
    override também não vira salvo-conduto para esconder mudança de motor;
  · o λ chega aos WORKERS, não só ao processo pai.

Estrutura em funções + guarda `__main__` (padrão do `test_nsga2`): o teste de workers
sobe um `ProcessPoolExecutor`, e no Windows o spawn re-importa o módulo principal — com
código solto no nível do módulo, cada worker re-executaria o arquivo inteiro.
"""

import copy
import json
import random

from src.engine import config, provenance
from src.engine.fitness import (evaluate_detail, evaluate_population, set_lambdas,
                                set_lambdas_override, set_seed_base)
from src.engine.individual import Individual
from src.engine.paths import RESULTS_DIR
from src.engine.provenance import compare, config_values, fingerprint, stamp


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def _reset() -> None:
    """Volta o processo à config do arquivo — os testes de override sujam estado global."""
    provenance.clear_overrides()
    set_lambdas(config.LAMBDA_DRIFT, config.LAMBDA_DOMINANCE)


def test_stamp_is_stable():
    separator("Carimbo é estável entre chamadas")
    _reset()
    assert fingerprint() == fingerprint()
    s = stamp()
    assert compare(s).is_current
    assert "overrides" not in s, "sem override, a chave nem aparece"
    print(f"  fingerprint = {s['fingerprint']}")
    print(f"  engine      = {s['engine_digest']}   canônicos = {s['archetypes_digest']}")
    print("  ✓ duas chamadas dão o mesmo carimbo, e ele se reconhece como atual")


def test_every_constant_is_covered():
    separator("Toda constante pública de config.py entra no carimbo")
    _reset()
    esperadas = {
        name for name in dir(config)
        if name.isupper() and not name.startswith("_")
        and isinstance(getattr(config, name), (bool, int, float, str, list, tuple))
        and name not in provenance._CONFIG_EXCLUDED
    }
    gravadas = set(config_values())
    ausentes = esperadas - gravadas
    print(f"  {len(gravadas)} constantes gravadas, {len(provenance._CONFIG_EXCLUDED)} excluída(s)")
    assert not ausentes, f"constantes fora do carimbo: {sorted(ausentes)}"
    print("  ✓ nenhuma constante representável ficou de fora")

    # N_WORKERS não entra: a avaliação resemeia ao _SEED_BASE antes de cada round-robin,
    # então o resultado independe de quantos workers avaliam. Um alarme que dispara à toa
    # deixa de ser lido.
    assert "N_WORKERS" not in gravadas
    print("  ✓ N_WORKERS excluído (não muda número)")

    # As que decidem o que É equilíbrio precisam estar lá — são as que a agenda de
    # calibração fechou, e mudar qualquer uma invalida a bateria inteira.
    for crítica in ("MATCHUP_WR_CAP", "MATCHUP_FLOOR", "MATCHUP_THRESHOLD", "LAMBDA_DRIFT",
                    "LAMBDA_DOMINANCE", "ACTION_PERSISTENCE_SUBTICKS", "SIMS_PER_MATCHUP",
                    "TICK_SCALE", "ATTRIBUTE_BOUNDS", "DRIFT_DEFINING_WEIGHT"):
        assert crítica in gravadas, crítica
    print("  ✓ as constantes que definem equilíbrio e motor estão no carimbo")


def test_each_axis_diverges_alone():
    separator("Cada eixo do carimbo dispara sozinho")
    _reset()
    s = stamp()

    const = copy.deepcopy(s)
    const["config"]["MATCHUP_WR_CAP"] = 0.20
    const["fingerprint"] = "divergente"
    div = compare(const)
    assert not div.is_current
    assert div.config_changed["MATCHUP_WR_CAP"] == (0.20, config.MATCHUP_WR_CAP)
    assert not div.engine_changed and not div.archetypes_changed
    print(f"  constante:   {div.describe()[0]}")

    motor = copy.deepcopy(s)
    motor["engine_digest"] = "0" * 12
    motor["fingerprint"] = "divergente"
    div = compare(motor)
    assert div.engine_changed and not div.config_changed
    print(f"  motor:       {div.describe()[0]}")

    canon = copy.deepcopy(s)
    canon["archetypes_digest"] = "0" * 12
    canon["fingerprint"] = "divergente"
    div = compare(canon)
    assert div.archetypes_changed and not div.engine_changed
    print(f"  canônicos:   {div.describe()[0]}")

    div = compare(None)
    assert div.missing and not div.is_current
    print(f"  sem carimbo: {div.describe()[0]}")
    print("  ✓ os quatro modos de divergência são distinguidos")


def test_json_round_trip():
    separator("Carimbo sobrevive ao round-trip por JSON")
    _reset()
    # Tuplas viram listas no JSON. Se `config_values` não normalizasse, todo artefato
    # relido acusaria mudança em ATTRIBUTE_BOUNDS — falso positivo permanente.
    relido = json.loads(json.dumps(stamp(), ensure_ascii=False))
    assert compare(relido).is_current, compare(relido).describe()
    print(f"  ATTRIBUTE_BOUNDS relido como {type(relido['config']['ATTRIBUTE_BOUNDS'][0]).__name__}")
    print("  ✓ sem falso positivo por tupla↔lista")


def test_override_is_recorded():
    separator("Override de constante entra no carimbo")
    _reset()
    base = fingerprint()
    set_lambdas_override(4.0, 1.0)
    braço = stamp()

    # O valor GRAVADO é o usado, não o do arquivo — senão o artefato mentiria sobre a
    # própria origem, que é a falha que o módulo existe para impedir.
    assert braço["config"]["LAMBDA_DRIFT"] == 4.0
    assert braço["overrides"]["LAMBDA_DRIFT"] == {"usado": 4.0, "config": config.LAMBDA_DRIFT}
    assert braço["fingerprint"] != base
    print(f"  config.LAMBDA_DRIFT={config.LAMBDA_DRIFT} · gravado={braço['config']['LAMBDA_DRIFT']}")
    print(f"  fingerprint próprio: {braço['fingerprint']} (default: {base})")
    print("  ✓ o braço grava o λ que usou, com fingerprint próprio")
    _reset()
    return braço


def test_experiment_arm_is_not_stale(braço):
    separator("Braço de experimento ≠ artefato obsoleto")
    _reset()

    div = compare(braço)
    assert not div.is_current and div.is_experiment_arm
    print("  só o override diverge      → braço de experimento")

    # A regra é estrita: qualquer divergência FORA do declarado volta a ser obsoleto,
    # senão o override viraria salvo-conduto para esconder mudança de motor.
    sujo = copy.deepcopy(braço); sujo["engine_digest"] = "0" * 12
    assert not compare(sujo).is_experiment_arm
    print("  override + motor mudado    → obsoleto")

    sujo = copy.deepcopy(braço); sujo["config"]["MATCHUP_WR_CAP"] = 0.30
    assert not compare(sujo).is_experiment_arm
    print("  override + outra constante → obsoleto")
    print("  ✓ o override não é salvo-conduto")


def test_lambda_reaches_workers():
    separator("λ chega aos workers, não só ao processo pai")
    # O pool nasce por spawn no Windows e re-importa o módulo: sem propagação explícita
    # os workers avaliariam com o λ do config.py enquanto o pai usa o do braço, e a
    # divergência sairia como RESULTADO em vez de erro. É o modo de falha mais caro do
    # sweep — um braço inteiro medindo o λ errado, sem sintoma.
    _reset()
    random.seed(7)
    for λ in (0.25, 4.0):
        set_lambdas_override(λ, 1.0)
        set_seed_base(42)
        pop = [Individual.random() for _ in range(12)]
        evaluate_population(pop)                      # caminho paralelo
        paralelo = pop[0].fitness
        pop[0].invalidate_fitness()
        set_seed_base(42)
        serial = evaluate_detail(pop[0]).fitness      # caminho serial, mesmo indivíduo
        assert abs(paralelo - serial) < 1e-12, (λ, paralelo, serial)
        print(f"  λ_drift={λ:<5} worker={paralelo:.6f} == serial={serial:.6f}")
    _reset()
    print("  ✓ worker e pai avaliam sob o mesmo λ")


def test_results_artifacts():
    separator("Artefatos em results/ (se existirem)")
    _reset()
    encontrados = sorted(RESULTS_DIR.rglob("*.json")) if RESULTS_DIR.exists() else []
    if not encontrados:
        print("  results/ vazio — nada a verificar (rode a bateria)")
    for path in encontrados:
        data = json.loads(path.read_text(encoding="utf-8"))
        div = compare(data.get("provenance"))
        if div.is_current:
            marca = "✓ atual"
        elif div.is_experiment_arm:
            marca = "ℹ braço de experimento"
        else:
            marca = "⚠ " + div.describe()[0]
        print(f"  {path.relative_to(RESULTS_DIR).as_posix():<52s} {marca}")


if __name__ == "__main__":
    test_stamp_is_stable()
    test_every_constant_is_covered()
    test_each_axis_diverges_alone()
    test_json_round_trip()
    braço = test_override_is_recorded()
    test_experiment_arm_is_not_stale(braço)
    test_lambda_reaches_workers()
    test_results_artifacts()
    separator("Todos os testes passaram ✓")
