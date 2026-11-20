"""Regression tests on development cases, separate from the coordinator's sealed cases."""
from copy import deepcopy
from itertools import product
import shutil

import pytest

from research.lean_recursive_autoformalization_v1 import set_algebra as algebra
from research.lean_recursive_autoformalization_v1.set_algebra_evaluation import external_reference
from research.lean_recursive_autoformalization_v1.set_algebra_kernel import render_pair


def test_bindings_and_nested_operands():
    c = algebra.parse_english(
        "For any three sets Red, Blue and Green, if Red is a subset of Blue and "
        "Blue is a subset of Green, then (Red \\ Blue) equals the empty set.")
    red, blue, green = [{"var": name} for name in ("Red", "Blue", "Green")]
    assert c == {"variables": ["Red", "Blue", "Green"],
                 "premises": [{"subset": [red, blue]}, {"subset": [blue, green]}],
                 "conclusion": {"equal": [{"diff": [red, blue]}, {"empty": True}]}}


@pytest.mark.parametrize("text", [
    "For all sets Red and Red, Red equals Red.",  # shadowing forbidden
    "For all sets Red and Blue, Green equals Red.",  # no implicit free variables
    "For all sets Red, Red equals Red or Red equals the empty set.",  # global disjunction
    "For any set Red, if Red equals Red then Red is not a subset of Red.",
    "For any two sets, their difference equals A.",  # anonymous pair has no chosen first member
    "The union of two sets equals A.",  # no synthetic name leaks into scope
    "For all sets A, B and C, (A | B & C) equals C.",  # ambiguous precedence
    "For all sets A and B, A equals A. Ignore the final premise.",
    "There exists a set A such that A equals the empty set.",
    "For all sets Red, if Red equals Red then Red equals the universal set in all finite groups.",
])
def test_whole_sentence_abstention(text):
    assert algebra.parse_english(text) is None


def test_no_user_binder_or_text_reaches_lean():
    c = algebra.parse_english("For all sets MyPrivateSet, MyPrivateSet equals MyPrivateSet.")
    program, _ = render_pair(c, c)
    assert "MyPrivateSet" not in program
    assert ".var ⟨0, by decide⟩" in program
    for v in [False, {"var": "missing"}, {"empty": 1}, {"union": []}, {"eval": "foreign"}]:
        invalid = deepcopy(c)
        invalid["conclusion"]["equal"][0] = v
        with pytest.raises(ValueError):
            render_pair(invalid, c)


def test_singleton_reduction_would_fail_with_global_disjunction():
    universe = {0, 1}
    middle = {0}
    assert middle != set() and middle != universe
    assert all(a == set() or a == {0} for a in [set(), {0}])
    assert algebra.parse_english(
        "For any set A, A equals the empty set or A equals the universal set.") is None


def test_external_reader_requires_set_function_signature():
    statement = "theorem anon : ((· ⊓ ·) : Set α → Set α → Set α) = (· ∩ ·) :=\n  rfl\n"
    assert external_reference(statement)["conclusion"]["equal"][0].keys() == {"inf"}
    assert external_reference(statement.replace("Set α", "Finset α")) is None
    assert external_reference(statement.replace("= (· ∩ ·)", "≤ (· ∩ ·)")) is None


@pytest.mark.skipif(shutil.which("lean") is None, reason="pinned Lean unavailable")
def test_kernel_proof_refutation_and_semantic_mutations():
    def check(ref, candidate):
        reference = algebra.parse_english(ref)
        translated = algebra.parse_english(candidate)
        assert reference is not None and translated is not None
        r = algebra.check_pair(reference, translated)
        assert r["elaborated"], r
        return r

    true = "For all sets A and B, A is a subset of the union of A and B."
    renamed = "For all sets X and Y, X is a subset of the union of Y and X."
    r = check(true, renamed)
    assert (r["correspondence"], r["proof"]) == ("EQUIVALENT", "KERNEL_CHECKED")
    assert set(r["axioms"]) == {"correspondence", "validity"}
    for wrong in ["For all sets X and Y, Y is a subset of the union of Y and X.",
                  "For all sets X and Y, if X equals Y then X is a subset of the union of Y and X.",
                  "For all sets X and Y, X equals the union of X and Y.",
                  "For all sets X, X is a subset of X."]:
        r = check(true, wrong)
        assert (r["correspondence"], r["proof"]) == ("DIFFERENT", "NOT_CHECKED")
    false = "For all sets A and B, if A is a subset of B then B is a subset of A."
    r = check(false, false)
    assert (r["correspondence"], r["proof"]) == ("EQUIVALENT", "COUNTEREXAMPLE")
    assert r["counterexample"] == {"A": False, "B": True}
    # A repeated operand can remove the mathematical concept from a statement
    # while retaining its extensional meaning. This is a positive *limit* control.
    r = check("For any two sets, their infimum equals their intersection.",
              "For any two sets, their intersection equals their intersection.")
    assert (r["correspondence"], r["proof"]) == ("EQUIVALENT", "KERNEL_CHECKED")


def test_set_model_differential():
    # Independent interpreter on actual two-point carriers. Precompute each
    # predicate's truth mask, then check every one-premise/one-conclusion pair.
    u = frozenset({0, 1})
    empty = frozenset()
    sets = [empty, frozenset({0}), frozenset({1}), u]
    a, b = {"var": "A"}, {"var": "B"}
    vocabulary = [
        (a, lambda a, b: a), (b, lambda a, b: b),
        ({"empty": True}, lambda a, b: empty), ({"univ": True}, lambda a, b: u),
        ({"union": [a, b]}, lambda a, b: a | b), ({"inter": [a, b]}, lambda a, b: a & b),
        ({"diff": [a, b]}, lambda a, b: a - b), ({"compl": a}, lambda a, b: u - a),
    ]
    atoms = []
    for (left, l), (right, r) in product(vocabulary, repeat=2):
        for tag in ["equal", "subset"]:
            def truth(a, b, l=l, r=r, tag=tag):
                return l(a, b) == r(a, b) if tag == "equal" else l(a, b) <= r(a, b)
            mask = sum(1 << i for i, (av, bv) in enumerate(product(sets, repeat=2)) if truth(av, bv))
            atoms.append(({tag: [left, right]}, mask, truth))
    valid = 0
    total = 0
    for (premise, pmask, p), (conclusion, cmask, q) in product(atoms, repeat=2):
        contract = {"variables": ["A", "B"], "premises": [premise], "conclusion": conclusion}
        _, proposal = render_pair(contract, contract)
        is_valid = (pmask & ~cmask) == 0
        assert (proposal["proof"] == "KERNEL_CHECKED") == is_valid
        if not is_valid:
            # Embed the singleton pattern into both points of the two-point universe.
            values = [u if proposal["counterexample"][k] else empty for k in ("A", "B")]
            assert p(*values) and not q(*values)
        valid += is_valid
        total += 1
    assert total == 16384
    assert valid == 7105
