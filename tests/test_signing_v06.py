from __future__ import annotations

from copy import deepcopy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.crypto_domains_v06 import (
    CERTIFICATE_SIGNATURE_DOMAIN,
    PACKAGE_SIGNATURE_DOMAIN,
)
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.signing_v06 import (
    SIGNATURE_RECORD_FORMAT,
    sign_certificate_v06,
    sign_jcs_payload,
    verify_certificate_signature_v06,
    verify_jcs_signature,
)


PAYLOAD = {
    "spec_version": "pcs-0.6",
    "subject": "cross-language-fixture",
    "semantic_hash": "1" * 64,
    "integrity_hash": "2" * 64,
}


def test_v06_signature_record_round_trip():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD, key)

    assert record["signature_format"] == SIGNATURE_RECORD_FORMAT
    result = verify_jcs_signature(
        record,
        key.public_key(),
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
    )
    assert result["valid"], result["errors"]


def test_v06_signature_record_detects_payload_tamper():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD, key)
    tampered = deepcopy(record)
    tampered["payload"]["payload"]["subject"] = "tampered"

    result = verify_jcs_signature(
        tampered,
        key.public_key(),
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
    )
    assert not result["valid"]
    assert any(
        "payload SHA-256 mismatch" in error or "signature verification failed" in error
        for error in result["errors"]
    )


def test_v06_signature_record_rejects_domain_substitution():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD, key)
    substituted = deepcopy(record)
    substituted["payload"]["domain"] = PACKAGE_SIGNATURE_DOMAIN

    result = verify_jcs_signature(
        substituted,
        key.public_key(),
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
    )
    assert not result["valid"]
    assert "signature payload envelope does not match expected format/domain" in result["errors"]


def test_valid_certificate_domain_signature_is_not_valid_package_signature():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD, key)

    result = verify_jcs_signature(
        record,
        key.public_key(),
        expected_domain=PACKAGE_SIGNATURE_DOMAIN,
    )
    assert not result["valid"]


def test_legacy_signature_format_is_not_accepted_as_v06():
    key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD, key)
    legacy = deepcopy(record)
    legacy["signature_format"] = "pcs-ed25519-v1"

    result = verify_jcs_signature(
        legacy,
        key.public_key(),
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
    )
    assert not result["valid"]
    assert any("signature_format" in error for error in result["errors"])


def test_wrong_public_key_and_pinned_fingerprint_fail_closed():
    signing_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()
    record = sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD, signing_key)

    wrong_key_result = verify_jcs_signature(
        record,
        wrong_key.public_key(),
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
    )
    assert not wrong_key_result["valid"]

    wrong_pin = "0" * 64
    pin_result = verify_jcs_signature(
        record,
        signing_key.public_key(),
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
        expected_fingerprint=wrong_pin,
    )
    assert not pin_result["valid"]
    assert any("pinned expected fingerprint" in error for error in pin_result["errors"])


V06_CERTIFICATE = finalize_certificate_hashes_v06(
    {
        "spec_version": "pcs-0.6",
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
        "integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
        "generated_at": "2026-09-29T00:00:00+00:00",
        "subject": "signature fixture",
        "mission_scope": "signature binding fixture",
        "assumptions": [],
        "claims": [],
        "artifacts": [],
        "evidence": [],
        "workflow": {"nodes": []},
        "workflow_summary": {"node_count": 0, "topological_order": []},
        "semantic_hash": "",
        "integrity_hash": "",
    }
)


def test_v06_certificate_signature_round_trip():
    key = Ed25519PrivateKey.generate()
    record = sign_certificate_v06(V06_CERTIFICATE, key)
    result = verify_certificate_signature_v06(
        V06_CERTIFICATE,
        record,
        key.public_key(),
    )
    assert result["valid"], result["errors"]


def test_valid_signature_for_different_certificate_payload_is_rejected():
    from copy import deepcopy

    key = Ed25519PrivateKey.generate()
    other_source = deepcopy(V06_CERTIFICATE)
    other_source["subject"] = "other certificate"
    other_source["semantic_hash"] = ""
    other_source["integrity_hash"] = ""
    other = finalize_certificate_hashes_v06(other_source)

    record = sign_certificate_v06(other, key)
    result = verify_certificate_signature_v06(
        V06_CERTIFICATE,
        record,
        key.public_key(),
    )
    assert not result["valid"]
    assert "signature payload does not match v0.6 certificate" in result["errors"]


def test_certificate_signature_refuses_hash_invalid_certificate():
    from copy import deepcopy

    key = Ed25519PrivateKey.generate()
    tampered = deepcopy(V06_CERTIFICATE)
    tampered["subject"] = "tampered without rehash"

    try:
        sign_certificate_v06(tampered, key)
    except Exception as exc:
        assert "invalid v0.6 certificate" in str(exc)
    else:
        raise AssertionError("signing should refuse a hash-invalid v0.6 certificate")
