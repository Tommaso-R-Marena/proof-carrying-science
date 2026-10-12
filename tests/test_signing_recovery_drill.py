from scripts.exercise_signing_recovery import exercise


def test_actual_isolated_key_recovery_drill():
    report = exercise()
    assert report["passed"]
    assert report["control_count"] == 17
    assert all(report["controls"].values())
    assert report["production_mutations"] == report["financial_spend"] == 0
    assert report["synthetic_test_keys_only"] and not report["pcs_authority"]
