"""Research v3: one SQLite transaction, real pinned authority, replayed receipts.

SQLite/OS durability and source/owner configuration are trusted, not proved.
An external retained checkpoint is needed to detect complete database rollback.
No test callback or per-request verifier substitution is part of this API.
"""

from __future__ import annotations
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import re
import sqlite3
from contextlib import contextmanager
from proof_gate import POLICY_HASH, Model, wire_bytes
from promotion_v2 import (
    Head,
    IntegrityFailure,
    ProposalRejected,
    StaleHead,
    blob_hash,
    canonical,
    strict_json,
    receipt_hash,
    ZERO_HASH,
)
from sealed_inference import SealedInference, decode_sealed_model
from pinned_authority import PinnedAuthority

VERSION = "pgsi-transactional-store-v3"
MAX_DATABASE = 16 * 1024 * 1024


def record(raw):
    if type(raw) is not bytes or len(raw) > 4096:
        raise IntegrityFailure("Invalid/oversized canonical record")
    return strict_json(raw)


MAX_GENERATIONS = 7  # Strictly gains a previously incorrect member of seven cases.


def request_hash(expected, raw):
    return hashlib.sha256(
        b"PGSI-REQUEST-v3\0"
        + canonical({"expected": asdict(expected), "candidate_hex": raw.hex()})
    ).hexdigest()


def request_id_ok(value):
    if type(value) is not str or re.fullmatch("[0-9a-f]{32}", value) is None:
        raise IntegrityFailure("Expected a 128-bit lowercase request identifier")


