from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pcs.canonical_json import JCS_PROFILE
from pcs.certificate_v06 import (
    SPEC_VERSION_V06,
    finalize_certificate_hashes_v06,
    verify_certificate_hashes_v06,
)
from pcs.crypto_domains_v06 import (
    CERTIFICATE_INTEGRITY_DOMAIN,
    CERTIFICATE_SEMANTIC_DOMAIN,
)
from pcs.hashing import sha256_json
from pcs.schema_validation import validate_v06_certificate_shape


ROOT = Path(__file__).resolve().parents[1]

BASE_CERTIFICATE = {
    "spec_version": SPEC_VERSION_V06,
    "checker_version": "pcs-python-kernel/0.6.0-dev",
    "canonical_json_profile": JCS_PROFILE,
    "semantic_hash_format": CERTIFICATE_SEMANTIC_DOMAIN,
    "integrity_hash_format": CERTIFICATE_INTEGRITY_DOMAIN,
    "generated_at": "2026-09-29T00:00:00+00:00",
    "subject": "v0.6 canonical fixture",
    "mission_scope": "computational assurance; test fixture",
    "assumptions": [{"id": "A1", "statement": "fixture assumption"}],
    "claims": [
        {
            "id": "C1",
            "kind": "computational",
            "required_evidence": ["E1"],
            "assumptions": ["A1"],
            "assessment": {"status": "COMPUTATIONALLY_SUPPORTED"},
        }
    ],
    "artifacts": [],
    "evidence": [{"id": "E1", "kind": "computational_test", "outcome": "PASS"}],
    "workflow": {"nodes": []},
    "workflow_summary": {"node_count": 0, "topological_order": []},
    "semantic_hash": "",
    "integrity_hash": "",
}

EXPECTED_SEMANTIC_HASH = "2b796888292f0eba69e2519a096b4882fd49024e29012c578e5913a6879daba0"
EXPECTED_INTEGRITY_HASH = "f67f5a5a144a1db50985adba2b766b06b2df87bcb30af1ad8817779af39d8b57"


def test_v06_certificate_hash_vector():
    cert = finalize_certificate_hashes_v06(BASE_CERTIFICATE)
    assert cert["semantic_hash"] == EXPECTED_SEMANTIC_HASH
    assert cert["integrity_hash"] == EXPECTED_INTEGRITY_HASH
    validate_v06_certificate_shape(cert)
    result = verify_certificate_hashes_v06(cert)
    assert result["valid"], result["errors"]


def test_v06_semantic_hash_ignores_generation_timestamp_but_integrity_binds_it():
    first = finalize_certificate_hashes_v06(BASE_CERTIFICATE)
    changed = deepcopy(BASE_CERTIFICATE)
    changed["generated_at"] = "2026-09-29T00:00:01+00:00"
    second = finalize_certificate_hashes_v06(changed)

    assert first["semantic_hash"] == second["semantic_hash"]
    assert first["integrity_hash"] != second["integrity_hash"]


def test_v06_scientific_content_change_changes_both_hashes():
    first = finalize_certificate_hashes_v06(BASE_CERTIFICATE)
    changed = deepcopy(BASE_CERTIFICATE)
    changed["claims"][0]["assessment"]["status"] = "OPEN"
    second = finalize_certificate_hashes_v06(changed)

    assert first["semantic_hash"] != second["semantic_hash"]
    assert first["integrity_hash"] != second["integrity_hash"]


def test_v06_semantic_tamper_is_detected_even_if_integrity_is_unchanged():
    cert = finalize_certificate_hashes_v06(BASE_CERTIFICATE)
    tampered = deepcopy(cert)
    tampered["subject"] = "tampered"

    result = verify_certificate_hashes_v06(tampered)
    assert not result["valid"]
    assert "v0.6 certificate semantic hash mismatch" in result["errors"]
    assert "v0.6 certificate integrity hash mismatch" in result["errors"]


def test_v06_integrity_hash_binds_recorded_semantic_hash():
    cert = finalize_certificate_hashes_v06(BASE_CERTIFICATE)
    tampered = deepcopy(cert)
    tampered["semantic_hash"] = "0" * 64

    result = verify_certificate_hashes_v06(tampered)
    assert not result["valid"]
    assert "v0.6 certificate semantic hash mismatch" in result["errors"]
    assert "v0.6 certificate integrity hash mismatch" in result["errors"]


def test_v05_hash_semantics_are_not_reused_for_v06_certificate():
    cert = finalize_certificate_hashes_v06(BASE_CERTIFICATE)
    legacy_style = deepcopy(cert)
    legacy_style.pop("generated_at", None)
    legacy_style.pop("semantic_hash", None)
    legacy_style.pop("integrity_hash", None)
    assert sha256_json(legacy_style) != cert["semantic_hash"]


def test_public_and_packaged_v06_certificate_schemas_match():
    assert (ROOT / "schemas/certificate_v06.schema.json").read_bytes() == (
        ROOT / "pcs/schemas/certificate_v06.schema.json"
    ).read_bytes()
