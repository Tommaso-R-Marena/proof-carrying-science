from pcs.decision import assess_claim, OPEN, FAILED, COMPUTATIONAL, FORMAL, EMPIRICAL, MIXED

def ev(kind="computational_test", outcome="PASS"):
    return {"id": "E", "kind": kind, "outcome": outcome}

def claim(kind="computational", required=None):
    return {"id": "C", "kind": kind, "required_evidence": required if required is not None else ["E"]}

def test_missing_and_unverified_do_not_accept():
    assert assess_claim(claim(), {})["status"] == OPEN
    assert assess_claim(claim(), {"E": ev(outcome="UNVERIFIED")})["status"] == OPEN

def test_failure_dominates():
    assert assess_claim(claim(), {"E": ev(outcome="FAIL")})["status"] == FAILED

def test_computational_acceptance():
    assert assess_claim(claim(), {"E": ev()})["status"] == COMPUTATIONAL

def test_formal_requires_only_passing_formal_evidence():
    assert assess_claim(claim("formal"), {"E": ev("formal_proof")})["status"] == FORMAL
    assert assess_claim(claim("formal"), {"E": ev("computational_test")})["status"] == OPEN

def test_empirical_and_mixed_classes_remain_distinct():
    assert assess_claim(claim("empirical"), {"E": ev("empirical_validation")})["status"] == EMPIRICAL
    mixed = {"id":"C","kind":"mixed","required_evidence":["F","V"]}
    evidence = {"F":{"id":"F","kind":"formal_proof","outcome":"PASS"},"V":{"id":"V","kind":"statistical_validation","outcome":"PASS"}}
    assert assess_claim(mixed, evidence)["status"] == MIXED
