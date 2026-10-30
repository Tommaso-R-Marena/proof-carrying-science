from pcs_next_v1.demos.puromycin_demo import (
    check_labels_against_registration,
    load,
    register_group_params,
)


def test_registration_matches_pristine():
    rows = load()
    reg = register_group_params(rows)
    st = check_labels_against_registration(rows, reg)
    assert st["status"] == "COMPUTATIONALLY_TESTED"


def test_swapped_labels_refuted():
    rows = load()
    reg = register_group_params(rows)
    swapped = [{**r, "state": "untreated" if r["state"] == "treated" else "treated"} for r in rows]
    st = check_labels_against_registration(swapped, reg)
    assert st["status"] == "REFUTED"
