"""Metamorphic relations for one-compartment IV bolus PK."""

from __future__ import annotations

from typing import Any

from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from .pkpd import predict_concentration


def check_dose_homogeneity(
    dose: float,
    volume: float,
    clearance: float,
    times: list[float],
    *,
    scale: float = 2.0,
    rel_tol: float = 1e-9,
) -> dict[str, Any]:
    """C(t; α·dose) = α · C(t; dose) for α > 0."""
    if scale <= 0:
        return status_record(
            AssuranceStatus.UNSUPPORTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="scale must be positive",
        )
    bad = []
    for t in times:
        c1 = predict_concentration(dose, volume, clearance, t)
        c2 = predict_concentration(dose * scale, volume, clearance, t)
        if abs(c2 - scale * c1) > rel_tol * max(1.0, abs(scale * c1)):
            bad.append({"t": t, "c1": c1, "c2": c2})
    if bad:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="dose homogeneity failed",
            evidence_ids=[f"t={b['t']}" for b in bad[:5]],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason=f"dose homogeneity holds for scale={scale}",
        assumptions=["Linear one-compartment IV bolus"],
    )


def check_prediction_table_dose_scale(
    model: dict[str, float],
    rows: list[tuple[float, float]],
    scaled_rows: list[tuple[float, float]],
    *,
    scale: float,
    rel_tol: float = 1e-6,
) -> dict[str, Any]:
    """If predictions claim dose→α·dose, concentrations must scale by α (same times)."""
    by_t = {t: c for t, c in rows}
    mismatches = []
    for t, c_s in scaled_rows:
        if t not in by_t:
            mismatches.append({"t": t, "kind": "missing_base_time"})
            continue
        expect = scale * by_t[t]
        if abs(c_s - expect) > max(1e-12, rel_tol * abs(expect)):
            mismatches.append({"t": t, "scaled": c_s, "expected": expect})
    if mismatches:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="scaled prediction table violates dose homogeneity",
            evidence_ids=[f"t={m.get('t')}" for m in mismatches[:5]],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="scaled table respects dose homogeneity",
    )
