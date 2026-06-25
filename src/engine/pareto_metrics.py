"""Métricas quantitativas de qualidade da fronteira de Pareto (Deb 2001; Deb et al. 2002).

Comparar fronteiras "no olho" não escala — a literatura usa indicadores numéricos:

  • **hipervolume** — área dominada pela fronteira em relação a um ponto de
    referência (os piores valores possíveis). Captura convergência *e* espalhamento
    num único número; MAIOR é melhor.
  • **spacing** (Schott) — desvio-padrão da distância de cada ponto ao vizinho mais
    próximo. Mede a uniformidade da distribuição ao longo da fronteira; MENOR é melhor.

Ambos os objetivos `(dominance_penalty, drift_penalty)` são minimizados, então o
ponto de referência fica no canto superior-direito (piores valores) e a fronteira é
uma escada descendente em x.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

Point = Tuple[float, float]


def _staircase(points: Sequence[Point], reference: Point) -> List[Point]:
    """Reduz os pontos à escada não-dominada (x crescente, y estritamente decrescente),
    descartando os que não dominam o ponto de referência."""
    r0, r1 = reference
    inside = [(x, y) for x, y in points if x < r0 and y < r1]
    inside.sort(key=lambda p: (p[0], p[1]))
    stair: List[Point] = []
    best_y = math.inf
    for x, y in inside:
        if y < best_y:
            stair.append((x, y))
            best_y = y
    return stair


def hypervolume_2d(points: Sequence[Point], reference: Point) -> float:
    """Hipervolume 2D (área dominada) para minimização de ambos os objetivos.

    Decompõe a região dominada em faixas verticais: para cada degrau `(x_i, y_i)` da
    escada, a contribuição é `(x_{i+1} − x_i) · (r1 − y_i)`, com `x_{n+1} = r0`."""
    r0, r1 = reference
    stair = _staircase(points, reference)
    if not stair:
        return 0.0
    hv = 0.0
    for i, (x, y) in enumerate(stair):
        x_next = stair[i + 1][0] if i + 1 < len(stair) else r0
        hv += (x_next - x) * (r1 - y)
    return hv


def spacing(points: Sequence[Point]) -> float:
    """Spacing de Schott: desvio-padrão das distâncias (Manhattan) ao vizinho mais
    próximo. 0 = pontos perfeitamente uniformes. Indefinido (0.0) para < 2 pontos."""
    pts = list(points)
    n = len(pts)
    if n < 2:
        return 0.0
    nearest: List[float] = []
    for i, (xi, yi) in enumerate(pts):
        best = math.inf
        for j, (xj, yj) in enumerate(pts):
            if i == j:
                continue
            d = abs(xi - xj) + abs(yi - yj)
            if d < best:
                best = d
        nearest.append(best)
    mean_d = sum(nearest) / n
    var = sum((mean_d - d) ** 2 for d in nearest) / (n - 1)
    return math.sqrt(var)
