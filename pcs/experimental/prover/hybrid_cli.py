"""Local controlled-English → typed IR → attributed hybrid Lean proof search.

No raw Lean input, arbitrary tactics, automatic training or production authority.
The frozen verified-memory checkpoint supplies proposals only. Completed proofs
are independently replayed; unsupported/ambiguous interpretation never succeeds.
"""
import argparse
import json
from pathlib import Path

from .induction_language import formalize, explain, parse_lean
from .induction_ir import canonical_declaration, digest


def run(statement, models="research/verified-memory-v1", *, budget=48, interpretation=None):
    if type(budget) is not int or not 6 <= budget <= 96:
        raise ValueError("hybrid budget must be an integer in [6,96]")
    language = formalize(statement)
    result = {"format": "pcs-local-hybrid-loop-v1", "formalization": language,
              "status": "unknown", "training_feedback": None,
              "pcs_authority": False, "production_authority": False,
              "automatic_training": False, "automatic_promotion": False}
    if language["status"] == "unsupported":
        return {**result, "status": "unsupported_formalization"}
    if language["status"] == "ambiguous" and interpretation is None:
        return {**result, "status": "ambiguous_interpretation"}
    index = 0 if interpretation is None else interpretation
    if type(index) is not int or not 0 <= index < len(language["candidates"]):
        raise ValueError("invalid selected interpretation")
    candidate = language["candidates"][index]
    goal = candidate["ir"]
    if digest(parse_lean(candidate["lean"])) != digest(canonical_declaration(goal)):
        raise RuntimeError("controlled statement roundtrip failed")
    from .memory_cli import load
    from .hybrid import solve
    registry, checkpoint, library, model = load(models)
    try:
        searched = solve(goal, library, model, budget=budget)
    except RuntimeError as error:
        return {**result, "status": "resource_exhaustion" if "resource exhaustion" in str(error) else "unknown",
                "reason": str(error), "explanation": explain(goal)}
    result.update(status=searched["status"], search=searched,
                  explanation=explain(goal), checkpoint_sha256=checkpoint["sha256"],
                  library_sha256=registry["library_sha256"], interpretation=index)
    if searched["status"] == "verified":
        result["training_feedback"] = {"original_statement": statement, "goal": goal,
                                       "receipt": searched["receipt"],
                                       "independent_replay": searched["independent_replay"],
                                       "winning_component": searched["winning_component"],
                                       "eligible_for_training": False,
                                       "required": "Cleared source license or consent, split contamination review and fresh intake replay."}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("statement")
    parser.add_argument("--models", default="research/verified-memory-v1")
    parser.add_argument("--budget", type=int, default=48)
    parser.add_argument("--interpretation", type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(args.statement, args.models, budget=args.budget, interpretation=args.interpretation)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "winning_component": result.get("search", {}).get("winning_component"),
                      "artifact": args.output}))
