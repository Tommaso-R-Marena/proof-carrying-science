"""Staged local commitment with a separately executable pinned witness.

PREPARE -> local SQLite COMMIT -> witness FINALIZE -> nonce-fresh eligibility.
These are separate durable transitions, never a distributed atomic transaction.
Only research artifact intake is implemented; no empirical or serving deployment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from research.authorization_history_v1 import history
from research.scientific_receiver_v1 import host
from research.scientific_history_v2.audit import (
    AuditBudget, AuditReport, CheckedArtifact, audit_history, audit_material,
    authenticate_material,
)
from research.scientific_witness_v1.client import WitnessClient
from research.scientific_witness_v1.protocol import (
    canonical, digest, decode_anchor, checked_intent, advance, verify_statement,
)


class AuthorityRejected(ValueError):
    """No fully witnessed eligible snapshot is available."""


@dataclass(frozen=True)
class EligibleSnapshot:
    anchor: history.Anchor
    artifact: CheckedArtifact
    fresh_witness_view: bytes
    mathematical_status: str = field(default="EXECUTED_AND_REPRODUCED", init=False)
    historical_math_status: str = field(default="HISTORICALLY_REPLAYED", init=False)
    witness_authentication: str = field(default="AUTHENTICATED", init=False)
    independent_administration: str = field(default="UNVERIFIED", init=False)
    empirical_validity: str = field(default="UNVERIFIED", init=False)
    scientific_acceptance: bool = field(default=False, init=False)
    production_authority: bool = field(default=False, init=False)
    model_promotion_authority: bool = field(default=False, init=False)


def _bootstrap(root, config, witness):
    if (type(root) is not history.Root or type(config) is not host.OperatorConfig
            or type(witness) is not WitnessClient
            or witness.root != root or witness.config != config):
        raise AuthorityRejected("Fixed operator root/profile and pinned network witness required")


def _permanent_receipt(response, kind, raw, root, config, witness):
    payload = verify_statement(response["receipt"], witness.witness_public_key,
                               root, config, kind=kind)
    if payload.get("intent_sha256") != digest(raw):
        raise AuthorityRejected("Witness receipt is for a different captured intent")
    return payload


class ScientificAuthority:
    """Operator bootstrap is separate from requester-supplied signed bytes.

    Construction replays ALL local historical science. current() obtains a fresh
    witness view and reaudits local authentication; it returns captured checked
    bytes only. Private attributes/frozen objects are not a hostile-host boundary.
    """
    def __init__(self, path: Path, root: history.Root, anchor: history.Anchor,
                 config: host.OperatorConfig, witness: WitnessClient,
                 *, budget: AuditBudget = AuditBudget()):
        _bootstrap(root, config, witness)
        self.path, self.root, self.config, self.witness = Path(path), root, config, witness
        self.budget = budget
        self._lock = RLock()
        self._history = history.History(self.path, root, anchor)
        self._audit = audit_history(self.path, root, anchor, config, budget=budget)
        self._artifact = self._audit.artifacts[-1]
        self.current()  # Pending/local-only/ahead/rolled-back state cannot open eligible.

    def current(self) -> EligibleSnapshot:
        with self._lock:
            local = self._history.snapshot()
            evidence = self.witness.checkpoint_evidence()  # Own fresh nonce + pinned signature.
            view = evidence["statement"]["payload"]
            if (view.get("pending") is not None
                    or decode_anchor(view["anchor"]) != local.anchor
                    or self._audit.anchor != local.anchor
                    or self._artifact.raw != local.anchor.incumbent):
                raise AuthorityRejected("No matching finalized local/witness checkpoint")
            # The full signed statement remains independently authenticatable;
            # a third party still needs its OWN fresh challenge for currentness.
            return EligibleSnapshot(local.anchor, self._artifact, canonical(evidence))

    def submit(self, signed_intent: bytes) -> EligibleSnapshot:
        if type(signed_intent) is not bytes:
            raise AuthorityRejected("Only captured immutable signed intent bytes are accepted")
        captured = signed_intent
        envelope = checked_intent(captured)
        with self._lock:
            self.current()
            old = self._history.snapshot()
            # Reject wrong signatures/stale CAS before the witness launches Lean.
            next_anchor = advance(self.root, old.anchor, envelope,
                                  {e.payload.event_id for e in old.envelopes})
            authenticate_material(self.root, next_anchor,
                                  tuple(e.encode() for e in old.envelopes) + (captured,),
                                  self.config, budget=self.budget)
            prepared = self.witness.prepare(captured)
            _permanent_receipt(prepared, "prepared", captured,
                               self.root, self.config, self.witness)
            # Exact original intent; final CAS independently repeats auth/replay.
            new_anchor = self._history.append(captured)
            finalized = self.witness.finalize(digest(captured))
            _permanent_receipt(finalized, "finalized", captured,
                               self.root, self.config, self.witness)
            # Recheck the complete committed local history, not an inherited flag.
            self._audit = audit_history(self.path, self.root, new_anchor,
                                        self.config, budget=self.budget)
            self._artifact = self._audit.artifacts[-1]
            return self.current()  # Never infer currentness from an old receipt.


@dataclass(frozen=True)
class RecoveryResult:
    anchor: history.Anchor
    audit: AuditReport
    materialized_finalized_events: int
    resolved_pending: bool
    new_authorization_created: bool = field(default=False, init=False)


def recover(path: Path, root: history.Root, config: host.OperatorConfig,
            witness: WitnessClient, *, budget: AuditBudget = AuditBudget(),
            resolve_pending: bool = False) -> RecoveryResult:
    """Recover only exact independently retained signed material or refuse.

    No missing database is created. Find an exact authenticated local prefix of
    fresh witness history (or its unique pending successor); refuse all other
    forks/suffixes. Re-materializing a witnessed record is not new authorization.
    Explicit resolve_pending permits the exact already-reserved signed intent,
    after actual retrospective science. It never substitutes another candidate.
    """
    _bootstrap(root, config, witness)
    material = witness.export()
    target = decode_anchor(material["anchor"])
    if (type(material.get("envelopes")) is not list
            or len(material["envelopes"]) > budget.max_events):
        raise AuthorityRejected("Bounded complete witness history required")
    from research.scientific_witness_v1.protocol import unhex
    raws = tuple(unhex(raw) for raw in material["envelopes"])
    authenticated = authenticate_material(root, target, raws, config, budget=budget)
    anchors, current, seen = [history.initial(root)], history.initial(root), set()
    for envelope in authenticated:
        current = advance(root, current, envelope, seen)
        seen.add(envelope.payload.event_id)
        anchors.append(current)
    pending = material.get("pending")
    pending_raw, pending_next = None, None
    if pending is not None:
        pending_raw = unhex(pending["intent"])
        if digest(pending_raw) != pending["intent_sha256"]:
            raise AuthorityRejected("Changed pending witness intent")
        pending_envelope = checked_intent(pending_raw)
        pending_next = advance(root, target, pending_envelope, seen)
        if pending_next != decode_anchor(pending["next_anchor"]):
            raise AuthorityRejected("Pending witness transition disagrees with exact intent")
        if not resolve_pending:
            raise AuthorityRejected("Pending transition requires explicit exact-intent recovery")
        # Also enforces aggregate/event budgets including reserved successor.
        complete = audit_material(root, pending_next, raws + (pending_raw,),
                                  config, budget=budget)
    else:
        complete = audit_material(root, target, raws, config, budget=budget)
    candidates = [(a, raws[:i]) for i, a in enumerate(anchors)]
    if pending_next is not None:
        candidates.append((pending_next, raws + (pending_raw,)))
    matched = []
    for anchor, prefix in candidates:
        try:
            store = history.History(Path(path), root, anchor)
            if tuple(e.encode() for e in store.snapshot().envelopes) == prefix:
                matched.append((store, len(prefix)))
        except history.Rejected:
            continue
    if len(matched) != 1:
        raise AuthorityRejected("Local store is not one exact known witnessed prefix/successor")
    store, length = matched[0]
    materialized = 0
    for raw in raws[length:]:
        store.append(raw)
        materialized += 1
    if pending_raw is not None:
        if store.expected_anchor == target:
            prepared = witness.prepare(pending_raw)  # Idempotent exact reserved intent.
            _permanent_receipt(prepared, "prepared", pending_raw, root, config, witness)
            store.append(pending_raw)
        elif store.expected_anchor != pending_next:
            raise AuthorityRejected("Ambiguous pending local outcome")
        finalized = witness.finalize(digest(pending_raw))
        _permanent_receipt(finalized, "finalized", pending_raw, root, config, witness)
        target = pending_next
    view = witness.checkpoint()
    if view.get("pending") is not None or decode_anchor(view["anchor"]) != target:
        raise AuthorityRejected("Witness changed during recovery; no eligible result")
    final_local = history.History(Path(path), root, target).snapshot()
    final_raws = raws + ((pending_raw,) if pending_raw is not None else ())
    if tuple(e.encode() for e in final_local.envelopes) != final_raws:
        raise AuthorityRejected("Recovered local bytes differ from the freshly checked sequence")
    # Reuse only this invocation's immutable actual scientific checks, after
    # exact-byte authenticated DB comparison; no supplied audit cache is accepted.
    return RecoveryResult(target, complete, materialized, pending_raw is not None)
