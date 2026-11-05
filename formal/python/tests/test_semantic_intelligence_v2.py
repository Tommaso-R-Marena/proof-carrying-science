"""Tests of PCS Proof-Carrying Semantic Intelligence v2 through the compiled Lean authority.

Run from the project root after ``lake build``:

    python3 -m unittest discover -s python/tests -v

Every outcome asserted here is computed by ``pcs-semantic-check --v2`` (the Lean binary).
Positive and countermodel results are additionally re-checked by an *independent* Python
finite-model evaluator (``semantic_intelligence_v2.evaluate_claim``), written separately from
the Lean evaluator: a reported countermodel must be valid under the independent semantics, and
a certified candidate must agree with the interpretation on every sampled finite structure.
The controlled-language output is re-parsed by an independent Python parser.

These are tests of the compiled program, not proofs; the corresponding guarantees are
kernel-checked in Lean (see PCS_PROOF_CARRYING_SEMANTIC_INTELLIGENCE_V2_REPORT.md).
"""

from __future__ import annotations

import copy
import itertools
import json
import os
import random
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcs_semantic import semantic_intelligence_v2 as v2  # noqa: E402
from pcs_semantic.semantic_translation_v1 import canonical_json  # noqa: E402
import test_semantic_translation_v1 as v1t  # noqa: E402  (mutation helpers)

FIX = os.path.join(ROOT, "fixtures", "semantic_intelligence_v2")
BINARY = os.environ.get("PCS_SEMANTIC_CHECK",
                        os.path.join(ROOT, ".lake", "build", "bin", "pcs-semantic-check"))
SCHEMA_PATH = os.path.join(ROOT, "schemas", "semantic_intelligence_v2.schema.json")


def load(path):
    with open(os.path.join(FIX, path), "rb") as f:
        return f.read()


def load_json(path):
    return json.loads(load(path))


def run_bytes(a, r):
    return v2.check_v2_bytes(a, r, binary=BINARY)


def run(authority, request):
    return v2.check_v2(authority, request, binary=BINARY)


def random_finite_model(authority, rng, size=3):
    """A random registry-conforming finite structure in countermodel JSON shape."""
    reg = authority["registry"]
    carriers, nxt = {}, 0
    for s in reg["sorts"]:
        k = rng.randint(1, size)
        carriers[s["id"]] = list(range(nxt, nxt + k))
        nxt += k
    preds, fns = [], []
    for e in reg["symbols"]:
        keys = list(itertools.product(*[carriers[a] for a in e["args"]]))
        if e["kind"] == "pred":
            preds.append({"symbol": e["id"], "true_on": [list(k) for k in keys if rng.random() < 0.5]})
        else:
            fns.append({"symbol": e["id"], "table": [{"args": list(k),
                                                       "value": rng.choice(carriers[e["result"]])}
                                                      for k in keys]})
    return {"functions": fns, "predicates": preds,
            "sorts": [{"carrier": v, "sort": k} for k, v in carriers.items()]}


try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


class SetUp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(BINARY):
            raise unittest.SkipTest(f"binary {BINARY} not built (run `lake build`)")
        cls.authority_bytes = load("authority.json")
        cls.authority = json.loads(cls.authority_bytes)
        cls.expected = load_json("expected.json")
        cls.fixtures = cls.expected["fixtures"]
        cls.by_name = {f["name"]: f for f in cls.fixtures}
        cls.lenient = copy.deepcopy(cls.authority)
        cls.lenient["require_elaboration"] = False
        cls.lenient["require_proof"] = False


