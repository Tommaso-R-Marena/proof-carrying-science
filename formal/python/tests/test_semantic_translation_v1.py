"""Tests of PCS Semantic Translation Contract v1 through the compiled Lean authority.

Run from the project root after ``lake build``:

    python3 -m unittest discover -s python/tests -v

Every verdict asserted here is computed by ``pcs-semantic-check`` (the Lean binary).  The
semantic fuzz campaign additionally checks every ACCEPTED mutant against an *independent*
Python finite-model evaluator of the fragment (differential test: accepted ⇒ the candidate
and the interpretation agree on every sampled finite model).  These are tests of the
compiled program, not proofs; the corresponding guarantees are kernel-checked in Lean.
"""

from __future__ import annotations

import copy
import itertools
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "python"))

from pcs_semantic import semantic_translation_v1 as st  # noqa: E402

FIX = os.path.join(ROOT, "fixtures", "semantic_translation_v1")
BINARY = os.environ.get("PCS_SEMANTIC_CHECK",
                        os.path.join(ROOT, ".lake", "build", "bin", "pcs-semantic-check"))
SCHEMA_PATH = os.path.join(ROOT, "schemas", "semantic_translation_v1.schema.json")


def load(path):
    with open(os.path.join(FIX, path), "rb") as f:
        return f.read()


def load_json(path):
    return json.loads(load(path).decode("utf-8"))


def run_bytes(a: bytes, r: bytes) -> st.Decision:
    return st.check_bytes(a, r, binary=BINARY)


def run(authority, request) -> st.Decision:
    return st.check(authority, request, binary=BINARY)


try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


def schema_validate(doc, which):
    if jsonschema is None:
        raise unittest.SkipTest("jsonschema not installed")
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    sub = dict(schema)
    sub.pop("oneOf")
    sub["$ref"] = f"#/$defs/{which}"
    jsonschema.validate(doc, sub)


class SetUp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(BINARY):
            raise RuntimeError(f"build the binary first (lake build): {BINARY} missing")
        cls.expected = load_json("expected.json")["fixtures"]
        cls.authority = load_json("authority.json")
        cls.safety = load_json("requests/pos_safety.json")


# ---------------------------------------------------------------------------------------
class FixtureTests(SetUp):
    def test_all_fixtures(self):
        self.assertGreaterEqual(len(self.expected), 36)
        for fx in self.expected:
            with self.subTest(fx["name"]):
                dec = run_bytes(load(fx["authority"]), load(fx["request"]))
                self.assertEqual(dec.verdict, fx["verdict"], dec.diagnostics)
                for code in fx["codes"]:
                    self.assertIn(code, dec.codes)
                schema_validate(dec.raw, "decision")
                if fx["verdict"] == "ACCEPTED":
                    self.assertTrue(dec.authoritative)
                    self.assertIsNotNone(dec.explanation)
                else:
                    self.assertFalse(dec.authoritative)
                    self.assertIsNone(dec.explanation)

    def test_fixture_files_match_schema(self):
        schema_validate(self.authority, "authority")
        for fx in self.expected:
            with self.subTest(fx["name"]):
                schema_validate(load_json(fx["request"]), "request")

    def test_fixture_files_are_canonical(self):
        for fx in self.expected:
            raw = load(fx["request"])
            self.assertEqual(st.canonical_json(json.loads(raw.decode("utf-8"))), raw)


