"""
Representação de um personagem dentro do AG.

Cada personagem possui:
  - 9 atributos numéricos (cromossomo 1)
  - 5 pesos comportamentais (cromossomo 2)

Um indivíduo do AG é composto por 5 personagens (um por arquétipo),
totalizando 70 genes.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import List, Tuple

from archetypes import ArchetypeDefinition, ArchetypeID
from config import ATTRIBUTE_BOUNDS, WEIGHT_BOUNDS


# ─────────────────────────────────────────────────────────────────────────────
# Índices dos atributos (facilita leitura no código de combate)
# ─────────────────────────────────────────────────────────────────────────────

class Attr:
    HP           = 0
    DAMAGE       = 1
    ATTACK_SPEED = 2
    RANGE        = 3
    SPEED        = 4
    DEFENSE      = 5
    STUN         = 6
    KNOCKBACK    = 7
    RECOVERY     = 8

class WIdx:
    ATTACK        = 0
    ADVANCE       = 1
    RETREAT       = 2
    DEFEND        = 3
    AGGRESSIVENESS= 4


# ─────────────────────────────────────────────────────────────────────────────
# Character
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Character:
    """
    Representa um personagem com seus genes (atributos + pesos).

    Os valores são normalizados internamente na escala definida pelo design:
      - atributos: 0–100
      - pesos:     0–1
    """
    archetype: ArchetypeDefinition
    attributes: List[float]   # 9 genes
    weights: List[float]      # 5 genes

    # ── Propriedades de acesso rápido ─────────────────────────────────────

    @property
    def hp(self)         -> float: return self.attributes[Attr.HP]
    @property
    def damage(self)     -> float: return self.attributes[Attr.DAMAGE]
    @property
    def attack_speed(self) -> float: return self.attributes[Attr.ATTACK_SPEED]
    @property
    def range_(self)     -> float: return self.attributes[Attr.RANGE]
    @property
    def speed(self)      -> float: return self.attributes[Attr.SPEED]
    @property
    def defense(self)    -> float: return self.attributes[Attr.DEFENSE]
    @property
    def stun(self)       -> float: return self.attributes[Attr.STUN]
    @property
    def knockback(self)  -> float: return self.attributes[Attr.KNOCKBACK]
    @property
    def recovery(self)   -> float: return self.attributes[Attr.RECOVERY]

    @property
    def w_attack(self)         -> float: return self.weights[WIdx.ATTACK]
    @property
    def w_advance(self)        -> float: return self.weights[WIdx.ADVANCE]
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

    # ── Construtor a partir do arquétipo (valores iniciais canônicos) ──────

    @classmethod
    def from_archetype(cls, archetype: ArchetypeDefinition) -> "Character":
        """Cria personagem com os valores iniciais definidos pelo arquétipo."""
        return cls(
            archetype=archetype,
            attributes=list(archetype.initial_attributes),
            weights=list(archetype.initial_weights),
        )

    # ── Construtor aleatório dentro dos bounds globais ────────────────────

    @classmethod
    def random(cls, archetype: ArchetypeDefinition) -> "Character":
        """Cria personagem com genes aleatórios dentro dos bounds globais."""
        attributes = [
            random.uniform(lo, hi)
            for lo, hi in ATTRIBUTE_BOUNDS
        ]
        weights = [
            random.uniform(lo, hi)
            for lo, hi in WEIGHT_BOUNDS
        ]
        return cls(archetype=archetype, attributes=attributes, weights=weights)

    # ── Utilitários ───────────────────────────────────────────────────────

    def clone(self) -> "Character":
        return copy.deepcopy(self)

    def genes(self) -> List[float]:
        """Retorna todos os genes concatenados (usado no AG)."""
        return self.attributes + self.weights

    def load_genes(self, genes: List[float]) -> None:
        """Carrega genes a partir de uma lista plana de 14 valores."""
        assert len(genes) == 14, f"Esperado 14 genes, recebido {len(genes)}"
        self.attributes = list(genes[:9])
        self.weights    = list(genes[9:])

    def clip(self) -> None:
        """Garante que todos os genes estão dentro dos bounds."""
        for i, (lo, hi) in enumerate(ATTRIBUTE_BOUNDS):
            self.attributes[i] = max(lo, min(hi, self.attributes[i]))
        for i, (lo, hi) in enumerate(WEIGHT_BOUNDS):
            self.weights[i] = max(lo, min(hi, self.weights[i]))

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{n}={v:.1f}"
            for n, v in zip(
                ["hp","dmg","as","rng","spd","def","stun","kb","rec"],
                self.attributes,
            )
        )
        ws = ", ".join(
            f"{n}={v:.2f}"
            for n, v in zip(
                ["atk","adv","ret","def","agg"],
                self.weights,
            )
        )
        return f"Character({self.name} | {attrs} | {ws})"
