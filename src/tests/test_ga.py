"""
Smoke test do contrato de convergência do AG — o ramo que foi código morto até
2026-09-16, quando o gate era `dominance_penalty <= 1e-9` (exatamente zero, portanto
inalcançável) e a confirmação rodava no mesmo stream de RNG do treino.

Rode com: py -m src.tests.test_ga
"""

from itertools import combinations

from src.engine.config import (
    CONVERGENCE_SEED_OFFSET,
    GLOBAL_CONVERGENCE_THRESHOLD,
    MATCHUP_WR_CAP,
    SIMS_CONVERGENCE_CHECK,
)
from src.engine.fitness import (
    FitnessDetail,
    evaluate_detail_n,
    get_seed_base,
    roster_balanced,
    set_seed_base,
)
from src.engine.ga import _confirm_convergence
from src.engine.individual import Individual


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def _detail(winrates, matchup_wr) -> FitnessDetail:
    """FitnessDetail mínimo para exercitar o predicado — só os campos que ele lê."""
    return FitnessDetail(
        fitness=0.0,
        winrates=list(winrates),
        matchup_winrates={
            pair: wr for pair, wr in zip(combinations(range(5), 2), matchup_wr)
        },
    )


_BALANCED_WR      = [0.5] * 5
_BALANCED_MATCHUP = [0.5] * 10


# ── 1. roster_balanced — a definição de equilíbrio do projeto ────────────────

separator("roster_balanced: banda global E ausência de counter duro")

assert roster_balanced(_detail(_BALANCED_WR, _BALANCED_MATCHUP))
print("  ✓ roster perfeitamente equilibrado passa")

# Logo dentro de cada régua passa. (Não se testa a borda EXATA: `0.5 + 0.15` não é
# representável, e o projeto nunca depende disso — WR real é razão de contagens.)
EPS = 1e-6
inside_wr = [0.5 + GLOBAL_CONVERGENCE_THRESHOLD - EPS] + [0.5] * 4
inside_mu = [0.5 + MATCHUP_WR_CAP - EPS] + [0.5] * 9
assert roster_balanced(_detail(inside_wr, _BALANCED_MATCHUP))
assert roster_balanced(_detail(_BALANCED_WR, inside_mu))
print(f"  ✓ logo dentro das réguas passa (WR global ±{GLOBAL_CONVERGENCE_THRESHOLD}, "
      f"par ±{MATCHUP_WR_CAP})")

# Um único personagem fora da banda global reprova o roster inteiro.
over_wr = [0.5 + GLOBAL_CONVERGENCE_THRESHOLD + 0.01] + [0.5] * 4
assert not roster_balanced(_detail(over_wr, _BALANCED_MATCHUP))
print("  ✓ um personagem fora da banda global reprova")

# Um único par counter duro reprova, mesmo com todos em banda global.
over_mu = [0.5 + MATCHUP_WR_CAP + 0.01] + [0.5] * 9
assert not roster_balanced(_detail(_BALANCED_WR, over_mu))
print("  ✓ um par counter duro reprova, mesmo com os 5 em banda global")

# NÃO exige cada par a 50%: arestas de ciclo dentro do teto são permitidas —
# é esse espaço que dá lugar ao ciclo de vantagens.
cycle_mu = [0.5 + MATCHUP_WR_CAP - EPS, 0.5 - MATCHUP_WR_CAP + EPS] + [0.5] * 8
assert roster_balanced(_detail(_BALANCED_WR, cycle_mu))
print("  ✓ arestas de ciclo (par com favorito, dentro do teto) NÃO reprovam")


# ── 2. Confirmação fora do stream do treino ─────────────────────────────────

separator("_confirm_convergence: stream independente, base restaurado")

ind = Individual.from_canonical()

TRAINING_SEED = 42
set_seed_base(TRAINING_SEED)
confirmed = _confirm_convergence(ind)

