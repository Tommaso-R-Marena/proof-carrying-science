"""Persistent, replay-protecting receipt store for the PCS v3 semantic authority.

**Reference implementation (SQLite).  Tested, not formally verified.**

The Lean authority (``pcs-semantic-check --v3``) is a pure function of
``(authority, request, ledger snapshot, clock)``; its decision and state transition are proved
(``PCS.V2.Semantic.V3``).  This store supplies the snapshot and commits the transition.  The
properties below are **operational**: they rely on SQLite's transaction semantics (atomicity,
durability with ``synchronous=FULL``, exclusive write locks), on the file system honouring
``fsync``, on a trusted monotone clock, and on honest key management.

Protocol of ``ReceiptStore.certify`` (one exclusive transaction per request):

1. ``BEGIN IMMEDIATE`` — takes SQLite's reserved (single-writer) lock; concurrent certifications
   in other threads or processes are serialized here.
2. Clock check: ``now`` must be ≥ the largest clock value ever used by this store
   (``CLOCK_REGRESSION`` otherwise — fail closed).
3. Read the consumed nonces **restricted to the request's nonces**, the run-time revocations and
   the ledger genesis.  ``decideV3_restrict`` proves the decision on this restricted snapshot
   equals the decision on the full ledger.
4. Run the Lean binary on the exact request bytes.
5. Only if the outcome is ``CERTIFIED_TRANSLATION`` *and* the binary's ``consumed_nonces`` equal
   the request's nonces: insert them (``PRIMARY KEY (scope, nonce)`` — a uniqueness violation
   aborts the transaction, defence in depth), record the clock, ``COMMIT``.
6. Any other outcome, any error, any exception: ``ROLLBACK`` — nothing is consumed.
7. A certified result is returned **only after** ``COMMIT`` succeeded.  A crash before the
   commit consumes nothing and releases no certified result (the request can be retried, and
   then certifies at most once).

Lost persistence is fail-closed: ``ReceiptStore.open`` refuses a missing database or a database
for another scope.  Re-initialising a store requires an explicit ``initialize`` with a new
``genesis``; the authority rejects every receipt issued before the genesis
(``pre_genesis_receipt_rejected``), so — under a monotone clock — a receipt accepted in an
earlier epoch cannot be replayed after a reset.

Key revocation: ``revoke`` records a key in this scope; revocations are passed to the authority
in the snapshot (``revoked_key_rejected``).  Key rotation is expressed by validity windows in the
authority configuration (``inactive_key_rejected``).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .semantic_translation_v1 import canonical_json
from .receipts_v3 import LEDGER_STATE_SCHEMA, DECISION_V3_SCHEMA

_DEFAULT_BINARY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".lake", "build", "bin", "pcs-semantic-check")

STRENGTHENING_SCHEMA = "pcs-semantic-strengthening-decision-v3"
OUTCOMES_STRENGTHENING = ("CERTIFIED_STRENGTHENING", "NOT_A_STRENGTHENING", "INVALID_PROPOSAL",
                          "RECEIPT_REJECTED", "INVALID_AUTHORITY")

OUTCOMES_V3 = ("CERTIFIED_TRANSLATION", "VERIFIED_COUNTEREXAMPLE", "NEEDS_HUMAN_CLARIFICATION",
               "UNRESOLVED_PROOF_OBLIGATION", "UNSUPPORTED_FRAGMENT", "SEARCH_EXHAUSTED",
               "INVALID_PROPOSAL", "RECEIPT_REJECTED", "INVALID_AUTHORITY")


class StoreError(Exception):
    """Fail-closed store error (never a certification)."""


@dataclass
class StoreResult:
    outcome: str
    certified: bool
    decision: Optional[Dict[str, Any]]
    consumed: List[str] = field(default_factory=list)
    store_error: Optional[str] = None


def _connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=60.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(
  scope TEXT PRIMARY KEY,
  genesis INTEGER NOT NULL,
  last_clock INTEGER NOT NULL,
  store_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consumed(
  scope TEXT NOT NULL,
  nonce TEXT NOT NULL,
  consumed_at INTEGER NOT NULL,
  request_sha256 TEXT NOT NULL,
  PRIMARY KEY (scope, nonce)
);
CREATE TABLE IF NOT EXISTS revoked(
  scope TEXT NOT NULL,
  key TEXT NOT NULL,
  revoked_at INTEGER NOT NULL,
  PRIMARY KEY (scope, key)
);
"""


