from pcs_next_v1.adapters.units import (
    challenge_clearance_unit_value_consistency,
    clearance_to_L_per_h,
    verify_predictions_unit_aware,
)
from pcs_next_v1.adapters.pkpd import predict_concentration


def test_mL_per_min_conversion():
    assert abs(clearance_to_L_per_h(1.0, "mL/min") - 0.06) < 1e-15
    assert clearance_to_L_per_h(1.0, "L/h") == 1.0


def test_unit_label_only_swap_refuted():
    dose, V, CL = 100.0, 10.0, 1.0
    rows = [(t, predict_concentration(dose, V, CL, t)) for t in (0.0, 0.5, 1.0, 2.0, 4.0)]
    model = {
        "dose": {"value": dose, "unit": "mg"},
        "volume": {"value": V, "unit": "L"},
        "clearance": {"value": CL, "unit": "mL/min"},  # wrong label
    }
    st = challenge_clearance_unit_value_consistency(model, rows)
    assert st["status"] == "REFUTED"


def test_correct_units_pass():
    dose, V, CL = 100.0, 10.0, 1.0
    rows = [(t, predict_concentration(dose, V, CL, t)) for t in (0.0, 1.0, 2.0)]
    model = {
        "dose": {"value": dose, "unit": "mg"},
        "volume": {"value": V, "unit": "L"},
        "clearance": {"value": CL, "unit": "L/h"},
    }
    st = verify_predictions_unit_aware(model, rows)
    assert st["status"] == "COMPUTATIONALLY_TESTED"
