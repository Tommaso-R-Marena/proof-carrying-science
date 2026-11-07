"""Experimental, offline, fail-closed multi-agent authorization gate.

Not a deployed security boundary. No executable external tools are exposed.
Cryptographic statements are conditional on trusted key custody and the crypto library.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

DOMAIN = b"PCS-DELEGATED-ACTION-v1\x00"
CAPS = frozenset({"append:public/report", "append:private/notes", "delete:private/notes"})
RISKY = frozenset({"append:private/notes", "delete:private/notes"})
RESOURCES = ("public/report", "private/notes")
MAX_PAYLOAD = 512
MAX_STATE = 4096
MAX_CHAIN = 6
MAX_HISTORY = 4096
ZERO = "0" * 64
NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}\Z", re.ASCII)


class Denied(ValueError):
    pass


def _is_int(x):
    return type(x) is int


def _check_json(x, depth=0):
    if depth > 12:
        raise Denied("JSON nesting")
    if x is None or type(x) is bool or _is_int(x):
        if _is_int(x) and not -(1 << 63) <= x < (1 << 63):
            raise Denied("integer out of range")
        return
    if type(x) is str:
        if any(ord(c) < 32 or ord(c) > 126 for c in x):
            raise Denied("noncanonical string")
        if len(x) > 4096:
            raise Denied("string too long")
        return
    if type(x) is list:
        if len(x) > 16:
            raise Denied("list too long")
        for v in x:
            _check_json(v, depth + 1)
        return
    if type(x) is dict:
        if len(x) > 20 or any(type(k) is not str for k in x):
            raise Denied("bad object")
        for k, v in x.items():
            _check_json(k, depth + 1)
            _check_json(v, depth + 1)
        return
    raise Denied("unsupported JSON type")


def canonical(x) -> bytes:
    _check_json(x)
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def loads(data: bytes):
    if type(data) is not bytes or len(data) > 32768:
        raise Denied("invalid input bytes")
    def pair_check(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise Denied("duplicate JSON key")
            result[k] = v
        return result
    def no_float(_):
        raise Denied("floating-point values disallowed")
    try:
        obj = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pair_check,
                         parse_float=no_float, parse_constant=no_float)
    except (UnicodeError, ValueError, TypeError, OverflowError) as e:
        raise Denied("invalid JSON") from e
    canonical(obj)
    return obj


def digest(x) -> str:
    return hashlib.sha256(canonical(x)).hexdigest()


def public_hex(private: Ed25519PrivateKey) -> str:
    return private.public_key().public_bytes(serialization.Encoding.Raw,
                                             serialization.PublicFormat.Raw).hex()


def sign(private: Ed25519PrivateKey, kind: str, body: dict) -> dict:
    signature = private.sign(DOMAIN + kind.encode("ascii") + b"\x00" + canonical(body)).hex()
    return {"body": body, "signature": signature}


def verify(public: str, kind: str, packet: dict) -> dict:
    if type(packet) is not dict or set(packet) != {"body", "signature"}:
        raise Denied("invalid signed packet")
    body, sig = packet["body"], packet["signature"]
    if type(body) is not dict or type(sig) is not str or len(sig) != 128:
        raise Denied("invalid signature format")
    try:
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public))
        pk.verify(bytes.fromhex(sig), DOMAIN + kind.encode("ascii") + b"\x00" + canonical(body))
    except (ValueError, InvalidSignature, TypeError) as e:
        raise Denied("signature invalid") from e
    return body


def _fields(obj, names):
    if type(obj) is not dict or set(obj) != set(names):
        raise Denied("unexpected fields")


def _name(x):
    if type(x) is not str or not NAME.fullmatch(x):
        raise Denied("invalid identifier")


def validate_chain(chain, trusted_root: str, epoch: int, now: int) -> tuple[str, tuple[str, ...]]:
    if type(chain) is not list or not (1 <= len(chain) <= MAX_CHAIN):
        raise Denied("invalid delegation depth")
    parent = None
    ids = set()
    for item in chain:
        if type(item) is not dict or "body" not in item or type(item["body"]) is not dict:
            raise Denied("invalid grant")
        b = item["body"]
        _fields(b, {"id", "issuer", "subject", "parent", "caps", "delegate", "epoch", "not_before", "expires"})
        _name(b["id"])
        if b["id"] in ids:
            raise Denied("delegation cycle")
        ids.add(b["id"])
        if not all(type(b[k]) is str and len(b[k]) == 64 for k in ("issuer", "subject")):
            raise Denied("bad principal")
        if not (_is_int(b["epoch"]) and _is_int(b["not_before"]) and _is_int(b["expires"])):
            raise Denied("invalid times")
        if b["epoch"] != epoch or not b["not_before"] <= now < b["expires"]:
            raise Denied("grant stale")
        if type(b["delegate"]) is not bool or type(b["caps"]) is not list:
            raise Denied("invalid caps")
        if (not b["caps"] or any(type(cap) is not str for cap in b["caps"])
            or len(set(b["caps"])) != len(b["caps"]) or not set(b["caps"]) <= CAPS):
            raise Denied("bad capability")
        expected_issuer = trusted_root if parent is None else parent["subject"]
        if b["issuer"] != expected_issuer or b["parent"] != (None if parent is None else parent["id"]):
            raise Denied("broken lineage")
        if parent is not None:
            if not parent["delegate"] or not set(b["caps"]) <= set(parent["caps"]):
                raise Denied("delegation amplified")
            if b["not_before"] < parent["not_before"] or b["expires"] > parent["expires"]:
                raise Denied("delegation widened time")
        verify(expected_issuer, "grant", item)
        parent = b
    return parent["subject"], tuple(parent["caps"])


def _action_fields(action):
    _fields(action, {"id", "agent", "cap", "payload", "expected_version", "epoch", "preimage_sha256"})
    _name(action["id"])
    if type(action["agent"]) is not str or len(action["agent"]) != 64:
        raise Denied("invalid agent key")
    if (type(action["cap"]) is not str or action["cap"] not in CAPS
        or type(action["payload"]) is not str):
        raise Denied("invalid action")
    if len(action["payload"]) > MAX_PAYLOAD or (action["cap"].startswith("delete:") and action["payload"]):
        raise Denied("invalid payload")
    if not _is_int(action["expected_version"]) or not _is_int(action["epoch"]):
        raise Denied("invalid state version")
    if type(action["preimage_sha256"]) is not str or len(action["preimage_sha256"]) != 64:
        raise Denied("invalid preimage")


def _review_ok(review, action, chain, trusted_reviewer, now):
    b = verify(trusted_reviewer, "review", review)
    _fields(b, {"id", "action_sha256", "chain_sha256", "epoch", "expected_version", "preimage_sha256", "expires"})
    _name(b["id"])
    if (not _is_int(b["expires"]) or not _is_int(b["epoch"])
        or not _is_int(b["expected_version"]) or now >= b["expires"]):
        raise Denied("review expired or malformed")
    if (b["action_sha256"] != digest(action) or b["chain_sha256"] != digest(chain)
        or b["epoch"] != action["epoch"] or b["expected_version"] != action["expected_version"]
        or b["preimage_sha256"] != action["preimage_sha256"]):
        raise Denied("review not bound to proposal")
    return b["id"]


class Gate:
    """Local transactional resource simulator: no network/filesystem effect adapter."""
    def __init__(self, db_path: str | Path, *, root_public: str, reviewer_public: str,
                 clock: Callable[[], int] | None = None):
        self.db_path = str(db_path)
        self.root = root_public
        self.reviewer = reviewer_public
        self.clock = clock or (lambda: int(time.time()))
        # Trusted keys must be configured out-of-band, never from a model response.
        if len(bytes.fromhex(root_public)) != 32 or len(bytes.fromhex(reviewer_public)) != 32:
            raise ValueError("bad trust roots")
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (one INTEGER PRIMARY KEY CHECK(one=1), version INTEGER NOT NULL, epoch INTEGER NOT NULL, head TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS resources (name TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS used_reviews (nonce TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS events (version INTEGER PRIMARY KEY, record TEXT NOT NULL, hash TEXT NOT NULL);
            """)
            db.execute("INSERT OR IGNORE INTO meta VALUES (1,0,0,?)", (ZERO,))
            for n in RESOURCES:
                db.execute("INSERT OR IGNORE INTO resources VALUES (?, '')", (n,))

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            yield db
        finally:
            db.close()

    def snapshot(self):
        with self._db() as db:
            v, e, head = db.execute("SELECT version,epoch,head FROM meta WHERE one=1").fetchone()
            rows = dict(db.execute("SELECT name,body FROM resources"))
        return {"version": v, "epoch": e, "head": head, "resources": rows}

    def _commit_event(self, db, version, epoch, head, event):
        record = {"version": version+1, "epoch": epoch, "prior": head, "event": event}
        h = digest(record)
        db.execute("INSERT INTO events VALUES (?,?,?)", (version+1, canonical(record).decode("ascii"), h))
        db.execute("UPDATE meta SET version=?,epoch=?,head=? WHERE one=1", (version+1, epoch, h))
        return {"version": version+1, "epoch": epoch, "head": h, "event": event["kind"]}

    def apply(self, request: dict, chain: list, review: dict | None = None):
        """The only action path: verify at commit time inside the SQLite writer lock."""
        now = self.clock()
        if not _is_int(now):
            raise Denied("untrusted clock")
        canonical({"request": request, "chain": chain, "review": review})
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._verify_state(db)
                version, epoch, head = db.execute("SELECT version,epoch,head FROM meta WHERE one=1").fetchone()
                if version >= MAX_HISTORY:
                    raise Denied("history budget exhausted")
                if version:
                    last = loads(db.execute("SELECT record FROM events WHERE version=?", (version,)).fetchone()[0].encode("ascii"))
                    if now < last["event"]["observed_at"]:
                        raise Denied("clock rollback")
                if type(request) is not dict or "body" not in request:
                    raise Denied("missing request")
                action = request["body"]
                _action_fields(action)
                if action["epoch"] != epoch or action["expected_version"] != version:
                    raise Denied("stale world state")
                principal, caps = validate_chain(chain, self.root, epoch, now)
                if action["agent"] != principal or action["cap"] not in caps:
                    raise Denied("agent not authorized")
                verify(principal, "action", request)
                resource = action["cap"].split(":", 1)[1]
                old = db.execute("SELECT body FROM resources WHERE name=?", (resource,)).fetchone()[0]
                old_hash = hashlib.sha256(old.encode("ascii")).hexdigest()
                if action["preimage_sha256"] != old_hash:
                    raise Denied("stale resource preimage")
                review_id = None
                if action["cap"] in RISKY:
                    if review is None:
                        raise Denied("human-review proof missing")
                    review_id = _review_ok(review, action, chain, self.reviewer, now)
                    if db.execute("SELECT 1 FROM used_reviews WHERE nonce=?", (review_id,)).fetchone():
                        raise Denied("review replay")
                elif review is not None:
                    raise Denied("unexpected review")
                if action["cap"].startswith("append:"):
                    new = old + action["payload"]
                else:
                    new = ""  # modeled delete only; no external resource is touched
                if len(new) > MAX_STATE:
                    raise Denied("state budget exceeded")
                db.execute("UPDATE resources SET body=? WHERE name=?", (new, resource))
                if review_id is not None:
                    db.execute("INSERT INTO used_reviews VALUES (?)", (review_id,))
                event = {"kind": "action", "request": request, "chain": chain, "review": review,
                         "resource": resource, "before": old, "after": new, "observed_at": now}
                receipt = self._commit_event(db, version, epoch, head, event)
                db.execute("COMMIT")
                return receipt
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def rotate_epoch(self, root_command: dict):
        """Revokes every existing lease and approval, not just a single agent."""
        now = self.clock()
        canonical(root_command)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._verify_state(db)
                version, epoch, head = db.execute("SELECT version,epoch,head FROM meta WHERE one=1").fetchone()
                if version >= MAX_HISTORY:
                    raise Denied("history budget exhausted")
                if version:
                    last = loads(db.execute("SELECT record FROM events WHERE version=?", (version,)).fetchone()[0].encode("ascii"))
                    if now < last["event"]["observed_at"]:
                        raise Denied("clock rollback")
                b = verify(self.root, "rotate", root_command)
                _fields(b, {"id", "expected_version", "epoch", "kind"})
                _name(b["id"])
                if b["kind"] != "rotate" or b["expected_version"] != version or b["epoch"] != epoch:
                    raise Denied("stale root command")
                event = {"kind": "rotate", "command": root_command, "observed_at": now}
                receipt = self._commit_event(db, version, epoch+1, head, event)
                db.execute("COMMIT")
                return receipt
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def replay(self, expected_head: str | None = None):
        """Recompute hash chain and local effects; caller pins external head if available."""
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                outcome = self._verify_state(db, expected_head)
                db.execute("COMMIT")
                return outcome
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def _verify_state(self, db, expected_head: str | None = None):
        rows = db.execute("SELECT version,record,hash FROM events ORDER BY version").fetchall()
        meta = db.execute("SELECT version,epoch,head FROM meta WHERE one=1").fetchone()
        resources = dict(db.execute("SELECT name,body FROM resources"))
        nonces = {r[0] for r in db.execute("SELECT nonce FROM used_reviews")}
        if len(rows) > MAX_HISTORY:
            raise Denied("history budget exceeded")
        head, epoch = ZERO, 0
        modeled = {n: "" for n in RESOURCES}
        approved = set()
        last_time = -1
        for i, (version, raw, h) in enumerate(rows, 1):
            record = loads(raw.encode("ascii"))
            if version != i or record["version"] != i or record["prior"] != head or h != digest(record):
                raise Denied("history corrupted")
            evt = record["event"]
            if not _is_int(evt["observed_at"]) or evt["observed_at"] < last_time:
                raise Denied("history clock regressed")
            last_time = evt["observed_at"]
            if evt["kind"] == "rotate":
                b = verify(self.root, "rotate", evt["command"])
                if b != {"id": b["id"], "expected_version": i-1, "epoch": epoch, "kind": "rotate"}:
                    raise Denied("bad historic rotation")
                epoch += 1
            elif evt["kind"] == "action":
                a = evt["request"]["body"]
                _action_fields(a)
                if a["expected_version"] != i-1 or a["epoch"] != epoch:
                    raise Denied("invalid historical version")
                principal, caps = validate_chain(evt["chain"], self.root, epoch, evt["observed_at"])
                if principal != a["agent"] or a["cap"] not in caps:
                    raise Denied("invalid historical authority")
                verify(principal, "action", evt["request"])
                resource = a["cap"].split(":", 1)[1]
                old = modeled[resource]
                if evt["resource"] != resource or evt["before"] != old or a["preimage_sha256"] != hashlib.sha256(old.encode("ascii")).hexdigest():
                    raise Denied("invalid historical preimage")
                if a["cap"] in RISKY:
                    if evt["review"] is None:
                        raise Denied("missing historic review")
                    review_id = _review_ok(evt["review"], a, evt["chain"], self.reviewer, evt["observed_at"])
                    if review_id in approved:
                        raise Denied("historic review reused")
                    approved.add(review_id)
                elif evt["review"] is not None:
                    raise Denied("unexpected historic review")
                new = old + a["payload"] if a["cap"].startswith("append:") else ""
                if len(new) > MAX_STATE or evt["after"] != new:
                    raise Denied("historic effect mismatch")
                modeled[resource] = new
            else:
                raise Denied("unknown event kind")
            if record["epoch"] != epoch:
                raise Denied("historical epoch mismatch")
            head = h
        if (len(rows), epoch, head) != meta or modeled != resources or nonces != approved:
            raise Denied("final state mismatch")
        if expected_head is not None and head != expected_head:
            raise Denied("external anchor mismatch")
        return {"events_verified": len(rows), "epoch": epoch, "head": head}