# ---------------------------------------------------------------------------------------
class FixtureTests(SetUp):
    def test_all_v2_fixtures(self):
        for fx in self.fixtures:
            with self.subTest(fx["name"]):
                dec = run_bytes(self.authority_bytes, load(fx["request"]))
                self.assertEqual(dec.outcome, fx["outcome"], dec.diagnostics)
                self.assertEqual(dec.label, fx["label"])
                for c in fx["codes"]:
                    self.assertIn(c, dec.codes)
                self.assertEqual(dec.authoritative, fx["outcome"] == "CERTIFIED_TRANSLATION")

    def test_fixture_files_are_canonical(self):
        for fx in self.fixtures:
            raw = load(fx["request"])
            self.assertEqual(canonical_json(json.loads(raw)), raw, fx["name"])
        self.assertEqual(canonical_json(self.authority), self.authority_bytes)

    def test_outcome_coverage(self):
        seen = {f["outcome"] for f in self.fixtures}
        for o in v2.OUTCOMES:
            self.assertIn(o, seen, f"no fixture exercises {o}")

    def test_schema(self):
        if jsonschema is None:
            raise unittest.SkipTest("jsonschema not installed")
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
        def sub(name):
            return {"$ref": "#/$defs/" + name, "$defs": schema["$defs"]}
        for fx in self.fixtures:
            jsonschema.validate(load_json(fx["request"]), sub("request"))
            dec = run_bytes(self.authority_bytes, load(fx["request"]))
            jsonschema.validate(dec.raw, sub("decision"))
        for b in self.expected["countermodels"]:
            jsonschema.validate(load_json(b["bundle"]), sub("countermodel_bundle"))
        rec = v2.training_record(os.path.join(FIX, "authority.json"),
                                 os.path.join(FIX, "requests/neg_forall_to_exists.json"),
                                 "machine-generated-fixture", "test", binary=BINARY)
        jsonschema.validate(rec, sub("training_record"))


# ---------------------------------------------------------------------------------------
class IndependentOracleTests(SetUp):
    """Differential checks against the independent Python semantics."""

    def test_reported_countermodels_valid_under_independent_semantics(self):
        n = 0
        for fx in self.fixtures:
            req = load_json(fx["request"])
            dec = run_bytes(self.authority_bytes, load(fx["request"]))
            cm = dec.countermodel
            if cm is None:
                continue
            n += 1
            with self.subTest(fx["name"]):
                self.assertTrue(v2.countermodel_is_valid(
                    self.authority, req["request"]["interpretation"]["selected"],
                    req["request"]["candidate"]["claim"], cm))
        self.assertGreaterEqual(n, 10)

    def test_certified_fixtures_agree_on_random_models(self):
        rng = random.Random(2026)
        for fx in self.fixtures:
            if fx["outcome"] != "CERTIFIED_TRANSLATION":
                continue
            req = load_json(fx["request"])["request"]
            i, c = req["interpretation"]["selected"], req["candidate"]["claim"]
            with self.subTest(fx["name"]):
                for _ in range(200):
                    M = random_finite_model(self.authority, rng)
                    self.assertEqual(v2.evaluate_claim(i, M), v2.evaluate_claim(c, M))

    def test_countermodel_bundles(self):
        for b in self.expected["countermodels"]:
            raw = load(b["bundle"])
            with self.subTest(b["name"]):
                self.assertEqual(v2.check_countermodel_bytes(self.authority_bytes, raw,
                                                             binary=BINARY), b["valid"])
                d = json.loads(raw)
                self.assertEqual(v2.countermodel_is_valid(self.authority, d["interpretation"],
                                                          d["candidate"], d["countermodel"]),
                                 b["valid"])

    def test_tampered_countermodels_rejected(self):
        rng = random.Random(7)
        valid = [b for b in self.expected["countermodels"] if b["valid"]]
        for b in valid:
            d = load_json(b["bundle"])
            for k in range(6):
                t = copy.deepcopy(d)
                m = t["countermodel"]["model"]
                if k == 0:
                    t["countermodel"]["candidate_holds"] = not t["countermodel"]["candidate_holds"]
                elif k == 1:
                    t["countermodel"]["interpretation_holds"] = t["countermodel"]["candidate_holds"]
                elif k == 2:
                    t["candidate"] = t["interpretation"]
                elif k == 3:
                    m["sorts"][0]["carrier"] = []
                elif k == 4 and m["functions"]:
                    m["functions"][0]["table"][0]["value"] = 999
                else:
                    p = rng.choice(m["predicates"])
                    p["true_on"] = [] if p["true_on"] else p["true_on"]
                lean_ok = v2.check_countermodel_bytes(self.authority_bytes, canonical_json(t),
                                                      binary=BINARY)
                py_ok = v2.countermodel_is_valid(self.authority, t["interpretation"],
                                                 t["candidate"], t["countermodel"])
                with self.subTest(b["name"], mutation=k):
                    # the Lean re-verifier and the independent oracle must agree
                    self.assertEqual(lean_ok, py_ok)
                    if k in (0, 1, 2, 3, 4):
                        self.assertFalse(lean_ok)


