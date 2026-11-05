"""Unit controls for deterministic generation, safe shrinking, and real source-window identity."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from runtime_differential import conditional_cases, forge_cases, lean_expr, minimize, shrink_candidates
from verify_runtime_refinement import check_window


def test_generators_are_seeded_and_include_actual_error_cases():
    left = forge_cases(123, 20)
    assert left == forge_cases(123, 20)
    assert left != forge_cases(124, 20)
    assert {c["program"]["body"].get("op") for c in left} >= {"ult", "shl", "neg", "not"}
    assert all(0 <= v.get("bits", 0) < 2**64 for c in left for v in c["inputs"])
    assert conditional_cases(123, 20) == conditional_cases(123, 20)
    assert any(not c["task"]["variables"] for c in conditional_cases(123, 20))


def test_shrinking_retains_an_actual_disagreement_predicate_and_budget():
    # Predicate stands in for fresh evaluator disagreement. Successful shrink keeps it true.
    original = {"program": {"body": {"kind": "bin_op", "op": "add", "lhs": {"kind": "const_bv", "width": "u8", "value": 100},
                                      "rhs": {"kind": "const_bv", "width": "u8", "value": 200}}}, "inputs": [1,2,3]}
    def disagrees(c):
        return c["program"]["body"].get("kind") == "const_bv" and c["program"]["body"]["value"] > 0 or c["program"]["body"].get("kind") == "bin_op"
    result = minimize(original, disagrees, 64)
    assert disagrees(result["input"])
    assert len(json.dumps(result["input"])) < len(json.dumps(original))
    assert result["attempts"] <= 64
    assert original["inputs"] == [1,2,3]


def test_shrink_candidates_are_strictly_smaller_and_do_not_mutate_source():
    source = {"inputs": [99, 3]}; before = copy.deepcopy(source)
    assert all(len(json.dumps(c,sort_keys=True)) < len(json.dumps(source,sort_keys=True)) for c in shrink_candidates(source))
    assert source == before


def test_exact_value_type_window_rejects_tampering_but_preserves_unrelated_lines():
    snapshot=(ROOT / "formal/source_reference/certiforge/crates/certir-interpreter/src/lib.rs.txt").read_bytes()
    changed=snapshot.split(b"\n"); changed[22]=changed[22].replace(b"Ty::Bool",b"Ty::BitVec(width)")
    with pytest.raises(ValueError,match="source extraction window changed"):
        check_window(snapshot,b"\n".join(changed),21,26)
    changed=snapshot.split(b"\n"); changed[-1]=b"// unrelated trailing comment"
    assert check_window(snapshot,b"\n".join(changed),21,26)==check_window(snapshot,snapshot,21,26)


def test_lean_renderer_escapes_names_and_keeps_left_right_order():
    expr={"kind":"bin_op","op":"sub","lhs":{"kind":"var","name":"x"},"rhs":{"kind":"var","name":"y"}}
    assert lean_expr(expr)=='(.binop .sub (.var "x") (.var "y"))'
    with pytest.raises(ValueError):lean_expr({"kind":"run_shell"})
