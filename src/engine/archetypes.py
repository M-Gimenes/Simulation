"""
Definição dos 5 arquétipos canônicos: atributos iniciais, pesos, genes definidores
e ciclo de vantagens.

Linha que separa o que o fitness pode codificar do que não pode:
  - PREMISSA (pode entrar no fitness): o que cada arquétipo É — valores canônicos e
    `defining_genes`. É dado de entrada da FGC, anterior e independente da pergunta
    de equilíbrio.
  - RESPOSTA (nunca entra no fitness): quem vence quem (`beats`) e se equilíbrio e
    identidade são compatíveis. Codificar isso responderia à pergunta com ela mesma.

Ciclo:
  Rushdown     → Zoner, Combo Master
  Zoner        → Grappler, Turtle
  Grappler     → Rushdown, Turtle
  Combo Master → Grappler, Zoner
  Turtle       → Rushdown, Combo Master
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Tuple


class ArchetypeID(Enum):
    ZONER = auto()
    RUSHDOWN = auto()
    COMBO_MASTER = auto()
    GRAPPLER = auto()
    TURTLE = auto()


# ── Conjuntos de valores iniciais ────────────────────────────────────────────

@dataclass(frozen=True)
class AttributeSet:
    hp:              float
    damage:          float
    attack_cooldown: float
    range_:          float
    speed:           float
    stun:            float
    knockback:       float
    grab_power:      float

    def __iter__(self):
        return iter(dataclasses.astuple(self))


@dataclass(frozen=True)
class WeightSet:
    w_retreat:        float
    w_defend:         float
    w_aggressiveness: float

    def __iter__(self):
        return iter(dataclasses.astuple(self))


# ── Definição de arquétipo ───────────────────────────────────────────────────

@dataclass(frozen=True)
class ArchetypeDefinition:
    id:          ArchetypeID
    name:        str
    description: str

    initial_attributes: AttributeSet
    initial_weights:    WeightSet

    # Genes em que o arquétipo ocupa um extremo por design — o que o torna
    # reconhecível. Espelham as asserções inter-personagem da Layer 1 do validador
    # (fonte única da premissa) e ponderam o drift via DRIFT_DEFINING_WEIGHT.
    defining_genes: Tuple[str, ...]

    # Ciclo de vantagens — métrica post-hoc. NUNCA referenciado pelo fitness.
    beats: Tuple[ArchetypeID, ...]


# ── Tabela de arquétipos ─────────────────────────────────────────────────────

ARCHETYPES: Dict[ArchetypeID, ArchetypeDefinition] = {
    ArchetypeID.ZONER: ArchetypeDefinition(
        id=ArchetypeID.ZONER,
        name="Zoner",
        description=(
            "Controla espaço com alcance máximo e knockback. "
            "Ataca antes do inimigo chegar e o empurra para fora de range. "
            "Sofre contra quem fecha distância rápido."
        ),
        initial_attributes=AttributeSet(
            hp=300.0, damage=20.0, attack_cooldown=4.0, range_=18.0,
            speed=2.5, stun=0.10, knockback=2.0,
            grab_power=0.05,
        ),
        initial_weights=WeightSet(
            w_retreat=0.6, w_defend=0.2, w_aggressiveness=0.3,
        ),
        defining_genes=("range", "knockback", "w_retreat"),
        beats=(ArchetypeID.GRAPPLER, ArchetypeID.TURTLE),
    ),
    ArchetypeID.RUSHDOWN: ArchetypeDefinition(
        id=ArchetypeID.RUSHDOWN,
        name="Rushdown",
        description=(
            "Fecha distância em segundos e sufoca com ataques rápidos. "
            "Se ferra contra quem absorve a pressão e pune no contra-ataque."
        ),
        initial_attributes=AttributeSet(
            hp=320.0, damage=16.0, attack_cooldown=1.0, range_=10.0,
            speed=5.0, stun=0.10, knockback=1.0,
            grab_power=0.20,
        ),
        initial_weights=WeightSet(
            w_retreat=0.05, w_defend=0.1, w_aggressiveness=0.9,
        ),
        defining_genes=("speed", "attack_cooldown", "w_aggressiveness"),
        beats=(ArchetypeID.ZONER, ArchetypeID.COMBO_MASTER),
    ),
    ArchetypeID.COMBO_MASTER: ArchetypeDefinition(
        id=ArchetypeID.COMBO_MASTER,
        name="Combo Master",
        description=(
            "Velocidade alta fecha distância, stun extremo encadeia combos. "
            "Neutraliza tanques e zoners com lockdown. "
            "Perde para pressão antes de configurar os combos."
        ),
        initial_attributes=AttributeSet(
            hp=350.0, damage=18.0, attack_cooldown=3.0, range_=10.0,
            speed=3.0, stun=0.55, knockback=0.5,
            grab_power=0.30,
        ),
        initial_weights=WeightSet(
            w_retreat=0.05, w_defend=0.2, w_aggressiveness=0.7,
        ),
        defining_genes=("stun",),
        beats=(ArchetypeID.GRAPPLER, ArchetypeID.ZONER),
    ),
    ArchetypeID.GRAPPLER: ArchetypeDefinition(
        id=ArchetypeID.GRAPPLER,
        name="Grappler",
        description=(
            "Tank que pune corpo a corpo com burst máximo. "
            "HP alto sustenta a troca até encostar. "
            "Sofre contra distância — range mínimo exige encosto total."
        ),
        initial_attributes=AttributeSet(
            hp=400.0, damage=27.0, attack_cooldown=4.0, range_=8.0,
            speed=2.0, stun=0.30, knockback=0.5,
            grab_power=0.90,
        ),
        initial_weights=WeightSet(
            w_retreat=0.1, w_defend=0.4, w_aggressiveness=0.7,
        ),
        defining_genes=("damage", "grab_power"),
        beats=(ArchetypeID.RUSHDOWN, ArchetypeID.TURTLE),
    ),
    ArchetypeID.TURTLE: ArchetypeDefinition(
        id=ArchetypeID.TURTLE,
        name="Turtle",
        description=(
            "Muralha viva — absorve tudo e contra-ataca com paciência. "
            "Derrota agressivos pelo atrito de HP%. "
            "Perde para quem rompe o bloqueio com stun."
        ),
        initial_attributes=AttributeSet(
            hp=450.0, damage=15.0, attack_cooldown=5.0, range_=13.0,
            speed=1.5, stun=0.20, knockback=1.0,
            grab_power=0.15,
        ),
        initial_weights=WeightSet(
            w_retreat=0.4, w_defend=0.7, w_aggressiveness=0.2,
        ),
        defining_genes=("hp", "attack_cooldown", "speed", "w_defend"),
        beats=(ArchetypeID.RUSHDOWN, ArchetypeID.COMBO_MASTER),
    ),
}

ARCHETYPE_ORDER: List[ArchetypeID] = [
    ArchetypeID.ZONER,
    ArchetypeID.RUSHDOWN,
    ArchetypeID.COMBO_MASTER,
    ArchetypeID.GRAPPLER,
    ArchetypeID.TURTLE,
]

ARCHETYPE_ALIASES: Dict[str, ArchetypeID] = {
    "zoner":       ArchetypeID.ZONER,
    "z":           ArchetypeID.ZONER,
    "rushdown":    ArchetypeID.RUSHDOWN,
    "rd":          ArchetypeID.RUSHDOWN,
    "combo":       ArchetypeID.COMBO_MASTER,
    "combomaster": ArchetypeID.COMBO_MASTER,
    "cm":          ArchetypeID.COMBO_MASTER,
    "grappler":    ArchetypeID.GRAPPLER,
    "grap":        ArchetypeID.GRAPPLER,
    "g":           ArchetypeID.GRAPPLER,
    "turtle":      ArchetypeID.TURTLE,
    "t":           ArchetypeID.TURTLE,
}
