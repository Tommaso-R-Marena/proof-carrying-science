"""Authored regression corpus for the restricted Boolean receiver.

The two files enter the CLI separately. Expected outcomes and witness values
are fixed here; the receiver neither constructs nor consults these labels.
"""
import itertools
import json
from pathlib import Path
import subprocess

import pytest

LEAN = Path(__file__).resolve().parents[1] / "lean"


def var(name):
    return {"var": {"name": name}}


def truth(value):
    return {"truth": {"value": value}}


def binary(tag, left, right):
    return {tag: {"left": left, "right": right}}


def quant(tag, name, body):
    return {tag: {"name": name, "body": body}}


def neg(body):
    return {"neg": {"body": body}}


def contract(premise, conclusion, names=("p", "q")):
    return {"format": "pcs-bool-contract-v1", "variables": list(names),
            "contract": {"premise": premise, "conclusion": conclusion}}


def canonical(doc):
    return (json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode()


P, Q = var("p"), var("q")
TOP, BOTTOM = truth(True), truth(False)
FORWARD = binary("implies", P, Q)
EQUALITY = binary("conj", FORWARD, binary("implies", Q, P))
EQUIVALENT = "SEMANTICALLY_EQUIVALENT"
DIFF = "COUNTEREXAMPLE_FOUND"


CASES = [
    ("double-negation", contract(P, Q), contract(neg(neg(P)), neg(neg(Q))), EQUIVALENT, "REFUTED"),
    ("implication-as-negated-conjunction", contract(TOP, FORWARD),
     contract(TOP, neg(binary("conj", P, neg(Q)))), EQUIVALENT, "REFUTED"),
    ("valid-identity", contract(P, P), contract(P, P), EQUIVALENT, "VALID_FOR_ALL_ASSIGNMENTS"),
    ("reverse-implication", contract(TOP, FORWARD), contract(TOP, binary("implies", Q, P)),
     DIFF, "UNASSESSED"),
    ("replace-valid-conditional-with-unrelated-valid-conditional", contract(P, P), contract(Q, Q),
     DIFF, "UNASSESSED"),
    ("drop-premise", contract(P, Q), contract(TOP, Q), DIFF, "UNASSESSED"),
    ("impossible-premise", contract(P, Q), contract(BOTTOM, Q), DIFF, "UNASSESSED"),
    ("true-conclusion", contract(P, Q), contract(P, TOP), DIFF, "UNASSESSED"),
    ("weaken-conjunction", contract(TOP, binary("conj", P, Q)), contract(TOP, P), DIFF, "UNASSESSED"),
    ("quantifier-order", contract(TOP, quant("every", "p", quant("someVal", "q", EQUALITY)), ()),
     contract(TOP, quant("someVal", "q", quant("every", "p", EQUALITY)), ()), DIFF, "UNASSESSED"),
    ("rename-binder", contract(TOP, quant("every", "x", var("x")), ()),
     contract(TOP, quant("every", "y", var("y")), ()), EQUIVALENT, "REFUTED"),
    ("capture-free-name", contract(TOP, quant("someVal", "x", P)),
     contract(TOP, quant("someVal", "p", P)), DIFF, "UNASSESSED"),
    ("switch-quantifier", contract(TOP, quant("every", "p", P), ()),
     contract(TOP, quant("someVal", "p", P), ()), DIFF, "UNASSESSED"),
    ("distinct-closed-tautologies", contract(TOP, quant("every", "p", binary("implies", P, P)), ()),
     contract(TOP, TOP, ()), EQUIVALENT, "VALID_FOR_ALL_ASSIGNMENTS"),
    ("measure-outside-language", contract(TOP, TOP), contract(TOP, {"measure": "real_line"}),
     "UNKNOWN", None),
    ("reverse-signature", contract(P, Q), contract(P, Q, ("q", "p")), "UNKNOWN", None),
    ("unbound-name", contract(P, Q), contract(P, var("r")), "UNKNOWN", None),
    ("duplicate-signature", contract(P, Q), contract(P, P, ("p", "p")), "UNKNOWN", None),
]


def interpret(formula, variables):
    """Independent named interpreter using Python booleans and explicit binders."""
    (kind, fields), = formula.items()
    if kind == "var":
        return variables[fields["name"]]
    if kind == "truth":
        return fields["value"]
    if kind == "neg":
        return not interpret(fields["body"], variables)
    if kind in {"conj", "implies"}:
        left = interpret(fields["left"], variables)
        right = interpret(fields["right"], variables)
        return left and right if kind == "conj" else not left or right
    values = (interpret(fields["body"], {**variables, fields["name"]: b}) for b in (False, True))
    return {"every": all, "someVal": any}[kind](values)


def observation(doc, variables):
    return {role: interpret(formula, variables) for role, formula in doc["contract"].items()}


@pytest.fixture(scope="module", autouse=True)
def build_checker():
    subprocess.run(["lake", "build", "PCS.V2.FiniteReferenceFixtures"], cwd=LEAN, check=True, timeout=180)


@pytest.mark.parametrize("case,ref,candidate,label,validity", CASES, ids=[r[0] for r in CASES])
def test_reference_receiver(tmp_path, case, ref, candidate, label, validity):
    paths = [tmp_path / "reference.json", tmp_path / "candidate.json"]
    for path, doc in zip(paths, (ref, candidate), strict=True):
        path.write_bytes(canonical(doc))
    proc = subprocess.run(["lake", "env", "lean", "--run", "tools/CheckFiniteReference.lean", *paths],
                          cwd=LEAN, capture_output=True, text=True, timeout=45)
    assert proc.returncode == {EQUIVALENT: 0, DIFF: 1, "UNKNOWN": 2}[label], proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["translation"] == label
    assert result.get("validity") == validity
    if label == "UNKNOWN":
        assert result["reason"]
        return
    if label == DIFF:
        assert result["reference"] == observation(ref, result["assignment"])
        assert result["candidate"] == observation(candidate, result["assignment"])
        assert result["reference"] != result["candidate"]
        return
    variables = ref["variables"]
    for bits in itertools.product((False, True), repeat=len(variables)):
        assignment = dict(zip(variables, bits, strict=True))
        verdict = observation(candidate, assignment)
        assert observation(ref, assignment) == verdict
        if validity == "VALID_FOR_ALL_ASSIGNMENTS":
            assert not verdict["premise"] or verdict["conclusion"]
    if validity == "REFUTED":
        assert observation(candidate, result["assignment"]) == {"premise": True, "conclusion": False}
