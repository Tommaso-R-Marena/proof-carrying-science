"""Audit frozen mathematical experiment membership and exact raw evidence.

This does not grant proof authority. Successful rows must already contain a
fresh kernel audit; --replay reconstructs a deterministic sample's entire
approved library in another Lean environment. Missing rows remain incomplete.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .induction_ir import digest, theorem
from .evidence_storage import exists, read, logical_paths, raw_bytes

ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
TYPED_MODES = ("symbolic", "memory_structural", "memory_learned", "Std", "hybrid")
MATHLIB_MODES = ("lexical", "structural", "standard")


def validate_transfer_protocol(protocol, tasks, library, experiment_protocol):
    finals = [task for task in tasks if task["kind"] == "typed" and task["split"] == "final"]
    if (protocol.get("format") != "pcs-checkpoint-transfer-v2"
            or protocol.get("frozen_before_variant_evaluation") is not True
            or protocol.get("tasks_sha256") != digest(finals)
            or protocol.get("library_sha256") != digest(library)):
        raise ValueError("frozen transfer corpus/library binding mismatch")
    for key, source_key in (("budget", "typed_action_budget"), ("depth", "depth"), ("beam", "beam")):
        if protocol.get(key) != experiment_protocol.get(source_key):
            raise ValueError("frozen transfer resource setting mismatch")
    entries = protocol.get("models", [])
    if not entries or len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("empty or duplicate frozen checkpoints")
    return finals


def _checked(row, task):
    if row.get("task") != task:
        raise ValueError("result no longer matches frozen task")
    result = row["result"]
    if result["status"] not in {"verified", "unknown", "resource_exhausted"}:
        raise ValueError("unsupported experimental outcome")
    receipt = result.get("receipt")
    if result["status"] != "verified":
        if receipt is not None:
            raise ValueError("unresolved result carries successful proof")
        return
    if not isinstance(receipt, dict):
        raise ValueError("verified result lacks proof")
    if task["kind"] == "typed":
        if receipt.get("goal_sha256") != digest(task["goal"]) or receipt.get("statement") != theorem(task["goal"]):
            raise ValueError("changed immutable theorem")
        replay = result.get("independent_replay") or row.get("independent_replay")
        if not isinstance(replay, dict):
            raise ValueError("successful theorem lacks independent replay")
        independent_kernel = replay.get("kernel")
    else:
        if receipt.get("statement") != task["statement"]:
            raise ValueError("changed frozen Mathlib theorem")
        independent_kernel = receipt.get("independent_kernel")
    for kernel in (receipt.get("kernel"), independent_kernel):
        if not isinstance(kernel, dict) or not set(kernel.get("axioms", ["missing"])) <= ALLOWED_AXIOMS:
            raise ValueError("missing kernel evidence or unapproved axioms")


def audit(folder):
    folder = Path(folder)
    tasks = json.loads((folder / "tasks.json").read_text())
    protocol = json.loads((folder / "protocol.json").read_text())
    variants = json.loads((folder / "checkpoint-transfer-protocol.json").read_text())
    if digest(tasks) != protocol["tasks_sha256"]:
        raise ValueError("changed frozen corpus")
    finals = [task for task in tasks if task["kind"] == "typed" and task["split"] == "final"]
    if digest(finals) != variants["tasks_sha256"]:
        raise ValueError("changed frozen transfer split")
    missing, counts, rows, expected_paths = [], {}, [], set()
    for task in tasks:
        modes = TYPED_MODES if task["kind"] == "typed" else MATHLIB_MODES
        for mode in modes:
            path = folder / "results" / (task["id"] + "-" + mode + ".json")
            expected_paths.add(path)
            if not exists(path):
                missing.append(str(path.relative_to(folder)))
                continue
            row = read(path)
            if row.get("mode") != mode:
                raise ValueError("wrong result policy")
            _checked(row, task)
            key = task["kind"] + ":" + task["split"] + ":" + mode
            count = counts.setdefault(key, {"tasks": 0, "verified": 0, "unknown": 0, "resource_exhausted": 0})
            count["tasks"] += 1
            count[row["result"]["status"]] += 1
            rows.append({"path": str(path.relative_to(folder)), "task": task["id"], "split": task["split"],
                         "mode": mode, "status": row["result"]["status"], "cost": row["result"].get("cost", {}),
                         "expansions": row["result"].get("expansions"),
                         "winning_component": row["result"].get("winning_component"),
                         "sha256": hashlib.sha256(raw_bytes(path)).hexdigest()})
    for checkpoint in variants["models"]:
        for task in finals:
            path = folder / "checkpoint-transfer" / (checkpoint["id"] + "-" + task["id"] + ".json")
            expected_paths.add(path)
            if not exists(path):
                missing.append(str(path.relative_to(folder)))
                continue
            row = read(path)
            if row.get("checkpoint") != checkpoint:
                raise ValueError("changed frozen checkpoint")
            _checked(row, task)
            key = "transfer:final:" + checkpoint["id"]
            count = counts.setdefault(key, {"tasks": 0, "verified": 0, "unknown": 0, "resource_exhausted": 0})
            count["tasks"] += 1
            count[row["result"]["status"]] += 1
            rows.append({"path": str(path.relative_to(folder)), "task": task["id"], "split": "final",
                         "mode": checkpoint["id"], "status": row["result"]["status"],
                         "cost": row["result"].get("cost", {}), "expansions": row["result"].get("expansions"),
                         "sha256": hashlib.sha256(raw_bytes(path)).hexdigest()})
    actual_paths = set(logical_paths(folder / "results")) | set(logical_paths(folder / "checkpoint-transfer"))
    if actual_paths - expected_paths:
        raise ValueError("unexpected experimental result membership")
    return {"format": "pcs-mathematical-evidence-audit-v1", "complete": not missing,
            "expected_comparisons": len(expected_paths), "recorded_comparisons": len(rows),
            "missing": missing, "counts": counts, "records": rows,
            "tasks_sha256": digest(tasks), "final_transfer_sha256": digest(finals),
            "new_training": False, "model_promotion": False,
            "cost_boundary": "Cold legacy, pooled loading and warm search costs are distinct; no incomplete-run total is reconstructed."}


def replay_sample(folder):
    from .memory_environment import replay_memory_receipt
    from .environment import ROOT
    # Lean subprocesses use the nested formal workspace as their working
    # directory; a caller-relative cache must be resolved before invoking them.
    folder = Path(folder).resolve()
    checked = audit(folder)
    tasks = json.loads((folder / "tasks.json").read_text())
    seen, replays = set(), []
    # Order is frozen task order and then frozen policy order. Read ALL saved
    # rows, including those written before a process restart.
    for task in tasks:
        if task["kind"] != "typed" or task["split"] != "final":
            continue
        for mode in TYPED_MODES:
            path = folder / "results" / (task["id"] + "-" + mode + ".json")
            if not exists(path):
                continue
            row = read(path)
            result = row["result"]
            if result["status"] != "verified" or result["receipt"]["format"] == "pcs-std-baseline-proof-v1":
                continue
            component = result.get("winning_component") or mode
            if component in seen:
                continue
            seen.add(component)
            fresh = replay_memory_receipt(task["goal"], result["receipt"],
                                          cache=ROOT / ".lake/pcs-prover/resume-independent" / digest(str(folder)))
            replays.append({"task": task["id"], "mode": mode, "component": component,
                            "source_receipt_sha256": digest(result["receipt"]),
                            "fresh_receipt_sha256": digest(fresh), "kernel": fresh["kernel"],
                            "full_library_reconstructed": True, "independent_compiler": True})
    report = {"format": "pcs-mathematical-resume-independent-audit-v1", "replays": replays,
              "verified": len(replays), "complete_comparison_membership": checked["complete"],
              "scope": "first final non-Std success per attributed component, all rows including pre-resume",
              "legacy_replay_physical_calls": "not instrumented; no invented aggregate"}
    (folder / "resume-independent-replays.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    report = replay_sample(args.folder) if args.replay else audit(args.folder)
    output = Path(args.folder) / "evidence-audit.json"
    if not args.replay:
        output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in {"records", "replays"}}))
