from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical_json import canonicalize_jcs_bytes
from .receipt_contract_v06 import (
    V06ReceiptContractError,
    assert_verification_receipt_contract_v06,
    audit_verification_receipt_file_v06,
)
from .jsonio import StrictJSONError, strict_json_load
from .signing import public_key_fingerprint
from .verifier_io_v06 import V06VerifierIOError, load_public_key_v06


REVIEW_RECEIPT_SIGNATURE_FORMAT_V06 = "pcs-reviewer-receipt-ed25519-v1"
REVIEW_RECEIPT_SIGNATURE_DOMAIN_V06 = b"pcs-reviewer-receipt-ed25519-v1\0"


class V06ReceiptSignatureError(ValueError):
    pass


def _load_private_key(path: str | Path) -> Ed25519PrivateKey:
    try:
        raw = Path(path).read_bytes()
        key = serialization.load_pem_private_key(raw, password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise V06ReceiptSignatureError(
            f"cannot load reviewer Ed25519 private key: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise V06ReceiptSignatureError("reviewer private key is not Ed25519")
    return key


def _receipt_bytes(path: str | Path) -> bytes:
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise V06ReceiptSignatureError(
            f"cannot read verification receipt: {type(exc).__name__}: {exc}"
        ) from exc
    if len(raw) > 16 * 1024 * 1024:
        raise V06ReceiptSignatureError("verification receipt exceeds 16 MiB limit")
    return raw


def _receipt_object(path: str | Path) -> dict[str, Any]:
    try:
        obj = strict_json_load(path)
    except (OSError, StrictJSONError) as exc:
        raise V06ReceiptSignatureError(
            f"verification receipt is not strict JSON: {exc}"
        ) from exc
    if not isinstance(obj, dict):
        raise V06ReceiptSignatureError("verification receipt root must be an object")
    if not isinstance(obj.get("valid"), bool):
        raise V06ReceiptSignatureError("verification receipt lacks boolean valid")
    if not isinstance(obj.get("accepted"), bool):
        raise V06ReceiptSignatureError("verification receipt lacks boolean accepted")
    return obj


def receipt_signature_payload_v06(
    receipt: dict[str, Any],
    receipt_sha256: str,
) -> dict[str, Any]:
    reviewer_policy = receipt.get("reviewer_policy")
    policy_sha256 = (
        reviewer_policy.get("policy_sha256")
        if isinstance(reviewer_policy, dict)
        else None
    )
    return {
        "receipt_format": receipt.get("format"),
        "receipt_sha256": receipt_sha256,
        "bundle_sha256": receipt.get("bundle_sha256"),
        "certificate_semantic_hash": receipt.get("certificate_semantic_hash"),
        "certificate_integrity_hash": receipt.get("certificate_integrity_hash"),
        "normalized_index_semantic_hash": receipt.get(
            "normalized_index_semantic_hash"
        ),
        "policy_sha256": policy_sha256,
        "valid": receipt["valid"],
        "accepted": receipt["accepted"],
    }


def sign_verification_receipt_v06(
    receipt_path: str | Path,
    reviewer_private_key_path: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    output = Path(output_path).resolve()
    if output.exists() and not overwrite:
        raise V06ReceiptSignatureError(
            f"refusing to overwrite existing reviewer receipt signature: {output}"
        )

    raw = _receipt_bytes(receipt_path)
    receipt = _receipt_object(receipt_path)
    try:
        assert_verification_receipt_contract_v06(receipt)
    except V06ReceiptContractError as exc:
        raise V06ReceiptSignatureError(str(exc)) from exc
    receipt_sha256 = hashlib.sha256(raw).hexdigest()
    payload = receipt_signature_payload_v06(receipt, receipt_sha256)

    private_key = _load_private_key(reviewer_private_key_path)
    public_key = private_key.public_key()
    message = REVIEW_RECEIPT_SIGNATURE_DOMAIN_V06 + canonicalize_jcs_bytes(payload)
    signature = private_key.sign(message)

    record = {
        "signature_format": REVIEW_RECEIPT_SIGNATURE_FORMAT_V06,
        "algorithm": "Ed25519",
        "reviewer_public_key_fingerprint": public_key_fingerprint(public_key),
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonicalize_jcs_bytes(record))
    return record


def verify_verification_receipt_signature_v06(
    receipt_path: str | Path,
    signature_path: str | Path,
    reviewer_public_key_path: str | Path,
    *,
    expected_reviewer_fingerprint: str | None = None,
    bundle_path: str | Path | None = None,
    producer_public_key_path: str | Path | None = None,
    authority_path: str | Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        raw = _receipt_bytes(receipt_path)
        receipt = _receipt_object(receipt_path)
        contract = audit_verification_receipt_file_v06(
            receipt_path,
            bundle_path=bundle_path,
            producer_public_key_path=producer_public_key_path,
            authority_path=authority_path,
        )
        receipt_sha256 = hashlib.sha256(raw).hexdigest()
        expected_payload = receipt_signature_payload_v06(
            receipt,
            receipt_sha256,
        )

        try:
            record = strict_json_load(signature_path)
        except (OSError, StrictJSONError) as exc:
            raise V06ReceiptSignatureError(
                f"reviewer receipt signature is not strict JSON: {exc}"
            ) from exc
        if not isinstance(record, dict):
            raise V06ReceiptSignatureError(
                "reviewer receipt signature root must be an object"
            )

        if record.get("signature_format") != REVIEW_RECEIPT_SIGNATURE_FORMAT_V06:
            errors.append("unsupported reviewer receipt signature format")
        if record.get("algorithm") != "Ed25519":
            errors.append("unsupported reviewer receipt signature algorithm")
        if record.get("payload") != expected_payload:
            errors.append(
                "reviewer receipt signature payload does not match exact receipt"
            )

        try:
            public_key = load_public_key_v06(reviewer_public_key_path)
        except V06VerifierIOError as exc:
            raise V06ReceiptSignatureError(str(exc)) from exc
        fingerprint = public_key_fingerprint(public_key)
        recorded_fingerprint = record.get("reviewer_public_key_fingerprint")
        if recorded_fingerprint != fingerprint:
            errors.append("reviewer public key fingerprint mismatch")
        if (
            expected_reviewer_fingerprint is not None
            and fingerprint.lower() != expected_reviewer_fingerprint.lower()
        ):
            errors.append("reviewer fingerprint does not match expected reviewer")

        try:
            signature = base64.b64decode(
                record.get("signature", ""),
                validate=True,
            )
            message = (
                REVIEW_RECEIPT_SIGNATURE_DOMAIN_V06
                + canonicalize_jcs_bytes(expected_payload)
            )
            public_key.verify(signature, message)
        except Exception as exc:
            errors.append(
                "reviewer receipt signature verification failed: "
                f"{type(exc).__name__}: {exc}"
            )

        if not contract["valid"]:
            errors.extend(
                f"receipt contract: {error}" for error in contract["errors"]
            )
        return {
            "valid": not errors,
            "errors": errors,
            "contract_valid": contract["valid"],
            "contract_errors": contract["errors"],
            "contract_checks": contract.get("checks", {}),
            "signature_format": record.get("signature_format"),
            "reviewer_public_key_fingerprint": recorded_fingerprint,
            "receipt_sha256": receipt_sha256,
            "bundle_sha256": expected_payload["bundle_sha256"],
            "certificate_semantic_hash": expected_payload["certificate_semantic_hash"],
            "certificate_integrity_hash": expected_payload["certificate_integrity_hash"],
            "normalized_index_semantic_hash": expected_payload[
                "normalized_index_semantic_hash"
            ],
            "policy_sha256": expected_payload["policy_sha256"],
            "pcs_valid": expected_payload["valid"],
            "reviewer_accepted": expected_payload["accepted"],
        }
    except V06ReceiptSignatureError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "contract_valid": False,
            "contract_errors": [str(exc)],
            "contract_checks": {},
            "signature_format": None,
            "reviewer_public_key_fingerprint": None,
            "receipt_sha256": None,
            "bundle_sha256": None,
            "certificate_semantic_hash": None,
            "certificate_integrity_hash": None,
            "normalized_index_semantic_hash": None,
            "policy_sha256": None,
            "pcs_valid": None,
            "reviewer_accepted": None,
        }
