"""Numerical optimization distinction helpers."""

from __future__ import annotations

from typing import Any, Callable


def classify_solution(
    x: list[float],
    *,
    feasible: bool,
    grad_norm: float | None,
    certified_bound: float | None,
    global_method: bool,
) -> dict[str, Any]:
    labels = []
    if feasible:
        labels.append("FEASIBLE")
    else:
        labels.append("INFEASIBLE")
    if grad_norm is not None and grad_norm <= 1e-8 and feasible:
        labels.append("FIRST_ORDER_STATIONARY")
    if certified_bound is not None:
        labels.append("CERTIFIED_BOUND")
    if global_method and feasible:
        labels.append("CLAIMED_GLOBAL")
    else:
        labels.append("LOCAL_OR_UNSPECIFIED")
    return {
        "x": x,
        "labels": labels,
        "note": "Local stationarity is not global optimality unless explicitly certified.",
    }


def grid_minimize_1d(fn: Callable[[float], float], lo: float, hi: float, n: int = 101) -> dict[str, Any]:
    if n < 2 or hi <= lo:
        return {"status": "UNSUPPORTED"}
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    vals = [(x, fn(x)) for x in xs]
    best = min(vals, key=lambda t: t[1])
    return {
        "status": "COMPUTATIONALLY_TESTED",
        "x": best[0],
        "f": best[1],
        "labels": ["FEASIBLE", "GRID_APPROXIMATE_GLOBAL_ON_INTERVAL"],
        "assumptions": ["Continuous fn; grid resolution may miss narrower basins"],
    }
