"""
Smoke test do critério que escolhe a configuração do híbrido.

O critério é uma decisão de projeto escrita em código justamente para não ser ajustada
depois de ver os números. Este teste é o que garante que ele faz o que o texto diz — cada
um dos quatro passos, e o caso em que ele **recusa** adotar o híbrido.

Rode com: py -m src.tests.test_hybrid_choice
"""

from src.experiments.hybrid_choice import choose, evaluate_arm, paired_wins

SEEDS = [1000, 1001, 1002, 1003, 1004]


def separator(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def _artifact(dominance, counters, drift, l12, l3, tau, split=0.5, carry="front",
              balanced=True):
    """Um `multi_run` de mentira: só os campos que o critério lê. Escalares viram uma
    lista constante sobre as 5 sementes."""
    const = lambda v: v if isinstance(v, list) else [v] * len(SEEDS)
    dom, cnt, dr = const(dominance), const(counters), const(drift)
    a, b, t = const(l12), const(l3), const(tau)
    return {
        "hybrid_split": split, "hybrid_carry": carry, "seeds": SEEDS,
        "pop_size": 120, "n_generations": 60, "sims_per_matchup": 1000,
        "per_seed": [{
            "seed": s, "dominance_penalty": dom[i], "n_hard_counters": cnt[i],
            "drift_penalty": dr[i], "validator_structural": a[i],
            "validator_behavioral": b[i], "rank_agreement": t[i],
            "roster_balanced": balanced,
        } for i, s in enumerate(SEEDS)],
    }


ANCHOR = _artifact(dominance=0.040, counters=0.3, drift=0.250, l12=11, l3=2, tau=0.26)


def test_paired_wins_counts_seeds_not_medians():
    separator("paired_wins: conta sementes, e respeita a direção da métrica")
    # Pior em 4, muito melhor em 1: a mediana sobe, mas as sementes é que contam.
    lopsided = _artifact(dominance=[0.05, 0.05, 0.05, 0.05, 0.001],
                         counters=0.3, drift=0.25, l12=11, l3=2, tau=0.26)
    wins, n = paired_wins(lopsided, ANCHOR, "dominance_penalty", "menor")
    assert (wins, n) == (1, 5), f"esperado 1/5, veio {wins}/{n}"
    print("  ✓ 'menor é melhor': 1 vitória em 5 sementes")

    wins, _ = paired_wins(lopsided, ANCHOR, "rank_agreement", "maior")
    assert wins == 0, "τ idêntico não é vitória — empate não conta a favor"
    print("  ✓ 'maior é melhor': empate não conta como vitória")


def test_eliminates_arm_that_loses_balance_on_most_seeds():
    separator("passo 1: elimina quem perde equilíbrio de forma consistente")
    worse = _artifact(dominance=0.070, counters=0.3, drift=0.150, l12=15, l3=4, tau=0.55)
    card = evaluate_arm(worse, ANCHOR)
    assert card["eliminated"], "perder dominance em 5/5 tem de eliminar"
    assert "5/5" in card["elimination_reasons"][0]
    print(f"  ✓ perde dominance em 5/5 → eliminado ({card['elimination_reasons'][0]})")
    print("    (mesmo batendo as 4 réguas de identidade — é o ponto do filtro:")
    print("     comprar identidade com equilíbrio responde outra pergunta)")


def test_does_not_eliminate_on_a_hairline_median():
    separator("passo 1: uma mediana por um fio NÃO elimina")
    # Pior na mediana por 0,0001, mas ganha em 2 das 5 sementes e empata em counters.
    hairline = _artifact(dominance=[0.0401, 0.0401, 0.0401, 0.039, 0.039],
                         counters=0.3, drift=0.150, l12=15, l3=4, tau=0.55)
    card = evaluate_arm(hairline, ANCHOR)
    assert not card["eliminated"], (
        f"n = 5: mediana por um fio é ruído, não custo — razões: {card['elimination_reasons']}"
    )
    print("  ✓ pior na mediana por 0,0001, ganha 2/5 sementes → sobrevive")

    # Pior nas DUAS medidas de equilíbrio ao mesmo tempo: aí sim é evidência.
    both = _artifact(dominance=[0.0401, 0.0401, 0.0401, 0.039, 0.039],
                     counters=0.9, drift=0.150, l12=15, l3=4, tau=0.55)
    assert evaluate_arm(both, ANCHOR)["eliminated"]
    print("  ✓ pior na mediana E em counters → eliminado")


def test_counts_identity_rulers():
    separator("passo 2: conta as 4 réguas de identidade batidas")
    two = _artifact(dominance=0.030, counters=0.2, drift=0.150, l12=15, l3=2, tau=0.26)
    card = evaluate_arm(two, ANCHOR)
    assert card["n_identity_beaten"] == 2, card["identity_beaten"]
    assert set(card["identity_beaten"]) == {"drift", "L1+L2"}
    print(f"  ✓ bate drift e L1+L2, empata L3 e τ → {card['n_identity_beaten']}/4")


def test_tau_breaks_the_tie():
    separator("passo 3: desempate por τ")
    a = _artifact(dominance=0.030, counters=0.2, drift=0.150, l12=15, l3=4, tau=0.50,
                  split=0.25)
    b = _artifact(dominance=0.030, counters=0.2, drift=0.150, l12=15, l3=4, tau=0.60,
                  split=0.75)
    chosen, trail = choose([evaluate_arm(a, ANCHOR), evaluate_arm(b, ANCHOR)])
    assert chosen["split"] == 0.75, chosen
    assert any("τ" in s for s in trail)
    print("  ✓ contagem idêntica (4/4), τ 0,60 > 0,50 → vence o split 0,75")


def test_simplicity_breaks_a_full_tie():
    separator("passo 4: empate total → a configuração mais simples")
    arms = [
        evaluate_arm(_artifact(0.030, 0.2, 0.150, 15, 4, 0.55, split=s, carry=c), ANCHOR)
        for s, c in [(0.25, "front"), (0.5, "front"), (0.75, "scalar_optimum")]
    ]
    chosen, trail = choose(arms)
    assert (chosen["split"], chosen["carry"]) == (0.5, "front"), chosen
    assert any("simples" in s for s in trail)
    print("  ✓ tudo empatado → split 0,5 / front")
    print("    (com n = 5 nada separa do ruído; escolher por um fio é escolher por sorte)")


def test_refuses_to_adopt_when_nobody_survives():
    separator("o critério sabe dizer NÃO")
    arms = [
        evaluate_arm(_artifact(0.080, 1.5, 0.100, 17, 5, 0.70, split=s), ANCHOR)
        for s in (0.25, 0.5, 0.75)
    ]
    chosen, trail = choose(arms)
    assert chosen is None, "todos piores em equilíbrio → não adotar"
    assert any("NÃO é adotado" in s for s in trail)
    print("  ✓ todos eliminados → híbrido não adotado, bateria roda o protocolo padrão")
    print("    (um critério que só sabe escolher não é critério, é justificativa)")


if __name__ == "__main__":
    test_paired_wins_counts_seeds_not_medians()
    test_eliminates_arm_that_loses_balance_on_most_seeds()
    test_does_not_eliminate_on_a_hairline_median()
    test_counts_identity_rulers()
    test_tau_breaks_the_tie()
    test_simplicity_breaks_a_full_tie()
    test_refuses_to_adopt_when_nobody_survives()

    print(f"\n{'─'*60}")
    print("  Todos os testes de hybrid_choice passaram ✓")
    print('─'*60)
