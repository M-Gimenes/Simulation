"""
Smoke test do híbrido NSGA-II → AG escalar.

O que este teste protege são as três coisas que tornam o braço comparável ao AG escalar:
o **orçamento** somar exatamente o do escalar sozinho, o **stream** da fase 2 continuar a
rotação em vez de reciclar o da fase 1, e `converged_at` vir na escala do run inteiro.
Sem qualquer uma delas o híbrido venceria a comparação por um artefato.

Tudo roda sob `if __name__ == "__main__"`: o híbrido usa o pool persistente, e no Windows
os workers re-importam o módulo de entrada — código de teste no nível do módulo viraria
recursão de processos.

Rode com: py -m src.tests.test_hybrid
"""

from src.engine import hybrid
from src.engine.fitness import generation_seed, get_seed_base, set_seed_base
from src.engine.ga import run as run_ga
from src.engine.individual import Individual

POP = 12
GENS = 8


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


class _FakeScalar:
    """Um `GAResult` de mentira: `converged_at` é aritmética de deslocamento e não
    precisa de uma execução real para ser testada."""
    def __init__(self, converged_at):
        self.converged_at = converged_at
        self.convergence_gate_fired = 1
        self.convergence_rejected = 0
        self.history = []
        self.best = None
        self.best_detail = None


def test_budget_splits_exactly():
    separator("orçamento: as duas fases somam n_generations")
    for split in (0.25, 0.5, 0.75):
        result = hybrid.run(seed=7, verbose=False, pop_size=POP, n_generations=GENS,
                            split=split)
        total = result.generations_pareto + result.generations_scalar
        assert total == GENS, (
            f"split {split}: {result.generations_pareto} + {result.generations_scalar} "
            f"= {total}, esperado {GENS}"
        )
        assert result.generations_pareto == int(GENS * split)
        print(f"  ✓ split {split}: {result.generations_pareto} Pareto + "
              f"{result.generations_scalar} escalar = {GENS}")
    print("    (é o que torna a comparação com o AG escalar de ORÇAMENTO IGUAL)")


def test_phase_two_continues_the_stream_rotation():
    separator("gen_offset: a fase escalar não recicla os streams da fase de Pareto")
    set_seed_base(None)
    run_ga(seed=7, verbose=False, pop_size=POP, n_generations=1, gen_offset=5)
    assert get_seed_base() == generation_seed(7, 6), (
        f"após 1 geração com offset 5 o base devia ser generation_seed(7, 6) = "
        f"{generation_seed(7, 6)}, veio {get_seed_base()}"
    )
    print(f"  ✓ gen_offset=5, 1 geração → generation_seed(7, 6) = {get_seed_base()}")

    set_seed_base(None)
    run_ga(seed=7, verbose=False, pop_size=POP, n_generations=1)
    assert get_seed_base() == generation_seed(7, 1)
    print(f"  ✓ sem offset, 1 geração → generation_seed(7, 1) = {get_seed_base()}")
    print("    (sem isso a fase 2 reavaliaria nos mesmos sorteios da fase 1, e a rotação")
    print("     deixaria de proteger justamente onde o ruído decide a seleção)")


def test_converged_at_is_on_the_whole_run_scale():
    separator("converged_at: deslocado pelas gerações da fase de Pareto")
    shifted = hybrid.HybridResult(scalar=_FakeScalar(3), generations_pareto=75,
                                  generations_scalar=75, carried=40, front_size=40,
                                  carry="front")
    assert shifted.converged_at == 78, (
        f"convergir na geração 3 da fase 2 de um split 50/50 é convergir na 78, "
        f"veio {shifted.converged_at}"
    )
    print("  ✓ converged_at 3 na fase 2 (75 de Pareto antes) → 78 no run inteiro")

    never = hybrid.HybridResult(scalar=_FakeScalar(None), generations_pareto=75,
                                generations_scalar=75, carried=40, front_size=40,
                                carry="front")
    assert never.converged_at is None, "não convergir não pode virar a geração 75"
    print("  ✓ não convergir segue None — não vira a geração da troca de fase")


def test_carry_modes():
    separator("carry: a fronteira inteira ou um representante")
    whole = hybrid.run(seed=7, verbose=False, pop_size=POP, n_generations=GENS,
                       carry="front")
    assert whole.carried == whole.front_size and whole.carried > 0
    print(f"  ✓ carry='front' entrega os {whole.carried} pontos da fronteira")

    one = hybrid.run(seed=7, verbose=False, pop_size=POP, n_generations=GENS,
                     carry="scalar_optimum")
    assert one.carried == 1
    print("  ✓ carry='scalar_optimum' entrega 1 ponto")
    return whole


def test_result_is_a_point_with_the_garesult_interface(whole):
    separator("interface: o híbrido devolve um ponto, como o escalar")
    assert isinstance(whole.best, Individual)
    assert whole.best_detail is not None
    for field in ("best", "best_detail", "converged_at", "convergence_gate_fired",
                  "convergence_rejected", "history"):
        assert hasattr(whole, field), f"falta `{field}` — o `multi_run` o consome"
    print("  ✓ expõe best/best_detail/converged_at/gate_fired/rejected/history")
    print("    (é o que deixa o `multi_run` tratá-lo pelo mesmo caminho do AG escalar)")


if __name__ == "__main__":
    test_budget_splits_exactly()
    test_phase_two_continues_the_stream_rotation()
    test_converged_at_is_on_the_whole_run_scale()
    whole = test_carry_modes()
    test_result_is_a_point_with_the_garesult_interface(whole)

    print(f"\n{'─'*60}")
    print("  Todos os testes de hybrid passaram ✓")
    print('─'*60)
