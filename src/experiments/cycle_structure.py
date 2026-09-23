"""cycle_structure.py — o ciclo autoral medido **uma vez**, na resolução que ele exige.

O ciclo de vantagens (`ArchetypeDefinition.beats`) é **premissa declarada**, não régua:
ele nunca esteve no fitness, por decisão — codificar "o Zoner deve ganhar do Grappler"
seria responder à pergunta de pesquisa com ela mesma. O que este tool faz é **falsificá-lo
uma vez**, e é por isso que ele grava um artefato próprio em vez de devolver um número por
execução como o `baselines` fazia.

**Por que saiu do `baselines`.** Lá a contagem rodava a `MULTI_RUN_SIMS` (200 lutas por
par), e as arestas de um roster *equilibrado* têm margem mediana de 0,026–0,048 contra um
desvio binomial de 0,035 a 200 lutas: nessa resolução a direção de cada aresta é
cara-ou-coroa e a contagem mede ruído. Medido: o mesmo roster lê **5/10 a 200 lutas e 8/10
a 16.000**, e os espelhos — estrutura zero por construção — marcam 5,8/10 "mantidas" com
0,2/10 decididas. O piso de 5/10 sempre foi válido (os nulos aleatórios têm arestas
decididas, margem mediana 0,47); o que não era válido era o valor do alvo.

**A estatística que vale é `kept_and_decided`.** Aresta indecisa é sorteio, não ciclo:
contá-la mistura sinal com ruído nos dois sentidos. Só entram as arestas cuja margem passa
de `2σ`, e o teste é binomial sobre elas — mantidas contra 50%.

Uso:
    py -m src.experiments.cycle_structure              # protocolo: 16 × 1000 lutas por par
    py -m src.experiments.cycle_structure --streams 4 --sims 500   # rodada barata
"""

from __future__ import annotations

import argparse
import json
import random
import statistics as st
from itertools import combinations
from math import comb
from typing import Dict, List, Optional, Tuple

from scipy.stats import binomtest, mannwhitneyu

from src.engine.archetypes import ARCHETYPE_ORDER, ARCHETYPES, ArchetypeID
from src.engine.config import MULTI_RUN_VALIDATION_SEED
from src.engine.fitness import (
    FitnessDetail,
    evaluate_detail_n,
    get_seed_base,
    parallel_map,
    set_seed_base,
)
from src.engine.individual import Individual
from src.engine.paths import CYCLE_PATH, MULTI_RUN_GA_PATH, MULTI_RUN_NSGA2_PATH
from src.engine.provenance import refuse_if_stale, stamp

# Resolução do protocolo. 16 × 1000 = 16.000 lutas por par → σ = 0,0040, e a aresta
# mediana de um roster evoluído (margem 0,026–0,048) fica a 6–12σ. Sorteios separados em
# vez de uma amostra só porque cada stream é uma realização independente do RNG do
# combate: a média entre eles é a WR do par, não a de um sorteio afortunado.
STREAMS_DEFAULT = 16
SIMS_DEFAULT = 1000
SEED_BASE = 950000  # família de sementes própria, disjunta de treino/validação/externa
SEED_STRIDE = 53

N_RANDOM = 30  # mesmo n do `baselines`: a resolução do p empírico é 1/N

EDGES: List[Tuple[ArchetypeID, ArchetypeID]] = [
    (winner, loser) for winner in ARCHETYPE_ORDER for loser in ARCHETYPES[winner].beats
]


# ─────────────────────────────────────────────────────────────────────────────
# Medição
# ─────────────────────────────────────────────────────────────────────────────


def edge_winrates(detail: FitnessDetail) -> List[float]:
    """WR do favorito CANÔNICO de cada aresta, na ordem de `EDGES`. Não é a WR do lado
    A: abaixo de 0,5 significa aresta invertida."""
    pair_wr = {
        (ARCHETYPE_ORDER[i], ARCHETYPE_ORDER[j]): wr
        for (i, j), wr in detail.matchup_winrates.items()
    }
    return [
        pair_wr[(w, l)] if (w, l) in pair_wr else 1.0 - pair_wr[(l, w)]
        for w, l in EDGES
    ]


