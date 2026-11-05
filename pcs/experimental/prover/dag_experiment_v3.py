"""Frozen transfer experiment; no evaluation data enters gradient updates."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time
import torch
from .dag_policy_v3 import DAGPolicy
from .model import imitate
from .environment import candidates
from .induction_language import formalize
from .induction_ir import digest
from .data import structural_fingerprint
from .memory_cost import MeasuredInductionEnvironment
from .memory_search import memory_search

ROOT = Path(__file__).resolve().parents[3]
STATEMENTS = [
 ("natural_conjunctive_normalization", "For all natural numbers a and b, ((a + 0) equals a and (b * 1) equals b)."),
 ("natural_successor_congruence", "For all natural numbers a and b, if a equals b then the successor of (a + a) equals the successor of (b + b)."),
 ("integer_two_step_order", "For all integers a, b and c, if (a ≤ b and b ≤ c) then a ≤ c."),
 ("integer_antisymmetric_pair", "For all integers a and b, if (a ≤ b and b ≤ a) then (a equals b and b equals a)."),
 ("function_repeated_argument", "For all functions from natural numbers to natural numbers f, ∀ (a : Nat) (b : Nat), (a = b) → (f(f(a)) = f(f(b)))."),
 ("predicate_pair_transport", "For all predicates on natural numbers P, ∀ (a : Nat) (b : Nat), ((a = b) and P(a)) → P(b)."),
 ("list_append_left_unit_pair", "For all lists of natural numbers xs and ys, ((nil appended to xs) equals xs and (nil appended to ys) equals ys)."),
 ("list_length_cons_zero", "For all lists of natural numbers xs, ∀ (n : Nat), the length of (List.cons n xs) equals the successor of (the length of xs)."),
 ("list_append_right_unit_pair", "For all lists of natural numbers xs and ys, ((xs appended to nil) equals xs and (ys appended to nil) equals ys)."),
 ("natural_witness_pair", "For all natural numbers n, there exists a natural number x such that (x equals n and (x + 0) equals n)."),
 ("natural_disjunctive_order", "For all natural numbers a and b, if (a ≤ b or b ≤ a) then (b ≤ a or a ≤ b)."),
 ("function_conditional_rewrite", "For all functions from natural numbers to natural numbers f, ∀ (a : Nat) (b : Nat), ((f(a) = b) and (b = a)) → (f(a) = a)."),
]


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def freeze(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    if (folder / "protocol.json").exists():
        raise ValueError("protocol already frozen; use a new output directory")
    source = ROOT / "research/lean-learning-v2/training-trajectories.json.gz"
    episodes = json.load(gzip.open(source, "rt"))
    episodes = [e for e in episodes if e["split"] == "train" and e["family"] not in {"arithmetic", "functions"} and not e["id"].startswith(("nat_", "function_"))]
    tasks = []
    for identity, statement in STATEMENTS:
        parsed = formalize(statement)
        if parsed["status"] != "supported" or len(parsed["candidates"]) != 1:
            raise ValueError("unsupported frozen task " + identity + ": " + str(parsed))
        tasks.append({"id": identity, "family": identity, "split": "final", "goal": parsed["candidates"][0]["ir"], "statement": statement,
                      "license": "Apache-2.0", "source": "PCS authored cross-domain transfer challenge; known elementary mathematics"})
    train_fingerprints = {structural_fingerprint(e["goal"]) for e in episodes}
    if train_fingerprints & {structural_fingerprint(t["goal"]) for t in tasks}:
        raise ValueError("training/final alpha duplicate")
    write(folder / "tasks.json", tasks)
    write(folder / "protocol.json", {"format": "pcs-dag-transfer-protocol-v3", "tasks_sha256": digest(tasks),
          "training_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "training_ids": [e["id"] for e in episodes],
          "training_source": str(source.relative_to(ROOT)), "architectures": ["dag", "bag"], "seed": 43, "epochs": 20,
          "budget": 48, "depth": 18, "beam": 4, "per_lean_call_timeout_seconds": 30,
          "selection": "no model selection or retuning; both frozen models reported", "split": "logic-only training; arithmetic/list/function domain transfer final",
          "limitations": ["author-known mathematical structures; not a private blind benchmark", "domain split does not establish exhaustive semantic contamination freedom", "no novel mathematics claim"]})
    return len(tasks)


def run(folder):
    folder = Path(folder)
    if any((folder / name).exists() for name in ("training.json", "results.json.gz", "summary.json", "dag.json", "bag.json")):
        raise ValueError("experiment artifacts already exist; preserve history and use a new output directory")
    protocol = json.loads((folder / "protocol.json").read_text()); tasks = json.loads((folder / "tasks.json").read_text())
    if digest(tasks) != protocol["tasks_sha256"]:
        raise ValueError("frozen evaluation changed")
    training_source = ROOT / protocol["training_source"]
    if hashlib.sha256(training_source.read_bytes()).hexdigest() != protocol["training_source_sha256"]:
        raise ValueError("training source changed")
    started = time.monotonic()
    training = [e for e in json.load(gzip.open(training_source, "rt")) if e["id"] in protocol["training_ids"]]
    env = MeasuredInductionEnvironment(timeout=30)
    construction = {"physical_lean_calls": env.actual_calls, "wall_seconds": time.monotonic() - started}
    # Labels and intermediate states are re-created from current actual Lean.
    verify_start = time.monotonic(); calls = env.actual_calls
    refreshed = []
    for episode in training:
        receipt = env.verify(episode["goal"], episode["result"]["receipt"]["actions"])
        observed = env.observe(episode["goal"], receipt["actions"])
        if observed["status"] != "closed":
            raise RuntimeError("training trajectory not independently closed")
        refreshed.append({**episode, "result": {"status": "verified", "receipt": receipt, "states": observed["states"]}})
    verification = {"proofs": len(refreshed), "physical_lean_calls": env.actual_calls - calls, "wall_seconds": time.monotonic() - verify_start}
    with gzip.open(folder / "checked-training.json.gz", "wt") as out:
        json.dump(refreshed, out)
    models = {}; records = []
    for architecture in protocol["architectures"]:
        torch.manual_seed(protocol["seed"])
        model = DAGPolicy(architecture=architecture)
        tick = time.monotonic()
        stats = imitate(model, refreshed, epochs=protocol["epochs"], seed=protocol["seed"], candidate_provider=env.candidates)
        stats.update({"wall_seconds": time.monotonic() - tick, "parameters": sum(p.numel() for p in model.parameters())})
        metadata = {"protocol_sha256": digest(protocol), "training": stats, "experimental": True, "production_authority": False}
        checkpoint = folder / (architecture + ".json")
        sha = model.save(checkpoint, metadata)
        models[architecture] = DAGPolicy.load(checkpoint, sha)
        records.append({"architecture": architecture, "checkpoint_sha256": sha, **stats})
    write(folder / "training.json", {"construction": construction, "independent_training_verification": verification, "models": records})
    results = []
    for task in tasks:
        for name, rank in [("symbolic", env.default_rank), *[(n, m.rank) for n, m in models.items()]]:
            before = env.actual_calls; tick = time.monotonic()
            # Each search gets its own observation cache, identical action space.
            env.observations.clear()
            result = memory_search(env, task["goal"], rank, budget=protocol["budget"], depth=protocol["depth"], beam=protocol["beam"])
            cost = {"physical_lean_calls": env.actual_calls - before, "wall_seconds": time.monotonic() - tick}
            replay = None; replay_cost = None
            if result["status"] == "verified":
                # Distinct invocation re-elaborates exact immutable theorem/action sequence.
                before = env.actual_calls; tick = time.monotonic()
                replay = env.verify(task["goal"], result["receipt"]["actions"])
                if replay["goal_sha256"] != digest(task["goal"]) or replay["proof"] != result["receipt"]["proof"]:
                    raise RuntimeError("independent final replay differs")
                replay_cost = {"physical_lean_calls": env.actual_calls - before, "wall_seconds": time.monotonic() - tick}
            row = {"task": task["id"], "policy": name, "result": result, "search_cost": cost,
                   "independent_replay": replay, "replay_cost": replay_cost}
            results.append(row)
            with gzip.open(folder / "results.json.gz", "wt") as out:
                json.dump(results, out)
            print(json.dumps({"task": task["id"], "policy": name, "status": result["status"], "cost": cost}), flush=True)
    env.close()
    write(folder / "summary.json", {"format": "pcs-dag-policy-transfer-evaluation-v3", "tasks": len(tasks), "comparisons": len(results),
          "solved": {n: sum(r["policy"] == n and r["result"]["status"] == "verified" for r in results) for n in ["symbolic", "dag", "bag"]},
          "independently_replayed_proofs": sum(r["independent_replay"] is not None for r in results), "training": records,
          "physical_lean_calls": env.actual_calls, "total_wall_seconds": time.monotonic() - started,
          "max_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          "child_cpu_user_seconds": resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime,
          "child_cpu_system_seconds": resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,
          "scientific_authority": False, "promoted": False})


def solve_checkpoint(checkpoint, expected_sha, goal_path, output, budget=48):
    """Use a saved policy in the same real Lean search engine as the experiment."""
    model = DAGPolicy.load(checkpoint, expected_sha)
    goal = json.loads(Path(goal_path).read_text())
    env = MeasuredInductionEnvironment(timeout=30)
    try:
        result = memory_search(env, goal, model.rank, budget=budget, depth=18, beam=4)
        replay = env.verify(goal, result["receipt"]["actions"]) if result["status"] == "verified" else None
        if replay and replay["goal_sha256"] != digest(goal):
            raise RuntimeError("independent theorem replay mismatch")
        packet = {"format": "pcs-dag-checkpoint-search-v3", "checkpoint_sha256": expected_sha,
                  "result": result, "independent_replay": replay,
                  "physical_lean_calls_including_construction_and_replay": env.actual_calls,
                  "scientific_authority": False, "training_authorization": False}
        write(output, packet)
        return packet
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=["freeze", "run", "solve"]); parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint"); parser.add_argument("--sha256"); parser.add_argument("--goal"); parser.add_argument("--budget", type=int, default=48)
    args = parser.parse_args()
    if args.command == "freeze": print(freeze(args.output))
    elif args.command == "run": run(args.output)
    else:
        if not all([args.checkpoint, args.sha256, args.goal]): parser.error("solve requires checkpoint, sha256 and goal")
        print(json.dumps({"status": solve_checkpoint(args.checkpoint, args.sha256, args.goal, args.output, args.budget)["result"]["status"]}))

if __name__ == "__main__": main()
