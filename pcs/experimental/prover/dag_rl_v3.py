"""Sequential checker-controlled DAG actor-critic continuation, no promotion."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time
from .dag_experiment_v3 import write
from .dag_policy_v3 import DAGPolicy
from .data import structural_fingerprint
from .hybrid import std_search, replay_std_receipt
from .induction_language import formalize
from .induction_ir import digest
from .memory_cost import MeasuredInductionEnvironment
from .memory_search import memory_search
from .model import actor_critic

STATEMENTS = [
 ("successor_existential", "For all natural numbers n, there exists a natural number m such that the successor of n equals m."),
 ("universal_function_identity", "For all functions from natural numbers to natural numbers f, ∀ (n : Nat), (∀ (x : Nat), f(x) = x) → (f(f(n)) = n)."),
 ("reverse_length_conjunction", "For all lists of natural numbers xs, ((the reversal of (the reversal of xs)) equals xs and (the length of (the reversal of xs)) equals the length of xs)."),
 ("integer_equality_transport_sum", "For all integers a, b and c, if (a equals b and b equals c) then (a + c) equals (c + c)."),
]


def run(folder):
    folder = Path(folder)
    if (folder / "rl-protocol.json").exists():
        raise ValueError("RL experiment already frozen; do not overwrite history")
    old_tasks = json.loads((folder / "tasks.json").read_text())
    training = json.load(gzip.open(folder / "checked-training.json.gz", "rt"))
    train_stats = json.loads((folder / "training.json").read_text())
    base_sha = next(m["checkpoint_sha256"] for m in train_stats["models"] if m["architecture"] == "dag")
    tasks = []
    for identity, statement in STATEMENTS:
        parsed = formalize(statement)
        if parsed["status"] != "supported":
            raise ValueError("unsupported new RL final task " + identity)
        tasks.append({"id": identity, "family": identity, "split": "final", "goal": parsed["candidates"][0]["ir"],
                      "statement": statement, "license": "Apache-2.0", "source": "PCS authored fresh bounded RL transfer diagnostic"})
    if {structural_fingerprint(t["goal"]) for t in tasks} & {structural_fingerprint(t["goal"]) for t in training + old_tasks}:
        raise ValueError("new final alpha-contamination")
    protocol = {"format": "pcs-dag-sequential-rl-v3", "checkpoint_sha256": base_sha, "algorithm": "existing sequential-on-policy-actor-critic-v1",
                "episodes": 8, "seed": 59, "episode_max_steps": 12, "search_budget": 48, "depth": 18, "beam": 4,
                "tasks": tasks, "training_ids": [t["id"] for t in training], "training_data_sha256": digest(training),
                "environment_source_sha256": hashlib.sha256(Path(__file__).with_name("environment.py").read_bytes()).hexdigest(),
                "reward_authority": "LeanEnvironment.step immutable goal and kernel verification; model supplies only candidate action index",
                "no_retuning": True, "selection": "report supervised and RL; never promote automatically", "limitations": ["four author-known new structures, not private blind generalization", "single seed; no superiority significance claim"]}
    write(folder / "rl-protocol.json", protocol)
    model = DAGPolicy.load(folder / "dag.json", base_sha)
    tick = time.monotonic(); env = MeasuredInductionEnvironment(timeout=30, max_steps=12)
    construction = {"calls": env.actual_calls, "wall_seconds": time.monotonic() - tick}
    before = env.actual_calls; tick = time.monotonic()
    try:
        stats = actor_critic(model, env, training, episodes=protocol["episodes"], seed=protocol["seed"])
        rl_cost = {"calls": env.actual_calls - before, "wall_seconds": time.monotonic() - tick}
        train_replays = []
        for index, episode in enumerate(stats["episodes"]):
            # Every terminal positive reward must have an independent checked receipt.
            positives = [s for s in episode["steps"] if s["reward"] == 1.0]
            if bool(positives) != (episode["status"] == "verified") or any(s["status"] != "verified" for s in positives):
                raise RuntimeError("reward authority contract violated")
            if episode["status"] == "verified":
                task = training[index % len(training)]
                receipt = env.verify(task["goal"], episode["receipt"]["actions"])
                train_replays.append({"episode": index, "receipt": receipt})
        with gzip.open(folder / "rl-training.json.gz", "wt") as out:
            json.dump({"construction": construction, "training_cost": rl_cost, "stats": stats, "independent_terminal_replays": train_replays}, out)
        rl_sha = model.save(folder / "dag-rl.json", {"experimental": True, "production_authority": False, "protocol_sha256": digest(protocol),
                   "before_weights_sha256": stats["before"], "after_weights_sha256": stats["after"]})
    finally:
        env.close()
    supervised = DAGPolicy.load(folder / "dag.json", base_sha)
    reinforced = DAGPolicy.load(folder / "dag-rl.json", rl_sha)
    env = MeasuredInductionEnvironment(timeout=30)
    results = []
    try:
        for task in tasks:
            for name, rank in [("symbolic", env.default_rank), ("supervised_dag", supervised.rank), ("rl_dag", reinforced.rank)]:
                before = env.actual_calls; tick = time.monotonic(); env.observations.clear()
                result = memory_search(env, task["goal"], rank, budget=48, depth=18, beam=4)
                cost = {"calls": env.actual_calls - before, "wall_seconds": time.monotonic() - tick}
                replay = env.verify(task["goal"], result["receipt"]["actions"]) if result["status"] == "verified" else None
                results.append({"task": task["id"], "policy": name, "result": result, "independent_replay": replay, "cost": cost})
                with gzip.open(folder / "rl-evaluation.json.gz", "wt") as out: json.dump(results, out)
                print(json.dumps({"task": task["id"], "policy": name, "status": result["status"]}), flush=True)
        # Stronger whole-goal tactics are separately reported, not budget-equivalent.
        standards = []
        for task in tasks:
            result = std_search(env, task["goal"])
            replay = replay_std_receipt(task["goal"], result["receipt"]) if result["status"] == "verified" else None
            standards.append({"task": task["id"], "result": result, "independent_replay": replay})
        write(folder / "rl-std-baseline.json", standards)
    finally:
        env.close()
    write(folder / "rl-summary.json", {"format": "pcs-dag-rl-results-v3", "episodes": len(stats["episodes"]),
          "verified_training_episodes": stats["verified_episodes"], "independently_replayed_training_terminals": len(train_replays),
          "weights_changed": stats["weights_changed"], "checkpoint_sha256": rl_sha, "training_cost": rl_cost,
          "solved": {name: sum(r["policy"] == name and r["result"]["status"] == "verified" for r in results) for name in ["symbolic", "supervised_dag", "rl_dag"]},
          "std_solved": sum(r["result"]["status"] == "verified" for r in standards), "final_tasks": len(tasks),
          "evaluation_physical_calls_including_replays": env.actual_calls, "promoted": False, "scientific_authority": False})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); args = parser.parse_args(); run(args.output)
