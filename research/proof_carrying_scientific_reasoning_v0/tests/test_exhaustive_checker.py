"""Exhaustive / property-style tests for schema-v1 checker + meet + JSON surface.

Closes remaining test coverage gaps called out in EQUIVALENCE_BREAKS.
"""
from __future__ import annotations

import copy
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "independent_checker"))
sys.path.insert(0, str(ROOT / "python"))

import check_certificate_v1 as v1
from scientific_reasoning.authority import meet as auth_meet
from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.meet_tables import RANK, TIE_ORDER, meet_str
from scientific_reasoning.syntax import Authority, Context, Premise, atom, land, lnot


AUTH = list(Authority)


def _base_ctx(n: int = 2) -> Context:
    return Context(tuple(Premise(i, atom(i), AUTH[i % len(AUTH)]) for i in range(n)))


def test_meet_tables_identity_with_enum_and_v1():
    for a, b in itertools.product(AUTH, repeat=2):
        assert meet_str(a.value, b.value) == auth_meet(a, b).value
        assert v1.meet(a.value, b.value) == meet_str(a.value, b.value)
    # Finding G lock
    assert meet_str("assumption", "empiricalAsserted") == "assumption"
    assert meet_str("empiricalAsserted", "assumption") == "assumption"


def test_all_single_hyp_authorities_accepted_math_false():
    for a in AUTH:
        Γ = Context([Premise(0, atom(0), a)])
        b = Builder(Γ)
        b.hyp(0)
        j = v1.check(b.finish().to_json())
        assert j.declared_authority == a.value
        assert j.math_established is False
        assert j.formula == ["atom", 0]
        assert j.support == [0]


def test_all_andI_authority_pairs_match_meet():
    for a, b in itertools.product(AUTH, repeat=2):
        Γ = Context(
            [Premise(0, atom(0), a), Premise(1, atom(1), b)]
        )
        bld = Builder(Γ)
        h0, h1 = bld.hyp(0), bld.hyp(1)
        bld.and_i(h0, h1)
        j = v1.check(bld.finish().to_json())
        assert j.declared_authority == meet_str(a.value, b.value)
        assert j.math_established is False
        assert j.formula == ["and", ["atom", 0], ["atom", 1]]


def test_andE_roundtrips_for_each_side():
    Γ = _base_ctx(2)
    b = Builder(Γ)
    h0, h1 = b.hyp(0), b.hyp(1)
    a = b.and_i(h0, h1)
    e1, e2 = b.and_e1(a), b.and_e2(a)
    cert = b.finish().to_json()
    j1 = v1.check({**cert, "conclusion_step": e1})
    j2 = v1.check({**cert, "conclusion_step": e2})
    assert j1.formula == ["atom", 0]
    assert j2.formula == ["atom", 1]


def test_json_duplicate_key_rejected():
    text = '{"schema_version":1,"schema_version":1,"premises":[],"steps":[],"conclusion_step":0}'
    try:
        v1.parse_certificate_json(text)
        assert False
    except v1.CheckError as e:
        assert "duplicate" in str(e).lower()


def test_json_bool_schema_rejected_via_parse_and_check():
    raw = {
        "schema_version": True,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    try:
        v1.check(raw)
        assert False
    except v1.CheckError:
        pass


def test_json_unknown_top_key_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["extra_field"] = 1
    try:
        v1.check(c)
        assert False
    except v1.CheckError as e:
        assert "unknown" in str(e).lower()


def test_json_unknown_step_key_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["steps"][0]["nonce"] = "x"
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_claimed_formula_mismatch_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["steps"][0]["formula"] = ["atom", 99]
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_claimed_support_bool_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["steps"][0]["support"] = [True]
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_top_level_conclusion_mismatch_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["conclusion"] = ["atom", 7]
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_final_authority_mismatch_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["final_authority"] = "mathVerified"
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_empty_steps_rejected():
    c = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}],
        "steps": [],
        "conclusion_step": 0,
    }
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_oob_conclusion_rejected():
    b = Builder(_base_ctx(1))
    b.hyp(0)
    c = b.finish().to_json()
    c["conclusion_step"] = 99
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_forward_ref_and_self_ref_rejected():
    for left, right in [(0, 0), (1, 0), (0, 1)]:
        bad = {
            "schema_version": 1,
            "premises": [
                {"id": 0, "formula": ["atom", 0], "declared_authority": "hypothesis"}
            ],
            "steps": [{"id": 0, "rule": "andI", "left": left, "right": right}],
            "conclusion_step": 0,
        }
        try:
            v1.check(bad)
            assert False, (left, right)
        except v1.CheckError:
            pass


def test_andE_on_not_rejected():
    Γ = Context([Premise(0, lnot(atom(0)), Authority.hypothesis)])
    b = Builder(Γ)
    h = b.hyp(0)
    # manually craft andE1 from not
    c = b.finish().to_json()
    c["steps"].append({"id": 1, "rule": "andE1", "from": h})
    c["conclusion_step"] = 1
    try:
        v1.check(c)
        assert False
    except v1.CheckError:
        pass


def test_nested_and_chain_length_8():
    n = 8
    Γ = Context(tuple(Premise(i, atom(i), Authority.empiricalAsserted) for i in range(n)))
    b = Builder(Γ)
    ids = [b.hyp(i) for i in range(n)]
    cur = ids[0]
    for i in range(1, n):
        cur = b.and_i(cur, ids[i])
    j = v1.check(b.finish().to_json())
    assert j.support == list(range(n))
    assert j.math_established is False


def test_parse_path_roundtrip_tmp(tmp_path: Path):
    b = Builder(_base_ctx(2))
    h0, h1 = b.hyp(0), b.hyp(1)
    b.and_i(h0, h1)
    p = tmp_path / "c.json"
    p.write_text(b.finish().dumps(), encoding="utf-8")
    j = v1.check_path(str(p))
    assert j.formula[0] == "and"


def test_mutation_battery_all_rejected():
    b = Builder(_base_ctx(2))
    h0, h1 = b.hyp(0), b.hyp(1)
    a = b.and_i(h0, h1)
    base = b.finish(a).to_json()
    mutants = []
    m = copy.deepcopy(base)
    m["schema_version"] = 2
    mutants.append(m)
    m = copy.deepcopy(base)
    m["steps"][2]["left"] = 2
    mutants.append(m)
    m = copy.deepcopy(base)
    m["steps"][2]["authority"] = "mathVerified"
    mutants.append(m)
    m = copy.deepcopy(base)
    m["steps"][2]["math_established"] = True
    mutants.append(m)
    m = copy.deepcopy(base)
    m["premises"].append(copy.deepcopy(m["premises"][0]))
    mutants.append(m)
    m = copy.deepcopy(base)
    m["steps"][0]["id"] = 9
    mutants.append(m)
    m = copy.deepcopy(base)
    m["steps"].append({"id": 3, "rule": "exFalso", "from": 0})
    m["conclusion_step"] = 3
    mutants.append(m)
    for i, m in enumerate(mutants):
        try:
            v1.check(m)
            assert False, f"mutant {i} accepted"
        except v1.CheckError:
            pass


def test_rank_tie_tables_complete():
    assert set(RANK) == set(TIE_ORDER) == {a.value for a in AUTH}
    # unique tie values
    assert len(set(TIE_ORDER.values())) == len(TIE_ORDER)
