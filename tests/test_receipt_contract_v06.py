from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.formal_coverage_v06 import CERTIFIED_BUILTIN_CHECK_TYPES_V06
from pcs.receipt_contract_v06 import (
    audit_verification_receipt_file_v06,
    audit_verification_receipt_v06,
)
from pcs.receipt_signature_v06 import (
    REVIEW_RECEIPT_SIGNATURE_DOMAIN_V06,
    REVIEW_RECEIPT_SIGNATURE_FORMAT_V06,
    V06ReceiptSignatureError,
    receipt_signature_payload_v06,
    sign_verification_receipt_v06,
    verify_verification_receipt_signature_v06,
)
from pcs.verifier_io_v06 import V06VerifierIOError, write_verification_receipt_v06
from pcs.signing import public_key_fingerprint


def _coverage(*, authoritative: bool) -> dict:
    return {
        "format": "pcs-formal-coverage-v1",
        "checker_classification_scope": "CHECK_TYPE_ONLY",
        "execution_authority_scope": "EXACT_PACKAGE_VERIFICATION",
        "certified_checker_types": sorted(CERTIFIED_BUILTIN_CHECK_TYPES_V06),
        "evidence_total": 1,
        "certified_type_evidence": 1,
        "outside_certified_type_evidence": 0,
        "package_authority": (
            "LEAN_AUTHORITATIVE_ACCEPT"
            if authoritative
            else "LEAN_AUTHORITY_REJECT"
        ),
        "evidence": [
            {
                "evidence_id": "E1",
                "check_type": "reaction_balance",
                "checker_semantics": "PROVED_IN_LEAN_FOR_THIS_CHECK_TYPE",
                "execution_authority": (
                    "AUTHORITATIVELY_REPLAYED_BY_LEAN"
                    if authoritative
                    else "CHECKER_TYPE_PROVED_PACKAGE_NOT_LEAN_ACCEPTED"
                ),
            }
        ],
    }


def _receipt(
    *,
    bundle_sha256: str = "a" * 64,
    producer_fingerprint: str = "f" * 64,
    authority_sha256: str = "1" * 64,
    accepted: bool = True,
) -> dict:
    return {
        "format": "pcs-end-to-end-verifier-v06-v1",
        "authority_required": True,
        "authoritative": True,
        "valid": True,
        "accepted": accepted,
        "failed_stage": None,
        "errors": [],
        "stages": {"lean_authority": True},
        "bundle_sha256": bundle_sha256,
        "archive_format": "zip",
        "archive_assurance": "python-materialized-legacy-zip",
        "certificate_semantic_hash": "b" * 64,
        "certificate_integrity_hash": "c" * 64,
        "normalized_index_semantic_hash": "d" * 64,
        "public_key_fingerprint": producer_fingerprint,
        "lean_authority": {
            "format": "pcs-lean-authority-result-v1",
            "required": True,
            "accepted": True,
            "verdict": "ACCEPT",
            "mode": "test",
            "authority_sha256": authority_sha256,
            "observation_transcript_sha256": "2" * 64,
            "certificate_semantic_hash": "b" * 64,
            "archive_mode": "python-materialized-members",
        },
        "formal_coverage": _coverage(authoritative=True),
        "reviewer_policy": (
            {
                "applied": False,
                "pass": None,
                "policy_sha256": None,
                "failures": [],
            }
            if accepted
            else {
                "applied": True,
                "pass": False,
                "policy_sha256": "e" * 64,
                "failures": [{"type": "claim_status"}],
            }
        ),
    }


def test_contract_accepts_consistent_bound_provenance_summary():
    receipt = _receipt()
    receipt["provenance"] = {
        "mode": "bound",
        "semantic_hash": "9" * 64,
        "entries": [
            {
                "kind": "build_provenance",
                "format": "dsse-in-toto-statement-v1-ed25519",
                "sha256": "8" * 64,
            },
            {
                "kind": "sbom",
                "format": "cyclonedx-json-1.5",
                "sha256": "7" * 64,
            },
        ],
        "reviewer_expectations": {
            "applied": True,
            "build_provenance_fingerprint": "6" * 64,
            "subject_sha256": ["5" * 64],
        },
    }

    audit = audit_verification_receipt_v06(receipt)

    assert audit["valid"], audit["errors"]
    assert audit["checks"]["provenance_bound_hash"] is True
    assert audit["checks"]["provenance_entry_contract"] is True
    assert audit["checks"][
        "provenance_reviewer_expectations_contract"
    ] is True


def test_contract_rejects_inconsistent_reviewer_provenance_expectations():
    receipt = _receipt()
    receipt["provenance"] = {
        "mode": "bound",
        "semantic_hash": "9" * 64,
        "entries": [
            {
                "kind": "sbom",
                "format": "cyclonedx-json-1.5",
                "sha256": "7" * 64,
            }
        ],
        "reviewer_expectations": {
            "applied": False,
            "build_provenance_fingerprint": "6" * 64,
            "subject_sha256": [],
        },
    }

    audit = audit_verification_receipt_v06(receipt)

    assert audit["valid"] is False
    assert audit["checks"][
        "provenance_reviewer_expectations_contract"
    ] is False


