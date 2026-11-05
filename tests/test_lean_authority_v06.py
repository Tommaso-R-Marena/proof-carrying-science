from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.lean_authority_v06 import (
    V06LeanAuthorityError,
    build_authority_transcript_v06,
    enforce_lean_authority_v06,
    resolve_lean_authority_v06,
)
import pcs.lean_authority_v06 as authority_mod
from pcs.verifier_io_v06 import verify_package_directory_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))


def _write_public_key(path: Path) -> None:
    key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )
    path.write_bytes(
        key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def test_authority_transcript_binds_certificate_and_exact_evidence_order():
    certificate = {
        "semantic_hash": "ab" * 32,
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "environment": None,
        "evidence": [{"id": "E1"}, {"id": "E2"}],
    }
    transcript = build_authority_transcript_v06(
        certificate=certificate,
        environment_replay={
            "valid": True,
            "_authority_fresh_capture": None,
        },
        workflow_replay={"valid": True},
        replay={
            "valid": True,
            "evidence": [
                {"id": "E1", "kind": "computational_test", "outcome": "PASS"},
                {"id": "E2", "kind": "provenance", "outcome": "UNVERIFIED"},
            ],
        },
    )
    assert transcript["certificate_semantic_hash"] == certificate["semantic_hash"]
    assert transcript["checker_version"] == certificate["checker_version"]
    assert [x["evidence_id"] for x in transcript["replay"]] == ["E1", "E2"]


def test_authority_transcript_rejects_incomplete_observation_set():
    certificate = {
        "semantic_hash": "ab" * 32,
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "environment": None,
        "evidence": [{"id": "E1"}, {"id": "E2"}],
    }
    with pytest.raises(V06LeanAuthorityError, match="exactly cover"):
        build_authority_transcript_v06(
            certificate=certificate,
            environment_replay={"valid": True, "_authority_fresh_capture": None},
            workflow_replay={"valid": True},
            replay={
                "valid": True,
                "evidence": [
                    {"id": "E1", "kind": "computational_test", "outcome": "PASS"}
                ],
            },
        )


def test_explicit_missing_authority_fails_closed(tmp_path: Path):
    with pytest.raises(V06LeanAuthorityError, match="does not exist"):
        resolve_lean_authority_v06(tmp_path / "missing-authority")




def _dummy_context() -> dict:
    return {
        "certificate": {
            "semantic_hash": "ab" * 32,
            "checker_version": "pcs-python-kernel/0.6.0-dev",
            "environment": None,
            "evidence": [
                {
                    "id": "E1",
                    "check_spec": {"type": "reaction_balance"},
                }
            ],
        },
        "environment_replay": {
            "valid": True,
            "_authority_fresh_capture": None,
        },
        "workflow_replay": {"valid": True},
        "replay": {
            "valid": True,
            "evidence": [
                {"id": "E1", "kind": "computational_test", "outcome": "PASS"}
            ],
        },
    }


def test_lean_rejection_overrides_successful_python_precheck(monkeypatch):
    monkeypatch.setattr(
        authority_mod,
        "run_lean_authority_v06",
        lambda **kwargs: {
            "format": "pcs-lean-authority-result-v1",
            "required": True,
            "accepted": False,
            "verdict": "REJECT",
            "mode": "test",
            "authority_sha256": "00" * 32,
            "observation_transcript_sha256": "11" * 32,
            "certificate_semantic_hash": "ab" * 32,
        },
    )
    key = Ed25519PublicKey.from_public_bytes(bytes(range(32)))
    result = enforce_lean_authority_v06(
        {
            "format": "pcs-end-to-end-verifier-v06-v1",
            "authority_required": True,
            "authoritative": False,
            "valid": True,
            "failed_stage": None,
            "errors": [],
            "stages": {"normalized_set": True},
        },
        authority_context=_dummy_context(),
        certificate_signature_bytes=b"{}",
        package_manifest_bytes=b"{}",
        package_signature_bytes=b"{}",
        package_files={},
        public_key=key,
        expected_fingerprint=None,
    )
    assert result["valid"] is False
    assert result["authoritative"] is False
    assert result["failed_stage"] == "lean_authority"
    assert result["stages"]["lean_authority"] is False
    coverage = result["formal_coverage"]
    assert coverage["package_authority"] == "LEAN_AUTHORITY_REJECT"
    assert coverage["evidence"][0]["checker_semantics"] == "PROVED_IN_LEAN_FOR_THIS_CHECK_TYPE"
    assert coverage["evidence"][0]["execution_authority"] == "CHECKER_TYPE_PROVED_PACKAGE_NOT_LEAN_ACCEPTED"


def test_lean_acceptance_is_the_only_authoritative_success(monkeypatch):
    monkeypatch.setattr(
        authority_mod,
        "run_lean_authority_v06",
        lambda **kwargs: {
            "format": "pcs-lean-authority-result-v1",
            "required": True,
            "accepted": True,
            "verdict": "ACCEPT",
            "mode": "test",
            "authority_sha256": "00" * 32,
            "observation_transcript_sha256": "11" * 32,
            "certificate_semantic_hash": "ab" * 32,
        },
    )
    key = Ed25519PublicKey.from_public_bytes(bytes(range(32)))
    result = enforce_lean_authority_v06(
        {
            "format": "pcs-end-to-end-verifier-v06-v1",
            "authority_required": True,
            "authoritative": False,
            "valid": True,
            "failed_stage": None,
            "errors": [],
            "stages": {"normalized_set": True},
        },
        authority_context=_dummy_context(),
        certificate_signature_bytes=b"{}",
        package_manifest_bytes=b"{}",
        package_signature_bytes=b"{}",
        package_files={},
        public_key=key,
        expected_fingerprint=None,
    )
    assert result["valid"] is True
    assert result["authoritative"] is True
    assert result["stages"]["lean_authority"] is True
    coverage = result["formal_coverage"]
    assert coverage["package_authority"] == "LEAN_AUTHORITATIVE_ACCEPT"
    assert coverage["certified_type_evidence"] == 1
    assert coverage["evidence"][0]["execution_authority"] == "AUTHORITATIVELY_REPLAYED_BY_LEAN"


@pytest.mark.skipif(
    shutil.which("lake") is None,
    reason="Lean/Lake unavailable",
)
def test_golden_directory_is_accepted_by_mandatory_lean_authority(tmp_path: Path):
    package = tmp_path / "pkg"
    shutil.copytree(GOLDEN, package)
    (package / "metadata.json").unlink()
    public_key = tmp_path / "public.pem"
    _write_public_key(public_key)

    result = verify_package_directory_end_to_end_v06(
        package,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
    )
    assert result["valid"], result
    assert result["stages"]["lean_authority"] is True
    assert result["lean_authority"]["accepted"] is True
    assert result["lean_authority"]["verdict"] == "ACCEPT"
    assert len(result["lean_authority"]["authority_sha256"]) == 64
    assert len(result["lean_authority"]["observation_transcript_sha256"]) == 64
