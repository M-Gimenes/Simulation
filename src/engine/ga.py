"""
Loop principal do AG escalar — inicializa, evolui e retorna o melhor indivíduo.

Roda sempre o orçamento inteiro (`n_generations`, default `MAX_GENERATIONS`).
Convergência (roster equilibrado: WR global ~50% por boneco e nenhum counter duro,
confirmado fora do stream de treino) e estagnação (`STAGNATION_LIMIT` gerações sem
melhoria) são **eventos registrados**, não paradas.

Por quê: o NSGA-II não tem como parar pelo mesmo critério — "o roster está equilibrado?"
não se pergunta a uma *fronteira*, que de propósito contém pontos desequilibrados e fiéis.
Parar o escalar mais cedo tornaria a comparação entre os dois ambígua ("melhor" vira
indistinguível de "usou menos orçamento"). Com os dois em orçamento fixo, a comparação é
de **qualidade sob orçamento igual** — e `converged_at` vira um segundo eixo, de
**velocidade**, que antes não existia.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

from .combat import seed_combat
from .config import (
    CONVERGENCE_SEED_OFFSET,
    MAX_GENERATIONS,
    POPULATION_SIZE,
    SIMS_CONVERGENCE_CHECK,
    STAGNATION_LIMIT,
)
from .archetypes import ARCHETYPE_ORDER, ARCHETYPES
from .fitness import (
    FitnessDetail,
    evaluate_detail,
    evaluate_detail_n,
    evaluate_population,
    generation_seed,
    get_seed_base,
    roster_balanced,
    set_seed_base,
)
from .individual import Individual
from .operators import elite_count, next_generation
from .paths import GA_RESULTS_PATH
from .provenance import stamp


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
    converged_at: Optional[int]   # 1ª geração com equilíbrio confirmado fora do stream
    stagnated_at: Optional[int]   # 1ª geração em que a estagnação bateu o limite
    history: List[GenerationStats]
    seed: Optional[int] = None

    # Quantas vezes o gate (`roster_balanced` no laço) disparou, e em quantas delas a
    # confirmação num stream inédito RECUSOU. A razão entre os dois é o ajuste ao stream
    # de RNG quantificado numa linha — o roster parecia equilibrado sob o stream de treino
    # e não sobrevivia a outro. Medir isso exigia instrumentar o laço; sem os contadores o
    # número só existiria numa medição ad-hoc, fora de qualquer artefato.
    # Os dois param de contar na primeira confirmação aceita: seguir contando obrigaria a
    # confirmar sempre, e cada confirmação custa SIMS_CONVERGENCE_CHECK simulações.
    convergence_gate_fired: int = 0
    convergence_rejected:   int = 0

    @property
    def converged(self) -> bool:
        return self.converged_at is not None

    @property
    def stop_reason(self) -> str:
        """Descreve o que ACONTECEU — a parada é sempre por orçamento."""
        marks = []
        if self.converged_at is not None:
            marks.append(f"convergiu na geração {self.converged_at}")
        if self.stagnated_at is not None:
            marks.append(f"estagnou na geração {self.stagnated_at}")
        suffix = f" ({'; '.join(marks)})" if marks else ""
        return f"orçamento esgotado ({self.generation} gerações){suffix}"


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


def _log_header(verbose: bool, pop_size: int, n_generations: int) -> None:
    if not verbose:
        return
    names = "  ".join(f"{ARCHETYPES[aid].name[:4]:>4}" for aid in ARCHETYPE_ORDER)
    print(f"\n{'─'*80}")
    print(f"  AG iniciado — pop={pop_size}  elites={elite_count(pop_size)}  "
          f"max_gen={n_generations}")
    print(f"  Arquétipos: [{names}]")
    print(f"{'─'*80}")


# ─────────────────────────────────────────────────────────────────────────────
# Convergência
# ─────────────────────────────────────────────────────────────────────────────

def _confirm_convergence(individual: Individual) -> FitnessDetail:
    """Reavalia o indivíduo num stream de RNG **independente** do treino.

    O laço avalia todo mundo sob o mesmo stream (Common Random Numbers): é o correto
    para SELEÇÃO, porque a diferença de fitness passa a refletir genes e não sorteio.
    Mas reavaliar no mesmo stream não confirma nada — mede a mesma realização do RNG
    com mais amostras, e a confirmação não pode discordar do gate. Aqui o base vira
    `seed + CONVERGENCE_SEED_OFFSET`, então convergir significa que o equilíbrio
    **sobrevive a um stream que o AG nunca viu**. Sem semente (`None`) as avaliações
    já usam entropia e são independentes por si."""
    training_base = get_seed_base()
    if training_base is None:
        return evaluate_detail_n(individual, SIMS_CONVERGENCE_CHECK)
    set_seed_base(training_base + CONVERGENCE_SEED_OFFSET)
    try:
        return evaluate_detail_n(individual, SIMS_CONVERGENCE_CHECK)
    finally:
        set_seed_base(training_base)


# ─────────────────────────────────────────────────────────────────────────────
# Loop principal
# ─────────────────────────────────────────────────────────────────────────────

def run(
    seed: Optional[int] = None,
    verbose: bool = True,
    log_every: int = 1,
    pop_size: int = POPULATION_SIZE,
    n_generations: int = MAX_GENERATIONS,
) -> GAResult:
    """`pop_size` e `n_generations` são o ORÇAMENTO da execução. Ficam como parâmetro, e
    não só como constante, porque experimentos exploratórios (sweeps de calibração) rodam
    barato antes de a bateria rodar caro — e editar o `config.py` para isso mudaria a
    configuração global, invalidaria a comparação com o que já foi medido e é fácil de
    esquecer de desfazer. Quem varia o orçamento deve registrá-lo em
    `provenance.override`, para o artefato não afirmar o orçamento do arquivo."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        seed_combat(seed)
    set_seed_base(generation_seed(seed, 0) if seed is not None else None)

    _log_header(verbose, pop_size, n_generations)
    t_start = time.time()

    population = [Individual.from_canonical()] + [
        Individual.random() for _ in range(pop_size - 1)
    ]
    evaluate_population(population)

    history: List[GenerationStats] = []
    best_fitness_ever = -float("inf")
    stagnation_count  = 0
    converged_at: Optional[int] = None
    stagnated_at: Optional[int] = None
    gate_fired        = 0     # disparos do gate de convergência
    rejected          = 0     # recusados pela confirmação fora do stream
    best_ind          = max(population, key=lambda ind: ind.fitness)
    best_detail       = evaluate_detail(best_ind)

    for gen in range(n_generations):

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

        # Convergência = o critério de equilíbrio (C2) vale no laço (gate, de graça
        # sobre a avaliação em mãos) E sobrevive a uma reavaliação com mais simulações
        # num stream de RNG que o AG nunca viu. Mesmo predicado nas duas pontas, amostra
        # independente na segunda: é isso que faz da confirmação um teste de replicação.
        # Só até a primeira confirmação: o que interessa é QUANDO convergiu, e a
        # confirmação custa SIMS_CONVERGENCE_CHECK simulações extras por disparo.
        if converged_at is None and roster_balanced(best_detail):
            gate_fired += 1
            if roster_balanced(_confirm_convergence(best_ind)):
                converged_at = gen
            else:
                rejected += 1

        if best_ind.fitness - best_fitness_ever > 0.001:
            best_fitness_ever = best_ind.fitness
            stagnation_count  = 0
        else:
            stagnation_count += 1

        if stagnated_at is None and stagnation_count >= STAGNATION_LIMIT:
            stagnated_at = gen

        population = next_generation(population)
        if seed is not None:
            # Stream NOVO para a geração seguinte. Os elites chegam aqui medidos no
            # stream anterior, então a geração inteira é reavaliada — é o custo do
            # protocolo, e é o que mantém a comparação DENTRO da geração consistente
            # (CRN) enquanto impede o ajuste a uma única realização do RNG.
            set_seed_base(generation_seed(seed, gen + 1))
            for ind in population:
                ind.invalidate_fitness()
        evaluate_population(population)

    # O laço produz uma geração a mais que as logadas: `history` cobre
    # 0..n_generations-1 e esta população é a de índice n_generations. Rotulá-la
    # como n_generations-1 dava um número que não existe no `history`.
    best_ind    = max(population, key=lambda ind: ind.fitness)
    best_detail = evaluate_detail(best_ind)
    return GAResult(
        best=best_ind,
        best_detail=best_detail,
        generation=n_generations,
        converged_at=converged_at,
        stagnated_at=stagnated_at,
        convergence_gate_fired=gate_fired,
        convergence_rejected=rejected,
        history=history,
        seed=seed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Persistência
# ─────────────────────────────────────────────────────────────────────────────

def save_results(result: GAResult, path: Path = GA_RESULTS_PATH) -> None:
    """Grava o resultado do AG escalar. Mesmo contrato do `nsga2.save_results`:
    semente, condição de parada, objetivos do melhor indivíduo e histórico por
    geração — o suficiente para reproduzir a execução e plotar a convergência."""
    detail = result.best_detail
    data = {
        "provenance":      stamp(),
        "algorithm":       "ga",
        "seed":            result.seed,
        "generations_run": result.generation + 1,
        "stop_reason":     result.stop_reason,
        "converged_at":    result.converged_at,
        "stagnated_at":    result.stagnated_at,
        "convergence_gate_fired": result.convergence_gate_fired,
        "convergence_rejected":   result.convergence_rejected,
        "fitness":         result.best.fitness,
        "objectives": {
            "dominance_penalty": detail.dominance_penalty,
            "drift_penalty":     detail.drift_penalty,
        },
        "best_individual": [c.genes() for c in result.best.characters],
        "history": [
            {
                "gen":               s.generation,
                "best_fitness":      s.best_fitness,
                "mean_fitness":      s.mean_fitness,
                "worst_fitness":     s.worst_fitness,
                "dominance_penalty": s.dominance_penalty,
                "drift_penalty":     s.drift_penalty,
                "elapsed_s":         round(s.elapsed_s, 3),
            }
            for s in result.history
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
