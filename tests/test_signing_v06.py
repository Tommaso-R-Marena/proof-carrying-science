from __future__ import annotations

from copy import deepcopy

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.crypto_domains_v06 import (
    CERTIFICATE_SIGNATURE_DOMAIN,
    PACKAGE_SIGNATURE_DOMAIN,
)
from pcs.signing_v06 import (
    SIGNATURE_RECORD_FORMAT,
    sign_jcs_payload,
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
    assert "unsupported v0.6 signature record format" in result["errors"]


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
