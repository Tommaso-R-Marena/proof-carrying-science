import math

from pcs_next_v1.adapters.units import CLEARANCE_TO_L_PER_H, clearance_to_L_per_h


def test_conversion_monotone_and_positive():
    for unit, factor in CLEARANCE_TO_L_PER_H.items():
        assert factor > 0
        for v in (0.0, 0.1, 1.0, 10.0, 100.0):
            out = clearance_to_L_per_h(v, unit)
            assert out == v * factor
            assert out >= 0
            assert math.isfinite(out)


def test_mL_min_vs_L_h_disagree_on_same_numeric():
    # Same numeric field under different units must not be identified
    a = clearance_to_L_per_h(1.0, "L/h")
    b = clearance_to_L_per_h(1.0, "mL/min")
    assert a != b
    assert abs(a / b - (1.0 / 0.06)) < 1e-12
