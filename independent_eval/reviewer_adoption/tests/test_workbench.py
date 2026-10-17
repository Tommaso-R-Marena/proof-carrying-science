from __future__ import annotations

import json
from pathlib import Path

from independent_eval.reviewer_adoption.workbench.generate_report import (
    generate_report,
    main as gen_main,
)
from independent_eval.reviewer_adoption.workbench.inspect_evidence import (
    INSPECTION_CLASSES,
    classify_claim_strength,
    inspect_evidence_dir,
)

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


def test_claim_strength_lattice_classification():
    assert classify_claim_strength(
        reported_status="COMPUTATIONALLY_SUPPORTED", kind="computational"
    ) == "computationally_supported"
    assert classify_claim_strength(
        reported_status="OPEN", kind="scientific"
    ) == "scientific_adequacy_open"
    assert classify_claim_strength(
        reported_status="COMPUTATIONALLY_SUPPORTED", kind="scientific"
    ) == "empirically_unsupported"
    assert classify_claim_strength(
        reported_status="REJECTED", kind="computational"
    ) == "rejected_or_failed"
    assert classify_claim_strength(
        reported_status="HASH_MISMATCH", kind="computational"
    ) == "rejected_or_failed"
    assert classify_claim_strength(
        reported_status="SIGNATURE_OK", kind="integrity"
    ) == "cryptographic_validity"
    assert classify_claim_strength(
        reported_status="CRYPTOGRAPHIC_VALID", kind="cryptographic"
    ) == "cryptographic_validity"
    assert classify_claim_strength(
        reported_status="EMPIRICALLY_UNSUPPORTED", kind="scientific"
    ) == "empirically_unsupported"
    assert classify_claim_strength(
        reported_status="UNREPORTED", kind="computational"
    ) == "unknown_or_ambiguous"
    assert classify_claim_strength(reported_status=None, kind=None) == "unknown_or_ambiguous"


def test_fixture_claims_have_inspection_class_and_summary():
    inspection = inspect_evidence_dir(FIXTURE)
    d = inspection.to_dict()
    assert "claim_strength_summary" in d
    summary = d["claim_strength_summary"]
    assert set(summary) == set(INSPECTION_CLASSES)
    replay = next(c for c in inspection.claims if c.id == "C_REPLAY")
    biology = next(c for c in inspection.claims if c.id == "C_BIOLOGY")
    assert replay.inspection_class == "computationally_supported"
    assert biology.inspection_class == "scientific_adequacy_open"
    assert summary["computationally_supported"] >= 1
    assert summary["scientific_adequacy_open"] >= 1
    assert d["workbench_issues_accept"] is False
    assert "not PCS authority" in (d.get("inspection_class_note") or "")


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
    assert "Inspection class" in text
    assert "computationally_supported" in text
    assert "scientific_adequacy_open" in text
    assert 'class="strength-dl"' in text
    assert "<caption>" in text
    assert "focus-visible" in text
    assert "skip-link" in text


def test_generate_report_format_json_and_both(tmp_path: Path):
    html_out = tmp_path / "both.html"
    written_both = generate_report(FIXTURE, html_out, fmt="both")
    assert "html" in written_both and "json" in written_both
    assert written_both["html"].is_file()
    assert written_both["json"].is_file()
    payload = json.loads(written_both["json"].read_text(encoding="utf-8"))
    assert payload["workbench_issues_accept"] is False
    assert "claim_strength_summary" in payload
    assert any(c.get("inspection_class") for c in payload["claims"])

    json_only = tmp_path / "only.json"
    written_json = generate_report(FIXTURE, json_only, fmt="json")
    assert "json" in written_json and "html" not in written_json
    assert written_json["json"].is_file()

    html_only = tmp_path / "only.html"
    written_html = generate_report(FIXTURE, html_only, fmt="html")
    assert "html" in written_html and "json" not in written_html
    assert not html_only.with_suffix(".inspection.json").exists()

    assert gen_main(["--evidence", str(FIXTURE), "--out", str(tmp_path / "cli.json"), "--format", "json"]) == 0
    assert (tmp_path / "cli.json").is_file()
