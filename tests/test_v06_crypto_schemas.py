from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.crypto_domains_v06 import (
    CERTIFICATE_SEMANTIC_DOMAIN,
    CERTIFICATE_SIGNATURE_DOMAIN,
    hash_envelope,
)
from pcs.schema_validation import (
    SchemaValidationError,
    validate_v06_hash_envelope_shape,
    validate_v06_signature_record_shape,
)
from pcs.signing_v06 import sign_jcs_payload


ROOT = Path(__file__).resolve().parents[1]


def test_public_and_packaged_v06_crypto_schemas_are_identical():
    for name in ("hash_envelope_v06.schema.json", "signature_record_v06.schema.json"):
        assert (ROOT / "schemas" / name).read_bytes() == (
            ROOT / "pcs" / "schemas" / name
        ).read_bytes()


def test_v06_hash_envelope_schema_accepts_generated_envelope():
    validate_v06_hash_envelope_shape(
        hash_envelope(CERTIFICATE_SEMANTIC_DOMAIN, {"claim": "C1"})
    )


def test_v06_hash_envelope_schema_rejects_unknown_field():
    envelope = hash_envelope(CERTIFICATE_SEMANTIC_DOMAIN, {"claim": "C1"})
    envelope["unexpected"] = True
    with pytest.raises(SchemaValidationError):
        validate_v06_hash_envelope_shape(envelope)


def test_v06_signature_schema_accepts_generated_record():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(
        CERTIFICATE_SIGNATURE_DOMAIN,
        {"claim": "C1"},
        key,
    )
    validate_v06_signature_record_shape(record)


def test_v06_signature_schema_rejects_extra_signed_envelope_field():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(
        CERTIFICATE_SIGNATURE_DOMAIN,
        {"claim": "C1"},
        key,
    )
    bad = deepcopy(record)
    bad["payload"]["unexpected"] = True
    with pytest.raises(SchemaValidationError):
        validate_v06_signature_record_shape(bad)


def test_v06_signature_schema_rejects_malformed_base64_length():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(
        CERTIFICATE_SIGNATURE_DOMAIN,
        {"claim": "C1"},
        key,
    )
    bad = deepcopy(record)
    bad["signature"] = "AAAA"
    with pytest.raises(SchemaValidationError):
        validate_v06_signature_record_shape(bad)



def test_v06_package_schema_requires_certificate_and_forbids_self_reference():
    from pcs.schema_validation import validate_v06_package_manifest_shape

    base = {
        "package_format": "pcs-package-v2",
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "certificate_spec_version": "pcs-0.6",
        "certificate_semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
        "certificate_integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
        "certificate_semantic_hash": "a" * 64,
        "certificate_integrity_hash": "b" * 64,
        "files": {
            "certificate.json": {"sha256": "c" * 64, "size": 1},
        },
    }
    validate_v06_package_manifest_shape(base)

    missing = deepcopy(base)
    missing["files"] = {"artifact.txt": {"sha256": "d" * 64, "size": 1}}
    with pytest.raises(SchemaValidationError):
        validate_v06_package_manifest_shape(missing)

    self_bound = deepcopy(base)
    self_bound["files"]["package_signature.json"] = {"sha256": "e" * 64, "size": 1}
    with pytest.raises(SchemaValidationError):
        validate_v06_package_manifest_shape(self_bound)
