from pcs_epistemic.differential import run_differential


def test_python_agrees_with_all_lean_control_vectors():
    report = run_differential()
    assert report["failed"] == 0, report["failures"]
    assert report["passed"] == report["total"]
    assert report["total"] >= 16
