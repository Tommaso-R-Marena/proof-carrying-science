"""Documented runtime correspondence checks (Python vs oracle; Lean scope notes)."""

from __future__ import annotations

from typing import Any

from ..demos.nca import trapezoidal_auc
from ..oracles.nca_oracle import oracle_trapezoidal_auc
from ..demos.oral_pk import bateman
from ..oracles.bateman_oracle import oracle_bateman


def nca_correspondence(times: list[float], concs: list[float]) -> dict[str, Any]:
    a = trapezoidal_auc(times, concs)
    b = oracle_trapezoidal_auc(times, concs)
    return {
        "impl": a,
        "oracle": b,
        "match": abs(a - b) < 1e-12,
        "lean_scope_note": (
            "Lean PcsNext.NCA proves Nat trapezoid nonnegativity; it does not prove IEEE float AUC."
        ),
    }


def bateman_correspondence(samples: list[float]) -> dict[str, Any]:
    rows = []
    ok = True
    for t in samples:
        a = bateman(t, dose=4.0, v=0.5, ka=1.5, ke=0.1)
        b = oracle_bateman(t, 4.0, 0.5, 1.5, 0.1)
        match = abs(a - b) < 1e-12
        ok = ok and match
        rows.append({"t": t, "impl": a, "oracle": b, "match": match})
    return {
        "ok": ok,
        "rows": rows,
        "lean_scope_note": (
            "Lean PcsNext.Bateman proves Nat proxy monotonicity/nonnegativity only — not float Bateman."
        ),
    }
