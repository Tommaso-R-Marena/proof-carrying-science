"""Runnable English → trained Lean search → independent check → feedback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .environment import LeanEnvironment, search
from .ir import digest
from .language import formalize, explain, parse_lean


def run(statement, registry_dir=None, budget=96, interpretation=None, library_path=None, prepared_env=None):
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
        if registry.get("format") == "pcs-reuse-model-registry-v1":
            from .reuse_model import ReuseNetwork
            model = ReuseNetwork.load(folder / entry["checkpoint"], entry["sha256"])
            if library_path is None: library_path = folder / "library.json"
        else:
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
    owns_env = prepared_env is None
    if prepared_env is not None:
        from .library import LibraryEnvironment
        if type(prepared_env) is not LibraryEnvironment or not registry_dir or registry.get("format") != "pcs-reuse-model-registry-v1":
            raise ValueError("a receiver-created checked library environment requires its bound model registry")
        if prepared_env.library_sha256 != registry["library_sha256"]:
            raise ValueError("prepared environment library identity mismatch")
        env = prepared_env
        result["library"] = {"sha256": env.library_sha256, "lemmas": env.catalog,
                             "construction_invocations": env.construction_invocations,
                             "construction_seconds": env.construction_seconds, "construction_amortized": True}
    elif library_path is not None:
        from pcs.jsonio import strict_json_loads
        from .library import LibraryEnvironment
        raw = Path(library_path).read_bytes()
        if len(raw) > 256000: raise ValueError("library source exceeds bound")
        library = strict_json_loads(raw.decode())
        if registry_dir and registry.get("format") == "pcs-reuse-model-registry-v1" and digest(library) != registry["library_sha256"]:
            raise ValueError("model registry library identity mismatch")
        env = LibraryEnvironment(library, timeout=30)
        result["library"] = {"sha256": env.library_sha256, "lemmas": env.catalog,
                             "construction_invocations": env.construction_invocations,
                             "construction_seconds": env.construction_seconds}
    else:
        env = LeanEnvironment(timeout=30)
    try:
        observed = env.observe(candidate["ir"], [])
        roundtrip = parse_lean(candidate["lean"])
        if digest(roundtrip) != digest(candidate["ir"]):
            raise RuntimeError("typed statement roundtrip failed")
        result["elaboration"] = observed["states"][0]
        if registry_dir and registry.get("format") == "pcs-reuse-model-registry-v1":
            from .portfolio import search_portfolio
            solved = search_portfolio(env, candidate["ir"], model.rank, budget=budget, beam=4)
        else:
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
                "hint_exposure": "model proposals and optional symbolic fallback", "automatic_training_authorization": False,
                "human_consent": False, "source_license": "unspecified", "checker": env.version}
        return result
    except RuntimeError as error:
        result["status"] = "resource_exhaustion" if "resource exhaustion" in str(error) else "unknown"
        result["reason"] = str(error)
        result["training_feedback"] = None
        return result
    finally:
        if owns_env: env.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("statement")
    p.add_argument("--models")
    p.add_argument("--library", help="Typed checked-lemma library JSON; every entry is rebuilt through Lean")
    p.add_argument("--budget", type=int, default=96)
    p.add_argument("--interpretation", type=int)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = run(args.statement, args.models, args.budget, args.interpretation, args.library)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "model": result["model"], "artifact": args.output}))


if __name__ == "__main__":
    main()
