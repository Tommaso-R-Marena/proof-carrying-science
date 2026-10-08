"""End-to-end tests of the reference elaboration/kernel-check issuers and the v3 authority.

A provable claim (``∀ r, revoked r → revoked r``) is taken through the whole pipeline:
confirmation (test key), elaboration receipt (issued only after the real Lean frontend check),
kernel-check receipt (issued only after the proof file's declarations are re-checked by the Lean
kernel and its axioms are claimed/allowed), then ``pcs-semantic-check --v3``.

Adversarial proof files must make the issuer REFUSE to sign: ``sorry``, a custom ``axiom``,
``native_decide``-style axioms, a theorem of a different statement, a ``def`` instead of a
``theorem``, a notation hijack in the proof file, an ``import`` in the proof file, and — the
strongest case — a theorem added by meta-code with ``debug.skipKernelTC`` whose ``#print axioms``
is empty but whose proof term is ill-typed (only the kernel replay catches it).

All keys are PUBLIC test keys: the resulting receipts demonstrate the mechanism and carry no
authority.  Run:  python3 -m unittest python.tests.test_issuer_v3 -v
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
from pcs_semantic.issuer_v3 import (IssuerRefused, issue_elaboration_receipt,  # noqa: E402
                                    issue_proof_receipt, run_tool)

BIN = os.path.join(ROOT, ".lake", "build", "bin", "pcs-semantic-check")
FIX = os.path.join(ROOT, "fixtures", "semantic_authority_v3")
GENESIS, NOW, ISSUED, EXPIRES = 1000, 2000, 1500, 3000
K = {n: R.test_key("pcs-v3-test-" + n + "-seed") for n in ("confirmation", "elaboration", "proof")}

SOURCE = "∀ (r : Nat), (PCS.Examples.Agent.revoked r) → (PCS.Examples.Agent.revoked r)"
CLAIM = {"assumptions": [{"args": [{"var": "r"}], "op": "pred", "symbol": "revoked"}],
         "conclusion": {"args": [{"var": "r"}], "op": "pred", "symbol": "revoked"},
         "params": [{"name": "r", "sort": "Time"}]}
HONEST_PROOF = "theorem pcs_claim : " + SOURCE + " := fun _ h => h\n"


def _load(rel):
    with open(os.path.join(FIX, rel), encoding="utf-8") as f:
        return json.load(f)


class Work:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="pcs-issuer-v3-")
        self.n = 0

    def write(self, data, suffix):
        self.n += 1
        p = os.path.join(self.dir, f"w{self.n}{suffix}")
        with open(p, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        return p


W = Work()
A = _load("authority.json")
A_PATH = W.write(canonical_json(A), ".json")


def base_request(axioms=("propext", "Quot.sound")):
    req = copy.deepcopy(_load(os.path.join("requests", "pos_certified.json")))
    req["receipts"] = []
    req["proof_axioms"] = list(axioms)
    core = req["request"]
    core["certificate"] = None
    b = core["request"]
    b["interpretation"]["selected"] = copy.deepcopy(CLAIM)
    b["interpretation"]["ambiguities"] = []
    b["interpretation"]["source_text"] = "Whenever permission is revoked at r, it is revoked at r."
    b["candidate"]["claim"] = copy.deepcopy(CLAIM)
    b["candidate"]["lean_source"] = SOURCE
    b["candidate"]["groundings"] = [g for g in b["candidate"]["groundings"] if g["symbol"] == "revoked"]
    return req


def proof_refused(proof_text, req=None, authority=None, env_src=None):
    req = req or base_request()
    authority = authority or A
    a_path = W.write(canonical_json(authority), ".json")
    r_path = W.write(canonical_json(req), ".json")
    env_path = W.write(env_src, ".lean") if env_src is not None else None
    try:
        issue_proof_receipt(K["proof"], authority, a_path, req, r_path, W.write(proof_text, ".lean"),
                            "nonce-x", ISSUED, EXPIRES, env_path=env_path)
    except IssuerRefused as e:
        return e.code
    return None


class TestIssuersV3(unittest.TestCase):

    def test_end_to_end_certified_with_tool_issued_receipts(self):
        req = base_request()
        r_path = W.write(canonical_json(req), ".json")
        conf = R.sign_envelope(K["confirmation"], "confirmation",
                               R.expected_statement(A, req, "confirmation"), "e2e-conf", ISSUED, EXPIRES)
        elab = issue_elaboration_receipt(K["elaboration"], A, A_PATH, req, r_path, "e2e-elab",
                                         ISSUED, EXPIRES)
        proof = issue_proof_receipt(K["proof"], A, A_PATH, req, r_path, W.write(HONEST_PROOF, ".lean"),
                                    "e2e-proof", ISSUED, EXPIRES)
        req["receipts"] = [conf, elab, proof]
        final = W.write(canonical_json(req), ".json")
        st = {"consumed": [], "genesis": GENESIS, "now": NOW, "revoked": [],
              "schema": R.LEDGER_STATE_SCHEMA}
        st_path = W.write(canonical_json(st), ".json")
        p = subprocess.run([BIN, "--v3", A_PATH, final, st_path], capture_output=True, text=True)
        out = json.loads(p.stdout)
        self.assertEqual(p.returncode, 0, p.stdout[:400])
        self.assertEqual(out["outcome"], "CERTIFIED_TRANSLATION")
        # replay of the same receipts against the resulting ledger state is rejected
        st2 = dict(st, consumed=["e2e-conf", "e2e-elab", "e2e-proof"])
        p2 = subprocess.run([BIN, "--v3", A_PATH, final, W.write(canonical_json(st2), ".json")],
                            capture_output=True, text=True)
        self.assertNotEqual(p2.returncode, 0)
        self.assertEqual(json.loads(p2.stdout)["outcome"], "RECEIPT_REJECTED")

    def test_elaboration_issuer_refuses_bad_source(self):
        req = base_request()
        req["request"]["request"]["candidate"]["lean_source"] = SOURCE.replace("→", "∧")
        with self.assertRaises(IssuerRefused) as cm:
            issue_elaboration_receipt(K["elaboration"], A, A_PATH, req,
                                      W.write(canonical_json(req), ".json"), "x", ISSUED, EXPIRES)
        self.assertEqual(cm.exception.code, "SOURCE_NOT_CANONICAL")

    def test_sorry_refused(self):
        self.assertEqual(proof_refused("theorem pcs_claim : " + SOURCE + " := sorry\n"),
                         "AXIOM_NOT_CLAIMED")

    def test_custom_axiom_refused(self):
        self.assertEqual(proof_refused("axiom cheat : " + SOURCE + "\ntheorem pcs_claim : " + SOURCE +
                                       " := cheat\n"), "AXIOM_NOT_CLAIMED")

    def test_unallowed_claimed_axiom_refused(self):
        req = base_request(axioms=("propext", "Quot.sound", "Lean.ofReduceBool"))
        self.assertEqual(proof_refused(HONEST_PROOF, req=req), "AXIOM_NOT_ALLOWED")

    def test_classical_axiom_not_claimed_refused(self):
        proof = ("theorem pcs_claim : " + SOURCE +
                 " := fun r h => (Classical.em (PCS.Examples.Agent.revoked r)).elim id (fun hn => absurd h hn)\n")
        self.assertEqual(proof_refused(proof), "AXIOM_NOT_CLAIMED")

    def test_different_statement_refused(self):
        self.assertEqual(proof_refused("theorem pcs_claim : True := trivial\n"), "STATEMENT_MISMATCH")

    def test_def_instead_of_theorem_refused(self):
        self.assertEqual(proof_refused("def pcs_claim : " + SOURCE + " := fun _ h => h\n"),
                         "NOT_A_THEOREM")

    def test_missing_declaration_refused(self):
        self.assertEqual(proof_refused("theorem other : " + SOURCE + " := fun _ h => h\n"),
                         "DECL_NOT_FOUND")

    def test_notation_hijack_in_proof_file_refused(self):
        proof = "macro_rules | `($a → $b) => `(True)\ntheorem pcs_claim : " + SOURCE + " := fun _ => trivial\n"
        self.assertEqual(proof_refused(proof), "STATEMENT_MISMATCH")

    def test_import_in_proof_file_refused(self):
        self.assertEqual(proof_refused("import Lean\n" + HONEST_PROOF), "ENV_LOAD_FAILED")

    def test_kernel_bypass_via_skipKernelTC_refused(self):
        env_src = "import Lean\nimport PCS.Examples.Agent\nimport PCS.Examples.Repro\nimport PCS.Examples.Bio\n"
        env_path = W.write(env_src, ".lean")
        a = copy.deepcopy(A)
        rc, fp = run_tool("fingerprint", W.write(canonical_json(a), ".json"), env_path=env_path)
        self.assertEqual(rc, 0)
        a["context"]["env_fingerprint"] = fp.strip()
        forged = (
            "open Lean Elab Command Term in\n"
            "set_option debug.skipKernelTC true in\n"
            "run_cmd liftTermElabM do\n"
            "  let ty ← elabTerm (← `(" + SOURCE + ")) none\n"
            "  let ty ← instantiateMVars ty\n"
            "  addDecl (.thmDecl { name := `pcs_claim, levelParams := [], type := ty,"
            " value := mkConst ``True.intro })\n")
        self.assertEqual(proof_refused(forged, authority=a, env_src=env_src), "KERNEL_REPLAY_FAILED")
        # positive control in the same environment
        self.assertIsNone(proof_refused(HONEST_PROOF, authority=a, env_src=env_src))


if __name__ == "__main__":
    unittest.main()
