"""
Smoke test do carimbo de proveniência.
Rode com: py -m src.tests.test_provenance

O que precisa valer, e por quê (ver docs/reference/09-reproducibility.md):
  · o carimbo é ESTÁVEL — se variasse entre chamadas, todo artefato nasceria "obsoleto"
    e o alarme seria descartado no primeiro dia;
  · o carimbo é SENSÍVEL — pega constante, canônico e código do motor, que são as três
    coisas que invalidam `results/` — e, por artefato, o código da ferramenta que o gravou;
  · o carimbo é ESPECÍFICO — diz QUAL constante mudou, não só que algo mudou;
  · o carimbo é ENUMERADO de `config.py`, senão a próxima constante nasce invisível;
  · um BRAÇO de experimento (um sweep) não é confundido com artefato obsoleto — mas o
    override também não vira salvo-conduto para esconder mudança de motor;
  · quem GRAVA um artefato a partir de outro recusa entrada que não seja atual;
  · TODO peso (λ e os três do dominance) e as regras do combate chegam aos WORKERS, não
    só ao pai.

Estrutura em funções + guarda `__main__` (padrão do `test_nsga2`): o teste de workers
sobe um `ProcessPoolExecutor`, e no Windows o spawn re-importa o módulo principal — com
código solto no nível do módulo, cada worker re-executaria o arquivo inteiro.
"""

import copy
import json
import random

from src.engine import config, provenance
from src.engine.combat import TRAINING_RULES, set_rules
from src.engine.fitness import (evaluate_detail, evaluate_population, runtime_state,
                                set_dominance_weights, set_dominance_weights_override,
                                set_lambdas, set_lambdas_override, set_seed_base)
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
    set_dominance_weights(config.DOMINANCE_GLOBAL_WEIGHT, config.DOMINANCE_CAP_WEIGHT,
                          config.DOMINANCE_DECIS_WEIGHT)
    set_rules(TRAINING_RULES)


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

    # N_WORKERS não entra: cada luta é semeada a partir do _SEED_BASE (fitness.fight_seed),
    # então o resultado independe de quantos workers avaliam. Um alarme que dispara à toa
    # deixa de ser lido.
    assert "N_WORKERS" not in gravadas
    print("  ✓ N_WORKERS excluído (não muda número)")

    # MULTI_RUN_N_SEEDS também não: é o tamanho da amostra do multi_run, gravado no corpo
    # do artefato dele. E um artefato carimbado quando ela ainda entrava no carimbo, com
    # outro valor, continua atual — senão excluí-la invalidaria a bateria que a exclusão
    # existe para proteger.
    assert "MULTI_RUN_N_SEEDS" not in gravadas
    antigo = stamp()
    antigo["config"]["MULTI_RUN_N_SEEDS"] = config.MULTI_RUN_N_SEEDS // 2
    antigo["fingerprint"] = "de-quando-ela-entrava"
    assert compare(antigo).is_current
    print("  ✓ MULTI_RUN_N_SEEDS excluído, e um artefato que ainda a grava segue atual")

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


def test_measurement_code_is_stamped():
    separator("Código de medição entra no carimbo, por artefato")
    _reset()
    # Um número post-hoc (placar do validador, posição entre piso e teto) sai de código
    # fora do motor. Sem isto, mudar as asserções do validador deixaria o baselines.json
    # se declarando atual com o placar da regra antiga.
    tool = "src.experiments.baselines"
    modules = provenance.measurement_modules(tool)
    assert tool in modules
    assert "src.analysis.archetype_validator" in modules, "a dependência transitiva entra"
    assert not any(m.startswith("src.engine") for m in modules), "o motor já tem digest próprio"
    print(f"  {tool} → {', '.join(modules)}")

    s = stamp(tool=tool)
    assert compare(s).is_current
    velho = copy.deepcopy(s); velho["measurement"]["digest"] = "0" * 12
    div = compare(velho)
    assert div.measurement_changed and not div.is_current
    assert not div.is_experiment_arm, "mudança de medição não é variação declarada"
    print(f"  medição mudada → {div.describe()[0]}")

    assert "measurement" not in stamp(), "artefato do motor (sem ferramenta) não declara medição"
    print("  ✓ só a mudança do código que produziu os números invalida o artefato")


