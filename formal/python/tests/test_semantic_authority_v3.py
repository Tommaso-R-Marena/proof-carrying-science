"""Tests of the PCS v3 stateful receipt authority and its persistent SQLite store.

These are operational tests of (a) the compiled ``pcs-semantic-check --v3`` binary, whose pure
decision function is proved in ``PCS/V2/TranslationV3*.lean``, and (b) the reference persistent
store ``pcs_semantic.receipt_store`` (tested, not verified).  Receipts are signed with the
``cryptography`` package using PUBLIC test seeds; they carry no authority.

Run from the project root:  python3 -m unittest discover -s python/tests -v
"""

from __future__ import annotations

import copy
import json
import multiprocessing
import os
import random
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "python"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from pcs_semantic.semantic_translation_v1 import canonical_json  # noqa: E402
from pcs_semantic import receipts_v3 as R  # noqa: E402
from pcs_semantic.receipt_store import ReceiptStore, StoreError  # noqa: E402
import gen_semantic_v3_fixtures as G  # noqa: E402

BIN = os.path.join(ROOT, ".lake", "build", "bin", "pcs-semantic-check")
FIX = os.path.join(ROOT, "fixtures", "semantic_authority_v3")
SCOPE = "pcs-fixture-scope-v3"


def _write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def run_v3(authority, request, state):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for n, obj in (("a", authority), ("r", request), ("s", state)):
            p = os.path.join(d, n + ".json")
            with open(p, "wb") as f:
                f.write(obj if isinstance(obj, bytes) else canonical_json(obj))
            paths.append(p)
        proc = subprocess.run([BIN, "--v3", *paths], capture_output=True, timeout=600)
    return json.loads(proc.stdout), proc.returncode


def new_store(d, genesis=G.GENESIS):
    return ReceiptStore.initialize(os.path.join(d, "ledger.sqlite"), SCOPE, genesis)


def _certify_in_subprocess(args):
    db, auth_path, req_path, now = args
    proc = subprocess.run([sys.executable, "-m", "pcs_semantic.receipt_store", "certify", db, SCOPE,
                           auth_path, req_path, "--now", str(now)],
                          capture_output=True, cwd=os.path.join(ROOT, "python"), timeout=600)
    return proc.returncode, proc.stdout.decode()


class FixtureFiles(unittest.TestCase):
    def test_committed_fixtures_regenerate_identically(self):
        before = {}
        for root, _, files in os.walk(FIX):
            for f in files:
                p = os.path.join(root, f)
                before[p] = _read(p)
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_semantic_v3_fixtures.py")],
                       check=True, capture_output=True)
        for p, data in before.items():
            self.assertEqual(_read(p), data, p)

    def test_every_fixture_matches_expectation(self):
        exp = json.loads(_read(os.path.join(FIX, "expected.json")))["fixtures"]
        self.assertGreaterEqual(len(exp), 37)
        for f in exp:
            a = _read(os.path.join(FIX, f["authority"]))
            r = _read(os.path.join(FIX, f["request"]))
            s = _read(os.path.join(FIX, f["state"]))
            d, rc = run_v3(a, r, s)
            self.assertEqual(d["outcome"], f["outcome"], f["name"])
            self.assertEqual(d["receipt_phase"]["status"], f["receipt_status"], f["name"])
            if d["outcome"] != "CERTIFIED_TRANSLATION":
                self.assertEqual(d["consumed_nonces"], [], f["name"])


class StoreReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.A = G.base_authority()
        self.ab = canonical_json(self.A)
        self.req = G.make_request(self.A, prefix="store")
        self.rb = canonical_json(self.req)

    def tearDown(self):
        self.tmp.cleanup()

    def test_certify_then_replay_rejected_same_process(self):
        st = new_store(self.d)
        r1 = st.certify(self.ab, self.rb, now=G.NOW)
        self.assertTrue(r1.certified)
        self.assertEqual(sorted(st.consumed_nonces()), sorted(e["nonce"] for e in self.req["receipts"]))
        r2 = st.certify(self.ab, self.rb, now=G.NOW + 1)
        self.assertFalse(r2.certified)
        self.assertEqual(r2.outcome, "RECEIPT_REJECTED")
        self.assertEqual(r2.decision["receipt_phase"]["failure"]["reason"], "REPLAY")

    def test_replay_across_process_boundaries_and_restart(self):
        new_store(self.d)
        db = os.path.join(self.d, "ledger.sqlite")
        ap, rp = os.path.join(self.d, "a.json"), os.path.join(self.d, "r.json")
        _write(ap, self.ab)
        _write(rp, self.rb)
        rc1, out1 = _certify_in_subprocess((db, ap, rp, G.NOW))
        self.assertEqual(rc1, 0, out1)
        self.assertTrue(json.loads(out1)["certified"])
        # a fresh process (simulated restart) sees the persisted ledger
        rc2, out2 = _certify_in_subprocess((db, ap, rp, G.NOW + 5))
        self.assertEqual(rc2, 1, out2)
        self.assertEqual(json.loads(out2)["outcome"], "RECEIPT_REJECTED")

    def test_concurrent_requests_one_nonce_exactly_one_certifies(self):
        new_store(self.d)
        db = os.path.join(self.d, "ledger.sqlite")
        ap = os.path.join(self.d, "a.json")
        _write(ap, self.ab)
        # eight distinct requests that all share the proof nonce, plus identical copies
        paths = []
        for i in range(8):
            req = G.make_request(self.A, prefix=f"conc{i}")
            # rewrite the proof envelope to a shared nonce and re-sign it with the proof key
            pe = req["receipts"][2]
            req["receipts"][2] = R.sign_envelope(G.K["proof"], "proof", pe["statement"],
                                                 "shared-proof-nonce", pe["issued_at"], pe["expires_at"])
            p = os.path.join(self.d, f"r{i}.json")
            _write(p, canonical_json(req))
            paths.append(p)
            paths.append(p)  # the identical request submitted twice
        with multiprocessing.Pool(8) as pool:
            results = pool.map(_certify_in_subprocess, [(db, ap, p, G.NOW) for p in paths])
        certified = [json.loads(o)["certified"] for rc, o in results]
        self.assertEqual(sum(certified), 1, results)
        st = ReceiptStore.open(db, SCOPE)
        self.assertEqual(st.consumed_nonces().count("shared-proof-nonce"), 1)

    def test_crash_before_commit_consumes_nothing_and_releases_nothing(self):
        new_store(self.d)
        db = os.path.join(self.d, "ledger.sqlite")
        ap, rp = os.path.join(self.d, "a.json"), os.path.join(self.d, "r.json")
        _write(ap, self.ab)
        _write(rp, self.rb)
        proc = subprocess.run([sys.executable, "-m", "pcs_semantic.receipt_store", "certify", db, SCOPE,
                               ap, rp, "--now", str(G.NOW), "--crash-before-commit"],
                              capture_output=True, cwd=os.path.join(ROOT, "python"), timeout=600)
        self.assertEqual(proc.returncode, 77)
        self.assertEqual(proc.stdout, b"")  # no result released
        st = ReceiptStore.open(db, SCOPE)
        self.assertEqual(st.consumed_nonces(), [])
        # retry certifies exactly once
        self.assertTrue(st.certify(self.ab, self.rb, now=G.NOW).certified)
        self.assertFalse(st.certify(self.ab, self.rb, now=G.NOW).certified)

    def test_lost_persistence_is_fail_closed(self):
        new_store(self.d)
        db = os.path.join(self.d, "ledger.sqlite")
        self.assertTrue(ReceiptStore.open(db, SCOPE).certify(self.ab, self.rb, now=G.NOW).certified)
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(db + suffix):
                os.remove(db + suffix)
        with self.assertRaises(StoreError):
            ReceiptStore.open(db, SCOPE)
        with self.assertRaises(StoreError):
            ReceiptStore.open(db, "another-scope")

    def test_reset_with_new_genesis_rejects_old_receipts(self):
        db = os.path.join(self.d, "ledger.sqlite")
        st = new_store(self.d)
        self.assertTrue(st.certify(self.ab, self.rb, now=G.NOW).certified)
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(db + suffix):
                os.remove(db + suffix)
        st2 = ReceiptStore.initialize(db, SCOPE, genesis=G.NOW + 10)
        r = st2.certify(self.ab, self.rb, now=G.NOW + 20)
        self.assertFalse(r.certified)
        self.assertEqual(r.decision["receipt_phase"]["failure"]["kind"], "BEFORE_GENESIS")

    def test_reinitialize_refused(self):
        db = os.path.join(self.d, "ledger.sqlite")
        new_store(self.d)
        with self.assertRaises(StoreError):
            ReceiptStore.initialize(db, SCOPE, genesis=0)

    def test_clock_regression_fail_closed(self):
        st = new_store(self.d)
        other = canonical_json(G.make_request(self.A, prefix="clock"))
        self.assertTrue(st.certify(self.ab, other, now=G.NOW + 100).certified)
        r = st.certify(self.ab, self.rb, now=G.NOW)
        self.assertFalse(r.certified)
        self.assertEqual(r.outcome, "CLOCK_REGRESSION")
        self.assertNotIn(self.req["receipts"][0]["nonce"], st.consumed_nonces())

    def test_runtime_revocation(self):
        st = new_store(self.d)
        st.revoke(G.K["proof"].public, at=G.NOW)
        r = st.certify(self.ab, self.rb, now=G.NOW)
        self.assertFalse(r.certified)
        self.assertEqual(r.decision["receipt_phase"]["failure"]["reason"], "REVOKED_KEY")
        self.assertEqual(st.consumed_nonces(), [])

    def test_rejected_requests_consume_nothing(self):
        st = new_store(self.d)
        bad = canonical_json(G.make_request(self.A, "neg_forall_to_exists", prefix="sem"))
        r = st.certify(self.ab, bad, now=G.NOW)
        self.assertEqual(r.outcome, "VERIFIED_COUNTEREXAMPLE")
        self.assertEqual(st.consumed_nonces(), [])

    def test_expired_and_rotated_keys(self):
        st = new_store(self.d)
        late = st.certify(self.ab, self.rb, now=G.EXPIRES)  # window is [issued, expires)
        self.assertFalse(late.certified)
        self.assertEqual(late.decision["receipt_phase"]["failure"]["reason"], "OUTSIDE_VALIDITY_WINDOW")

    def test_malformed_and_noncanonical_requests(self):
        st = new_store(self.d)
        pretty = json.dumps(self.req, indent=1, sort_keys=True).encode()
        r = st.certify(self.ab, pretty, now=G.NOW)
        self.assertEqual(r.outcome, "INVALID_PROPOSAL")
        r = st.certify(self.ab, b"{not json", now=G.NOW)
        self.assertEqual(r.outcome, "INVALID_PROPOSAL")
        self.assertEqual(st.consumed_nonces(), [])
        # the canonical bytes still certify afterwards
        self.assertTrue(st.certify(self.ab, self.rb, now=G.NOW).certified)


