"""
Personagem do AG: 8 atributos numéricos + 3 pesos comportamentais (11 genes).
Indivíduo é composto por 5 personagens, um por arquétipo (55 genes total).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from .archetypes import ArchetypeDefinition, ArchetypeID
from .config import ATTRIBUTE_BOUNDS, WEIGHT_BOUNDS


# ─────────────────────────────────────────────────────────────────────────────
# Índices dos atributos
# ─────────────────────────────────────────────────────────────────────────────

class Attr:
    HP              = 0
    DAMAGE          = 1
    ATTACK_COOLDOWN = 2
    RANGE           = 3
    SPEED           = 4
    STUN            = 5
    KNOCKBACK       = 6
    GRAB_POWER      = 7

class WIdx:
    RETREAT       = 0
    DEFEND        = 1
    AGGRESSIVENESS= 2


# ─────────────────────────────────────────────────────────────────────────────
# Character
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Character:
    archetype: ArchetypeDefinition
    attributes: List[float]
    weights: List[float]

    # ── Propriedades de acesso rápido ─────────────────────────────────────

    @property
    def hp(self)              -> float: return self.attributes[Attr.HP]
    @property
    def damage(self)          -> float: return self.attributes[Attr.DAMAGE]
    @property
    def attack_cooldown(self) -> float: return self.attributes[Attr.ATTACK_COOLDOWN]
    @property
    def range_(self)          -> float: return self.attributes[Attr.RANGE]
    @property
    def speed(self)           -> float: return self.attributes[Attr.SPEED]
    @property
    def stun(self)            -> float: return self.attributes[Attr.STUN]
    @property
    def knockback(self)       -> float: return self.attributes[Attr.KNOCKBACK]
    @property
    def grab_power(self)      -> float: return self.attributes[Attr.GRAB_POWER]

    @property
    def w_retreat(self)        -> float: return self.weights[WIdx.RETREAT]
    @property
    def w_defend(self)         -> float: return self.weights[WIdx.DEFEND]
    @property
    def w_aggressiveness(self) -> float: return self.weights[WIdx.AGGRESSIVENESS]

    @property
    def archetype_id(self) -> ArchetypeID:
        return self.archetype.id

    @property
    def name(self) -> str:
        return self.archetype.name

    # ── Construtores ──────────────────────────────────────────────────────

    @classmethod
    def from_archetype(cls, archetype: ArchetypeDefinition) -> "Character":
        return cls(
            archetype=archetype,
            attributes=list(archetype.initial_attributes),
            weights=list(archetype.initial_weights),
        )

    @classmethod
    def random(cls, archetype: ArchetypeDefinition) -> "Character":
        attributes = [
            random.uniform(lo, hi)
            for lo, hi in ATTRIBUTE_BOUNDS
        ]
        weights = [
            random.uniform(lo, hi)
            for lo, hi in WEIGHT_BOUNDS
        ]
        char = cls(archetype=archetype, attributes=attributes, weights=weights)
        char.clip()
        return char

    # ── Utilitários ───────────────────────────────────────────────────────

    def clone(self) -> "Character":
        return Character(self.archetype, self.attributes[:], self.weights[:])

    def genes(self) -> List[float]:
        return self.attributes + self.weights

    def intention_probabilities(self) -> List[float]:
        """Probabilidade de cada intenção, na ordem de `weights` — o que os 3 pesos
        significam no combate. A intenção é sorteada proporcionalmente aos pesos, então
        só a razão entre eles importa; pesos somando 0 caem sempre em GUARDA (ver
        `combat._decide_action`)."""
        total = sum(self.weights)
        if total <= 0.0:
            return [1.0 if i == WIdx.DEFEND else 0.0 for i in range(len(self.weights))]
        return [w / total for w in self.weights]

    def load_genes(self, genes: List[float]) -> None:
        n_attrs = len(ATTRIBUTE_BOUNDS)
        expected = n_attrs + len(WEIGHT_BOUNDS)
        assert len(genes) == expected, f"Esperado {expected} genes, recebido {len(genes)}"
        self.attributes = list(genes[:n_attrs])
        self.weights    = list(genes[n_attrs:])

    def clip(self) -> None:
        for i, (lo, hi) in enumerate(ATTRIBUTE_BOUNDS):
            self.attributes[i] = max(lo, min(hi, self.attributes[i]))
        for i, (lo, hi) in enumerate(WEIGHT_BOUNDS):
            self.weights[i] = max(lo, min(hi, self.weights[i]))

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{n}={v:.1f}"
            for n, v in zip(
                ["hp","dmg","cd","rng","spd","stun","kb","grab"],
                self.attributes,
            )
        )
        ws = ", ".join(
            f"{n}={v:.2f}"
            for n, v in zip(
                ["ret","def","agg"],
                self.weights,
            )
        )
        return f"Character({self.name} | {attrs} | {ws})"
