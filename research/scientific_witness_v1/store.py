"""Durable serial witness. Honest storage/OS/key continuity are assumptions.

The witness executes science itself at genesis/prepare. FINALIZED means witness
commitment, never observation of a remote coordinator's local database commit.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import stat
from threading import RLock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY, checker_identity
from research.scientific_receiver_v1 import host
from .protocol import (Rejected, MAX_DATABASE, MAX_EVENTS, MAX_ARTIFACT, MAX_RESPONSE,
                       canonical, parse, digest, sign, verify, checked_intent,
                       advance, anchor_json, decode_anchor)

SCHEMA = {
    "config": "CREATE TABLE config (id INTEGER PRIMARY KEY CHECK(id = 1), root BLOB NOT NULL, profile BLOB NOT NULL, witness BLOB NOT NULL, genesis BLOB NOT NULL) STRICT",
    "head": "CREATE TABLE head (id INTEGER PRIMARY KEY CHECK(id = 1), anchor BLOB NOT NULL) STRICT",
    "pending": "CREATE TABLE pending (id INTEGER PRIMARY KEY CHECK(id = 1), intent BLOB NOT NULL, receipt BLOB NOT NULL) STRICT",
    "events": "CREATE TABLE events (generation INTEGER PRIMARY KEY, intent BLOB NOT NULL, prepared BLOB NOT NULL, finalized BLOB NOT NULL) STRICT",
}


class WitnessStore:
    def _setup(self, path, root, config, witness_key):
        if (type(root) is not history.Root or type(config) is not host.OperatorConfig
                or root.policy != POLICY or root.checker != checker_identity(config)
                or root.genesis_generation != 0 or len(root.genesis_incumbent) > MAX_ARTIFACT
                or len(root.genesis_id) > 256
                or not isinstance(witness_key, Ed25519PrivateKey)):
            raise Rejected("Fixed supported root/profile/key required")
        self.path, self.root, self.config, self.key = Path(path), root, config, witness_key
        self.public_key = witness_key.public_key().public_bytes_raw()
        if self.public_key in (root.authority, root.witness):
            raise Rejected("Post-verification witness key must be distinct from intent keys")
        self._identity = canonical(config.identity())
        self._lock = RLock()
        self._service = host.ReceiverService(config)

    def __init__(self, path, root, config, witness_key):
        self._setup(path, root, config, witness_key)
        with self._connection() as c:
            self._load(c)
        # Startup checks genesis under current fixed profile; old events are
        # authenticated witness attestations, not fresh whole-history Lean replay.
        self._science(root.genesis_incumbent)

    @classmethod
    def create(cls, path, root, config, witness_key):
        self = cls.__new__(cls)
        self._setup(path, root, config, witness_key)
        checked = self._science(root.genesis_incumbent)
        receipt = sign(self.key, root, "genesis", {
            "anchor": anchor_json(history.initial(root)), "verification": checked})
        # Explicit creation only; never overwrite or follow an existing path.
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with self._connection(check_schema=False) as c:
                c.execute("BEGIN IMMEDIATE")
                for sql in SCHEMA.values():
                    c.execute(sql)
                c.execute("INSERT INTO config VALUES (1,?,?,?,?)",
                          (root.encode(), self._identity, self.public_key, canonical(receipt)))
                c.execute("INSERT INTO head VALUES (1,?)", (canonical(anchor_json(history.initial(root))),))
                self._guard_commit(c)
                c.execute("COMMIT")
            return self
        except BaseException:
            self.path.unlink(missing_ok=True)
            raise

    @contextmanager
    def _connection(self, check_schema=True):
        try:
            info = self.path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_DATABASE:
                raise Rejected("Witness store must be a bounded regular nonsymlink file")
            for suffix in ("-wal", "-shm", "-journal"):
                side = Path(str(self.path) + suffix)
                if side.exists() or side.is_symlink():
                    si = side.lstat()
                    if suffix != "-journal" or not stat.S_ISREG(si.st_mode) or si.st_size > 2 * MAX_DATABASE:
                        raise Rejected("Invalid witness sidecar")
        except OSError as exc:
            raise Rejected("Missing/unreadable witness state; explicit recovery required") from exc
        c = sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True,
                            isolation_level=None, timeout=10)
        c.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 8 << 20)
        try:
            c.execute("PRAGMA trusted_schema=OFF")
            c.execute("PRAGMA synchronous=FULL")
            if c.execute("PRAGMA journal_mode").fetchone() != ("delete",):
                raise Rejected("Only DELETE journal mode supported")
            if check_schema:
                rows = c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name").fetchall()
                if rows != [("table", n, n, SCHEMA[n]) for n in sorted(SCHEMA)]:
                    raise Rejected("Unknown or altered witness schema")
            yield c
        finally:
            if c.in_transaction:
                c.execute("ROLLBACK")
            c.close()

    def _science(self, raw):
        if type(raw) is not bytes or len(raw) > MAX_ARTIFACT:
            raise Rejected("Unsupported bounded scientific artifact")
        response = self._service.verify_bytes(raw)
        r = response["receipt"]
        if (not host.replay_signed_receipt(response, self._service.public_key_hex)
                or r["accepted"] is not True or r["errors"]
                or r["raw_hex"] != raw.hex() or r["raw_sha256"] != digest(raw)
                or r["raw_bytes"] != len(raw) or r["operator_config_sha256"] != self.root.checker.hex()
                or canonical(r["operator_identity"]) != self._identity
                or r["checks"] != {"pins_before": True, "pins_after": True, "response_checked": True}):
            raise Rejected("Actual fixed scientific verifier rejected or failed")
        result = {"response": r["verifier_response"],
                  "response_sha256": digest(canonical(r["verifier_response"])),
                  "host_receipt_sha256": digest(canonical(response))}
        self._validate_science(raw, result)
        return result

    def _validate_science(self, raw, value):
        if (type(value) is not dict or set(value) != {"response", "response_sha256", "host_receipt_sha256"}
                or value["response_sha256"] != digest(canonical(value["response"]))
                or type(value["host_receipt_sha256"]) is not str or len(value["host_receipt_sha256"]) != 64):
            raise Rejected("Malformed witness scientific evidence")
        try:
            host._validated_response(raw, canonical(value["response"]) + b"\n")
            if value["response"]["accepted"] is not True:
                raise Rejected("Witness statement does not claim mathematical acceptance")
        except (host.HostRejected, KeyError, TypeError, ValueError) as exc:
            raise Rejected("Scientific evidence differs from exact candidate") from exc

    def _prepared(self, intent, previous, next_anchor, checked):
        return sign(self.key, self.root, "prepared", {
            "intent_sha256": digest(intent), "intent": intent.hex(),
            "previous": anchor_json(previous), "next": anchor_json(next_anchor), "verification": checked})

    def _check_prepared(self, intent, receipt, previous, seen):
        e = checked_intent(intent)
        next_anchor = advance(self.root, previous, e, seen)
        value = verify(receipt, self.root, self.public_key, kind="prepared")
        if (set(value) != {"intent_sha256", "intent", "previous", "next", "verification"}
                or value["intent_sha256"] != digest(intent) or value["intent"] != intent.hex()
                or value["previous"] != anchor_json(previous) or value["next"] != anchor_json(next_anchor)):
            raise Rejected("Prepared statement has wrong exact transition binding")
        self._validate_science(e.payload.candidate, value["verification"])
        return next_anchor, e

    def _load(self, c):
        row = c.execute("SELECT root,profile,witness,genesis FROM config WHERE id=1").fetchone()
        if row is None or row[:3] != (self.root.encode(), self._identity, self.public_key):
            raise Rejected("Witness bootstrap/root/profile/key mismatch")
        genesis = parse(row[3])
        g = verify(genesis, self.root, self.public_key, kind="genesis")
        anchor = history.initial(self.root)
        if set(g) != {"anchor", "verification"} or g["anchor"] != anchor_json(anchor):
            raise Rejected("Wrong witness genesis binding")
        self._validate_science(anchor.incumbent, g["verification"])
        count, wire = c.execute("SELECT count(*),coalesce(sum(length(intent)+length(prepared)+length(finalized)),0) FROM events").fetchone()
        if count > MAX_EVENTS or wire > MAX_DATABASE // 2:
            raise Rejected("Witness history exceeds event/wire budget")
        if c.execute("PRAGMA page_count").fetchone()[0] * c.execute("PRAGMA page_size").fetchone()[0] > MAX_DATABASE:
            raise Rejected("Witness database page budget exceeded")
        events, seen = [], set()
        artifact_bytes, envelope_bytes = len(self.root.genesis_incumbent), 0
        for generation, intent, prepared, finalized in c.execute("SELECT generation,intent,prepared,finalized FROM events ORDER BY generation"):
            prep, final = parse(prepared), parse(finalized)
            previous = anchor
            anchor, e = self._check_prepared(intent, prep, anchor, seen)
            f = verify(final, self.root, self.public_key, kind="finalized")
            expected = {"intent_sha256": digest(intent), "previous": anchor_json(previous),
                        "anchor": anchor_json(anchor), "prepared_sha256": digest(prepared)}
            if generation != anchor.generation or f != expected:
                raise Rejected("Finalized witness chain mismatch")
            seen.add(e.payload.event_id)
            artifact_bytes += len(e.payload.candidate)
            envelope_bytes += len(intent)
            events.append({"intent": intent.hex(), "prepared": prep, "finalized": final})
        h = c.execute("SELECT anchor FROM head WHERE id=1").fetchone()
        if h is None or parse(h[0]) != anchor_json(anchor):
            raise Rejected("Witness head is inconsistent with retained chain")
        rows = c.execute("SELECT id,length(intent),length(receipt) FROM pending").fetchall()
        if len(rows) > 1 or any(r[0] != 1 or r[1] > 65536 or r[2] > (1 << 20) for r in rows):
            raise Rejected("Malformed pending state")
        pending = None
        if rows:
            intent, receipt = c.execute("SELECT intent,receipt FROM pending WHERE id=1").fetchone()
            p = parse(receipt)
            next_anchor, e = self._check_prepared(intent, p, anchor, seen)
            if count >= MAX_EVENTS:
                raise Rejected("Pending successor exceeds witness event domain")
            artifact_bytes += len(e.payload.candidate)
            envelope_bytes += len(intent)
            pending = {"intent": intent.hex(), "intent_sha256": digest(intent),
                       "next_anchor": anchor_json(next_anchor), "receipt": p}
        if artifact_bytes > 262144 or envelope_bytes > 1048576:
            raise Rejected("Retained science/envelope audit-domain budget exceeded")
        return anchor, seen, events, pending, genesis

    @staticmethod
    def _payload(anchor, events, pending, genesis, export):
        payload = {"anchor": anchor_json(anchor), "pending": pending,
                   "finalized": events[-1]["finalized"] if events else genesis}
        if export:
            payload.update(envelopes=[e["intent"] for e in events], receipts=events, genesis=genesis)
        return payload

    def _guard_commit(self, c):
        """Validate staged state/exportability before a durable positive return."""
        anchor, _, events, pending, genesis = self._load(c)
        payload = self._payload(anchor, events, pending, genesis, True)
        maximum_reply = sign(self.key, self.root, "response:export", payload, bytes(32))
        if len(canonical(maximum_reply)) > MAX_RESPONSE:
            raise Rejected("Staged witness history exceeds complete export budget")

    def prepare(self, intent: bytes):
        e = checked_intent(intent)
        with self._lock:
            with self._connection() as c:
                c.execute("BEGIN")
                anchor, seen, events, pending, _ = self._load(c)
                c.execute("COMMIT")
            for event in events:
                if event["intent"] == intent.hex():
                    return event["prepared"]  # Historical idempotency, not a fresh current view.
            if pending:
                if pending["intent"] == intent.hex():
                    return pending["receipt"]
                raise Rejected("Conflicting successor already pending")
            if len(events) >= MAX_EVENTS:
                raise Rejected("Witness event budget exhausted")
            next_anchor = advance(self.root, anchor, e, seen)  # Authenticate before expensive science.
            checked = self._science(e.payload.candidate)
            prepared = self._prepared(intent, anchor, next_anchor, checked)
            with self._connection() as c:
                c.execute("BEGIN IMMEDIATE")
                current, _, _, pending, _ = self._load(c)
                if current != anchor or pending is not None:
                    raise Rejected("Witness changed while science was checked")
                c.execute("INSERT INTO pending VALUES (1,?,?)", (intent, canonical(prepared)))
                self._guard_commit(c)
                c.execute("COMMIT")
            return prepared

    def finalize(self, intent_sha256: str):
        if (type(intent_sha256) is not str or len(intent_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in intent_sha256)):
            raise Rejected("Invalid exact intent digest")
        with self._lock, self._connection() as c:
            c.execute("BEGIN IMMEDIATE")
            anchor, _, events, pending, _ = self._load(c)
            for event in events:
                if digest(bytes.fromhex(event["intent"])) == intent_sha256:
                    c.execute("COMMIT")
                    return event["finalized"]
            if pending is None or pending["intent_sha256"] != intent_sha256:
                raise Rejected("No unique checked pending transition")
            next_anchor = decode_anchor(pending["next_anchor"])
            prepared = canonical(pending["receipt"])
            finalized = sign(self.key, self.root, "finalized", {
                "intent_sha256": intent_sha256, "previous": anchor_json(anchor),
                "anchor": anchor_json(next_anchor), "prepared_sha256": digest(prepared)})
            c.execute("INSERT INTO events VALUES (?,?,?,?)", (next_anchor.generation,
                      bytes.fromhex(pending["intent"]), prepared, canonical(finalized)))
            c.execute("UPDATE head SET anchor=? WHERE id=1", (canonical(anchor_json(next_anchor)),))
            c.execute("DELETE FROM pending WHERE id=1")
            self._guard_commit(c)
            c.execute("COMMIT")
            return finalized

    def _view(self, nonce, export):
        if type(nonce) is not bytes or len(nonce) != 32:
            raise Rejected("Fresh 32-byte receiver nonce required")
        with self._lock, self._connection() as c:
            c.execute("BEGIN")
            anchor, _, events, pending, genesis = self._load(c)
            c.execute("COMMIT")
        payload = self._payload(anchor, events, pending, genesis, export)
        return sign(self.key, self.root, "export" if export else "checkpoint", payload, nonce)

    def checkpoint(self, nonce: bytes):
        return self._view(nonce, False)

    def export(self, nonce: bytes):
        return self._view(nonce, True)
