"""Property-style tests for lattice and assurance invariants."""

from __future__ import annotations

import itertools

from pcs_epistemic.assures import assure, supports_claim
from pcs_epistemic.compose import compose_assures
from pcs_epistemic.dialectic import agreement_core, dispute_frontier
from pcs_epistemic.lattice import EvidenceClass, le, meet


def test_le_reflexive_transitive_antisymmetric():
    classes = list(EvidenceClass)
    for a in classes:
        assert le(a, a)
    for a, b, c in itertools.product(classes, repeat=3):
        if le(a, b) and le(b, c):
            assert le(a, c)
    for a, b in itertools.product(classes, repeat=2):
        if le(a, b) and le(b, a):
            assert a == b


def test_meet_commutative_idempotent():
    for a, b in itertools.product(EvidenceClass, repeat=2):
        assert meet(a, b) == meet(b, a)
    for a in EvidenceClass:
        assert meet(a, a) == a


def test_agreement_dispute_partition_invariant():
    formal = {"id": "f", "required_class": "formal", "required_evidence": ["e"]}
    comp = {"id": "c", "required_class": "computational", "required_evidence": ["e2"]}
    models = [
        {
            "claims": [formal, comp],
            "evidence": [
                {"id": "e", "class": "formal", "accepted": True},
                {"id": "e2", "class": "computational", "accepted": True},
            ],
        },
        {
            "claims": [formal, comp],
            "evidence": [
                {"id": "e", "class": "formal", "accepted": True},
                {"id": "e2", "class": "computational", "accepted": False},
            ],
        },
    ]
    candidates = [formal, comp]
    core = agreement_core(models, candidates)
    dispute = dispute_frontier(models, candidates)
    assert not any(c in dispute for c in core)
    assert {c["id"] for c in core}.isdisjoint({c["id"] for c in dispute})


def test_compose_requires_disjoint_ids():
    claim = {"id": "c", "required_class": "computational", "required_evidence": ["e"]}
    ev = [{"id": "e", "class": "computational", "accepted": True}]
    assert assure(claim, ev, level="computational")
    collided = compose_assures(
        claim, ev, claim, ev, level_upstream="computational", level_downstream="computational"
    )
    assert collided["composed_assured"] is False


def test_vacuous_claim_supported():
    claim = {"id": "vacuous", "required_class": "formal", "required_evidence": []}
    assert supports_claim(claim, [])
    assert assure(claim, [], level="formal")
