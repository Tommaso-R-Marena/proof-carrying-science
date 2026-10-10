"""Reproducible collection → verification → BC → sequential RL → evaluation."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time

import torch

from .corpus import tasks
from .environment import LeanEnvironment, search
from .ir import digest
from .model import ReasoningNetwork, imitate, actor_critic


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def evaluate(env, problems, rank, budget):
    results = []
    for task in problems:
        result = search(env, task["goal"], rank=rank, budget=budget, beam=4)
        results.append({**task, "result": result})
    return results


def reproduce(output, epochs=35, episodes=12, seeds=(17, 31, 47), budget=96):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    corpus = tasks()
    partitions = {name: [t for t in corpus if t["split"] == name] for name in ("train", "validation", "final")}
    # Protocol and all task partitions are committed to disk BEFORE collecting,
    # fitting or evaluating any policy. Public final tasks remain open to audit.
    protocol = {"format": "pcs-prover-protocol-v1", "budget": budget, "beam": 4, "depth": 18,
                "epochs": epochs, "rl_episodes_per_generation": episodes, "seeds": list(seeds),
                "selection": "validation verified count, then fewer expansions; no authority promotion",
                "final_evaluations": "all frozen checkpoints once; no fitting against final results",
                "limitations": ["public authored elementary tasks", "no external project transfer",
                                "probe replay caching shared; expansion budgets equal, timing cache-dependent"]}
    write(output / "protocol.json", protocol)
    write(output / "tasks.json", corpus)
    source_root = Path(__file__).resolve().parents[3]
    source_files = list(Path(__file__).parent.glob("*.py")) + [source_root / "formal/PCSProofProbe.lean", source_root / "formal/PCSProofWorker.lean"]
    source_manifest = {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_files)}
    write(output / "source-manifest.json", source_manifest)
    env = LeanEnvironment()
    try:
        print("Collecting actual Lean training trajectories", flush=True)
        training = evaluate(env, partitions["train"], None, budget * 2)
        # Independently replay every successful label in a fresh Lean process.
        for record in training:
            if record["result"]["status"] == "verified":
                checked = env.verify(record["goal"], record["result"]["receipt"]["actions"])
                if checked["goal_sha256"] != digest(record["goal"]):
                    raise RuntimeError("training label does not bind original theorem")
        write(output / "training-trajectories.json", training)
        manifest = {"format": "pcs-intelligence-data-v1", "license": "Apache-2.0",
                    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    "tasks_sha256": digest(corpus), "training_sha256": digest(training),
                    "lean": env.version, "adapter_sha256": env.source_sha,
                    "human_trajectories": False, "hint_exposure": "symbolic search only",
                    "splits": {k: [t["id"] for t in v] for k, v in partitions.items()}}
        write(output / "data-manifest.json", manifest)
        write(output / "premise-catalog.json", env._source("#pcs_catalog\n", "PCS_CATALOG:"))
        models, training_reports, rl_reports, registry = {}, {}, {}, []
        for seed in seeds:
            print(f"Training graph/bag and sequential RL, seed {seed}", flush=True)
            torch.manual_seed(seed)
            initial = ReasoningNetwork()
            models[f"untrained-{seed}"] = copy.deepcopy(initial)
            graph = copy.deepcopy(initial)
            training_reports[f"graph-{seed}"] = imitate(graph, training, epochs=epochs, seed=seed)
            models[f"graph-{seed}"] = copy.deepcopy(graph)
            torch.manual_seed(seed)
            bag = ReasoningNetwork(architecture="bag")
            training_reports[f"bag-{seed}"] = imitate(bag, training, epochs=epochs, seed=seed)
            models[f"bag-{seed}"] = bag
            for generation in [1, 2]:
                report = actor_critic(graph, env, partitions["train"], episodes=episodes, seed=seed + generation)
                rl_reports[f"rl{generation}-{seed}"] = report
                models[f"rl{generation}-{seed}"] = copy.deepcopy(graph)
        write(output / "supervised-training.json", training_reports)
        write(output / "rl-training.json", rl_reports)
        # Freeze ALL model weights before any final benchmark execution.
        for name, model in models.items():
            sha = model.save(output / f"{name}.json", {"dataset": digest(training), "protocol": digest(protocol),
                                                    "torch": torch.__version__, "status": "experimental"})
            registry.append({"id": name, "checkpoint": f"{name}.json", "sha256": sha,
                             "parameters": sum(p.numel() for p in model.parameters()),
                             "architecture": model.architecture, "approval": "experimental-local",
                             "supported_domain": "typed elementary Lean propositions and Nat expressions",
                             "pcs_authority": False})
        evaluations = {}
        print("Evaluating frozen models and baselines", flush=True)
        for split in ["validation", "final"]:
            evaluations[split] = {"symbolic": evaluate(env, partitions[split], None, budget)}
            def random_rank(state, options):
                rng = random.Random(int(digest(state), 16) ^ 123)
                return [rng.random() for _ in options]
            evaluations[split]["random"] = evaluate(env, partitions[split], random_rank, budget)
            for name, model in models.items():
                evaluations[split][name] = evaluate(env, partitions[split], model.rank, budget)
                solved = sum(r["result"]["status"] == "verified" for r in evaluations[split][name])
                print(f"{split}: {name} {solved}/{len(partitions[split])}", flush=True)
        def metrics(records):
            return {"verified": sum(r["result"]["status"] == "verified" for r in records),
                    "tasks": len(records), "expansions": sum(r["result"]["expansions"] for r in records),
                    "actual_lean_requests": sum(r["result"]["lean_invocations"] for r in records),
                    "wall_seconds": sum(r["result"]["wall_seconds"] for r in records)}
        summary = {s: {name: metrics(records) for name, records in results.items()} for s, results in evaluations.items()}
        selected = max((n for n in models if not n.startswith("untrained-")), key=lambda n: (summary["validation"][n]["verified"], -summary["validation"][n]["expansions"]))
        write(output / "evaluations.json", evaluations)
        write(output / "registry.json", {"format": "pcs-model-registry-v1", "models": registry,
                                        "selected_local_experiment": selected, "production_authority": False})
        write(output / "summary.json", {"metrics": summary, "selected": selected,
            "training_verified": sum(r["result"]["status"] == "verified" for r in training),
            "total_wall_seconds": time.monotonic() - start, "actual_lean_requests": env.invocations,
            "lean_wall_seconds": env.seconds, "torch": torch.__version__, "cpu_threads": torch.get_num_threads(),
            "gpu_used": False, "financial_spend": 0})
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
        write(output / "SHA256.json", files)
        return summary
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--episodes", type=int, default=12)
    parser.add_argument("--seeds", type=int, nargs="+", default=[17, 31, 47])
    args = parser.parse_args()
    reproduce(args.output, args.epochs, args.episodes, args.seeds)


if __name__ == "__main__":
    main()
