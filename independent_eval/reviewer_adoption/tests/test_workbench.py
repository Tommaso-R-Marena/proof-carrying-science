"""Task 15 — offline workbench tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from independent_eval.reviewer_adoption.workbench.generate_report import main as gen_main
from independent_eval.reviewer_adoption.workbench.inspect_evidence import inspect_evidence_dir

FIXTURE = ROOT / "workbench" / "fixtures" / "sample_bundle"


def test_inspect_does_not_issue_accept():
    insp = inspect_evidence_dir(FIXTURE)
    d = insp.to_dict()
    assert d["workbench_issues_accept"] is False
    assert "does not replace pcs" in d["disclaimer"].lower() or "does not issue" in d["disclaimer"].lower()
    assert d["claims"]
    assert d["claims"][0]["reported_status"]
    assert any("did not decide" in n.lower() for n in d["claims"][0]["notes"])


def test_generate_html(tmp_path):
    out = tmp_path / "report.html"
    rc = gen_main(["--evidence", str(FIXTURE), "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "workbench_issues_accept = false" in text
    assert out.with_suffix(".inspection.json").is_file()
