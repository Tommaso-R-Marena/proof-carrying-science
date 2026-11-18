"""Mutation suite: valid generators + invalid mutants for schema v1."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "independent_checker"))
sys.path.insert(0, str(ROOT / "python"))

import check_certificate_v1 as v1
from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Authority, Context, Premise, atom, land


def _valid_cert() -> dict:
    Γ = Context(
        premises=(
            Premise(0, atom(0), Authority.empiricalAsserted),
            Premise(1, atom(1), Authority.mathVerified),
        )
    )
    b = Builder(Γ)
    a = b.hyp(0)
    c = b.hyp(1)
    d = b.and_i(a, c)
    return b.finish(d).to_json()


def test_valid_accepted():
    j = v1.check(_valid_cert())
    assert j.declared_authority == "empiricalAsserted"
    assert j.formula[0] == "and"


def _mutants():
    base = _valid_cert()
    ms = []
    # wrong conclusion step
    m = copy.deepcopy(base)
    m["conclusion_step"] = 99
    ms.append(("oob_conclusion", m))
    # swap andI citations to self-forward
    m = copy.deepcopy(base)
    m["steps"][2]["left"] = 2
    ms.append(("self_ref_andI", m))
    # unknown rule
    m = copy.deepcopy(base)
    m["steps"].append({"id": 3, "rule": "exFalso", "from": 0})
    m["conclusion_step"] = 3
    ms.append(("exfalso", m))
    # schema
    m = copy.deepcopy(base)
    m["schema_version"] = 0
    ms.append(("schema0", m))
    # claimed authority escalation on reconstructed step
    m = copy.deepcopy(base)
    m["steps"][2]["authority"] = "mathVerified"
    ms.append(("claim_escalate", m))
    # duplicate premise
    m = copy.deepcopy(base)
    m["premises"].append(m["premises"][0])
    ms.append(("dup_premise", m))
    return ms


def test_all_mutants_rejected():
    for name, m in _mutants():
        try:
            v1.check(m)
            assert False, f"mutant {name} accepted"
        except v1.CheckError:
            pass
