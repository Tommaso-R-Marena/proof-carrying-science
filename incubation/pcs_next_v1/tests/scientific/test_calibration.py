from pcs_next_v1.falsification.calibration import expected_calibration_error, bootstrap_mean_ci

def test_perfect_calibration():
    # Within each bin, mean confidence equals empirical accuracy.
    probs = [0.0] * 10 + [1.0] * 10
    outcomes = [0] * 10 + [1] * 10
    ece = expected_calibration_error(probs, outcomes, bins=2)["ece"]
    assert ece < 1e-9

def test_bootstrap_seed_stable():
    a = bootstrap_mean_ci([1.0, 2.0, 3.0], seed=1)
    b = bootstrap_mean_ci([1.0, 2.0, 3.0], seed=1)
    assert a == b
