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
    return {
        "signature_format": SIGNATURE_RECORD_FORMAT,
        "algorithm": "Ed25519",
        "public_key_fingerprint": public_key_fingerprint(public_key),
        "payload_sha256": hashlib.sha256(canonical).hexdigest(),
        "payload": envelope,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_jcs_signature(
    record: dict[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_domain: str,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

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
