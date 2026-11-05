"""PCS signed human-interpretation confirmation: authenticated external act, NOT meaning proof.

A trusted caller must supply the approved Ed25519 public key independently of
proposal content. The signer and authorization workflow are outside the TCB of
this Python structural precheck; this verifier cannot prove human intent.
"""
from __future__ import annotations

import time
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .semantic_translation_v1 import SemanticError, canonical_bytes, check_translation, interpretation_digest, sha256

RECEIPT_FORMAT = "pcs-interpretation-confirmation-v1"
_DOMAIN = b"PCS_INTERPRETATION_CONFIRMATION_V1\x00"
_FIELDS = frozenset({"format", "claim_id", "interpretation_sha256", "registry_sha256",
                     "claim_ir_sha256", "approver", "issued_at", "expires_at", "nonce",
                     "signature_hex"})
_MAX_LIFETIME = 30 * 24 * 3600


def signing_payload(unsigned_receipt: Mapping[str, Any]) -> bytes:
    """Domain-separated canonical payload for independent signer implementation."""
    return _DOMAIN + canonical_bytes(unsigned_receipt)


def _bad(code: str, reason: str) -> None:
    raise SemanticError(code, "confirmation_receipt", reason)


def verify_confirmation_receipt(receipt: Any, *, approved_public_key_hex: str,
                                expected_interpretation_sha256: str, expected_registry_sha256: str,
                                expected_claim_id: str, expected_claim_ir_sha256: str | None = None,
                                now_epoch: int | None = None) -> str:
    """Return the receipt SHA after verifying signer, context and validity interval.

    This does not check the human behind the signature or what their words meant.
    """
    if not isinstance(receipt, dict) or set(receipt) != _FIELDS or receipt.get("format") != RECEIPT_FORMAT:
        _bad("CONFIRMATION_RECEIPT_MALFORMED", "unknown or incomplete receipt format")
    if (not isinstance(receipt["claim_id"], str) or receipt["claim_id"] != expected_claim_id
            or receipt["interpretation_sha256"] != expected_interpretation_sha256
            or receipt["registry_sha256"] != expected_registry_sha256
            or receipt["claim_ir_sha256"] != expected_claim_ir_sha256):
        _bad("CONFIRMATION_RECEIPT_BINDING_MISMATCH", "receipt is for a different claim, registry, interpretation or Claim IR")
    for field in ("interpretation_sha256", "registry_sha256"):
        value = receipt[field]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            _bad("CONFIRMATION_RECEIPT_MALFORMED", "invalid bound digest")
    if receipt["claim_ir_sha256"] is not None:
        v = receipt["claim_ir_sha256"]
        if not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
            _bad("CONFIRMATION_RECEIPT_MALFORMED", "invalid Claim IR digest")
    if not isinstance(receipt["approver"], str) or not 1 <= len(receipt["approver"]) <= 128:
        _bad("CONFIRMATION_RECEIPT_MALFORMED", "invalid approver identifier")
    nonce = receipt["nonce"]
    if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in "0123456789abcdef" for c in nonce):
        _bad("CONFIRMATION_RECEIPT_MALFORMED", "nonce must be 16 bytes in hex")
    start, expiry = receipt["issued_at"], receipt["expires_at"]
    if (type(start) is not int or type(expiry) is not int or start < 0 or expiry <= start
            or expiry - start > _MAX_LIFETIME):
        _bad("CONFIRMATION_RECEIPT_MALFORMED", "invalid receipt validity interval")
    clock = int(time.time()) if now_epoch is None else now_epoch
    if type(clock) is not int or not start <= clock <= expiry:
        _bad("CONFIRMATION_RECEIPT_EXPIRED", "receipt not valid at the trusted verification time")
    signature_hex = receipt["signature_hex"]
    if not isinstance(signature_hex, str) or len(signature_hex) != 128:
        _bad("CONFIRMATION_RECEIPT_MALFORMED", "expected 64-byte Ed25519 signature")
    if not isinstance(approved_public_key_hex, str) or len(approved_public_key_hex) != 64:
        _bad("CONFIRMATION_SIGNER_NOT_APPROVED", "missing exact approved Ed25519 public key")
    try:
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(approved_public_key_hex))
        signature = bytes.fromhex(signature_hex)
        unsigned = {k: v for k, v in receipt.items() if k != "signature_hex"}
        key.verify(signature, signing_payload(unsigned))
    except (ValueError, InvalidSignature, TypeError):
        _bad("CONFIRMATION_SIGNATURE_INVALID", "signature verification against approved key failed")
    return sha256(receipt)


def check_translation_with_confirmation(registry: Any, interpretation: Any, candidate: Any, *,
                                        approved_registry_sha256: str, confirmation_receipt: Any,
                                        approved_signer_public_key_hex: str,
                                        claim_ir: Mapping[str, Any] | None = None,
                                        now_epoch: int | None = None) -> dict[str, Any]:
    """Run the normal fail-closed checker, upgrading *only* receipt authenticity.

    It intentionally cannot grant Lean or PCS authority, even with valid signature.
    """
    digest = interpretation_digest(interpretation) if isinstance(interpretation, dict) else ""
    claim_id = interpretation.get("claim_id") if isinstance(interpretation, dict) else None
    ir_digest = claim_ir.get("claim_ir_sha256") if isinstance(claim_ir, dict) else None
    try:
        evidence_hash = verify_confirmation_receipt(
            confirmation_receipt, approved_public_key_hex=approved_signer_public_key_hex,
            expected_interpretation_sha256=digest,
            expected_registry_sha256=approved_registry_sha256,
            expected_claim_id=claim_id, expected_claim_ir_sha256=ir_digest, now_epoch=now_epoch)
    except (SemanticError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        result = check_translation(registry, interpretation, candidate,
                                   approved_registry_sha256=approved_registry_sha256,
                                   confirmed_interpretation_sha256=None, claim_ir=claim_ir)
        result["diagnostics"].append(exc.record() if isinstance(exc, SemanticError) else
                                     {"code": "CONFIRMATION_RECEIPT_MALFORMED", "path": "confirmation_receipt",
                                      "message": "receipt could not be validated"})
        result["decision"] = "REJECTED"
        result["confirmation_authenticated"] = False
        result["confirmation_receipt_sha256"] = None
        result["authoritative"] = False
        return result
    result = check_translation(registry, interpretation, candidate,
                               approved_registry_sha256=approved_registry_sha256,
                               confirmed_interpretation_sha256=digest, claim_ir=claim_ir)
    result["confirmation_authenticated"] = True
    result["confirmation_receipt_sha256"] = evidence_hash
    result["authoritative"] = False
    return result