class ReceiptStore:
    def __init__(self, path: str, scope: str, binary: str = _DEFAULT_BINARY,
                 timeout: float = 600.0):
        self.path = path
        self.scope = scope
        self.binary = binary
        self.timeout = timeout

    # ------------------------------------------------------------------ lifecycle

    @classmethod
    def initialize(cls, path: str, scope: str, genesis: int, **kw) -> "ReceiptStore":
        if os.path.exists(path):
            con = _connect(path)
            try:
                row = con.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone()
                if row and con.execute("SELECT 1 FROM meta WHERE scope=?", (scope,)).fetchone():
                    raise StoreError("store already initialized for this scope; refusing to reset")
            finally:
                con.close()
        con = _connect(path)
        try:
            con.executescript(SCHEMA)
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT INTO meta(scope, genesis, last_clock, store_id) VALUES (?,?,?,?)",
                        (scope, genesis, genesis, os.urandom(16).hex()))
            con.execute("COMMIT")
        finally:
            con.close()
        return cls(path, scope, **kw)

    @classmethod
    def open(cls, path: str, scope: str, **kw) -> "ReceiptStore":
        """Fail closed on lost persistence: a missing database or scope is an error, never an
        empty ledger."""
        if not os.path.exists(path):
            raise StoreError("receipt store missing (lost persistence); refusing to run")
        con = _connect(path)
        try:
            row = con.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone()
            if not row or not con.execute("SELECT 1 FROM meta WHERE scope=?", (scope,)).fetchone():
                raise StoreError("receipt store not initialized for this scope")
        finally:
            con.close()
        return cls(path, scope, **kw)

    # ------------------------------------------------------------------ admin

    def revoke(self, key: str, at: int) -> None:
        con = _connect(self.path)
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT OR IGNORE INTO revoked(scope, key, revoked_at) VALUES (?,?,?)",
                        (self.scope, key, at))
            con.execute("COMMIT")
        finally:
            con.close()

    def consumed_nonces(self) -> List[str]:
        con = _connect(self.path)
        try:
            return [r[0] for r in con.execute(
                "SELECT nonce FROM consumed WHERE scope=? ORDER BY nonce", (self.scope,))]
        finally:
            con.close()

    def genesis(self) -> int:
        con = _connect(self.path)
        try:
            return con.execute("SELECT genesis FROM meta WHERE scope=?", (self.scope,)).fetchone()[0]
        finally:
            con.close()

    # ------------------------------------------------------------------ certification

    def _run_binary(self, authority_bytes: bytes, request_bytes: bytes,
                    state_bytes: bytes, mode: str = "translation") -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for name, data in (("authority.json", authority_bytes), ("request.json", request_bytes),
                               ("state.json", state_bytes)):
                p = os.path.join(d, name)
                with open(p, "wb") as f:
                    f.write(data)
                paths.append(p)
            flag = "--v3" if mode == "translation" else "--v3-strengthen"
            proc = subprocess.run([self.binary, flag, *paths], capture_output=True,
                                  timeout=self.timeout)
        try:
            dec = json.loads(proc.stdout.decode("utf-8"))
        except Exception as exc:  # fail closed
            raise StoreError(f"unparsable authority output (exit {proc.returncode}): {exc}")
        if mode == "strengthening":
            if dec.get("schema") != STRENGTHENING_SCHEMA or dec.get("outcome") not in OUTCOMES_STRENGTHENING:
                raise StoreError("authority output has an unexpected schema")
            expected_rc = 4 if dec["outcome"] == "CERTIFIED_STRENGTHENING" else 1
        else:
            if dec.get("schema") != DECISION_V3_SCHEMA or dec.get("outcome") not in OUTCOMES_V3:
                raise StoreError("authority output has an unexpected schema")
            expected_rc = {"CERTIFIED_TRANSLATION": 0, "VERIFIED_COUNTEREXAMPLE": 3}.get(dec["outcome"], 1)
        if proc.returncode != expected_rc:
            raise StoreError("authority exit code disagrees with its decision")
        return dec

    def certify(self, authority_bytes: bytes, request_bytes: bytes, now: Optional[int] = None,
                _crash_before_commit: bool = False, mode: str = "translation") -> StoreResult:
        """Atomic check-and-consume.  Never raises on a rejection; raises ``StoreError`` (and
        consumes nothing) on any operational failure.  ``mode="strengthening"`` runs the separate
        ``--v3-strengthen`` decision; its only accepting outcome is ``CERTIFIED_STRENGTHENING``
        (never reported as ``CERTIFIED_TRANSLATION``)."""
        if mode not in ("translation", "strengthening"):
            raise StoreError("unknown mode")
        accept = "CERTIFIED_TRANSLATION" if mode == "translation" else "CERTIFIED_STRENGTHENING"
        if now is None:
            now = int(time.time())
        try:
            req = json.loads(request_bytes.decode("utf-8"))
            nonces = [e["nonce"] for e in req.get("receipts", []) if isinstance(e, dict)
                      and isinstance(e.get("nonce"), str)]
        except Exception:
            req, nonces = None, []
        con = _connect(self.path)
        try:
            con.execute("BEGIN IMMEDIATE")
            try:
                meta = con.execute("SELECT genesis, last_clock FROM meta WHERE scope=?",
                                   (self.scope,)).fetchone()
                if meta is None:
                    raise StoreError("scope not initialized")
                genesis, last_clock = meta
                if now < last_clock:
                    con.execute("ROLLBACK")
                    return StoreResult("CLOCK_REGRESSION", False, None,
                                       store_error="clock moved backwards; refusing to decide")
                consumed = sorted({n for (n,) in con.execute(
                    "SELECT nonce FROM consumed WHERE scope=? AND nonce IN (%s)"
                    % ",".join("?" * len(nonces)), (self.scope, *nonces))}) if nonces else []
                revoked = sorted(k for (k,) in con.execute(
                    "SELECT key FROM revoked WHERE scope=?", (self.scope,)))
                state = {"consumed": consumed, "genesis": genesis, "now": now, "revoked": revoked,
                         "schema": LEDGER_STATE_SCHEMA}
                dec = self._run_binary(authority_bytes, request_bytes, canonical_json(state), mode)
                if dec["outcome"] != accept:
                    con.execute("ROLLBACK")
                    return StoreResult(dec["outcome"], False, dec)
                reported = (dec["consumed_nonces"] if mode == "translation"
                            else dec.get("new_ledger_consumed") or [])
                if sorted(reported) != sorted(nonces) or len(set(nonces)) != len(nonces):
                    raise StoreError("authority consumed-nonce set disagrees with the request")
                digest = hashlib.sha256(request_bytes).hexdigest()
                for n in nonces:
                    con.execute("INSERT INTO consumed(scope, nonce, consumed_at, request_sha256) "
                                "VALUES (?,?,?,?)", (self.scope, n, now, digest))
                con.execute("UPDATE meta SET last_clock=? WHERE scope=?", (max(now, last_clock), self.scope))
                if _crash_before_commit:
                    os._exit(77)  # simulated crash: the transaction is never committed
                con.execute("COMMIT")
                return StoreResult(accept, True, dec, consumed=list(nonces))
            except sqlite3.IntegrityError as exc:
                con.execute("ROLLBACK")
                return StoreResult("RECEIPT_REJECTED", False, None,
                                   store_error=f"nonce uniqueness violation: {exc}")
            except BaseException:
                try:
                    con.execute("ROLLBACK")
                except Exception:
                    pass
                raise
        finally:
            con.close()


