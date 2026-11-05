"""Typed anti-unification with independently checked counterexample rejection.

Two true specialized cancellation statements generate a quantified cancellation
component. Two unrelated true arithmetic identities also generate a false claim;
that failure remains evidence. This does not claim original mathematics.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from .environment import ROOT, search
from .induction_ir import digest
from .induction_language import formalize
from .memory_discovery import anti_unify
from .memory_cost import MeasuredMemoryEnvironment
from .memory_environment import structural_rank, replay_memory_receipt
from .memory_falsify import falsify
from .evidence_storage import exists

PAIRS = [
    ("shared-offset-cancellation", "For all natural numbers a, b and c, if (a + (0 + c)) equals (b + (0 + c)) then a equals b.",
     "For all natural numbers a, b and c, if (a + (1 + c)) equals (b + (1 + c)) then a equals b."),
    ("invalid-identity-generalization", "For all natural numbers a, (a + 0) equals a.",
     "For all natural numbers a, (a * 1) equals a."),
]
TRANSFER = [
    "For all natural numbers a, b and c, if (a + (7 + c)) equals (b + (7 + c)) then (a + 1) equals (b + 1).",
    "For all natural numbers a, b and c, if (a + (9 + c)) equals (b + (9 + c)) then a equals b.",
]


def freeze(folder):
    folder = Path(folder)
    if folder.exists():
        raise ValueError("new abstraction generation required")
    rows = []
    for identity, left, right in PAIRS:
        goals = [formalize(statement)["candidates"][0]["ir"] for statement in (left, right)]
        rows.append({"id": identity, "source_statements": [left, right], "source_goals": goals,
                     "candidate": anti_unify(*goals), "source_license": "CC0-1.0"})
    transfers = [{"id": "transfer-" + str(i), "statement": statement,
                  "goal": formalize(statement)["candidates"][0]["ir"]} for i, statement in enumerate(TRANSFER)]
    protocol = {"format": "pcs-abstraction-repair-v2", "frozen_before_execution": True,
                "candidate_budget": 48, "transfer_budget": 48, "beam": 4,
                "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "inputs_sha256": digest([rows, transfers]), "novel_mathematics_claim": False,
                "scope": "new author-owned specialized sources; transfer public, not blind; false generalization must be rejected"}
    folder.mkdir(parents=True)
    for name, value in (("protocol.json", protocol), ("candidates.json", rows), ("transfer.json", transfers)):
        (folder / name).write_text(json.dumps(value, indent=2) + "\n")


def execute(folder):
    folder = Path(folder)
    if exists(folder / "results.json"):
        raise ValueError("completed generation is immutable")
    protocol = json.loads((folder / "protocol.json").read_text())
    rows = json.loads((folder / "candidates.json").read_text())
    transfers = json.loads((folder / "transfer.json").read_text())
    if digest([rows, transfers]) != protocol["inputs_sha256"]:
        raise ValueError("changed frozen abstraction inputs")
    env = MeasuredMemoryEnvironment(None, timeout=30)
    start = time.monotonic()
    audit = []
    accepted = []
    try:
        for row in rows:
            sources = []
            for goal in row["source_goals"]:
                searched = search(env, goal, structural_rank, budget=48, beam=4)
                sources.append(searched)
            screen = falsify(env, row["candidate"], limit=32)
            result = None
            replay = None
            if screen["status"] == "verified_counterexample":
                status = "refuted"
            else:
                result = search(env, row["candidate"], structural_rank, budget=48, beam=4)
                status = "admitted" if result["status"] == "verified" else "unknown"
                if status == "admitted":
                    replay = replay_memory_receipt(row["candidate"], result["receipt"])
                    accepted.append({"goal": row["candidate"], "actions": result["receipt"]["actions"],
                                     "license": "CC0-1.0", "source_revision": protocol["source_revision"]})
            audit.append({**row, "source_searches": sources, "status": status,
                          "falsification": screen, "search": result, "independent_replay": replay})
        baseline = []
        for task in transfers:
            before = env.actual_calls
            result = search(env, task["goal"], structural_rank, budget=48, beam=4)
            baseline.append({**task, "result": result, "physical_lean_calls": env.actual_calls - before})
        construction = {"physical_lean_calls": env.actual_calls, "seconds": env.construction_seconds}
    finally:
        env.close()
    with_memory = []
    enhanced = MeasuredMemoryEnvironment({"format": "pcs-checked-lemma-library-v1", "entries": accepted}, timeout=30)
    try:
        for task in transfers:
            before = enhanced.actual_calls
            result = search(enhanced, task["goal"], structural_rank, budget=48, beam=4)
            replay = replay_memory_receipt(task["goal"], result["receipt"]) if result["receipt"] else None
            with_memory.append({**task, "result": result, "independent_replay": replay,
                                "physical_lean_calls_excluding_legacy_replay": enhanced.actual_calls - before})
        memory_construction_calls = enhanced.construction_invocations
    finally:
        enhanced.close()
    report = {"format": "pcs-abstraction-repair-results-v2", "audit": audit,
              "baseline": baseline, "with_memory": with_memory, "admitted_entries": accepted,
              "cost": {"discovery_and_baseline_measured_calls": construction["physical_lean_calls"],
                       "memory_construction_completed_calls": memory_construction_calls,
                       "wall_seconds": time.monotonic() - start},
              "novel_mathematics_claim": False,
              "limitations": ["A useful routine generalization does not imply mathematical novelty", "Two source pairs and two public transfer tasks are narrow evidence", "Legacy replay-helper physical costs are excluded explicitly"]}
    (folder / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"admitted": len(accepted), "refuted": sum(r["status"] == "refuted" for r in audit),
                      "baseline_solved": sum(r["result"]["status"] == "verified" for r in baseline),
                      "memory_solved": sum(r["result"]["status"] == "verified" for r in with_memory)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "execute"])
    parser.add_argument("folder")
    args = parser.parse_args()
    (freeze if args.command == "freeze" else execute)(args.folder)