# ---------------------------------------------------------------------------------------
class WireTests(SetUp):
    def base(self):
        return load("requests/pos_ai_safety_supplied_certificate.json")

    def assertInvalid(self, a, r):
        dec = run_bytes(a, r)
        self.assertEqual(dec.outcome, "INVALID_PROPOSAL")
        self.assertIn("MALFORMED_INPUT", dec.codes)
        self.assertFalse(dec.authoritative)

    def test_whitespace_not_canonical(self):
        self.assertInvalid(self.authority_bytes, json.dumps(json.loads(self.base()), indent=1).encode())

    def test_unsorted_keys(self):
        d = json.loads(self.base())
        raw = json.dumps(dict(reversed(list(d.items()))), separators=(",", ":")).encode()
        self.assertInvalid(self.authority_bytes, raw)

    def test_duplicate_keys(self):
        raw = self.base()
        dup = b'{"bounds":{"cert_cap":0,"cert_depth":0,"model_bound":0,"model_budget":0},' + raw[1:]
        self.assertInvalid(self.authority_bytes, dup)

    def test_truncated_empty_and_invalid_utf8(self):
        raw = self.base()
        self.assertInvalid(self.authority_bytes, raw[:-1])
        self.assertInvalid(self.authority_bytes, b"")
        self.assertInvalid(self.authority_bytes, b"\xff\xfe" + raw)

    def test_oversized_payload(self):
        raw = self.base()
        big = raw[:-1] + b',"zz":"' + b"a" * (16 * 1024 * 1024 + 10) + b'"}'
        self.assertInvalid(self.authority_bytes, big)

    def test_unknown_schema_and_rule(self):
        d = json.loads(self.base())
        d["schema"] = "pcs-semantic-translation-v3"
        self.assertInvalid(self.authority_bytes, canonical_json(d))
        d = json.loads(self.base())
        d["certificate"]["left"][0]["rule"] = "trust_me"
        self.assertInvalid(self.authority_bytes, canonical_json(d))

    def test_extra_field(self):
        d = json.loads(self.base())
        d["model_says"] = "certified"
        self.assertInvalid(self.authority_bytes, canonical_json(d))

    def test_huge_bounds_are_clamped(self):
        d = load_json("requests/neg_forall_to_exists.json")
        d["bounds"] = {"cert_cap": 2 ** 40, "cert_depth": 2 ** 40, "model_bound": 2 ** 40,
                       "model_budget": 2 ** 40}
        t = time.time()
        dec = run(self.authority, d)
        self.assertLess(time.time() - t, 120)
        self.assertEqual(dec.outcome, "VERIFIED_COUNTEREXAMPLE")

    def test_python_bridge_fails_closed(self):
        self.assertEqual(v2.check_v2_bytes(self.authority_bytes, self.base(),
                                           binary="/nonexistent").outcome, "INVALID_PROPOSAL")
        good = run_bytes(self.authority_bytes, self.base())
        out = json.dumps(good.raw).encode()
        self.assertEqual(v2.parse_decision_v2(out, 1).outcome, "INVALID_PROPOSAL")
        forged = dict(good.raw, diagnostics=[{"code": "X", "component": "", "detail": ""}])
        self.assertEqual(v2.parse_decision_v2(json.dumps(forged).encode(), 0).outcome,
                         "INVALID_PROPOSAL")
        self.assertFalse(v2.parse_decision_v2(b"CERTIFIED_TRANSLATION", 0).authoritative)


