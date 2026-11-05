"""One-compartment IV bolus PK checks (exact on rationals via floats with tolerance)."""

from __future__ import annotations

import math
from typing import Any

from ..core.statuses import AssuranceStatus, ClaimClass, status_record


SUPPORTED = {
    "fragment": "pcs-next-pkpd-one-compartment-iv-bolus-v1",
    "model": "C(t) = (dose/V) * exp(- (CL/V) * t)",
    "limitations": [
        "Does not establish biological correctness.",
        "Supports only one-compartment IV bolus with constant CL,V.",
    ],
}


def predict_concentration(dose: float, volume: float, clearance: float, t: float) -> float:
    if volume <= 0 or clearance < 0 or dose < 0 or t < 0:
        raise ValueError("domain error")
    k = clearance / volume
    return (dose / volume) * math.exp(-k * t)


def verify_predictions(
    model: dict[str, Any],
    rows: list[tuple[float, float]],
    *,
    rel_tol: float = 1e-6,
    abs_tol: float = 1e-9,
) -> dict[str, Any]:
    for key in ("dose", "volume", "clearance"):
        if key not in model:
            return status_record(
                AssuranceStatus.UNSUPPORTED,
                claim_class=ClaimClass.TECHNICAL_VERIFICATION,
                reason=f"missing model field {key}",
                assumptions=list(SUPPORTED["limitations"]),
            )
    dose, V, CL = float(model["dose"]), float(model["volume"]), float(model["clearance"])
    mismatches = []
    for t, c_obs in rows:
        c_hat = predict_concentration(dose, V, CL, t)
        if abs(c_hat - c_obs) > max(abs_tol, rel_tol * abs(c_hat)):
            mismatches.append({"t": t, "observed": c_obs, "predicted": c_hat})
    if mismatches:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="predictions deviate from one-compartment IV bolus model",
            evidence_ids=[f"mismatch@{m['t']}" for m in mismatches[:5]],
            limitations=list(SUPPORTED["limitations"]),
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="rows match one-compartment IV bolus within tolerance",
        assumptions=["Floating-point tolerance contract", *SUPPORTED["limitations"]],
    )
