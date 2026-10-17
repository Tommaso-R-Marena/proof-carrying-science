"""First-order absorption one-compartment (Bateman) model for oral PK demos.

C(t) = (F*Dose*ka)/(V*(ka-ke)) * (exp(-ke*t) - exp(-ka*t)) for ka != ke, t>=0.
"""

from __future__ import annotations

import math
from typing import Any


def bateman(t: float, *, dose: float, v: float, ka: float, ke: float, f: float = 1.0) -> float:
    if t < 0 or dose < 0 or v <= 0 or ka <= 0 or ke <= 0 or f < 0:
        raise ValueError("domain error")
    if abs(ka - ke) < 1e-12:
        # limiting form: (F*Dose*ka/V) * t * exp(-ke*t)
        return (f * dose * ka / v) * t * math.exp(-ke * t)
    return (f * dose * ka / (v * (ka - ke))) * (math.exp(-ke * t) - math.exp(-ka * t))


def sse(params: tuple[float, float, float], times: list[float], concs: list[float], dose: float) -> float:
    ka, ke, v = params
    s = 0.0
    for t, c in zip(times, concs):
        pred = bateman(t, dose=dose, v=v, ka=ka, ke=ke)
        s += (pred - c) ** 2
    return s


def fit_bateman_grid(
    times: list[float],
    concs: list[float],
    dose: float,
    *,
    ka_grid: list[float] | None = None,
    ke_grid: list[float] | None = None,
    v_grid: list[float] | None = None,
) -> dict[str, Any]:
    """Coarse deterministic grid search — reproducible, no ML."""
    ka_grid = ka_grid or [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    ke_grid = ke_grid or [0.05, 0.08, 0.1, 0.15, 0.2, 0.3]
    # V in L/kg-ish relative to dose units used in Theoph (mg/kg → conc mg/L ⇒ V in L/kg)
    v_grid = v_grid or [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2]
    best = None
    best_sse = float("inf")
    proposals = 0
    for ka in ka_grid:
        for ke in ke_grid:
            if abs(ka - ke) < 1e-9:
                continue
            for v in v_grid:
                proposals += 1
                err = sse((ka, ke, v), times, concs, dose)
                if err < best_sse:
                    best_sse = err
                    best = {"ka": ka, "ke": ke, "V": v, "sse": err}
    assert best is not None
    preds = [bateman(t, dose=dose, v=best["V"], ka=best["ka"], ke=best["ke"]) for t in times]
    rmse = math.sqrt(best_sse / max(1, len(times)))
    return {**best, "rmse": rmse, "predictions": preds, "proposals": proposals}
