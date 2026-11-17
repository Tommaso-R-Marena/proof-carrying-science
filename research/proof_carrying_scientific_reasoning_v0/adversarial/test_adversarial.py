"""Adversarial scientific-reasoning attacks (Family A/D/E/F subset)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "independent_checker"))

from scientific_reasoning import Authority, Context, Premise, derive_hyp, build_certificate
from scientific_reasoning.syntax import atom
from scientific_reasoning.evaluator import EvalError
import check_certificate as indep


def test_hidden_premise_rejected():
    Γ = Context(premises=(Premise(0, atom(0), Authority.empiricalAsserted),))
    try:
        derive_hyp(Γ, 7)
        assert False
    except EvalError:
        pass


def test_duplicate_ids_rejected():
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(0, atom(1), Authority.assumption),
        )
    )
    try:
        derive_hyp(Γ, 0)
        assert False
    except EvalError:
        pass


def test_statement_substitution_caught_by_independent():
    Γ = Context(premises=(Premise(0, atom(0), Authority.mathVerified),))
    j = derive_hyp(Γ, 0)
    cert = build_certificate(Γ, [j]).to_json()
    cert["conclusion"] = ["atom", 99]
    try:
        indep.check(cert)
        assert False
    except indep.CheckError:
        pass


def test_authority_promotion_attack():
    bad = {
        "premises": [{"id": 0, "formula": ["atom", 0], "authority": "hypothesis"}],
        "steps": [
            {"rule": "hyp", "support": [0], "authority": "hypothesis", "formula": ["atom", 0]}
        ],
        "final_support": [0],
        "final_authority": "mathVerified",
        "conclusion": ["atom", 0],
    }
    try:
        indep.check(bad)
        assert False
    except indep.CheckError:
        pass