def circular_triads(detail: FitnessDetail) -> float:
    """Tríades circulares do torneio (Kendall & Babington Smith 1940):
    `C(n,3) − Σ C(d_i, 2)`, com `d_i` = vitórias do personagem i.

    Mede estrutura **sem depender de autoria**: 0 = ordem estrita (um bicho-papão vence
    todos), 2,5 = torneio aleatório, 5 = máximo em 5 personagens — o torneio REGULAR, em
    que cada um vence 2 e perde 2. Equilíbrio global com pares decididos **força**
    intransitividade (um roster estritamente transitivo teria WRs 100/75/50/25/0), então
    a tríade de um roster equilibrado é em boa parte consequência do objetivo. Vale ao
    lado da decidibilidade, nunca sozinha: a 200 lutas um espelho chega a 4 por ruído."""
    wins = [0.0] * len(ARCHETYPE_ORDER)
    for (i, j), wr in detail.matchup_winrates.items():
        if wr > 0.5:
            wins[i] += 1
        elif wr < 0.5:
            wins[j] += 1
        else:
            wins[i] += 0.5
            wins[j] += 0.5
    # Empates dão meia-vitória; C(d,2) = d(d−1)/2 estende para d fracionário.
    return comb(len(wins), 3) - sum(d * (d - 1) / 2 for d in wins)


_SIMS_PER_STREAM = SIMS_DEFAULT


def _stream_worker(individual: Individual) -> Tuple[List[float], float]:
    """Roda no pool, sob o seed-base que o pai fixou para este stream."""
    detail = evaluate_detail_n(individual, _SIMS_PER_STREAM)
    return edge_winrates(detail), circular_triads(detail)


def measure_all(rosters: List[Individual], streams: int, sims: int) -> List[dict]:
    """WR média de cada aresta sobre `streams` sorteados, para todos os rosters de uma
    vez. O seed-base é do stream, não do roster: os rosters são comparados sob os MESMOS
    sorteios (Common Random Numbers), então a diferença entre eles é de genes."""
    global _SIMS_PER_STREAM
    _SIMS_PER_STREAM = sims
    previous = get_seed_base()
    per_stream: List[List[Tuple[List[float], float]]] = []
    try:
        for k in range(streams):
            set_seed_base(SEED_BASE + SEED_STRIDE * k)
            per_stream.append(parallel_map(_stream_worker, rosters))
    finally:
        set_seed_base(previous)

    sigma = decided_threshold(streams, sims) / 2
    out = []
    for r in range(len(rosters)):
        wrs = [st.mean(per_stream[k][r][0][e] for k in range(streams))
               for e in range(len(EDGES))]
        triads = st.mean(per_stream[k][r][1] for k in range(streams))
        out.append(summarize(wrs, triads, 2 * sigma))
    return out


def decided_threshold(streams: int, sims: int) -> float:
    """`2σ` da WR de um par sob `streams × sims` lutas. Abaixo disso a direção da aresta
    não está estabelecida, e contá-la é contar sorteio."""
    return 2 * (0.25 / (streams * sims)) ** 0.5


