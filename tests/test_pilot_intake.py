import copy
import json
import tempfile
from pathlib import Path

import pytest

from pcs.intake import (
    freeze_intake,
    validate_lock,
    assert_lock_matches_certificate,
    PilotIntakeError,
)
from pcs.kernel import build_certificate


def _paths():
    root = Path(__file__).resolve().parents[1]
    return (
        root / "examples" / "pkpd_one_compartment" / "pilot_intake.json",
        root / "examples" / "pkpd_one_compartment" / "manifest.json",
    )


def test_frozen_intake_matches_reference_certificate():
    intake_path, manifest_path = _paths()
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    lock = freeze_intake(intake)
    assert validate_lock(lock)["intake_semantic_hash"] == lock["intake_semantic_hash"]
    with tempfile.TemporaryDirectory() as td:
        cert = build_certificate(manifest_path, Path(td) / "evidence")
        assert_lock_matches_certificate(lock, cert)


def test_same_claim_id_with_changed_statement_is_rejected():
    intake_path, manifest_path = _paths()
    lock = freeze_intake(json.loads(intake_path.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory() as td:
        cert = build_certificate(manifest_path, Path(td) / "evidence")
        cert = copy.deepcopy(cert)
        cert["claims"][0]["statement"] = "A weaker post-hoc claim with the same ID."
        with pytest.raises(PilotIntakeError, match="claim statement changed"):
            assert_lock_matches_certificate(lock, cert)


def test_same_claim_id_with_changed_assurance_class_is_rejected():
    intake_path, manifest_path = _paths()
    lock = freeze_intake(json.loads(intake_path.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory() as td:
        cert = build_certificate(manifest_path, Path(td) / "evidence")
        cert = copy.deepcopy(cert)
        cert["claims"][0]["kind"] = "formal"
        with pytest.raises(PilotIntakeError, match="assurance class changed"):
            assert_lock_matches_certificate(lock, cert)


def test_changed_assumption_text_is_rejected():
    intake_path, manifest_path = _paths()
    lock = freeze_intake(json.loads(intake_path.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory() as td:
        cert = build_certificate(manifest_path, Path(td) / "evidence")
        cert = copy.deepcopy(cert)
        cert["assumptions"][0]["statement"] = "Changed after observing results."
        with pytest.raises(PilotIntakeError, match="assumption statement changed"):
            assert_lock_matches_certificate(lock, cert)


def test_tampered_intake_lock_hash_is_rejected():
    intake_path, _ = _paths()
    lock = freeze_intake(json.loads(intake_path.read_text(encoding="utf-8")))
    lock["intake"]["notes"] = "tampered after freeze"
    with pytest.raises(PilotIntakeError, match="semantic hash mismatch"):
        validate_lock(lock)


def test_freeze_intake_file_refuses_overwrite_by_default():
    from pcs.intake import freeze_intake_file
    intake_path, _ = _paths()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "pilot.lock.json"
        freeze_intake_file(intake_path, out)
        original = out.read_bytes()
        with pytest.raises(PilotIntakeError, match="refusing to overwrite"):
            freeze_intake_file(intake_path, out)
        assert out.read_bytes() == original
