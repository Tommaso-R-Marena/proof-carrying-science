"""Freeze and execute a new public prospective mathematical benchmark generation.

No private/blind-test claim: tasks are public, developer-authored, and Lean's
libraries contain relevant mathematics. No new fitting uses this final split.
Historical v1 final tasks/checkpoints remain immutable and explicitly exposed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from .environment import ROOT, search, _symbolic_priority
from .induction_ir import digest
from .induction_language import formalize
from .evidence_storage import exists, read, logical_paths

TYPED_TASKS = [
 ("utility-cancel-chain", "utility", "For all natural numbers a, b, c and d, if (a + c) equals (b + c) and (b + d) equals (c + d) then a equals c."),
 ("utility-reverse-congruence", "utility", "For all lists of natural numbers xs and ys, if xs equals ys then the reversal of xs equals the reversal of ys."),
 ("utility-successor-double", "utility", "For all natural numbers a and b, if the successor of (the successor of a) equals the successor of (the successor of b) then a equals b."),
 ("utility-predicate-persist", "utility", "For all predicates on natural numbers P, if (P(0) and (∀ (n : Nat), P(n) implies P(the successor of n))) then (∀ (k : Nat), P(k + (k * k)))."),
 ("selection-cancel-reversed", "selection", "For all natural numbers a, b and c, if (a + c) equals (b + c) then the successor of a equals the successor of b."),
 ("selection-reverse-triple", "selection", "For all lists of natural numbers xs, the reversal of (the reversal of (the reversal of xs)) equals the reversal of xs."),
 ("selection-order-chain", "selection", "For all natural numbers a, b and c, if (a + c) ≤ (b + c) then a ≤ b."),
 ("selection-function-recurrence", "selection", "For all functions from natural numbers to natural numbers f, if ((f(0) equals 0) and (∀ (n : Nat), f(the successor of n) equals the successor of f(n))) then (∀ (k : Nat), f(k) equals k)."),
 ("final-cancel-common-function", "final", "For all functions from natural numbers to natural numbers f, (∀ (a : Nat), ∀ (b : Nat), ∀ (c : Nat), ((f(a) + c) equals (f(b) + c)) implies (f(a) equals f(b)))."),
 ("final-cancel-context", "final", "For all natural numbers a, b, c and d, if (a + c) equals (b + c) then (a + d) equals (b + d)."),
 ("final-nested-successor-context", "final", "For all natural numbers a and b, if the successor of (the successor of a) equals the successor of (the successor of b) then (a + a) equals (b + b)."),
 ("final-list-reverse-quad", "final", "For all lists of natural numbers xs, the reversal of (the reversal of (the reversal of (the reversal of xs))) equals xs."),
 ("final-list-length-context", "final", "For all lists of natural numbers xs and ys, the length of ((the reversal of xs) appended to (the reversal of ys)) equals the length of (xs appended to ys)."),
 ("final-predicate-renamed", "final", "For all predicates on natural numbers Q, if (Q(0) and (∀ (t : Nat), Q(t) implies Q(the successor of t))) then (∀ (m : Nat), Q((m * m) + (m * m)))."),
 ("final-function-offset", "final", "For all functions from natural numbers to natural numbers g, (∀ (a : Nat), ((g(0) equals a) and (∀ (t : Nat), g(the successor of t) equals the successor of g(t))) implies (∀ (m : Nat), g(m) equals (a + m)))."),
 ("final-predicate-successor", "final", "For all predicates on natural numbers Q, if (Q(0) and (∀ (t : Nat), Q(t) implies Q(the successor of t))) then (∀ (m : Nat), Q(the successor of (m * m)))."),
]
MATHLIB_TASKS = [
 ("external-function-composition", "selection", "∀ (f g : Nat → Nat), Function.Injective f → Function.Injective g → Function.Injective (f ∘ g)"),
 ("external-group-double-inverse", "selection", "∀ (G : Type) [Group G] (a : G), (a⁻¹)⁻¹ = a"),
 ("external-image-composition", "final", "∀ (f g : Nat → Nat) (s : Set Nat), (g ∘ f) '' s = g '' (f '' s)"),
 ("external-preimage-union", "final", "∀ (f : Nat → Nat) (s t : Set Nat), f ⁻¹' (s ∪ t) = (f ⁻¹' s) ∪ (f ⁻¹' t)"),
 ("external-injective-cancel-context", "final", "∀ (f : Nat → Nat), Function.Injective f → ∀ a b, f a = f b → a = b"),
 ("external-surjective-composition", "final", "∀ (f g : Nat → Nat), Function.Surjective f → Function.Surjective g → Function.Surjective (g ∘ f)"),
 ("external-group-right-inverse", "final", "∀ (G : Type) [Group G] (a b : G), a * b * b⁻¹ = a"),
 ("external-factorial-positive", "final", "∀ n : Nat, 0 < n.factorial"),
]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def freeze(folder):
    folder = Path(folder)
    if folder.exists():
        raise ValueError("new generation directory must not already exist")
    rows = []
    for identity, split, statement in TYPED_TASKS:
        parsed = formalize(statement)
        if parsed["status"] != "supported":
            raise ValueError(f"unsupported frozen author statement {identity}: {parsed}")
        rows.append({"id": identity, "split": split, "statement": statement, "goal": parsed["candidates"][0]["ir"],
                     "license": "CC0-1.0", "source": "PCS developer-authored prospective v2", "kind": "typed"})
    for identity, split, statement in MATHLIB_TASKS:
        rows.append({"id": identity, "split": split, "statement": statement, "license": "CC0-1.0",
                     "source": "PCS developer-authored statement; mathematics may already exist in Mathlib", "kind": "mathlib"})
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths = [Path(__file__), Path(__file__).with_name("hybrid.py"), Path(__file__).with_name("mathlib_retrieval.py")]
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    protocol = {"format": "pcs-prospective-hybrid-v2", "frozen_before_evaluation": True,
                "created_source_revision": revision, "tasks_sha256": digest(rows), "source_manifest_sha256": digest(manifest),
                "typed_action_budget": 48, "depth": 18, "beam": 4, "mathlib_retrieval_limit": 8,
                "seed": 17, "new_training": False,
                "models": "historical frozen v1 checkpoints; no final-data training or reselection",
                "exposure": "Public developer-authored prospective tasks, not private blind data. Existing v1 final is historical exposed.",
                "selection": "No model promotion or tuning on this experiment; all components frozen before first result.",
                "resource_limit": "8 GiB Lean subprocess address-space, 60s CPU, 30s invocation timeout",
                "claim_boundary": "No novel mathematics or general-English fidelity claim; every success independently replayed."}
    folder.mkdir(parents=True)
    write(folder / "tasks.json", rows)
    write(folder / "protocol.json", protocol)
    write(folder / "source-manifest.json", manifest)
    print(json.dumps({"frozen": str(folder), "tasks": len(rows), "tasks_sha256": digest(rows)}))


def evaluate(folder, *, kind="all"):
    from .hybrid import solve, std_search, replay_std_receipt
    from .memory_cli import load
    from .memory_cost import MeasuredMemoryEnvironment, MeasuredInductionEnvironment
    from .memory_environment import structural_rank, replay_memory_receipt
    from .mathlib_retrieval import MathlibRetriever
    folder = Path(folder)
    tasks = json.loads((folder / "tasks.json").read_text())
    protocol = json.loads((folder / "protocol.json").read_text())
    if digest(tasks) != protocol["tasks_sha256"]:
        raise ValueError("frozen tasks changed")
    registry, entry, library, model = load(ROOT / "research/verified-memory-v1")
    records = folder / "results"
    records.mkdir(exist_ok=True)
    start = time.monotonic()
    if kind in {"all", "typed"}:
        for task in tasks:
            if task["kind"] != "typed":
                continue
            for mode in ("symbolic", "memory_structural", "memory_learned", "Std", "hybrid"):
                target = records / (task["id"] + "-" + mode + ".json")
                if exists(target):
                    continue
                if mode == "hybrid":
                    result = solve(task["goal"], library, model, budget=protocol["typed_action_budget"])
                else:
                    env = MeasuredInductionEnvironment(timeout=30) if mode == "Std" else MeasuredMemoryEnvironment(library if mode != "symbolic" else None, timeout=30)
                    try:
                        before = time.monotonic()
                        if mode == "Std":
                            result = std_search(env, task["goal"])
                            replay = replay_std_receipt(task["goal"], result["receipt"]) if result["receipt"] else None
                        else:
                            rank = model.rank if mode == "memory_learned" else structural_rank
                            result = search(env, task["goal"], rank, budget=protocol["typed_action_budget"], depth=18, beam=4)
                            replay = replay_memory_receipt(task["goal"], result["receipt"]) if result["receipt"] else None
                        result["independent_replay"] = replay
                        result["cost"] = {"measured_lean_calls_excluding_legacy_memory_replay": env.actual_calls,
                                          "cold_search_and_replay_wall_seconds": time.monotonic() - before,
                                          "construction_seconds": getattr(env, "construction_seconds", None)}
                    finally:
                        env.close()
                write(target, {"task": task, "mode": mode, "checkpoint_sha256": entry["sha256"] if mode in {"memory_learned", "hybrid"} else None, "result": result})
                print(json.dumps({"task": task["id"], "mode": mode, "status": result["status"]}), flush=True)
    if kind in {"all", "mathlib"}:
        retriever = MathlibRetriever()
        write(folder / "mathlib-catalog.json", {"mathlib_revision": retriever.mathlib.name,
              "catalog_sha256": retriever.catalog_sha256, "entries": retriever.catalog,
              "imports_sha256": retriever.import_digests})
        for task in tasks:
            if task["kind"] != "mathlib":
                continue
            for mode in ("lexical", "structural", "standard"):
                target = records / (task["id"] + "-" + mode + ".json")
                if exists(target):
                    continue
                result = retriever.solve(task["statement"], mode="lexical" if mode == "lexical" else "structural", limit=protocol["mathlib_retrieval_limit"], standard=mode == "standard")
                write(target, {"task": task, "mode": mode, "result": result})
                print(json.dumps({"task": task["id"], "mode": mode, "status": result["status"]}), flush=True)
    summary = {}
    for path in logical_paths(records):
        row = read(path)
        key = row["task"]["kind"] + ":" + row["task"]["split"] + ":" + row["mode"]
        count = summary.setdefault(key, {"tasks": 0, "verified": 0})
        count["tasks"] += 1
        count["verified"] += row["result"]["status"] == "verified"
    write(folder / "summary.json", {"format": "pcs-prospective-hybrid-summary-v2", "counts": summary,
          "this_invocation_wall_seconds": time.monotonic() - start,
          "limitations": ["Public developer-authored benchmarks, not blind/private", "Frozen old model is not fitted on new tasks", "No automatic promotion", "Memory independent-replay legacy helper costs are explicitly excluded where uninstrumented"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "evaluate"])
    parser.add_argument("folder")
    parser.add_argument("--kind", choices=["all", "typed", "mathlib"], default="all")
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.folder)
    else:
        evaluate(args.folder, kind=args.kind)


if __name__ == "__main__":
    main()
