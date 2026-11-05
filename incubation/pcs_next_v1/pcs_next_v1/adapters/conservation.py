"""Finite-volume / multi-compartment amount conservation checks."""

from __future__ import annotations

from typing import Any, Callable

from ..core.statuses import AssuranceStatus, ClaimClass, status_record


def amount(volumes: dict[str, float], concentrations: dict[str, float]) -> float:
    return sum(volumes[k] * concentrations[k] for k in volumes)


def check_trajectory_conservation(
    volumes: dict[str, float],
    trajectory: list[dict[str, float]],
    *,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-12,
) -> dict[str, Any]:
    """trajectory rows map cell_id -> concentration (same keys as volumes)."""
    if not trajectory:
        return status_record(
            AssuranceStatus.UNSUPPORTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="empty trajectory",
        )
    amounts = [amount(volumes, row) for row in trajectory]
    a0 = amounts[0]
    spread = max(amounts) - min(amounts)
    tol = max(abs_tol, rel_tol * max(1.0, abs(a0)))
    if spread > tol:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="amount not conserved along trajectory",
            evidence_ids=[f"spread={spread}", f"a0={a0}"],
            limitations=["Closed-system assumption; no sources/sinks."],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="amount conserved within tolerance",
        assumptions=["Closed system", f"tol={tol}"],
    )


def check_transfer_preserves_total(
    a: float,
    b: float,
    k: float,
    transfer_fn: Callable[[float, float, float], tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Runtime check mirroring Lean PcsNext.Conservation.transfer."""

    def _default(aa: float, bb: float, kk: float) -> tuple[float, float]:
        if kk <= aa:
            return aa - kk, bb + kk
        return aa, bb

    fn = transfer_fn or _default
    a2, b2 = fn(a, b, k)
    if abs((a2 + b2) - (a + b)) > 1e-12 * max(1.0, abs(a + b)):
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="transfer changed total amount",
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="transfer preserved total",
    )
