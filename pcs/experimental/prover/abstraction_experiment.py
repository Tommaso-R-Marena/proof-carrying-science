"""Run frozen induction, state-mined lemmas and measured sequential learning."""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tarfile
import time

import torch

from .environment import LeanEnvironment, search, ROOT
from .induction_environment import InductionEnvironment
from .library import replay_library_receipt
from .abstraction_environment import AbstractionEnvironment, abstraction_priority
from .discovery import discover
from .model import ReasoningNetwork, imitate, actor_critic
from .reuse_model import ReuseNetwork
from .reuse_experiment import metrics
from .ir import digest


def write(path, value):
    raw=(json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if len(raw)>512000: path.with_suffix(path.suffix+".gz").write_bytes(gzip.compress(raw,mtime=0))
    else:path.write_bytes(raw)


def measured_search(env, task, rank, protocol):
    # No policy benefits from another policy's memoized Lean observations.
    env.observations.clear()
    start, calls, lean_seconds = time.monotonic(), env.invocations, env.seconds
    result = search(env, task["goal"], rank, budget=protocol["budget"],
                    beam=protocol["beam"], depth=protocol["depth"])
    return {**task, "result": result, "cost": {
        "all_lean_invocations": env.invocations-calls, "lean_seconds": env.seconds-lean_seconds,
        "wall_seconds_including_initial_state": time.monotonic()-start}}


def reproduce(output):
    output = Path(output)
    protocol = json.loads((output / "protocol.json").read_text())
    tasks = json.loads((output / "tasks.json").read_text())
    if digest(tasks) != protocol["tasks_sha256"]: raise ValueError("frozen tasks changed")
    if (output / "summary.json").exists(): raise ValueError("do not overwrite completed experiments")
    parts = {s: [t for t in tasks if t["split"] == s] for s in ["train", "validation", "final"]}
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    sources = [*Path(__file__).parent.glob("*.py"), ROOT / "formal/PCSProofProbe.lean", ROOT / "formal/PCSProofWorker.lean", ROOT / "formal/PCSReuseWorker.lean"]
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}
    write(output / "source-manifest.json", manifest)
    with tarfile.open(output / "source-overlay.tar.gz", "w:gz") as archive:
        for p in sorted(sources): archive.add(p, arcname=str(p.relative_to(ROOT)))
    start = time.monotonic()
    base, library_env = InductionEnvironment(timeout=30), None
    try:
        training = []
        for task in parts["train"]:
            record = measured_search(base, task, None, protocol); training.append(record)
            print("Collect", task["id"], record["result"]["status"], flush=True)
        write(output / "initial-trajectories.json", training)
        library, discovery, mined_training = discover(base, training,
            heldout=parts["validation"]+parts["final"], candidate_limit=protocol["candidate_limit"],
            budget=protocol["candidate_search_budget"], source_revision=revision)
        write(output / "discovery.json", discovery); write(output / "library.json", library)
        print("Discovered", len(library["entries"]), "checked lemmas from", len(discovery), "candidates", flush=True)
        library_env = AbstractionEnvironment(library, timeout=30, heldout=parts["validation"]+parts["final"])
        write(output / "catalog.json", library_env.catalog)
        reuse_training = [measured_search(library_env, task, abstraction_priority, protocol) for task in parts["train"]]
        if protocol.get("training_source")=="original_verified_trajectories_replayed_in_library_environment":
            original=[]
            for record in training:
                if record["result"]["status"]!="verified":continue
                actions=record["result"]["receipt"]["actions"]
                observed=library_env.observe(record["goal"],actions)
                receipt=library_env.verify(record["goal"],actions)
                original.append({**record,"result":{**record["result"],"receipt":receipt,"states":observed["states"]}})
            reuse_training=original+reuse_training
        write(output / "training-trajectories.json", reuse_training)
        models, training_reports = {}, {}
        for seed in protocol["seeds"]:
            print("Train seed", seed, flush=True)
            if protocol.get("grounded_model"):
                from .grounded_model import GroundedNetwork,train_validity
                network=GroundedNetwork
            else:network=ReuseNetwork
            torch.manual_seed(seed); model = network()
            models[f"untrained-{seed}"] = copy.deepcopy(model)
            if protocol.get("grounded_model"):
                started=time.monotonic()
                training_reports[f"checker-response-{seed}"]={**train_validity(model,training,epochs=protocol["validity_epochs"],seed=seed),"wall_seconds":time.monotonic()-started}
            started = time.monotonic()
            training_reports[f"graph-{seed}"] = {**imitate(model, reuse_training, epochs=protocol["epochs"], seed=seed,
                candidate_provider=library_env.candidates), "wall_seconds": time.monotonic()-started}
            models[f"graph-{seed}"] = copy.deepcopy(model)
            torch.manual_seed(seed); bag = network(architecture="bag")
            started = time.monotonic()
            training_reports[f"bag-{seed}"] = {**imitate(bag, reuse_training, epochs=protocol["epochs"], seed=seed,
                candidate_provider=library_env.candidates), "wall_seconds": time.monotonic()-started}
            models[f"bag-{seed}"] = bag
            if protocol.get("grounded_model"):
                torch.manual_seed(seed);ungrounded=ReuseNetwork()
                started=time.monotonic()
                training_reports[f"ungrounded-{seed}"]={**imitate(ungrounded,reuse_training,epochs=protocol["epochs"],seed=seed,
                    candidate_provider=library_env.candidates),"wall_seconds":time.monotonic()-started}
                models[f"ungrounded-{seed}"]=ungrounded
            for generation in range(1, protocol["generations"]+1):
                started, calls = time.monotonic(), library_env.invocations
                report = actor_critic(model, library_env, parts["train"], episodes=protocol["rl_episodes_per_generation"], seed=seed+generation)
                training_reports[f"rl{generation}-{seed}"] = {**report, "wall_seconds": time.monotonic()-started,
                                                              "all_lean_invocations": library_env.invocations-calls}
                models[f"rl{generation}-{seed}"] = copy.deepcopy(model)
        write(output / "training.json", training_reports)
        registry = []
        for name, model in models.items():
            sha = model.save(output / (name+".json"), {"protocol_sha256": digest(protocol),
                "source_manifest_sha256": digest(manifest), "training_sha256": digest(reuse_training),
                "library_sha256": library_env.library_sha256, "experimental": True})
            registry.append({"id": name, "checkpoint": name+".json", "sha256": sha,
                "parameters": sum(p.numel() for p in model.parameters()), "architecture": model.architecture,
                "network":"grounded" if model.__class__.__name__=="GroundedNetwork" else "reuse",
                "pcs_authority": False, "approval": "experimental-local"})
        old_folder = ROOT / "research/lean-learning-v2"
        old_registry = json.loads((old_folder / "registry.json").read_text())
        old_entry = next(m for m in old_registry["models"] if m["id"] == old_registry["selected_local_experiment"])
        old = ReasoningNetwork.load(old_folder / old_entry["checkpoint"], old_entry["sha256"])
        def random_rank(state, options):
            rng = random.Random(int(digest(state),16)^123)
            return [rng.random() for _ in options]
        evaluations = {}
        selected = None
        for split in ["validation", "final"]:
            policies = {"symbolic": (base, None), "previous_graph": (base, old.rank),
                "symbolic_discovery": (library_env, abstraction_priority), "random_discovery": (library_env, random_rank)}
            policies.update({name: (library_env, model.rank) for name, model in models.items()})
            evaluations[split] = {}
            for name, (env, rank) in policies.items():
                records = [measured_search(env, t, rank, protocol) for t in parts[split]]
                evaluations[split][name] = records
                print(split, name, metrics(records), flush=True)
            if split == "validation":
                eligible = [n for n in models if not n.startswith("untrained-")]
                selected = max(eligible, key=lambda n: (metrics(evaluations[split][n])["verified"],
                    -metrics(evaluations[split][n])["expansions"]))
                write(output / "registry.json", {"format": "pcs-reuse-model-registry-v1", "models": registry,
                    "selected_local_experiment": selected, "library_sha256": library_env.library_sha256,
                    "selection_frozen_before_final": True, "production_authority": False,
                    "environment": "AbstractionEnvironment"})
        independent = []
        # Independently rebuild and replay both selected and strongest symbolic
        # final proofs, irrespective of which one performs better.
        for name in [selected, "symbolic", "symbolic_discovery"]:
            for r in evaluations["final"][name]:
                if r["result"]["status"] != "verified": continue
                receipt = r["result"]["receipt"]
                replay_start = time.monotonic()
                if "library" in receipt:
                    checked = replay_library_receipt(r["goal"], receipt, cache=base.cache)
                else:
                    fresh = LeanEnvironment(cache=base.cache, timeout=30)
                    try: checked = fresh.verify(r["goal"], receipt["actions"])
                    finally: fresh.close()
                independent.append({"policy": name, "id": r["id"], "receipt_sha256": digest(checked),
                    "axioms": checked["kernel"]["axioms"], "wall_seconds": time.monotonic()-replay_start})
        write(output / "independent-final-replay.json", independent)
        (output / "evaluations.json.gz").write_bytes(gzip.compress(json.dumps(evaluations,sort_keys=True).encode(),mtime=0))
        summaries = {s: {n: {**metrics(rs), "all_lean_invocations": sum(r["cost"]["all_lean_invocations"] for r in rs),
            "wall_seconds_including_initial_state": sum(r["cost"]["wall_seconds_including_initial_state"] for r in rs)}
            for n, rs in es.items()} for s, es in evaluations.items()}
        summary = {"metrics": summaries, "selected": selected, "library_lemmas": len(library["entries"]),
            "discovery_candidates": len(discovery), "discovery_expansions": sum(r["expansions"] for r in discovery),
            "discovery_lean_invocations": sum(r.get("lean_invocations",0) for r in discovery),
            "library_construction_invocations": library_env.construction_invocations,
            "library_construction_seconds": library_env.construction_seconds,
            "training": metrics(reuse_training), "total_wall_seconds": time.monotonic()-start,
            "actual_lean_invocations": base.invocations+library_env.invocations+1,
            "independent_replay_seconds": sum(r["wall_seconds"] for r in independent),
            "training_parameters": {n: sum(p.numel() for p in m.parameters()) for n,m in models.items()},
            "torch": torch.__version__, "gpu_used": False, "financial_spend": 0,
            "claim": "Public authored mathematical transfer. Negative results retained. No novel mathematics or breakthrough established."}
        write(output / "summary.json", summary)
        write(output / "EVIDENCE_SHA256.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
        return summary
    finally:
        base.close()
        if library_env is not None: library_env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    reproduce(args.output)


if __name__ == "__main__": main()
