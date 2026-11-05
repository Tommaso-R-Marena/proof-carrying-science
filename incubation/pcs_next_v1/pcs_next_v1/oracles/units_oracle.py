"""Independent clearance-unit conversion oracle (no shared helpers with adapters.units)."""

from __future__ import annotations


def oracle_clearance_to_L_per_h(value: float, unit: str) -> float:
    """Convert clearance to L/h via explicit factors (oracle copy)."""
    factors = {
        "L/h": 1.0,
        "L/min": 60.0,
        "mL/h": 1.0 / 1000.0,
        "mL/min": 60.0 / 1000.0,  # 0.06
    }
    if unit not in factors:
        raise ValueError(f"unsupported unit {unit}")
    return float(value) * factors[unit]
