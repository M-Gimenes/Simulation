"""Proveniência dos artefatos — o carimbo que faz um JSON velho se denunciar sozinho.

Mexer em `config.py`, nos canônicos ou no motor invalida **todo** o `results/` de uma vez,
e não há versionamento parcial. Sem carimbo, um artefato obsoleto é indistinguível de um
atual: `git status` fica limpo (o JSON velho segue versionado) e o mtime é o do *checkout*,
não o da geração. Foi assim que três artefatos de `external_validation` atravessaram uma
troca de motor inteira em 2026-09-17 — e a falha não apareceu como erro, apareceu como um
número plausível, numa tabela que acabou comparando o AG de uma bateria com o NSGA-II de
outra.

Três escolhas de projeto, cada uma contra um modo de falha específico:

1. **As constantes são enumeradas, não listadas à mão.** Uma lista curada apodrece em
   silêncio: a próxima constante adicionada ficaria invisível ao carimbo, que é exatamente
   o buraco que este módulo existe para fechar. Vale a mesma regra dos testes que derivam
   das tabelas em vez de repetir a aridade.
2. **O código do motor entra por digest, não só as constantes.** O incidente que motivou
   isto não foi mudança de constante — `grab_power`, a colisão e a rotação do stream são
   *código*. Um carimbo só de constantes teria dito "atual" com o motor já diferente.
3. **`config.py` fica fora do digest de código, porque seus valores são gravados um a um.**
   "`MATCHUP_WR_CAP` foi de 0,15 para 0,20" é acionável; "o hash mudou" não é.
4. **O código de MEDIÇÃO entra por artefato.** Um número post-hoc — o placar do
   validador, a posição entre piso e teto, o veredito da validação externa — é produzido
   por código fora do motor. Cada ferramenta que grava um artefato declara o próprio
   módulo, e o carimbo guarda o digest dele e de tudo de `src/` fora de `src/engine/`
   que ele importa, transitivamente. Mudar as asserções do validador invalida os
   artefatos que as usaram — e só eles, não a bateria inteira. A lista de módulos é
   derivada das importações, não escrita à mão, pela mesma razão do item 1.

Duas constantes não entram, pela mesma razão — carimbá-las faria uma mudança inócua
invalidar a bateria inteira, e um alarme que dispara à toa deixa de ser lido:

- `N_WORKERS`: cada luta é semeada por `fitness.fight_seed` a partir do `_SEED_BASE`, e
  o estado do pai viaja com cada tarefa, então o resultado independe de quantos workers
  avaliam.
- `MULTI_RUN_N_SEEDS`: é só o tamanho da amostra do `multi_run`, que o artefato dele já
  grava no corpo (`n_seeds`, `seeds`); nenhum outro artefato depende dela.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .archetypes import ARCHETYPE_ORDER, ARCHETYPES

_ENGINE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _ENGINE_DIR.parent.parent

# Fora do digest de código: `config.py` porque seus valores vão gravados um a um (mais
# informativo que um hash), `paths.py` porque layout de arquivo não muda número, e este
# próprio módulo porque carimbar o carimbador é auto-referência sem ganho.
_SOURCE_EXCLUDED = frozenset({"config.py", "paths.py", "provenance.py"})

_CONFIG_EXCLUDED = frozenset({"N_WORKERS", "MULTI_RUN_N_SEEDS"})

_DIGEST_LEN = 12


# ─────────────────────────────────────────────────────────────────────────────
# Overrides de tempo de execução
# ─────────────────────────────────────────────────────────────────────────────
#
# Um experimento que VARIA uma constante (o sweep de LAMBDA_DRIFT) quebraria o carimbo
# silenciosamente: `config.py` continuaria dizendo 1.0 enquanto a execução usa 4.0, e o
# artefato mentiria sobre a própria origem — exatamente a classe de falha que este módulo
# existe para impedir. Por isso o override é REGISTRADO aqui, na mesma fonte que carimba,
# em vez de ser um argumento que cada tool lembraria (ou não) de repassar.
#
# Efeito: `config_values()` devolve o valor EM USO, então o `fingerprint` de cada braço do
# sweep é distinto por construção, e um artefato de λ=4.0 lido sob a config padrão acusa
# `LAMBDA_DRIFT: 4.0 → 1.0`. É a leitura correta: ele foi produzido sob outra premissa.

_OVERRIDES: Dict[str, Any] = {}


def override(name: str, value: Any) -> None:
    """Registra que `name` está valendo `value` nesta execução, e não o de `config.py`.

    Um valor **igual** ao do arquivo não é override e não é registrado. Sem essa guarda,
    uma tool que chama `override` incondicionalmente (o `multi_run` chama, mesmo quando o
    λ pedido é o default) carimbaria a bateria principal com um bloco `overrides` vazio de
    conteúdo — e `is_experiment_arm` passaria a valer nela, que é exatamente a confusão
    que a distinção existe para impedir.
    """
    if not hasattr(config, name):
        raise AttributeError(f"'{name}' não é constante de config.py — override recusado")
    if _normalized(value) == _normalized(getattr(config, name)):
        _OVERRIDES.pop(name, None)
        return
    _OVERRIDES[name] = value


def override_budget(pop_size: int, n_generations: int, algorithm: str) -> None:
    """Registra o orçamento desta execução sob os nomes que o algoritmo de fato usa.

    O escalar lê `POPULATION_SIZE`/`MAX_GENERATIONS` e o NSGA-II lê
    `NSGA2_POP_SIZE`/`NSGA2_GENERATIONS` — que no `config.py` são derivados dos
    primeiros, mas são constantes distintas. Registrar os quatro quando só um algoritmo
    rodou afirmaria um orçamento que ninguém usou; registrar o par errado seria pior.

    O **híbrido** roda as duas fases e portanto lê os quatro: o orçamento registrado é o
    do run inteiro, e a repartição entre as fases fica no corpo do artefato
    (`hybrid_split`), não aqui — o carimbo diz quanto se gastou, o corpo diz como.
    """
    if algorithm in ("ga", "hybrid"):
        override("POPULATION_SIZE", pop_size)
        override("MAX_GENERATIONS", n_generations)
    if algorithm in ("nsga2", "hybrid"):
        override("NSGA2_POP_SIZE", pop_size)
        override("NSGA2_GENERATIONS", n_generations)


def overrides() -> Dict[str, Any]:
    return dict(_OVERRIDES)


def clear_overrides() -> None:
    _OVERRIDES.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Coleta
# ─────────────────────────────────────────────────────────────────────────────

def _normalized(value: Any) -> Any:
    """Valor em forma JSON, ou `None` se não for representável.

    Tuplas viram listas — `ATTRIBUTE_BOUNDS` é lista de tuplas, e JSON não distingue
    as duas; normalizar aqui evita que um round-trip pelo artefato pareça mudança.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        items = [_normalized(v) for v in value]
        return items if all(i is not None or v is None for i, v in zip(items, value)) else None
    return None


