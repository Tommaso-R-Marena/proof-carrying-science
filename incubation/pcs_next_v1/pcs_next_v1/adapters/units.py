"""Unit-aware calculation checks (restricted vocabulary)."""

from __future__ import annotations

from typing import Any

from ..core.errors import ErrorCode, PcsNextError

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
