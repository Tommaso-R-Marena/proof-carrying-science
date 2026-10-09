"""Adversarial tests of the v3 elaboration bridge checker ``tools/CheckElaborationV3.lean``.

The checker runs the *real* Lean 4.28.0 frontend on the exact rendered candidate source inside a
fingerprinted environment and compares the elaborated expression with the expression built
directly from the proved syntax tree ``readClaim``.  These are executable tests of a meta-level
tool (trusting the Lean frontend), not proofs.

Each adversarial environment is tested twice:
* against the **pinned** authority (fingerprint of the honest environment) — must give
  ``ENV_FINGERPRINT_MISMATCH``;
* against an authority **re-pinned** to the adversarial environment's own fingerprint — this
  shows what the structural check alone catches (``STRUCTURE_MISMATCH`` for notation hijacks)
  and what only the fingerprint catches (a changed definition body with the same type).

Run from the project root (after ``lake build``):
    python3 -m unittest python.tests.test_elaboration_v3 -v
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

FIX = os.path.join(ROOT, "fixtures", "semantic_authority_v3")
TOOL = os.path.join("tools", "CheckElaborationV3.lean")

HEADER = "import PCS.Examples.Agent\nimport PCS.Examples.Repro\nimport PCS.Examples.Bio\n"
AGENT_BODY_OPAQUE = (
    "structure Action where\n  id : Nat\n  deriving Repr, DecidableEq, Inhabited\n"
    "opaque revoked : Nat → Prop\nopaque before : Nat → Nat → Prop\n"
    "opaque performs : Nat → Action → Prop\nopaque forbidden : Action → Prop\n"
    "opaque withinBudget : Nat → Prop\n")


def _load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


class ElabHarness:
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="pcs-elab-v3-")
        self.n = 0

    def _file(self, data: bytes, suffix: str) -> str:
        self.n += 1
        p = os.path.join(self.tmp, f"f{self.n}{suffix}")
        with open(p, "wb") as f:
            f.write(data)
        return p

    def run(self, *args, env_src=None):
        cmd = ["lake", "env", "lean", "--run", TOOL, *args]
        if env_src is not None:
            cmd += ["--env", self._file(env_src.encode("utf-8"), ".lean")]
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        return p.returncode, (lines[-1] if lines else "")

    def fingerprint(self, authority, env_src=None):
        rc, out = self.run("fingerprint", self._file(canonical_json(authority), ".json"),
                           env_src=env_src)
        assert rc == 0, out
        return out.strip()

    def check(self, authority, request, env_src=None, raw_request=None):
        a = self._file(canonical_json(authority), ".json")
        r = self._file(raw_request if raw_request is not None else canonical_json(request), ".json")
        rc, out = self.run("check", a, r, env_src=env_src)
        return rc, out.split(" ")[0]

    def repin(self, authority, env_src=None):
        a = copy.deepcopy(authority)
        a["context"]["env_fingerprint"] = self.fingerprint(a, env_src)
        return a


H = ElabHarness()
A = _load("authority.json")
REQ = {n: _load(os.path.join("requests", n + ".json")) for n in
       ("pos_certified", "pos_pos_ai_safety_identical", "pos_pos_bio_supplied_certificate",
        "pos_pos_repro_supplied_certificate")}


def cand(req):
    return req["request"]["request"]["candidate"]


class TestElaborationBridgeV3(unittest.TestCase):

    def assertCode(self, got, code):
        self.assertEqual(got[1], code, got)
        self.assertEqual(got[0], 0 if code == "ELABORATION_MATCHES" else 1, got)

    # ---- positive controls --------------------------------------------------------------
    def test_positive_fixtures_elaborate_as_their_syntax_tree(self):
        for name, req in REQ.items():
            with self.subTest(name):
                self.assertCode(H.check(A, req), "ELABORATION_MATCHES")

    def test_fingerprint_is_deterministic_and_pinned(self):
        with open(os.path.join(FIX, "env_fingerprint.txt"), encoding="utf-8") as f:
            pinned = f.read().strip()
        self.assertEqual(H.fingerprint(A), pinned)
        self.assertEqual(H.fingerprint(A), pinned)
        self.assertEqual(A["context"]["env_fingerprint"], pinned)

    # ---- overloaded notation ------------------------------------------------------------
    def _notation_attack(self, req, rule):
        env = HEADER + rule + "\n"
        self.assertCode(H.check(A, req, env_src=env), "ENV_FINGERPRINT_MISMATCH")
        self.assertCode(H.check(H.repin(A, env), req, env_src=env), "STRUCTURE_MISMATCH")

    def test_overloaded_and_notation(self):
        self._notation_attack(REQ["pos_certified"], "macro_rules | `($a ∧ $b) => `($a ∨ $b)")

    def test_overloaded_negation_notation(self):
        self._notation_attack(REQ["pos_certified"], "macro_rules | `(¬ $p) => `($p)")

    def test_overloaded_equality_notation(self):
        self._notation_attack(REQ["pos_pos_repro_supplied_certificate"],
                              "macro_rules | `($a = $b) => `(HEq $a $b)")

    def test_overloaded_arrow_notation_classically_equivalent(self):
        # `a → b` re-read as `¬ a ∨ b`: classically equivalent, still structurally rejected
        self._notation_attack(REQ["pos_pos_bio_supplied_certificate"],
                              "macro_rules | `($a → $b) => `(¬ $a ∨ $b)")

    def test_self_looping_notation_fails_closed(self):
        env = HEADER + "macro_rules | `($a = $b) => `($b = $a)\n"
        rc, code = H.check(H.repin(A, env), REQ["pos_pos_repro_supplied_certificate"], env_src=env)
        self.assertEqual(rc, 1)
        self.assertIn(code, ("ELABORATION_ERROR", "STRUCTURE_MISMATCH"))

    # ---- shadowing and namespace changes ------------------------------------------------
    def test_root_level_shadowing_declarations(self):
        env = (HEADER + "def revoked (_ : Nat) : Prop := True\n"
               "def forbidden (_ : PCS.Examples.Agent.Action) : Prop := False\n"
               "def PCS.Examples.Agent.Action.forbidden : Prop := True\n")
        self.assertCode(H.check(A, REQ["pos_certified"], env_src=env), "ENV_FINGERPRINT_MISMATCH")
        # fully qualified names are resolved exactly; shadows at other paths change nothing
        self.assertCode(H.check(H.repin(A, env), REQ["pos_certified"], env_src=env),
                        "ELABORATION_MATCHES")

    def test_namespace_change(self):
        env = ("import PCS.Examples.Repro\nimport PCS.Examples.Bio\n"
               "namespace PCS.Examples.AgentMoved\n" + AGENT_BODY_OPAQUE +
               "end PCS.Examples.AgentMoved\n")
        self.assertCode(H.check(A, REQ["pos_certified"], env_src=env), "ENV_FINGERPRINT_MISMATCH")
        self.assertCode(H.check(H.repin(A, env), REQ["pos_certified"], env_src=env), "NOT_GROUNDED")

    # ---- changed definitions ------------------------------------------------------------
    def test_changed_definition_same_type_is_caught_by_fingerprint(self):
        body = AGENT_BODY_OPAQUE.replace("opaque revoked : Nat → Prop",
                                         "def revoked (_ : Nat) : Prop := False")
        env = ("import PCS.Examples.Repro\nimport PCS.Examples.Bio\n"
               "namespace PCS.Examples.Agent\n" + body + "end PCS.Examples.Agent\n")
        self.assertCode(H.check(A, REQ["pos_certified"], env_src=env), "ENV_FINGERPRINT_MISMATCH")
        # Honest negative control: with a re-pinned fingerprint the structure still matches —
        # elaboration cannot see a changed body; only the fingerprint binds definitions.
        self.assertCode(H.check(H.repin(A, env), REQ["pos_certified"], env_src=env),
                        "ELABORATION_MATCHES")

    def test_axiom_backed_symbol_not_grounded(self):
        body = AGENT_BODY_OPAQUE.replace("opaque forbidden : Action → Prop",
                                         "axiom forbidden : Action → Prop")
        env = ("import PCS.Examples.Repro\nimport PCS.Examples.Bio\n"
               "namespace PCS.Examples.Agent\n" + body + "end PCS.Examples.Agent\n")
        self.assertCode(H.check(H.repin(A, env), REQ["pos_certified"], env_src=env), "NOT_GROUNDED")

    # ---- registry attacks ----------------------------------------------------------------
    def _sym(self, a, sid):
        return next(s for s in a["registry"]["symbols"] if s["id"] == sid)

    def test_incorrect_argument_types(self):
        a = copy.deepcopy(A)
        self._sym(a, "forbidden")["args"] = ["Time"]
        self.assertCode(H.check(H.repin(a), REQ["pos_certified"]), "NOT_GROUNDED")

    def test_symbol_grounded_in_wrongly_typed_constant(self):
        a = copy.deepcopy(A)
        self._sym(a, "forbidden")["lean_name"] = "PCS.Examples.Agent.withinBudget"
        a["registry"]["symbols"] = [s for s in a["registry"]["symbols"] if s["id"] != "withinBudget"]
        self.assertCode(H.check(H.repin(a), REQ["pos_certified"]), "NOT_GROUNDED")

    def test_misleading_symbol_name(self):
        # registry id `inSite` silently re-pointed to the same-typed `inSiteLegacy`
        a = copy.deepcopy(A)
        self._sym(a, "inSite")["lean_name"] = "PCS.Examples.Bio.inSiteLegacy"
        a["registry"]["symbols"] = [s for s in a["registry"]["symbols"] if s["id"] != "inSiteLegacy"]
        req = REQ["pos_pos_bio_supplied_certificate"]
        self.assertCode(H.check(a, req), "ENV_FINGERPRINT_MISMATCH")
        self.assertCode(H.check(H.repin(a), req), "SOURCE_NOT_CANONICAL")

    def test_duplicate_grounding(self):
        a = copy.deepcopy(A)
        self._sym(a, "inSiteLegacy")["lean_name"] = "PCS.Examples.Bio.inSite"
        self.assertCode(H.check(H.repin(a), REQ["pos_pos_bio_supplied_certificate"]), "NOT_GROUNDED")

    def test_missing_constant(self):
        a = copy.deepcopy(A)
        self._sym(a, "forbidden")["lean_name"] = "PCS.Examples.Agent.forbiddenX"
        self.assertCode(H.check(H.repin(a), REQ["pos_certified"]), "NOT_GROUNDED")

    # ---- request attacks -----------------------------------------------------------------
    def test_lean_source_not_canonical(self):
        for src in ["open PCS.Examples.Agent in " + cand(REQ["pos_certified"])["lean_source"],
                    cand(REQ["pos_certified"])["lean_source"].replace("∧", "∨"),
                    "True"]:
            req = copy.deepcopy(REQ["pos_certified"])
            cand(req)["lean_source"] = src
            with self.subTest(src[:40]):
                self.assertCode(H.check(A, req), "SOURCE_NOT_CANONICAL")

    def _rename_binder(self, req, old, new):
        s = json.dumps(req)
        s = s.replace(f'{{"var": "{old}"}}', f'{{"var": "{new}"}}')
        s = s.replace(f'"name": "{old}"', f'"name": "{new}"')
        return json.loads(s)

    def test_binder_named_like_registry_namespace(self):
        req = self._rename_binder(REQ["pos_certified"], "r", "PCS")
        self.assertCode(H.check(A, req), "GATE_FAILED")

    def test_binder_named_like_registry_constant_component(self):
        req = self._rename_binder(REQ["pos_certified"], "r", "revoked")
        self.assertCode(H.check(A, req), "GATE_FAILED")

    def test_keyword_binder(self):
        req = self._rename_binder(REQ["pos_certified"], "r", "fun")
        self.assertCode(H.check(A, req), "GATE_FAILED")

    def test_non_canonical_json(self):
        raw = json.dumps(REQ["pos_certified"], indent=1).encode("utf-8")
        self.assertCode(H.check(A, None, raw_request=raw), "MALFORMED_INPUT")


if __name__ == "__main__":
    unittest.main()
