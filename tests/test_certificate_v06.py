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

PREDICATE = {
    "type": "reaction_balance",
    "reactants": [
        {"formula": "H2", "coefficient": 2},
        {"formula": "O2", "coefficient": 1},
    ],
    "products": [{"formula": "H2O", "coefficient": 2}],
}

BASE_CERTIFICATE = {
    "spec_version": SPEC_VERSION_V06,
    "checker_version": "pcs-python-kernel/0.6.0-dev",
    "canonical_json_profile": JCS_PROFILE,
    "semantic_hash_format": CERTIFICATE_SEMANTIC_DOMAIN,
    "integrity_hash_format": CERTIFICATE_INTEGRITY_DOMAIN,
    "generated_at": "2026-09-29T00:00:00+00:00",
    "subject": "v0.6 canonical fixture",
    "mission_scope": "computational assurance; test fixture",
    "assumptions": [
        {"id": "A1", "statement": "fixture assumption", "scope": ["C1"]}
    ],
    "claims": [
        {
            "id": "C1",
            "statement": "The fixture reaction is atom-balanced.",
            "kind": "computational",
            "predicate": PREDICATE,
            "required_evidence": ["E1"],
            "assumptions": ["A1"],
            "assessment": {
                "status": "COMPUTATIONALLY_SUPPORTED",
                "reason": "all declared computational checks passed",
            },
        }
    ],
    "artifacts": [],
    "evidence": [
        {
            "id": "E1",
            "kind": "computational_test",
            "claim_ids": ["C1"],
            "outcome": "PASS",
            "checker": "pcs-python-kernel/0.6.0-dev",
            "predicate": PREDICATE,
            "artifact_ids": [],
            "check_spec": PREDICATE,
        }
    ],
    "workflow": {"nodes": []},
    "workflow_summary": {"node_count": 0, "topological_order": []},
    "semantic_hash": "",
    "integrity_hash": "",
}

EXPECTED_SEMANTIC_HASH = "ea49dee3044a7e50f0f38c272d589b01ad2fe274308bf2dcda904a4a4ea28d7a"
EXPECTED_INTEGRITY_HASH = "a47acf203157f783f654320a5b80a8437cb70d5c43aeb723b1941e50689deeb9"


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
    changed["claims"][0]["statement"] = "A different machine-bound scientific statement."
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
