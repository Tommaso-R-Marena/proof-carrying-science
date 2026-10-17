"""Tests for the independent scientific-assurance pilot workflow."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from pcs.independent_pilot_v1 import (
    IndependentPilotError,
    PILOT_ID,
    TRUST_BOUNDARY,
    run_cleanroom_independent_pilot_v1,
    run_independent_pilot_v1,
    stage_external_lab_project,
)
from pcs.intake import validate_lock
from pcs.lean_authority_v06 import V06LeanAuthorityError, resolve_lean_authority_v06


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"


def _authority_available() -> bool:
    if AUTHORITY.is_file() and os.access(AUTHORITY, os.X_OK):
        return True
    try:
        resolve_lean_authority_v06(None)
        return True
    except V06LeanAuthorityError:
        return False


pytestmark = pytest.mark.skipif(
    not _authority_available(),
    reason="pcs-lean-authority unavailable; build with: cd formal && lake build pcs-lean-authority",
)


def test_stage_external_lab_is_synthetic_and_inventoried(tmp_path):
    staged = stage_external_lab_project(tmp_path / "lab")
    assert staged["pilot_id"] == PILOT_ID
    lab = Path(staged["project_root"])
    assert (lab / "pk_model.json").is_file()
    assert (lab / "predictions.csv").is_file()
    assert (lab / "pilot_intake.json").is_file()
    inventory = json.loads((lab / "lab-inventory.json").read_text(encoding="utf-8"))
    assert inventory["data_classification"] == "synthetic"
    assert "pk_model.json" in inventory["files"]


def test_trust_boundary_separates_proved_tested_and_unproved():
    assert TRUST_BOUNDARY["format"] == "pcs-trust-boundary-assessment-v1"
    assert TRUST_BOUNDARY["kernel_proved_guarantees"]
    assert TRUST_BOUNDARY["independently_tested_properties"]
    assert TRUST_BOUNDARY["unproved_environmental_assumptions"]
    assert "OPEN" in TRUST_BOUNDARY["scientific_vs_computational"]["empirical_scientific_validity"]


def test_independent_pilot_end_to_end(tmp_path):
    evidence = run_independent_pilot_v1(
        tmp_path / "pilot",
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
        apply_closeout=True,
    )
    assert evidence["format"] == "pcs-independent-pilot-evidence-ledger-v1"
    assert evidence["stages"]["intake_frozen"] is True
    assert evidence["stages"]["discovery_confirmed"] is True
    assert evidence["stages"]["attested"] is True
    assert evidence["stages"]["second_environment_verified"] is True
    assert evidence["stages"]["authoritative"] is True
    assert evidence["stages"]["adversarial_pass"] is True
    assert evidence["stages"]["closeout_applied"] is True
    assert evidence["bundle_sha256"]
    assert evidence["signer_fingerprint"]
    assert len(evidence["signer_fingerprint"]) == 64

    out = tmp_path / "pilot"
    assert (out / "EVIDENCE_LEDGER.json").is_file()
    assert (out / "INDEPENDENT_PILOT_REPORT.md").is_file()
    assert (out / "reviewer" / "verification-receipt.json").is_file()
    assert (out / "reviewer" / "REVIEWER_REPORT.md").is_file()
    assert (out / "archive" / "TRUST_BOUNDARY_ASSESSMENT.json").is_file()
    assert (out / "adversarial" / "ADVERSARIAL_RESULTS.json").is_file()
    # Private demo key must not be delivered to the reviewer archive.
    delivery = out / "archive" / "pilot-delivery"
    assert (delivery / "study.pcs.zip").is_file()
    assert (delivery / "trusted-public.pem").is_file()
    assert not (delivery / "demo-producer-private.pem").exists()
    assert not list(delivery.glob("**/*private*"))

    receipt = json.loads((out / "reviewer" / "verification-receipt.json").read_text())
    assert receipt["valid"] is True
    assert receipt["authoritative"] is True
    assert receipt["bundle_sha256"] == evidence["bundle_sha256"]

    lock = validate_lock(
        json.loads((out / "producer" / "intake" / "pilot-intake.lock.json").read_text())
    )
    assert lock["intake"]["pilot_id"] == PILOT_ID


def test_independent_pilot_refuses_nonempty_output_without_overwrite(tmp_path):
    target = tmp_path / "exists"
    target.mkdir()
    (target / "keep.txt").write_text("x", encoding="utf-8")
    with pytest.raises(IndependentPilotError, match="already exists"):
        run_independent_pilot_v1(target, lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None)


def test_adversarial_suite_fail_closed_on_delivered_bundle(tmp_path):
    evidence = run_independent_pilot_v1(
        tmp_path / "pilot",
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
    )
    adv = json.loads(
        (tmp_path / "pilot" / "adversarial" / "ADVERSARIAL_RESULTS.json").read_text()
    )
    assert adv["pass"] is True
    names = {case["attack"] for case in adv["cases"]}
    for required in (
        "changed_scientific_artifact",
        "false_certificate_bytes",
        "signature_substitution_wrong_key",
        "path_traversal_member",
        "absolute_archive_member",
        "stale_receipt_bundle_binding",
        "ambiguous_post_hoc_claim",
        "unexpected_source_modification_detected",
    ):
        assert required in names
        case = next(c for c in adv["cases"] if c["attack"] == required)
        assert case["rejected"] is True, case


def test_pilot_bundle_artifact_bytes_match_certificate_digests(tmp_path):
    """Exact-byte correspondence: packaged payload SHA-256 equals certificate digests.

    This is an independently tested property of the delivered ZIP, not a Lean
    refinement proof of the Python runtime.
    """
    import hashlib
    import zipfile

    evidence = run_independent_pilot_v1(
        tmp_path / "pilot",
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
    )
    bundle = Path(evidence["paths"]["bundle"])
    with zipfile.ZipFile(bundle, "r") as zf:
        certificate = json.loads(zf.read("certificate.json").decode("utf-8"))
        payloads = {
            name: zf.read(name)
            for name in zf.namelist()
            if name.startswith("artifacts/") and name.endswith("/payload")
        }
    assert payloads, "expected content-addressed artifact payloads"
    artifact_digests = {
        artifact["sha256"]
        for artifact in certificate.get("artifacts", [])
        if isinstance(artifact, dict) and isinstance(artifact.get("sha256"), str)
    }
    payload_digests = {hashlib.sha256(raw).hexdigest() for raw in payloads.values()}
    assert payload_digests <= artifact_digests
    assert evidence["bundle_sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()


def test_cleanroom_independent_pilot(tmp_path):
    if shutil.which("python3") is None:
        pytest.skip("python3 unavailable")
    summary = run_cleanroom_independent_pilot_v1(
        tmp_path / "cleanroom",
        lean_authority_path=AUTHORITY if AUTHORITY.is_file() else None,
        overwrite=True,
    )
    assert summary["pass"] is True
    assert summary["evidence"]["stages"]["authoritative"] is True
    assert (tmp_path / "cleanroom" / "CLEANROOM_SUMMARY.json").is_file()
