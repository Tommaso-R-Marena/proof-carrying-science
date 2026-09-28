import json
import tempfile
from pathlib import Path

import pytest

from pcs.kernel import build_certificate, verify_certificate, AssuranceError
from pcs.policy import validate_policy, PolicyError
from pcs.schema_validation import (
    validate_verification_receipt_shape,
    SchemaValidationError,
)


def test_manifest_schema_rejects_missing_subject_before_certification():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "x.txt").write_text("x", encoding="utf-8")
        manifest = {
            "assumptions": [],
            "claims": [],
            "artifacts": [{"id": "a", "path": "x.txt", "role": "input"}],
            "checks": [],
            "workflow": {"nodes": []},
        }
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(AssuranceError, match="manifest failed JSON Schema validation"):
            build_certificate(path, root / "out")


def test_certificate_schema_failure_returns_invalid_not_exception():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / "certificate.json"
        path.write_text(json.dumps({"spec_version": "pcs-0.5"}), encoding="utf-8")
        result = verify_certificate(path)
        assert result["valid"] is False
        assert any("certificate failed JSON Schema validation" in e for e in result["errors"])


def test_policy_schema_rejects_unknown_fields():
    policy = {
        "policy_version": "pcs-acceptance-policy-v1",
        "required_claims": {"C": ["COMPUTATIONALLY_SUPPORTED"]},
        "unexpected": True,
    }
    with pytest.raises(PolicyError, match="acceptance policy failed JSON Schema validation"):
        validate_policy(policy)


def test_verification_receipt_requires_timestamp():
    receipt = {
        "verification_receipt_format": "pcs-bundle-verification-v1",
        "verifier_version": "pcs-python-kernel/0.5.0",
        "valid": True,
        "bundle_sha256": "0" * 64,
        "verification_inputs": {
            "require_signature": False,
            "expected_signer_fingerprint": None,
            "policy_sha256": None,
        },
        "assurance_dimensions": {
            "scientific_replay": "PASS",
            "package_integrity": "PASS",
            "signer_authenticity": "UNSIGNED",
            "reviewer_policy": "NOT_APPLIED",
        },
    }
    with pytest.raises(SchemaValidationError):
        validate_verification_receipt_shape(receipt)


def test_packaged_schemas_match_repository_canonical_copies():
    root = Path(__file__).resolve().parents[1]
    names = [
        "manifest.schema.json",
        "certificate.schema.json",
        "package_manifest.schema.json",
        "acceptance_policy.schema.json",
        "verification_receipt.schema.json",
    ]
    for name in names:
        assert (root / "schemas" / name).read_bytes() == (root / "pcs" / "schemas" / name).read_bytes()
