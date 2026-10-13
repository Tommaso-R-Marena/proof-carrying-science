"""Source mutations must fail before cached proofs can be offered as evidence."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checked_runtime_gate", ROOT / "scripts/verify_runtime_checked_boundary.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def source_file(tmp_path, wrapper):
    current = tmp_path / "lib.rs"
    current.write_bytes(b"\n" * (gate.START - 1) + wrapper)
    return current


def test_exact_current_window_accepted(tmp_path):
    current = source_file(tmp_path, gate.SNAPSHOT.read_bytes())
    assert gate.check_current_source(current) == gate.digest(gate.SNAPSHOT)


@pytest.mark.parametrize("old,new", [
    (b"*bits !=", b"*bits =="),
    (b"width.mask()", b"0"),
    (b"store.values()", b"store.keys()"),
    (b"eval_expr(store, expr)", b"eval_expr(store, &Expr::ConstBool { value: true })"),
    (b"noncanonical bitvector input", b"accepted bitvector input"),
    (b"return Err", b"return Ok"),
    (b"if let Value::BitVec", b"if let Value::Bool"),
])
def test_mutated_boundary_rejected(tmp_path, old, new):
    original = gate.SNAPSHOT.read_bytes()
    assert old in original
    with pytest.raises(ValueError, match="source window changed"):
        gate.check_current_source(source_file(tmp_path, original.replace(old, new)))


def test_truncated_source_is_rejected(tmp_path):
    current = tmp_path / "lib.rs"
    current.write_text("pub fn eval_expr_checked() {}\n")
    with pytest.raises(ValueError, match="outside file"):
        gate.check_current_source(current)
