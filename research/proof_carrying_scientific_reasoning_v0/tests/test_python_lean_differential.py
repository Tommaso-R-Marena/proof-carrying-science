"""Differential harness: Lean-shaped LTR checker ↔ schema-v1 independent checker.

Mirrors `checkStepsLTR` / `checkCertificate` control flow from
`lean/ScientificReasoning/CheckCertificate.lean` on the structured core
(unique ids, step reconstruction, conclusion index). JSON surface checks
remain Python-only (trust boundary).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "independent_checker"))
sys.path.insert(0, str(ROOT / "python"))

import check_certificate_v1 as v1
from scientific_reasoning.authority import meet as meet_auth
from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Authority, Context, Premise, atom


Step = Union[
    Tuple[str, int],  # ("hyp", pid) | ("andE1"|"andE2", src)
    Tuple[str, int, int],  # ("andI", left, right)
]


@dataclass
class J:
    formula: Any
    support: List[int]
    declared: str
    math_established: bool = False


def _meet(a: str, b: str) -> str:
    return meet_auth(Authority(a), Authority(b)).value


def lean_check_steps(
    premises: List[dict], steps: List[Step]
) -> Optional[List[J]]:
    """Lean `checkStepsLTR` shape over an explicit StepSpec list."""
    ids = [p["id"] for p in premises]
    if len(ids) != len(set(ids)):
        return None
    pm = {p["id"]: p for p in premises}
    acc: List[J] = []
    for st in steps:
        tag = st[0]
        if tag == "hyp":
            pid = st[1]
            if pid not in pm:
                return None
            p = pm[pid]
            acc.append(
                J(p["formula"], [pid], p["declared_authority"], False)
            )
        elif tag == "andI":
            l, r = st[1], st[2]
            if not (l < len(acc) and r < len(acc)):
                return None
            jl, jr = acc[l], acc[r]
            acc.append(
                J(
                    ["and", jl.formula, jr.formula],
                    jl.support + jr.support,
                    _meet(jl.declared, jr.declared),
                    jl.math_established and jr.math_established,
                )
            )
        elif tag in ("andE1", "andE2"):
            s = st[1]
            if not (s < len(acc)):
                return None
            j0 = acc[s]
            φ = j0.formula
            if not (isinstance(φ, list) and len(φ) == 3 and φ[0] == "and"):
                return None
            out = φ[1] if tag == "andE1" else φ[2]
            acc.append(J(out, list(j0.support), j0.declared, j0.math_established))
        else:
            return None
    return acc


def lean_check_certificate(
    premises: List[dict], steps: List[Step], conclusion: int
) -> Optional[J]:
    js = lean_check_steps(premises, steps)
    if js is None or not (0 <= conclusion < len(js)):
        return None
    return js[conclusion]


def _steps_from_builder_cert(cert_json: dict) -> List[Step]:
    out: List[Step] = []
    for s in cert_json["steps"]:
        rule = s["rule"]
        if rule == "hyp":
            out.append(("hyp", s["premise_id"]))
        elif rule == "andI":
            out.append(("andI", s["left"], s["right"]))
        elif rule == "andE1":
            out.append(("andE1", s["from"]))
        elif rule == "andE2":
            out.append(("andE2", s["from"]))
        else:
            raise AssertionError(rule)
    return out


def _agree(v1j: v1.Judgment, lj: J) -> None:
    assert v1j.formula == lj.formula
    assert list(v1j.support) == list(lj.support)
    assert v1j.declared_authority == lj.declared
    assert v1j.math_established is False
    assert lj.math_established is False


def test_differential_hyp_andI_andE():
    Γ = Context(
        [
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(1, atom(1), Authority.hypothesis),
        ]
    )
    b = Builder(Γ)
    h0 = b.hyp(0)
    h1 = b.hyp(1)
    a = b.and_i(h0, h1)
    e1 = b.and_e1(a)
    e2 = b.and_e2(a)
    cert = b.finish(e2).to_json()
    steps = _steps_from_builder_cert(cert)

    for concl in (h0, h1, a, e1, e2):
        c = dict(cert)
        c["conclusion_step"] = concl
        v1j = v1.check(c)
        lj = lean_check_certificate(c["premises"], steps, concl)
        assert lj is not None
        _agree(v1j, lj)


def test_differential_reject_forged_andI():
    premises = [
        {"id": 0, "formula": ["atom", 0], "declared_authority": "empiricalAsserted"},
        {"id": 1, "formula": ["atom", 1], "declared_authority": "hypothesis"},
    ]
    # Lean-shaped steps that forge andI without building hyps first — invalid indices
    assert lean_check_steps(premises, [("andI", 0, 1)]) is None

    forged = {
        "schema_version": 1,
        "premises": premises,
        "steps": [
            {
                "id": 0,
                "rule": "andI",
                "left": 0,
                "right": 1,
                "formula": ["and", ["atom", 0], ["atom", 1]],
            }
        ],
        "conclusion_step": 0,
    }
    try:
        v1.check(forged)
        assert False, "forged andI must fail v1"
    except v1.CheckError:
        pass


def test_differential_reject_duplicate_premise_ids():
    premises = [
        {"id": 0, "formula": ["atom", 0], "declared_authority": "empiricalAsserted"},
        {"id": 0, "formula": ["atom", 1], "declared_authority": "hypothesis"},
    ]
    assert lean_check_certificate(premises, [("hyp", 0)], 0) is None
