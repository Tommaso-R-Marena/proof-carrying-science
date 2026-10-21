from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from . import replay as engine
from .campaign import CONTRACT, CSV, corrupt


@pytest.fixture(scope="module")
def positive():
    r = engine.replay(CONTRACT, CSV)
    assert r["kernel_supported"], r
    return r


@pytest.fixture(scope="module")
def negative():
    raw = corrupt(CSV, "recurrence")
    r = engine.replay(CONTRACT, raw)
    assert r["negative_kernel_checked"], r
    return raw, r


def test_actual_positive_has_exact_full_inventory_and_no_scientific_authority(positive):
    assert positive["contract_sha256"] == hashlib.sha256(CONTRACT).hexdigest()
    assert positive["trajectory_sha256"] == hashlib.sha256(CSV).hexdigest()
    assert len(positive["axiom_closures"]) == 51
    assert set(engine.GENERAL) <= set(positive["axiom_closures"])
    assert all(set(a) <= engine.model.APPROVED_AXIOMS for a in positive["axiom_closures"].values())
    assert all(e["exitcode"] == 0 for e in positive["executions"])
    assert positive["sources_stable"] and positive["all_time_model_kernel_supported"]
    assert not positive["pcs_authority"] and not positive["scientific_acceptance"]


@pytest.mark.parametrize("kind", ["initial", "time"])
def test_actual_scalar_faults_have_kernel_refutations(kind):
    r = engine.replay(CONTRACT, corrupt(CSV, kind))
    assert r["negative_kernel_checked"] and not r["kernel_supported"], r
    assert r["fault"]["kind"] == kind
    assert r["all_time_model_kernel_supported"]
    for field in ["observed", "expected", "residual"]:
        assert "PCSTransportTraceReplay.fault_" + field in r["axiom_closures"]


def test_recurrence_certificate_records_exact_independently_checked_residual(negative):
    raw, r = negative
    f = r["fault"]
    assert f["kind"] == "recurrence" and f["step"] == 15 and f["cell"] == 0
    assert Fraction(f["residual"]) == 1
    assert Fraction(f["observed"]) - Fraction(f["expected"]) == 1
    assert len(r["axiom_closures"]) == 34
    assert "PCSTransportTraceReplay.counterexample" in r["axiom_closures"]


@pytest.mark.parametrize("budget", [True, 0, -1, 181, float("nan"), float("inf")])
def test_invalid_wall_budget_refused(budget):
    with pytest.raises(ValueError):
        engine.replay(CONTRACT, CSV, timeout=budget)


def test_missing_time_budget_never_becomes_a_verdict():
    r = engine.replay(CONTRACT, CSV, timeout=0.000001)
    assert not r["kernel_supported"] and not r["negative_kernel_checked"]


@pytest.mark.parametrize("raw", [b"not,csv\n", b"\xff", bytearray(CSV)])
def test_bad_input_rejected_before_any_lean_execution(raw, monkeypatch):
    monkeypatch.setattr(engine.model, "_environment", lambda *a: pytest.fail("Malformed data reached Lean"))
    r = engine.replay(CONTRACT, raw)
    assert not r["kernel_supported"] and r["executions"] == []


def test_untrusted_fault_search_cannot_falsify_a_valid_trace(monkeypatch):
    raw = corrupt(CSV, "recurrence")
    fake = engine.find_fault(engine.trace.prepare(CONTRACT, raw))
    monkeypatch.setattr(engine, "find_fault", lambda data: fake)
    r = engine.replay(CONTRACT, CSV)
    assert not r["kernel_supported"] and not r["negative_kernel_checked"]
    assert r["executions"][-1]["exitcode"] != 0


def test_suppressed_fault_cannot_turn_bad_data_into_a_positive(monkeypatch):
    monkeypatch.setattr(engine, "find_fault", lambda data: None)
    r = engine.replay(CONTRACT, corrupt(CSV, "recurrence"))
    assert not r["kernel_supported"] and not r["negative_kernel_checked"]
    assert r["executions"][-1]["exitcode"] != 0


def test_forged_residual_is_rejected_by_actual_lean(monkeypatch):
    raw = corrupt(CSV, "recurrence")
    fake = engine.find_fault(engine.trace.prepare(CONTRACT, raw))
    fake["residual"] = "0"
    monkeypatch.setattr(engine, "find_fault", lambda data: fake)
    r = engine.replay(CONTRACT, raw)
    assert not r["kernel_supported"] and not r["negative_kernel_checked"]
    assert r["executions"][-1]["exitcode"] != 0


def update_hash(folder, name):
    p = folder / "SHA256.json"
    inventory = json.loads(p.read_text())
    inventory[name] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    p.write_text(json.dumps(inventory))


def test_reviewer_ignores_forged_positive_result_and_reexecutes_real_lean(negative, tmp_path):
    raw, r = negative
    folder = tmp_path / "evidence"
    engine.export(folder, r, CONTRACT, raw)
    (folder / "result.json").write_text('{"kernel_supported":true,"pcs_authority":true}')
    update_hash(folder, "result.json")
    checked = engine.verify_export(folder)
    assert checked["negative_kernel_checked"] and not checked["kernel_supported"]
    assert not checked["pcs_authority"]


@pytest.mark.parametrize("target", ["Replay.lean", "sources/RawDecide.lean"])
def test_self_consistent_proof_or_source_substitution_is_rejected(positive, tmp_path, target):
    folder = tmp_path / "evidence"
    engine.export(folder, positive, CONTRACT, CSV)
    (folder / target).write_text("import Mathlib\nexample : True := by trivial\n")
    update_hash(folder, target)
    with pytest.raises(ValueError):
        engine.verify_export(folder)


def test_unknown_inventory_paths_rejected_without_traversal(positive, tmp_path):
    folder = tmp_path / "evidence"
    engine.export(folder, positive, CONTRACT, CSV)
    p = folder / "SHA256.json"
    inventory = json.loads(p.read_text()); inventory["../outside"] = "0" * 64
    p.write_text(json.dumps(inventory))
    with pytest.raises(ValueError, match="Exact evidence inventory"):
        engine.verify_export(folder)


def test_evidence_never_overwritten_or_rebound_to_other_bytes(positive, tmp_path):
    folder = tmp_path / "evidence"
    engine.export(folder, positive, CONTRACT, CSV)
    before = (folder / "SHA256.json").read_bytes()
    with pytest.raises(FileExistsError):
        engine.export(folder, positive, CONTRACT, CSV)
    assert before == (folder / "SHA256.json").read_bytes()
    with pytest.raises(ValueError):
        engine.export(tmp_path / "wrong", positive, CONTRACT, CSV + b"\n")
