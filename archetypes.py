"""
Definição dos 5 arquétipos e seus valores iniciais.

Ciclo de vantagens fechado:
  Rushdown     → vence Zoner e Combo Master   (pressão não deixa iniciar setup)
  Zoner        → vence Grappler e Turtle       (controla espaço, fica fora da zona de punição)
  Grappler     → vence Rushdown e Turtle       (grab é counter ao bloqueio; burst pune recuo)
  Combo Master → vence Grappler e Zoner        (Grappler lento morre pra combo; burst converte acerto)
  Turtle       → vence Rushdown e Combo Master (bloqueio absorve pressão e quebra setup de combo)
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
    hp:           float
    damage:       float
    attack_cooldown: float
    range_:       float
    speed:        float
    defense:      float
    stun:         float
    knockback:    float
    recovery:     float

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
    """Metadados imutáveis de um arquétipo."""

    id:          ArchetypeID
    name:        str
    description: str

    initial_attributes: AttributeSet
    initial_weights:    WeightSet

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
            hp=300.0, damage=12.0, attack_cooldown=4.0, range_=18.0,
            speed=2.5, defense=0.05, stun=1.0, knockback=2.0, recovery=0.2,
        ),
        initial_weights=WeightSet(
            w_retreat=0.6, w_defend=0.2, w_aggressiveness=0.3,
        ),
        beats=(ArchetypeID.GRAPPLER, ArchetypeID.TURTLE),  # controla espaço, fica fora da zona de punição
    ),
    ArchetypeID.RUSHDOWN: ArchetypeDefinition(
        id=ArchetypeID.RUSHDOWN,
        name="Rushdown",
        description=(
            "Fecha distância em segundos e sufoca com ataques rápidos. "
            "Se ferra contra alta defesa e personagens que absorvem pressão."
        ),
        initial_attributes=AttributeSet(
            hp=320.0, damage=11.0, attack_cooldown=1.0, range_=10.0,
            speed=5.0, defense=0.10, stun=1.0, knockback=1.0, recovery=0.3,
        ),
        initial_weights=WeightSet(
            w_retreat=0.05, w_defend=0.1, w_aggressiveness=0.9,
        ),
        beats=(ArchetypeID.ZONER, ArchetypeID.COMBO_MASTER),  # pressão não deixa iniciar setup
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
            hp=350.0, damage=13.0, attack_cooldown=3.0, range_=10.0,
            speed=3.0, defense=0.15, stun=3.5, knockback=0.5, recovery=0.25,
        ),
        initial_weights=WeightSet(
            w_retreat=0.05, w_defend=0.2, w_aggressiveness=0.7,
        ),
        beats=(ArchetypeID.GRAPPLER, ArchetypeID.ZONER),  # Grappler lento morre pra combo; burst converte acerto no Zoner
    ),
    ArchetypeID.GRAPPLER: ArchetypeDefinition(
        id=ArchetypeID.GRAPPLER,
        name="Grappler",
        description=(
            "Tank que pune corpo a corpo com burst máximo. "
            "Recuperação alta resiste aos combos adversários. "
            "Sofre contra distância — range mínimo exige encosto total."
        ),
        initial_attributes=AttributeSet(
            hp=400.0, damage=20.0, attack_cooldown=4.0, range_=8.0,
            speed=2.0, defense=0.20, stun=2.5, knockback=0.5, recovery=0.35,
        ),
        initial_weights=WeightSet(
            w_retreat=0.1, w_defend=0.4, w_aggressiveness=0.7,
        ),
        beats=(ArchetypeID.RUSHDOWN, ArchetypeID.TURTLE),  # grab é counter ao bloqueio; burst pune recuo
    ),
    ArchetypeID.TURTLE: ArchetypeDefinition(
        id=ArchetypeID.TURTLE,
        name="Turtle",
        description=(
            "Muralha viva — absorve tudo e contra-ataca com paciência. "
            "Derrota agressivos pelo atrito de HP%. "
            "Perde para quem quebra a defesa com stun."
        ),
        initial_attributes=AttributeSet(
            hp=450.0, damage=10.0, attack_cooldown=5.0, range_=13.0,
            speed=1.5, defense=0.25, stun=2, knockback=1, recovery=0.5,
        ),
        initial_weights=WeightSet(
            w_retreat=0.4, w_defend=0.7, w_aggressiveness=0.2,
        ),
        beats=(ArchetypeID.RUSHDOWN, ArchetypeID.COMBO_MASTER),  # bloqueio absorve pressão e quebra setup de combo
    ),
}

# Lista ordenada (garante indexação consistente no cromossomo)
ARCHETYPE_ORDER: List[ArchetypeID] = [
    ArchetypeID.ZONER,
    ArchetypeID.RUSHDOWN,
    ArchetypeID.COMBO_MASTER,
    ArchetypeID.GRAPPLER,
    ArchetypeID.TURTLE,
]

NUM_ARCHETYPES = len(ARCHETYPE_ORDER)

# Aliases de CLI — ponto único de verdade para viewers e scripts
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
