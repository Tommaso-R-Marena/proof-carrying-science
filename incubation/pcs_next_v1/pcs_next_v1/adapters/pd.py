"""Direct Emax PD fragment checks."""

from __future__ import annotations

from typing import Any

from ..core.statuses import AssuranceStatus, ClaimClass, status_record

SUPPORTED = {
    "fragment": "pcs-next-pd-direct-emax-v1",
    "model": "E(C) = E0 + Emax * C / (EC50 + C)",
    "limitations": [
        "Direct effect only; no effect compartment / hysteresis.",
        "Does not establish pharmacological truth.",
    ],
}


def predict_emax(c: float, e0: float, emax: float, ec50: float) -> float:
    if c < 0 or ec50 <= 0:
        raise ValueError("domain error")
    return e0 + emax * c / (ec50 + c)


def verify_emax_rows(
    pd: dict[str, Any],
    rows: list[tuple[float, float]],
    *,
    rel_tol: float = 1e-6,
    abs_tol: float = 1e-9,
) -> dict[str, Any]:
    """rows = (concentration, effect)."""
    try:
        e0 = float(pd["e0"]["value"] if isinstance(pd.get("e0"), dict) else pd["e0"])
        emax = float(pd["emax"]["value"] if isinstance(pd.get("emax"), dict) else pd["emax"])
        ec50 = float(pd["ec50"]["value"] if isinstance(pd.get("ec50"), dict) else pd["ec50"])
    except (KeyError, TypeError, ValueError) as exc:
        return status_record(
            AssuranceStatus.UNSUPPORTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"missing PD fields: {exc}",
            limitations=list(SUPPORTED["limitations"]),
        )
    mismatches = []
    for c, e_obs in rows:
        e_hat = predict_emax(c, e0, emax, ec50)
        if abs(e_hat - e_obs) > max(abs_tol, rel_tol * abs(e_hat)):
            mismatches.append({"c": c, "observed": e_obs, "predicted": e_hat})
    if mismatches:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="effect rows deviate from direct Emax model",
            evidence_ids=[f"mismatch@c={m['c']}" for m in mismatches[:5]],
            limitations=list(SUPPORTED["limitations"]),
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="rows match direct Emax within tolerance",
        assumptions=list(SUPPORTED["limitations"]),
    )