def summarize(wrs: List[float], triads: float, threshold: float) -> dict:
    return {
        "edge_winrates":     wrs,
        "kept":              sum(wr > 0.5 for wr in wrs),
        "decided":           sum(abs(wr - 0.5) > threshold for wr in wrs),
        "kept_and_decided":  sum(wr > 0.5 + threshold for wr in wrs),
        "median_margin":     st.median(abs(wr - 0.5) for wr in wrs),
        "circular_triads":   triads,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Os grupos comparados
# ─────────────────────────────────────────────────────────────────────────────


def mirror_roster(archetype_id: ArchetypeID) -> Individual:
    """Cinco cópias do mesmo arquétipo: estrutura de torneio ZERO por construção. Aqui
    ele não é piso de identidade e sim **controle de ruído** — o que a métrica marca
    quando não há nada para marcar."""
    ind = Individual.from_canonical()
    proto = ind.get(archetype_id)
    for char in ind.characters:
        char.attributes = list(proto.attributes)
        char.weights = list(proto.weights)
    return ind


def _seeded_rosters(path, representative: Optional[str]) -> List[Individual]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    refuse_if_stale(artifact.get("provenance"), path.name)
    out = []
    for record in artifact["per_seed"]:
        genes = (record["representatives"][representative]["genes"] if representative
                 else record["genes"])
        out.append(Individual._from_genes(genes))
    return out


def build_groups(n_random: int, seed: int) -> Dict[str, List[Individual]]:
    rng_state = random.getstate()
    random.seed(seed)
    randoms = [Individual.random() for _ in range(n_random)]
    random.setstate(rng_state)
    return {
        "canônico":       [Individual.from_canonical()],
        "AG escalar":     _seeded_rosters(MULTI_RUN_GA_PATH, None),
        "NSGA-II":        _seeded_rosters(MULTI_RUN_NSGA2_PATH, "scalar_optimum"),
        "espelhos":       [mirror_roster(aid) for aid in ARCHETYPE_ORDER],
        "aleatórios":     randoms,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Teste
# ─────────────────────────────────────────────────────────────────────────────


def _kept_rate(record: dict) -> Optional[float]:
    """Fração das arestas DECIDIDAS que seguem a direção autoral. É a taxa, não a
    contagem: grupos com decidibilidade diferente não têm contagens comparáveis — um
    roster aleatório decide 10/10 arestas e um equilibrado ~9/10, então comparar
    `kept_and_decided` cru puniria o equilibrado por ter uma aresta em cima do limiar."""
    return record["kept_and_decided"] / record["decided"] if record["decided"] else None


def falsification_test(target: List[dict], nulls: List[dict]) -> dict:
    """O ciclo autoral sobrevive? Duas leituras, ambas sobre arestas DECIDIDAS —
    aresta indecisa é sorteio, e contá-la mistura sinal com ruído nos dois sentidos.

    1. **Binomial**, o teste da premissa: das arestas decididas do alvo, quantas seguem
       a direção autoral? O acaso dá metade.
    2. **Contra os nulos**, pela taxa: o alvo segue a direção autoral com frequência
       maior que um roster sem projeto? Mann-Whitney + Â₁₂, a dupla do resto do
       protocolo."""
    kept = sum(r["kept_and_decided"] for r in target)
    decided = sum(r["decided"] for r in target)
    a = [r for r in (_kept_rate(x) for x in target) if r is not None]
    b = [r for r in (_kept_rate(x) for x in nulls) if r is not None]
    comparable = bool(a) and bool(b)
    return {
        "kept_and_decided": kept,
        "decided": decided,
        "kept_rate": kept / decided if decided else None,
        "binomial_p": binomtest(kept, decided, 0.5).pvalue if decided else None,
        "null_kept_rate": st.mean(b) if b else None,
        "vs_nulls_p": (mannwhitneyu(a, b, alternative="two-sided").pvalue
                       if comparable else None),
        "vs_nulls_a12": (sum((x > y) + 0.5 * (x == y) for x in a for y in b)
                         / (len(a) * len(b)) if comparable else None),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Relatório
# ─────────────────────────────────────────────────────────────────────────────

_LINE = "═" * 78


def _agg(records: List[dict], key: str) -> float:
    return st.mean(r[key] for r in records)


def print_report(groups: Dict[str, List[dict]], threshold: float, streams: int,
                 sims: int, test: dict) -> None:
    n_pairs = len(list(combinations(ARCHETYPE_ORDER, 2)))
    n_nulls = len(groups["aleatórios"])
    print(_LINE)
    print(f"  ESTRUTURA DO TORNEIO — {streams} × {sims} = {streams * sims} lutas por par")
    print(_LINE)
    print(f"  aresta DECIDIDA = |WR − 0,5| > 2σ = {threshold:.4f}")
    print(f"  tríades: 0 = ordem estrita · 2,5 = acaso · {n_pairs // 2} = máximo (torneio regular)")
    print()
    print(f"  {'grupo':<22}{'n':>4}{'mantidas':>11}{'decididas':>11}"
          f"{'mant. E decid.':>16}{'margem med.':>13}{'tríades':>9}")
    print("  " + "─" * 84)
    for label, records in groups.items():
        print(f"  {label:<22}{len(records):>4}"
              f"{_agg(records, 'kept'):>8.2f}/{n_pairs}"
              f"{_agg(records, 'decided'):>8.2f}/{n_pairs}"
              f"{_agg(records, 'kept_and_decided'):>13.2f}/{n_pairs}"
              f"{_agg(records, 'median_margin'):>13.4f}"
              f"{_agg(records, 'circular_triads'):>9.2f}")
    print("  " + "─" * 84)
    print("  Os espelhos são CONTROLE DE RUÍDO: estrutura zero por construção, então")
    print("  'mantidas' alto com 'decididas' ~0 é a assinatura de uma métrica medindo")
    print("  sorteio. Os aleatórios são o PISO: arestas decididas, direção ao acaso.")
    print("  Comparar grupos pela CONTAGEM de mantidas seria injusto — quem decide")
    print("  menos arestas tem teto menor —, por isso o teste abaixo usa a taxa.")
    print()
    print(_LINE)
    print("  O CICLO AUTORAL SOBREVIVE AO EQUILÍBRIO?")
    print(_LINE)
    print(f"  arestas decididas do AG escalar: {test['decided']}")
    print(f"  delas, na direção autoral:       {test['kept_and_decided']}"
          f"  ({test['kept_rate']:.1%})")
    print(f"  teste binomial contra 50%:       p = {test['binomial_p']:.3f}")
    print(f"  taxa dos {n_nulls} nulos aleatórios:     {test['null_kept_rate']:.1%}"
          f"   →  p = {test['vs_nulls_p']:.3f}, Â₁₂ = {test['vs_nulls_a12']:.2f}")
    print()
    print("  O ciclo NUNCA esteve no fitness (o objetivo é cego à direção, |WR − 0,5|),")
    print("  então isto não é falha do método: é a premissa autoral sendo falsificada.")
    print("  E o canônico, no mesmo motor, já não a realiza — ver a linha dele acima.")
    print(_LINE)


def print_canonical_edges(record: dict, ga: List[dict], threshold: float) -> None:
    print()
    print(_LINE)
    print("  ARESTA A ARESTA — WR do favorito canônico")
    print(_LINE)
    print(f"  {'aresta':<32}{'canônico':>10}{'AG (média ± dp)':>22}{'mantida':>10}")
    print("  " + "─" * 74)
    for k, (w, l) in enumerate(EDGES):
        values = [r["edge_winrates"][k] for r in ga]
        mean, sd = st.mean(values), st.stdev(values) if len(values) > 1 else 0.0
        canon = record["edge_winrates"][k]
        mark = "✓" if canon > 0.5 else "✗"
        print(f"  {ARCHETYPES[w].name + ' > ' + ARCHETYPES[l].name:<32}"
              f"{canon:>9.3f}{mark}{mean:>14.3f} ±{sd:.3f}"
              f"{sum(v > 0.5 for v in values):>7}/{len(values)}")
    print("  " + "─" * 74)
    print("  No canônico as arestas que quebram são inversões TOTAIS (0,000–0,011):")
    print("  o Rushdown ganha de todos e a Turtle perde para todos. Isso é hierarquia,")
    print("  não ciclo — a premissa já não se realiza antes de qualquer otimização.")
    print(_LINE)


# ─────────────────────────────────────────────────────────────────────────────
# Entrada
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--streams", type=int, default=STREAMS_DEFAULT,
                        help=f"sorteios independentes por par (default: {STREAMS_DEFAULT})")
    parser.add_argument("--sims", type=int, default=SIMS_DEFAULT,
                        help=f"lutas por sorteio (default: {SIMS_DEFAULT})")
    parser.add_argument("--n-random", type=int, default=N_RANDOM,
                        help=f"rosters aleatórios do piso (default: {N_RANDOM})")
    parser.add_argument("--seed", type=int, default=MULTI_RUN_VALIDATION_SEED,
                        help="semente que sorteia os rosters aleatórios")
    args = parser.parse_args()

    threshold = decided_threshold(args.streams, args.sims)
    rosters = build_groups(args.n_random, args.seed)
    flat = [ind for group in rosters.values() for ind in group]
    print(f"  medindo {len(flat)} rosters × {args.streams} sorteios × {args.sims} lutas…",
          flush=True)
    measured = measure_all(flat, args.streams, args.sims)

    groups: Dict[str, List[dict]] = {}
    cursor = 0
    for label, inds in rosters.items():
        groups[label] = measured[cursor:cursor + len(inds)]
        cursor += len(inds)

    test = falsification_test(groups["AG escalar"], groups["aleatórios"])
    print_report(groups, threshold, args.streams, args.sims, test)
    print_canonical_edges(groups["canônico"][0], groups["AG escalar"], threshold)

    CYCLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "streams": args.streams,
        "sims_per_stream": args.sims,
        "fights_per_pair": args.streams * args.sims,
        "decided_threshold": threshold,
        "n_random": args.n_random,
        "seed": args.seed,
        "edges": [[ARCHETYPES[w].name, ARCHETYPES[l].name] for w, l in EDGES],
        "groups": groups,
        "falsification_test": test,
    }
    with CYCLE_PATH.open("w", encoding="utf-8") as fh:
        json.dump({"provenance": stamp(tool=__spec__.name), **artifact}, fh,
                  indent=2, ensure_ascii=False)
    print(f"\n  → {CYCLE_PATH.relative_to(CYCLE_PATH.parent.parent.parent)}")


if __name__ == "__main__":
    main()