# ---------------------------------------------------------------------------------------
class WireAdversarialTests(SetUp):
    """Malformed or non-canonical inputs must be rejected (MALFORMED_INPUT)."""

    def assertMalformed(self, a: bytes, r: bytes):
        dec = run_bytes(a, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertIn("MALFORMED_INPUT", dec.codes)

    def test_whitespace_is_not_canonical(self):
        self.assertMalformed(load("authority.json"), json.dumps(self.safety, indent=1).encode())

    def test_unsorted_keys(self):
        raw = json.dumps(self.safety, separators=(",", ":"), ensure_ascii=False).encode()
        # json.dumps without sort_keys keeps insertion order; force a non-sorted top level
        d = {"schema": self.safety["schema"]}
        d.update({k: v for k, v in self.safety.items() if k != "schema"})
        raw = json.dumps(d, separators=(",", ":"), ensure_ascii=False).encode()
        self.assertMalformed(load("authority.json"), raw)

    def test_missing_field(self):
        r = copy.deepcopy(self.safety)
        del r["candidate"]["groundings"]
        self.assertMalformed(load("authority.json"), st.canonical_json(r))

    def test_extra_field(self):
        r = copy.deepcopy(self.safety)
        r["candidate"]["trusted"] = True
        self.assertMalformed(load("authority.json"), st.canonical_json(r))

    def test_wrong_schema_tag(self):
        r = copy.deepcopy(self.safety)
        r["schema"] = "pcs-proof-proposals-v1"
        self.assertMalformed(load("authority.json"), st.canonical_json(r))

    def test_unknown_operator(self):
        r = copy.deepcopy(self.safety)
        r["candidate"]["claim"]["conclusion"] = {"arg": r["candidate"]["claim"]["conclusion"],
                                                "op": "probably"}
        self.assertMalformed(load("authority.json"), st.canonical_json(r))

    def test_float_confidence(self):
        raw = load("requests/pos_safety.json").replace(b'"model_confidence":900',
                                                     b'"model_confidence":0.9')
        self.assertMalformed(load("authority.json"), raw)

    def test_negative_confidence(self):
        raw = load("requests/pos_safety.json").replace(b'"model_confidence":900',
                                                     b'"model_confidence":-1')
        self.assertMalformed(load("authority.json"), raw)

    def test_truncated_and_empty(self):
        raw = load("requests/pos_safety.json")
        self.assertMalformed(load("authority.json"), raw[: len(raw) // 2])
        self.assertMalformed(load("authority.json"), b"")
        self.assertMalformed(b"", raw)

    def test_invalid_utf8(self):
        self.assertMalformed(load("authority.json"), b"\xff\xfe" + load("requests/pos_safety.json"))

    def test_python_side_rejects_non_canonical_values(self):
        r = copy.deepcopy(self.safety)
        r["candidate"]["model_confidence"] = 0.99
        dec = run(self.authority, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertFalse(dec.authoritative)

    def test_missing_binary_fails_closed(self):
        dec = st.check(self.authority, self.safety, binary="/nonexistent/pcs-semantic-check")
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertFalse(dec.authoritative)

    def test_output_parser_fails_closed(self):
        self.assertFalse(st.parse_decision(b"ACCEPTED", 0).authoritative)
        forged = st.canonical_json({"diagnostics": [], "expected_lean_source": "",
                                    "explanation": None, "explanation_literal": None,
                                    "schema": st.DECISION_SCHEMA, "verdict": "ACCEPTED"})
        self.assertFalse(st.parse_decision(forged, 1).authoritative)  # exit code disagrees
        self.assertTrue(st.parse_decision(forged, 0).authoritative)


# ---------------------------------------------------------------------------------------
class ReceiptAdversarialTests(SetUp):
    def test_tampered_confirmation_signature(self):
        r = copy.deepcopy(self.safety)
        sig = r["confirmation"]["signature"]
        r["confirmation"]["signature"] = ("A" if sig[0] != "A" else "B") + sig[1:]
        dec = run(self.authority, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertIn("CONFIRMATION_NOT_VERIFIED", dec.codes)

    def test_interpretation_edited_after_confirmation(self):
        r = copy.deepcopy(self.safety)
        r["interpretation"]["source_text"] += " (edited)"
        dec = run(self.authority, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertIn("CONFIRMATION_NOT_VERIFIED", dec.codes)

    def test_ambiguity_resolution_edited_after_confirmation(self):
        r = copy.deepcopy(self.safety)
        r["interpretation"]["ambiguities"][0]["resolution"] = "at or after"
        dec = run(self.authority, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertIn("CONFIRMATION_NOT_VERIFIED", dec.codes)

    def test_confirmation_replayed_from_other_request(self):
        r = copy.deepcopy(self.safety)
        r["confirmation"] = load_json("requests/pos_arith.json")["confirmation"]
        dec = run(self.authority, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertIn("CONFIRMATION_NOT_VERIFIED", dec.codes)

    def test_role_confusion_elaboration_as_proof(self):
        r = copy.deepcopy(self.safety)
        r["proof"]["authority"] = r["elaboration"]["authority"]
        r["proof"]["signature"] = r["elaboration"]["signature"]
        dec = run(self.authority, r)
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertIn("PROOF_NOT_VERIFIED", dec.codes)

    def test_role_confusion_proof_key_as_confirmation(self):
        r = copy.deepcopy(self.safety)
        r["confirmation"]["authority"] = r["proof"]["authority"]
        dec = run(self.authority, r)
        self.assertIn("CONFIRMATION_NOT_VERIFIED", dec.codes)

    def test_axiom_list_edited(self):
        r = copy.deepcopy(self.safety)
        r["proof"]["axioms"] = []  # signature covers the axiom list
        dec = run(self.authority, r)
        self.assertIn("PROOF_NOT_VERIFIED", dec.codes)

    def test_unauthorized_key_added_by_request_has_no_effect(self):
        # keys come only from the authority file; a request cannot add keys
        r = copy.deepcopy(self.safety)
        r["confirmation"]["authority"] = "AAAA"
        dec = run(self.authority, r)
        self.assertIn("CONFIRMATION_NOT_VERIFIED", dec.codes)

    def test_receipts_removed(self):
        for k, code in [("confirmation", "CONFIRMATION_MISSING"),
                        ("elaboration", "ELABORATION_NOT_VERIFIED"),
                        ("proof", "PROOF_NOT_VERIFIED")]:
            with self.subTest(k):
                r = copy.deepcopy(self.safety)
                r[k] = None
                dec = run(self.authority, r)
                self.assertNotEqual(dec.verdict, "ACCEPTED")
                self.assertIn(code, dec.codes)


# ---------------------------------------------------------------------------------------
class MetadataTests(SetUp):
    """Model confidence, proposer identity and self-asserted confirmation are irrelevant."""

    def test_metadata_does_not_change_verdicts(self):
        for fx in self.expected:
            if fx["authority"] != "authority.json":
                continue
            base = load_json(fx["request"])
            for conf, proposer, asserted in [(0, "x", False), (1000, "model:certain", True),
                                             (2 ** 53, "", True)]:
                r = copy.deepcopy(base)
                r["candidate"]["model_confidence"] = conf
                r["candidate"]["proposer"] = proposer
                r["interpretation"]["proposer"] = proposer
                with self.subTest(fx["name"], conf=conf):
                    # interpretation.proposer / model_asserts_confirmed are not covered by
                    # the confirmation signature, so they cannot break or forge it
                    r["interpretation"]["model_asserts_confirmed"] = asserted
                    dec = run(self.authority, r)
                    self.assertEqual(dec.verdict, fx["verdict"])


# ---------------------------------------------------------------------------------------
# Independent finite-model semantics of the fragment (test oracle only)
# ---------------------------------------------------------------------------------------

def registry_signatures(authority):
    sig = {}
    for e in authority["registry"]["symbols"]:
        sig[e["id"]] = (e["kind"], e["args"], e["result"])
    return sig


def random_model(authority, rng, size=3):
    sorts = [s["id"] for s in authority["registry"]["sorts"]]
    dom = {s: list(range(rng.randint(1, size))) for s in sorts}
    tables = {}
    for name, (kind, args, result) in registry_signatures(authority).items():
        keys = list(itertools.product(*[dom[a] for a in args]))
        if kind == "pred":
            tables[name] = {k: rng.random() < 0.5 for k in keys}
        else:
            tables[name] = {k: rng.choice(dom[result]) for k in keys}
    return dom, tables


def ev_term(t, M, env):
    if "var" in t:
        return env[t["var"]]
    return M[1][t["fn"]][tuple(ev_term(a, M, env) for a in t["args"])]


def ev(f, M, env):
    op = f["op"]
    if op == "true":
        return True
    if op == "false":
        return False
    if op == "pred":
        return M[1][f["symbol"]][tuple(ev_term(a, M, env) for a in f["args"])]
    if op == "eq":
        return ev_term(f["lhs"], M, env) == ev_term(f["rhs"], M, env)
    if op == "ne":
        return ev_term(f["lhs"], M, env) != ev_term(f["rhs"], M, env)
    if op == "not":
        return not ev(f["arg"], M, env)
    if op == "and":
        return ev(f["lhs"], M, env) and ev(f["rhs"], M, env)
    if op == "or":
        return ev(f["lhs"], M, env) or ev(f["rhs"], M, env)
    if op == "implies":
        return (not ev(f["lhs"], M, env)) or ev(f["rhs"], M, env)
    if op in ("forall", "exists"):
        vals = (ev(f["body"], M, {**env, f["var"]: d}) for d in M[0][f["sort"]])
        return all(vals) if op == "forall" else any(vals)
    raise ValueError(op)


def ev_claim(c, M):
    names = [p["name"] for p in c["params"]]
    for vals in itertools.product(*[M[0][p["sort"]] for p in c["params"]]):
        env = dict(zip(names, vals))
        if all(ev(a, M, env) for a in c["assumptions"]) and not ev(c["conclusion"], M, env):
            return False
    return True


# ---------------------------------------------------------------------------------------
def subformulas(f, path=()):
    yield path, f
    for k in ("arg", "lhs", "rhs", "body"):
        if k in f and isinstance(f[k], dict) and "op" in f[k]:
            yield from subformulas(f[k], path + (k,))


def get_at(f, path):
    for k in path:
        f = f[k]
    return f


def set_at(root, path, value):
    if not path:
        return value
    get_at(root, path[:-1])[path[-1]] = value
    return root


def var_names(c):
    names = [p["name"] for p in c["params"]]

    def walk(x):
        if isinstance(x, dict):
            if "var" in x and isinstance(x["var"], str):
                names.append(x["var"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(c)
    return sorted(set(names))


def mutate_claim(c, rng, authority):
    c = copy.deepcopy(c)
    sig = registry_signatures(authority)
    targets = [("conclusion", p) for p, _ in subformulas(c["conclusion"])]
    for i, a in enumerate(c["assumptions"]):
        targets += [(("assumptions", i), p) for p, _ in subformulas(a)]
    which = rng.randrange(12)
    if which == 0 and c["assumptions"]:
        c["assumptions"].pop(rng.randrange(len(c["assumptions"])))
        return c
    if which == 1 and c["assumptions"]:
        c["assumptions"].append(copy.deepcopy(rng.choice(c["assumptions"])))
        return c
    if which == 2 and len(c["assumptions"]) > 1:
        rng.shuffle(c["assumptions"])
        return c
    if which == 3 and c["params"]:
        c["params"].pop(rng.randrange(len(c["params"])))
        return c
    if which == 4 and len(c["params"]) > 1:
        rng.shuffle(c["params"])
        return c
    owner, path = rng.choice(targets)
    root = c["conclusion"] if owner == "conclusion" else c["assumptions"][owner[1]]
    f = get_at(root, path)
    op = f["op"]
    new = copy.deepcopy(f)
    if op in ("forall", "exists") and which % 2 == 0:
        new["op"] = "exists" if op == "forall" else "forall"
    elif op in ("and", "or", "implies") and which % 3 == 0:
        new["op"] = rng.choice([o for o in ("and", "or", "implies") if o != op])
    elif op in ("and", "or", "implies", "eq", "ne") and which % 3 == 1:
        new["lhs"], new["rhs"] = new["rhs"], new["lhs"]
    elif op == "not" and which % 2 == 1:
        new = new["arg"]
    elif op == "pred" and which % 2 == 0:
        same = [s for s, (k, args, _) in sig.items()
                if k == "pred" and len(args) == len(f["args"]) and s != f["symbol"]]
        if same:
            new["symbol"] = rng.choice(same)
    elif op == "pred" and f["args"]:
        i = rng.randrange(len(f["args"]))
        new["args"][i] = {"var": rng.choice(var_names(c) + ["zz"])}
    elif op == "eq" and which % 2 == 0:
        new["op"] = "ne"
    else:
        new = {"arg": new, "op": "not"}
    if owner == "conclusion":
        c["conclusion"] = set_at(c["conclusion"], path, new)
    else:
        c["assumptions"][owner[1]] = set_at(c["assumptions"][owner[1]], path, new)
    return c


def rename_consistently(c, rng, avoid):
    """α-rename every binder (fresh names), preserving meaning."""
    c = copy.deepcopy(c)
    counter = itertools.count()

    def fresh():
        while True:
            n = f"v{next(counter)}_{rng.randrange(1000)}"
            if n not in avoid:
                return n

    def ren_term(t, m):
        if "var" in t:
            return {"var": m.get(t["var"], t["var"])}
        return {"args": [ren_term(a, m) for a in t["args"]], "fn": t["fn"]}

    def ren(f, m):
        op = f["op"]
        if op in ("true", "false", "unsupported"):
            return f
        if op == "pred":
            return {**f, "args": [ren_term(a, m) for a in f["args"]]}
        if op in ("eq", "ne"):
            return {**f, "lhs": ren_term(f["lhs"], m), "rhs": ren_term(f["rhs"], m)}
        if op == "not":
            return {**f, "arg": ren(f["arg"], m)}
        if op in ("and", "or", "implies"):
            return {**f, "lhs": ren(f["lhs"], m), "rhs": ren(f["rhs"], m)}
        x = fresh()
        return {**f, "var": x, "body": ren(f["body"], {**m, f["var"]: x})}

    m = {}
    for p in c["params"]:
        x = fresh()
        m[p["name"]] = x
        p["name"] = x
    c["assumptions"] = [ren(a, m) for a in c["assumptions"]]
    c["conclusion"] = ren(c["conclusion"], m)
    return c


class SemanticFuzzTests(SetUp):
    """Mutation campaign without receipts (so that only the semantic checks decide)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lenient = copy.deepcopy(cls.authority)
        cls.lenient["require_elaboration"] = False
        cls.lenient["require_proof"] = False
        cls.positives = [load_json(fx["request"]) for fx in cls.expected
                         if fx["verdict"] == "ACCEPTED"]
        reg = cls.authority["registry"]["symbols"]
        cls.avoid = {e["id"] for e in reg} | {e["lean_name"] for e in reg}

    def submit(self, base, new_claim):
        r = copy.deepcopy(base)
        r["candidate"]["claim"] = new_claim
        r["elaboration"] = None
        r["proof"] = None
        first = run(self.lenient, r)
        r["candidate"]["lean_source"] = first.expected_lean_source  # honest re-rendering
        return run(self.lenient, r)

    def test_alpha_renaming_and_assumption_reordering_accepted(self):
        rng = random.Random(20261008)
        for base in self.positives:
            for _ in range(5):
                c = rename_consistently(base["candidate"]["claim"], rng, self.avoid)
                rng.shuffle(c["assumptions"])
                dec = self.submit(base, c)
                self.assertEqual(dec.verdict, "ACCEPTED", dec.diagnostics)

    def test_mutation_campaign_no_false_accept(self):
        rng = random.Random(78)
        accepted = rejected = 0
        for n in range(240):
            base = self.positives[n % len(self.positives)]
            c = base["candidate"]["claim"]
            for _ in range(rng.randint(1, 2)):
                c = mutate_claim(c, rng, self.authority)
            dec = self.submit(base, c)
            self.assertIn(dec.verdict, st.VERDICTS)
            if dec.verdict == "ACCEPTED":
                accepted += 1
                interp = base["interpretation"]["selected"]
                for _ in range(25):
                    M = random_model(self.authority, rng)
                    self.assertEqual(ev_claim(interp, M), ev_claim(c, M),
                                     f"FALSE ACCEPT: {json.dumps(c)}")
            else:
                rejected += 1
                self.assertTrue(dec.diagnostics)
        # the campaign must actually exercise the rejection paths
        self.assertGreater(rejected, 150)
        print(f"\n[semantic fuzz] mutants accepted={accepted} rejected={rejected}", file=sys.stderr)

    def test_rejected_mutants_with_genuine_receipts_still_rejected(self):
        # even a semantically wrong candidate that carries genuine receipts is rejected
        dec = run_bytes(load("authority.json"), load("requests/neg_negation_dropped.json"))
        self.assertEqual(dec.verdict, "REJECTED")
        self.assertNotIn("ELABORATION_NOT_VERIFIED", dec.codes)
        self.assertNotIn("PROOF_NOT_VERIFIED", dec.codes)


# ---------------------------------------------------------------------------------------
class ExplainTests(SetUp):
    def test_explain_structure(self):
        c = self.safety["candidate"]["claim"]
        out = st.explain(self.authority, c, binary=BINARY)
        self.assertIsNotNone(out)
        e = out["explanation"]
        self.assertEqual(e["variables"], c["params"])
        self.assertEqual(out["lean_source"], self.safety["candidate"]["lean_source"])
        self.assertTrue(out["well_typed"])
        self.assertEqual(e["negations"], 1)
        self.assertEqual([q["quantifier"] for q in e["quantifiers"]], ["forall"] * 3)
        self.assertEqual(sorted(r["id"] for r in e["references"]),
                         ["before", "revokedAt", "unsafeAt"])
        self.assertTrue(any("not semantically certified" in s or "NOT" in s or "certified" in s
                            for s in e["not_established"]))
        schema_validate(e, "explanation")

    def test_explain_reports_problems(self):
        bad = st.claim([], [], st.not_(st.pred("unsafeAt", st.var("t"), st.var("j"))))
        out = st.explain(self.authority, bad, binary=BINARY)
        self.assertEqual(sorted(out["free_variables"]), ["j", "t"])
        unsup = st.claim([], [], st.unsupported("modal:necessarily"))
        out = st.explain(self.authority, unsup, binary=BINARY)
        self.assertEqual(out["unsupported_constructs"], ["modal:necessarily"])
        self.assertFalse(out["well_typed"])


# ---------------------------------------------------------------------------------------
class LoopTests(SetUp):
    def test_repair_loop_uses_checker_feedback(self):
        good = self.safety
        bad = load_json("requests/neg_negation_dropped.json")
        seen = []

        def proposer(history):
            seen.append([fb["failure_codes"] for _, fb in history])
            return bad if not history else good

        out = st.propose_check_repair(self.authority, proposer, binary=BINARY)
        self.assertEqual(out, good)
        self.assertIn("NEGATION_MISMATCH", seen[1][0])

    def test_confident_wrong_proposer_never_accepted(self):
        bad = load_json("requests/neg_high_confidence_failing.json")
        out = st.propose_check_repair(self.authority, lambda h: bad, max_rounds=3, binary=BINARY)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
