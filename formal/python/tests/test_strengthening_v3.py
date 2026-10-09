"""Tests of the separate, explicitly authorized strengthening mode (``--v3-strengthen``).

Equivalence is not entailment: a candidate that is logically stronger than the selected
interpretation must never be reported as ``CERTIFIED_TRANSLATION``.  Strengthening mode has its
own outcome (``CERTIFIED_STRENGTHENING``, exit code 4 — never 0), its own authorization statement
(purpose ``strengthening-authorization``, binding the exact candidate) and the same stateful
ledger protocol.  Test keys are PUBLIC; the receipts carry no authority.

Run:  python3 -m unittest python.tests.test_strengthening_v3 -v
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "python"))

from pcs_semantic.semantic_translation_v1 import canonical_json  # noqa: E402
from pcs_semantic import receipts_v3 as R  # noqa: E402
from pcs_semantic.receipt_store import ReceiptStore  # noqa: E402

BIN = os.path.join(ROOT, ".lake", "build", "bin", "pcs-semantic-check")
FIX = os.path.join(ROOT, "fixtures", "semantic_authority_v3")
GENESIS, NOW, ISSUED, EXPIRES = 1000, 2000, 1500, 3000
K = {n: R.test_key("pcs-v3-test-" + n + "-seed") for n in ("confirmation", "elaboration", "proof")}
TMP = tempfile.mkdtemp(prefix="pcs-strengthen-v3-")
_n = [0]


def _w(obj):
    _n[0] += 1
    p = os.path.join(TMP, f"s{_n[0]}.json")
    with open(p, "wb") as f:
        f.write(canonical_json(obj))
    return p


def _load(rel):
    with open(os.path.join(FIX, rel), encoding="utf-8") as f:
        return json.load(f)


A = _load("authority.json")
A_PATH = _w(A)


def state(consumed=()):
    return {"consumed": list(consumed), "genesis": GENESIS, "now": NOW, "revoked": [],
            "schema": R.LEDGER_STATE_SCHEMA}


def run(mode, req, st=None):
    p = subprocess.run([BIN, mode, A_PATH, _w(req), _w(st or state())], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def with_candidate_conclusion(make_concl):
    """A request whose candidate conclusion is ``make_concl(interpretation conclusion)``, with the
    canonical Lean rendering filled in from the authority's own output."""
    req = copy.deepcopy(_load(os.path.join("requests", "pos_certified.json")))
    req["receipts"] = []
    core = req["request"]
    core["certificate"] = None
    b = core["request"]
    sel = b["interpretation"]["selected"]
    b["candidate"]["claim"] = copy.deepcopy(sel)
    budget = {"args": [{"var": sel["params"][0]["name"]}], "op": "pred", "symbol": "withinBudget"}
    b["candidate"]["claim"]["conclusion"] = make_concl(copy.deepcopy(sel["conclusion"]), budget)
    b["candidate"]["groundings"].append({"lean_name": "PCS.Examples.Agent.withinBudget",
                                         "provenance": "PCS/Examples/Agent.lean",
                                         "symbol": "withinBudget"})
    _, out = run("--v3", req)
    b["candidate"]["lean_source"] = out["expected_lean_source"]
    return req


def sign_all(req, mode, prefix):
    req = copy.deepcopy(req)
    req["receipts"] = [R.sign_envelope(K[role], role, R.expected_statement(A, req, role, mode=mode),
                                       f"{prefix}-{role}", ISSUED, EXPIRES)
                       for role in ("confirmation", "elaboration", "proof")]
    return req


STRONGER = with_candidate_conclusion(lambda c, b: {"lhs": c, "op": "and", "rhs": b})
WEAKER = with_candidate_conclusion(lambda c, b: {"lhs": c, "op": "or", "rhs": b})


