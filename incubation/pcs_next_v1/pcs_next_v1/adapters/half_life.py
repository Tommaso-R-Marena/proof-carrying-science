"""One-compartment half-life consistency: t½ ≈ ln(2) * V / CL."""

from __future__ import annotations

import math
from typing import Any

from ..core.statuses import AssuranceStatus, ClaimClass, status_record

LN2 = math.log(2)


def predicted_half_life(volume: float, clearance: float) -> float:
    if volume <= 0 or clearance <= 0:
        raise ValueError("domain")
    return LN2 * volume / clearance


def check_half_life(
    *,
    volume: float,
    clearance: float,
    t_half: float,
    rel_tol: float = 0.5,
) -> dict[str, Any]:
    if volume <= 0 or clearance <= 0 or t_half <= 0:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="non-positive V/CL/t½",
            limitations=["1-compartment IV assumption only"],
        )
    pred = predicted_half_life(volume, clearance)
    rel = abs(pred - t_half) / t_half
    if rel > rel_tol:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"t½ inconsistent with V/CL rel_err={rel:.3f}",
            evidence_ids=[f"pred={pred}", f"reported={t_half}"],
            limitations=["1-compartment; multi-compartment t½ not comparable"],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason=f"t½≈ln2·V/CL within rel_tol={rel_tol}",
        assumptions=["One-compartment disposition"],
    )
