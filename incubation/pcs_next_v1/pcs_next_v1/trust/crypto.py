"""Ed25519 signing helpers using the cryptography library."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from ..core.errors import ErrorCode, PcsNextError


@dataclass(frozen=True)
class KeyPin:
    public_der: bytes
    fingerprint: str


def fingerprint_public_der(public_der: bytes) -> str:
    return hashlib.sha256(public_der).hexdigest()


def generate_keypair() -> tuple[bytes, bytes, str]:
    """Return (private_der, public_der, fingerprint). Research/demo only."""
    priv = Ed25519PrivateKey.generate()
    priv_der = priv.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_der = priv.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_der, pub_der, fingerprint_public_der(pub_der)


def sign_bytes(private_der: bytes, message: bytes) -> bytes:
    priv = serialization.load_der_private_key(private_der, password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise PcsNextError(ErrorCode.SIGNATURE_INVALID, "private key is not Ed25519")
    return priv.sign(message)


def verify_bytes(public_der: bytes, message: bytes, signature: bytes) -> None:
    try:
        pub = serialization.load_der_public_key(public_der)
    except ValueError as exc:
        raise PcsNextError(ErrorCode.SIGNATURE_INVALID, "invalid public key DER") from exc
    if not isinstance(pub, Ed25519PublicKey):
        raise PcsNextError(ErrorCode.SIGNATURE_INVALID, "public key is not Ed25519")
    try:
        pub.verify(signature, message)
    except InvalidSignature as exc:
        raise PcsNextError(ErrorCode.SIGNATURE_INVALID, "signature verification failed") from exc


def require_pinned_signer(public_der: bytes, pinned: set[str]) -> str:
    fp = fingerprint_public_der(public_der)
    if fp not in pinned:
        raise PcsNextError(
            ErrorCode.SIGNER_UNPINNED,
            "signer fingerprint not in receiver trust pin set",
            details={"fingerprint": fp},
        )
    return fp
