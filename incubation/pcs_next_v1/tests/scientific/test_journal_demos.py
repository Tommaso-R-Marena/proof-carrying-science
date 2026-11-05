from pathlib import Path
from pcs_next_v1.demos.provenance import verify_manifest
from pcs_next_v1.demos.theophylline_demo import load_theoph, by_subject, falsify_iv_bolus_on_oral, fit_oral_subject, run_demo as run_theoph
from pcs_next_v1.demos.indomethacin_demo import run_demo as run_indo
from pcs_next_v1.demos.edrug3d_demo import run_demo as run_edrug
from pcs_next_v1.demos.osp_ddi_demo import run_demo as run_osp
from pcs_next_v1.demos.nca import trapezoidal_auc
from pcs_next_v1.core.statuses import AssuranceStatus

def test_manifest():
    assert verify_manifest()["ok"] is True

def test_theoph_shape():
    rows = load_theoph()
    assert len(rows) == 132
    assert len(by_subject(rows)) == 12

def test_theoph_iv_misspecification_refuted():
    rows = load_theoph()
    subj = by_subject(rows)[1]
    out = falsify_iv_bolus_on_oral(subj)
    assert out["structural"]["status"] == AssuranceStatus.REFUTED.value

def test_theoph_oral_fit_runs():
    rows = load_theoph()
    out = fit_oral_subject(by_subject(rows)[1])
    assert out["fit"]["rmse"] >= 0
    assert out["status"]["status"] in {
        AssuranceStatus.COMPUTATIONALLY_TESTED.value,
        AssuranceStatus.CONDITIONAL.value,
    }

def test_nca_oracle_agree():
    # independent hand calculation
    times = [0.0, 1.0, 2.0]
    concs = [0.0, 2.0, 0.0]
    assert abs(trapezoidal_auc(times, concs) - 2.0) < 1e-12

def test_run_all_demos(tmp_path):
    t = run_theoph(tmp_path / "t")
    assert t["n_subjects"] == 12
    assert t["external_lab_validation"]["status"] == "OPEN"
    assert t["leakage_injected_failure"]["status"] == "REFUTED"
    assert t["subjects_oral_pass"] >= 8
    i = run_indo(tmp_path / "i")
    assert i["n_subjects"] >= 1
    assert i["monoexponential_refuted"] >= 1
    assert i["biexponential_pass"] >= 1
    e = run_edrug(tmp_path / "e")
    assert e["n_with_vd_cl_thalf"] > 100
    o = run_osp(tmp_path / "o")
    assert o["n_rows"] > 100
    assert o["n_missing_reference"] == 0
