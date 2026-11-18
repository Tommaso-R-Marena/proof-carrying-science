"""Formula depth limits and JSON parse-edge coverage."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "independent_checker"))
sys.path.insert(0, str(ROOT / "python"))

import check_certificate_v1 as v1
from scientific_reasoning.certificates_v1 import Builder
from scientific_reasoning.syntax import Authority, Context, Premise, atom, lnot


def _deep_not(n: int):
    φ = ["atom", 0]
    for _ in range(n):
        φ = ["not", φ]
    return φ


def test_depth_at_limit_accepted():
    # Lean/Python max depth 64: depth counts nestings; atom depth 0, one not => 1
    φ = _deep_not(64)
    c = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": φ, "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    j = v1.check(c)
    assert j.math_established is False


def test_depth_over_limit_rejected():
    φ = _deep_not(65)
    c = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": φ, "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    try:
        v1.check(c)
        assert False
    except v1.CheckError as e:
        assert "depth" in str(e).lower()


def test_json_too_large_rejected():
    huge = "{" + ("\"a\":1," * 200000) + "\"b\":1}"
    # may hit duplicate or size — ensure CheckError
    try:
        v1.parse_certificate_json(huge)
        assert False
    except v1.CheckError:
        pass


def test_malformed_json_rejected():
    try:
        v1.parse_certificate_json("{not json")
        assert False
    except v1.CheckError:
        pass


def test_non_object_json_rejected():
    try:
        v1.parse_certificate_json("[1,2,3]")
        assert False
    except v1.CheckError:
        pass


def test_parse_then_check_valid(tmp_path: Path):
    Γ = Context([Premise(0, lnot(atom(0)), Authority.hypothesis)])
    b = Builder(Γ)
    b.hyp(0)
    text = b.finish().dumps()
    data = v1.parse_certificate_json(text)
    j = v1.check(data)
    assert j.formula[0] == "not"


def test_authority_alias_field_accepted():
    c = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": ["atom", 0], "authority": "derived"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    j = v1.check(c)
    assert j.declared_authority == "derived"


def test_deep_and_tree_under_limit():
    # balanced-ish and nesting via left spine
    φ = ["atom", 0]
    for i in range(1, 20):
        φ = ["and", φ, ["atom", i]]
    c = {
        "schema_version": 1,
        "premises": [{"id": 0, "formula": φ, "declared_authority": "hypothesis"}],
        "steps": [{"id": 0, "rule": "hyp", "premise_id": 0}],
        "conclusion_step": 0,
    }
    assert v1.check(c).formula == φ
