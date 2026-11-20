"""Tests for the bounded compile proxy and kernel reference checks."""
from lean_compile_oracle import compare_reference, compile_lean, normalize_candidate


def test_elaboration_template_drops_candidate_name_and_emits_no_admission():
    assert normalize_candidate("theorem t (n : Nat) : n = n") == (
        "import Std\nset_option autoImplicit false\ndef Candidate : Prop := ∀ (x0 : Nat), x0 = x0\n"
    )


def test_annotations_only_probe_a_proposition():
    row = compile_lean("import Mathlib\ntheorem t : False := by sorry")
    assert row["status"] == "WELL_TYPED_UNVALIDATED"
    assert not row["proof_verified"]
    assert "sorry" not in row["normalized"]


def test_proof_of_alpha_renamed_reference_and_separate_axiom_audit():
    row = compare_reference("theorem a (n : Nat) : n = n", "example (m : Nat) : m = m")
    assert row["status"] == "PROOF_VERIFIED"
    assert row["equivalence_verified"] and row["proof_axioms"] == []


def test_false_but_equivalent_and_weakened_cases():
    equal = compare_reference("example : False", "example : False")
    assert equal["status"] == "SEMANTICALLY_EQUIVALENT" and not equal["proof_verified"]
    weaker = compare_reference("example : True", "example : False")
    assert weaker["status"] == "WELL_TYPED_UNVALIDATED" and not weaker["equivalence_verified"]


def test_well_formed_expression_with_wrong_type():
    row = compile_lean("example : 2 + 2")
    assert row["syntax_valid"] and row["status"] == "ELABORATION_FAILED"


def test_invalid_expression_is_distinct_from_a_type_error():
    row = compile_lean("example (n : Nat) : n +")
    assert row["syntax_valid"] is False and row["status"] == "SYNTAX_INVALID"
