"""Scheduling boundaries and real retained-model/effect diagnostics."""
from copy import deepcopy
import hashlib
import json
import sys

import pytest

from . import routing


def _inputs():
    artifact = {"id": "data", "sha256": hashlib.sha256(b"x\n1\n").hexdigest(),
                "size": 4, "status": "EXTRACTED", "path": "data.csv"}

    def obligation(identity, checker, category="verification"):
        return {"id": identity, "checker": checker, "category": category,
                "artifact_ids": [artifact["id"]],
                "source_bindings": [{k: artifact[k] for k in ("sha256", "size")} | {"artifact_id": artifact["id"]}],
                "source": {"artifact_id": artifact["id"], "sha256": artifact["sha256"], "locator": {"line": 1}},
                "payload": {"artifact_id": artifact["id"]}, "authority": True}

    obligations = [obligation("formal", "lean_closed"), obligation("numeric", "csv_numeric"),
                   obligation("rows", "csv_rows"), obligation("meaning", "meaning_review", "meaning"),
                   obligation("unsupported", "future_neural_science")]
    return obligations, [artifact]


def test_supported_cheap_checks_precede_lean_and_meaning_stays_open():
    obligations, artifacts = _inputs()
    original = deepcopy((obligations, artifacts))
    result = routing.plan(obligations, artifacts)
    assert [r["checker"] for r in result["steps"]] == ["csv_rows", "csv_numeric", "lean_closed"]
    assert {r["obligation_id"]: r["status"] for r in result["deferred"]} == {
        "meaning": "NEEDS_REVIEW", "unsupported": "NEEDS_REVIEW"}
    assert result["checks_executed"] == 0
    assert result["authority"] is False and result["scientific_acceptance"] is False
    assert all(r["authority"] is False for r in result["steps"] + result["deferred"])
    assert original == (obligations, artifacts)
    assert routing.plan(list(reversed(obligations)), list(reversed(artifacts))) == result
    json.dumps(result, allow_nan=False)


def test_budget_defers_verification_without_erasing_review_obligations():
    obligations, artifacts = _inputs()
    result = routing.plan(obligations, artifacts, budget=3)
    assert [r["obligation_id"] for r in result["steps"]] == ["rows", "numeric"]
    deferred = {r["obligation_id"]: r["status"] for r in result["deferred"]}
    assert deferred == {"formal": "DEFERRED_BUDGET", "meaning": "NEEDS_REVIEW", "unsupported": "NEEDS_REVIEW"}
    assert result["remaining_budget"] == 0
    zero = routing.plan(obligations, artifacts, budget=0)
    assert zero["steps"] == []
    assert len(zero["deferred"]) == len(obligations)


def test_learned_scientific_mode_falls_back_without_loading_neural_models(monkeypatch):
    obligations, artifacts = _inputs()
    monkeypatch.setitem(sys.modules, "research.proof_jepa_rl_v1.model", None)
    monkeypatch.setitem(sys.modules, "research.safety_jepa_v1.model", None)
    learned = routing.plan(obligations, artifacts, mode="learned")
    baseline = routing.plan(obligations, artifacts)
    assert learned["effective_mode"] == "deterministic"
    assert learned["requested_mode"] == "learned"
    assert "incompatible" in learned["fallback_reason"]
    assert learned["steps"] == baseline["steps"]
    assert learned["deferred"] == baseline["deferred"]


def test_ols_requires_bound_fit_artifact_and_costs_three_units():
    obligations, artifacts = _inputs()
    obligation = deepcopy(obligations[2])
    obligation.update(id="fit", checker="ols_optimality")
    fit = {"id": "fit-json", "sha256": hashlib.sha256(b"{}").hexdigest(),
           "size": 2, "status": "EXTRACTED", "path": "ols_experiment.json"}
    artifacts.append(fit)
    obligation["payload"]["fit_artifact_id"] = fit["id"]
    unbound = routing.plan([obligation], artifacts)
    assert unbound["steps"] == []
    assert unbound["deferred"][0]["status"] == "NEEDS_REVIEW"
    obligation["artifact_ids"].append(fit["id"])
    obligation["source_bindings"].append({"artifact_id": fit["id"], "sha256": fit["sha256"], "size": fit["size"]})
    result = routing.plan([obligation], artifacts, budget=3)
    assert result["steps"][0]["checker"] == "ols_optimality"
    assert result["estimated_cost"] == 3
    assert result["deferred"] == []
    assert routing.plan([obligation], artifacts, budget=2)["deferred"][0]["status"] == "DEFERRED_BUDGET"