def _main(argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="pcs-receipt-store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("db"); i.add_argument("scope"); i.add_argument("genesis", type=int)
    c = sub.add_parser("certify"); c.add_argument("db"); c.add_argument("scope")
    c.add_argument("authority"); c.add_argument("request"); c.add_argument("--now", type=int)
    c.add_argument("--binary", default=_DEFAULT_BINARY)
    c.add_argument("--crash-before-commit", action="store_true")
    v = sub.add_parser("revoke"); v.add_argument("db"); v.add_argument("scope"); v.add_argument("key")
    v.add_argument("at", type=int)
    s = sub.add_parser("status"); s.add_argument("db"); s.add_argument("scope")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "init":
            ReceiptStore.initialize(a.db, a.scope, a.genesis)
            print("INITIALIZED"); return 0
        if a.cmd == "revoke":
            ReceiptStore.open(a.db, a.scope).revoke(a.key, a.at); print("REVOKED"); return 0
        if a.cmd == "status":
            st = ReceiptStore.open(a.db, a.scope)
            print(json.dumps({"consumed": st.consumed_nonces(), "genesis": st.genesis()})); return 0
        st = ReceiptStore.open(a.db, a.scope, binary=a.binary)
        with open(a.authority, "rb") as f:
            ab = f.read()
        with open(a.request, "rb") as f:
            rb = f.read()
        res = st.certify(ab, rb, now=a.now, _crash_before_commit=a.crash_before_commit)
        print(json.dumps({"certified": res.certified, "consumed": res.consumed,
                          "outcome": res.outcome, "store_error": res.store_error}, sort_keys=True))
        return 0 if res.certified else 1
    except StoreError as exc:
        print(json.dumps({"certified": False, "outcome": "STORE_ERROR", "store_error": str(exc)}))
        return 2


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
