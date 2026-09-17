"""
Smoke test do carimbo de proveniência.
Rode com: py -m src.tests.test_provenance

O que precisa valer, e por quê (ver docs/reference/09-reproducibility.md):
  · o carimbo é ESTÁVEL — se ele variasse entre chamadas, todo artefato nasceria
    "obsoleto" e o alarme seria descartado no primeiro dia;
  · o carimbo é SENSÍVEL — tem de pegar constante, canônico e código do motor, que
    são as três coisas que invalidam `results/`;
  · o carimbo é ESPECÍFICO — diz QUAL constante mudou, não só que algo mudou;
  · o carimbo é ENUMERADO de `config.py`, não listado à mão, senão a próxima
    constante adicionada nasce invisível.
"""

import copy

from src.engine import config, provenance
from src.engine.provenance import compare, config_values, fingerprint, stamp


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# ── 1. Estabilidade ───────────────────────────────────────────────────────────

separator("Carimbo é estável entre chamadas")
assert fingerprint() == fingerprint()
s = stamp()
assert compare(s).is_current
print(f"  fingerprint = {s['fingerprint']}")
print(f"  engine      = {s['engine_digest']}   canônicos = {s['archetypes_digest']}")
print("  ✓ duas chamadas dão o mesmo carimbo, e ele se reconhece como atual")


# ── 2. Cobertura: as constantes vêm enumeradas de config.py ───────────────────

separator("Toda constante pública de config.py entra no carimbo")
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


# ── 3. Sensibilidade: cada eixo dispara ───────────────────────────────────────

separator("Cada eixo do carimbo dispara sozinho")

const = copy.deepcopy(s)
const["config"]["MATCHUP_WR_CAP"] = 0.20
const["fingerprint"] = "divergente"
div = compare(const)
assert not div.is_current
assert div.config_changed["MATCHUP_WR_CAP"] == (0.20, config.MATCHUP_WR_CAP)
assert not div.engine_changed and not div.archetypes_changed
print(f"  constante:  {div.describe()[0]}")

motor = copy.deepcopy(s)
motor["engine_digest"] = "0" * 12
motor["fingerprint"] = "divergente"
div = compare(motor)
assert div.engine_changed and not div.config_changed
print(f"  motor:      {div.describe()[0]}")

canon = copy.deepcopy(s)
canon["archetypes_digest"] = "0" * 12
canon["fingerprint"] = "divergente"
div = compare(canon)
assert div.archetypes_changed and not div.engine_changed
print(f"  canônicos:  {div.describe()[0]}")

div = compare(None)
assert div.missing and not div.is_current
print(f"  sem carimbo: {div.describe()[0]}")
print("  ✓ os quatro modos de divergência são distinguidos")


# ── 4. Round-trip por JSON ────────────────────────────────────────────────────

separator("Carimbo sobrevive ao round-trip por JSON")
import json

# Tuplas viram listas no JSON. Se `config_values` não normalizasse, todo artefato
# relido acusaria mudança em ATTRIBUTE_BOUNDS — falso positivo permanente.
relido = json.loads(json.dumps(s, ensure_ascii=False))
assert compare(relido).is_current, compare(relido).describe()
print(f"  ATTRIBUTE_BOUNDS gravado como {type(relido['config']['ATTRIBUTE_BOUNDS'][0]).__name__}")
print("  ✓ sem falso positivo por tupla↔lista")


# ── 5. Os artefatos em results/ estão carimbados e atuais ─────────────────────

separator("Artefatos em results/ (se existirem)")
from src.engine.paths import RESULTS_DIR

encontrados = sorted(RESULTS_DIR.rglob("*.json")) if RESULTS_DIR.exists() else []
if not encontrados:
    print("  results/ vazio — nada a verificar (rode a bateria)")
for path in encontrados:
    data = json.loads(path.read_text(encoding="utf-8"))
    div = compare(data.get("provenance"))
    marca = "✓ atual" if div.is_current else "⚠ " + div.describe()[0]
    print(f"  {path.relative_to(RESULTS_DIR).as_posix():<52s} {marca}")


separator("Todos os testes passaram ✓")
