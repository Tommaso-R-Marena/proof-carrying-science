"""Resource-amortized replay of frozen prospective tasks and frozen policies.

The library is independently reconstructed once per environment and cannot be
modified by policies. Every proof is rechecked in a fresh Lean compiler using
that exact source/olean-bound approved library module. Selected final successes
are additionally replayed with the conservative whole-library rebuilding helper.
No search action allocation or task definition changes from the original freeze.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from .environment import ROOT, search
from .hybrid import std_search, replay_std_receipt
from .induction_ir import digest, theorem
from .memory_cli import load
from .memory_cost import MeasuredMemoryEnvironment, MeasuredInductionEnvironment
from .memory_environment import structural_rank, replay_memory_receipt
from .memory_model import MemoryNetwork
from .evidence_storage import exists, read, logical_paths


def replay_cached(env, goal, receipt):
    if receipt.get("goal_sha256") != digest(goal) or receipt.get("statement") != theorem(goal):
        raise ValueError("immutable original theorem changed")
    before = env.actual_calls
    fresh = env.verify(goal, receipt["actions"])
    for field in ("proof", "primitive_catalog_sha256", "memory_source_sha256", "library_declarations",
                  "library_sha256", "adapter_sha256", "lean"):
        if fresh.get(field) != receipt.get(field):
            raise ValueError("receiver library/checker binding mismatch")
    return {"status": "verified", "kernel": fresh["kernel"], "physical_lean_calls": env.actual_calls - before,
            "library_reconstructed_for_replay": False,
            "independent_compiler": True, "goal_sha256": digest(goal)}


def _write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def evaluate(folder, *, variants=False):
    import torch
    torch.set_num_threads(1)
    folder = Path(folder)
    protocol = json.loads((folder / "protocol.json").read_text())
    tasks = json.loads((folder / "tasks.json").read_text())
    if digest(tasks) != protocol["tasks_sha256"]:
        raise ValueError("changed frozen prospective tasks")
    registry, selected, library, model = load(ROOT / "research/verified-memory-v1")
    cache = ROOT / ".lake/pcs-prover/pooled-hybrid-v2"
    cache.mkdir(parents=True, exist_ok=True)
    memory = MeasuredMemoryEnvironment(library, cache=cache / "memory", timeout=30)
    basic = MeasuredMemoryEnvironment(None, cache=cache / "basic", timeout=30)
    std = MeasuredInductionEnvironment(cache=cache / "std", timeout=30)
    loading = {label: {"physical_lean_calls": env.actual_calls,
                         "construction_wall_seconds": getattr(env, "construction_seconds", None)}
               for label, env in (("memory", memory), ("basic", basic), ("std", std))}
    _write(folder / ("variant-pooled-loading-cost.json" if variants else "pooled-loading-cost.json"), loading)
    output = folder / ("checkpoint-transfer" if variants else "results")
    output.mkdir(exist_ok=True)
    variant_protocol = json.loads((folder / "checkpoint-transfer-protocol.json").read_text()) if variants else None
    if variants:
        from .mathematical_evidence import validate_transfer_protocol
        validate_transfer_protocol(variant_protocol, tasks, library, protocol)
    entries = variant_protocol["models"] if variants else [selected]
    replays = []
    try:
        for entry in entries:
            active_model = MemoryNetwork.load(ROOT / "research/verified-memory-v1" / entry["checkpoint"], entry["sha256"]) if variants else model
            for task in tasks:
                if task["kind"] != "typed" or variants and task["split"] != "final":
                    continue
                modes = (entry["id"],) if variants else ("symbolic", "memory_structural", "memory_learned", "Std", "hybrid")
                for mode in modes:
                    path = output / ((entry["id"] + "-" + task["id"] if variants else task["id"] + "-" + mode) + ".json")
                    if exists(path):
                        continue
                    start = time.monotonic()
                    for env in (memory, basic):
                        env.observations.clear()
                    before = {id(env): env.actual_calls for env in (memory, basic, std)}
                    winner = None
                    replay = None
                    stages = []
                    if mode in {"Std", "hybrid"}:
                        result = std_search(std, task["goal"])
                        stages.append({"component": "ordinary_Std", "status": result["status"], "expansions": result["expansions"]})
                        if result["receipt"]:
                            replay = replay_std_receipt(task["goal"], result["receipt"], cache=cache / "std-replay")
                            winner = "ordinary_Std"
                    if mode == "hybrid" and result["status"] != "verified":
                        remaining = protocol["typed_action_budget"] - result["expansions"]
                        for label, rank, allocation in (("memory_structural", structural_rank, remaining // 2),
                                                       ("frozen_neural", active_model.rank, remaining - remaining // 2)):
                            result = search(memory, task["goal"], rank, budget=allocation, depth=18, beam=4)
                            stages.append({"component": label, "status": result["status"], "expansions": result["expansions"]})
                            if result["receipt"]:
                                replay = replay_cached(memory, task["goal"], result["receipt"])
                                winner = label
                                break
                        result["expansions"] = sum(stage["expansions"] for stage in stages)
                    elif mode not in {"Std", "hybrid"}:
                        env = basic if mode == "symbolic" else memory
                        rank = active_model.rank if variants or mode == "memory_learned" else structural_rank
                        result = search(env, task["goal"], rank, budget=protocol["typed_action_budget"], depth=18, beam=4)
                        if result["receipt"]:
                            replay = replay_cached(env, task["goal"], result["receipt"])
                            winner = "frozen_neural" if variants or mode == "memory_learned" else mode
                    result["independent_replay"] = replay
                    result["winning_component"] = winner
                    result["stages"] = stages
                    result["resource_accounting"] = "pooled immutable library; exact fresh compiler proof replay; separate admission/loading artifact"
                    result["cost"] = {"physical_search_and_cached_replay_calls": sum(env.actual_calls - before[id(env)] for env in (memory, basic, std)),
                                      "independent_std_replay_calls": replay["all_lean_calls"] if replay and "all_lean_calls" in replay else 0,
                                      "warm_search_and_replay_wall_seconds": time.monotonic() - start}
                    if variants:
                        row = {"task": task, "checkpoint": entry, "result": result, "independent_replay": replay}
                    else:
                        row = {"task": task, "mode": mode, "checkpoint_sha256": entry["sha256"] if mode in {"memory_learned", "hybrid"} else None, "result": result}
                    _write(path, row)
                    print(json.dumps({"task": task["id"], "mode": mode, "status": result["status"], "winner": winner}), flush=True)
                    if not variants and task["split"] == "final" and result["receipt"] and mode in {"symbolic", "memory_structural", "memory_learned", "hybrid"}:
                        replays.append(row)
    finally:
        for env in (memory, basic, std):
            env.close()
    summary = {}
    for path in logical_paths(output):
        row = read(path)
        mode = row["checkpoint"]["id"] if variants else row["mode"]
        key = row["task"]["split"] + ":" + mode
        count = summary.setdefault(key, {"tasks": 0, "verified": 0})
        count["tasks"] += 1
        count["verified"] += row["result"]["status"] == "verified"
    _write(folder / ("checkpoint-transfer-summary.json" if variants else "pooled-summary.json"), {"counts": summary,
           "new_training": False, "automatic_promotion": False, "library_loading": loading})
    if not variants:
        seen = set()
        chosen = []
        for row in replays:
            # Predeclared audit sampling: first final receipt per attributed
            # component; all other successes still get fresh compiler replay.
            key = row["result"].get("winning_component")
            if key in seen:
                continue
            seen.add(key)
            receipt = row["result"]["receipt"]
            if receipt["format"] == "pcs-std-baseline-proof-v1":
                continue
            fresh = replay_memory_receipt(row["task"]["goal"], receipt, cache=cache / "full-rebuild-replay")
            chosen.append({"task": row["task"]["id"], "component": key, "fresh_receipt_sha256": digest(fresh),
                           "full_library_reconstructed": True, "kernel": fresh["kernel"]})
        _write(folder / "selected-full-library-replays.json", {"verified": len(chosen), "replays": chosen})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--variants", action="store_true")
    args = parser.parse_args()
    evaluate(args.folder, variants=args.variants)
