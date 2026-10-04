from __future__ import annotations

from typing import Any

from .canonical_json import canonicalize_jcs_bytes, jcs_sha256


HASH_ENVELOPE_FORMAT = "pcs-jcs-sha256-v1"
SIGNATURE_PAYLOAD_FORMAT = "pcs-jcs-ed25519-payload-v1"

CERTIFICATE_SEMANTIC_DOMAIN = "pcs-certificate-semantic-sha256-v2"
CERTIFICATE_INTEGRITY_DOMAIN = "pcs-certificate-integrity-sha256-v2"
RUNTIME_SEMANTIC_DOMAIN = "pcs-runtime-semantic-sha256-v2"
INTAKE_SEMANTIC_DOMAIN = "pcs-intake-semantic-sha256-v2"
PREDICATE_COMMITMENT_DOMAIN = "pcs-predicate-sha256-v2"
NORMALIZED_DECISION_DOMAIN = "pcs-normalized-decision-sha256-v2"
NORMALIZED_INDEX_DOMAIN = "pcs-normalized-index-sha256-v2"

CERTIFICATE_SIGNATURE_DOMAIN = "pcs-certificate-signature-v2"
PACKAGE_SIGNATURE_DOMAIN = "pcs-package-signature-v2"
EXTERNAL_VALIDATOR_SIGNATURE_DOMAIN = "pcs-external-validator-receipt-signature-v1"

HASH_DOMAINS = frozenset(
    {
        CERTIFICATE_SEMANTIC_DOMAIN,
        CERTIFICATE_INTEGRITY_DOMAIN,
        RUNTIME_SEMANTIC_DOMAIN,
        INTAKE_SEMANTIC_DOMAIN,
        PREDICATE_COMMITMENT_DOMAIN,
        NORMALIZED_DECISION_DOMAIN,
        NORMALIZED_INDEX_DOMAIN,
    }
)
SIGNATURE_DOMAINS = frozenset(
    {
        CERTIFICATE_SIGNATURE_DOMAIN,
        PACKAGE_SIGNATURE_DOMAIN,
        EXTERNAL_VALIDATOR_SIGNATURE_DOMAIN,
    }
)


class CryptoDomainError(ValueError):
    pass


def hash_envelope(domain: str, payload: Any) -> dict[str, Any]:
    if domain not in HASH_DOMAINS:
        raise CryptoDomainError(f"unsupported PCS v0.6 hash domain: {domain!r}")
    return {
        "format": HASH_ENVELOPE_FORMAT,
        "domain": domain,
        "payload": payload,
    }


def domain_sha256(domain: str, payload: Any) -> str:
    return jcs_sha256(hash_envelope(domain, payload))


def signature_payload_envelope(domain: str, payload: Any) -> dict[str, Any]:
    if domain not in SIGNATURE_DOMAINS:
        raise CryptoDomainError(f"unsupported PCS v0.6 signature domain: {domain!r}")
    return {
        "format": SIGNATURE_PAYLOAD_FORMAT,
        "domain": domain,
        "payload": payload,
    }


def signature_payload_bytes(domain: str, payload: Any) -> bytes:
    return canonicalize_jcs_bytes(signature_payload_envelope(domain, payload))
