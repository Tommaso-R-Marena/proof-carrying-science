"""Bounded proposal-only control demo, with an explicit runtime enforcement boundary.

Untrusted input is JSON data. Only the trusted constructor supplies the effect.
This is not a sandbox for arbitrary Python code or a proof of observation fidelity.
"""
from __future__ import annotations

import hashlib
from threading import RLock
from typing import Any, Callable

from .canonical_json import canonicalize_jcs_bytes


def digest(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


class ControlMonitor:
    def __init__(self, policy: dict, effect: Callable[[int], None]):
        if type(policy) is not dict or set(policy) != {"format", "operation", "max_actions", "max_value"}:
            raise ValueError("invalid policy")
        if (policy["format"] != "pcs-control-policy-v1" or policy["operation"] != "write_result" or
            type(policy["max_actions"]) is not int or not 1 <= policy["max_actions"] <= 10 or
            type(policy["max_value"]) is not int or not 0 <= policy["max_value"] <= 255):
            raise ValueError("unsupported bounded policy")
        self.policy = dict(policy)
        self.policy_sha256 = digest(self.policy)
        self._lock = RLock()
        self._effect = effect
        self._active = True
        self._seen: set[str] = set()
        self._executions = 0
        self.audit: list[dict] = []

    def revoke(self) -> None:
        with self._lock:
            self._active = False

    def submit(self, proposal: Any) -> dict:
        with self._lock:
            return self._submit(proposal)

    def _submit(self, proposal: Any) -> dict:
        reason = "REJECTED_SCHEMA"
        nonce = None
        if type(proposal) is dict and set(proposal) == {"nonce", "operation", "value", "policy_sha256"}:
            nonce = proposal["nonce"]
            if type(nonce) is not str or not 1 <= len(nonce) <= 64:
                reason = "REJECTED_NONCE"
            elif not self._active:
                reason = "REJECTED_REVOKED"
            elif nonce in self._seen:
                reason = "REJECTED_REPLAY"
            elif proposal["policy_sha256"] != self.policy_sha256:
                reason = "REJECTED_POLICY_MISMATCH"
            elif proposal["operation"] != self.policy["operation"]:
                reason = "REJECTED_OPERATION"
            elif type(proposal["value"]) is not int or not 0 <= proposal["value"] <= self.policy["max_value"]:
                reason = "REJECTED_VALUE"
            elif self._executions >= self.policy["max_actions"]:
                reason = "REJECTED_BUDGET"
            else:
                # Consume the nonce and budget before the effect. A failed effect
                # may have partial consequences and cannot be safely retried.
                self._seen.add(nonce)
                self._executions += 1
                try:
                    self._effect(proposal["value"])
                    reason = "EXECUTED"
                except Exception:
                    reason = "EFFECT_FAILED_POSSIBLY_PARTIAL"
        previous = self.audit[-1]["event_sha256"] if self.audit else self.policy_sha256
        record = {"sequence": len(self.audit), "state": reason,
                  "nonce": nonce if type(nonce) is str and len(nonce) <= 64 else None,
                  "policy_sha256": self.policy_sha256, "previous_sha256": previous,
                  "pcs_authority": False, "lean_kernel_checked": False}
        record["event_sha256"] = digest(record)
        self.audit.append(record)
        return dict(record)


def consistent_audit(events: list[dict], policy_sha256: str) -> bool:
    """Check hash-chain consistency, not identity, signatures, or external truth."""
    previous = policy_sha256
    for index, event in enumerate(events):
        core = {key: value for key, value in event.items() if key != "event_sha256"}
        if (event.get("sequence") != index or event.get("policy_sha256") != policy_sha256 or
            event.get("previous_sha256") != previous or digest(core) != event.get("event_sha256")):
            return False
        previous = event["event_sha256"]
    return True
