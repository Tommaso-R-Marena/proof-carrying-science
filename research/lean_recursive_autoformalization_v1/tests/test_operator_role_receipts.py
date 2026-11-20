from copy import deepcopy
import itertools
import json
from pathlib import Path
import shutil

import pytest

from research.lean_recursive_autoformalization_v1 import operator_role_receipts as roles
from research.lean_recursive_autoformalization_v1.set_algebra import parse_english

CASES = {
    498: ("Prove that the infimum (greatest lower bound) of two sets is the same as their intersection.",
          "theorem inf_eq_inter : ((· ⊓ ·) : Set α → Set α → Set α) = (· ∩ ·) :=\n  rfl\n"),
    499: ("Prove that for any two sets, the result of taking their union is the same as taking their supremum.",
          "theorem sup_eq_union : ((· ⊔ ·) : Set α → Set α → Set α) = (· ∪ ·) :=\n  rfl\n"),
}


def test_bindings_fail_closed_before_proof():
    en, formal = CASES[498]
    candidate = parse_english(en)
    for i, text, source in [(498, en + " ", formal), (498, en, formal + " "),
                            (498, "\ud800", formal), (498, en * 1024, formal),
                            (499, en, formal), (1000, en, formal)]:
        outcome = roles.verify(i, text, source, candidate)
        assert not outcome["strict_accept"]
        assert outcome["concept"] in {"UNSUPPORTED_SOURCE", "SOURCE_BINDING_MISMATCH"}
    forged = deepcopy(candidate)
    forged["conclusion"]["equal"][0] = {"var": "unbound"}
    assert roles.verify(498, en, formal, forged)["concept"] == "UNKNOWN"


@pytest.mark.parametrize("i,expected", [(498, ("inf", "inter")), (499, ("union", "sup"))])
def test_all_256_operator_and_argument_role_pairs(i, expected):
    en, formal = CASES[i]
    reference = roles.external_reference(formal)
    a, b = {"var": "X"}, {"var": "Y"}
    operands = [(tag, [left, right]) for tag in ["union", "inter", "sup", "inf"]
                for left, right in itertools.product([a, b], repeat=2)]
    matched = 0
    for (lhs, lhs_args), (rhs, rhs_args) in itertools.product(operands, repeat=2):
        candidate = {"variables": ["X", "Y"], "premises": [],
                     "conclusion": {"equal": [{lhs: lhs_args}, {rhs: rhs_args}]}}
        _, _, _, forecast = roles._program(reference, candidate, roles.SOURCES[i][2])
        expected_match = (lhs, rhs) == expected and lhs_args == rhs_args == [a, b]
        assert forecast == expected_match
        matched += forecast
    assert matched == 1


@pytest.mark.skipif(shutil.which("lean") is None, reason="pinned Lean unavailable")
@pytest.mark.parametrize("i", [498, 499])
def test_kernel_controls_and_frozen_extensional_program(i):
    en, formal = CASES[i]
    directory = Path(roles.__file__).parent / "results" / "set_algebra"
    old = json.loads((directory / "forml4_basic.json").read_text())
    old_receipt = next(r["review"] for r in old["items"] if r["source_index"] == i)
    fixed = json.loads((directory / "operator_roles.json").read_text())
    for name, candidate in roles.controls(parse_english(en)).items():
        receipt = roles.verify(i, en, formal, candidate)
        assert receipt == fixed["results"][str(i)][name]
        assert (receipt["correspondence"], receipt["proof"]) == ("EQUIVALENT", "KERNEL_CHECKED")
        assert receipt["strict_accept"] is (name in {"original", "alpha_renamed"})
        assert "operatorRoles" in receipt["axioms"]
        assert "alignment" in receipt["axioms"]
        if name == "original":
            assert receipt["extensional_lean_sha256"] == old_receipt["lean_sha256"]
