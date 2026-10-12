"""Prospective untouched-generation comparison of existing frozen checkpoints.

No fitting or selection is performed here. The old untrained, BC, bag and two
sequential-RL checkpoints compete under the same action budget. This measures
transfer of historical training, not a new RL run or claimed improvement.
"""
import argparse
import json
from pathlib import Path
import time

from .environment import ROOT, search
from .induction_ir import digest
from .memory_cli import load
from .memory_model import MemoryNetwork
from .memory_cost import MeasuredMemoryEnvironment
from .memory_environment import replay_memory_receipt

MODEL_IDS = ("untrained-17", "supervised-17", "bag-17", "rl1-17", "rl2-17")


def freeze(folder):
    folder = Path(folder)
    target = folder / "checkpoint-transfer-protocol.json"
    if target.exists():
        raise ValueError("checkpoint transfer protocol already frozen")
    tasks = json.loads((folder / "tasks.json").read_text())
    registry = json.loads((ROOT / "research/verified-memory-v1/registry.json").read_text())
    rows = [row for row in tasks if row["split"] == "final" and row["kind"] == "typed"]
    models = [entry for identity in MODEL_IDS for entry in registry["models"] if entry["id"] == identity]
    protocol = {"format": "pcs-checkpoint-transfer-v2", "frozen_before_variant_evaluation": True,
                "tasks_sha256": digest(rows), "models": models, "budget": 48, "beam": 4, "depth": 18,
                "library_sha256": registry["library_sha256"], "training": "none; historical frozen v1 checkpoints",
                "selection": "none; no default replacement", "new_RL_claim": False,
                "compute": "one fixed independently checked library per process; construction reported separately; proof-state cache cleared per theorem/policy"}
    target.write_text(json.dumps(protocol, indent=2) + "\n")


def execute(folder):
    folder = Path(folder)
    protocol = json.loads((folder / "checkpoint-transfer-protocol.json").read_text())
    tasks = [row for row in json.loads((folder / "tasks.json").read_text()) if row["split"] == "final" and row["kind"] == "typed"]
    if digest(tasks) != protocol["tasks_sha256"]:
        raise ValueError("changed frozen checkpoint-transfer tasks")
    registry, selected, library, _ = load(ROOT / "research/verified-memory-v1")
    if registry["library_sha256"] != protocol["library_sha256"]:
        raise ValueError("changed frozen checked memory")
    target = folder / "checkpoint-transfer"
    target.mkdir(exist_ok=True)
    env = MeasuredMemoryEnvironment(library, timeout=30)
    construction = {"physical_lean_calls": env.actual_calls, "wall_seconds": env.construction_seconds}
    start = time.monotonic()
    try:
        for entry in protocol["models"]:
            model = MemoryNetwork.load(ROOT / "research/verified-memory-v1" / entry["checkpoint"], entry["sha256"])
            for task in tasks:
                path = target / (entry["id"] + "-" + task["id"] + ".json")
                if path.exists():
                    continue
                env.observations.clear()
                before = env.actual_calls
                searched = search(env, task["goal"], model.rank, budget=48, beam=4, depth=18)
                replay = replay_memory_receipt(task["goal"], searched["receipt"]) if searched["receipt"] else None
                row = {"task": task, "checkpoint": entry, "result": searched, "independent_replay": replay,
                       "physical_search_lean_calls": env.actual_calls - before,
                       "independent_replay_calls": "not instrumented by legacy helper"}
                path.write_text(json.dumps(row, indent=2) + "\n")
                print(json.dumps({"model": entry["id"], "task": task["id"], "status": searched["status"]}), flush=True)
    finally:
        env.close()
    counts = {}
    for path in target.glob("*.json"):
        row = json.loads(path.read_text())
        count = counts.setdefault(row["checkpoint"]["id"], {"tasks": 0, "verified": 0, "physical_search_calls": 0})
        count["tasks"] += 1
        count["verified"] += row["result"]["status"] == "verified"
        count["physical_search_calls"] += row["physical_search_lean_calls"]
    (folder / "checkpoint-transfer-summary.json").write_text(json.dumps({"counts": counts,
          "construction": construction, "this_invocation_wall_seconds": time.monotonic() - start,
          "no_new_training": True, "no_promotion": True, "new_RL_claim": False}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "execute"])
    parser.add_argument("folder")
    args = parser.parse_args()
    (freeze if args.command == "freeze" else execute)(args.folder)