def test_contract_rejects_inconsistent_provenance_summary():
    receipt = _receipt()
    receipt["provenance"] = {
        "mode": "none",
        "semantic_hash": "9" * 64,
        "entries": [],
    }

    audit = audit_verification_receipt_v06(receipt)

    assert audit["valid"] is False
    assert audit["checks"]["provenance_none_contract"] is False
    assert any(
        "mode=none" in error
        for error in audit["errors"]
    )


def test_contract_rejects_valid_without_authoritative_lean_acceptance():
    receipt = _receipt()
    receipt["authoritative"] = False
    receipt["stages"]["lean_authority"] = False

    audit = audit_verification_receipt_v06(receipt)

    assert audit["valid"] is False
    assert any("valid and authoritative" in error for error in audit["errors"])
    assert any(
        "lean_authority.accepted contradicts authoritative" in error
        for error in audit["errors"]
    )


def test_contract_rejects_formal_coverage_that_overclaims_execution():
    receipt = _receipt()
    receipt["authoritative"] = False
    receipt["valid"] = False
    receipt["accepted"] = False
    receipt["lean_authority"]["accepted"] = False
    receipt["lean_authority"]["verdict"] = "REJECT"
    receipt["stages"]["lean_authority"] = False
    receipt["formal_coverage"]["package_authority"] = "LEAN_AUTHORITY_REJECT"
    # Deliberately leave the evidence row claiming authoritative replay.
    receipt["reviewer_policy"] = {
        "applied": False,
        "pass": None,
        "policy_sha256": None,
        "failures": [],
    }

    audit = audit_verification_receipt_v06(receipt)

    assert audit["valid"] is False
    assert any(
        "execution authority contradicts package authority" in error
        for error in audit["errors"]
    )


def test_contract_binds_optional_external_bundle_key_and_authority(tmp_path: Path):
    bundle = tmp_path / "bundle.pcs.zip"
    bundle.write_bytes(b"exact bundle bytes")
    authority = tmp_path / "pcs-lean-authority"
    authority.write_bytes(b"exact authority bytes")

    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    producer_public = private.public_key()
    producer_path = tmp_path / "producer-public.pem"
    producer_path.write_bytes(
        producer_public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    receipt = _receipt(
        bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
        producer_fingerprint=public_key_fingerprint(producer_public),
        authority_sha256=hashlib.sha256(authority.read_bytes()).hexdigest(),
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    audit = audit_verification_receipt_file_v06(
        receipt_path,
        bundle_path=bundle,
        producer_public_key_path=producer_path,
        authority_path=authority,
    )
    assert audit["valid"], audit["errors"]
    assert audit["checks"]["external_bundle_binding"] is True
    assert audit["checks"]["external_producer_key_binding"] is True
    assert audit["checks"]["external_authority_binary_binding"] is True

    bundle.write_bytes(b"different bytes")
    mismatch = audit_verification_receipt_file_v06(
        receipt_path,
        bundle_path=bundle,
        producer_public_key_path=producer_path,
        authority_path=authority,
    )
    assert mismatch["valid"] is False
    assert mismatch["checks"]["external_bundle_binding"] is False


def test_writer_and_normal_signer_refuse_contradictory_receipt(tmp_path: Path):
    contradictory = _receipt()
    contradictory["authoritative"] = False
    contradictory["stages"]["lean_authority"] = False

    with pytest.raises(V06VerifierIOError, match="receipt contract failed"):
        write_verification_receipt_v06(
            contradictory,
            tmp_path / "writer-refused.json",
        )

    receipt_path = tmp_path / "contradictory.json"
    receipt_path.write_text(
        json.dumps(contradictory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(31, 63)))
    private_path = tmp_path / "reviewer-private.pem"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    with pytest.raises(V06ReceiptSignatureError, match="receipt contract failed"):
        sign_verification_receipt_v06(
            receipt_path,
            private_path,
            tmp_path / "should-not-exist.sig.json",
        )


def test_valid_signature_over_contradictory_receipt_is_still_rejected(tmp_path: Path):
    receipt = _receipt()
    receipt["authoritative"] = False
    receipt["stages"]["lean_authority"] = False

    receipt_path = tmp_path / "receipt.json"
    raw = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    receipt_path.write_bytes(raw)

    reviewer_private = Ed25519PrivateKey.from_private_bytes(bytes(range(31, 63)))
    reviewer_public = reviewer_private.public_key()
    reviewer_public_path = tmp_path / "reviewer-public.pem"
    reviewer_public_path.write_bytes(
        reviewer_public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    receipt_sha256 = hashlib.sha256(raw).hexdigest()
    payload = receipt_signature_payload_v06(receipt, receipt_sha256)
    signature = reviewer_private.sign(
        REVIEW_RECEIPT_SIGNATURE_DOMAIN_V06 + canonicalize_jcs_bytes(payload)
    )
    signature_record = {
        "signature_format": REVIEW_RECEIPT_SIGNATURE_FORMAT_V06,
        "algorithm": "Ed25519",
        "reviewer_public_key_fingerprint": public_key_fingerprint(reviewer_public),
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    signature_path = tmp_path / "receipt.sig.json"
    signature_path.write_bytes(canonicalize_jcs_bytes(signature_record))

    checked = verify_verification_receipt_signature_v06(
        receipt_path,
        signature_path,
        reviewer_public_path,
    )

    assert checked["contract_valid"] is False
    assert checked["valid"] is False
    assert any(error.startswith("receipt contract:") for error in checked["errors"])
