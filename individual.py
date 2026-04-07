"""
Indivíduo do AG — representa um conjunto completo de 5 personagens.

Por que coletivo? O winrate de cada personagem depende de todos os outros
simultaneamente. Avaliar um personagem isolado não tem sentido aqui.

Total: 70 genes por indivíduo (5 personagens × 14 genes cada).
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import List, Optional

from archetypes import ARCHETYPE_ORDER, ArchetypeID, ARCHETYPES
from character import Character


@dataclass
class Individual:
    """
    Um indivíduo da população evolutiva.

    characters: lista de 5 Character, um por arquétipo,
                na ordem definida por ARCHETYPE_ORDER.
    fitness:    valor calculado pela função de aptidão (None = não avaliado).
    """
    characters: List[Character]
    fitness: Optional[float] = field(default=None, compare=False)

    # ── Construtores ──────────────────────────────────────────────────────

    @classmethod
    def from_canonical(cls) -> "Individual":
        """Cria indivíduo com os valores iniciais canônicos de cada arquétipo."""
        characters = [
            Character.from_archetype(ARCHETYPES[aid])
            for aid in ARCHETYPE_ORDER
        ]
        return cls(characters=characters)

    @classmethod
    def random(cls) -> "Individual":
        """Cria indivíduo com genes completamente aleatórios."""
        characters = [
            Character.random(ARCHETYPES[aid])
            for aid in ARCHETYPE_ORDER
        ]
        return cls(characters=characters)

    # ── Acesso por arquétipo ──────────────────────────────────────────────

    def get(self, aid: ArchetypeID) -> Character:
        idx = ARCHETYPE_ORDER.index(aid)
        return self.characters[idx]

    def __getitem__(self, idx: int) -> Character:
        return self.characters[idx]

    def __len__(self) -> int:
        return len(self.characters)

    # ── Validação e correção ──────────────────────────────────────────────

    def clip(self) -> None:
        """Aplica clipping em todos os personagens."""
        for c in self.characters:
            c.clip()

    def invalidate_fitness(self) -> None:
        self.fitness = None

    @property
    def is_evaluated(self) -> bool:
        return self.fitness is not None

    # ── Clonagem ─────────────────────────────────────────────────────────

    def clone(self) -> "Individual":
        ind = Individual(
            characters=[c.clone() for c in self.characters],
            fitness=self.fitness,
        )
        return ind

    # ── Representação ─────────────────────────────────────────────────────

    def summary(self) -> str:
        fit_str = f"{self.fitness:.4f}" if self.fitness is not None else "N/A"
        lines = [f"Individual (fitness={fit_str})"]
        for c in self.characters:
            lines.append(f"  {c}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        fit = f"{self.fitness:.4f}" if self.fitness is not None else "N/A"
        return f"Individual(fitness={fit}, n_chars={len(self.characters)})"
