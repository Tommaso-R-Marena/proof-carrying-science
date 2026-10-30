from pcs_epistemic.assures import assure, supports_claim
from pcs_epistemic.compose import compose_assures


FORMAL_CLAIM = {
    "id": "c_formal",
    "required_class": "formal",
    "required_evidence": ["e1"],
}


def test_formal_evidence_assures_formal():
    evidence = [{"id": "e1", "class": "formal", "accepted": True}]
    assert assure(FORMAL_CLAIM, evidence, level="formal")


def test_computational_cannot_assure_formal():
    evidence = [{"id": "e1", "class": "computational", "accepted": True}]
    assert not assure(FORMAL_CLAIM, evidence, level="formal")


def test_missing_evidence_blocks():
    assert not supports_claim(FORMAL_CLAIM, [])


def test_compose_pipeline():
    up_claim = {"id": "c1", "required_class": "computational", "required_evidence": ["e1"]}
    down_claim = {"id": "c2", "required_class": "computational", "required_evidence": ["e2"]}
    up_ev = [{"id": "e1", "class": "computational", "accepted": True}]
    down_ev = [{"id": "e2", "class": "computational", "accepted": True}]
    result = compose_assures(
        up_claim,
        up_ev,
        down_claim,
        down_ev,
        level_upstream="computational",
        level_downstream="computational",
    )
    assert result["composed_assured"] is True


def test_compose_rejects_id_collision():
    claim = {"id": "c", "required_class": "computational", "required_evidence": ["e1"]}
    ev = [{"id": "e1", "class": "computational", "accepted": True}]
    result = compose_assures(
        claim,
        ev,
        claim,
        ev,
        level_upstream="computational",
        level_downstream="computational",
    )
    assert result["evidence_disjoint"] is False
    assert result["composed_assured"] is False
