"""Operadores genéticos: torneio, crossover por bloco, mutação gaussiana, NSGA-II."""

from __future__ import annotations

import random
from typing import List

from .config import (
    ATTRIBUTE_BOUNDS,
    ATTRIBUTE_MUTATION_SIGMA,
    ELITE_SIZE,
    MUTATION_RATE,
    TOURNAMENT_SIZE,
    WEIGHT_BOUNDS,
    WEIGHT_MUTATION_SIGMA,
)
from .individual import Individual


# ─────────────────────────────────────────────────────────────────────────────
# Seleção por torneio
# ─────────────────────────────────────────────────────────────────────────────

def tournament_selection(population: List[Individual], k: int = TOURNAMENT_SIZE) -> Individual:
    candidates = random.sample(population, k)
    return max(candidates, key=lambda ind: ind.fitness)


# ─────────────────────────────────────────────────────────────────────────────
# Cruzamento por bloco de personagem
# ─────────────────────────────────────────────────────────────────────────────

def crossover(parent1: Individual, parent2: Individual) -> Individual:
    child_chars = []
    for i in range(len(parent1)):
        donor = parent1 if random.random() < 0.5 else parent2
        child_chars.append(donor[i].clone())

    child = Individual(characters=child_chars)
    return child


# ─────────────────────────────────────────────────────────────────────────────
# Mutação gaussiana
# ─────────────────────────────────────────────────────────────────────────────

def mutate(individual: Individual, mutation_rate: float = MUTATION_RATE) -> Individual:
    for char in individual.characters:
        for i, (lo, hi) in enumerate(ATTRIBUTE_BOUNDS):
            if random.random() < mutation_rate:
                sigma = ATTRIBUTE_MUTATION_SIGMA * (hi - lo)
                char.attributes[i] += random.gauss(0.0, sigma)

        for i, (lo, hi) in enumerate(WEIGHT_BOUNDS):
            if random.random() < mutation_rate:
                sigma = WEIGHT_MUTATION_SIGMA * (hi - lo)
                char.weights[i] += random.gauss(0.0, sigma)

    individual.clip()
    individual.invalidate_fitness()
    return individual


# ─────────────────────────────────────────────────────────────────────────────
# Geração seguinte
# ─────────────────────────────────────────────────────────────────────────────

def next_generation(population: List[Individual]) -> List[Individual]:
    pop_size = len(population)
    sorted_pop = sorted(population, key=lambda ind: ind.fitness, reverse=True)

    new_gen: List[Individual] = [ind.clone() for ind in sorted_pop[:ELITE_SIZE]]

    while len(new_gen) < pop_size:
        p1 = tournament_selection(population)
        p2 = tournament_selection(population)
        child = crossover(p1, p2)
        mutate(child)
        new_gen.append(child)

    return new_gen


# ─────────────────────────────────────────────────────────────────────────────
# NSGA-II — torneio binário por dominância + crowding
# ─────────────────────────────────────────────────────────────────────────────


def nsga2_binary_tournament(population: List[Individual]) -> Individual:
    a, b = random.sample(population, 2)
    if a.rank < b.rank:
        return a
    if b.rank < a.rank:
        return b
    if a.crowding > b.crowding:
        return a
    if b.crowding > a.crowding:
        return b
    return random.choice([a, b])
