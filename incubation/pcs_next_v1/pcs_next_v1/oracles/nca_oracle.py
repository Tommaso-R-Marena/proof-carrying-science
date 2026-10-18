"""Independent NCA oracle (hand-derived formulas; no imports from demos.nca)."""

from __future__ import annotations


def oracle_trapezoidal_auc(times: list[float], concs: list[float]) -> float:
    if len(times) != len(concs) or len(times) < 2:
        raise ValueError("bad input")
    order = sorted(range(len(times)), key=lambda i: times[i])
    auc = 0.0
    for a, b in zip(order, order[1:]):
        dt = times[b] - times[a]
        if dt < 0:
            raise ValueError("time order")
        auc += (concs[a] + concs[b]) * dt * 0.5
    return auc


def oracle_cmax_tmax(times: list[float], concs: list[float]) -> tuple[float, float]:
    i = max(range(len(concs)), key=lambda j: (concs[j], -times[j]))
    return concs[i], times[i]
