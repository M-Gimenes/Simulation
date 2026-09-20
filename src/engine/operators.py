"""Operadores genéticos: torneio, crossover por bloco, mutação gaussiana, NSGA-II."""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .config import (
    ATTRIBUTE_BOUNDS,
    ATTRIBUTE_MUTATION_SIGMA,
    ELITE_RATE,
    MUTATION_RATE,
    TOURNAMENT_SIZE,
    WEIGHT_BOUNDS,
    WEIGHT_MUTATION_SIGMA,
)
from .individual import Individual
from .provenance import override as _register_override


# ─────────────────────────────────────────────────────────────────────────────
# Parâmetros de seleção como ESTADO DE PROCESSO
# ─────────────────────────────────────────────────────────────────────────────
# Mesma razão dos λ e dos pesos do dominance (ver `fitness.py`): um sweep os varia entre
# execuções, e `from .config import X` congela o valor no import — mudar `config.ELITE_RATE`
# em tempo de execução não teria efeito nenhum aqui.
#
# **Mas sem a plumbing de `RuntimeState`**, e isso é o ponto: estes dois são lidos
# exclusivamente por `next_generation` e `tournament_selection`, que rodam só no processo
# PAI — os workers avaliam fitness, nunca reproduzem. Logo não atravessam o spawn, e
# propagá-los ao pool seria cerimônia sem efeito.

_ELITE_RATE:      float = ELITE_RATE
_TOURNAMENT_SIZE: int   = TOURNAMENT_SIZE


def set_selection(elite_rate: float, tournament_size: int) -> None:
    """Define os parâmetros de seleção neste processo."""
    global _ELITE_RATE, _TOURNAMENT_SIZE
    _ELITE_RATE, _TOURNAMENT_SIZE = elite_rate, tournament_size


def set_selection_override(elite_rate: float, tournament_size: int) -> None:
    """Como `set_selection`, e registra no carimbo. É o ponto de entrada das tools."""
    set_selection(elite_rate, tournament_size)
    _register_override("ELITE_RATE", elite_rate)
    _register_override("TOURNAMENT_SIZE", tournament_size)


def get_selection() -> Tuple[float, int]:
    """`(elite_rate, tournament_size)` em vigor."""
    return _ELITE_RATE, _TOURNAMENT_SIZE


# ─────────────────────────────────────────────────────────────────────────────
# Seleção por torneio
# ─────────────────────────────────────────────────────────────────────────────

def tournament_selection(population: List[Individual], k: Optional[int] = None) -> Individual:
    """`k = None` usa o tamanho de torneio em vigor; um `k` explícito o sobrepõe (testes)."""
    candidates = random.sample(population, _TOURNAMENT_SIZE if k is None else k)
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

def elite_count(pop_size: int) -> int:
    """Quantos indivíduos o elitismo preserva numa população deste tamanho.

    Derivado da TAXA sobre o tamanho REAL, e não de uma contagem fixa: com a contagem
    absoluta do orçamento default, uma execução de orçamento reduzido mantinha 30
    elites e o elitismo efetivo ia de 10% para 25% (pop 120) ou 100% (pop 30) — aí o
    `while` abaixo nunca roda e a geração seguinte é só clones, ou seja o AG para de
    buscar sem dar sinal nenhum.

    Mínimo de 1 **quando a taxa é positiva**: uma população pequena demais para 10% ainda
    preserva o melhor. Taxa exatamente 0 é o braço "sem elitismo" do sweep e devolve 0 —
    arredondar para 1 ali descaracterizaria o braço que existe para mostrar o que o
    elitismo segura."""
    if _ELITE_RATE <= 0.0:
        return 0
    return max(1, round(pop_size * _ELITE_RATE))


def next_generation(population: List[Individual]) -> List[Individual]:
    pop_size = len(population)
    sorted_pop = sorted(population, key=lambda ind: ind.fitness, reverse=True)

    new_gen: List[Individual] = [ind.clone() for ind in sorted_pop[:elite_count(pop_size)]]

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