class TestStrengtheningV3(unittest.TestCase):

    def test_authorized_strengthening_certified_with_distinct_outcome(self):
        req = sign_all(STRONGER, "strengthening", "st-ok")
        rc, out = run("--v3-strengthen", req)
        self.assertEqual((rc, out["outcome"]), (4, "CERTIFIED_STRENGTHENING"), out)
        self.assertEqual(out["schema"], "pcs-semantic-strengthening-decision-v3")
        self.assertEqual(sorted(out["new_ledger_consumed"]),
                         sorted(e["nonce"] for e in req["receipts"]))

    def test_stronger_candidate_is_never_a_certified_translation(self):
        for mode in ("strengthening", "translation"):
            req = sign_all(STRONGER, mode, "st-tr-" + mode)
            rc, out = run("--v3", req)
            with self.subTest(mode):
                self.assertNotEqual(rc, 0)
                self.assertNotEqual(out["outcome"], "CERTIFIED_TRANSLATION")

    def test_ordinary_confirmation_does_not_authorize_strengthening(self):
        req = sign_all(STRONGER, "translation", "st-conf")
        rc, out = run("--v3-strengthen", req)
        self.assertEqual((rc, out["outcome"]), (1, "RECEIPT_REJECTED"))
        self.assertEqual(out["failure"]["reason"], "STATEMENT_MISMATCH")

    def test_strengthening_authorization_is_not_an_ordinary_confirmation(self):
        # an identical (equivalent) candidate with a strengthening authorization in --v3 mode
        req = with_candidate_conclusion(lambda c, b: c)
        req["request"]["request"]["candidate"]["groundings"].pop()
        _, out = run("--v3", req)
        req["request"]["request"]["candidate"]["lean_source"] = out["expected_lean_source"]
        rc, out = run("--v3", sign_all(req, "strengthening", "st-as-conf"))
        self.assertNotEqual(rc, 0)
        self.assertEqual(out["outcome"], "RECEIPT_REJECTED")
        rc, out = run("--v3", sign_all(req, "translation", "st-as-conf2"))
        self.assertEqual((rc, out["outcome"]), (0, "CERTIFIED_TRANSLATION"))

    def test_weaker_candidate_is_not_a_strengthening(self):
        rc, out = run("--v3-strengthen", sign_all(WEAKER, "strengthening", "st-weak"))
        self.assertEqual((rc, out["outcome"]), (1, "NOT_A_STRENGTHENING"))
        self.assertEqual(out["new_ledger_consumed"], [])

    def test_authorization_bound_to_exact_candidate(self):
        other = with_candidate_conclusion(lambda c, b: {"lhs": b, "op": "and", "rhs": c})
        req = sign_all(STRONGER, "strengthening", "st-bind")
        req2 = copy.deepcopy(other)
        req2["receipts"] = req["receipts"]
        rc, out = run("--v3-strengthen", req2)
        self.assertEqual((rc, out["outcome"]), (1, "RECEIPT_REJECTED"))

    def test_strengthening_replay_rejected(self):
        req = sign_all(STRONGER, "strengthening", "st-replay")
        rc, out = run("--v3-strengthen", req)
        self.assertEqual(rc, 4)
        rc2, out2 = run("--v3-strengthen", req, state(out["new_ledger_consumed"]))
        self.assertEqual((rc2, out2["outcome"]), (1, "RECEIPT_REJECTED"))
        self.assertEqual(out2["failure"]["reason"], "REPLAY")

    def test_quantifier_scope_change_is_not_a_strengthening(self):
        # pushing the extra conjunct under the quantifiers in a way that changes scope is fine only
        # if entailment is proved; swapping ∀ for ∃ in the conclusion is rejected
        def to_exists(c, _b):
            c = copy.deepcopy(c)
            c["op"] = "exists"
            return c
        req = with_candidate_conclusion(to_exists)
        req["request"]["request"]["candidate"]["groundings"].pop()
        _, out = run("--v3", req)
        req["request"]["request"]["candidate"]["lean_source"] = out["expected_lean_source"]
        rc, out = run("--v3-strengthen", sign_all(req, "strengthening", "st-q"))
        self.assertEqual((rc, out["outcome"]), (1, "NOT_A_STRENGTHENING"))

    def test_persistent_store_strengthening_mode(self):
        db = os.path.join(TMP, "store-strengthen.sqlite")
        store = ReceiptStore.initialize(db, A["context"]["scope"], GENESIS)
        req = sign_all(STRONGER, "strengthening", "st-store")
        raw = canonical_json(req)
        a = canonical_json(A)
        # translation mode never certifies a strengthening, and consumes nothing
        r0 = store.certify(a, raw, now=NOW)
        self.assertFalse(r0.certified)
        self.assertEqual(store.consumed_nonces(), [])
        r1 = store.certify(a, raw, now=NOW, mode="strengthening")
        self.assertEqual((r1.outcome, r1.certified), ("CERTIFIED_STRENGTHENING", True))
        r2 = ReceiptStore.open(db, A["context"]["scope"]).certify(a, raw, now=NOW, mode="strengthening")
        self.assertEqual((r2.outcome, r2.certified), ("RECEIPT_REJECTED", False))


if __name__ == "__main__":
    unittest.main()
