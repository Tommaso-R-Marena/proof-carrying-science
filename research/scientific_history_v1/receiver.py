"""Join unchanged scientific-process and authorization-history research APIs.

An admitted artifact is a bounded mathematical contract, not empirical scientific
acceptance, model-quality improvement, neural promotion or production authority.
The operator config, host/OS, external root/anchor and cache artifacts stay trusted.
"""

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from threading import RLock

from research.authorization_history_v1 import history
from research.scientific_receiver_v1 import host, reference


POLICY = b"PCS-SCI-HISTORY-V1"


class IntakeRejected(ValueError):
    """No new admitted snapshot is returned after any check/commit failure."""


def checker_identity(config: host.OperatorConfig) -> bytes:
    if type(config) is not host.OperatorConfig:
        raise IntakeRejected("Fixed operator configuration required")
    return hashlib.sha256(host._canonical(config.identity())).digest()


@dataclass(frozen=True)
class RationalResult:
    final_a: Fraction
    final_b: Fraction
    total: Fraction
    lower_a: Fraction
    upper_a: Fraction
    lower_b: Fraction
    upper_b: Fraction
    step_count: int
    unit_code: bool
    physical: bool


@dataclass(frozen=True)
class AdmittedArtifactSnapshot:
    anchor: history.Anchor
    candidate: bytes
    result: RationalResult
    raw_sha256: str
    checker: bytes
    scientific_acceptance: bool = field(default=False, init=False)
    production_authority: bool = field(default=False, init=False)
    promotion_authority: bool = field(default=False, init=False)
    historical_scientific_audit: bool = field(default=False, init=False)


class ScientificReceivingLedger:
    """Operator supplies trust inputs once; submitters supply only immutable bytes.

    current() audits the retained external anchor against the DB before returning
    cached, immutable checked bytes/results. It does not trust a historical host
    receipt. Construction always reexecutes the fixed scientific verifier on the
    authenticated incumbent. Publishing returned anchors is a separate obligation.
    Private Python attributes are interface organization, not a security root.
    """

    def __init__(self, path: Path, root: history.Root, external_anchor: history.Anchor,
                 config: host.OperatorConfig):
        identity = checker_identity(config)
        if type(root) is not history.Root or root.policy != POLICY or root.checker != identity:
            raise IntakeRejected("Root must pin this policy and exact operator profile")
        self._root, self._config = root, config
        self._identity = host._canonical(config.identity())
        self._lock = RLock()
        self._history = history.History(path, root, external_anchor)
        self._service = host.ReceiverService(config)  # No requester verifier/callback.
        checked = self._verify(external_anchor.incumbent)
        self._current = self._snapshot(external_anchor, external_anchor.incumbent, checked)

    def _verify(self, raw: bytes) -> RationalResult:
        envelope = self._service.verify_bytes(raw)
        receipt = envelope["receipt"]
        response = receipt["verifier_response"]
        digest = hashlib.sha256(raw).hexdigest()
        if (not host.replay_signed_receipt(envelope, self._service.public_key_hex)
                or receipt["accepted"] is not True or receipt["errors"] != []
                or receipt["raw_hex"] != raw.hex() or receipt["raw_sha256"] != digest
                or receipt["raw_bytes"] != len(raw)
                or receipt["operator_config_sha256"] != self._root.checker.hex()
                or host._canonical(receipt["operator_identity"]) != self._identity
                or receipt["checks"] != {"pins_before": True, "pins_after": True, "response_checked": True}
                or receipt["scientific_acceptance"] is not False
                or receipt["production_authority"] is not False
                or type(response) is not dict):
            raise IntakeRejected("Fresh mathematical verification/byte/profile binding failed")
        # Repeat the unchanged host's exact response/result/echo validation. The
        # result is then copied into frozen typed values, not a mutable receipt.
        try:
            host._validated_response(raw, host._canonical(response) + b"\n")
            decision = reference.assess(raw)
            if response["accepted"] is not True or response["error"] != "" or not decision.accepted:
                raise IntakeRejected("Scientific contract rejected")
            result = response["result"]
            rationals = tuple(Fraction(result[name]) for name in (
                "finalA", "finalB", "total", "lowerA", "upperA", "lowerB", "upperB"))
            return RationalResult(*rationals, result["stepCount"], result["unitCode"], result["physical"])
        except (host.HostRejected, KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise IntakeRejected("Exact mathematical response/result binding failed") from exc

    def _snapshot(self, anchor, raw, checked):
        return AdmittedArtifactSnapshot(anchor, raw, checked, hashlib.sha256(raw).hexdigest(),
                                        self._root.checker)

    def _audit_current(self):
        audited = self._history.snapshot()
        if (audited.anchor != self._current.anchor
                or audited.anchor.incumbent != self._current.candidate):
            raise IntakeRejected("Cached checked artifact differs from authenticated current state")
        return audited

    def current(self) -> AdmittedArtifactSnapshot:
        with self._lock:
            self._audit_current()
            return self._current

    def submit(self, signed_envelope: bytes) -> AdmittedArtifactSnapshot:
        if type(signed_envelope) is not bytes:
            raise IntakeRejected("Only immutable signed envelope bytes are accepted")
        captured = signed_envelope  # One immutable snapshot for decode and commit.
        envelope = history.Envelope.decode(captured)
        payload = envelope.payload
        if (payload.certificate != b"" or (payload.authority, payload.witness, payload.policy, payload.checker)
                != (self._root.authority, self._root.witness, POLICY, self._root.checker)):
            raise IntakeRejected("Wrong scope or nonempty reserved auxiliary certificate")
        with self._lock:
            audited = self._audit_current()
            # Cheap read-only authorization/CAS preflight avoids launching Lean
            # for unauthenticated or already stale requests. Append below still
            # rechecks independently under its SQLite transaction after Lean.
            history._advance(self._root, audited.anchor, envelope,
                             {old.payload.event_id for old in audited.envelopes})
            checked = self._verify(payload.candidate)
            anchor = self._history.append(captured)  # Actual signatures + CAS; failures propagate.
            snapshot = self._snapshot(anchor, payload.candidate, checked)
            self._current = snapshot  # No cache update or successful return before COMMIT.
            return snapshot
