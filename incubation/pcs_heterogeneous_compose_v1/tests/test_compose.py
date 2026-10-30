from heck.canonical import digest_obj
from heck.compose import CompositeClaim, EvidenceAtom, accept, achieved_level, compose_receipt
from heck.levels import Level


def _atom(i: str, level: Level, supported: bool = True) -> EvidenceAtom:
    return EvidenceAtom(
        id=i,
        level=level,
        supported=supported,
        claim_id=f"c-{i}",
        evidence_sha256=digest_obj({"id": i}),
    )


def test_formal_singleton_accepts():
    atoms = [_atom("f", Level.FORMAL)]
    claim = CompositeClaim("1", Level.FORMAL, ("f",))
    assert accept(atoms, claim)
    assert achieved_level(atoms, claim) is Level.FORMAL


def test_empirical_cannot_satisfy_formal():
    atoms = [_atom("e", Level.EMPIRICAL)]
    claim = CompositeClaim("1", Level.FORMAL, ("e",))
    assert not accept(atoms, claim)


def test_heterogeneous_meet_is_empirical():
    atoms = [_atom("f", Level.FORMAL), _atom("e", Level.EMPIRICAL)]
    claim_emp = CompositeClaim("1", Level.EMPIRICAL, ("f", "e"))
    claim_form = CompositeClaim("2", Level.FORMAL, ("f", "e"))
    assert achieved_level(atoms, claim_emp) is Level.EMPIRICAL
    assert accept(atoms, claim_emp)
    assert not accept(atoms, claim_form)


def test_unsupported_and_missing_and_empty():
    atoms = [_atom("f", Level.FORMAL, supported=False)]
    assert not accept(atoms, CompositeClaim("1", Level.FORMAL, ("f",)))
    assert not accept(atoms, CompositeClaim("2", Level.FORMAL, ("missing",)))
    assert not accept([], CompositeClaim("3", Level.FORMAL, ()))


def test_receipt_deterministic_and_reasons():
    atoms = [_atom("e", Level.EMPIRICAL)]
    claim = CompositeClaim("1", Level.FORMAL, ("e",))
    r1 = compose_receipt(atoms, claim)
    r2 = compose_receipt(atoms, claim)
    assert r1 == r2
    assert r1["accepted"] is False
    assert any("underleveled" in x or "achieved" in x for x in r1["rejection_reasons"]) or r1[
        "rejection_reasons"
    ]
