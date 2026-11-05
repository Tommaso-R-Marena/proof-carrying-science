"""Reproduce verified lemma reuse, graph retrieval, and sequential RL ablations."""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import subprocess
import time

import torch

from .environment import LeanEnvironment, search, _symbolic_priority
from .ir import digest
from .library import LibraryEnvironment, collect_library, replay_library_receipt
from .model import ReasoningNetwork, imitate, actor_critic
from .reuse_model import ReuseNetwork
from .reuse_corpus import benchmark


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def reuse_rank(state, options):
    """Strong deterministic baseline: prioritize checked reusable premises."""
    names = {e["name"] for e in state.get("available_lemmas", [])}
    target = state["goals"][0]["expression"] if state["goals"] else None
    # Do not starve necessary variable introductions or witness construction
    # when the retrieved list exceeds the beam width.
    variable_binder = target and target["kind"] == "forall" and target["children"][0]["kind"] in {"sort", "constant"}
    def score(a):
        if a["kind"] == "intro" and variable_binder: return 14.0
        if a["kind"] == "witness": return 13.0
        if a["kind"] == "apply" and a["argument"] in names: return 10.0
        return float(_symbolic_priority(state, a))
    return [score(a) for a in options]


def metrics(records):
    return {"verified": sum(r["result"]["status"] == "verified" for r in records), "tasks": len(records),
            "expansions": sum(r["result"]["expansions"] for r in records),
            "lean_invocations": sum(r["result"]["lean_invocations"] for r in records),
            "wall_seconds": sum(r["result"]["wall_seconds"] for r in records),
            "proof_actions": sum(len(r["result"]["receipt"]["actions"]) for r in records if r["result"]["receipt"]),
            "proofs_using_lemmas": sum(any(str(a["argument"]).startswith("PCSReuseL") for a in r["result"]["receipt"]["actions"])
                                      for r in records if r["result"]["receipt"])}


