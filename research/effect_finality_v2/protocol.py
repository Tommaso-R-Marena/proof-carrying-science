"""Isolated, offline authorization-to-effect finality research model.

Only a local SQLite sink is implemented. Nothing here can send real messages,
move money, execute code, delete files, or contact a remote service.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from research.delegated_action_gate_v1.gate import (
    Denied, canonical, loads, digest, sign, verify as _legacy_verify, validate_chain, public_hex,
    _fields, _is_int, _name, MAX_HISTORY,
)

LOWER_SIG = re.compile(r"[0-9a-f]{128}\Z", re.ASCII)


def verify(public, kind, packet):
    """Reject signature-text malleability before hashing token bytes into receipts."""
    if type(packet) is not dict or type(packet.get("signature")) is not str or not LOWER_SIG.fullmatch(packet["signature"]):
        raise Denied("noncanonical signature spelling")
    return _legacy_verify(public, kind, packet)


PROVIDER = "local-private-note-v2"
CAP = "append:private/notes"
ZERO = "0" * 64
MAX_BODY = 512
MAX_TOTAL = 4096


def hash_body(s: str) -> str:
    return hashlib.sha256(s.encode("ascii")).hexdigest()


def _ascii(s, limit=MAX_BODY):
    if type(s) is not str or len(s) > limit or any(ord(c) < 32 or ord(c) > 126 for c in s):
        raise Denied("invalid ASCII text")


def _action(a):
    _fields(a, {"id", "intent", "agent", "cap", "payload", "epoch", "gate_version",
                "sink_version", "sink_preimage", "provider"})
    _name(a["id"])
    _name(a["intent"])
    if (type(a["agent"]) is not str or len(a["agent"]) != 64 or a["cap"] != CAP
        or a["provider"] != PROVIDER or not all(_is_int(a[k]) for k in ("epoch", "gate_version", "sink_version"))
        or type(a["sink_preimage"]) is not str or len(a["sink_preimage"]) != 64):
        raise Denied("invalid action")
    _ascii(a["payload"])
    if not a["payload"]:
        raise Denied("empty effects forbidden")


def _review(token, action, chain, reviewer_public, now):
    b = verify(reviewer_public, "effect-v2-review", token)
    _fields(b, {"id", "action_sha256", "chain_sha256", "expires", "epoch"})
    _name(b["id"])
    if (not _is_int(b["expires"]) or b["expires"] <= now
        or b["epoch"] != action["epoch"] or b["action_sha256"] != digest(action)
        or b["chain_sha256"] != digest(chain)):
        raise Denied("missing, expired, or unbound review")
    return b["id"]


def _rotate_body(command, root, current_epoch, gate_version):
    b = verify(root, "effect-v2-rotate", command)
    _fields(b, {"id", "epoch", "new_epoch", "expected_gate_version"})
    _name(b["id"])
    if (not all(_is_int(b[k]) for k in ("epoch", "new_epoch", "expected_gate_version"))
        or b["epoch"] != current_epoch or b["new_epoch"] != current_epoch + 1
        or b["expected_gate_version"] != gate_version):
        raise Denied("invalid or stale rotation")
    return b


@contextmanager
def _db(path):
    c = sqlite3.connect(str(path), isolation_level=None, timeout=8)
    c.execute("PRAGMA busy_timeout=8000")
    try:
        yield c
    finally:
        c.close()


class SignedSink:
    """Separate simulated provider. Its idempotency and epoch fences are trusted contracts."""
    def __init__(self, path: str | Path, *, sink_private: Ed25519PrivateKey,
                 gateway_public: str, root_public: str, clock: Callable[[], int] | None = None):
        self.path = str(path)
        self.clock = clock or (lambda: int(time.time()))
        self.key = sink_private
        self.gateway_public = gateway_public
        self.root_public = root_public
        with _db(self.path) as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS state (one INTEGER PRIMARY KEY CHECK(one=1),
                    version INTEGER NOT NULL, epoch INTEGER NOT NULL, body TEXT NOT NULL,
                    last_seen INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS effects (rid TEXT PRIMARY KEY, permit_hash TEXT NOT NULL,
                    receipt TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS fences (epoch INTEGER PRIMARY KEY, rotation_hash TEXT NOT NULL,
                    certificate TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS trust (one INTEGER PRIMARY KEY CHECK(one=1),config TEXT NOT NULL);
            """)
            c.execute("INSERT OR IGNORE INTO state VALUES(1,0,0,'',-1)")
            config=canonical({"root":root_public,"gateway":gateway_public,"sink":public_hex(sink_private),"provider":PROVIDER}).decode("ascii")
            c.execute("INSERT OR IGNORE INTO trust VALUES (1,?)",(config,))
            if c.execute("SELECT config FROM trust WHERE one=1").fetchone() != (config,):
                raise Denied("sink trust configuration changed on restart")
            self._trust=config

    def _verify_trust(self,c):
        if c.execute("SELECT config FROM trust WHERE one=1").fetchone() != (self._trust,):
            raise Denied("sink trust configuration changed")

    def _clock(self):
        now=self.clock()
        if not _is_int(now):raise Denied("invalid provider clock")
        return now

    def state(self):
        with _db(self.path) as c:
            self._verify_trust(c)
            v, e, body = c.execute("SELECT version,epoch,body FROM state WHERE one=1").fetchone()
        return {"provider": PROVIDER, "version": v, "epoch": e, "preimage": hash_body(body)}

    def snapshot(self):
        return sign(self.key, "effect-v2-snapshot", self.state())

    def deliver(self, permit: dict, *, simulate_response_loss=False):
        p = verify(self.gateway_public, "effect-v2-permit", permit)
        _fields(p, {"rid", "action_sha256", "chain_sha256", "review_sha256",
                    "epoch", "sink_version", "sink_preimage", "payload", "provider", "expires"})
        _name(p["rid"])
        if (p["provider"] != PROVIDER or not all(_is_int(p[k]) for k in ("epoch", "sink_version", "expires"))
            or any(type(p[k]) is not str or len(p[k]) != 64 for k in ("action_sha256", "chain_sha256", "review_sha256", "sink_preimage"))):
            raise Denied("bad dispatch permit")
        _ascii(p["payload"])
        if not p["payload"]:
            raise Denied("empty effect")
        permit_hash = digest(permit)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._verify_trust(c)
                now=self._clock()
                previous = c.execute("SELECT permit_hash,receipt FROM effects WHERE rid=?", (p["rid"],)).fetchone()
                if previous:
                    if previous[0] != permit_hash:
                        raise Denied("conflicting idempotency request")
                    receipt = loads(previous[1].encode("ascii"))
                else:
                    v, epoch, body, last = c.execute("SELECT version,epoch,body,last_seen FROM state WHERE one=1").fetchone()
                    if now < last or now >= p["expires"]:
                        raise Denied("provider clock rollback or expired permit")
                    if p["epoch"] != epoch or p["sink_version"] != v or p["sink_preimage"] != hash_body(body):
                        raise Denied("revoked or stale provider state")
                    new_body = body + p["payload"]
                    if len(new_body) > MAX_TOTAL:
                        raise Denied("provider capacity")
                    c.execute("UPDATE state SET version=?,body=?,last_seen=? WHERE one=1", (v+1, new_body, now))
                    receipt = sign(self.key, "effect-v2-receipt", {
                        "outcome": "APPLIED", "rid": p["rid"], "permit_sha256": permit_hash,
                        "epoch": epoch, "sink_version": v+1, "postimage": hash_body(new_body),
                    })
                    c.execute("INSERT INTO effects VALUES(?,?,?)", (p["rid"], permit_hash,
                                                                           canonical(receipt).decode("ascii")))
                c.execute("COMMIT")
            except BaseException:
                c.execute("ROLLBACK")
                raise
        if simulate_response_loss:
            raise TimeoutError("simulated lost response AFTER sink commit")
        return receipt

    def receipt_if_applied(self, rid: str):
        _name(rid)
        with _db(self.path) as c:
            self._verify_trust(c)
            item = c.execute("SELECT receipt FROM effects WHERE rid=?", (rid,)).fetchone()
        return None if item is None else loads(item[0].encode("ascii"))

    def fence(self, signed_rotation: dict):
        b = verify(self.root_public, "effect-v2-rotate", signed_rotation)
        _fields(b, {"id", "epoch", "new_epoch", "expected_gate_version"})
        if not all(_is_int(b[k]) for k in ("epoch", "new_epoch", "expected_gate_version")):
            raise Denied("invalid rotation")
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._verify_trust(c)
                now=self._clock()
                v, epoch, body, last = c.execute("SELECT version,epoch,body,last_seen FROM state WHERE one=1").fetchone()
                if now < last:raise Denied("provider clock rollback")
                row = c.execute("SELECT certificate,rotation_hash FROM fences WHERE epoch=?", (b["new_epoch"],)).fetchone()
                if row and row[1] == digest(signed_rotation):
                    cert = loads(row[0].encode("ascii"))
                else:
                    if b["epoch"] != epoch or b["new_epoch"] != epoch + 1:
                        raise Denied("out-of-order or conflicting fence")
                    c.execute("UPDATE state SET epoch=?,last_seen=? WHERE one=1", (b["new_epoch"],now))
                    cert = sign(self.key, "effect-v2-fence", {
                        "new_epoch": b["new_epoch"], "rotation_sha256": digest(signed_rotation),
                        "sink_version": v, "postimage": hash_body(body),
                    })
                    c.execute("INSERT INTO fences VALUES(?,?,?)", (
                        b["new_epoch"], digest(signed_rotation), canonical(cert).decode("ascii")))
                c.execute("COMMIT")
            except BaseException:
                c.execute("ROLLBACK")
                raise
        return cert

    def no_effect_after_fence(self, permit: dict):
        p = verify(self.gateway_public, "effect-v2-permit", permit)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._verify_trust(c)
                v, epoch, _body = c.execute("SELECT version,epoch,body FROM state WHERE one=1").fetchone()
                if not _is_int(p.get("epoch")) or epoch <= p["epoch"]:
                    raise Denied("cannot certify absence before provider fence")
                if c.execute("SELECT 1 FROM effects WHERE rid=?", (p["rid"],)).fetchone():
                    raise Denied("effect was committed; cannot certify absence")
                cert = sign(self.key, "effect-v2-receipt", {
                    "outcome": "NO_EFFECT", "rid": p["rid"], "permit_sha256": digest(permit),
                    "epoch": epoch, "sink_version": v, "postimage": None,
                })
                c.execute("COMMIT")
                return cert
            except BaseException:
                c.execute("ROLLBACK")
                raise


