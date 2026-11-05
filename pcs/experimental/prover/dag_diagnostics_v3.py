"""Additional, explicitly post-evaluation Std/Mathlib diagnostics.

These runs never select/retrain/promote a checkpoint or become blind test data.
"""
import argparse
import json
from pathlib import Path
import time
from .dag_experiment_v3 import write
from .dag_policy_v3 import tensors
from .hybrid import std_search, replay_std_receipt
from .induction_ir import digest
from .memory_cost import MeasuredInductionEnvironment
from .mathlib_retrieval import MathlibRetriever, MATHLIB_REVISION
from .state_graph import encode_state, decode_state

MATHLIB_TASKS = [
    {"id": "preimage_intersection", "statement": "∀ (f : Nat → Nat) (s t : Set Nat), f ⁻¹' (s ∩ t) = (f ⁻¹' s) ∩ (f ⁻¹' t)"},
    {"id": "preimage_union", "statement": "∀ (f : Nat → Nat) (s t : Set Nat), f ⁻¹' (s ∪ t) = (f ⁻¹' s) ∪ (f ⁻¹' t)"},
    {"id": "group_inverse_product", "statement": "∀ (G : Type) [Group G] (a b : G), (a * b)⁻¹ = b⁻¹ * a⁻¹"},
    {"id": "group_right_cancellation", "statement": "∀ (G : Type) [Group G] (a b c : G), a * c = b * c → a = b"},
]


def run(folder):
    folder = Path(folder)
    path = folder / "diagnostic_protocol.json"
    if path.exists():
        raise ValueError("diagnostic protocol already exists")
    tasks = json.loads((folder / "tasks.json").read_text())
    write(path, {"format": "pcs-post-evaluation-diagnostics-v3", "tasks_sha256": digest(tasks), "mathlib_tasks": MATHLIB_TASKS,
                 "mathlib_revision": MATHLIB_REVISION, "mathlib_retrieval_limit": 3,
                 "status": "fixed before diagnostic execution, after frozen model evaluation; no training/selection use",
                 "limitations": ["Mathlib retrieval uses existing symbolic ranker, not the trained DAG policy", "whole-goal Std tactics are not action-budget-equivalent to primitive search", "author-known elementary tasks, not blind evaluation"]})
    started = time.monotonic(); results = []
    env = MeasuredInductionEnvironment(timeout=30)
    construction = {"calls": env.actual_calls, "wall_seconds": time.monotonic() - started}
    try:
        for task in tasks:
            result = std_search(env, task["goal"])
            tick = time.monotonic()
            replay = replay_std_receipt(task["goal"], result["receipt"]) if result["status"] == "verified" else None
            results.append({"id": task["id"], "result": result, "independent_replay": replay,
                            "replay_wall_seconds": time.monotonic() - tick})
            write(folder / "std-diagnostics.json", {"construction": construction, "results": results})
            print(json.dumps({"kind": "Std", "id": task["id"], "status": result["status"]}), flush=True)
    finally:
        env.close()
    tick = time.monotonic(); retriever = MathlibRetriever(timeout=30)
    mathlib_construction = {"calls": retriever.calls, "wall_seconds": time.monotonic() - tick, "catalog_sha256": retriever.catalog_sha256,
                            "catalog_entries": len(retriever.catalog), "imports": retriever.import_digests}
    external = []
    for task in MATHLIB_TASKS:
        state = retriever.state(task["statement"])
        graph = encode_state(state)
        if decode_state(graph) != state:
            raise RuntimeError("actual Mathlib DAG round trip failed")
        values, edges = tensors(state)
        result = retriever.solve(task["statement"], mode="structural", limit=3)
        external.append({"task": task, "dag_schema": {"lossless": True, "nodes": len(values), "edges": len(edges)}, "result": result})
        write(folder / "mathlib-diagnostics.json", {"construction": mathlib_construction, "results": external,
              "physical_lean_calls_including_catalog_and_state_probes": retriever.calls, "elapsed_lean_seconds": retriever.seconds})
        print(json.dumps({"kind": "Mathlib", "id": task["id"], "status": result["status"]}), flush=True)
    write(folder / "diagnostic-summary.json", {"std_solved": sum(r["result"]["status"] == "verified" for r in results), "std_tasks": len(results),
          "mathlib_solved": sum(r["result"]["status"] == "verified" for r in external), "mathlib_tasks": len(external),
          "std_physical_calls": env.actual_calls, "mathlib_physical_calls": retriever.calls,
          "wall_seconds": time.monotonic() - started, "model_training_performed": False, "model_promoted": False})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); args = parser.parse_args(); run(args.output)
