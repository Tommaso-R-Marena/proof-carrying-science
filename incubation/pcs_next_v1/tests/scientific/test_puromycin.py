from pcs_next_v1.demos.puromycin_demo import load, fit_mm, falsify_linear, run_demo

def test_puromycin_load_and_fit():
    rows = load()
    assert len(rows) >= 10
    treated = [r for r in rows if r["state"] == "treated"]
    fit = fit_mm([r["conc"] for r in treated], [r["rate"] for r in treated])
    assert fit["vmax"] > 0 and fit["km"] > 0
    lin = falsify_linear([r["conc"] for r in treated], [r["rate"] for r in treated])
    assert lin["status"] in {"REFUTED", "COMPUTATIONALLY_TESTED"}

def test_puromycin_demo(tmp_path):
    r = run_demo(tmp_path)
    assert r["external_lab_validation"]["status"] == "OPEN"
    assert r["groups_pass"] >= 1
