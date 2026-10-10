"""Explicitly authorized authored demonstration, checked intake and next weights.

No arbitrary public submission is authorized for training by this script.
Output must be a new directory; evaluation statements freeze before training.
"""
import argparse
import gzip
import json
from pathlib import Path

from pcs.experimental.prover.cli import run
from pcs.experimental.prover.corpus import tasks
from pcs.experimental.prover.data import intake_feedback
from pcs.experimental.prover.environment import LeanEnvironment, search
from pcs.experimental.prover.language import formalize
from pcs.experimental.prover.model import ReasoningNetwork, imitate


def main():
    p = argparse.ArgumentParser(); p.add_argument("--models", required=True); p.add_argument("--output", required=True)
    args = p.parse_args(); folder = Path(args.models); out = Path(args.output); out.mkdir(exist_ok=False)
    protocol = {"format": "pcs-feedback-cycle-v1", "source_license": "Apache-2.0",
                "source": "PCS authored demo", "training_epochs": 4, "automatic_selection": False,
                "evaluation_statements": ["For all propositions W and X, if W then (X implies (W and W)).",
                    "For all natural numbers v, (v + 0) + (0 + v) equals v + v."]}
    (out / "feedback-protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    result = run("For all propositions U and V, if (U and V) then (U and (U and V)).", folder)
    (out / "end-to-end.json").write_text(json.dumps(result, indent=2) + "\n")
    if result["status"] != "verified": raise RuntimeError("authored demonstration not verified")
    registry = json.loads((folder / "registry.json").read_text())
    entry = next(e for e in registry["models"] if e["id"] == registry["selected_local_experiment"])
    model = ReasoningNetwork.load(folder / entry["checkpoint"], entry["sha256"])
    env = LeanEnvironment(timeout=30)
    try:
        heldout = [t for t in tasks() if t["split"] != "train"]
        extra = [{"goal": formalize(s)["candidates"][0]["ir"]} for s in protocol["evaluation_statements"]]
        eligible = intake_feedback(env, result["training_feedback"], heldout + extra,
                                   license="Apache-2.0", source_revision=entry["sha256"])
        before = [search(env, t["goal"], model.rank, budget=96, beam=4) for t in extra]
        training = imitate(model, [eligible], epochs=4)
        checkpoint_sha = model.save(out / "feedback-generation.json", {"parent": entry["sha256"], "training": training})
        after = [search(env, t["goal"], model.rank, budget=96, beam=4) for t in extra]
        cycle = {"protocol": protocol, "eligible": eligible, "training": training,
                 "checkpoint_sha256": checkpoint_sha, "before": before, "after": after,
                 "measured_improvement": sum(x["status"] == "verified" for x in after) > sum(x["status"] == "verified" for x in before)}
        (out / "feedback-cycle.json.gz").write_bytes(gzip.compress(json.dumps(cycle, sort_keys=True).encode(), mtime=0))
        print(json.dumps({"proof_actions": len(result["search"]["receipt"]["actions"]),
                         "before": [x["status"] for x in before], "after": [x["status"] for x in after],
                         "checkpoint_sha256": checkpoint_sha}))
    finally: env.close()


if __name__ == "__main__": main()
