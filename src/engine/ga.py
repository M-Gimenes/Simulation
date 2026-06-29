"""
Loop principal do AG escalar — inicializa, evolui e retorna o melhor indivíduo.

Para por convergência (roster equilibrado: WR global ~50% por boneco e nenhum
counter duro), estagnação (STAGNATION_LIMIT gerações sem melhoria) ou MAX_GENERATIONS.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .combat import seed_combat
from .config import (
    ELITE_SIZE,
    MAX_GENERATIONS,
    POPULATION_SIZE,
    SIMS_CONVERGENCE_CHECK,
    STAGNATION_LIMIT,
)
from .archetypes import ARCHETYPE_ORDER, ARCHETYPES
from .fitness import (
    FitnessDetail,
    character_balanced,
    evaluate,
    evaluate_detail,
    evaluate_detail_n,
    evaluate_population,
    is_hard_counter,
    set_seed_base,
)
from .individual import Individual
from .operators import next_generation


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados de saída
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GenerationStats:
    generation:             int
    best_fitness:           float
    mean_fitness:           float
    worst_fitness:          float
    drift_penalty:          float
    dominance_penalty:      float
    elapsed_s:              float


@dataclass
class GAResult:
    best: Individual
    best_detail: FitnessDetail
    generation: int
    converged: bool
    stagnated: bool
    history: List[GenerationStats]

    @property
    def stop_reason(self) -> str:
        if self.converged:
            return "convergência"
        if self.stagnated:
            return f"estagnação ({STAGNATION_LIMIT} gerações)"
        return f"máximo de gerações ({MAX_GENERATIONS})"


# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

def _log(stats: GenerationStats, verbose: bool) -> None:
    if not verbose:
        return
    print(
        f"Gen {stats.generation:4d} | "
        f"fit={stats.best_fitness:+.4f}  "
        f"mean={stats.mean_fitness:+.4f}  "
        f"dom={stats.dominance_penalty:.4f}  "
        f"drift={stats.drift_penalty:.3f}  "
        f"({stats.elapsed_s:.1f}s)"
    )


def _log_header(verbose: bool) -> None:
    if not verbose:
        return
    names = "  ".join(f"{ARCHETYPES[aid].name[:4]:>4}" for aid in ARCHETYPE_ORDER)
    print(f"\n{'─'*80}")
    print(f"  AG iniciado — pop={POPULATION_SIZE}  elites={ELITE_SIZE}  "
          f"max_gen={MAX_GENERATIONS}")
    print(f"  Arquétipos: [{names}]")
    print(f"{'─'*80}")


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal
# ─────────────────────────────────────────────────────────────────────────────

def run(
    seed: Optional[int] = None,
    verbose: bool = True,
    log_every: int = 1,
) -> GAResult:
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        seed_combat(seed)
    set_seed_base(seed)

    _log_header(verbose)
    t_start = time.time()

    population = [Individual.from_canonical()] + [
        Individual.random() for _ in range(POPULATION_SIZE - 1)
    ]
    evaluate_population(population)

    history: List[GenerationStats] = []
    best_fitness_ever = -float("inf")
    stagnation_count  = 0
    best_ind          = max(population, key=lambda ind: ind.fitness)
    best_detail       = evaluate_detail(best_ind)

    for gen in range(MAX_GENERATIONS):

        current_best = max(population, key=lambda ind: ind.fitness)
        if current_best.fitness != best_detail.fitness or gen == 0:
            best_ind    = current_best
            best_detail = evaluate_detail(best_ind)
            best_ind.fitness = best_detail.fitness

        fitnesses = [ind.fitness for ind in population]
        stats = GenerationStats(
            generation=gen,
            best_fitness=best_detail.fitness,
            mean_fitness=sum(fitnesses) / len(fitnesses),
            worst_fitness=min(fitnesses),
            drift_penalty=best_detail.drift_penalty,
            dominance_penalty=best_detail.dominance_penalty,
            elapsed_s=time.time() - t_start,
        )
        history.append(stats)

        if gen % log_every == 0:
            _log(stats, verbose)

        if best_detail.dominance_penalty <= 1e-9:
            confirmed = evaluate_detail_n(best_ind, SIMS_CONVERGENCE_CHECK)
            # Equilíbrio C2: nenhum boneco domina o roster (WR global ~50%) e nenhum
            # par é counter duro. NÃO exige cada par a 50% — arestas de ciclo são ok.
            global_ok = all(character_balanced(wr) for wr in confirmed.winrates)
            no_hard_counter = not any(
                is_hard_counter(wr) for wr in confirmed.matchup_winrates.values()
            )
            if global_ok and no_hard_counter:
                best_ind.fitness = confirmed.fitness
                return GAResult(
                    best=best_ind,
                    best_detail=confirmed,
                    generation=gen,
                    converged=True,
                    stagnated=False,
                    history=history,
                )

        if best_ind.fitness - best_fitness_ever > 0.001:
            best_fitness_ever = best_ind.fitness
            stagnation_count  = 0
        else:
            stagnation_count += 1

        if stagnation_count >= STAGNATION_LIMIT:
            return GAResult(
                best=best_ind,
                best_detail=best_detail,
                generation=gen,
                converged=False,
                stagnated=True,
                history=history,
            )

        population = next_generation(population)
        evaluate_population(population)

    best_ind    = max(population, key=lambda ind: ind.fitness)
    best_detail = evaluate_detail(best_ind)
    return GAResult(
        best=best_ind,
        best_detail=best_detail,
        generation=MAX_GENERATIONS - 1,
        converged=False,
        stagnated=False,
        history=history,
    )
