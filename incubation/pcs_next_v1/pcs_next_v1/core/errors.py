"""Stable error codes for fail-closed boundaries."""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    SCHEMA_INVALID = "PCS_NEXT_SCHEMA_INVALID"
    CANONICAL_INVALID = "PCS_NEXT_CANONICAL_INVALID"
    POLICY_UNPINNED = "PCS_NEXT_POLICY_UNPINNED"
    POLICY_SUBSTITUTION = "PCS_NEXT_POLICY_SUBSTITUTION"
    POLICY_DOWNGRADE = "PCS_NEXT_POLICY_DOWNGRADE"
    PRODUCER_VERDICT_IGNORED = "PCS_NEXT_PRODUCER_VERDICT_IGNORED"
    HASH_MISMATCH = "PCS_NEXT_HASH_MISMATCH"
    SIGNATURE_INVALID = "PCS_NEXT_SIGNATURE_INVALID"
    SIGNER_UNPINNED = "PCS_NEXT_SIGNER_UNPINNED"
    STATE_ILLEGAL = "PCS_NEXT_STATE_ILLEGAL"
    UNSUPPORTED_FRAGMENT = "PCS_NEXT_UNSUPPORTED_FRAGMENT"
    AMBIGUOUS_CLAIM = "PCS_NEXT_AMBIGUOUS_CLAIM"
    ADVERSARIAL_PACKAGE = "PCS_NEXT_ADVERSARIAL_PACKAGE"
    RESOURCE_LIMIT = "PCS_NEXT_RESOURCE_LIMIT"
    SANDBOX_UNAVAILABLE = "PCS_NEXT_SANDBOX_UNAVAILABLE"
    AUTHORITY_IDENTITY = "PCS_NEXT_AUTHORITY_IDENTITY"
    PATH_ESCAPE = "PCS_NEXT_PATH_ESCAPE"
    NONINTERFERENCE = "PCS_NEXT_NONINTERFERENCE"
    FORMAL_FAILED = "PCS_NEXT_FORMAL_FAILED"
    REPLAY_STALE = "PCS_NEXT_REPLAY_STALE"
    GENERATION_CONFLICT = "PCS_NEXT_GENERATION_CONFLICT"
    INTERNAL = "PCS_NEXT_INTERNAL"


class PcsNextError(Exception):
    def __init__(self, code: ErrorCode | str, message: str, *, details: dict | None = None):
        self.code = ErrorCode(code) if isinstance(code, str) else code
        self.message = message
        self.details = dict(details or {})
        super().__init__(f"{self.code.value}: {message}")

    def to_dict(self) -> dict:
        return {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
        }
