"""Reviewer-side pilot intake lock verification for v0.6 packages.

Producer-side ``attest_v06(..., intake_lock=...)`` is not sufficient: an
independent verifier must re-check the signed ``pilot-intake-lock.json`` member
against certificate semantics using only received bytes.

``frozen_at`` is producer-supplied metadata. It is **not** evidence of
out-of-band preregistration. Reviewers who need preregistration assurance must
supply ``expected_intake_semantic_hash`` from an independent channel.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .canonical_json import CanonicalJSONError, parse_jcs_json
from .intake import (
    INTAKE_LOCK_PACKAGE_MEMBER_V06,
    PilotIntakeError,
    assert_lock_matches_certificate,
    validate_lock,
)
from .jsonio import StrictJSONError


INTAKE_VERIFY_FORMAT_V06 = "pcs-intake-lock-verification-v06-v1"


class V06IntakeVerificationError(ValueError):
    pass


def _is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def verify_package_intake_lock_v06(
    *,
    certificate: Mapping[str, Any],
    package_files: Mapping[str, bytes],
    require_intake_lock: bool = False,
    expected_intake_semantic_hash: str | None = None,
) -> dict[str, Any]:
    """Verify signed intake-lock consistency for a reviewer-received package.

    Rules:
    - If ``require_intake_lock`` or ``expected_intake_semantic_hash`` is set, the
      signed member ``pilot-intake-lock.json`` must be present.
    - When present, the lock must validate, match certificate claim/assumption
      IDs/statements/assurance classes, and its semantic hash must equal the
      recomputed intake hash.
    - When ``expected_intake_semantic_hash`` is supplied out of band, it must equal
      the lock's ``intake_semantic_hash``.
    - ``frozen_at`` is recorded but never treated as preregistration proof.
    """
    errors: list[str] = []
    stages = {
        "member_present": False,
        "lock_valid": False,
        "certificate_consistent": False,
        "expected_hash_bound": expected_intake_semantic_hash is None,
    }

    if expected_intake_semantic_hash is not None:
        if not _is_hex64(expected_intake_semantic_hash):
            raise V06IntakeVerificationError(
                "expected_intake_semantic_hash must be a 64-character SHA-256 hex digest"
            )
        require_intake_lock = True

    raw = package_files.get(INTAKE_LOCK_PACKAGE_MEMBER_V06)
    present = isinstance(raw, (bytes, bytearray))
    stages["member_present"] = present

    if not present:
        if require_intake_lock:
            errors.append(
                f"required signed intake lock member missing: {INTAKE_LOCK_PACKAGE_MEMBER_V06}"
            )
            return {
                "format": INTAKE_VERIFY_FORMAT_V06,
                "valid": False,
                "required": True,
                "present": False,
                "errors": errors,
                "stages": stages,
                "intake_semantic_hash": None,
                "frozen_at": None,
                "preregistration_evidence": "none",
                "notes": [
                    "frozen_at is producer-supplied metadata and is not preregistration evidence",
                ],
            }
        return {
            "format": INTAKE_VERIFY_FORMAT_V06,
            "valid": True,
            "required": False,
            "present": False,
            "errors": [],
            "stages": stages,
            "intake_semantic_hash": None,
            "frozen_at": None,
            "preregistration_evidence": "none",
            "notes": [
                "no signed intake lock member; reviewer did not require one",
                "frozen_at is producer-supplied metadata and is not preregistration evidence",
            ],
        }

    try:
        parsed = parse_jcs_json(bytes(raw).decode("utf-8"))
        lock = validate_lock(parsed)
    except (UnicodeError, CanonicalJSONError, PilotIntakeError, StrictJSONError, TypeError) as exc:
        errors.append(f"signed intake lock is invalid: {type(exc).__name__}: {exc}")
        return {
            "format": INTAKE_VERIFY_FORMAT_V06,
            "valid": False,
            "required": bool(require_intake_lock),
            "present": True,
            "errors": errors,
            "stages": stages,
            "intake_semantic_hash": None,
            "frozen_at": None,
            "member_sha256": hashlib.sha256(bytes(raw)).hexdigest(),
            "preregistration_evidence": "none",
            "notes": [
                "frozen_at is producer-supplied metadata and is not preregistration evidence",
            ],
        }

    stages["lock_valid"] = True
    intake_hash = lock["intake_semantic_hash"]
    frozen_at = lock.get("frozen_at")

    try:
        assert_lock_matches_certificate(lock, dict(certificate))
        stages["certificate_consistent"] = True
    except PilotIntakeError as exc:
        errors.append(f"signed intake lock does not match certificate: {exc}")

    preregistration = "none"
    if expected_intake_semantic_hash is not None:
        if intake_hash.lower() != expected_intake_semantic_hash.lower():
            errors.append(
                "signed intake semantic hash does not match reviewer-owned "
                f"expected_intake_semantic_hash: actual={intake_hash} "
                f"expected={expected_intake_semantic_hash.lower()}"
            )
            stages["expected_hash_bound"] = False
        else:
            stages["expected_hash_bound"] = True
            preregistration = "reviewer_owned_expected_intake_semantic_hash"

    valid = not errors
    return {
        "format": INTAKE_VERIFY_FORMAT_V06,
        "valid": valid,
        "required": bool(require_intake_lock),
        "present": True,
        "errors": errors,
        "stages": stages,
        "intake_semantic_hash": intake_hash,
        "frozen_at": frozen_at,
        "member_sha256": hashlib.sha256(bytes(raw)).hexdigest(),
        "preregistration_evidence": preregistration,
        "notes": [
            "frozen_at is producer-supplied metadata and is not preregistration evidence",
            (
                "reviewer-owned expected_intake_semantic_hash provides an independent "
                "binding to a pre-agreed intake inventory"
                if preregistration != "none"
                else "without a reviewer-owned expected hash, only package-internal consistency is checked"
            ),
        ],
    }


def enforce_package_intake_lock_v06(
    verification: Mapping[str, Any],
    *,
    certificate: Mapping[str, Any] | None,
    package_files: Mapping[str, bytes],
    require_intake_lock: bool = False,
    expected_intake_semantic_hash: str | None = None,
) -> dict[str, Any]:
    """Conjoin intake-lock verification onto a package verification receipt."""
    result = dict(verification)
    stages = dict(result.get("stages") or {})

    # If the package already failed, still record intake status when checkable.
    if certificate is None:
        intake = {
            "format": INTAKE_VERIFY_FORMAT_V06,
            "valid": False,
            "required": bool(require_intake_lock or expected_intake_semantic_hash),
            "present": INTAKE_LOCK_PACKAGE_MEMBER_V06 in package_files,
            "errors": ["certificate unavailable for intake-lock verification"],
            "stages": {
                "member_present": INTAKE_LOCK_PACKAGE_MEMBER_V06 in package_files,
                "lock_valid": False,
                "certificate_consistent": False,
                "expected_hash_bound": expected_intake_semantic_hash is None,
            },
            "intake_semantic_hash": None,
            "frozen_at": None,
            "preregistration_evidence": "none",
            "notes": [
                "frozen_at is producer-supplied metadata and is not preregistration evidence",
            ],
        }
    else:
        intake = verify_package_intake_lock_v06(
            certificate=certificate,
            package_files=package_files,
            require_intake_lock=require_intake_lock,
            expected_intake_semantic_hash=expected_intake_semantic_hash,
        )

    stages["intake_lock"] = bool(intake.get("valid"))
    result["stages"] = stages
    result["intake_lock"] = intake

    if intake.get("valid") is not True and (
        require_intake_lock
        or expected_intake_semantic_hash is not None
        or intake.get("present") is True
    ):
        # Present-but-invalid locks always fail closed. Optional absence stays OK
        # unless the reviewer required a lock / expected hash.
        if intake.get("present") is True or require_intake_lock or expected_intake_semantic_hash:
            result["valid"] = False
            result["authoritative"] = False
            result["accepted"] = False
            if not result.get("failed_stage"):
                result["failed_stage"] = "intake_lock"
            errors = list(result.get("errors") or [])
            for item in intake.get("errors") or []:
                if item not in errors:
                    errors.append(item)
            result["errors"] = errors
    return result