def config_values() -> Dict[str, Any]:
    """Toda constante pública de `config.py` que seja representável em JSON, **com os
    overrides aplicados** — o valor que a execução de fato usou, não o do arquivo."""
    values: Dict[str, Any] = {}
    for name in sorted(dir(config)):
        if not name.isupper() or name.startswith("_") or name in _CONFIG_EXCLUDED:
            continue
        normalized = _normalized(_OVERRIDES.get(name, getattr(config, name)))
        if normalized is not None:
            values[name] = normalized
    return values


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_DIGEST_LEN]


def engine_digest() -> str:
    """Digest do código do motor — tudo em `src/engine/` menos `_SOURCE_EXCLUDED`.

    As fontes são lidas como texto e re-unidas com `\\n`: hashear bytes crus faria o
    digest mudar por final de linha num checkout de outra plataforma, que não muda
    número nenhum.
    """
    parts: List[str] = []
    for path in sorted(_ENGINE_DIR.glob("*.py")):
        if path.name in _SOURCE_EXCLUDED:
            continue
        source = path.read_text(encoding="utf-8")
        parts.append(f"{path.name}\n" + "\n".join(source.splitlines()))
    return _digest("\n".join(parts))


def archetypes_digest() -> str:
    """Digest da premissa: genes canônicos, genes definidores e ciclo de vantagens.

    Os três entram porque os três mudam número — os canônicos são a régua do drift, os
    definidores são o peso dessa régua, e `beats` decide a leitura post-hoc do ciclo.
    """
    parts: List[str] = []
    for aid in ARCHETYPE_ORDER:
        a = ARCHETYPES[aid]
        genes = list(a.initial_attributes) + list(a.initial_weights)
        parts.append(
            f"{a.name}|{[round(g, 10) for g in genes]}"
            f"|{sorted(a.defining_genes)}|{sorted(b.name for b in a.beats)}"
        )
    return _digest("\n".join(parts))


def _module_path(module: str) -> Path:
    return _PROJECT_ROOT.joinpath(*module.split(".")).with_suffix(".py")


