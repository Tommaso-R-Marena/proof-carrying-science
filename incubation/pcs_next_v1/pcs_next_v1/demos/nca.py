"""Noncompartmental analysis helpers (independent oracle-friendly)."""

from __future__ import annotations

from typing import Iterable


def trapezoidal_auc(times: list[float], concs: list[float]) -> float:
    if len(times) != len(concs) or len(times) < 2:
        raise ValueError("need paired time/concentration with n>=2")
    pairs = sorted(zip(times, concs), key=lambda t: t[0])
    auc = 0.0
    for (t0, c0), (t1, c1) in zip(pairs, pairs[1:]):
        if t1 < t0:
            raise ValueError("times must be sortable nondecreasing")
        if c0 < 0 or c1 < 0:
            raise ValueError("negative concentration unsupported in this fragment")
        auc += 0.5 * (c0 + c1) * (t1 - t0)
    return auc


def log_linear_terminal_half_life(times: list[float], concs: list[float], *, n_terminal: int = 3) -> float | None:
    """Estimate t1/2 from last n_terminal positive points via log-linear slope."""
    import math

    pairs = [(t, c) for t, c in sorted(zip(times, concs)) if c > 0]
    if len(pairs) < max(2, n_terminal):
        return None
    term = pairs[-n_terminal:]
    # simple least-squares on log C = a + b t
    xs = [t for t, _ in term]
    ys = [math.log(c) for _, c in term]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return None
    slope = num / den
    if slope >= 0:
        return None  # not decaying
    ke = -slope
    return math.log(2) / ke


def cmax_tmax(times: list[float], concs: list[float]) -> tuple[float, float]:
    i = max(range(len(concs)), key=lambda j: concs[j])
    return concs[i], times[i]