def test_writers_refuse_stale(braço):
    separator("Quem GRAVA um artefato a partir de outro recusa entrada não-atual")
    _reset()
    # Ler avisa; gravar recusa. Uma ferramenta que gera artefato novo carimba a config
    # VIGENTE — com entrada de outra config, o artefato novo se declararia atual
    # carregando número de outro sistema, e o aviso impresso na leitura se perderia.
    provenance.refuse_if_stale(stamp(), "atual.json")
    print("  atual                → aceito")

    velho = copy.deepcopy(stamp()); velho["engine_digest"] = "0" * 12
    velho["fingerprint"] = "divergente"
    for rótulo, recorded in (("obsoleto", velho), ("braço de experimento", braço),
                             ("sem carimbo", None)):
        try:
            provenance.refuse_if_stale(recorded, "entrada.json")
        except provenance.StaleArtifactError as exc:
            assert "entrada.json" in str(exc), "a mensagem nomeia a entrada"
            print(f"  {rótulo:<20} → recusado")
        else:
            raise AssertionError(f"{rótulo} foi aceito como entrada de um artefato novo")
    provenance.refuse_if_stale(braço, "controle.json", allow_experiment_arm=True)
    print("  braço, como controle  → aceito (a divergência é o override declarado)")
    print("  ✓ só um artefato atual gera outro")


def test_weights_reach_workers():
    separator("Todo peso e toda regra chegam aos workers, não só ao processo pai")
    # O pool nasce por spawn no Windows e re-importa o módulo: sem propagação explícita
    # os workers avaliariam com os pesos do config.py enquanto o pai usa os do braço, e a
    # divergência sairia como RESULTADO em vez de erro. É o modo de falha mais caro dos
    # sweeps — um braço inteiro medindo a configuração errada, sem sintoma.
    #
    # Os dois grupos de peso são testados porque o risco não é "esquecer de propagar",
    # é "esquecer de propagar O PRÓXIMO". `RuntimeState` existe para que acrescentar um
    # peso ao estado já o propague; este teste é o que verifica que ainda vale.
    #
    # E o pool é PERSISTENTE: os workers nascem na primeira avaliação e o estado do pai
    # muda depois — o seed-base a cada geração, os pesos a cada braço. Por isso o seed-base
    # também muda entre as iterações, todas servidas pelo mesmo pool vivo.
    _reset()
    random.seed(7)
    passo = 0
    for rótulo, aplicar, valores in (
        ("λ_drift",    lambda v: set_lambdas_override(v, config.LAMBDA_DOMINANCE), (0.0, 4.0)),
        ("dom_cap",    lambda v: set_dominance_weights_override(1.0, v, 0.5), (0.0, 4.0)),
        ("distância",  lambda v: set_rules(TRAINING_RULES._replace(initial_distance=v)),
                       (40.0, 60.0)),
    ):
        for valor in valores:
            aplicar(valor)
            semente = 42 + passo
            passo += 1
            set_seed_base(semente)
            pop = [Individual.random() for _ in range(12)]
            evaluate_population(pop)                      # caminho paralelo
            paralelo = pop[0].fitness
            pop[0].invalidate_fitness()
            set_seed_base(semente)
            serial = evaluate_detail(pop[0]).fitness      # serial, mesmo indivíduo
            assert abs(paralelo - serial) < 1e-12, (rótulo, valor, paralelo, serial)
            print(f"  {rótulo}={valor:<5} seed={semente}  worker={paralelo:.6f} == "
                  f"serial={serial:.6f}")
            _reset()

    # E o bundle tem de cobrir TODO peso que existe: se alguém adicionar um `set_*` sem
    # pôr no RuntimeState, o worker fica com o valor do config e nada acusa.
    estado = set(runtime_state()._fields)
    esperado = {"seed_base", "lambda_drift", "lambda_dominance",
                "dominance_global", "dominance_cap", "dominance_decis", "combat_rules"}
    assert estado == esperado, f"RuntimeState mudou: {estado ^ esperado}"
    print(f"  RuntimeState cobre {len(estado)} campos: {', '.join(sorted(estado))}")
    print("  ✓ worker e pai avaliam sob a mesma configuração")


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
    test_measurement_code_is_stamped()
    test_writers_refuse_stale(braço)
    test_weights_reach_workers()
    test_results_artifacts()
    separator("Todos os testes passaram ✓")
