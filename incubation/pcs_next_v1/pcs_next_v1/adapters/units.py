"""Unit-aware calculation checks (restricted vocabulary)."""

from __future__ import annotations

from typing import Any

from ..core.errors import ErrorCode, PcsNextError
from ..core.statuses import AssuranceStatus, ClaimClass, status_record

# dimension vectors: M L T
DIMS = {
    "kg": (1, 0, 0),
    "g": (1, 0, 0),
    "m": (0, 1, 0),
    "cm": (0, 1, 0),
    "L": (0, 3, 0),
    "mL": (0, 3, 0),
    "s": (0, 0, 1),
    "h": (0, 0, 1),
    "min": (0, 0, 1),
    "1/h": (0, 0, -1),
    "L/h": (0, 3, -1),
    "mL/min": (0, 3, -1),
    "mL/h": (0, 3, -1),
    "L/min": (0, 3, -1),
}

# Exact rational scale factors to litres / hour for clearance-like quantities.
# value_in_L_h = value * factor
CLEARANCE_TO_L_PER_H = {
    "L/h": 1.0,
    "L/min": 60.0,
    "mL/h": 0.001,
    "mL/min": 0.06,  # 1 mL/min = 0.06 L/h
}

VOLUME_TO_L = {
    "L": 1.0,
    "mL": 0.001,
}


def dim_of(unit: str) -> tuple[int, int, int]:
    if unit not in DIMS:
        raise PcsNextError(ErrorCode.UNSUPPORTED_FRAGMENT, f"unknown unit {unit}")
    return DIMS[unit]


def compatible(u1: str, u2: str) -> bool:
    return dim_of(u1) == dim_of(u2)


def check_quantity(value: float, unit: str, *, nonneg: bool = False) -> dict[str, Any]:
    dim_of(unit)  # validate
    if nonneg and value < 0:
        return {"status": "REFUTED", "reason": "negative value for non-negative quantity"}
    return {"status": "COMPUTATIONALLY_TESTED", "value": value, "unit": unit, "dim": list(dim_of(unit))}


def clearance_to_L_per_h(value: float, unit: str) -> float:
    if unit not in CLEARANCE_TO_L_PER_H:
        raise PcsNextError(ErrorCode.UNSUPPORTED_FRAGMENT, f"unsupported clearance unit {unit}")
    return float(value) * CLEARANCE_TO_L_PER_H[unit]


def volume_to_L(value: float, unit: str) -> float:
    if unit not in VOLUME_TO_L:
        raise PcsNextError(ErrorCode.UNSUPPORTED_FRAGMENT, f"unsupported volume unit {unit}")
    return float(value) * VOLUME_TO_L[unit]


def normalize_pk_model(model: dict[str, Any]) -> dict[str, Any]:
    """Return dose/volume/clearance in mg, L, L/h using declared units when present."""
    dose = float(model["dose"] if not isinstance(model.get("dose"), dict) else model["dose"]["value"])
    if isinstance(model.get("volume"), dict):
        V = volume_to_L(model["volume"]["value"], model["volume"].get("unit", "L"))
        V_unit = model["volume"].get("unit", "L")
    else:
        V = float(model["volume"])
        V_unit = model.get("volume_unit", "L")
        if V_unit != "L":
            V = volume_to_L(V, V_unit)
    if isinstance(model.get("clearance"), dict):
        cl_unit = model["clearance"].get("unit", model.get("clearance_unit", "L/h"))
        CL = clearance_to_L_per_h(model["clearance"]["value"], cl_unit)
        raw_cl = float(model["clearance"]["value"])
    else:
        cl_unit = model.get("clearance_unit", "L/h")
        raw_cl = float(model["clearance"])
        CL = clearance_to_L_per_h(raw_cl, cl_unit)
    return {
        "dose": dose,
        "volume": V,
        "clearance": CL,
        "clearance_unit_declared": cl_unit,
        "volume_unit_declared": V_unit if isinstance(model.get("volume"), dict) else model.get("volume_unit", "L"),
        "clearance_raw": raw_cl,
    }


def verify_predictions_unit_aware(
    model: dict[str, Any],
    rows: list[tuple[float, float]],
    *,
    rel_tol: float = 1e-6,
    abs_tol: float = 1e-9,
) -> dict[str, Any]:
    """PK verify after converting clearance/volume to L/h and L.

    Catches label-only unit swaps that leave the numeric field unchanged.
    """
    from .pkpd import predict_concentration

    try:
        norm = normalize_pk_model(model)
    except PcsNextError as exc:
        return status_record(
            AssuranceStatus.UNSUPPORTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=str(exc),
        )
    mismatches = []
    for t, c_obs in rows:
        c_hat = predict_concentration(norm["dose"], norm["volume"], norm["clearance"], t)
        if abs(c_hat - c_obs) > max(abs_tol, rel_tol * abs(c_hat)):
            mismatches.append({"t": t, "observed": c_obs, "predicted_unit_aware": c_hat})
    if mismatches:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="unit-aware predictions deviate (declared units applied to numeric fields)",
            evidence_ids=[f"mismatch@{m['t']}" for m in mismatches[:5]],
            assumptions=[
                f"clearance interpreted as {norm['clearance_unit_declared']} → {norm['clearance']} L/h",
                f"volume interpreted as {norm['volume_unit_declared']} → {norm['volume']} L",
            ],
            limitations=["Restricted to one-compartment IV bolus; dose assumed mg."],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="unit-aware one-compartment IV bolus match",
        assumptions=[
            f"clearance {norm['clearance_raw']} {norm['clearance_unit_declared']} = {norm['clearance']} L/h",
        ],
    )


def challenge_clearance_unit_value_consistency(model: dict[str, Any], rows: list[tuple[float, float]]) -> dict[str, Any]:
    """Compare unit-naive vs unit-aware verification; diverge ⇒ unit/value inconsistency."""
    from .pkpd import verify_predictions

    flat = {
        "dose": float(model["dose"]["value"]) if isinstance(model.get("dose"), dict) else float(model["dose"]),
        "volume": float(model["volume"]["value"]) if isinstance(model.get("volume"), dict) else float(model["volume"]),
        "clearance": float(model["clearance"]["value"]) if isinstance(model.get("clearance"), dict) else float(model["clearance"]),
    }
    naive = verify_predictions(flat, rows)
    aware = verify_predictions_unit_aware(model, rows)
    if naive["status"] == "COMPUTATIONALLY_TESTED" and aware["status"] == "REFUTED":
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="clearance/volume unit label inconsistent with numeric fields under prediction check",
            evidence_ids=["unit_naive_ok", "unit_aware_refuted"],
            limitations=["Does not prove which of label vs value is wrong — only that they disagree."],
        )
    if aware["status"] == "REFUTED":
        return aware
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="unit-naive and unit-aware checks agree",
    )
