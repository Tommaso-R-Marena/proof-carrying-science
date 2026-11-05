"""Replay every retained scientific artifact through the fixed actual receiver.

Authentication of authorization intent is distinct from scientific validity today
and from authenticated historical verification occurrence. No supplied receipt,
cache or current-validity flag bypasses any required scientific check.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterator

from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY, RationalResult, checker_identity
from research.scientific_receiver_v1 import host


MAX_ENVELOPE_BYTES = 40000


class AuditRejected(ValueError):
    """A complete successful audit is unavailable; no partial prefix is upgraded."""


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _elapsed(started: float, budget: AuditBudget) -> float:
    elapsed = time.monotonic() - started
    if elapsed > budget.max_wall_seconds:
        raise AuditRejected("Whole-audit elapsed acceptance budget exceeded")
    return elapsed


@dataclass(frozen=True)
class AuditBudget:
    max_events: int = 32
    max_artifact_bytes: int = 8192
    max_total_artifact_bytes: int = 262144
    max_total_envelope_bytes: int = 1048576
    max_wall_seconds: float = 300

    def __post_init__(self):
        for name, maximum in (("max_events", 32), ("max_artifact_bytes", 8192),
                              ("max_total_artifact_bytes", 262144),
                              ("max_total_envelope_bytes", 1048576)):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= maximum:
                raise AuditRejected("Invalid hard-bounded audit budget: " + name)
        if (type(self.max_wall_seconds) not in (int, float)
                or not math.isfinite(self.max_wall_seconds)
                or not 0 < self.max_wall_seconds <= 600):
            raise AuditRejected("Invalid whole-audit elapsed acceptance budget")


@dataclass(frozen=True)
class CheckedArtifact:
    raw: bytes
    raw_sha256: str
    result: RationalResult
    verifier_response: bytes
    verifier_response_sha256: str
    signed_host_receipt_sha256: str
    ephemeral_host_public_key: str

    def to_dict(self) -> dict:
        return {"raw_hex": self.raw.hex(), "raw_sha256": self.raw_sha256,
                "result": {name: str(value) if isinstance(value, Fraction) else value
                           for name, value in vars(self.result).items()},
                "verifier_response": json.loads(self.verifier_response),
                "verifier_response_sha256": self.verifier_response_sha256,
                "signed_host_receipt_sha256": self.signed_host_receipt_sha256,
                "ephemeral_host_public_key": self.ephemeral_host_public_key}


@dataclass(frozen=True)
class AuditProgress:
    index: int
    generation: int
    total_artifacts: int
    artifact: CheckedArtifact
    wall_seconds: float
    complete_history: bool = field(default=False, init=False)


@dataclass(frozen=True)
class AuditReport:
    root_sha256: str
    operator_config_sha256: str
    anchor: history.Anchor
    envelope_sha256: tuple[str, ...]
    artifacts: tuple[CheckedArtifact, ...]
    wall_seconds: float
    retrospective_mathematical_validity: str = field(default="EXECUTED_PASS", init=False)
    authorization_history: str = field(default="AUTHENTICATED", init=False)
    historically_authenticated_verification: str = field(default="UNVERIFIED", init=False)
    empirical_validity: str = field(default="UNVERIFIED", init=False)
    scientific_acceptance: bool = field(default=False, init=False)
    production_authority: bool = field(default=False, init=False)

    @property
    def historical_math_valid(self) -> bool:
        """Retrospective replay only; not historical verification occurrence."""
        return True

    def as_dict(self) -> dict:
        return self.to_dict()

    def to_dict(self) -> dict:
        return {"format": "pcs-scientific-history-full-audit-v2",
                "root_sha256": self.root_sha256,
                "operator_config_sha256": self.operator_config_sha256,
                "anchor": {"generation": self.anchor.generation,
                           "incumbent_hex": self.anchor.incumbent.hex(),
                           "tip_hex": self.anchor.tip.hex(),
                           "chain_digest_hex": self.anchor.chain_digest.hex()},
                "envelope_sha256": list(self.envelope_sha256),
                "artifacts": [item.to_dict() for item in self.artifacts],
                "wall_seconds": self.wall_seconds,
                "retrospective_mathematical_validity": self.retrospective_mathematical_validity,
                "authorization_history": self.authorization_history,
                "historically_authenticated_verification": self.historically_authenticated_verification,
                "empirical_validity": self.empirical_validity,
                "scientific_acceptance": False, "production_authority": False,
                "resume_policy": "restart_from_checked_genesis; partial progress is not an audit cache",
                "trust_scope": "Fixed operator root/config, host/compiler/imports, Ed25519/SHA256 and storage execution trusted; retrospective rerun does not prove original verification occurred."}


def _scope(root: history.Root, anchor: history.Anchor, config: host.OperatorConfig,
           budget: AuditBudget) -> None:
    if type(root) is not history.Root or type(anchor) is not history.Anchor:
        raise AuditRejected("Exact receiver-owned root/anchor required")
    if type(config) is not host.OperatorConfig or type(budget) is not AuditBudget:
        raise AuditRejected("Exact fixed operator config/budget required")
    if root.policy != POLICY or root.checker != checker_identity(config):
        raise AuditRejected("Unsupported historical policy/checker configuration")
    if len(root.genesis_id) > 256 or len(root.genesis_incumbent) > budget.max_artifact_bytes:
        raise AuditRejected("Genesis resource bound")


def authenticate_material(root: history.Root, anchor: history.Anchor,
                          envelopes: tuple[bytes, ...], config: host.OperatorConfig,
                          *, budget: AuditBudget = AuditBudget()) -> tuple[history.Envelope, ...]:
    """Authenticate a complete retained sequence without claiming its science.

    The predecessor/CAS/signature adapter uses the pinned, unchanged V1 helper.
    This one explicit private dependency is fenced here; no old API is rewritten.
    """
    _scope(root, anchor, config, budget)
    if type(envelopes) is not tuple or len(envelopes) > budget.max_events:
        raise AuditRejected("Bounded immutable envelope tuple required")
    if (any(type(raw) is not bytes or len(raw) > MAX_ENVELOPE_BYTES for raw in envelopes)
            or sum(map(len, envelopes)) > budget.max_total_envelope_bytes):
        raise AuditRejected("Envelope byte budget exceeded")
    current, seen, decoded = history.initial(root), set(), []
    total = len(root.genesis_incumbent)
    if total > budget.max_total_artifact_bytes:
        raise AuditRejected("Aggregate scientific byte budget exceeded at genesis")
    for raw in envelopes:
        envelope = history.Envelope.decode(raw)
        p = envelope.payload
        if (p.certificate != b"" or len(p.event_id) > 256
                or len(p.candidate) > budget.max_artifact_bytes):
            raise AuditRejected("Reserved certificate/metadata/artifact bound")
        total += len(p.candidate)
        if total > budget.max_total_artifact_bytes:
            raise AuditRejected("Aggregate scientific byte budget exceeded")
        current = history._advance(root, current, envelope, seen)
        seen.add(p.event_id)
        decoded.append(envelope)
    if current != anchor:
        raise AuditRejected("Retained sequence does not reconstruct exact external checkpoint")
    return tuple(decoded)


def _check_artifact(raw: bytes, root: history.Root, config: host.OperatorConfig,
                    service: host.ReceiverService) -> CheckedArtifact:
    envelope = service.verify_bytes(raw)
    try:
        receipt = envelope["receipt"]
        response = receipt["verifier_response"]
        if (not host.replay_signed_receipt(envelope, service.public_key_hex)
                or receipt["accepted"] is not True or receipt["errors"] != []
                or receipt["raw_hex"] != raw.hex() or receipt["raw_sha256"] != digest(raw)
                or receipt["raw_bytes"] != len(raw)
                or receipt["operator_config_sha256"] != root.checker.hex()
                or canonical(receipt["operator_identity"]) != canonical(config.identity())
                or receipt["checks"] != {"pins_before": True, "pins_after": True,
                                         "response_checked": True}
                or receipt["scientific_acceptance"] is not False
                or receipt["production_authority"] is not False):
            raise AuditRejected("Actual scientific check or exact byte/profile binding failed")
        # The unchanged host's own response adapter compares exact canonical
        # result fields against the independent Python scientific reference.
        host._validated_response(raw, canonical(response) + b"\n")
        if response["accepted"] is not True or response["error"] != "":
            raise AuditRejected("Scientific contract rejected")
        result = response["result"]
        rational = tuple(Fraction(result[name]) for name in
                         ("finalA", "finalB", "total", "lowerA", "upperA", "lowerB", "upperB"))
        values = RationalResult(*rational, result["stepCount"], result["unitCode"], result["physical"])
        encoded = canonical(response)
        return CheckedArtifact(raw, digest(raw), values, encoded, digest(encoded),
                               digest(canonical(envelope)), service.public_key_hex)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        if isinstance(exc, AuditRejected):
            raise
        raise AuditRejected("Malformed or scientifically rejected exact response") from exc


def verify_artifact(raw: bytes, root: history.Root, config: host.OperatorConfig) -> CheckedArtifact:
    """Actual single-artifact mathematical replay; not historical occurrence.

    No verifier callback/service can be supplied. Operator configuration is an
    explicit bootstrap input, and must match the receiver-owned fixed root.
    """
    if type(root) is not history.Root:
        raise AuditRejected("Exact receiver-owned root required")
    _scope(root, history.initial(root), config, AuditBudget())
    if type(raw) is not bytes or len(raw) > host.MAX_BYTES:
        raise AuditRejected("Immutable bounded scientific bytes required")
    return _check_artifact(raw, root, config, host.ReceiverService(config))


def audit_material_events(root: history.Root, anchor: history.Anchor,
                          envelopes: tuple[bytes, ...], config: host.OperatorConfig,
                          *, budget: AuditBudget = AuditBudget()) -> Iterator[AuditProgress | AuditReport]:
    """Stream checked-prefix observations; only the final item is a full audit.

    Restart always rechecks genesis and every event. Progress is informative,
    cannot authorize a prefix or serve as a trusted incremental cache.
    """
    started = time.monotonic()
    decoded = authenticate_material(root, anchor, envelopes, config, budget=budget)
    _elapsed(started, budget)
    service = host.ReceiverService(config)
    results = []
    raws = (root.genesis_incumbent, *(e.payload.candidate for e in decoded))
    for index, raw in enumerate(raws):
        _elapsed(started, budget)
        result = _check_artifact(raw, root, config, service)
        elapsed = _elapsed(started, budget)
        results.append(result)
        yield AuditProgress(index, root.genesis_generation + index, len(raws), result, elapsed)
    elapsed = _elapsed(started, budget)
    yield AuditReport(digest(root.encode()), root.checker.hex(), anchor,
                      tuple(digest(raw) for raw in envelopes), tuple(results),
                      elapsed)


def audit_material(root: history.Root, anchor: history.Anchor,
                   envelopes: tuple[bytes, ...], config: host.OperatorConfig,
                   *, budget: AuditBudget = AuditBudget()) -> AuditReport:
    """Authenticate and freshly check complete exact retained material."""
    last = None
    for last in audit_material_events(root, anchor, envelopes, config, budget=budget):
        pass
    if type(last) is not AuditReport:
        raise AuditRejected("Incomplete scientific replay")
    return last


def audit_history(path: Path, root: history.Root, anchor: history.Anchor,
                  config: host.OperatorConfig, *, budget: AuditBudget = AuditBudget()) -> AuditReport:
    """Audit exact retained SQLite history, rejecting changes during replay."""
    started = time.monotonic()
    _scope(root, anchor, config, budget)
    reader = history.History(path, root, anchor)
    snapshot = reader.snapshot()
    material = tuple(e.encode() for e in snapshot.envelopes)
    elapsed = _elapsed(started, budget)
    remaining = replace(budget, max_wall_seconds=budget.max_wall_seconds - elapsed)
    report = audit_material(root, anchor, material, config, budget=remaining)
    after = reader.snapshot()
    if after != snapshot:
        raise AuditRejected("Retained history changed during scientific audit")
    return replace(report, wall_seconds=_elapsed(started, budget))
