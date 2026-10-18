from pcs_next_v1.campaigns.real_world_mutation import run_campaign

# Gross mutations that must always be caught if the suite is healthy.
MUST_CATCH = {
    "scale_one_concentration_1.5x",
    "break_cleavage_stoichiometry",
    "inject_exec",
    "leak_S001_into_test",
    "policy_version_swap",
    "post_freeze_prediction_append",
    "duplicate_json_keys",
    "double_CellA_last_step",
    "halve_effect_keep_conc",
    "swap_csv_value_order",
    "clearance_unit_label_only_mL_min",
    "swap_treated_untreated_labels",
    "zero_one_concentration",
    "1e-12_time_jitter",
}


def test_campaign_runs(tmp_path):
    report = run_campaign(tmp_path / "camp")
    assert report["n_mutations"] >= 25
    assert not report["errors"], report["errors"]
    assert report["n_expected_detections"] >= 20
    assert report["catch_rate"] is not None
    # Boundary controls must not false-alarm
    false_alarms = [f for f in report["findings"] if f.get("outcome") == "FALSE_ALARM"]
    assert false_alarms == [], false_alarms
    by_mut = {f["mutation"]: f for f in report["findings"] if f["phase"] == "mutation"}
    for name in MUST_CATCH:
        assert name in by_mut, name
        assert by_mut[name]["outcome"] == "CAUGHT", (name, by_mut[name])
