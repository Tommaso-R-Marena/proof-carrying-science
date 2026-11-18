"""Regressions for SECURITY_FINDINGS_V1 — frozen JSON must not be edited."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "independent_checker"))
sys.path.insert(0, str(ROOT / "python"))

import check_certificate_v1 as v1
from scientific_reasoning.authority import meet
from scientific_reasoning.syntax import Authority
from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Context, Premise, atom


FINDINGS = ROOT / "results" / "security_findings_v1"


def _load(name: str) -> dict:
    return json.loads((FINDINGS / name).read_text(encoding="utf-8"))


def test_finding_A_rejected_by_v1():
    try:
        v1.check(_load("finding_A_forged_andI.json"))
        assert False, "forged andI must be rejected"
    except v1.CheckError:
        pass


def test_finding_B_forged_rejected():
    try:
        v1.check(_load("finding_B_forged_andE1.json"))
        assert False
    except v1.CheckError:
        pass


def test_finding_C_escalation_rejected():
    # Legacy cert claims mathVerified on andI of empirical+math — no citations either
    try:
        v1.check(_load("finding_C_authority_escalation_andI.json"))
        assert False
    except v1.CheckError:
        pass


def test_finding_C_escalation_with_citations_rejected():
    bad = {
        "schema_version": 1,
        "premises": [
            {"id": 0, "formula": ["atom", 0], "declared_authority": "empiricalAsserted"},
            {"id": 1, "formula": ["atom", 1], "declared_authority": "mathVerified"},
        ],
        "steps": [
            {"id": 0, "rule": "hyp", "premise_id": 0, "authority": "mathVerified"},
            {"id": 1, "rule": "hyp", "premise_id": 1},
            {"id": 2, "rule": "andI", "left": 0, "right": 1, "authority": "mathVerified"},
        ],
        "conclusion_step": 2,
        "final_authority": "mathVerified",
    }
    try:
        v1.check(bad)
        assert False
    except v1.CheckError:
        pass


def test_finding_F_declared_math_not_established():
    cert = {
        "schema_version": 1,
        "premises": [
            {"id": 0, "formula": ["atom", 0], "declared_authority": "mathVerified"}
        ],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    j = v1.check(cert)
    assert j.declared_authority == "mathVerified"
    assert j.math_established is False


def test_finding_G_meet_commutative():
    assert meet(Authority.assumption, Authority.empiricalAsserted) == meet(
        Authority.empiricalAsserted, Authority.assumption
    )


def test_valid_andE_control_v1():
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.mathVerified),
            Premise(1, atom(1), Authority.mathVerified),
        )
    )
    b = Builder(Γ)
    a = b.hyp(0)
    c = b.hyp(1)
    d = b.and_i(a, c)
    e = b.and_e1(d)
    cert = b.finish(e).to_json()
    j = v1.check(cert)
    assert j.formula == ["atom", 0]
    assert j.math_established is False


def test_bool_as_premise_id_rejected():
    bad = {
        "schema_version": 1,
        "premises": [{"id": True, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": True}],
        "conclusion_step": 0,
    }
    try:
        v1.check(bad)
        assert False
    except v1.CheckError:
        pass


def test_forward_ref_rejected():
    bad = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [
            {"id": 0, "rule": "andE1", "from": 1},
            {"id": 1, "rule": "hyp", "premise_id": 0},
        ],
        "conclusion_step": 0,
    }
    try:
        v1.check(bad)
        assert False
    except v1.CheckError:
        pass