# ---------------------------------------------------------------------------------------
class ReceiptTests(SetUp):
    def pos(self):
        return load_json("requests/pos_ai_safety_supplied_certificate.json")

    def test_tampered_confirmation_signature(self):
        d = self.pos()
        s = d["request"]["confirmation"]["signature"]
        d["request"]["confirmation"]["signature"] = ("A" if s[0] != "A" else "B") + s[1:]
        self.assertNotEqual(run(self.authority, d).outcome, "CERTIFIED_TRANSLATION")

    def test_interpretation_edited_after_confirmation(self):
        d = self.pos()
        d["request"]["interpretation"]["selected"]["conclusion"]["op"] = "exists"
        self.assertNotEqual(run(self.authority, d).outcome, "CERTIFIED_TRANSLATION")

    def test_proof_receipt_swapped_into_elaboration(self):
        d = self.pos()
        d["request"]["elaboration"]["authority"] = d["request"]["proof"]["authority"]
        d["request"]["elaboration"]["signature"] = d["request"]["proof"]["signature"]
        self.assertNotEqual(run(self.authority, d).outcome, "CERTIFIED_TRANSLATION")

    def test_receipts_from_other_claim(self):
        # genuine proof/elaboration receipts of the repro fixture attached to the safety one
        d = self.pos()
        other = load_json("requests/pos_repro_supplied_certificate.json")
        d["request"]["proof"] = other["request"]["proof"]
        d["request"]["elaboration"] = other["request"]["elaboration"]
        dec = run(self.authority, d)
        self.assertNotEqual(dec.outcome, "CERTIFIED_TRANSLATION")

    def test_unsigned_receipts_removed(self):
        for k in ("confirmation", "proof", "elaboration"):
            d = self.pos()
            d["request"][k] = None
            with self.subTest(k):
                self.assertNotEqual(run(self.authority, d).outcome, "CERTIFIED_TRANSLATION")

    def test_metadata_and_confidence_do_not_change_outcomes(self):
        for fx in self.fixtures:
            base = load_json(fx["request"])
            for conf, proposer, asserted in [(0, "human", False), (1000, "model:gpt", True),
                                             (2 ** 53, "", True)]:
                r = copy.deepcopy(base)
                r["request"]["candidate"]["model_confidence"] = conf
                r["request"]["candidate"]["proposer"] = proposer
                r["request"]["interpretation"]["proposer"] = proposer
                r["request"]["interpretation"]["model_asserts_confirmed"] = asserted
                with self.subTest(fx["name"], conf=conf):
                    self.assertEqual(run(self.authority, r).outcome, fx["outcome"])


