"""
Indivíduo do AG — representa um conjunto completo de 5 personagens.

Por que coletivo? O winrate de cada personagem depende de todos os outros
simultaneamente. Avaliar um personagem isolado não tem sentido aqui.

Total: 60 genes por indivíduo (5 personagens × 12 genes cada).
"""

from __future__ import annotations

import copy
import json
import os
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from archetypes import ARCHETYPE_ORDER, ArchetypeID, ARCHETYPES
from character import Character


@dataclass
class Individual:
    """
    Um indivíduo da população evolutiva.

    characters: lista de 5 Character, um por arquétipo,
                na ordem definida por ARCHETYPE_ORDER.
    fitness:    valor calculado pela função de aptidão (None = não avaliado).
    objectives: tupla de 3 valores NSGA-II (None = não avaliado).
    rank:       rank de não-dominância no NSGA-II (None = não classificado).
    crowding:   distância de aglomeração no NSGA-II (None = não calculado).
    """
    characters: List[Character]
    fitness: Optional[float] = field(default=None, compare=False)
    objectives: Optional[Tuple[float, float, float]] = field(default=None, compare=False)
    rank: Optional[int] = field(default=None, compare=False)
    crowding: Optional[float] = field(default=None, compare=False)

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

    @classmethod
    def from_nsga2(
        cls,
        path: str = "results/nsga2_results.json",
        representative: str = "knee_point",
    ) -> "Individual":
        """Carrega um representante da fronteira de Pareto do NSGA-II.

        representative: 'knee_point' | 'best_balance' | 'best_matchup' | 'best_drift'
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"'{path}' não encontrado — rode main.py --algorithm nsga2 primeiro.")
        with open(path) as fh:
            data = json.load(fh)
        reps = data.get("representatives", {})
        if representative not in reps:
            available = ", ".join(reps.keys()) if reps else "nenhum"
            raise KeyError(f"Representante '{representative}' não encontrado. Disponíveis: {available}")
        genes = reps[representative]["genes"]
        ind = cls.from_canonical()
        for char, char_genes in zip(ind.characters, genes):
            char.load_genes(char_genes)
            char.clip()
        objectives = reps[representative].get("objectives")
        if objectives is not None:
            ind.objectives = tuple(objectives)
        return ind

    @classmethod
    def from_results(cls, path: str = "results/results.json") -> "Individual":
        """Carrega o melhor indivíduo salvo pelo AG em results/results.json."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"'{path}' não encontrado — rode main.py primeiro.")
        with open(path) as fh:
            data = json.load(fh)
        if "best_individual" not in data:
            raise KeyError(f"'{path}' não contém 'best_individual'.")
        ind = cls.from_canonical()
        for char, genes in zip(ind.characters, data["best_individual"]):
            char.load_genes(genes)
            char.clip()
        return ind

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
        self.objectives = None  # genes mudaram → objetivos ficam inválidos também

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
