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
    resolve_lean_authority_v06,
)
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
