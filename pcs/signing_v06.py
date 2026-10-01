from __future__ import annotations

import base64
import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical_json import CanonicalJSONError, canonicalize_jcs_bytes
from .crypto_domains_v06 import (
    SIGNATURE_DOMAINS,
    CryptoDomainError,
    signature_payload_envelope,
)
from .signing import public_key_fingerprint
from .schema_validation import (
    SchemaValidationError,
    validate_v06_signature_record_shape,
)


SIGNATURE_RECORD_FORMAT = "pcs-ed25519-jcs-v2"


class V06SignatureError(ValueError):
    pass


def sign_jcs_payload(
    domain: str,
    payload: Any,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    envelope = signature_payload_envelope(domain, payload)
    canonical = canonicalize_jcs_bytes(envelope)
    signature = private_key.sign(canonical)
    public_key = private_key.public_key()
    record = {
        "signature_format": SIGNATURE_RECORD_FORMAT,
        "algorithm": "Ed25519",
        "public_key_fingerprint": public_key_fingerprint(public_key),
        "payload_sha256": hashlib.sha256(canonical).hexdigest(),
        "payload": envelope,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    validate_v06_signature_record_shape(record)
    return record


def verify_jcs_signature(
    record: dict[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_domain: str,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    try:
        validate_v06_signature_record_shape(record)
    except SchemaValidationError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "public_key_fingerprint": public_key_fingerprint(public_key),
        }

    if expected_domain not in SIGNATURE_DOMAINS:
        return {
            "valid": False,
            "errors": [f"unsupported expected v0.6 signature domain: {expected_domain!r}"],
            "public_key_fingerprint": public_key_fingerprint(public_key),
        }

    if record.get("signature_format") != SIGNATURE_RECORD_FORMAT:
        errors.append("unsupported v0.6 signature record format")
    if record.get("algorithm") != "Ed25519":
        errors.append("unsupported signature algorithm")

    fingerprint = public_key_fingerprint(public_key)
    if record.get("public_key_fingerprint") != fingerprint:
        errors.append("signature public key fingerprint mismatch")
    if expected_fingerprint is not None and fingerprint.lower() != expected_fingerprint.lower():
        errors.append("signer fingerprint does not match pinned expected fingerprint")

    payload = record.get("payload")
    canonical: bytes | None = None
    try:
        if not isinstance(payload, dict):
            raise V06SignatureError("signature payload must be an object")
        expected_envelope = signature_payload_envelope(
            expected_domain,
            payload.get("payload"),
        )
        if payload != expected_envelope:
            raise V06SignatureError(
                "signature payload envelope does not match expected format/domain"
            )
        canonical = canonicalize_jcs_bytes(expected_envelope)
        payload_hash = hashlib.sha256(canonical).hexdigest()
        if record.get("payload_sha256") != payload_hash:
            errors.append("signature payload SHA-256 mismatch")
    except (V06SignatureError, CryptoDomainError, CanonicalJSONError) as exc:
        errors.append(str(exc))

    if canonical is not None:
        try:
            raw_signature = base64.b64decode(record.get("signature", ""), validate=True)
            public_key.verify(raw_signature, canonical)
        except Exception as exc:
            errors.append(
                f"signature verification failed: {type(exc).__name__}: {exc}"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "public_key_fingerprint": fingerprint,
    }


def certificate_signature_payload_v06(certificate: dict[str, Any]) -> dict[str, Any]:
    from .certificate_v06 import verify_certificate_hashes_v06

    checked = verify_certificate_hashes_v06(certificate)
    if not checked["valid"]:
        raise V06SignatureError(
            f"refusing certificate signature payload for invalid v0.6 certificate: {checked['errors']}"
        )
    return {
        "spec_version": certificate.get("spec_version"),
        "checker_version": certificate.get("checker_version"),
        "canonical_json_profile": certificate.get("canonical_json_profile"),
        "semantic_hash_format": certificate.get("semantic_hash_format"),
        "integrity_hash_format": certificate.get("integrity_hash_format"),
        "subject": certificate.get("subject"),
        "semantic_hash": certificate.get("semantic_hash"),
        "integrity_hash": certificate.get("integrity_hash"),
    }


def sign_certificate_v06(
    certificate: dict[str, Any],
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    from .crypto_domains_v06 import CERTIFICATE_SIGNATURE_DOMAIN

    payload = certificate_signature_payload_v06(certificate)
    return sign_jcs_payload(CERTIFICATE_SIGNATURE_DOMAIN, payload, private_key)


def verify_certificate_signature_v06(
    certificate: dict[str, Any],
    record: dict[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    from .crypto_domains_v06 import CERTIFICATE_SIGNATURE_DOMAIN

    try:
        expected_payload = certificate_signature_payload_v06(certificate)
    except V06SignatureError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "public_key_fingerprint": public_key_fingerprint(public_key),
        }

    payload_envelope = record.get("payload")
    if not isinstance(payload_envelope, dict) or payload_envelope.get("payload") != expected_payload:
        return {
            "valid": False,
            "errors": ["signature payload does not match v0.6 certificate"],
            "public_key_fingerprint": public_key_fingerprint(public_key),
        }

    return verify_jcs_signature(
        record,
        public_key,
        expected_domain=CERTIFICATE_SIGNATURE_DOMAIN,
        expected_fingerprint=expected_fingerprint,
    )
