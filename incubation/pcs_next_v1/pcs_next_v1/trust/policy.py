"""Receiver-controlled acceptance policy — producer cannot authorize itself."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.canonical import canonical_hash, loads_strict
from ..core.errors import ErrorCode, PcsNextError
from ..core.schemas import POLICY_FORMAT, POLICY_SCHEMA, validate_schema


@dataclass(frozen=True)
class AcceptancePolicy:
    raw: dict[str, Any]
    content_hash: str

    @property
    def policy_id(self) -> str:
        return self.raw["policy_id"]

    @property
    def policy_version(self) -> str:
        return self.raw["policy_version"]

    @property
    def required_checks(self) -> list[str]:
        return list(self.raw["required_checks"])

    @property
    def pinned_signer_fingerprints(self) -> set[str]:
        return set(self.raw.get("pinned_signer_fingerprints", []))


def load_policy(path: str | Path) -> AcceptancePolicy:
    data = loads_strict(Path(path).read_bytes())
    if not isinstance(data, dict):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "policy must be object")
    return pin_policy(data)


def pin_policy(data: dict[str, Any]) -> AcceptancePolicy:
    validate_schema(data, POLICY_SCHEMA, label="acceptance_policy")
    if data["format"] != POLICY_FORMAT:
        raise PcsNextError(ErrorCode.POLICY_UNPINNED, "unknown policy format")
    if not data.get("fail_closed_unknown_versions", True):
        # Still allowed as a documented mode, but receiver must opt in explicitly.
        pass
    return AcceptancePolicy(raw=deepcopy(data), content_hash=canonical_hash(data))


def verify_policy_binding(
    *,
    receiver_policy: AcceptancePolicy,
    claimed_policy: dict[str, Any] | None,
    claimed_policy_hash: str | None,
) -> None:
    """Ensure certificate-embedded policy cannot substitute receiver policy."""
    if claimed_policy is None and claimed_policy_hash is None:
        return
    if claimed_policy is not None:
        claimed_hash = canonical_hash(claimed_policy)
        if claimed_policy_hash is not None and claimed_policy_hash != claimed_hash:
            raise PcsNextError(ErrorCode.POLICY_SUBSTITUTION, "embedded policy hash mismatch")
        if claimed_hash != receiver_policy.content_hash:
            # Producer-supplied policy is informational only; mismatch fails closed
            # unless versions are identical and hash matches.
            raise PcsNextError(
                ErrorCode.POLICY_SUBSTITUTION,
                "producer policy does not match receiver-pinned policy",
                details={
                    "receiver_hash": receiver_policy.content_hash,
                    "producer_hash": claimed_hash,
                },
            )
    elif claimed_policy_hash != receiver_policy.content_hash:
        raise PcsNextError(ErrorCode.POLICY_SUBSTITUTION, "producer policy hash mismatch")


def reject_producer_verdict(claimed_pass: Any) -> dict[str, Any]:
    """Document that producer PASS claims are ignored."""
    return {
        "producer_claimed_pass": claimed_pass,
        "receiver_action": "IGNORED",
        "error_code": ErrorCode.PRODUCER_VERDICT_IGNORED.value,
        "reason": "Untrusted recorded PASS values are never accepted as verification.",
    }


def check_version_compat(receiver: AcceptancePolicy, offered_protocol: str) -> None:
    if offered_protocol != receiver.raw["protocol_version"]:
        if receiver.raw.get("fail_closed_unknown_versions", True):
            raise PcsNextError(
                ErrorCode.POLICY_DOWNGRADE,
                "unsupported or unknown protocol version",
                details={
                    "receiver_protocol": receiver.raw["protocol_version"],
                    "offered_protocol": offered_protocol,
                },
            )
