"""Ed25519-signed independent receipt helpers (receiver-pinned)."""

from __future__ import annotations

from typing import Any

from ..core.canonical import canonicalize, canonical_hash
from ..core.errors import ErrorCode, PcsNextError
from .crypto import generate_keypair, require_pinned_signer, sign_bytes, verify_bytes
from .policy import AcceptancePolicy


def receipt_message(lock_hash: str, bundle_hash: str) -> bytes:
    return canonicalize({"lock_hash": lock_hash, "bundle_hash": bundle_hash})


def sign_package_hashes(
    *,
    lock_hash: str,
    bundle_hash: str,
    private_der: bytes,
) -> bytes:
    return sign_bytes(private_der, receipt_message(lock_hash, bundle_hash))


def verify_signed_package(
    *,
    lock_hash: str,
    bundle_hash: str,
    public_der: bytes,
    signature: bytes,
    policy: AcceptancePolicy,
) -> dict[str, Any]:
    fp = require_pinned_signer(public_der, policy.pinned_signer_fingerprints)
    verify_bytes(public_der, receipt_message(lock_hash, bundle_hash), signature)
    return {
        "ok": True,
        "signer_fingerprint": fp,
        "message_hash": canonical_hash({"lock_hash": lock_hash, "bundle_hash": bundle_hash}),
    }


def mint_demo_signer() -> dict[str, Any]:
    """Research/demo only — ephemeral keypair."""
    priv, pub, fp = generate_keypair()
    return {"private_der": priv, "public_der": pub, "fingerprint": fp}


def detect_signature_faults(
    *,
    lock_hash: str,
    bundle_hash: str,
    public_der: bytes,
    signature: bytes,
    policy: AcceptancePolicy,
) -> str:
    """Return 'ok' or a fault class string."""
    try:
        verify_signed_package(
            lock_hash=lock_hash,
            bundle_hash=bundle_hash,
            public_der=public_der,
            signature=signature,
            policy=policy,
        )
        return "ok"
    except PcsNextError as exc:
        if exc.code == ErrorCode.SIGNATURE_INVALID:
            return "signature_invalid"
        if exc.code == ErrorCode.SIGNER_UNPINNED:
            return "signer_not_pinned"
        return f"error:{exc.code.value}"
