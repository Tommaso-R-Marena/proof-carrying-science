"""Bounded proposal scheduling and retained-model diagnostics, with no authority.

Scientific obligations are a different schema from P1 Lean proof states and P2
synthetic tool observations. Their retained checkpoints therefore never rank
scientific checks. Optional diagnostics run those exact models on their original
stored states; they do not train, establish model origin, or measure science gain.
"""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import time

from pcs.jsonio import strict_json_loads

FORMAT = "pcs-scientific-check-plan-v1"
# Fixed scheduling work units, not learned or measured machine latency.
CHECK_COSTS = {"json_field": 1., "python_import": 1., "csv_rows": 1.,
               "sequence_length": 1., "coordinate_count": 2., "csv_numeric": 2.,
               "sequence_matches_structure": 3., "ols_optimality": 3., "lean_closed": 25.}
MAX_OBLIGATIONS = 4096
MAX_ARTIFACTS = 256
MAX_DIAGNOSTIC_BYTES = 256_000
_SHA = re.compile(r"[0-9a-f]{64}")
_RESEARCH = Path(__file__).resolve().parents[1]
_PINS = {
    "proof": {"directory": "proof_jepa_rl_v1", "checkpoint": "proof_guided-17.json",
              "checkpoint_sha256": "3a340553c2863cbd46cc306db2bc8cfb541cf30d467c3d63141c230756f7485d",
              "training_sha256": "25b962f9bad4ea26fb630cf90760766d933fef34294d43b634b1bb78ea4cbcf7"},
    "safety": {"directory": "safety_jepa_v1", "checkpoint": "jepa_rl-17.json",
               "checkpoint_sha256": "61611bd810b746c03695c1cee70e809b90d30d6735294c72cecae19d8974e07a",
               "training_sha256": "f72c098a30baf42d76453a5ee5f6cbbf6739f9f9f8885d4eca024501bc2f2e7f",
               "scenarios_sha256": "fa09a4bb21fe0982ee865df0ffaee8bfb11e84219a80148b97bc40cf82e69af4"},
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _artifacts(records):
    if isinstance(records, dict):
        records = records["artifacts"] if "artifacts" in records else list(records.values())
    if type(records) is not list or len(records) > MAX_ARTIFACTS:
        raise ValueError("bounded artifact list required")
    result = {}
    for record in records:
        if type(record) is not dict or type(record.get("id")) is not str or not record["id"]:
            raise ValueError("artifact identity required")
        if record["id"] in result:
            raise ValueError("duplicate artifact identity")
        result[record["id"]] = record
    return result


def _binding_problem(obligation, artifacts):
    bindings = obligation.get("source_bindings")
    artifact_ids = obligation.get("artifact_ids")
    if (type(bindings) is not list or not bindings or type(artifact_ids) is not list
            or any(type(a) is not str for a in artifact_ids)):
        return "Missing source bindings; review the obligation before checking."
    bound = set()
    for binding in bindings:
        if type(binding) is not dict or type(binding.get("artifact_id")) is not str:
            return "Malformed source binding."
        identity = binding["artifact_id"]
        if identity in bound:
            return "Duplicate source binding."
        bound.add(identity)
        artifact = artifacts.get(identity)
        if artifact is None:
            return "Bound artifact is unavailable."
        if (type(binding.get("sha256")) is not str or not _SHA.fullmatch(binding["sha256"])
                or type(binding.get("size")) is not int or binding["size"] < 0
                or artifact.get("sha256") != binding["sha256"]
                or type(artifact.get("size")) is not int or artifact["size"] != binding["size"]):
            return "Source-binding hash or size mismatch."
        if artifact.get("status") in ("ERROR", "UNSUPPORTED", "NEEDS_REVIEW"):
            return "Bound artifact extraction is unavailable or requires review."
    if bound != set(artifact_ids) or len(artifact_ids) != len(bound):
        return "Source bindings do not match the obligation artifact identities."
    payload = obligation.get("payload", {})
    if type(payload) is not dict:
        return "Malformed checker payload."
    for field in ("artifact_id", "structure_artifact_id", "fit_artifact_id"):
        if field in payload and (type(payload[field]) is not str or payload[field] not in bound):
            return "Checker target is outside the source bindings."
    source = obligation.get("source")
    if (type(source) is not dict or type(source.get("artifact_id")) is not str or source["artifact_id"] not in bound
            or source.get("sha256") != artifacts[source["artifact_id"]].get("sha256")):
        return "Source locator is not bound to the available artifact bytes."
    return None


def plan(obligations, artifacts, mode="deterministic", budget=100.):
    """Select supported cheap checks before Lean; leave meaning explicitly open.

    This is a schedule, never a check result. Metadata bindings are compared here;
    executing checkers must independently re-read and hash the snapshot bytes.
    Learned mode always falls back: neither retained model accepts this schema.
    """
    if type(mode) is not str or mode not in {"deterministic", "learned"}:
        raise ValueError("mode must be deterministic or learned")
    if type(budget) not in (int, float) or not math.isfinite(budget) or not 0 <= budget <= 1_000_000:
        raise ValueError("budget must be a finite nonnegative bounded number")
    if type(obligations) is not list or len(obligations) > MAX_OBLIGATIONS:
        raise ValueError("bounded obligation list required")
    inventory = _artifacts(artifacts)
    identities, candidates, deferred = set(), [], []
    for obligation in obligations:
        if (type(obligation) is not dict or type(obligation.get("id")) is not str
                or not obligation["id"] or len(obligation["id"]) > 256):
            raise ValueError("bounded obligation identity required")
        identity = obligation["id"]
        if identity in identities:
            raise ValueError("duplicate obligation identity")
        identities.add(identity)
        checker = obligation.get("checker")
        if type(checker) is not str or len(checker) > 128:
            raise ValueError("bounded checker name required")
        row = {"obligation_id": identity, "checker": checker, "authority": False}
        if checker == "meaning_review" or obligation.get("category") == "meaning":
            reason = "Scientific meaning and source interpretation require explicit review."
        elif checker not in CHECK_COSTS:
            reason = "No supported independent checker; the obligation requires review."
        else:
            reason = _binding_problem(obligation, inventory)
        if reason:
            deferred.append({**row, "status": "NEEDS_REVIEW", "reason": reason})
        else:
            candidates.append({**row, "estimated_cost": CHECK_COSTS[checker]})
    candidates.sort(key=lambda row: (row["checker"] == "lean_closed", row["estimated_cost"], row["checker"], row["obligation_id"]))
    steps, spent = [], 0.
    for row in candidates:
        if spent + row["estimated_cost"] <= budget:
            steps.append({**row, "status": "PLANNED", "reason": "Supported source-bound check within the fixed work-unit budget."})
            spent += row["estimated_cost"]
        else:
            deferred.append({**row, "status": "DEFERRED_BUDGET", "reason": "Insufficient remaining scheduling budget; no check was executed."})
    result = {"format": FORMAT, "requested_mode": mode, "effective_mode": "deterministic",
              "fallback_reason": ("Scientific obligation schema is incompatible with the retained P1 Lean-state and P2 tool-observation models; deterministic fallback was used." if mode == "learned" else None),
              "steps": steps, "deferred": sorted(deferred, key=lambda row: row["obligation_id"]),
              "budget": float(budget), "estimated_cost": spent, "remaining_budget": float(budget) - spent,
              "cost_unit": "fixed scheduling work units; not measured latency", "authority": False,
              "checks_executed": 0, "scientific_acceptance": False}
    result["plan_sha256"] = _digest(result)
    return result


def _pinned_read(path, expected, *, compressed=False):
    """Read finite retained JSON, checking compressed bytes before decoding."""
    with Path(path).open("rb") as stream:
        raw = stream.read(16_000_001)
    if len(raw) > 16_000_000 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("retained diagnostic artifact digest/size mismatch")
    if compressed:
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(16_000_001)
        if len(raw) > 16_000_000:
            raise ValueError("retained diagnostic decoded artifact exceeds bound")
    return strict_json_loads(raw.decode("utf-8"))


def _samples(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"samples must be an integer in 1..{maximum}")


def _bounded_report(report):
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(raw) > MAX_DIAGNOSTIC_BYTES:
        raise ValueError("diagnostic output exceeds byte bound")
    return report


def _tensor_digest(model):
    h = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(str(tuple(value.shape)).encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def frozen_diagnostics(*, samples=4):
    """Run frozen real P1/P2 checkpoints on bounded original stored states.

    Recorded labels describe only the stored action, not an unexecuted new top
    proposal. This is a retrospective training-state diagnostic with no gain
    claim, no updates, and no scientific-domain adapter or ranking.
    """
    _samples(samples, 16)
    import torch
    models, old_threads = {}, torch.get_num_threads()
    try:
        from pcs.experimental.prover.environment import candidates
        from research.proof_jepa_rl_v1.model import ProofJEPA
        from research.safety_jepa_v1.model import ACTIONS, SafetyJEPA

        torch.set_num_threads(1)
        for kind, model_class in (("proof", ProofJEPA), ("safety", SafetyJEPA)):
            pin = _PINS[kind]
            root = _RESEARCH / pin["directory"] / "evidence"
            data = _pinned_read(root / "training.json.gz", pin["training_sha256"], compressed=True)
            if data.get("authority") != "NONE":
                raise ValueError("retained records must carry no authority")
            with torch.random.fork_rng(devices=[]):
                model = model_class.load(root / pin["checkpoint"], pin["checkpoint_sha256"])
            model.eval().requires_grad_(False)
            before = _tensor_digest(model)
            rows, inference_cpu = [], 0.
            for index, record in enumerate(data["transitions"][:samples]):
                if kind == "proof":
                    state, recorded_action = record["state"], record["action"]
                    options = candidates(state)[:31]
                    if recorded_action not in options:
                        options.append(deepcopy(recorded_action))
                    outcome = {"valid": record["valid"], "kernel_completed": record["kernel_completed"]}
                else:
                    state, recorded_action, options = record["obs"], record["action"], list(ACTIONS)
                    outcome = {field: record[field] for field in ("unsafe", "blocked", "completion")}
                started = time.process_time()
                with torch.inference_mode():
                    scores = model.rank(state, options)
                elapsed = time.process_time() - started
                inference_cpu += elapsed
                if not scores or len(scores) != len(options) or any(not math.isfinite(s) for s in scores):
                    raise ValueError("invalid retained-model diagnostic scores")
                best = max(range(len(scores)), key=lambda i: (scores[i], -i))
                rows.append({"stored_transition_index": index, "state_sha256": _digest(state),
                             "options_sha256": _digest(options), "options_count": len(options),
                             "top_action": options[best], "top_score": scores[best],
                             "recorded_action": recorded_action, "recorded_action_score": scores[options.index(recorded_action)],
                             "recorded_action_outcome": outcome,
                             "top_action_matches_recorded": options[best] == recorded_action,
                             "inference_cpu_seconds": elapsed})
            after = _tensor_digest(model)
            if before != after:
                raise ValueError("frozen diagnostic changed model tensors")
            # Catch checkpoint mutation as well as tensor mutation during inference.
            _pinned_read(root / pin["checkpoint"], pin["checkpoint_sha256"])
            models[kind] = {"checkpoint": pin["directory"] + "/evidence/" + pin["checkpoint"],
                            "checkpoint_sha256": pin["checkpoint_sha256"], "stored_data_sha256": pin["training_sha256"],
                            "tensor_sha256_before": before, "tensor_sha256_after": after,
                            "parameters_frozen": True, "updates": 0, "device": "cpu",
                            "inference_cpu_seconds": inference_cpu, "rows": rows}
    finally:
        torch.set_num_threads(old_threads)
    return _bounded_report({"format": "pcs-scientific-frozen-model-diagnostic-v1", "models": models,
        "samples_per_model": samples, "training_performed": False, "scientific_routing_compatible": False,
        "scientific_gain_evaluated": False, "generation_origin_attested": False, "authority": False,
        "scope": "Retrospective scores on original retained training observations; stored action labels are not fresh checks of the top proposal."})


def replay_diagnostics(*, samples=2, proof_cache=None):
    """Reexecute bounded retained P2 effects; optionally replay P1 Lean proofs.

    P2 effects use only the original synthetic confined tool environment. P1
    requires an explicitly supplied disposable cache and the pinned Lean host.
    No model is trained or used as a verifier, and no scientific gain is tested.
    """
    _samples(samples, 8)
    from research.safety_jepa_v1.replay import replay_trace

    pin = _PINS["safety"]
    root = _RESEARCH / pin["directory"] / "evidence"
    training = _pinned_read(root / "training.json.gz", pin["training_sha256"], compressed=True)
    scenarios = _pinned_read(root / "scenarios.json", pin["scenarios_sha256"])
    records = {record["id"]: record for record in scenarios}
    rows = []
    for index, trace in enumerate(training["traces"][:samples]):
        started = time.process_time()
        actual = replay_trace(records[trace["scenario_id"]], trace["rows"], trace["guarded"])
        if actual["success"] != trace["success"] or actual["unsafe_executions"] != trace["unsafe_executions"]:
            raise ValueError("retained diagnostic episode outcome mismatch")
        rows.append({"stored_trace_index": index, "trace_sha256": _digest(trace),
                     "guarded": trace["guarded"], "matched": True, "actual_outcome": actual,
                     "replay_cpu_seconds": time.process_time() - started})
    proof = {"status": "NOT_REQUESTED", "reason": "Supply proof_cache for fresh original-goal Lean replay."}
    if proof_cache is not None:
        from research.proof_jepa_rl_v1.data import replay_receipt
        from research.proof_jepa_rl_v1.experiment import LeanEnvironment
        pin = _PINS["proof"]
        root = _RESEARCH / pin["directory"] / "evidence"
        data = _pinned_read(root / "training.json.gz", pin["training_sha256"], compressed=True)
        env = LeanEnvironment(cache=proof_cache, timeout=30)
        proofs = []
        try:
            accepted = [r for r in data["episodes"] if r["result"].get("receipt") is not None][:samples]
            for episode in accepted:
                fresh = replay_receipt(env, episode, episode["result"]["receipt"], data["verifier"])
                proofs.append({"task_id": episode["id"], "goal_sha256": fresh["goal_sha256"],
                               "receipt_sha256": _digest(fresh), "status": "KERNEL_REPLAYED"})
            proof = {"status": "REPLAYED", "proofs": proofs, "physical_attempts": env.actual_calls}
        finally:
            env.close()
    return _bounded_report({"format": "pcs-scientific-retained-replay-diagnostic-v1", "safety": {
        "stored_data_sha256": _PINS["safety"]["training_sha256"],
        "scenarios_sha256": _PINS["safety"]["scenarios_sha256"], "rows": rows}, "proof": proof,
        "authority": False, "training_performed": False, "scientific_gain_evaluated": False,
        "generation_origin_attested": False,
        "scope": "Bounded original-domain replay of retained effects/proofs; no scientific acceptance or attestation of neural proposal origin."})