# ---------------------------------------------------------------------------------------
class CampaignTests(SetUp):
    """Semantic mutation campaign with an independent oracle (lenient receipts)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.positives = [load_json(f["request"]) for f in cls.fixtures
                         if f["outcome"] == "CERTIFIED_TRANSLATION"]
        reg = cls.authority["registry"]["symbols"]
        cls.avoid = {e["id"] for e in reg} | {e["lean_name"] for e in reg}

    def submit(self, base, claim, cert=None, bounds=None):
        r = copy.deepcopy(base)
        r["request"]["candidate"]["claim"] = claim
        r["request"]["candidate"]["groundings"] = []
        r["certificate"] = cert
        r["bounds"] = bounds or {"cert_cap": 400, "cert_depth": 3, "model_bound": 3,
                                 "model_budget": 20000}
        first = run(self.lenient, r)
        r["request"]["candidate"]["lean_source"] = first.raw["expected_lean_source"] if first.raw else ""
        syms = set()

        def walk(x):
            if isinstance(x, dict):
                if "symbol" in x:
                    syms.add(x["symbol"])
                if "fn" in x:
                    syms.add(x["fn"])
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(claim)
        reg = {e["id"]: e for e in self.authority["registry"]["symbols"]}
        r["request"]["candidate"]["groundings"] = [
            {"lean_name": reg[s]["lean_name"], "provenance": reg[s]["provenance"], "symbol": s}
            for s in sorted(syms) if s in reg]
        return run(self.lenient, r)

    def test_alpha_renaming_certified(self):
        rng = random.Random(11)
        for base in self.positives:
            for _ in range(3):
                c = v1t.rename_consistently(base["request"]["candidate"]["claim"], rng, self.avoid)
                dec = self.submit(base, c)
                self.assertEqual(dec.outcome, "CERTIFIED_TRANSLATION", dec.diagnostics)

    def test_mutation_campaign_no_false_certification(self):
        rng = random.Random(78)
        counts = {}
        for n in range(150):
            base = self.positives[n % len(self.positives)]
            interp = base["request"]["interpretation"]["selected"]
            c = base["request"]["candidate"]["claim"]
            for _ in range(rng.randint(1, 2)):
                c = v1t.mutate_claim(c, rng, self.authority)
            dec = self.submit(base, c)
            counts[dec.outcome] = counts.get(dec.outcome, 0) + 1
            if dec.outcome == "CERTIFIED_TRANSLATION":
                for _ in range(40):
                    M = random_finite_model(self.authority, rng)
                    self.assertEqual(v2.evaluate_claim(interp, M), v2.evaluate_claim(c, M),
                                     f"FALSE CERTIFICATION: {json.dumps(c)}")
            elif dec.outcome == "VERIFIED_COUNTEREXAMPLE":
                self.assertTrue(v2.countermodel_is_valid(self.authority, interp, c,
                                                         dec.countermodel),
                                f"INVALID COUNTERMODEL: {json.dumps(c)}")
            else:
                self.assertTrue(dec.diagnostics)
        self.assertGreater(counts.get("VERIFIED_COUNTEREXAMPLE", 0), 30)
        print(f"\n[v2 semantic campaign] {counts}", file=sys.stderr)

    def test_search_exhausted_is_not_equivalence(self):
        base = load_json("requests/unresolved_search_disabled.json")
        dec = run(self.authority, base)
        self.assertEqual(dec.outcome, "SEARCH_EXHAUSTED")
        self.assertEqual(dec.label, "UNRESOLVED")
        self.assertFalse(dec.authoritative)


# ---------------------------------------------------------------------------------------
class ExplanationAndRecordTests(SetUp):
    def test_controlled_language_reparses_independently(self):
        for fx in self.fixtures:
            if fx["outcome"] != "CERTIFIED_TRANSLATION":
                continue
            req = load_json(fx["request"])["request"]
            dec = run(self.authority, load_json(fx["request"]))
            cnl = dec.raw["controlled_language"]
            with self.subTest(fx["name"]):
                self.assertTrue(cnl["cnl_valid"])
                self.assertEqual(v2.parse_cnl(cnl["conclusion"]), req["candidate"]["claim"]["conclusion"])
                self.assertEqual([v2.parse_cnl(a) for a in cnl["assumptions"]],
                                 req["candidate"]["claim"]["assumptions"])
                views = dec.raw["explanation_views"]
                self.assertTrue(any(s.startswith("NOT established") for s in views["trust"]))

    def test_cnl_parser_rejects_noise(self):
        self.assertIsNone(v2.parse_cnl("for-every t of-sort Time (  true )"))
        self.assertIsNone(v2.parse_cnl("true true"))
        self.assertIsNone(v2.parse_cnl("holds of of ( )"))

    def test_training_records(self):
        a = os.path.join(FIX, "authority.json")
        for name in ("pos_repro_search_certificate", "neg_forall_to_exists",
                     "unresolved_search_disabled", "neg_forged_confirmation"):
            fx = self.by_name[name]
            p = os.path.join(FIX, fx["request"])
            rec = v2.training_record(a, p, "machine-generated-fixture", "test-revision",
                                     binary=BINARY)
            rec2 = v2.training_record(a, p, "machine-generated-fixture", "test-revision",
                                      binary=BINARY)
            with self.subTest(name):
                self.assertIsNotNone(rec)
                self.assertEqual(rec, rec2)  # deterministic re-check
                self.assertEqual(rec["label"], fx["label"])
                self.assertEqual(rec["outcome"], fx["outcome"])
                self.assertEqual(rec["provenance"], "machine-generated-fixture")
                self.assertIn(rec["partition"], ("train", "evaluation"))
                if fx["outcome"] == "VERIFIED_COUNTEREXAMPLE":
                    self.assertIsNotNone(rec["countermodel"])


# ---------------------------------------------------------------------------------------
class LeanEnvironmentTests(SetUp):
    """Grounding and elaboration against the real Lean environment (executable checks)."""

    def lean_run(self, args, timeout=600):
        import subprocess
        return subprocess.run(["lake", "env", "lean", *args], cwd=ROOT, capture_output=True,
                              timeout=timeout)

    def test_registry_grounded_in_lean_environment(self):
        p = self.lean_run(["--run", "tools/CheckRegistryGrounding.lean",
                           os.path.join(FIX, "authority.json")])
        self.assertEqual(p.returncode, 0, p.stdout.decode())
        self.assertIn(b"GROUNDED", p.stdout)

    def test_grounding_mutations_rejected(self):
        import tempfile
        muts = []
        a = copy.deepcopy(self.authority)
        a["registry"]["symbols"][0]["lean_name"] = "PCS.Examples.Agent.revokedAt"   # hallucinated
        muts.append(("nonexistent declaration", a))
        a = copy.deepcopy(self.authority)
        a["registry"]["symbols"][2]["args"] = ["Time"]                                # wrong arity
        muts.append(("wrong arity", a))
        a = copy.deepcopy(self.authority)
        a["registry"]["symbols"][2]["args"] = ["Action", "Time"]                      # swapped sorts
        muts.append(("swapped argument sorts", a))
        a = copy.deepcopy(self.authority)
        for e in a["registry"]["symbols"]:
            if e["id"] == "outputDigest":
                e["result"] = "Dataset"                                                # wrong result
        muts.append(("wrong result sort", a))
        a = copy.deepcopy(self.authority)
        a["registry"]["sorts"][1]["lean_type"] = "PCS.Examples.Agent.forbidden"       # not a type
        muts.append(("sort grounded in a predicate", a))
        a = copy.deepcopy(self.authority)
        a["registry"]["symbols"][1]["lean_name"] = "Nat.lt_irrefl"                    # a theorem
        muts.append(("theorem used as symbol", a))
        a = copy.deepcopy(self.authority)
        a["registry"]["symbols"][3]["lean_name"] = a["registry"]["symbols"][0]["lean_name"]
        muts.append(("duplicate grounding", a))
        for name, auth in muts:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(auth, f)
            try:
                p = self.lean_run(["--run", "tools/CheckRegistryGrounding.lean", f.name])
            finally:
                os.unlink(f.name)
            with self.subTest(name):
                self.assertEqual(p.returncode, 1, p.stdout.decode())
                self.assertIn(b"NOT_GROUNDED", p.stdout)

    def test_rendered_lean_sources_elaborate(self):
        import tempfile
        lines = ["import PCS.Examples.Agent", "import PCS.Examples.Repro", "import PCS.Examples.Bio", ""]
        n = 0
        for fx in self.fixtures:
            if fx["outcome"] != "CERTIFIED_TRANSLATION":
                continue
            dec = run_bytes(self.authority_bytes, load(fx["request"]))
            lines.append(f"def pcs_rendered_{n} : Prop := {dec.raw['expected_lean_source']}")
            n += 1
        with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, dir=ROOT) as f:
            f.write("\n".join(lines) + "\n")
        try:
            p = self.lean_run([f.name])
        finally:
            os.unlink(f.name)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr).decode())
        self.assertGreaterEqual(n, 6)


if __name__ == "__main__":
    unittest.main()