def reproduce(output, *, epochs=12, episodes=6, seeds=(17, 31, 47), budget=64):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    foundations, problems = benchmark()
    parts = {s: [p for p in problems if p["split"] == s] for s in ("train", "validation", "final")}
    protocol = {"format": "pcs-reuse-experiment-v1", "budget": budget, "depth": 18, "beam": 4,
                "seeds": list(seeds), "epochs": epochs, "rl_episodes_per_generation": episodes,
                "library": "training foundations only; exact alpha holdout exclusion; fresh kernel construction",
                "selection": "validation verified count, then expansions; no final-based tuning",
                "resource_accounting": "construction, training and final replay recorded separately; online prefix rebuilding is included in measured search wall time",
                "claims": "elementary public compositional transfer only; no novel mathematics or architectural superiority assumed"}
    write(output / "protocol.json", protocol)
    write(output / "tasks.json", {"foundations": foundations, "problems": problems})
    root = Path(__file__).resolve().parents[3]
    sources = [*Path(__file__).parent.glob("*.py"), root / "formal/PCSProofProbe.lean", root / "formal/PCSProofWorker.lean"]
    source_manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}
    write(output / "source-manifest.json", source_manifest)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    base = LeanEnvironment(timeout=30)
    lib = None
    try:
        print("Collecting reusable mathematical proofs through Lean", flush=True)
        library, construction = collect_library(base, foundations, budget=192,
                                                heldout=parts["validation"] + parts["final"], source_revision=revision)
        write(output / "library.json", library)
        write(output / "library-collection.json", construction)
        lib = LibraryEnvironment(library, heldout=parts["validation"] + parts["final"], timeout=30)
        write(output / "library-catalog.json", lib.catalog)
        def evaluate(env, tasks_, rank):
            records = []
            for t in tasks_:
                r = search(env, t["goal"], rank, budget=budget, beam=4)
                records.append({**t, "result": r})
            return records
        print("Collecting independent reuse training transitions", flush=True)
        training = evaluate(lib, parts["train"], reuse_rank)
        for r in training:
            if r["result"]["status"] == "verified":
                replay_library_receipt(r["goal"], r["result"]["receipt"], cache=base.cache)
        write(output / "training-trajectories.json", training)
        models, reports = {}, {}
        for seed in seeds:
            print(f"Training graph, bag, and sequential actor-critic generations: {seed}", flush=True)
            torch.manual_seed(seed)
            initial = ReuseNetwork()
            models[f"untrained-{seed}"] = copy.deepcopy(initial)
            graph = copy.deepcopy(initial)
            reports[f"graph-{seed}"] = imitate(graph, training, epochs=epochs, seed=seed, candidate_provider=lib.candidates)
            models[f"graph-{seed}"] = copy.deepcopy(graph)
            torch.manual_seed(seed)
            bag = ReuseNetwork(architecture="bag")
            reports[f"bag-{seed}"] = imitate(bag, training, epochs=epochs, seed=seed, candidate_provider=lib.candidates)
            models[f"bag-{seed}"] = bag
            for generation in [1, 2]:
                reports[f"rl{generation}-{seed}"] = actor_critic(graph, lib, parts["train"], episodes=episodes, seed=seed+generation)
                models[f"rl{generation}-{seed}"] = copy.deepcopy(graph)
        write(output / "training.json", reports)
        registry = []
        # All checkpoints frozen before evaluating validation or final tasks.
        for name, model in models.items():
            sha = model.save(output / f"{name}.json", {"library_sha256": lib.library_sha256,
                    "protocol_sha256": digest(protocol), "source_manifest_sha256": digest(source_manifest),
                    "training_sha256": digest(training), "status": "experimental"})
            registry.append({"id": name, "checkpoint": f"{name}.json", "sha256": sha,
                             "parameters": sum(p.numel() for p in model.parameters()), "architecture": model.architecture,
                             "approval": "experimental-local", "pcs_authority": False})
        evaluations = {}
        old_folder = root / "research/lean-learning-v2"
        old_registry = json.loads((old_folder / "registry.json").read_text())
        old_entry = next(e for e in old_registry["models"] if e["id"] == old_registry["selected_local_experiment"])
        old = ReasoningNetwork.load(old_folder / old_entry["checkpoint"], old_entry["sha256"])
        def random_rank(state, options):
            rng = random.Random(int(digest(state), 16) ^ 123)
            return [rng.random() for _ in options]
        def retrieval_only(state, options):
            return [10 if str(a["argument"]).startswith("PCSReuseL") else 0 for a in options]
        for split in ["validation", "final"]:
            print(f"Frozen evaluation: {split}", flush=True)
            evaluations[split] = {"symbolic": evaluate(base, parts[split], None),
                "previous_graph": evaluate(base, parts[split], old.rank),
                "symbolic_reuse": evaluate(lib, parts[split], reuse_rank),
                "retrieval_only": evaluate(lib, parts[split], retrieval_only),
                "random_reuse": evaluate(lib, parts[split], random_rank)}
            for name, model in models.items():
                evaluations[split][name] = evaluate(lib, parts[split], model.rank)
                print(split, name, metrics(evaluations[split][name]), flush=True)
        # Choose only on validation, then report the already frozen final run.
        summaries = {s: {n: metrics(rs) for n, rs in es.items()} for s, es in evaluations.items()}
        eligible = [n for n in models if not n.startswith("untrained-")]
        selected = max(eligible, key=lambda n: (summaries["validation"][n]["verified"], -summaries["validation"][n]["expansions"]))
        independent = []
        for record in evaluations["final"][selected]:
            if record["result"]["status"] == "verified":
                checked = replay_library_receipt(record["goal"], record["result"]["receipt"], cache=base.cache)
                independent.append({"id": record["id"], "receipt_sha256": digest(checked), "axioms": checked["kernel"]["axioms"]})
        write(output / "independent-final-replay.json", independent)
        write(output / "registry.json", {"format": "pcs-reuse-model-registry-v1", "models": registry,
                    "selected_local_experiment": selected, "library_sha256": lib.library_sha256, "production_authority": False})
        raw = json.dumps(evaluations, sort_keys=True, separators=(",", ":")).encode()
        (output / "evaluations.json.gz").write_bytes(gzip.compress(raw, mtime=0))
        summary = {"metrics": summaries, "selected": selected, "library_lemmas": len(lib.catalog),
                   "library_collection": metrics(construction), "library_construction_invocations": lib.construction_invocations,
                   "library_construction_seconds": lib.construction_seconds, "training": metrics(training),
                   "total_wall_seconds": time.monotonic()-start, "actual_lean_invocations": base.invocations+lib.invocations,
                   "gpu_used": False, "financial_spend": 0, "torch": torch.__version__, "independent_selected_final_proofs": len(independent)}
        write(output / "summary.json", summary)
        write(output / "SHA256.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
        return summary
    finally:
        base.close()
        if lib is not None: lib.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--episodes", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[17, 31, 47])
    parser.add_argument("--budget", type=int, default=64)
    args = parser.parse_args()
    reproduce(args.output, epochs=args.epochs, episodes=args.episodes, seeds=tuple(args.seeds), budget=args.budget)


if __name__ == "__main__": main()
