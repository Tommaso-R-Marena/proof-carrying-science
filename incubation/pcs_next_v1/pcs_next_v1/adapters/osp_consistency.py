"""Consistency checks on OSP observed-data style tables."""

from __future__ import annotations

from typing import Any

from ..core.statuses import AssuranceStatus, ClaimClass, status_record


def _f(x: Any) -> float | None:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def check_cl_auc_dose_consistency(
    row: dict[str, Any],
    *,
    dose_key: str = "Dose",
    cl_key: str = "CL Avg",
    auc_key: str = "AUC Avg",
    rel_tol: float = 0.5,
) -> dict[str, Any] | None:
    """If Dose, CL, AUC present: CL ≈ Dose/AUC (order-of-magnitude teaching check).

    Returns None if insufficient fields (skip).
    """
    dose = _f(row.get(dose_key))
    cl = _f(row.get(cl_key))
    auc = _f(row.get(auc_key))
    if dose is None or cl is None or auc is None or auc == 0:
        return None
    if dose <= 0 or cl <= 0 or auc <= 0:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="non-positive Dose/CL/AUC where all three present",
            limitations=["Units not normalized across OSP studies; coarse check only."],
        )
    implied = dose / auc
    rel = abs(implied - cl) / max(abs(cl), abs(implied))
    if rel > rel_tol:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"CL vs Dose/AUC inconsistent rel_err={rel:.3f}",
            evidence_ids=[f"cl={cl}", f"dose/auc={implied}"],
            limitations=[
                "Units often differ across OSP rows; use only when units are commensurate.",
                "rel_tol default 0.5 is deliberately coarse.",
            ],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason=f"CL≈Dose/AUC within rel_tol={rel_tol}",
        limitations=["Coarse unit-agnostic teaching check"],
    )


def scan_table_cl_auc(
    rows: list[dict[str, Any]],
    *,
    dose_key: str = "Dose",
    cl_key: str = "CL Avg",
    auc_key: str = "AUC Avg",
    rel_tol: float = 0.5,
) -> dict[str, Any]:
    checked = 0
    refuted = 0
    details = []
    for i, r in enumerate(rows):
        st = check_cl_auc_dose_consistency(r, dose_key=dose_key, cl_key=cl_key, auc_key=auc_key, rel_tol=rel_tol)
        if st is None:
            continue
        checked += 1
        if st["status"] == "REFUTED":
            refuted += 1
            if len(details) < 5:
                details.append({"row": i, "reason": st["reason"]})
    return {
        "checked": checked,
        "refuted": refuted,
        "details": details,
        "status": "REFUTED" if refuted else ("COMPUTATIONALLY_TESTED" if checked else "SKIPPED"),
    }
