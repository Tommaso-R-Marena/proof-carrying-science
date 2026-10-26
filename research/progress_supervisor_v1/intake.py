"""Bounded, exact-type capture preflight. A valid plan grants NO authority.

Every positive replay must still build/check the native Lean implementation,
execute real fixed SQL tools, compare exact canonical receipts and kernel-check
the observed wire/path. This module rejects malformed claims before those effects.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .authority import packet
from .binding import SourceBinding, source_inventory
from .broker import PUBLIC, parse_proposal
from .certificate import encode, groups, propose, sha
from .evidence import ORIGINS
from .example import model

ROOT_FIELDS = frozenset(("format", "data_origin", "sources", "model_hex", "certificate_hex",
                         "pre_sanitized", "samples", "final"))
EVENT_FIELDS = frozenset(("request_id", "generation", "source", "target", "action", "proposal",
                          "proposal_classification", "body_sha256", "request_hex", "reply_hex",
                          "source_id", "previous_sha256", "pcs_authority", "event_sha256"))
SNAPSHOT_FIELDS = frozenset(("state", "transitions", "head", "public", "pcs_authority"))
HALT_FIELDS = frozenset(("status", "state", "generation", "pcs_authority"))


def _snapshot(value):
    """Detach caller-owned JSON values without normalizing floats into integers."""
    nodes, characters = 4096, 1024 * 1024

    def copy(item, depth):
        nonlocal nodes, characters
        nodes -= 1
        if nodes < 0 or depth > 16:
            raise ValueError("bounded JSON capture tree required")
        kind = type(item)
        if kind is dict:
            if len(item) > 64 or any(type(k) is not str or len(k) > 256 for k in item):
                raise ValueError("bounded string-keyed capture object required")
            return {key: copy(child, depth + 1) for key, child in item.items()}
        if kind is list:
            if len(item) > 64:
                raise ValueError("bounded capture list required")
            return [copy(child, depth + 1) for child in item]
        if kind is str:
            characters -= len(item)
            if len(item) > 8192 or characters < 0:
                raise ValueError("bounded capture strings required")
            return item
        if item is None or kind in (bool, int, float):
            return item
        raise ValueError("capture must contain only JSON values")

    return copy(value, 0)


def _object(value, fields, label):
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"exact {label} schema required")


def _nat(value, label, limit=65536):
    if type(value) is not int or not 0 <= value < limit:
        raise ValueError(f"exact bounded integer {label} required")
    return value


def _hex(value, label, *, size=None, maximum=4096):
    if type(value) is not str or len(value) % 2 or len(value) > 2 * maximum or re.fullmatch("[0-9a-f]*", value) is None:
        raise ValueError(f"canonical lowercase {label} hex required")
    if size is not None and len(value) != size * 2:
        raise ValueError(f"exact {label} byte length required")
    return bytes.fromhex(value)


def _rid(value):
    if type(value) is not str or re.fullmatch("[a-z0-9_-]{1,64}", value) is None:
        raise ValueError("bounded request identity required")
    return value


@dataclass(frozen=True)
class ReplaySample:
    request_id: str
    proposal: bytes
    receipt_json: bytes


@dataclass(frozen=True)
class ReplayPlan:
    pre_sanitized: bool
    data_origin: str
    sources: tuple[tuple[str, str], ...]
    binding: SourceBinding
    model_raw: bytes
    certificate_raw: bytes
    samples: tuple[ReplaySample, ...]
    final_json: bytes


def preflight(capture):
    """Validate the entire fixed-workflow claim, before files/verifiers/effects.

    The returned immutable bytes are the only input consumed by replay. No
    caller-owned dictionaries survive. Structural/digest/model checks here are
    ordinary trusted Python, not a Lean verdict or a proof of SQL correspondence.
    """
    cap = _snapshot(capture)
    _object(cap, ROOT_FIELDS, "capture")
    if cap["format"] != "pcs-progress-supervisor-capture-v1" or cap["data_origin"] not in ORIGINS:
        raise ValueError("unsupported capture schema")
    expected_sources = source_inventory()
    if cap["sources"] != expected_sources:
        raise ValueError("capture belongs to different implementation sources")
    if type(cap["pre_sanitized"]) is not bool:
        raise ValueError("exact Boolean fixture mode required")
    pre = cap["pre_sanitized"]
    m = model()
    raw = encode(m)
    cert = propose(raw, [4])
    cert_raw = encode(cert)
    if _hex(cap["model_hex"], "model") != raw or _hex(cap["certificate_hex"], "certificate") != cert_raw:
        raise ValueError("model/certificate byte identity mismatch")
    binding = SourceBinding.capture(raw, cert_raw)
    state, generation, head = 0, 0, binding.seed(pre)
    seen, planned = {}, []
    ranks, allowed, edges = dict(cert["ranks"]), {tuple(p) for p in cert["allowed"]}, groups(m)
    samples = cap["samples"]
    if type(samples) is not list or not 1 <= len(samples) <= 32:
        raise ValueError("bounded nonempty capture required")
    for sample in samples:
        _object(sample, {"request_id", "proposal_hex", "record"}, "sample")
        rid = _rid(sample["request_id"])
        proposal_raw = _hex(sample["proposal_hex"], "proposal")
        proposal, classification = parse_proposal(proposal_raw)
        record = sample["record"]
        if type(record) is not dict:
            raise ValueError("exact receipt object required")
        if set(record) == HALT_FIELDS:
            _nat(record["state"], "halt state")
            _nat(record["generation"], "halt generation", 5)
            if rid in seen or state != 4 or record != dict(status="HALTED", state=4, generation=generation, pcs_authority=False) or record["pcs_authority"] is not False:
                raise ValueError("halt receipt disagrees with captured history")
        else:
            _object(record, EVENT_FIELDS, "event receipt")
            for key in ("source", "target", "action"):
                _nat(record[key], key)
            _nat(record["generation"], "generation", 5)
            if record["proposal"] is not None:
                _nat(record["proposal"], "proposal")
            if record["pcs_authority"] is not False or _rid(record["request_id"]) != rid:
                raise ValueError("receipt identity/authority disagrees")
            for key in ("body_sha256", "source_id", "previous_sha256", "event_sha256"):
                _hex(record[key], key, size=32)
            _hex(record["request_hex"], "native request", size=6)
            _hex(record["reply_hex"], "native reply", size=6)
            core = {k: v for k, v in record.items() if k != "event_sha256"}
            if record["event_sha256"] != sha(encode(core)):
                raise ValueError("receipt digest disagrees with canonical fields")
            if rid in seen:
                old_raw, old_receipt = seen[rid]
                if proposal_raw != old_raw or encode(record) != old_receipt:
                    raise ValueError("retry identity/body/receipt disagrees")
            else:
                if state == 4 or record["generation"] != generation + 1 or record["source"] != state or record["previous_sha256"] != head:
                    raise ValueError("receipt order/chain disagrees with captured history")
                if record["source_id"] != binding.source_id or record["body_sha256"] != sha(proposal_raw) or record["proposal"] != proposal or record["proposal_classification"] != classification:
                    raise ValueError("receipt source/proposal binding disagrees")
                action, target = record["action"], record["target"]
                if (state, action) not in allowed or target not in edges[state, action]:
                    raise ValueError("receipt transition disagrees with fixed certificate")
                # This fixed fixture has a deterministic observed read outcome.
                expected_target = {0: 1, 1: 3 if pre else 2, 2: 3, 3: 4}[action]
                if target != expected_target or ranks[target] >= ranks[state]:
                    raise ValueError("receipt outcome disagrees with fixed fixture")
                request, reply = packet(state, proposal), bytes([1, 1, action, 0, ranks[state], 0])
                if record["request_hex"] != request.hex() or record["reply_hex"] != reply.hex():
                    raise ValueError("receipt wire bytes disagree with action/rank")
                seen[rid] = (proposal_raw, encode(record))
                state, generation, head = target, generation + 1, record["event_sha256"]
        planned.append(ReplaySample(rid, proposal_raw, encode(record)))
    final = cap["final"]
    _object(final, SNAPSHOT_FIELDS, "final snapshot")
    _nat(final["state"], "final state")
    _nat(final["transitions"], "final transition count", 5)
    _hex(final["head"], "final chain head", size=32)
    if final["pcs_authority"] is not False or state != 4 or final != dict(state=state, transitions=generation, head=head, public=[PUBLIC], pcs_authority=False):
        raise ValueError("final effects disagree with complete captured history")
    return ReplayPlan(pre, cap["data_origin"], tuple(sorted(expected_sources.items())), binding,
                      raw, cert_raw, tuple(planned), encode(final))
