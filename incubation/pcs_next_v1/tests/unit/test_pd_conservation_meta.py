from pcs_next_v1.adapters.conservation import check_trajectory_conservation, check_transfer_preserves_total
from pcs_next_v1.adapters.metamorphic_pk import check_dose_homogeneity, check_prediction_table_dose_scale
from pcs_next_v1.adapters.osp_consistency import check_cl_auc_dose_consistency
from pcs_next_v1.adapters.pd import predict_emax, verify_emax_rows
from pcs_next_v1.adapters.pkpd import predict_concentration


def test_emax_verify():
    pd = {"e0": 0.0, "emax": 100.0, "ec50": 2.0}
    rows = [(c, predict_emax(c, 0.0, 100.0, 2.0)) for c in (0.0, 1.0, 2.0, 10.0)]
    assert verify_emax_rows(pd, rows)["status"] == "COMPUTATIONALLY_TESTED"
    bad = [(c, e * 0.5) for c, e in rows]
    assert verify_emax_rows(pd, bad)["status"] == "REFUTED"


def test_conservation_and_transfer():
    assert check_transfer_preserves_total(5, 2, 3)["status"] == "COMPUTATIONALLY_TESTED"
    vols = {"A": 1.0, "B": 2.0}
    traj = [{"A": 1.0, "B": 0.0}, {"A": 0.5, "B": 0.25}]
    assert check_trajectory_conservation(vols, traj)["status"] == "COMPUTATIONALLY_TESTED"
    leak = [{"A": 1.0, "B": 0.0}, {"A": 1.0, "B": 0.25}]
    assert check_trajectory_conservation(vols, leak)["status"] == "REFUTED"


def test_metamorphic_dose():
    assert check_dose_homogeneity(100, 10, 1, [0, 1, 2], scale=2)["status"] == "COMPUTATIONALLY_TESTED"
    rows = [(t, predict_concentration(100, 10, 1, t)) for t in (0.0, 1.0, 2.0)]
    scaled = [(t, 2 * c) for t, c in rows]
    assert check_prediction_table_dose_scale({}, rows, scaled, scale=2)["status"] == "COMPUTATIONALLY_TESTED"
    broken = [(t, 2 * c if t != 1.0 else c) for t, c in rows]
    assert check_prediction_table_dose_scale({}, rows, broken, scale=2)["status"] == "REFUTED"


def test_osp_cl_auc():
    assert check_cl_auc_dose_consistency({"Dose": "100", "CL Avg": "1", "AUC Avg": "100"})["status"] == "COMPUTATIONALLY_TESTED"
    assert check_cl_auc_dose_consistency({"Dose": "100", "CL Avg": "50", "AUC Avg": "100"})["status"] == "REFUTED"
    assert check_cl_auc_dose_consistency({"CL Avg": "1"}) is None
