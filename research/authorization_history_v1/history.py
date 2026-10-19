"""Signed authorization envelopes, exact replay and atomic local generation CAS.

This module never executes a scientific checker. A signature means only that a
holder of a pinned key signed these exact bytes. External Root/Anchor protection,
honest SQLite/OS execution, Ed25519 authenticity and SHA256 collision resistance
are assumptions, not results of this experiment. See the accompanying report.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


MAX_BYTES = 1 << 20
MAX_WIRE = 16 << 20
MAX_GENERATION = (1 << 63) - 1
SIGNING_DOMAIN = b"PCS-AUTHORIZATION-HISTORY-V1\x00"
ROOT_DOMAIN = b"PCS-AUTHORIZATION-ROOT-V1\x00"
LINK_DOMAIN = b"PCS-AUTHORIZATION-LINK-V1\x00"


class Rejected(ValueError):
    """An unauthenticated, stale, ambiguous or malformed history fails closed."""


def _bytes(value: bytes, name: str, *, length: int | None = None) -> bytes:
    if type(value) is not bytes or len(value) > MAX_BYTES:
        raise Rejected(f"Invalid bounded bytes: {name}")
    if length is not None and len(value) != length:
        raise Rejected(f"Invalid byte length: {name}")
    return value


def _nat(value: int) -> int:
    if type(value) is not int or not 0 <= value <= MAX_GENERATION:
        raise Rejected("Invalid bounded generation")
    return value


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _object(raw: bytes, fields: set[str]) -> dict:
    if type(raw) is not bytes or len(raw) > MAX_WIRE:
        raise Rejected("Invalid bounded wire bytes")
    try:
        value = json.loads(raw)
        if type(value) is not dict or set(value) != fields or _canonical(value) != raw:
            raise Rejected("Noncanonical or unrecognized object")
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Rejected("Invalid canonical object") from exc


def _unhex(value: str, name: str) -> bytes:
    if type(value) is not str or len(value) > MAX_BYTES * 2 or len(value) % 2:
        raise Rejected(f"Invalid lowercase hex: {name}")
    if any(c not in "0123456789abcdef" for c in value):
        raise Rejected(f"Invalid lowercase hex: {name}")
    return bytes.fromhex(value)


@dataclass(frozen=True)
class Root:
    authority: bytes
    witness: bytes
    policy: bytes
    checker: bytes
    genesis_id: bytes
    genesis_incumbent: bytes
    genesis_generation: int = 0

    def __post_init__(self):
        _bytes(self.authority, "authority", length=32)
        _bytes(self.witness, "witness", length=32)
        if self.authority == self.witness:
            raise Rejected("Authority and witness keys must differ")
        for name in ("policy", "checker", "genesis_id", "genesis_incumbent"):
            _bytes(getattr(self, name), name)
        if not self.policy or not self.checker or not self.genesis_id:
            raise Rejected("Empty root identity")
        _nat(self.genesis_generation)

    def encode(self) -> bytes:
        return _canonical({
            "format": "pcs-authorization-root-v1",
            "authority": self.authority.hex(), "witness": self.witness.hex(),
            "policy": self.policy.hex(), "checker": self.checker.hex(),
            "genesis_id": self.genesis_id.hex(),
            "genesis_incumbent": self.genesis_incumbent.hex(),
            "genesis_generation": self.genesis_generation,
        })


@dataclass(frozen=True)
class Anchor:
    """Retain outside the producer-controlled store; no self-trust from DB bytes."""

    generation: int
    incumbent: bytes
    tip: bytes
    chain_digest: bytes

    def __post_init__(self):
        _nat(self.generation)
        _bytes(self.incumbent, "incumbent")
        _bytes(self.tip, "tip")
        _bytes(self.chain_digest, "chain_digest", length=32)


def initial(root: Root) -> Anchor:
    return Anchor(root.genesis_generation, root.genesis_incumbent, root.genesis_id,
                  hashlib.sha256(ROOT_DOMAIN + root.encode()).digest())


PAYLOAD_BYTES = ("authority", "witness", "policy", "checker", "previous_id", "expected_chain_digest",
                 "event_id", "expected_incumbent", "candidate", "certificate")
PAYLOAD_FIELDS = set(PAYLOAD_BYTES) | {"format", "event_class", "expected_generation", "next_generation"}


@dataclass(frozen=True)
class Payload:
    authority: bytes
    witness: bytes
    policy: bytes
    checker: bytes
    previous_id: bytes
    expected_chain_digest: bytes
    event_id: bytes
    expected_generation: int
    next_generation: int
    expected_incumbent: bytes
    candidate: bytes
    certificate: bytes

    def __post_init__(self):
        for name in PAYLOAD_BYTES:
            _bytes(getattr(self, name), name)
        _bytes(self.expected_chain_digest, "expected_chain_digest", length=32)
        _nat(self.expected_generation)
        _nat(self.next_generation)
        if not self.event_id:
            raise Rejected("Empty event ID")

    def encode(self) -> bytes:
        value = {name: getattr(self, name).hex() for name in PAYLOAD_BYTES}
        value.update(format="pcs-authorization-payload-v1", event_class="model-promotion-authorization",
                     expected_generation=self.expected_generation, next_generation=self.next_generation)
        return _canonical(value)

    @classmethod
    def decode(cls, raw: bytes) -> Payload:
        value = _object(raw, PAYLOAD_FIELDS)
        if value["format"] != "pcs-authorization-payload-v1" or value["event_class"] != "model-promotion-authorization":
            raise Rejected("Wrong payload domain/class")
        result = cls(**{name: _unhex(value[name], name) for name in PAYLOAD_BYTES},
                     expected_generation=value["expected_generation"], next_generation=value["next_generation"])
        if result.encode() != raw:
            raise Rejected("Noncanonical payload")
        return result

    def signing_bytes(self) -> bytes:
        return SIGNING_DOMAIN + self.encode()


@dataclass(frozen=True)
class Envelope:
    payload: Payload
    authority_signature: bytes
    witness_signature: bytes

    def __post_init__(self):
        if type(self.payload) is not Payload:
            raise Rejected("Exact payload type required")
        _bytes(self.authority_signature, "authority signature", length=64)
        _bytes(self.witness_signature, "witness signature", length=64)

    def encode(self) -> bytes:
        # Payload is embedded as an object, not a digest or selected projection.
        return _canonical({"format": "pcs-authorization-envelope-v1",
                           "payload": json.loads(self.payload.encode()),
                           "authority_signature": self.authority_signature.hex(),
                           "witness_signature": self.witness_signature.hex()})

    @classmethod
    def decode(cls, raw: bytes) -> Envelope:
        value = _object(raw, {"format", "payload", "authority_signature", "witness_signature"})
        if value["format"] != "pcs-authorization-envelope-v1" or type(value["payload"]) is not dict:
            raise Rejected("Wrong envelope domain")
        result = cls(Payload.decode(_canonical(value["payload"])),
                     _unhex(value["authority_signature"], "authority_signature"),
                     _unhex(value["witness_signature"], "witness_signature"))
        if result.encode() != raw:
            raise Rejected("Noncanonical envelope")
        return result


def proposed_payload(root: Root, expected: Anchor, *, event_id: bytes,
                     candidate: bytes, certificate: bytes) -> Payload:
    return Payload(root.authority, root.witness, root.policy, root.checker, expected.tip, expected.chain_digest,
                   event_id, expected.generation, expected.generation + 1,
                   expected.incumbent, candidate, certificate)


def _advance(root: Root, expected: Anchor, envelope: Envelope, seen: set[bytes]) -> Anchor:
    payload = envelope.payload
    if (payload.authority, payload.witness, payload.policy, payload.checker) != (
            root.authority, root.witness, root.policy, root.checker):
        raise Rejected("Untrusted authority/witness/policy/checker scope")
    if (payload.expected_generation != expected.generation
            or payload.next_generation != expected.generation + 1
            or payload.expected_incumbent != expected.incumbent
            or payload.previous_id != expected.tip
            or payload.expected_chain_digest != expected.chain_digest):
        raise Rejected("Stale or conflicting generation/incumbent/predecessor")
    if payload.event_id == root.genesis_id or payload.event_id in seen:
        raise Rejected("Replayed event ID")
    try:
        Ed25519PublicKey.from_public_bytes(root.authority).verify(
            envelope.authority_signature, payload.signing_bytes())
        Ed25519PublicKey.from_public_bytes(root.witness).verify(
            envelope.witness_signature, payload.signing_bytes())
    except (InvalidSignature, ValueError) as exc:
        raise Rejected("Invalid Ed25519 signature") from exc
    digest = hashlib.sha256(LINK_DOMAIN + expected.chain_digest + envelope.encode()).digest()
    return Anchor(payload.next_generation, payload.candidate, payload.event_id, digest)


# Schema is checked exactly, including absence of extra tables, views and triggers.
SCHEMA = {
    "config": "CREATE TABLE config (id INTEGER PRIMARY KEY CHECK(id = 1), root BLOB NOT NULL) STRICT",
    "head": "CREATE TABLE head (id INTEGER PRIMARY KEY CHECK(id = 1), generation INTEGER NOT NULL, incumbent BLOB NOT NULL, tip BLOB NOT NULL, chain_digest BLOB NOT NULL) STRICT",
    "events": "CREATE TABLE events (generation INTEGER PRIMARY KEY, envelope BLOB NOT NULL) STRICT",
}


def _connect(path: Path) -> sqlite3.Connection:
    # mode=rw prevents an absent history from silently becoming a new genesis.
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10,
                                 isolation_level=None)
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def _schema(connection: sqlite3.Connection):
    rows = connection.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name").fetchall()
    expected = [("table", name, name, SCHEMA[name]) for name in sorted(SCHEMA)]
    if rows != expected:
        raise Rejected("Altered or unknown SQLite schema")


@dataclass(frozen=True)
class Snapshot:
    anchor: Anchor
    envelopes: tuple[Envelope, ...]


def _replay(connection: sqlite3.Connection, root: Root) -> tuple[Snapshot, tuple[Anchor, ...]]:
    _schema(connection)
    if connection.execute("SELECT id, root FROM config").fetchall() != [(1, root.encode())]:
        raise Rejected("Store root differs from receiver-pinned root")
    current = initial(root)
    anchors = [current]
    seen: set[bytes] = set()
    events = []
    for generation, raw in connection.execute("SELECT generation, envelope FROM events ORDER BY generation"):
        envelope = Envelope.decode(raw)
        current = _advance(root, current, envelope, seen)
        if type(generation) is not int or generation != current.generation:
            raise Rejected("Missing, reordered or inconsistent generation")
        seen.add(envelope.payload.event_id)
        anchors.append(current)
        events.append(envelope)
    if connection.execute("SELECT id, generation, incumbent, tip, chain_digest FROM head").fetchall() != [
            (1, current.generation, current.incumbent, current.tip, current.chain_digest)]:
        raise Rejected("Stored head differs from exact authenticated replay")
    return Snapshot(current, tuple(events)), tuple(anchors)


class History:
    """A handle pinned to an exact externally expected committed checkpoint.

    append returns the next checkpoint only after COMMIT. Publishing/retaining it
    externally is a caller obligation and is not atomic with the local DB commit.
    A stale handle fails closed, including when another writer committed first.
    """

    def __init__(self, path: Path, root: Root, expected_anchor: Anchor):
        if type(root) is not Root or type(expected_anchor) is not Anchor:
            raise Rejected("Receiver-owned root and external expected anchor required")
        self.path = Path(path)
        self.root = root
        self.expected_anchor = expected_anchor
        self.snapshot()

    @classmethod
    def create(cls, path: Path, root: Root) -> History:
        if type(root) is not Root:
            raise Rejected("Receiver-owned root required")
        path = Path(path)
        # Never overwrite any existing history, even an empty/malformed one.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        connection = None
        try:
            connection = _connect(path)
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA.values():
                connection.execute(statement)
            anchor = initial(root)
            connection.execute("INSERT INTO config VALUES (1, ?)", (root.encode(),))
            connection.execute("INSERT INTO head VALUES (1, ?, ?, ?, ?)",
                               (anchor.generation, anchor.incumbent, anchor.tip, anchor.chain_digest))
            connection.commit()
        finally:
            if connection is not None:
                connection.close()
        return cls(path, root, initial(root))

    def snapshot(self) -> Snapshot:
        connection = None
        try:
            connection = _connect(self.path)
            connection.execute("BEGIN")
            snapshot, _ = _replay(connection, self.root)
            if snapshot.anchor != self.expected_anchor:
                raise Rejected("History differs from external expected anchor")
            return snapshot
        except sqlite3.Error as exc:
            raise Rejected("SQLite history audit failed") from exc
        finally:
            if connection is not None:
                connection.close()

    def append(self, envelope_bytes: bytes) -> Anchor:
        envelope = Envelope.decode(envelope_bytes)
        connection = None
        try:
            connection = _connect(self.path)
            # The lock spans audit, signature checks, generation CAS and append.
            connection.execute("BEGIN IMMEDIATE")
            snapshot, _ = _replay(connection, self.root)
            if snapshot.anchor != self.expected_anchor:
                raise Rejected("Stale external expected anchor")
            next_anchor = _advance(self.root, snapshot.anchor, envelope,
                                   {e.payload.event_id for e in snapshot.envelopes})
            connection.execute("INSERT INTO events VALUES (?, ?)",
                               (next_anchor.generation, envelope_bytes))
            changed = connection.execute(
                "UPDATE head SET generation=?, incumbent=?, tip=?, chain_digest=? "
                "WHERE id=1 AND generation=? AND incumbent=? AND tip=? AND chain_digest=?",
                (next_anchor.generation, next_anchor.incumbent, next_anchor.tip, next_anchor.chain_digest,
                 snapshot.anchor.generation, snapshot.anchor.incumbent, snapshot.anchor.tip,
                 snapshot.anchor.chain_digest)).rowcount
            if changed != 1:
                raise Rejected("Generation CAS failed")
            connection.commit()  # Local logical linearization point.
            self.expected_anchor = next_anchor
            return next_anchor
        except sqlite3.Error as exc:
            raise Rejected("SQLite append failed") from exc
        finally:
            if connection is not None:
                connection.close()  # An uncommitted transaction rolls back.


def recover(path: Path, root: Root, *, previous: Anchor, expected_envelope: bytes) -> Anchor:
    """Reconcile one externally retained exact intent; never invent authorization.

    Returns previous if nothing committed, or the exact intent's committed anchor.
    Any other suffix/head fails closed. This performs no append or publication.
    The caller must protect previous, root and expected_envelope independently.
    """
    if type(root) is not Root or type(previous) is not Anchor:
        raise Rejected("Receiver-owned recovery root/anchor required")
    intent = Envelope.decode(expected_envelope)
    connection = None
    try:
        connection = _connect(Path(path))
        connection.execute("BEGIN")
        snapshot, anchors = _replay(connection, root)
        if snapshot.anchor == previous:
            _advance(root, previous, intent, {e.payload.event_id for e in snapshot.envelopes})
            return previous
        if len(anchors) < 2 or anchors[-2] != previous:
            raise Rejected("Ambiguous recovery prefix/suffix")
        next_anchor = _advance(root, previous, intent,
                               {e.payload.event_id for e in snapshot.envelopes[:-1]})
        if snapshot.anchor != next_anchor or snapshot.envelopes[-1].encode() != expected_envelope:
            raise Rejected("Committed suffix differs from externally retained intent")
        return next_anchor
    except sqlite3.Error as exc:
        raise Rejected("SQLite recovery audit failed") from exc
    finally:
        if connection is not None:
            connection.close()
