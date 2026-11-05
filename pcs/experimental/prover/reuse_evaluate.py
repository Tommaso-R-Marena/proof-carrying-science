"""Cold-search-cache audit of frozen checkpoints; no training or reselection."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import random
import time

from .environment import LeanEnvironment, search
from .ir import digest
from .library import LibraryEnvironment, reuse_priority, replay_library_receipt
from .model import ReasoningNetwork
from .reuse_model import ReuseNetwork
from .reuse_experiment import metrics, write


def evaluate_frozen(folder, output):
    folder, output = Path(folder), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    registry = json.loads((folder / "registry.json").read_text())
    task_file = json.loads((folder / "tasks.json").read_text())
    tasks = [t for t in task_file["problems"] if t["split"] == "final"]
    protocol = {"format": "pcs-cold-reuse-audit-v1", "source_experiment": str(folder),
                "frozen_registry_sha256": digest(registry), "task_sha256": digest(tasks), "budget": 64, "beam": 4,
                "cache": "empty observation cache before every policy; persistent worker/module initialization outside online measurement",
                "no_training": True, "no_model_reselection": True,
                "evaluation_exposure": "second public final evaluation to repair cross-policy timing/cache bias; not a private blind holdout"}
    write(output / "protocol.json", protocol)
    write(output / "evaluator-source-manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
          for p in [Path(__file__), Path(__file__).with_name("library.py"), Path(__file__).with_name("environment.py")]})
    base = LeanEnvironment(timeout=30)
    lib = LibraryEnvironment(json.loads((folder / "library.json").read_text()), heldout=tasks, timeout=30)
    started = time.monotonic()
    try:
        def run(env, rank):
            env.observations.clear()
            calls = env.invocations
            begin = time.monotonic()
            results = [{**t, "result": search(env, t["goal"], rank, budget=64, beam=4)} for t in tasks]
            report = metrics(results)
            report.update(all_observe_and_verify_invocations=env.invocations-calls,
                          whole_evaluation_wall_seconds=time.monotonic()-begin)
            return results, report
        models_root = Path(__file__).resolve().parents[3] / "research/lean-learning-v2"
        old_registry = json.loads((models_root / "registry.json").read_text())
        entry = next(e for e in old_registry["models"] if e["id"] == old_registry["selected_local_experiment"])
        old = ReasoningNetwork.load(models_root / entry["checkpoint"], entry["sha256"])
        def random_rank(state, options):
            canonical = [[g["target"], [(l["name"], l["type"]) for l in g["locals"]]] for g in state["goals"]]
            rng = random.Random(int(digest(canonical), 16) ^ 123)
            return [rng.random() for _ in options]
        policies = {"symbolic": (base, None), "previous_graph": (base, old.rank),
                    "symbolic_reuse": (lib, reuse_priority), "random_reuse": (lib, random_rank),
                    "retrieval_only": (lib, lambda s, opts: [10 if str(a["argument"]).startswith("PCSReuseL") else 0 for a in opts])}
        for e in registry["models"]:
            model = ReuseNetwork.load(folder / e["checkpoint"], e["sha256"])
            policies[e["id"]] = (lib, model.rank)
        evaluations, summaries = {}, {}
        for name, (env, rank) in policies.items():
            evaluations[name], summaries[name] = run(env, rank)
            print(name, summaries[name], flush=True)
        chosen = registry["selected_local_experiment"]
        replays = []
        for record in evaluations[chosen]:
            if record["result"]["status"] == "verified":
                fresh = replay_library_receipt(record["goal"], record["result"]["receipt"], cache=base.cache)
                replays.append({"id": record["id"], "receipt_sha256": digest(fresh), "axioms": fresh["kernel"]["axioms"]})
        write(output / "independent-replay.json", replays)
        write(output / "summary.json", {"metrics": summaries, "selected_unchanged": chosen,
                "library_construction_invocations": lib.construction_invocations,
                "library_construction_seconds": lib.construction_seconds,
                "wall_seconds": time.monotonic()-started, "financial_spend": 0, "gpu_used": False})
        (output / "evaluations.json.gz").write_bytes(gzip.compress(json.dumps(evaluations,sort_keys=True,separators=(",",":")).encode(),mtime=0))
        write(output / "SHA256.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    finally:
        base.close(); lib.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    evaluate_frozen(a.experiment, a.output)
