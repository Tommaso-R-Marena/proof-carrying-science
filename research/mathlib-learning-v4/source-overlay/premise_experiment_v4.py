"""Frozen, multi-seed Mathlib premise training with actual JSON optimizer resume.

Final benchmark selection and evaluation remain outside this training module.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time
import torch
from .induction_ir import digest
from .premise_policy_v4 import PremisePolicy, save_training_checkpoint, load_training_checkpoint
from .premise_learning_v4 import train_supervised, actor_critic, MathlibRLEnvironment, collect_checked_training


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def freeze(folder, catalog, episodes, *, final_protocol_sha256, evaluation_environment_sha256=None, seeds=(71, 79), epochs=20, rl_episodes=8):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    if (folder / "protocol.json").exists():
        raise ValueError("protocol already frozen; preserve history")
    if any(e.get("split") != "train" or not e.get("independent_receipt") for e in episodes):
        raise ValueError("independently checked training trajectories required")
    if type(final_protocol_sha256) is not str or len(final_protocol_sha256) != 64 or any(c not in "0123456789abcdef" for c in final_protocol_sha256):
        raise ValueError("separately frozen final benchmark fingerprint required")
    environment_file = Path(__file__).resolve().parents[3] / "benchmarks/mathlib-v4-environment-v1/evaluation-environment.json"
    environment_sha = hashlib.sha256(environment_file.read_bytes()).hexdigest()
    if evaluation_environment_sha256 is not None and evaluation_environment_sha256 != environment_sha:
        raise ValueError("independent frozen evaluation environment differs")
    source_files = [Path(__file__), Path(__file__).with_name("premise_policy_v4.py"), Path(__file__).with_name("premise_learning_v4.py"),
                    Path(__file__).with_name("mathlib_environment_v4.py")]
    protocol = {"format": "pcs-grounded-mathlib-learning-protocol-v4", "catalog_sha256": digest(catalog),
                "training_data_sha256": digest(episodes), "training_task_ids": [e["id"] for e in episodes],
                "training_statement_sha256": [e["goal_sha256"] for e in episodes], "final_protocol_sha256": final_protocol_sha256,
                "evaluation_environment_byte_sha256": environment_sha,
                "architectures": ["graph", "bag"], "seeds": list(seeds), "epochs": epochs, "optimizer_resume_at_epoch": epochs // 2,
                "supervised_adam_lr": .003, "value_loss": .03, "uncertainty_loss": .01, "gradient_clip": 1.,
                "rl_episodes_per_graph_seed": rl_episodes, "rl_seed_offset": 100, "rl_max_steps": 16,
                "rl_adam_lr": .0005, "gamma": .97, "entropy": .002, "terminal_reward": "actual kernel check only",
                "selection": "no model selected from final outcomes; all seeds/architectures retained, no automatic promotion",
                "source_files": [{"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in source_files],
                "limitations": ["small CPU experiment; performance requires independent final evaluation", "proposal policies do not confer certification authority"]}
    with gzip.open(folder / "catalog.json.gz", "wt") as out: json.dump(catalog, out)
    with gzip.open(folder / "checked-training.json.gz", "wt") as out: json.dump(episodes, out)
    write(folder / "protocol.json", protocol)
    return protocol


def train(folder, env=None):
    folder = Path(folder)
    if (folder / "training-summary.json").exists() or list(folder.glob("*-resume.json")):
        raise ValueError("training artifacts already exist; use a new experiment directory")
    protocol = json.loads((folder / "protocol.json").read_text())
    catalog = json.load(gzip.open(folder / "catalog.json.gz", "rt"))
    episodes = json.load(gzip.open(folder / "checked-training.json.gz", "rt"))
    if digest(catalog) != protocol["catalog_sha256"] or digest(episodes) != protocol["training_data_sha256"]:
        raise ValueError("frozen training data changed")
    for row in protocol["source_files"]:
        if hashlib.sha256(Path(__file__).with_name(row["name"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("frozen training source changed")
    # Stored producer flags are insufficient: reconstruct actual trajectories
    # through the current source-pinned verifier before any optimizer update.
    owns_environment = env is None
    if env is None:
        from .mathlib_environment_v4 import MathlibEnvironmentV4
        env = MathlibEnvironmentV4()
    try:
        if digest(env.catalog) != protocol["catalog_sha256"]:
            raise ValueError("fresh training environment catalog mismatch")
        if hasattr(env, "_states"):
            env._states.clear()
        before_calls, before_requests, tick = env.calls, env.worker_requests, time.monotonic()
        actual = collect_checked_training(env, [{"id": e["id"], "split": "train", "statement": e["statement"],
            "actions": e["actions"], "source": e["source"], "license": e["license"]} for e in episodes])
        for expected, fresh in zip(episodes, actual):
            if digest(expected["records"]) != digest(fresh["records"]):
                raise ValueError("stored training state/option labels differ from actual Lean")
            if expected["independent_receipt"]["kernel"] != fresh["independent_receipt"]["kernel"]:
                raise ValueError("stored training kernel evidence differs")
        write(folder / "pretraining-independent-recheck.json", {"proofs": len(actual), "compiler_invocations": env.calls - before_calls,
              "structured_worker_requests": env.worker_requests - before_requests,
              "physical_lean_calls": env.calls - before_calls + env.worker_requests - before_requests,
              "wall_seconds": time.monotonic() - tick, "dataset_labels_reconstructed": True, "catalog_sha256": digest(env.catalog)})
    finally:
        if owns_environment:
            env.close()
    torch.set_num_threads(2); rows = []
    for seed in protocol["seeds"]:
        for architecture in protocol["architectures"]:
            torch.manual_seed(seed)
            model = PremisePolicy(catalog, architecture=architecture)
            started = time.monotonic()
            optimizer, first = train_supervised(model, episodes, epochs=protocol["optimizer_resume_at_epoch"], seed=seed)
            resume = folder / f'{architecture}-{seed}-resume.json'
            resume_sha = save_training_checkpoint(resume, model, optimizer, {"next_epoch": first["next_epoch"], "protocol_sha256": digest(protocol)})
            resumed, optimizer, progress = load_training_checkpoint(resume, resume_sha, catalog)
            optimizer, second = train_supervised(resumed, episodes, epochs=protocol["epochs"], seed=seed,
                                                 optimizer=optimizer, start_epoch=progress["next_epoch"], restore_rng=True)
            checkpoint = folder / f'{architecture}-{seed}.json'
            metadata = {"protocol_sha256": digest(protocol), "training_data_sha256": digest(episodes),
                        "seed": seed, "experimental": True, "production_authority": False}
            checkpoint_sha = resumed.save(checkpoint, metadata)
            row = {"architecture": architecture, "seed": seed, "checkpoint": checkpoint.name, "checkpoint_sha256": checkpoint_sha,
                   "resume_checkpoint": resume.name, "resume_checkpoint_sha256": resume_sha, "actual_optimizer_resume": True,
                   "parameters": sum(p.numel() for p in resumed.parameters()), "phase1": first, "phase2": second,
                   "wall_seconds": time.monotonic() - started}
            rows.append(row); write(folder / "training-summary.json", {"format": "pcs-premise-supervised-training-v4", "models": rows, "promoted": False})
            print(json.dumps({"architecture": architecture, "seed": seed, "trained": True, "checkpoint_sha256": checkpoint_sha}), flush=True)
    return rows


def run_rl(folder, env):
    folder = Path(folder)
    if (folder / "rl-summary.json").exists():
        raise ValueError("RL results already exist; preserve history")
    protocol = json.loads((folder / "protocol.json").read_text())
    catalog = json.load(gzip.open(folder / "catalog.json.gz", "rt"))
    if digest(env.catalog) != protocol["catalog_sha256"]:
        raise ValueError("actual Mathlib catalog differs from frozen training environment")
    episodes = json.load(gzip.open(folder / "checked-training.json.gz", "rt"))
    tasks = [{"id": e["id"], "split": "train", "statement": e["statement"]} for e in episodes]
    supervised = json.loads((folder / "training-summary.json").read_text())["models"]
    rows = []
    for model_row in [r for r in supervised if r["architecture"] == "graph"]:
        model = PremisePolicy.load(folder / model_row["checkpoint"], model_row["checkpoint_sha256"], catalog)
        limit = 6
        environment = MathlibRLEnvironment(env, limit=limit, max_steps=protocol["rl_max_steps"])
        before_calls, before_requests, before_cpu = env.calls, env.worker_requests, env.cpu_seconds
        optimizer, stats = actor_critic(model, environment, tasks, episodes=protocol["rl_episodes_per_graph_seed"], seed=model_row["seed"] + protocol["rl_seed_offset"])
        seed = model_row["seed"]
        resume_path = folder / f'graph-rl-{seed}-resume.json'
        resume_sha = save_training_checkpoint(resume_path, model, optimizer, {"episodes_completed": len(stats["episodes"]), "protocol_sha256": digest(protocol)})
        checkpoint = folder / f'graph-rl-{seed}.json'
        checkpoint_sha = model.save(checkpoint, {"protocol_sha256": digest(protocol), "supervised_checkpoint_sha256": model_row["checkpoint_sha256"],
                                                 "experimental": True, "production_authority": False})
        with gzip.open(folder / f'rl-trajectories-{seed}.json.gz', "wt") as out: json.dump(stats, out)
        rows.append({"seed": seed, "checkpoint": checkpoint.name, "checkpoint_sha256": checkpoint_sha, "resume_checkpoint": resume_path.name,
                     "resume_checkpoint_sha256": resume_sha, "weights_changed": stats["weights_changed"], "episodes": len(stats["episodes"]),
                     "verified_episodes": sum(e["status"] == "verified" for e in stats["episodes"]),
                     "independently_replayed_terminals": sum(e["independent_receipt"] is not None for e in stats["episodes"]),
                     "compiler_invocations": env.calls - before_calls, "structured_worker_requests": env.worker_requests - before_requests,
                     "physical_lean_calls": env.calls - before_calls + env.worker_requests - before_requests, "child_cpu_seconds": env.cpu_seconds - before_cpu,
                     "wall_seconds": stats["wall_seconds"]})
        write(folder / "rl-summary.json", {"format": "pcs-real-mathlib-sequential-rl-v4", "models": rows, "promoted": False})
        print(json.dumps({"rl_seed": seed, "verified_episodes": rows[-1]["verified_episodes"], "weights_changed": stats["weights_changed"]}), flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=["train", "rl"]); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "train": train(args.output)
    else:
        from .mathlib_environment_v4 import MathlibEnvironmentV4
        env = MathlibEnvironmentV4()
        try: run_rl(args.output, env)
        finally: env.close()

if __name__ == "__main__": main()
