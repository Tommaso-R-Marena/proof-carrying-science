"""Independent receiving of an unsigned PGSI research history.

A receiver-owned native verifier rechecks the exact transition bytes and active
predictions. Source-bound semantic replay does not authenticate the producer's
unsigned deployment history. A separately trusted expected head is mandatory.
"""

from __future__ import annotations
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
from build_authority import source_inventory
from pinned_authority import PinnedAuthority
from promotion_v2 import (
    Head,
    IntegrityFailure,
    ProposalRejected,
    StaleHead,
    strict_json,
    _read_regular,
    blob_hash,
    receipt_hash,
    ZERO_HASH,
)
from proof_gate import POLICY_HASH
from sealed_inference import SealedInference, decode_sealed_model
from transactional_store import VERSION, MAX_GENERATIONS, request_hash, request_id_ok


def raw_hex(value, limit):
    if (
        type(value) is not str
        or len(value) > 2 * limit
        or len(value) % 2
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise IntegrityFailure("Invalid bounded byte encoding")
    return bytes.fromhex(value)


def replay_history(
    package, receiver: PinnedAuthority, *, expected: Head, xs=(-20, 0, 20)
):
    if type(receiver) is not PinnedAuthority or type(expected) is not Head:
        raise IntegrityFailure("Receiver-owned authority and checkpoint required")
    Head.parse(asdict(expected))
    fields = {
        "format",
        "owner_manifest_hex",
        "genesis_hex",
        "head",
        "blobs",
        "receipts",
        "historical_signature",
    }
    if (
        type(package) is not dict
        or set(package) != fields
        or package["format"] != "pgsi-portable-history-v1"
        or package["historical_signature"] is not None
    ):
        raise IntegrityFailure("Unapproved history envelope")
    if Head.parse(package["head"]) != expected:
        raise StaleHead("History differs from independently retained head")
    owner_raw = raw_hex(package["owner_manifest_hex"], 32768)
    owner = strict_json(owner_raw)
    if (
        type(owner) is not dict
        or owner.get("format") != "pgsi-native-authority-manifest-v1"
        or owner.get("wire_version") != "PGSI1"
        or owner.get("sources") != source_inventory()
    ):
        raise IntegrityFailure(
            "Producer-declared sources differ from trusted receiver sources"
        )
    owner_sha = hashlib.sha256(owner_raw).hexdigest()
    genesis = strict_json(raw_hex(package["genesis_hex"], 4096))
    if (
        type(genesis) is not dict
        or set(genesis)
        != {"version", "initial_sha256", "policy_sha256", "authority_manifest_sha256"}
        or genesis["version"] != VERSION
        or genesis["policy_sha256"] != POLICY_HASH
        or genesis["authority_manifest_sha256"] != owner_sha
    ):
        raise IntegrityFailure("Invalid genesis binding")
    encoded = package["blobs"]
    events = package["receipts"]
    if (
        type(encoded) is not dict
        or not 1 <= len(encoded) <= MAX_GENERATIONS + 1
        or type(events) is not list
        or len(events) > MAX_GENERATIONS
    ):
        raise IntegrityFailure("Unbounded history")
    blobs = {}
    for digest, value in encoded.items():
        raw = raw_hex(value, 80)
        if blob_hash(raw) != digest:
            raise IntegrityFailure("Exact artifact bytes were substituted")
        decode_sealed_model(raw)
        blobs[digest] = raw
    digest = genesis["initial_sha256"]
    previous = ZERO_HASH
    visited = {digest}
    keys = set()
    if digest not in blobs:
        raise IntegrityFailure("Missing genesis artifact")
    current = Head(0, digest, POLICY_HASH, ZERO_HASH)
    for i, row in enumerate(events, 1):
        if (
            type(row) is not dict
            or set(row) != {"generation", "request_id", "body_hex"}
            or type(row["generation"]) is not int
            or row["generation"] != i
        ):
            raise IntegrityFailure("Invalid receipt sequence")
        request_id_ok(row["request_id"])
        if row["request_id"] in keys:
            raise IntegrityFailure("Replayed request identifier")
        keys.add(row["request_id"])
        raw = raw_hex(row["body_hex"], 4096)
        event = strict_json(raw)
        expected_fields = {
            "version",
            "generation",
            "request_id",
            "request_sha256",
            "old_sha256",
            "new_sha256",
            "previous_receipt_sha256",
            "policy_sha256",
            "authority",
        }
        if (
            type(event) is not dict
            or set(event) != expected_fields
            or type(event["generation"]) is not int
            or event["generation"] != i
            or event["version"] != VERSION
            or event["request_id"] != row["request_id"]
            or event["old_sha256"] != digest
            or event["previous_receipt_sha256"] != previous
            or event["policy_sha256"] != POLICY_HASH
        ):
            raise IntegrityFailure("Receipt chain mismatch")
        new = event["new_sha256"]
        if new not in blobs or event["request_sha256"] != request_hash(
            current, blobs[new]
        ):
            raise IntegrityFailure(
                "Receipt does not bind expected original/candidate bytes"
            )
        declared = {
            "authority_manifest_sha256": owner_sha,
            "authority_binary_sha256": owner["binary_sha256"],
            "old_sha256": digest,
            "new_sha256": new,
            "verdict": "ACCEPT",
            "scope": "Lean finite-corpus predicate; native execution/host correspondence unproved",
        }
        if event["authority"] != declared:
            raise IntegrityFailure("Producer authority declaration mismatch")
        try:
            fresh = receiver.authorize(blobs[digest], blobs[new])
        except ProposalRejected as e:
            raise IntegrityFailure(
                "Fresh receiver Lean check rejects claimed transition"
            ) from e
        if fresh["old_sha256"] != digest or fresh["new_sha256"] != new:
            raise IntegrityFailure("Receiver byte identity mismatch")
        digest = new
        previous = receipt_hash(raw)
        visited.add(digest)
        current = Head(i, digest, POLICY_HASH, previous)
    if current != expected or visited != set(blobs):
        raise IntegrityFailure("Incomplete/forked history or orphan artifact")
    snapshot = SealedInference(
        current, blobs[digest], decode_sealed_model(blobs[digest])
    )
    if (
        type(xs) is not tuple
        or len(xs) > 65
        or any(type(x) is not int or x.bit_length() > 4096 for x in xs)
    ):
        raise IntegrityFailure("Bounded receiver inputs required")
    probe = receiver.probe(
        [{"raw_hex": snapshot.artifact.hex(), "xs": [str(x) for x in xs]}]
    )[0]
    if (
        probe.get("valid") is not True
        or probe["wire"].encode("ascii") != snapshot.artifact
        or tuple(int(v) for v in probe["predictions"]) != snapshot.batch(xs)
    ):
        raise IntegrityFailure("Fresh Lean/Python active inference mismatch")
    return {
        "format": "pgsi-independent-history-replay-v1",
        "head": asdict(current),
        "transitions_freshly_rechecked": len(events),
        "producer_manifest_sha256": owner_sha,
        "receiver_manifest_sha256": receiver.manifest_sha256,
        "receiver_binary_sha256": receiver.binary_sha256,
        "active_artifact_hex": snapshot.artifact.hex(),
        "inputs": list(xs),
        "predictions": list(snapshot.batch(xs)),
        "source_bound_semantic_replay": True,
        "producer_history_authenticated": False,
        "external_antirollback_only_if_expected_head_is_trusted": True,
        "native_execution_refinement_proved": False,
        "pcs_authority": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--history", required=True, type=Path)
    p.add_argument("--expected-head", required=True, type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    raw = _read_regular(a.history, 131072)
    if len(raw) > 131072:
        raise ValueError("History exceeds receiving budget")
    r = replay_history(
        strict_json(raw),
        PinnedAuthority(a.bundle),
        expected=Head.parse(strict_json(_read_regular(a.expected_head, 2048))),
    )
    if a.output:
        with a.output.open("x") as f:
            f.write(json.dumps(r, sort_keys=True, indent=2) + "\n")
    print(json.dumps(r, sort_keys=True))