@pytest.mark.parametrize("change", [
    lambda o, a: a[0].update(sha256="0" * 64),
    lambda o, a: a[0].update(size=5),
    lambda o, a: a[0].update(status="ERROR"),
    lambda o, a: o.update(source_bindings=[]),
    lambda o, a: o.update(artifact_ids=["absent"]),
    lambda o, a: o["payload"].update(artifact_id="unbound-target"),
    lambda o, a: o["payload"].update(artifact_id=[]),
    lambda o, a: o["source"].update(sha256="0" * 64),
    lambda o, a: o["source"].update(artifact_id=[]),
])
def test_stale_missing_or_unbound_sources_require_review(change):
    obligations, artifacts = _inputs()
    obligation = obligations[2]
    change(obligation, artifacts)
    result = routing.plan([obligation], artifacts)
    assert result["steps"] == []
    assert result["deferred"][0]["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("budget", [-1, float("nan"), float("inf"), True, 1_000_001])
def test_invalid_budget_is_rejected(budget):
    obligations, artifacts = _inputs()
    with pytest.raises(ValueError, match="budget"):
        routing.plan(obligations, artifacts, budget=budget)


def test_duplicate_identity_and_unbounded_inputs_are_rejected():
    obligations, artifacts = _inputs()
    with pytest.raises(ValueError, match="duplicate obligation"):
        routing.plan(obligations + [obligations[0]], artifacts)
    with pytest.raises(ValueError, match="duplicate artifact"):
        routing.plan(obligations, artifacts * 2)
    with pytest.raises(ValueError, match="bounded obligation"):
        routing.plan(obligations * routing.MAX_OBLIGATIONS, artifacts)
    with pytest.raises(ValueError, match="mode"):
        routing.plan(obligations, artifacts, mode="invented")


def test_graph_generated_obligations_have_compatible_bindings():
    from .adapters import extract
    from .knowledge import build_graph

    records = []
    for identity, name, raw in [("notes", "notes.md", b"PCS-CLAIM: mean(data.csv,x) = 1\n"),
                                 ("data", "data.csv", b"x\n1\n")]:
        records.append({"id": identity, "path": name, "sha256": hashlib.sha256(raw).hexdigest(),
                        "size": len(raw), **extract(name, raw)})
    graph = build_graph(records)
    result = routing.plan(graph["obligations"], graph["artifacts"], mode="learned")
    assert {r["checker"] for r in result["steps"]} == {"csv_rows", "csv_numeric"}
    assert all(r["checker"] == "meaning_review" for r in result["deferred"])


def test_retained_models_run_frozen_on_actual_stored_states():
    torch = pytest.importorskip("torch")
    rng_before = torch.get_rng_state().clone()
    threads_before = torch.get_num_threads()
    report = routing.frozen_diagnostics(samples=2)
    assert torch.equal(torch.get_rng_state(), rng_before)
    assert torch.get_num_threads() == threads_before
    assert report["training_performed"] is False
    assert report["scientific_routing_compatible"] is False
    assert report["scientific_gain_evaluated"] is False
    assert report["authority"] is False
    for kind, model in report["models"].items():
        assert model["checkpoint_sha256"] == routing._PINS[kind]["checkpoint_sha256"]
        assert model["tensor_sha256_before"] == model["tensor_sha256_after"]
        assert model["parameters_frozen"] and model["updates"] == 0
        assert model["inference_cpu_seconds"] > 0
        assert len(model["rows"]) == 2
        assert all(r["options_count"] > 1 and r["recorded_action_outcome"] for r in model["rows"])
    assert len(json.dumps(report, allow_nan=False).encode()) < routing.MAX_DIAGNOSTIC_BYTES


def test_actual_retained_tool_effect_replay_includes_guarded_and_unguarded_outcomes():
    report = routing.replay_diagnostics(samples=2)
    rows = report["safety"]["rows"]
    assert all(row["matched"] for row in rows)
    assert rows[0]["guarded"] and rows[0]["actual_outcome"]["success"]
    assert rows[0]["actual_outcome"]["unsafe_executions"] == 0
    assert not rows[1]["guarded"] and rows[1]["actual_outcome"]["unsafe_executions"] > 0
    assert report["proof"]["status"] == "NOT_REQUESTED"
    assert report["scientific_gain_evaluated"] is False
    assert report["authority"] is False


@pytest.mark.parametrize("samples", [0, 17, True, 1.5])
def test_diagnostic_sample_bounds(samples):
    with pytest.raises(ValueError, match="samples"):
        routing.frozen_diagnostics(samples=samples)
    with pytest.raises(ValueError, match="samples"):
        routing.replay_diagnostics(samples=samples)


def test_retained_input_digest_is_required_before_json_decode(tmp_path):
    artifact = tmp_path / "records.json"
    artifact.write_bytes(b'{"status":"forged"}')
    with pytest.raises(ValueError, match="digest"):
        routing._pinned_read(artifact, "0" * 64)
