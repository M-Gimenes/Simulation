"""
Indivíduo do AG = conjunto de 5 personagens (um por arquétipo).

Construtores: from_canonical, random, from_results, from_nsga2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .archetypes import ARCHETYPE_ORDER, ArchetypeID, ARCHETYPES
from .character import Character
from .paths import GA_RESULTS_PATH, NSGA2_RESULTS_PATH


@dataclass
class Individual:
    characters: List[Character]
    fitness: Optional[float] = field(default=None, compare=False)
    objectives: Optional[Tuple[float, float]] = field(default=None, compare=False)
    rank: Optional[int] = field(default=None, compare=False)
    crowding: Optional[float] = field(default=None, compare=False)

    # ── Construtores ──────────────────────────────────────────────────────

    @classmethod
    def from_canonical(cls) -> "Individual":
        characters = [
            Character.from_archetype(ARCHETYPES[aid])
            for aid in ARCHETYPE_ORDER
        ]
        return cls(characters=characters)

    @classmethod
    def random(cls) -> "Individual":
        characters = [
            Character.random(ARCHETYPES[aid])
            for aid in ARCHETYPE_ORDER
        ]
        return cls(characters=characters)

    @classmethod
    def _from_genes(cls, genes_list: List[List[float]]) -> "Individual":
        ind = cls.from_canonical()
        for char, genes in zip(ind.characters, genes_list):
            char.load_genes(genes)
            char.clip()
        return ind

    @classmethod
    def from_nsga2(
        cls,
        path: Path = NSGA2_RESULTS_PATH,
        representative: str = "knee_point",
    ) -> "Individual":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"'{path}' não encontrado — rode main.py --algorithm nsga2 primeiro.")
        with open(path) as fh:
            data = json.load(fh)
        reps = data.get("representatives", {})
        if representative not in reps:
            available = ", ".join(reps.keys()) if reps else "nenhum"
            raise KeyError(f"Representante '{representative}' não encontrado. Disponíveis: {available}")
        rep = reps[representative]
        ind = cls._from_genes(rep["genes"])
        objectives = rep.get("objectives")
        if objectives is not None:
            ind.objectives = tuple(objectives)
        return ind

    @classmethod
    def from_results(cls, path: Path = GA_RESULTS_PATH) -> "Individual":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"'{path}' não encontrado — rode main.py primeiro.")
        with open(path) as fh:
            data = json.load(fh)
        if "best_individual" not in data:
            raise KeyError(f"'{path}' não contém 'best_individual'.")
        return cls._from_genes(data["best_individual"])

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
        for c in self.characters:
            c.clip()

    def invalidate_fitness(self) -> None:
        self.fitness = None
        self.objectives = None

    @property
    def is_evaluated(self) -> bool:
        return self.fitness is not None

    # ── Clonagem ─────────────────────────────────────────────────────────

    def clone(self) -> "Individual":
        ind = Individual(
            characters=[c.clone() for c in self.characters],
            fitness=self.fitness,
            objectives=self.objectives,
            rank=self.rank,
            crowding=self.crowding,
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