class EffectGate:
    """Approval reservation gateway; no external IO other than its local ledger."""
    def __init__(self, path: str | Path, *, root_public: str, reviewer_public: str,
                 sink_public: str, dispatch_private: Ed25519PrivateKey,
                 clock: Callable[[], int] | None = None):
        self.path = str(path)
        self.root = root_public
        self.reviewer = reviewer_public
        self.sink = sink_public
        self.dispatch_private = dispatch_private
        self.clock = clock or (lambda: int(time.time()))
        if len({root_public, reviewer_public, public_hex(dispatch_private), sink_public}) != 4:
            raise Denied("trust roles must have distinct signing keys")
        with _db(self.path) as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS meta (one INTEGER PRIMARY KEY CHECK(one=1),
                    version INTEGER NOT NULL, epoch INTEGER NOT NULL, pending INTEGER NOT NULL,
                    rotation TEXT, head TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reservations (rid TEXT PRIMARY KEY,
                    intent TEXT NOT NULL, action TEXT NOT NULL, chain TEXT NOT NULL, review TEXT NOT NULL,
                    review_id TEXT UNIQUE NOT NULL, epoch INTEGER NOT NULL, status TEXT NOT NULL,
                    permit TEXT, outcome TEXT);
                CREATE TABLE IF NOT EXISTS events (version INTEGER PRIMARY KEY,
                    record TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS trust (one INTEGER PRIMARY KEY CHECK(one=1),config TEXT NOT NULL);
            """)
            c.execute("INSERT OR IGNORE INTO meta VALUES(1,0,0,0,NULL,?)", (ZERO,))
            config=canonical({"root":root_public,"reviewer":reviewer_public,"sink":sink_public,
                              "gateway":public_hex(dispatch_private),"provider":PROVIDER}).decode("ascii")
            c.execute("INSERT OR IGNORE INTO trust VALUES(1,?)",(config,))
            if c.execute("SELECT config FROM trust WHERE one=1").fetchone() != (config,):
                raise Denied("gate trust configuration changed on restart")
            self._trust=config

    def status(self):
        with _db(self.path) as c:
            self._integrity(c)
            v, e, p, rot, head = c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
            count = c.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
        return {"version":v, "epoch":e, "cut_pending":bool(p), "head":head, "reservations":count}

    def _audit(self, c, kind: str, detail: dict, *, epoch=None, pending=None, rotation=None, now=None):
        now=self.clock() if now is None else now
        if not _is_int(now):raise Denied("non-integer host clock")
        v, e, p, rot, head = c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
        if v >= MAX_HISTORY:
            raise Denied("audit budget exceeded")
        if v:
            previous=loads(c.execute("SELECT record FROM events WHERE version=?",(v,)).fetchone()[0].encode("ascii"))
            if now < previous["observed_at"]:
                raise Denied("host clock moved backwards")
        record = {"version":v+1,"prior":head,"kind":kind,"detail":detail,"observed_at":now}
        h = digest(record)
        c.execute("INSERT INTO events VALUES (?,?,?)", (v+1, canonical(record).decode("ascii"),h))
        c.execute("UPDATE meta SET version=?,epoch=?,pending=?,rotation=?,head=? WHERE one=1", (
            v+1, e if epoch is None else epoch, p if pending is None else int(pending),
            rot if rotation is None else canonical(rotation).decode("ascii"), h))

    def _integrity(self, c, expected_head=None):
        if c.execute("SELECT config FROM trust WHERE one=1").fetchone() != (self._trust,):
            raise Denied("gate trust configuration changed")
        meta = c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
        records = c.execute("SELECT version,record,hash FROM events ORDER BY version").fetchall()
        if len(records) > MAX_HISTORY or len(records) != meta[0]:
            raise Denied("audit length mismatch")
        head = ZERO
        epoch = 0
        pending = 0
        rotation = None
        transitions = {}
        review_ids = set()
        last_time=-1
        for i,(v,raw,h) in enumerate(records,1):
            r = loads(raw.encode("ascii"))
            _fields(r,{"version","prior","kind","detail","observed_at"})
            if (not _is_int(r["observed_at"]) or r["observed_at"] < last_time):
                raise Denied("historical clock regression")
            last_time=r["observed_at"]
            if v != i or r["version"] != i or r["prior"] != head or digest(r) != h:
                raise Denied("audit chain corruption")
            d = r["detail"]
            if r["kind"] == "RESERVE":
                _fields(d,{"rid","action","chain","review","review_id","observed_at","sink_snapshot"})
                if d["observed_at"] != r["observed_at"]:
                    raise Denied("timestamp mismatch")
                snap=verify(self.sink,"effect-v2-snapshot",d["sink_snapshot"])
                _fields(snap,{"provider","version","epoch","preimage"})
                a = verify(d["action"]["body"]["agent"], "effect-v2-action", d["action"])
                _action(a)
                if any(type(q) is not dict or type(q.get("signature")) is not str or not LOWER_SIG.fullmatch(q["signature"]) for q in d["chain"]):
                    raise Denied("noncanonical historic grant")
                principal,caps = validate_chain(d["chain"], self.root, epoch, d["observed_at"])
                if (principal != a["agent"] or CAP not in caps or a["epoch"] != epoch
                    or a["gate_version"] != i-1 or snap["provider"] != PROVIDER
                    or snap["epoch"] != epoch or snap["version"] != a["sink_version"]
                    or snap["preimage"] != a["sink_preimage"] or pending):
                    raise Denied("unauthorized historical reservation")
                reviewer_id = _review(d["review"],a,d["chain"],self.reviewer,d["observed_at"])
                if (d["review_id"] != reviewer_id or reviewer_id in review_ids or d["rid"] in transitions
                    or any(t["intent"] == a["intent"] and t["status"] not in ("NO_EFFECT", "ABANDONED")
                           for t in transitions.values())):
                    raise Denied("historical approval or unresolved intent replay")
                review_ids.add(reviewer_id)
                transitions[d["rid"]] = {"intent":a["intent"],"status":"RESERVED","action":d["action"],"chain":d["chain"],"review":d["review"],"review_id":reviewer_id,"epoch":epoch,"permit":None,"outcome":None}
            elif r["kind"] == "ISSUE":
                _fields(d,{"rid","permit"})
                item = transitions.get(d["rid"])
                if item is None or item["status"] != "RESERVED" or item["epoch"] != epoch or pending:
                    raise Denied("invalid historical issue")
                permit_body=self._check_permit(item,d["rid"],d["permit"])
                if r["observed_at"] >= permit_body["expires"]:
                    raise Denied("historically expired permit")
                item["permit"] = d["permit"]
                item["status"] = "IN_FLIGHT"
            elif r["kind"] == "RESULT":
                _fields(d,{"rid","receipt"})
                item = transitions.get(d["rid"])
                if item is None or item["status"] != "IN_FLIGHT":
                    raise Denied("invalid historical result")
                outcome = self._check_receipt(item,d["rid"],d["receipt"],epoch)
                item["outcome"] = d["receipt"]
                item["status"] = outcome
            elif r["kind"] == "ABANDON":
                _fields(d,{"rid"})
                item=transitions.get(d["rid"])
                if (item is None or item["status"]!="RESERVED"
                    or item["epoch"]>=epoch or pending):
                    raise Denied("invalid historical abandonment")
                item["status"]="ABANDONED"
            elif r["kind"] == "ROTATE":
                _fields(d,{"command"})
                if pending: raise Denied("overlapping historical rotations")
                _rotate_body(d["command"],self.root,epoch,i-1)
                rotation = d["command"]
                epoch += 1
                pending = 1
            elif r["kind"] == "FENCE":
                _fields(d,{"certificate"})
                cert = verify(self.sink, "effect-v2-fence",d["certificate"])
                _fields(cert,{"new_epoch","rotation_sha256","sink_version","postimage"})
                if not pending or cert["new_epoch"] != epoch or cert["rotation_sha256"] != digest(rotation):
                    raise Denied("invalid historical fence")
                pending = 0
            else:
                raise Denied("unknown audit transition")
            head=h
        if (meta[1],meta[2],meta[3],meta[4]) != (epoch,pending,None if rotation is None else canonical(rotation).decode("ascii"),head):
            raise Denied("audit metadata mismatch")
        db_rows = c.execute("SELECT rid,intent,action,chain,review,review_id,epoch,status,permit,outcome FROM reservations").fetchall()
        if set(x[0] for x in db_rows) != set(transitions):
            raise Denied("reservation index mismatch")
        for rid, intent, action, chain, review, review_id, e, status, permit, outcome in db_rows:
            t = transitions[rid]
            expected=(t["intent"],canonical(t["action"]).decode("ascii"), canonical(t["chain"]).decode("ascii"),
                      canonical(t["review"]).decode("ascii"),t["review_id"],t["epoch"],t["status"],
                      None if t["permit"] is None else canonical(t["permit"]).decode("ascii"),
                      None if t["outcome"] is None else canonical(t["outcome"]).decode("ascii"))
            if (intent,action,chain,review,review_id,e,status,permit,outcome) != expected:
                raise Denied("reservation index altered")
        if expected_head is not None and head != expected_head:
            raise Denied("independent checkpoint mismatch")
        return {"events_verified":len(records), "epoch":epoch,"pending":bool(pending),"head":head}

    def _check_permit(self,item,rid,permit):
        p=verify(public_hex(self.dispatch_private),"effect-v2-permit",permit)
        a=item["action"]["body"]
        expected={"rid":rid,"action_sha256":digest(a),"chain_sha256":digest(item["chain"]),
            "review_sha256":digest(item["review"]),"epoch":item["epoch"],
            "sink_version":a["sink_version"],"sink_preimage":a["sink_preimage"],
            "payload":a["payload"],"provider":PROVIDER,
            "expires":min([item["review"]["body"]["expires"]] + [g["body"]["expires"] for g in item["chain"]])}
        if p != expected:
            raise Denied("permit substitution")
        return p

    def _check_receipt(self,item,rid,receipt,current_epoch):
        b=verify(self.sink,"effect-v2-receipt",receipt)
        _fields(b,{"outcome","rid","permit_sha256","epoch","sink_version","postimage"})
        if b["rid"] != rid or b["permit_sha256"] != digest(item["permit"]):
            raise Denied("unbound sink receipt")
        if b["outcome"] == "APPLIED":
            if b["epoch"] != item["epoch"] or not _is_int(b["sink_version"]) or type(b["postimage"]) is not str or len(b["postimage"]) != 64:
                raise Denied("invalid applied receipt")
            return "APPLIED"
        if b["outcome"] == "NO_EFFECT":
            if not _is_int(b["epoch"]) or b["epoch"] <= item["epoch"] or b["epoch"] > current_epoch or not _is_int(b["sink_version"]) or b["postimage"] is not None:
                raise Denied("invalid no-effect receipt")
            return "NO_EFFECT"
        raise Denied("invalid outcome")

    def reserve(self, signed_action, chain, signed_review, sink_snapshot):
        now=self.clock()
        if not _is_int(now): raise Denied("clock must return integer")
        canonical({"request":signed_action,"chain":chain,"review":signed_review,"sink_snapshot":sink_snapshot})
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._integrity(c)
                version,epoch,pending,_,_=c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
                if pending: raise Denied("revocation fence incomplete")
                a=signed_action["body"]
                _action(a)
                if a["epoch"]!=epoch or a["gate_version"]!=version:
                    raise Denied("stale gate view")
                if any(type(q) is not dict or type(q.get("signature")) is not str or not LOWER_SIG.fullmatch(q["signature"]) for q in chain):
                    raise Denied("noncanonical grant signature")
                principal,caps=validate_chain(chain,self.root,epoch,now)
                if principal!=a["agent"] or CAP not in caps:
                    raise Denied("delegation does not authorize effect")
                verify(principal,"effect-v2-action",signed_action)
                review_id=_review(signed_review,a,chain,self.reviewer,now)
                s=verify(self.sink,"effect-v2-snapshot",sink_snapshot)
                _fields(s,{"provider","version","epoch","preimage"})
                if (s["provider"]!=PROVIDER or s["epoch"]!=epoch or s["version"]!=a["sink_version"]
                    or s["preimage"]!=a["sink_preimage"]):
                    raise Denied("wrong signed provider state")
                if c.execute("SELECT 1 FROM reservations WHERE rid=? OR review_id=?",(a["id"],review_id)).fetchone():
                    raise Denied("duplicate approval or reservation")
                if c.execute("SELECT 1 FROM reservations WHERE intent=? AND status NOT IN ('NO_EFFECT','ABANDONED')",(a["intent"],)).fetchone():
                    raise Denied("intent already accepted or outcome unknown")
                c.execute("INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,NULL,NULL)",(
                    a["id"],a["intent"],canonical(signed_action).decode("ascii"),canonical(chain).decode("ascii"),
                    canonical(signed_review).decode("ascii"),review_id,epoch,"RESERVED"))
                self._audit(c,"RESERVE",{"rid":a["id"],"action":signed_action,"chain":chain,
                                         "review":signed_review,"review_id":review_id,"observed_at":now,"sink_snapshot":sink_snapshot},now=now)
                c.execute("COMMIT")
                return a["id"]
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def _get(self,c,rid):
        row=c.execute("SELECT intent,action,chain,review,review_id,epoch,status,permit,outcome FROM reservations WHERE rid=?",(rid,)).fetchone()
        if row is None: raise Denied("unknown reservation")
        return {"intent":row[0],"action":loads(row[1].encode("ascii")),"chain":loads(row[2].encode("ascii")),
                "review":loads(row[3].encode("ascii")),"review_id":row[4],"epoch":row[5],
                "status":row[6],"permit":None if row[7] is None else loads(row[7].encode("ascii")),
                "outcome":None if row[8] is None else loads(row[8].encode("ascii"))}

    def issue(self,rid):
        _name(rid)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._integrity(c)
                _,epoch,pending,_,_=c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
                t=self._get(c,rid)
                if pending or t["epoch"]!=epoch or t["status"] not in ("RESERVED","IN_FLIGHT"):
                    raise Denied("cannot dispatch revoked or finalized reservation")
                now=self.clock()
                if not _is_int(now):raise Denied("invalid gateway clock")
                if any(type(q) is not dict or type(q.get("signature")) is not str or not LOWER_SIG.fullmatch(q["signature"]) for q in t["chain"]):
                    raise Denied("noncanonical grant")
                principal,caps=validate_chain(t["chain"],self.root,epoch,now)
                if principal!=t["action"]["body"]["agent"] or CAP not in caps:
                    raise Denied("delegation no longer valid")
                _review(t["review"],t["action"]["body"],t["chain"],self.reviewer,now)
                if t["status"] == "IN_FLIGHT":
                    permit=t["permit"]  # exact retry, only while authority still current
                else:
                    a=t["action"]["body"]
                    permit=sign(self.dispatch_private,"effect-v2-permit",{
                        "rid":rid,"action_sha256":digest(a),"chain_sha256":digest(t["chain"]),
                        "review_sha256":digest(t["review"]),"epoch":epoch,
                        "sink_version":a["sink_version"],"sink_preimage":a["sink_preimage"],
                        "payload":a["payload"],"provider":PROVIDER,
                        "expires":min([t["review"]["body"]["expires"]] + [g["body"]["expires"] for g in t["chain"]])})
                    self._check_permit(t,rid,permit)
                    c.execute("UPDATE reservations SET status='IN_FLIGHT',permit=? WHERE rid=?",(
                        canonical(permit).decode("ascii"),rid))
                    self._audit(c,"ISSUE",{"rid":rid,"permit":permit})
                c.execute("COMMIT")
                return permit
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def finish(self,rid,receipt):
        _name(rid)
        canonical(receipt)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._integrity(c)
                epoch=c.execute("SELECT epoch FROM meta WHERE one=1").fetchone()[0]
                t=self._get(c,rid)
                if t["status"] in ("APPLIED","NO_EFFECT"):
                    if t["outcome"] != receipt: raise Denied("terminal result conflict")
                    c.execute("COMMIT")
                    return t["status"]
                if t["status"]!="IN_FLIGHT": raise Denied("effect not dispatched")
                outcome=self._check_receipt(t,rid,receipt,epoch)
                c.execute("UPDATE reservations SET status=?,outcome=? WHERE rid=?",(
                    outcome,canonical(receipt).decode("ascii"),rid))
                self._audit(c,"RESULT",{"rid":rid,"receipt":receipt})
                c.execute("COMMIT")
                return outcome
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def abandon_after_fence(self,rid):
        """Only a never-issued reservation can be safely cancelled without a sink result."""
        _name(rid)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._integrity(c)
                _,epoch,pending,_,_=c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
                t=self._get(c,rid)
                if pending or t["epoch"]>=epoch or t["status"]!="RESERVED":
                    raise Denied("cannot abandon a sent or unfenced effect")
                c.execute("UPDATE reservations SET status='ABANDONED' WHERE rid=?",(rid,))
                self._audit(c,"ABANDON",{"rid":rid})
                c.execute("COMMIT")
                return "ABANDONED"
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def revoke(self,signed_rotation):
        canonical(signed_rotation)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._integrity(c)
                version,epoch,pending,_,_=c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
                if pending: raise Denied("cannot rotate during unresolved fence")
                _rotate_body(signed_rotation,self.root,epoch,version)
                self._audit(c,"ROTATE",{"command":signed_rotation},epoch=epoch+1,pending=True,rotation=signed_rotation)
                c.execute("COMMIT")
                return epoch+1
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def complete_fence(self,certificate):
        canonical(certificate)
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._integrity(c)
                _,epoch,pending,rot,_=c.execute("SELECT version,epoch,pending,rotation,head FROM meta WHERE one=1").fetchone()
                b=verify(self.sink,"effect-v2-fence",certificate)
                _fields(b,{"new_epoch","rotation_sha256","sink_version","postimage"})
                if (not pending or b["new_epoch"]!=epoch
                    or b["rotation_sha256"]!=digest(loads(rot.encode("ascii")))):
                    raise Denied("mismatched fencing certificate")
                self._audit(c,"FENCE",{"certificate":certificate},pending=False)
                c.execute("COMMIT")
                return epoch
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def replay(self,expected_head=None):
        with _db(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                result=self._integrity(c,expected_head)
                c.execute("COMMIT")
                return result
            except BaseException:
                c.execute("ROLLBACK")
                raise

    def reservation(self,rid):
        _name(rid)
        with _db(self.path) as c:
            self._integrity(c)
            return self._get(c,rid)
