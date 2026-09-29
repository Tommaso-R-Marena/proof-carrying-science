from __future__ import annotations

import hashlib

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.crypto_domains_v06 import (
    CERTIFICATE_INTEGRITY_DOMAIN,
    CERTIFICATE_SEMANTIC_DOMAIN,
    CERTIFICATE_SIGNATURE_DOMAIN,
    HASH_ENVELOPE_FORMAT,
    INTAKE_SEMANTIC_DOMAIN,
    PREDICATE_COMMITMENT_DOMAIN,
    NORMALIZED_DECISION_DOMAIN,
    PACKAGE_SIGNATURE_DOMAIN,
    RUNTIME_SEMANTIC_DOMAIN,
    SIGNATURE_PAYLOAD_FORMAT,
    CryptoDomainError,
    domain_sha256,
    hash_envelope,
    signature_payload_bytes,
    signature_payload_envelope,
)
from pcs.hashing import canonical_json_bytes, sha256_json


PAYLOAD = {"z": "é", "a": 1.0, "nested": {"b": 2, "a": 1}}

EXPECTED_HASHES = {
    CERTIFICATE_SEMANTIC_DOMAIN: "835f1ca3a9f2c64356a1a36e4d713f2f229618fb6fc0a6a51bb19c449645bdf8",
    CERTIFICATE_INTEGRITY_DOMAIN: "6f0032e60db4b03f69f0f78ff52a24596597ff4f8e0c08abf39f2997c3534fe8",
    RUNTIME_SEMANTIC_DOMAIN: "829e8c9e07d587ff5dfe1837bab087c73aeac678b47a5365d8cbc576db259fc6",
    INTAKE_SEMANTIC_DOMAIN: "f9e9b66c4f051d14247265e611b64c7c1bf415e7185a83a09ebea6a46fa7622d",
    PREDICATE_COMMITMENT_DOMAIN: "509c32f9f26b92ff1c3f5d3800a940fea55d02ce1a2f265820d86df870289131",
    NORMALIZED_DECISION_DOMAIN: "e2d3054b205ee218fa6358a7da8d0b9979900a753ce034a558ec0e1694726879",
}

EXPECTED_SIGNATURE_PAYLOAD_SHA256 = {
    CERTIFICATE_SIGNATURE_DOMAIN: "66b2b707526c28e7bb311ac05203712b133ed883fdc1158fd823b33205d04cd5",
    PACKAGE_SIGNATURE_DOMAIN: "cc81ab71e8ab901985fe8601bbd34b016be02d31c2c23fb8b8b5b0968c1a41cd",
}


@pytest.mark.parametrize(("domain", "expected"), EXPECTED_HASHES.items())
def test_v06_domain_hash_vectors(domain: str, expected: str):
    assert domain_sha256(domain, PAYLOAD) == expected
    envelope = hash_envelope(domain, PAYLOAD)
    assert envelope["format"] == HASH_ENVELOPE_FORMAT
    assert envelope["domain"] == domain


@pytest.mark.parametrize(
    ("domain", "expected_sha256"), EXPECTED_SIGNATURE_PAYLOAD_SHA256.items()
)
def test_v06_signature_payload_vectors(domain: str, expected_sha256: str):
    envelope = signature_payload_envelope(domain, PAYLOAD)
    assert envelope["format"] == SIGNATURE_PAYLOAD_FORMAT
    assert envelope["domain"] == domain
    assert hashlib.sha256(signature_payload_bytes(domain, PAYLOAD)).hexdigest() == expected_sha256


def test_same_payload_has_distinct_hash_in_each_v06_domain():
    hashes = {domain_sha256(domain, PAYLOAD) for domain in EXPECTED_HASHES}
    assert len(hashes) == len(EXPECTED_HASHES)


def test_v05_hash_is_not_reused_as_v06_domain_hash():
    legacy = sha256_json(PAYLOAD)
    assert all(legacy != domain_sha256(domain, PAYLOAD) for domain in EXPECTED_HASHES)


def test_signature_domains_are_distinct_for_same_payload():
    assert signature_payload_bytes(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD) != signature_payload_bytes(
        PACKAGE_SIGNATURE_DOMAIN, PAYLOAD
    )


def test_unknown_domains_fail_closed():
    with pytest.raises(CryptoDomainError):
        domain_sha256("pcs-unknown-sha256-v2", PAYLOAD)
    with pytest.raises(CryptoDomainError):
        signature_payload_bytes("pcs-unknown-signature-v2", PAYLOAD)


def test_v05_and_v06_signature_payloads_are_not_interchangeable():
    key = Ed25519PrivateKey.generate()
    public = key.public_key()

    legacy_payload = canonical_json_bytes(PAYLOAD)
    v06_payload = signature_payload_bytes(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD)

    legacy_signature = key.sign(legacy_payload)
    v06_signature = key.sign(v06_payload)

    public.verify(legacy_signature, legacy_payload)
    public.verify(v06_signature, v06_payload)

    with pytest.raises(InvalidSignature):
        public.verify(legacy_signature, v06_payload)
    with pytest.raises(InvalidSignature):
        public.verify(v06_signature, legacy_payload)


def test_certificate_and_package_signature_domains_cannot_cross_verify():
    key = Ed25519PrivateKey.generate()
    public = key.public_key()

    certificate_payload = signature_payload_bytes(CERTIFICATE_SIGNATURE_DOMAIN, PAYLOAD)
    package_payload = signature_payload_bytes(PACKAGE_SIGNATURE_DOMAIN, PAYLOAD)

    certificate_signature = key.sign(certificate_payload)
    package_signature = key.sign(package_payload)

    with pytest.raises(InvalidSignature):
        public.verify(certificate_signature, package_payload)
    with pytest.raises(InvalidSignature):
        public.verify(package_signature, certificate_payload)
