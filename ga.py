"""
Loop principal do Algoritmo Genético.

Fluxo:
  1. Inicializa população com indivíduos aleatórios.
  2. Avalia toda a população (round-robin).
  3. A cada geração:
       a. Registra estatísticas e loga.
       b. Verifica convergência  → para se dominance_penalty == 0 (todos matchups ≤ 60% WR).
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
    ELITE_SIZE,
    MATCHUP_CONVERGENCE_THRESHOLD,
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
    generation:             int
    best_fitness:           float
    mean_fitness:           float
    worst_fitness:          float
    specialization_penalty: float
    drift_penalty:          float
    dominance_penalty:      float
    winrates:               List[float]
    archetype_deviations:   List[float]
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
        f"spec={stats.specialization_penalty:.4f}  "
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


def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def log_matchup_matrix(detail: FitnessDetail, indent: str = "    ") -> None:
    names  = [ARCHETYPES[aid].name[:6] for aid in ARCHETYPE_ORDER]
    n      = len(names)
    col_w  = 7
    header = f"{indent}{'':12s}" + "".join(f"{name:>{col_w}}" for name in names)
    print(header)
    print(f"{indent}{'':12s}" + "─" * (col_w * n))
    for i, aid in enumerate(ARCHETYPE_ORDER):
        row = f"{indent}{ARCHETYPES[aid].name:<12s}"
        for j in range(n):
            if i == j:
                row += f"{'—':>{col_w}}"
            else:
                lo, hi  = min(i, j), max(i, j)
                wr      = detail.matchup_winrates.get((lo, hi), 0.0)
                wr      = wr if i < j else 1.0 - wr
                color   = "\033[32m" if wr >= 0.55 else ("\033[31m" if wr <= 0.45 else "")
                reset   = "\033[0m" if color else ""
                row    += f"{color}{wr:>{col_w-1}.0%}{reset} "
        print(row)


def _log_result(result: GAResult, verbose: bool) -> None:
    if not verbose:
        return
    d = result.best_detail
    print(f"\n{'─'*80}")
    print(f"  Parada: {result.stop_reason}  (geração {result.generation})")
    print(f"  {'Fitness':22s} {result.best.fitness:+.4f}")
    print(f"  {'Dominance penalty':22s} {d.dominance_penalty:.4f}")
    print(f"  {'Specialization penalty':22s} {d.specialization_penalty:.4f}")
    print(f"  {'Drift penalty':22s} {d.drift_penalty:.4f}")

    print(f"\n  Winrate agregado por personagem:")
    for i, aid in enumerate(ARCHETYPE_ORDER):
        wr = d.winrates[i]
        print(f"    {ARCHETYPES[aid].name:<15s} [{_bar(wr)}] {wr:.1%}")

    print(f"\n  Matriz de matchup (WR da linha vs coluna):")
    log_matchup_matrix(d)

    print(f"\n  Desvio arquetípico (drift do canônico):")
    for i, aid in enumerate(ARCHETYPE_ORDER):
        dev = d.archetype_deviations[i] if i < len(d.archetype_deviations) else 0.0
        print(f"    {ARCHETYPES[aid].name:<15s} [{_bar(dev)}] {dev:.3f}")
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
            best_fitness=best_detail.fitness,
            mean_fitness=sum(fitnesses) / len(fitnesses),
            worst_fitness=min(fitnesses),
            specialization_penalty=best_detail.specialization_penalty,
            drift_penalty=best_detail.drift_penalty,
            dominance_penalty=best_detail.dominance_penalty,
            winrates=best_detail.winrates,
            archetype_deviations=best_detail.archetype_deviations,
            elapsed_s=time.time() - t_start,
        )
        history.append(stats)

        if gen % log_every == 0:
            _log(stats, verbose)

        # ── Critério de convergência ──────────────────────────────────────
        # Candidato: bal_err da avaliação normal já abaixo do threshold.
        # Confirmação: re-avalia com SIMS_CONVERGENCE_CHECK para reduzir falsos
        # positivos causados pela estocasticidade.
        if best_detail.dominance_penalty <= 1e-9:
            confirmed   = evaluate_detail_n(best_ind, SIMS_CONVERGENCE_CHECK)
            matchups_ok = all(
                abs(wr - 0.5) <= MATCHUP_CONVERGENCE_THRESHOLD
                for wr in confirmed.matchup_winrates.values()
            )
            if matchups_ok:
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
