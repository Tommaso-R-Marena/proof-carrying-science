from research.scientific_semantics_v3.assurance import verify,THEOREMS,ALLOWED_AXIOMS


def test_actual_lean_partial_domain_proof_and_complete_axiom_audit():
    receipt=verify()
    assert receipt["status"]=="KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS",receipt
    assert set(receipt["axiom_audit"])==set(THEOREMS)
    assert all(set(v["axioms"])<=ALLOWED_AXIOMS for v in receipt["axiom_audit"].values())
    assert receipt["Python_Lean_refinement"]=="OPEN" and receipt["authority"] is False
