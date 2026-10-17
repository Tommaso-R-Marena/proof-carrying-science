"""Task 8 — formal/computational correctness vs scientific inadequacy."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.paths import INADEQUACY  # noqa: E402
from python_harness.pcs_cli import certify, load_json, verify_certificate  # noqa: E402


def test_inadequacy_index_lists_four_examples():
    index = load_json(INADEQUACY / "INDEX.json")
    assert len(index["examples"]) >= 4
    ids = {e["id"] for e in index["examples"]}
    assert "04_disjoint_but_biased_cohorts" in ids


def test_correct_but_inadequate_pkpd_still_verifies(tmp_path):
    ex = INADEQUACY / "examples" / "01_correct_but_inadequate_pkpd"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    cert = load_json(out / "certificate.json")
    for claim in cert["claims"]:
        assert claim["assessment"]["status"] == "COMPUTATIONALLY_SUPPORTED"
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()
    # Scientific adequacy is not a certificate field — document via README.
    readme = (ex / "README.md").read_text(encoding="utf-8").lower()
    assert "adequacy" in readme
    assert "empirical" in readme or "clinical" in readme


def test_balanced_but_biologically_inadequate_verifies(tmp_path):
    ex = INADEQUACY / "examples" / "02_balanced_but_biologically_inadequate"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    cert = load_json(out / "certificate.json")
    assert cert["claims"][0]["assessment"]["status"] == "COMPUTATIONALLY_SUPPORTED"
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()


def test_units_ok_quantity_inadequate_verifies(tmp_path):
    ex = INADEQUACY / "examples" / "03_units_ok_quantity_inadequate"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()


def test_aristotle_candidates_are_proposals_only():
    from python_harness.aristotle_candidates import build_candidates
    from python_harness.canonical_seal import verify_artifact_integrity

    catalog = build_candidates()
    assert catalog["candidate_count"] >= 4
    assert catalog["disclaimer"].startswith("PROPOSALS ONLY")
    assert catalog["issues_accept"] is False
    assert verify_artifact_integrity(catalog) is True
    for c in catalog["candidates"]:
        assert c["status"] == "proposal_candidate"
        assert c["not_claimed_done"] is True
        assert c["empirical_adequacy_established"] is False
        assert c["computational_support_expected"] is True
        prop = c["proposed_obligation"]
        assert prop["discharged"] is False
        assert prop["inspection_class"] == "scientific_adequacy_open"
        assert prop["proposed_obligation_families"]
        assert 1 <= prop["priority"] <= 5


def test_disjoint_but_biased_cohorts_verifies_without_adequacy(tmp_path):
    ex = INADEQUACY / "examples" / "04_disjoint_but_biased_cohorts"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    cert = load_json(out / "certificate.json")
    for claim in cert["claims"]:
        assert claim["assessment"]["status"] == "COMPUTATIONALLY_SUPPORTED"
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()
    readme = (ex / "README.md").read_text(encoding="utf-8").lower()
    assert "adequacy" in readme
    assert "represent" in readme or "sampling" in readme or "biased" in readme
    # Synthetic scaffolding only — no invented human-study results.
    assert "synthetic" in readme
    assert "no human participants" in readme or "no participants" in readme
