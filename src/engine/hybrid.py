"""
Híbrido NSGA-II → AG escalar, com o orçamento REPARTIDO entre as duas fases.

Motivação, medida em 2026-09-22 (`docs/thesis/07-findings-and-limitations.md`, «O AG
escalar não é ótimo na própria função»): os dois termos do fitness escalar têm ruído
**diferente**. `drift` é determinístico — sai dos genes —, enquanto `dominance` é
amostrado, com desvio 0,015–0,028 a 150 lutas por par. Passada a geração de convergência
(média 31 na bateria), o gradiente verdadeiro de `dominance` está esgotado mas o ruído
não, e ele é ~60× maior que o ganho de drift por geração. A seleção escalar passa a gastar
a pressão em sorte: a linhagem de drift mínimo morre na geração 7, a diversidade de drift
colapsa até a 20, e as 130 gerações restantes rendem 0,05.

No NSGA-II isso não acontece: `drift` é objetivo separado e sem ruído, e o extremo de
drift baixo fica protegido no rank 0 pela crowding infinita. É **multi-objetivização**
(Knowles, Watson & Corne 2001) agindo como robustez a ruído.

O híbrido explora as duas coisas: a fase de Pareto preserva a linhagem fiel enquanto o
equilíbrio é procurado, e a fase escalar refina o equilíbrio a partir de uma população que
já é de drift baixo — sem ter de matar ninguém para chegar lá.

**O orçamento é o mesmo do AG escalar sozinho**: `split × n_generations` gerações de
NSGA-II e o resto de escalar. A comparação só é honesta assim; `docs/thesis/04` registra
por que o braço de orçamento dobrado (`from_nsga`) não serve de resultado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import MAX_GENERATIONS, POPULATION_SIZE
from .ga import GAResult
from .ga import run as run_ga
from .individual import Individual
from .nsga2 import run as run_nsga2

# Fração do orçamento que vai para a fase de Pareto. 0,5 é o default; o sweep das
# sementes 1000–1004 é quem o escolhe (`run_sweeps.ps1`), e não a bateria.
HYBRID_SPLIT = 0.5

# O que a fase 1 entrega à fase 2. "front" passa a fronteira inteira, "scalar_optimum" (ou
# qualquer representante do `nsga2.select_representatives`) passa um ponto só.
HYBRID_CARRY = "front"


@dataclass
class HybridResult:
    """O resultado do escalar da fase 2, com o que a fase 1 entregou. Expõe os mesmos
    campos de `GAResult` porque o `multi_run` o consome pelo mesmo caminho — o híbrido
    devolve um PONTO, como o escalar, e não uma fronteira."""
    scalar: GAResult
    generations_pareto: int
    generations_scalar: int
    carried: int
    front_size: int
    carry: str

    @property
    def best(self) -> Individual:
        return self.scalar.best

    @property
    def best_detail(self):
        return self.scalar.best_detail

    @property
    def converged_at(self) -> Optional[int]:
        """Deslocado para a escala do orçamento INTEIRO. Convergir na geração 3 da fase
        escalar de um split 50/50 sobre 150 gerações é convergir na geração 78, não na 3 —
        a fase de Pareto gastou 75 gerações de orçamento antes. Sem o deslocamento, o eixo
        de velocidade compararia coisas diferentes com o AG escalar."""
        if self.scalar.converged_at is None:
            return None
        return self.generations_pareto + self.scalar.converged_at

    @property
    def convergence_gate_fired(self) -> int:
        return self.scalar.convergence_gate_fired

    @property
    def convergence_rejected(self) -> int:
        return self.scalar.convergence_rejected

    @property
    def history(self):
        return self.scalar.history


def run(
    seed: Optional[int] = None,
    verbose: bool = True,
    pop_size: int = POPULATION_SIZE,
    n_generations: int = MAX_GENERATIONS,
    split: float = HYBRID_SPLIT,
    carry: str = HYBRID_CARRY,
) -> HybridResult:
    """`split` é a fração do orçamento que vai para o NSGA-II; o resto vai para o escalar.

    A fase 2 recebe `gen_offset = generations_pareto`, então ela **continua** a rotação de
    stream em vez de reciclar os sorteios que a fase 1 já viu — sem isso, a proteção
    contra ajuste ao stream falharia exatamente na fase em que o ruído decide a seleção.
    """
    generations_pareto = int(n_generations * split)
    generations_scalar = n_generations - generations_pareto

    if verbose:
        print(f"\n  HÍBRIDO — fase 1: NSGA-II × {generations_pareto} gerações  |  "
              f"fase 2: AG escalar × {generations_scalar}  (carry={carry})")

    pareto = run_nsga2(seed=seed, pop_size=pop_size,
                       n_generations=generations_pareto, verbose=verbose)
    if carry == "front":
        carried: List[Individual] = list(pareto.pareto_front)
    else:
        carried = [pareto.representatives[carry]]

    if verbose:
        print(f"  fase 1 terminou: fronteira com {len(pareto.pareto_front)} pontos, "
              f"{len(carried)} carregados para a fase escalar")

    scalar = run_ga(seed=seed, verbose=verbose, pop_size=pop_size,
                    n_generations=generations_scalar,
                    initial_population=carried, gen_offset=generations_pareto)

    return HybridResult(
        scalar=scalar,
        generations_pareto=generations_pareto,
        generations_scalar=generations_scalar,
        carried=len(carried),
        front_size=len(pareto.pareto_front),
        carry=carry,
    )
