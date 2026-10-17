from __future__ import annotations

from pathlib import Path

from independent_eval.reviewer_adoption.workbench.generate_report import (
    generate_report,
    main as gen_main,
)
from independent_eval.reviewer_adoption.workbench.inspect_evidence import inspect_evidence_dir

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "workbench" / "fixtures" / "sample_bundle"


def test_inspect_extracts_claims_assumptions_artifacts_and_limitations():
    inspection = inspect_evidence_dir(FIXTURE)
    d = inspection.to_dict()
    assert d["workbench_issues_accept"] is False
    assert inspection.subject
    assert {c.id for c in inspection.claims} >= {"C_REPLAY", "C_BIOLOGY"}
    assert any(a.id == "A_MODEL" for a in inspection.assumptions)
    assert any(a.sha256 for a in inspection.artifacts)
    assert inspection.limitations_text and "biological" in inspection.limitations_text.lower()
    biology = next(c for c in inspection.claims if c.id == "C_BIOLOGY")
    assert biology.reported_status == "OPEN"
    assert any("did not decide" in n.lower() for n in biology.notes)


def test_generate_report_is_static_accessible_html(tmp_path: Path):
    out = tmp_path / "report.html"
    assert gen_main(["--evidence", str(FIXTURE), "--out", str(out)]) == 0
    generate_report(FIXTURE, tmp_path / "report2.html")
    text = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text
    assert 'lang="en"' in text
    assert "skip-link" in text
    assert "workbench_issues_accept = false" in text
    assert "This workbench inspects existing evidence" in text
    assert out.with_suffix(".inspection.json").is_file()
    assert 'th scope="col"' in text or "Reported status" in text
