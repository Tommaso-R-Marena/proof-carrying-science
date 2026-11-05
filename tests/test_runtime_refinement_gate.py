"""The integration gate must reject changed extraction bytes and forged inventories."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runtime_refinement_gate", ROOT / "scripts/verify_runtime_refinement.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_certified_window_rejects_changed_body():
    with pytest.raises(ValueError, match="window changed"):
        gate.check_window(b"outside\nreturn a\n", b"outside\nreturn b\n", 2, 2)


def test_uncertified_checker_repair_does_not_change_interpreter_window():
    assert gate.check_window(b"return a\nold checker\n", b"return a\nrepaired checker\n", 1, 1)


@pytest.mark.parametrize("start,stop", [(0, 1), (2, 1), (1, 8)])
def test_invalid_window_is_not_an_empty_success(start, stop):
    with pytest.raises(ValueError, match="outside file"):
        gate.check_window(b"a\n", b"a\n", start, stop)


@pytest.mark.parametrize("output", ["", "'T' depends on axioms: [sorryAx]\n",
                                    "'T' does not depend on any axioms\n'T' does not depend on any axioms\n"])
def test_missing_admitted_or_duplicate_theorem_rejected(output):
    with pytest.raises(ValueError):
        gate.check_inventory(output, ["T"])


def test_multiline_standard_axioms_accepted():
    output = "'T' depends on axioms: [propext,\n Classical.choice,\n Quot.sound]\n"
    assert set(gate.check_inventory(output, ["T"])["T"]) == {"propext", "Classical.choice", "Quot.sound"}