class DifferentialOracle(unittest.TestCase):
    """Random receipt mutations; the binary's receipt phase must agree with an independent
    Python implementation of the ``ReceiptsValid`` specification, and no mutant whose oracle
    verdict is invalid may certify."""

    def test_random_receipt_mutations(self):
        rng = random.Random(20261008)
        A = G.base_authority()
        base = G.make_request(A, prefix="fuzz")
        keys = list(G.K.values())
        n_cert = n_rej = 0
        for i in range(120):
            req = copy.deepcopy(base)
            st = G.state()
            for _ in range(rng.randint(1, 3)):
                m = rng.randrange(12)
                j = rng.randrange(len(req["receipts"]))
                e = req["receipts"][j]
                if m == 0:
                    st["consumed"].append(e["nonce"])
                elif m == 1:
                    req["receipts"][j] = R.resign(rng.choice(keys), dict(e, issuer=rng.choice(keys).public))
                elif m == 2:
                    k = rng.choice(keys)
                    req["receipts"][j] = R.resign(k, dict(e, issuer=k.public))
                elif m == 3:
                    e["issued_at"] = rng.choice([500, 1500, 2500])
                elif m == 4:
                    e["expires_at"] = rng.choice([1999, 2000, 2001, 4000])
                elif m == 5:
                    e["role"] = rng.choice(R.ROLES)
                elif m == 6:
                    e["nonce"] = rng.choice([x["nonce"] for x in req["receipts"]])
                elif m == 7:
                    st["revoked"].append(rng.choice(keys).public)
                elif m == 8:
                    req["proof_axioms"] = rng.choice([["propext"], ["sorryAx"], []])
                elif m == 9:
                    st["genesis"] = rng.choice([0, 1000, 1600])
                elif m == 10:
                    del req["receipts"][j]
                    if not req["receipts"]:
                        req["receipts"] = copy.deepcopy(base["receipts"][:1])
                else:
                    e["statement"] = copy.deepcopy(e["statement"])
                    e["statement"]["purpose"] = rng.choice(["confirmation", "elaboration",
                                                            "kernel-proof-check", "other"])
                # half the time, re-sign honestly with the issuer's own key if we know it
                if rng.random() < 0.5 and j < len(req["receipts"]):
                    e2 = req["receipts"][j]
                    for k in keys:
                        if k.public == e2["issuer"]:
                            req["receipts"][j] = R.resign(k, e2)
            d, rc = run_v3(A, req, st)
            valid, why = R.oracle_receipts_valid(A, req, st)
            self.assertEqual(d["receipt_phase"]["status"], "VALID" if valid else "INVALID",
                             (i, why, d["receipt_phase"]))
            self.assertEqual(d["outcome"] == "CERTIFIED_TRANSLATION", valid, (i, why))
            if valid:
                n_cert += 1
            else:
                n_rej += 1
        self.assertGreater(n_rej, 0)
        print(f"\n  differential receipt campaign: {n_cert} certified, {n_rej} rejected, 0 disagreements")


if __name__ == "__main__":
    unittest.main()
