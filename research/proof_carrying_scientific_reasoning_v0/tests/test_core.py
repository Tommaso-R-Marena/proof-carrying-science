from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning import (  # noqa: E402
    Authority,
    Context,
    Premise,
    build_certificate,
    certificate_invalidated,
    derive_and_i,
    derive_hyp,
    retract_context,
)
from scientific_reasoning.syntax import atom, land, lnot  # noqa: E402
from scientific_reasoning.evaluator import can_derive_unrelated  # noqa: E402
from scientific_reasoning.authority import meet, rank  # noqa: E402
from scientific_reasoning.explanation import explain  # noqa: E402
import check_certificate as indep  # noqa: E402


def test_and_intro_meet_authority():
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(1, atom(1), Authority.mathVerified),
        )
    )
    j0 = derive_hyp(Γ, 0)
    j1 = derive_hyp(Γ, 1)
    j = derive_and_i(j0, j1)
    assert j.authority == Authority.empiricalAsserted
    assert rank(j.authority) < rank(Authority.mathVerified)
    cert = build_certificate(Γ, [j0, j1, j])
    indep.check(cert.to_json())
    assert "empirical" in explain(cert).lower() or "Authority" in explain(cert)


def test_no_escalation_meet():
    assert meet(Authority.empiricalAsserted, Authority.mathVerified) == Authority.empiricalAsserted


def test_contradiction_no_unrelated():
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(1, lnot(atom(0)), Authority.empiricalAsserted),
            Premise(2, atom(2), Authority.hypothesis),
        )
    )
    assert can_derive_unrelated(Γ, 0)
    assert not can_derive_unrelated(Γ, 99)


def test_retraction_invalidates():
    Γ = Context(premises=(Premise(0, atom(0), Authority.assumption),))
    j = derive_hyp(Γ, 0)
    cert = build_certificate(Γ, [j])
    assert certificate_invalidated(cert, [0])
    Γ2 = retract_context(Γ, [0])
    assert Γ2.find(0) is None


def test_independent_rejects_escalation():
    bad = {
        "premises": [{"id": 0, "formula": ["atom", 0], "authority": "empiricalAsserted"}],
        "steps": [
            {
                "rule": "hyp",
                "support": [0],
                "authority": "mathVerified",
                "formula": ["atom", 0],
            }
        ],
        "final_support": [0],
        "final_authority": "mathVerified",
        "conclusion": ["atom", 0],
    }
    try:
        indep.check(bad)
        assert False, "should reject"
    except indep.CheckError:
        pass
