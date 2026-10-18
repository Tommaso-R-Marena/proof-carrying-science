from pcs_next_v1.adapters.tabular_integrity import (
    check_nonnegative_concentrations,
    check_registered_group_params,
    check_subject_time_integrity,
)


def test_zero_and_negative_conc():
    assert check_nonnegative_concentrations([1.0, 0.0], allow_zero=False)["status"] == "REFUTED"
    assert check_nonnegative_concentrations([1.0, -0.1], allow_zero=True)["status"] == "REFUTED"
    assert check_nonnegative_concentrations([1.0, 0.0], allow_zero=True)["status"] == "COMPUTATIONALLY_TESTED"


def test_sub_epsilon_jitter():
    rows = [
        {"id": 1, "time": 0.0},
        {"id": 1, "time": 1e-12},
        {"id": 1, "time": 1.0},
    ]
    st = check_subject_time_integrity(rows, min_delta=1e-9)
    assert st["status"] == "REFUTED"
    assert "sub_epsilon_jitter" in st["reason"] or any("jitter" in e for e in st["evidence_ids"])


def test_group_label_swap():
    registered = {"treated": {"vmax": 200.0, "km": 0.05}, "untreated": {"vmax": 160.0, "km": 0.06}}
    # observed fits look like the other group
    observed = {"treated": {"vmax": 160.0, "km": 0.06}, "untreated": {"vmax": 200.0, "km": 0.05}}
    st = check_registered_group_params(observed, registered, rel_tol=0.1)
    assert st["status"] == "REFUTED"