class TransactionalStore:
    def __init__(self, path: Path, authority: PinnedAuthority):
        # This is owner setup, never chosen in the untrusted request schema.
        if type(authority) is not PinnedAuthority:
            raise IntegrityFailure("Owner must provision the concrete pinned authority")
        self.path = Path(path).absolute()
        self.authority = authority

    @contextmanager
    def _db(self):
        if (
            self.path.is_symlink()
            or not self.path.is_file()
            or self.path.resolve() != self.path
        ):
            raise IntegrityFailure("Missing or linked research database")
        info = self.path.stat()
        if info.st_nlink != 1 or info.st_size > MAX_DATABASE:
            raise IntegrityFailure("Hardlinked/oversized database")
        for suffix in ["-wal", "-shm", "-journal"]:
            side = Path(str(self.path) + suffix)
            if side.is_symlink():
                raise IntegrityFailure("Linked SQLite sidecar")
            if side.exists() and (
                side.stat().st_nlink != 1 or side.stat().st_size > MAX_DATABASE
            ):
                raise IntegrityFailure("Invalid SQLite sidecar")
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            yield db
        except sqlite3.Error as e:
            raise IntegrityFailure("Research transaction/integrity failure") from e
        finally:
            db.close()

    @classmethod
    def initialize(cls, path, authority, initial: Model):
        path = Path(path).absolute()
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        store = cls(path, authority)
        raw = wire_bytes(initial)
        decode_sealed_model(raw)
        with store._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE state (name TEXT PRIMARY KEY, body BLOB NOT NULL)")
            db.execute(
                "CREATE TABLE blobs (digest TEXT PRIMARY KEY, body BLOB NOT NULL)"
            )
            db.execute(
                "CREATE TABLE receipts (generation INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, body BLOB NOT NULL)"
            )
            genesis = {
                "version": VERSION,
                "initial_sha256": blob_hash(raw),
                "policy_sha256": POLICY_HASH,
                "authority_manifest_sha256": authority.manifest_sha256,
            }
            head = Head(0, blob_hash(raw), POLICY_HASH, ZERO_HASH)
            db.execute("INSERT INTO blobs VALUES (?,?)", (blob_hash(raw), raw))
            db.executemany(
                "INSERT INTO state VALUES (?,?)",
                [("GENESIS", canonical(genesis)), ("HEAD", canonical(asdict(head)))],
            )
            db.execute("COMMIT")
        return store

    def _audit(self, db, checkpoint=None):
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise IntegrityFailure("SQLite integrity check failed")
        state_rows = db.execute(
            "SELECT name,CASE WHEN length(body)<=4096 THEN body ELSE NULL END FROM state LIMIT 3"
        ).fetchall()
        if len(state_rows) != 2:
            raise IntegrityFailure("Invalid state row count")
        rows = dict(state_rows)
        if set(rows) != {"GENESIS", "HEAD"}:
            raise IntegrityFailure("Unexpected state inventory")
        genesis = record(rows["GENESIS"])
        head = Head.parse(record(rows["HEAD"]))
        if (
            type(genesis) is not dict
            or set(genesis)
            != {
                "version",
                "initial_sha256",
                "policy_sha256",
                "authority_manifest_sha256",
            }
            or genesis["version"] != VERSION
            or genesis["policy_sha256"] != POLICY_HASH
            or genesis["authority_manifest_sha256"] != self.authority.manifest_sha256
            or head.policy_sha256 != POLICY_HASH
        ):
            raise IntegrityFailure("Genesis/policy/authority identity mismatch")
        if head.generation > MAX_GENERATIONS:
            raise IntegrityFailure("Impossible finite-gain generation count")
        blobs = dict(
            db.execute(
                "SELECT digest,CASE WHEN length(body)<=80 THEN body ELSE NULL END FROM blobs LIMIT 9"
            )
        )
        if len(blobs) > MAX_GENERATIONS + 1:
            raise IntegrityFailure("Unbounded blob inventory")
        for digest, raw in blobs.items():
            if type(raw) is not bytes or blob_hash(raw) != digest:
                raise IntegrityFailure("Blob byte/digest mismatch")
            decode_sealed_model(raw)
        digest = genesis["initial_sha256"]
        previous = ZERO_HASH
        visited = {digest}
        if digest not in blobs:
            raise IntegrityFailure("Missing genesis blob")
        history = [Head(0, digest, POLICY_HASH, ZERO_HASH)]
        events = db.execute(
            "SELECT generation,request_id,CASE WHEN length(body)<=4096 THEN body ELSE NULL END FROM receipts ORDER BY generation LIMIT 9"
        ).fetchall()
        if len(events) != head.generation:
            raise IntegrityFailure("Receipt count/generation mismatch")
        for gen, (generation, request_id, raw) in enumerate(events, 1):
            request_id_ok(request_id)
            event = record(raw)
            fields = {
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
                or set(event) != fields
                or type(event["generation"]) is not int
                or type(generation) is not int
                or generation != gen
                or event["generation"] != gen
                or event["version"] != VERSION
                or event["request_id"] != request_id
                or event["old_sha256"] != digest
                or event["previous_receipt_sha256"] != previous
                or event["policy_sha256"] != POLICY_HASH
            ):
                raise IntegrityFailure("Broken receipt chain")
            proposed = event["new_sha256"]
            if proposed not in blobs:
                raise IntegrityFailure("Missing proposed model")
            if event["request_sha256"] != request_hash(history[-1], blobs[proposed]):
                raise IntegrityFailure("Receipt request binding mismatch")
            try:
                actual = self.authority.authorize(blobs[digest], blobs[proposed])
            except ProposalRejected as e:
                raise IntegrityFailure(
                    "Stored receipt fails independent Lean replay"
                ) from e
            if event["authority"] != actual:
                raise IntegrityFailure("Authority receipt identity mismatch")
            digest = proposed
            previous = receipt_hash(raw)
            visited.add(digest)
            history.append(Head(gen, digest, POLICY_HASH, previous))
        if set(blobs) != visited or head != history[-1]:
            raise IntegrityFailure("Unreachable blobs or inconsistent HEAD")
        if checkpoint is not None:
            if type(checkpoint) is not Head:
                raise IntegrityFailure("Invalid checkpoint type")
            Head.parse(asdict(checkpoint))
            if (
                checkpoint.generation >= len(history)
                or history[checkpoint.generation] != checkpoint
            ):
                raise StaleHead(
                    "History rolls back or forks the independently retained checkpoint"
                )
        return head, blobs[head.active_sha256]

    def audit(self, *, checkpoint=None):
        with self._db() as db:
            db.execute("BEGIN")
            return self._audit(db, checkpoint)[0]

    def load(self, *, expected=None, checkpoint=None):
        with self._db() as db:
            db.execute("BEGIN")
            head, raw = self._audit(db, checkpoint)
            if expected is not None and head != expected:
                raise StaleHead("Unexpected inference generation")
            return SealedInference(head, raw, decode_sealed_model(raw))

    def export_history(self, *, expected: Head):
        """Snapshot exact unsigned history for a fresh receiver-owned verifier.

        The receiver must retain its expected head through a trusted channel;
        an expected head copied only from this package provides no rollback anchor.
        """
        with self._db() as db:
            db.execute("BEGIN")
            head, _ = self._audit(db)
            if head != expected:
                raise StaleHead("Cannot export unexpected generation")
            state = dict(db.execute("SELECT name,body FROM state"))
            return {
                "format": "pgsi-portable-history-v1",
                "owner_manifest_hex": canonical(self.authority.manifest).hex(),
                "genesis_hex": state["GENESIS"].hex(),
                "head": asdict(head),
                "blobs": {
                    digest: raw.hex()
                    for digest, raw in db.execute(
                        "SELECT digest,body FROM blobs ORDER BY digest"
                    )
                },
                "receipts": [
                    {"generation": gen, "request_id": key, "body_hex": raw.hex()}
                    for gen, key, raw in db.execute(
                        "SELECT generation,request_id,body FROM receipts ORDER BY generation"
                    )
                ],
                "historical_signature": None,
            }

    def promote(
        self, candidate: bytes, expected: Head, request_id: str, *, checkpoint=None
    ):
        request_id_ok(request_id)
        if type(expected) is not Head:
            raise IntegrityFailure("Typed expected head required")
        Head.parse(asdict(expected))
        decode_sealed_model(candidate)
        request_sha = request_hash(expected, candidate)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old, original = self._audit(db, checkpoint)
            duplicate = db.execute(
                "SELECT CASE WHEN length(body)<=4096 THEN body ELSE NULL END FROM receipts WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if duplicate:
                event = record(duplicate[0])
                if event["request_sha256"] != request_sha:
                    raise IntegrityFailure(
                        "Request identifier reused for different proposal"
                    )
                return Head(
                    event["generation"],
                    event["new_sha256"],
                    POLICY_HASH,
                    receipt_hash(duplicate[0]),
                )
            if old != expected:
                raise StaleHead("Generation-aware compare-and-swap conflict")
            observation = self.authority.authorize(original, candidate)
            # Both Python and Lean read exactly these immutable bytes; neither
            # verifier nor predictor reopens a proposer artifact pathname.
            if (
                blob_hash(original) != old.active_sha256
                or blob_hash(candidate) != observation["new_sha256"]
            ):
                raise IntegrityFailure("Byte snapshot identity mismatch")
            event = {
                "version": VERSION,
                "generation": old.generation + 1,
                "request_id": request_id,
                "request_sha256": request_sha,
                "old_sha256": old.active_sha256,
                "new_sha256": blob_hash(candidate),
                "previous_receipt_sha256": old.last_receipt_sha256,
                "policy_sha256": POLICY_HASH,
                "authority": observation,
            }
            raw = canonical(event)
            head = Head(
                old.generation + 1, blob_hash(candidate), POLICY_HASH, receipt_hash(raw)
            )
            db.execute(
                "INSERT OR IGNORE INTO blobs VALUES (?,?)",
                (head.active_sha256, candidate),
            )
            db.execute(
                "INSERT INTO receipts VALUES (?,?,?)",
                (head.generation, request_id, raw),
            )
            db.execute(
                "UPDATE state SET body=? WHERE name=?",
                (canonical(asdict(head)), "HEAD"),
            )
            db.execute("COMMIT")
            return head
