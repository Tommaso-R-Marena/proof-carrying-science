"""Runnable English → trained Lean search → independent check → feedback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .environment import LeanEnvironment, search
from .ir import digest
from .language import formalize, explain, parse_lean


def run(statement, registry_dir=None, budget=96, interpretation=None):
    ranker, model, model_id = None, None, "symbolic"
    if registry_dir:
        from .model import ReasoningNetwork
        from .formalization_model import FormalizationRanker
        folder = Path(registry_dir)
        registry = json.loads((folder / "registry.json").read_text())
        model_id = registry["selected_local_experiment"]
        entry = next(e for e in registry["models"] if e["id"] == model_id)
        # Only a basename in the receiver-selected registry folder may resolve.
        if Path(entry["checkpoint"]).name != entry["checkpoint"]:
            raise ValueError("invalid registry checkpoint path")
        model = ReasoningNetwork.load(folder / entry["checkpoint"], entry["sha256"])
        config = folder / "formalization-training.json"
        if config.exists():
            metadata = json.loads(config.read_text())
            ranker = FormalizationRanker.load(folder / "formalization.json", metadata["checkpoint_sha256"])
    language = formalize(statement, ranker.rank if ranker else None)
    result = {"format": "pcs-lean-learning-loop-v1", "formalization": language,
              "model": model_id, "pcs_authority": False, "training_feedback": None}
    if language["status"] == "unsupported":
        result["status"] = "unsupported_formalization"
        return result
    if language["status"] == "ambiguous" and interpretation is None:
        result["status"] = "ambiguous_interpretation"
        return result
    chosen = 0 if interpretation is None else interpretation
    if type(chosen) is not int or not 0 <= chosen < len(language["candidates"]):
        raise ValueError("invalid selected interpretation")
    candidate = language["candidates"][chosen]
    env = LeanEnvironment()
    try:
        observed = env.observe(candidate["ir"], [])
        roundtrip = parse_lean(candidate["lean"])
        if digest(roundtrip) != digest(candidate["ir"]):
            raise RuntimeError("typed statement roundtrip failed")
        result["elaboration"] = observed["states"][0]
        solved = search(env, candidate["ir"], model.rank if model else None, budget=budget, beam=4)
        result["search"] = solved
        result["status"] = solved["status"]
        result["explanation"] = explain(candidate["ir"])
        from .data import claim_graph
        result["pcs_claim_graph"] = claim_graph(statement, candidate["ir"], solved["receipt"])
        if solved["status"] == "verified":
            # Eligibility is a proposal; ingestion rechecks and evaluates split
            # contamination. User intent/consent is never inferred from a proof.
            result["training_feedback"] = {"format": "pcs-intelligence-data-v1", "goal": candidate["ir"],
                "goal_sha256": digest(candidate["ir"]), "original_statement": statement,
                "formal_statement": candidate["lean"], "receipt": solved["receipt"],
                "states": solved["states"], "model": model_id, "split": "unassigned",
                "hint_exposure": "model proposals", "automatic_training_authorization": False,
                "human_consent": False, "source_license": "unspecified", "checker": env.version}
        return result
    finally:
        env.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("statement")
    p.add_argument("--models")
    p.add_argument("--budget", type=int, default=96)
    p.add_argument("--interpretation", type=int)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = run(args.statement, args.models, args.budget, args.interpretation)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "model": result["model"], "artifact": args.output}))


if __name__ == "__main__":
    main()