def measurement_modules(tool: str) -> List[str]:
    """Os módulos cujo código produz os números de `tool`, fora do motor: o próprio e
    todo módulo de `src.` fora de `src.engine` que ele importa, transitivamente. O motor
    já está no `engine_digest`."""
    seen: set = set()
    pending = [tool]
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        for node in ast.walk(ast.parse(_module_path(module).read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                targets = [node.module]
            elif isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            else:
                continue
            pending += [t for t in targets
                        if t.startswith("src.") and not t.startswith("src.engine")
                        and _module_path(t).exists()]
    return sorted(seen)


def measurement_digest(tool: str) -> str:
    """Digest do código de medição de `tool` — ver `measurement_modules`."""
    parts = [
        f"{module}\n" + "\n".join(_module_path(module).read_text(encoding="utf-8").splitlines())
        for module in measurement_modules(tool)
    ]
    return _digest("\n".join(parts))


def fingerprint() -> str:
    """Identidade única da configuração vigente: constantes + premissa + motor."""
    return _digest(
        json.dumps(config_values(), sort_keys=True)
        + archetypes_digest()
        + engine_digest()
    )


def stamp(tool: Optional[str] = None) -> Dict[str, Any]:
    """O carimbo a gravar dentro de cada artefato. `tool` é o módulo da ferramenta que
    grava o artefato (ex.: `src.experiments.baselines`); com ele, o carimbo inclui o
    digest do código de medição — ver o item 4 do cabeçalho."""
    data: Dict[str, Any] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fingerprint": fingerprint(),
        "engine_digest": engine_digest(),
        "archetypes_digest": archetypes_digest(),
        "config": config_values(),
    }
    if tool is not None:
        data["measurement"] = {
            "tool":    tool,
            "modules": measurement_modules(tool),
            "digest":  measurement_digest(tool),
        }
    if _OVERRIDES:
        # Redundante com `config` de propósito: ali o valor está misturado com as outras
        # 44 constantes, aqui fica dito que ESTE artefato é de um braço de experimento.
        data["overrides"] = {
            name: {"usado": value, "config": _normalized(getattr(config, name))}
            for name, value in sorted(_OVERRIDES.items())
        }
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Verificação
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Divergence:
    """O que mudou entre o carimbo de um artefato e a configuração de agora."""

    missing:             bool                  = False   # artefato sem carimbo
    engine_changed:      bool                  = False
    archetypes_changed:  bool                  = False
    measurement_changed: bool                  = False   # código da ferramenta que o gravou
    config_changed:     Dict[str, Any]        = field(default_factory=dict)  # nome → (gravado, atual)
    overridden:         Dict[str, Any]        = field(default_factory=dict)  # os que o artefato declarou variar
    generated_at:       Optional[str]         = None

    @property
    def is_current(self) -> bool:
        return not (self.missing or self.engine_changed or self.archetypes_changed
                    or self.measurement_changed or self.config_changed)

    @property
    def is_experiment_arm(self) -> bool:
        """Divergência **inteiramente explicada** pelos overrides que o próprio artefato
        declarou: é um braço de experimento (um λ do sweep), não um artefato obsoleto.

        A distinção existe porque um sweep gera artefatos que divergem do `config.py` **de
        propósito**. Sem ela o alarme dispararia em todos eles e viraria ruído — e um
        alarme que dispara à toa deixa de ser lido, que é a premissa do módulo inteiro.
        A regra é estrita: qualquer divergência FORA do que foi declarado (motor,
        canônicos, ou outra constante) faz o artefato voltar a ser obsoleto.
        """
        return (
            bool(self.overridden)
            and not self.missing
            and not self.engine_changed
            and not self.archetypes_changed
            and not self.measurement_changed
            and set(self.config_changed) <= set(self.overridden)
        )

    def describe(self) -> List[str]:
        """Uma linha por divergência, em ordem de gravidade."""
        if self.missing:
            return ["gerado antes de existir carimbo de proveniência — origem desconhecida"]
        lines: List[str] = []
        if self.engine_changed:
            lines.append("o CÓDIGO do motor mudou desde a geração")
        if self.archetypes_changed:
            lines.append("os CANÔNICOS mudaram — todo número de drift está inválido")
        if self.measurement_changed:
            lines.append("o CÓDIGO de medição da ferramenta que o gravou mudou desde a geração")
        for name, (recorded, current) in sorted(self.config_changed.items()):
            marca = " (variação declarada do experimento)" if name in self.overridden else ""
            lines.append(f"{name}: {recorded!r} → {current!r}{marca}")
        return lines


def _measurement_changed(recorded: Dict[str, Any],
                         reference: Optional[Dict[str, Any]]) -> bool:
    """O código de medição do artefato mudou? Contra a configuração vigente, recalcula
    o digest da ferramenta que o gravou; contra outro carimbo, compara os dois digests
    quando ambos vêm da mesma ferramenta. Fica fora do `fingerprint`, então é checado
    antes do retorno antecipado de `compare`."""
    measured = recorded.get("measurement")
    if measured is None:
        return False
    if reference is None:
        try:
            return measured["digest"] != measurement_digest(measured["tool"])
        except FileNotFoundError:
            return True                   # a ferramenta que o gravou não existe mais
    other = reference.get("measurement")
    if other is None or other["tool"] != measured["tool"]:
        return False
    return measured["digest"] != other["digest"]


def compare(recorded: Optional[Dict[str, Any]],
            reference: Optional[Dict[str, Any]] = None) -> Divergence:
    """Compara o carimbo de um artefato com uma referência.

    `reference = None` usa a **configuração vigente** — a pergunta "este artefato ainda
    descreve o sistema?". Passando outro carimbo, a pergunta vira "estes dois artefatos
    são comparáveis entre si?", que é o que dois artefatos gerados em invocações separadas
    precisam responder antes de entrar no mesmo teste estatístico.
    """
    if not recorded or "fingerprint" not in recorded:
        return Divergence(missing=True)
    if reference is not None and "fingerprint" not in reference:
        return Divergence(missing=True)

    ref_fingerprint = reference["fingerprint"] if reference else fingerprint()
    ref_engine      = reference.get("engine_digest") if reference else engine_digest()
    ref_archetypes  = reference.get("archetypes_digest") if reference else archetypes_digest()
    ref_config      = reference.get("config", {}) if reference else config_values()

    div = Divergence(
        generated_at=recorded.get("generated_at"),
        overridden=dict(recorded.get("overrides", {})),
        measurement_changed=_measurement_changed(recorded, reference),
    )
    if recorded["fingerprint"] == ref_fingerprint:
        return div

    div.engine_changed     = recorded.get("engine_digest") != ref_engine
    div.archetypes_changed = recorded.get("archetypes_digest") != ref_archetypes

    # Uma constante excluída nunca diverge — nem num artefato carimbado antes de ela sair
    # do carimbo, que ainda a traz gravada.
    names = (set(recorded.get("config", {})) | set(ref_config)) - _CONFIG_EXCLUDED
    for name in sorted(names):
        was = recorded.get("config", {}).get(name, "<ausente>")
        now = ref_config.get(name, "<removida>")
        if was != now:
            div.config_changed[name] = (was, now)
    return div


class StaleArtifactError(ValueError):
    """Um artefato que não descreve o sistema atual foi usado para GERAR outro artefato."""


def refuse_if_stale(recorded: Optional[Dict[str, Any]], source: str,
                    allow_experiment_arm: bool = False) -> None:
    """Recusa um artefato que não seja atual. O par estrito de `warn_if_stale`.

    É a porta das ferramentas que GRAVAM um artefato a partir de outro. O carimbo que
    elas escrevem é o da configuração vigente; se a entrada fosse de outra configuração,
    a saída se declararia atual carregando um número de outro sistema — o aviso
    impresso na leitura seria o único rastro, e ele não fica no arquivo.

    `allow_experiment_arm` aceita também um braço de experimento — divergência
    inteiramente explicada pelos overrides que o próprio artefato declarou. É o caso de
    um CONTROLE (λ_drift = 0, sem semente canônica), que diverge do `config.py` de
    propósito e é justamente o que se quer comparar. Mudança de motor, de canônicos ou
    de constante não declarada segue recusada.
    """
    div = compare(recorded)
    if div.is_current or (allow_experiment_arm and div.is_experiment_arm):
        return
    detalhe = "\n      · ".join(div.describe())
    raise StaleArtifactError(
        f"'{source}' não descreve o sistema atual e não pode gerar um artefato novo:\n"
        f"      · {detalhe}\n"
        f"    Regere '{source}' antes (a bateria faz isso na ordem certa)."
    )


def warn_if_stale(recorded: Optional[Dict[str, Any]], source: str) -> Divergence:
    """Imprime o aviso e devolve a divergência. O aviso é o produto deste módulo:
    um carimbo que ninguém lê não teria evitado o incidente que o motivou."""
    div = compare(recorded)
    if div.is_current:
        return div

    if div.is_experiment_arm:
        variações = ", ".join(
            f"{name}={info['usado']:g}" if isinstance(info, dict) else f"{name}={info}"
            for name, info in sorted(div.overridden.items())
        )
        print(f"\n  ℹ BRAÇO DE EXPERIMENTO — '{source}' foi gerado com {variações}, "
              f"e não com a config vigente.\n")
        return div

    print(f"\n  ⚠ ARTEFATO OBSOLETO — '{source}' não descreve o sistema atual:")
    for line in div.describe():
        print(f"      · {line}")
    if div.generated_at:
        print(f"      gerado em {div.generated_at}")
    print("      Rode a bateria antes de citar qualquer número daqui"
          " (docs/reference/10-known-issues.md §3).\n")
    return div
