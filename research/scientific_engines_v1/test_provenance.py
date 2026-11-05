from .source_gate import check


def test_original_archives_exact_vendor_deltas_and_no_lean_escape_hatches():
    report = check()
    assert report["passed"] and report["active_lean_escape_hatches"] == 0
    assert set(report["archives"]) == {"prism", "aion"}
