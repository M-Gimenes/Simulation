"""
Loop principal do Algoritmo Genético.

Fluxo:
  1. Inicializa população com indivíduos aleatórios.
  2. Avalia toda a população (round-robin).
  3. A cada geração:
       a. Registra estatísticas e loga.
       b. Verifica convergência  → para se balance_error ≤ CONVERGENCE_THRESHOLD.
       c. Verifica estagnação    → para se sem melhoria > 0.001 por STAGNATION_LIMIT gerações.
       d. Produz próxima geração (elitismo + torneio + crossover + mutação).
       e. Avalia os novos indivíduos (elites já têm fitness).
  4. Retorna GAResult com o melhor indivíduo e histórico.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

from config import (
    CONVERGENCE_THRESHOLD,
    ELITE_SIZE,
    MAX_GENERATIONS,
    POPULATION_SIZE,
    SIMS_CONVERGENCE_CHECK,
    STAGNATION_LIMIT,
)
from archetypes import ARCHETYPE_ORDER, ARCHETYPES
from fitness import FitnessDetail, evaluate, evaluate_detail, evaluate_population, evaluate_detail_n
from individual import Individual
from operators import next_generation


# ─────────────────────────────────────────────────────────────────────────────
# Estruturas de dados de saída
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GenerationStats:
    generation: int
    best_fitness: float
    mean_fitness: float
    worst_fitness: float
    balance_error: float
    attribute_cost: float
    drift_penalty: float               # mean dos desvios arquetípicos
    winrates: List[float]              # por personagem, ordem ARCHETYPE_ORDER
    archetype_deviations: List[float]  # drift de cada personagem ao canônico
    elapsed_s: float                   # tempo acumulado desde o início


@dataclass
class GAResult:
    best: Individual
    best_detail: FitnessDetail
    generation: int            # geração em que parou
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
    wr_str = "  ".join(f"{wr:.2f}" for wr in stats.winrates)
    print(
        f"Gen {stats.generation:4d} | "
        f"fit={stats.best_fitness:+.4f}  "
        f"mean={stats.mean_fitness:+.4f}  "
        f"bal_err={stats.balance_error:.4f}  "
        f"attr_cost={stats.attribute_cost:.4f}  "
        f"WR=[{wr_str}]  "
        f"drift={stats.drift_penalty:.3f}  "
        f"({stats.elapsed_s:.1f}s)"
    )


def _log_header(verbose: bool) -> None:
    if not verbose:
        return
    names = "  ".join(f"{ARCHETYPES[aid].name[:4]:>4}" for aid in ARCHETYPE_ORDER)
    print(f"\n{'─'*80}")
    print(f"  AG iniciado — pop={POPULATION_SIZE}  elites={ELITE_SIZE}  "
          f"max_gen={MAX_GENERATIONS}  conv={CONVERGENCE_THRESHOLD}")
    print(f"  Arquétipos: [{names}]")
    print(f"{'─'*80}")


def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _log_result(result: GAResult, verbose: bool) -> None:
    if not verbose:
        return
    print(f"\n{'─'*80}")
    print(f"  Parada: {result.stop_reason}  (geração {result.generation})")
    print(f"  Melhor fitness: {result.best.fitness:+.4f}")
    print(f"  Balance error:  {result.best_detail.balance_error:.4f}")
    print(f"  Attribute cost: {result.best_detail.attribute_cost:.4f}")
    print(f"  Drift penalty:  {result.best_detail.drift_penalty:.4f}")
    print(f"  Winrates finais:")
    for i, aid in enumerate(ARCHETYPE_ORDER):
        name = ARCHETYPES[aid].name
        wr   = result.best_detail.winrates[i]
        print(f"    {name:15s} [{_bar(wr)}] {wr:.1%}")
    print(f"  Desvio arquetípico (drift do canônico):")
    devs = result.best_detail.archetype_deviations
    for i, aid in enumerate(ARCHETYPE_ORDER):
        name = ARCHETYPES[aid].name
        dev  = devs[i] if i < len(devs) else 0.0
        print(f"    {name:15s} [{_bar(dev)}] {dev:.3f}")
    print(f"{'─'*80}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal
# ─────────────────────────────────────────────────────────────────────────────

def run(
    seed: Optional[int] = None,
    verbose: bool = True,
    log_every: int = 1,
) -> GAResult:
    """
    Executa o AG completo.

    Args:
        seed:       semente para reprodutibilidade (None = aleatório).
        verbose:    imprime log por geração.
        log_every:  loga a cada N gerações (reduz output em runs longas).

    Returns:
        GAResult com o melhor indivíduo, histórico e motivo de parada.
    """
    if seed is not None:
        random.seed(seed)

    _log_header(verbose)
    t_start = time.time()

    # ── Inicialização ─────────────────────────────────────────────────────
    # Um indivíduo canônico semeia a população — dá ao AG um ponto de partida
    # com a estrutura de arquétipos, sem forçar preservação.
    population = [Individual.from_canonical()] + [
        Individual.random() for _ in range(POPULATION_SIZE - 1)
    ]
    evaluate_population(population)

    history: List[GenerationStats] = []
    best_fitness_ever = -float("inf")
    stagnation_count  = 0
    best_ind          = max(population, key=lambda ind: ind.fitness)
    best_detail       = evaluate_detail(best_ind)

    # ── Loop evolutivo ────────────────────────────────────────────────────
    for gen in range(MAX_GENERATIONS):

        # Melhor da geração atual (atualiza se necessário)
        current_best = max(population, key=lambda ind: ind.fitness)
        if current_best.fitness != best_detail.fitness or gen == 0:
            best_ind    = current_best
            best_detail = evaluate_detail(best_ind)
            # Sincroniza fitness com a avaliação de detalhe para manter consistência no log
            best_ind.fitness = best_detail.fitness

        # Estatísticas
        fitnesses = [ind.fitness for ind in population]
        stats = GenerationStats(
            generation=gen,
            best_fitness=best_detail.fitness,   # sempre da mesma avaliação que winrates/bal_err
            mean_fitness=sum(fitnesses) / len(fitnesses),
            worst_fitness=min(fitnesses),
            balance_error=best_detail.balance_error,
            attribute_cost=best_detail.attribute_cost,
            drift_penalty=best_detail.drift_penalty,
            winrates=best_detail.winrates,
            archetype_deviations=best_detail.archetype_deviations,
            elapsed_s=time.time() - t_start,
        )
        history.append(stats)

        if gen % log_every == 0:
            _log(stats, verbose)

        # ── Critério de convergência ──────────────────────────────────────
        # Candidato: bal_err da avaliação normal já abaixo do threshold.
        # Confirmação: re-avalia com SIMS_CONVERGENCE_CHECK (mais sims = menos ruído)
        # para evitar falsos positivos causados pela estocasticidade.
        if best_detail.balance_error <= CONVERGENCE_THRESHOLD:
            confirmed = evaluate_detail_n(best_ind, SIMS_CONVERGENCE_CHECK)
            if all(abs(wr - 0.5) <= CONVERGENCE_THRESHOLD for wr in confirmed.winrates):
                best_ind.fitness = confirmed.fitness
                _log_result(GAResult(best_ind, confirmed, gen, True, False, history), verbose)
                return GAResult(
                    best=best_ind,
                    best_detail=confirmed,
                    generation=gen,
                    converged=True,
                    stagnated=False,
                    history=history,
                )

        # ── Critério de estagnação ────────────────────────────────────────
        if best_ind.fitness - best_fitness_ever > 0.001:
            best_fitness_ever = best_ind.fitness
            stagnation_count  = 0
        else:
            stagnation_count += 1

        if stagnation_count >= STAGNATION_LIMIT:
            _log_result(GAResult(best_ind, best_detail, gen, False, True, history), verbose)
            return GAResult(
                best=best_ind,
                best_detail=best_detail,
                generation=gen,
                converged=False,
                stagnated=True,
                history=history,
            )

        # ── Próxima geração ───────────────────────────────────────────────
        population = next_generation(population)
        evaluate_population(population)

    # Máximo de gerações atingido
    best_ind    = max(population, key=lambda ind: ind.fitness)
    best_detail = evaluate_detail(best_ind)
    result = GAResult(
        best=best_ind,
        best_detail=best_detail,
        generation=MAX_GENERATIONS - 1,
        converged=False,
        stagnated=False,
        history=history,
    )
    _log_result(result, verbose)
    return result
