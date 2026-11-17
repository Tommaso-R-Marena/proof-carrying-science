"""Lock known Python↔Lean break points and the fixes we claim.

See verification/EQUIVALENCE_BREAKS.md.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "independent_checker"))
sys.path.insert(0, str(ROOT / "python"))

import check_certificate_v1 as v1
from scientific_reasoning.authority import meet as auth_meet
from scientific_reasoning.syntax import Authority, Context, Premise, atom, land, lnot
from scientific_reasoning.certificates_v1 import Builder

# Local Lean-shaped helpers (avoid cross-module import fragility under pytest).
def lean_check_steps(premises, steps):
    ids = [p["id"] for p in premises]
    if len(ids) != len(set(ids)):
        return None
    pm = {p["id"]: p for p in premises}
    acc = []
    for st in steps:
        tag = st[0]
        if tag == "hyp":
            pid = st[1]
            if pid not in pm:
                return None
            p = pm[pid]
            acc.append(
                {
                    "formula": p["formula"],
                    "support": [pid],
                    "declared": p["declared_authority"],
                }
            )
        elif tag == "andI":
            l, r = st[1], st[2]
            if not (l < len(acc) and r < len(acc)):
                return None
            jl, jr = acc[l], acc[r]
            acc.append(
                {
                    "formula": ["and", jl["formula"], jr["formula"]],
                    "support": jl["support"] + jr["support"],
                    "declared": v1.meet(jl["declared"], jr["declared"]),
                }
            )
        elif tag in ("andE1", "andE2"):
            s = st[1]
            if not (s < len(acc)):
                return None
            j0 = acc[s]
            φ = j0["formula"]
            if not (isinstance(φ, list) and len(φ) == 3 and φ[0] == "and"):
                return None
            out = φ[1] if tag == "andE1" else φ[2]
            acc.append(
                {"formula": out, "support": list(j0["support"]), "declared": j0["declared"]}
            )
        else:
            return None
    return acc


def lean_check_certificate(premises, steps, conclusion):
    js = lean_check_steps(premises, steps)
    if js is None or not (0 <= conclusion < len(js)):
        return None
    return js[conclusion]


AUTH_ALL = list(Authority)


def test_meet_lock_v1_matches_authority_library():
    """Break #3: duplicated meet tables must not drift."""
    for a, b in itertools.product(AUTH_ALL, repeat=2):
        assert v1.meet(a.value, b.value) == auth_meet(a, b).value, (a, b)


def test_andE_on_atom_rejected_by_both_paths():
    premises = [
        {"id": 0, "formula": ["atom", 0], "declared_authority": "empiricalAsserted"},
    ]
    assert lean_check_steps(premises, [("hyp", 0), ("andE1", 0)]) is None
    bad = {
        "schema_version": 1,
        "premises": premises,
        "steps": [
            {"id": 0, "rule": "hyp", "premise_id": 0},
            {"id": 1, "rule": "andE1", "from": 0},
        ],
        "conclusion_step": 1,
    }
    try:
        v1.check(bad)
        assert False, "andE1 on atom must fail"
    except v1.CheckError:
        pass


def test_step_id_vs_lean_divergence_documented():
    """Python requires step.id == index; Lean StepSpec has no id — documented break."""
    premises = [
        {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"},
    ]
    assert lean_check_certificate(premises, [("hyp", 0)], 0) is not None


def test_wf_empty_steps_rejected_python_only():
    """Lean StructuredCertificate can be empty-steps; Python WF rejects."""
    cert = {
        "schema_version": 1,
        "premises": [
            {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"},
        ],
        "steps": [],
        "conclusion_step": 0,
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError:
        pass
    # Lean-shaped core has nothing to run
    assert lean_check_certificate(cert["premises"], [], 0) is None


def test_wf_step_id_mismatch_rejected():
    cert = {
        "schema_version": 1,
        "premises": [
            {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"},
        ],
        "steps": [{"id": 7, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    try:
        v1.check(cert)
        assert False
    except v1.CheckError:
        pass
    # Lean StepSpec list has no step-id field — same reconstruction still works
    j = lean_check_certificate(cert["premises"], [("hyp", 0)], 0)
    assert j is not None and j["formula"] == ["atom", 0]


def test_claimed_authority_mismatch_rejected():
    Γ = Context([Premise(0, atom(0), Authority.empiricalAsserted)])
    b = Builder(Γ)
    b.hyp(0)
    c = b.finish().to_json()
    c["steps"][0]["authority"] = "mathVerified"
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_math_established_claim_rejected():
    Γ = Context([Premise(0, atom(0), Authority.mathVerified)])
    b = Builder(Γ)
    b.hyp(0)
    c = b.finish().to_json()
    c["steps"][0]["math_established"] = True
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass
    b2 = Builder(Γ)
    b2.hyp(0)
    j = v1.check(b2.finish().to_json())
    assert j.declared_authority == "mathVerified"
    assert j.math_established is False  # Finding F: declared ≠ established


def test_bool_schema_version_rejected():
    c = {
        "schema_version": True,  # JSON true must not be schema 1
        "premises": [
            {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"},
        ],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_classical_explosion_story_vs_derivability():
    """Document Finding E in Python: Boolean models of P∧¬P do not exist;
    our ND fragment still cannot derive unrelated atoms (Lean proves this)."""
    # Boolean satisfiability of premises atom0 and not atom0 is impossible
    def eval_f(φ, σ):
        tag = φ[0]
        if tag == "atom":
            return σ[φ[1]]
        if tag == "not":
            return not eval_f(φ[1], σ)
        if tag == "and":
            return eval_f(φ[1], σ) and eval_f(φ[2], σ)
        raise AssertionError(tag)

    premises = [("atom", 0), ("not", ("atom", 0)), ("atom", 2)]
    sats = []
    for bits in itertools.product([False, True], repeat=3):
        σ = {0: bits[0], 1: bits[1], 2: bits[2]}
        if all(eval_f(p, σ) for p in premises):
            sats.append(σ)
    assert sats == [], "classical models of demoΓ must be empty (explosion vacuous)"

    # Certificate path cannot invent atom 99
    Γ = Context(
        [
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(1, lnot(atom(0)), Authority.empiricalAsserted),
            Premise(2, atom(2), Authority.hypothesis),
        ]
    )
    b = Builder(Γ)
    b.hyp(0)
    b.hyp(1)
    b.hyp(2)
    j = v1.check(b.finish().to_json())
    assert j.formula != ["atom", 99]


def test_forward_ref_andI_rejected_both():
    premises = [
        {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"},
    ]
    assert lean_check_steps(premises, [("andI", 0, 0)]) is None
    bad = {
        "schema_version": 1,
        "premises": premises,
        "steps": [{"id": 0, "rule": "andI", "left": 0, "right": 0}],
        "conclusion_step": 0,
    }
    try:
        v1.check(bad)
        assert False
    except v1.CheckError:
        pass
