"""
Operadores genéticos do AG.

Seleção:   torneio com k candidatos (TOURNAMENT_SIZE)
Cruzamento: por bloco de personagem — preserva coerência interna (attrs + pesos)
Mutação:   gaussiana com dois sigmas distintos:
             atributos → sigma = 0.05 × range  (maior variação)
             pesos     → sigma = 0.02 × range  (inércia evolutiva, preserva arquétipo)
Elitismo:  top ELITE_SIZE copiados diretamente para a próxima geração
"""

from __future__ import annotations

import random
from typing import List

from config import (
    ATTRIBUTE_BOUNDS,
    ATTRIBUTE_MUTATION_SIGMA,
    ELITE_SIZE,
    MUTATION_RATE,
    TOURNAMENT_SIZE,
    WEIGHT_BOUNDS,
    WEIGHT_MUTATION_SIGMA,
)
from individual import Individual


# ─────────────────────────────────────────────────────────────────────────────
# Seleção por torneio
# ─────────────────────────────────────────────────────────────────────────────

def tournament_selection(population: List[Individual], k: int = TOURNAMENT_SIZE) -> Individual:
    """
    Seleciona o melhor entre k indivíduos sorteados aleatoriamente.
    Pressupõe que todos já foram avaliados (fitness != None).
    """
    candidates = random.sample(population, k)
    return max(candidates, key=lambda ind: ind.fitness)


# ─────────────────────────────────────────────────────────────────────────────
# Cruzamento por bloco de personagem
# ─────────────────────────────────────────────────────────────────────────────

def crossover(parent1: Individual, parent2: Individual) -> Individual:
    """
    Para cada slot de personagem (0–4), escolhe aleatoriamente o bloco
    completo de um dos pais (atributos + pesos juntos).

    Preserva coerência interna: nunca mistura attrs de um pai com pesos
    do outro para o mesmo personagem.
    O filho é uma cópia profunda — modificá-lo não afeta os pais.
    """
    child_chars = []
    for i in range(len(parent1)):
        donor = parent1 if random.random() < 0.5 else parent2
        child_chars.append(donor[i].clone())

    child = Individual(characters=child_chars)   # fitness = None
    return child


# ─────────────────────────────────────────────────────────────────────────────
# Mutação gaussiana
# ─────────────────────────────────────────────────────────────────────────────

def mutate(individual: Individual, mutation_rate: float = MUTATION_RATE) -> Individual:
    """
    Aplica mutação gaussiana gene a gene com probabilidade mutation_rate.

    Atributos: sigma = ATTRIBUTE_MUTATION_SIGMA × (max - min)  → 5 unidades
    Pesos:     sigma = WEIGHT_MUTATION_SIGMA    × (max - min)  → 0.02

    Modifica o indivíduo in-place e invalida o fitness.
    Retorna o próprio indivíduo (fluent).
    """
    for char in individual.characters:
        # Atributos — maior sigma, exploração mais ampla
        for i, (lo, hi) in enumerate(ATTRIBUTE_BOUNDS):
            if random.random() < mutation_rate:
                sigma = ATTRIBUTE_MUTATION_SIGMA * (hi - lo)
                char.attributes[i] += random.gauss(0.0, sigma)

        # Pesos — sigma menor, inércia evolutiva que tende a preservar arquétipo
        for i, (lo, hi) in enumerate(WEIGHT_BOUNDS):
            if random.random() < mutation_rate:
                sigma = WEIGHT_MUTATION_SIGMA * (hi - lo)
                char.weights[i] += random.gauss(0.0, sigma)

    individual.clip()              # garante que tudo está dentro dos bounds
    individual.invalidate_fitness()
    return individual


# ─────────────────────────────────────────────────────────────────────────────
# Geração seguinte
# ─────────────────────────────────────────────────────────────────────────────

def next_generation(population: List[Individual]) -> List[Individual]:
    """
    Produz uma nova geração a partir da atual.

    1. Ordena por fitness (desc) e preserva os ELITE_SIZE melhores intactos.
    2. Preenche o resto com filhos: torneio → crossover → mutação.

    A nova geração é retornada sem avaliar — avaliação fica com o loop principal.
    Pressupõe que todos os indivíduos da população atual já estão avaliados.
    """
    pop_size = len(population)
    sorted_pop = sorted(population, key=lambda ind: ind.fitness, reverse=True)

    # Elites: clones para não compartilhar referências com a geração anterior
    new_gen: List[Individual] = [ind.clone() for ind in sorted_pop[:ELITE_SIZE]]

    # Filhos via seleção → cruzamento → mutação
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
    """
    Torneio binário usando (rank, crowding).
    Vence o de menor rank; empate → vence o de maior crowding; empate total → sorteio.
    Pressupõe que `rank` e `crowding` estão atribuídos em todos os indivíduos.
    """
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
