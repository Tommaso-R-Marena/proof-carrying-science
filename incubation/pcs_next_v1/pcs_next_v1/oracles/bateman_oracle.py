"""Independent Bateman / MM oracles with exact small-domain checks."""

from __future__ import annotations

import math


def oracle_bateman(t: float, dose: float, v: float, ka: float, ke: float, f: float = 1.0) -> float:
    if t < 0:
        raise ValueError("t")
    if abs(ka - ke) < 1e-15:
        return (f * dose * ka / v) * t * math.exp(-ke * t)
    return (f * dose * ka / (v * (ka - ke))) * (math.exp(-ke * t) - math.exp(-ka * t))


def oracle_michaelis_menten(conc: float, vmax: float, km: float) -> float:
    if conc < 0 or vmax < 0 or km <= 0:
        raise ValueError("domain")
    return vmax * conc / (km + conc)


def mm_sse(vmax: float, km: float, concs: list[float], rates: list[float]) -> float:
    return sum((oracle_michaelis_menten(c, vmax, km) - r) ** 2 for c, r in zip(concs, rates))