assert get_seed_base() == TRAINING_SEED, (
    f"O base do treino tem de ser restaurado; ficou {get_seed_base()}"
)
print(f"  ✓ base do treino ({TRAINING_SEED}) restaurado após a confirmação")

# A confirmação tem de medir num stream diferente do treino: bate com uma avaliação
# feita explicitamente no stream de confirmação, e difere da feita no do treino.
set_seed_base(TRAINING_SEED + CONVERGENCE_SEED_OFFSET)
same_stream = evaluate_detail_n(ind, SIMS_CONVERGENCE_CHECK)
set_seed_base(TRAINING_SEED)
in_stream = evaluate_detail_n(ind, SIMS_CONVERGENCE_CHECK)

assert confirmed.winrates == same_stream.winrates, (
    "A confirmação não usou o stream seed + CONVERGENCE_SEED_OFFSET"
)
print(f"  ✓ confirmação usa o stream {TRAINING_SEED} + {CONVERGENCE_SEED_OFFSET}")
assert confirmed.winrates != in_stream.winrates, (
    "A confirmação caiu no mesmo stream do treino — não confirma nada"
)
print("  ✓ o stream de confirmação difere do stream de treino")

# Sem semente, as avaliações já usam entropia: a confirmação só não pode quebrar.
set_seed_base(None)
assert _confirm_convergence(ind) is not None
assert get_seed_base() is None
print("  ✓ sem semente (entropia) a confirmação roda e não mexe no base")

set_seed_base(None)


# ── 3. Orçamento fixo: convergência é evento, não parada ────────────────────

separator("run: esgota o orçamento e registra convergência/estagnação")

import src.engine.ga as _ga
import src.engine.fitness as _fit

_originals = {m: {n: getattr(m, n) for n in
                  ("POPULATION_SIZE", "MAX_GENERATIONS", "SIMS_PER_MATCHUP",
                   "STAGNATION_LIMIT", "N_WORKERS") if hasattr(m, n)}
              for m in (_ga, _fit)}
for mod, names in (( _ga, dict(POPULATION_SIZE=8, MAX_GENERATIONS=3,
                               SIMS_PER_MATCHUP=6, STAGNATION_LIMIT=1)),
                   ( _fit, dict(SIMS_PER_MATCHUP=6, N_WORKERS=1))):
    for name, value in names.items():
        if hasattr(mod, name):
            setattr(mod, name, value)
try:
    result = _ga.run(seed=1, verbose=False)
    assert len(result.history) == 3, (
        f"o AG tem de esgotar o orçamento (3 gerações logadas), deu {len(result.history)}"
    )
    print("  ✓ roda as 3 gerações do orçamento mesmo com STAGNATION_LIMIT=1")

    # O laço produz uma população a MAIS que as logadas: `history` cobre 0..2 e o
    # melhor devolvido vem da população de índice 3. Rotulá-lo 2 (a convenção antiga)
    # apontava para uma geração que existe no history e não é a dele.
    assert result.generation == 3, (
        f"o melhor vem da população pós-laço (índice 3), veio rotulado "
        f"{result.generation}"
    )
    assert result.generation == len(result.history), (
        "o rótulo tem de ser exatamente o índice seguinte ao último do history"
    )
    print("  ✓ o melhor devolvido é rotulado com o índice da população de onde veio")

    for field in (result.converged_at, result.stagnated_at):
        assert field is None or 0 <= field < 3, f"evento fora do intervalo: {field}"
    print(f"  ✓ eventos dentro do intervalo (converged_at={result.converged_at}, "
          f"stagnated_at={result.stagnated_at})")

    assert result.converged == (result.converged_at is not None)
    assert "orçamento esgotado" in result.stop_reason
    print(f"  ✓ stop_reason descreve o que aconteceu: {result.stop_reason!r}")
finally:
    for mod, names in _originals.items():
        for name, value in names.items():
            setattr(mod, name, value)
    set_seed_base(None)


separator("Todos os testes do AG passaram ✓")
