"""Current source bytes, including return rejection and derived types, are mandatory."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runtime_output_gate_v3", ROOT / "scripts/verify_runtime_output_boundary_v3.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def current_file(tmp_path, window, altered=None):
    source, start, stop, filename = window
    snapshot = gate.SNAPSHOTS / filename
    current = tmp_path / Path(source).name
    current.write_bytes(b"\n" * (start - 1) + (snapshot.read_bytes() if altered is None else altered))
    return current, snapshot, start, stop


@pytest.mark.parametrize("window", gate.WINDOWS)
def test_all_exact_source_windows_accepted(tmp_path, window):
    current, snapshot, start, stop = current_file(tmp_path, window)
    assert gate.check_selected_window(current, start, stop, snapshot) == gate.sha(snapshot)


@pytest.mark.parametrize("old,new", [
    (b"!=", b"=="),
    (b"eval_expr_checked", b"eval_expr"),
    (b"program.ret_ty", b"program.params"),
    (b"?;", b";"),
    (b"return type mismatch", b"return type accepted"),
    (b"Ok(out)", b"Ok(Value::Bool(true))"),
])
def test_return_continuation_mutations_rejected(tmp_path, old, new):
    window = gate.WINDOWS[0]
    original = (gate.SNAPSHOTS / window[3]).read_bytes()
    assert old in original
    current, snapshot, start, stop = current_file(tmp_path, window, original.replace(old, new))
    with pytest.raises(ValueError, match="source window changed|outside file"):
        gate.check_selected_window(current, start, stop, snapshot)


@pytest.mark.parametrize("window", gate.WINDOWS[1:])
def test_changed_derived_equality_rejected(tmp_path, window):
    original = (gate.SNAPSHOTS / window[3]).read_bytes()
    changed = original.replace(b"PartialEq, Eq,", b"PartialOrd, Ord,")
    assert changed != original
    current, snapshot, start, stop = current_file(tmp_path, window, changed)
    with pytest.raises(ValueError, match="source window changed"):
        gate.check_selected_window(current, start, stop, snapshot)


@pytest.mark.parametrize("start,stop", [(0, 1), (3, 2), (1, 999)])
def test_invalid_window_bounds_rejected(tmp_path, start, stop):
    current = tmp_path / "lib.rs"
    current.write_text("enum Ty {}\n")
    with pytest.raises(ValueError, match="outside file"):
        gate.check_selected_window(current, start, stop, gate.SNAPSHOTS / "type-equality.rs.txt")
