from pcs_next_v1.adapters.pkpd import predict_concentration, verify_predictions

def test_match_and_reject():
    model = {"dose": 100.0, "volume": 10.0, "clearance": 1.0}
    rows = [(t, predict_concentration(100, 10, 1, t)) for t in [0.0, 1.0, 2.0]]
    assert verify_predictions(model, rows)["status"] == "COMPUTATIONALLY_TESTED"
    bad = [(t, c + 1) for t, c in rows]
    assert verify_predictions(model, bad)["status"] == "REFUTED"
