"""Independent authored meaning labels and real Lean elaboration/explanation."""
from pathlib import Path
import argparse
import gzip
import json

from pcs.experimental.prover.environment import LeanEnvironment
from pcs.experimental.prover.ir import binary as b, var, declaration, digest
from pcs.experimental.prover.language import formalize, parse_lean, explain
from pcs.experimental.prover.research import investigate


def main():
    p = argparse.ArgumentParser(); p.add_argument("--output", required=True); p.add_argument("--models", required=True)
    args = p.parse_args(); folder = Path(args.models)
    n, m, a, c = [var(s) for s in ["n", "m", "A", "B"]]
    zero = {"op": "number", "value": 0, "type": "Nat"}
    one = {"op": "number", "value": 1, "type": "Nat"}
    cases = [
        ("For every natural number n, (n + 0) * 1 equals n.", declaration(["n"], b("eq", b("mul", b("add", n, zero), one), n), "Nat")),
        ("For all natural numbers n and m, (n + m) * 1 equals m + n.", declaration(["n", "m"], b("eq", b("mul", b("add", n, m), one), b("add", m, n)), "Nat")),
        ("For all propositions A and B, if (A and B) then (A and (A and B)).", declaration(["A", "B"], b("implies", b("and", a, c), b("and", a, b("and", a, c))))),
        ("For all propositions A and B, not (A implies B) implies (not B).", declaration(["A", "B"], b("implies", {"op": "not", "arg": b("implies", a, c)}, {"op": "not", "arg": c}))),
        ("For all propositions A and B, (A implies B) implies (B implies A).", declaration(["A", "B"], b("implies", b("implies", a, c), b("implies", c, a)))),
        ("There exists a natural number n such that n equals 0.", declaration([], {"op": "exists", "name": "n", "type": "Nat", "body": b("eq", n, zero)})),
        ("For all natural numbers n, there exists a natural number m such that n equals m.", declaration(["n"], {"op": "exists", "name": "m", "type": "Nat", "body": b("eq", n, m)}, "Nat")),
        ("For all integers n and m, n + m equals m + n.", declaration(["n", "m"], b("eq", b("add", n, m), b("add", m, n)), "Int")),
    ]
    env = LeanEnvironment(timeout=30)
    try:
        labels = []
        for text, expected in cases:
            output = formalize(text)
            candidate = output["candidates"][0]
            if output["status"] != "supported" or candidate["ir"] != expected:
                raise RuntimeError("independent meaning label mismatch: " + text)
            observed = env.observe(expected, [])
            labels.append({"text": text, "expected_ir": expected, "generated": candidate,
                           "actual_goal": observed["states"][0], "roundtrip": parse_lean(candidate["lean"]) == expected})
        negative = []
        for text, expected in [("For all propositions A, B and C, A and B or C.", "ambiguous"),
             ("For all propositions A, B and C, if A and B or C then A.", "ambiguous"),
             ("For all real numbers x, x equals x.", "unsupported"),
             ("Every connected graph has a spanning tree.", "unsupported"),
             ("For all natural numbers n, n equals P.", "unsupported"),
             ("For all propositions P and P, P.", "unsupported")]:
            output = formalize(text)
            if output["status"] != expected: raise RuntimeError("abstention/ambiguity mismatch")
            negative.append({"text": text, "expected": expected, "output": output})
        evaluations = json.loads(gzip.decompress((folder / "evaluations.json.gz").read_bytes()))
        explanations = []
        for task in evaluations["final"]["graph-17"]:
            receipt = task["result"]["receipt"]
            if not receipt: continue
            fresh = env.verify(task["goal"], receipt["actions"])
            reconstructed = parse_lean(fresh["statement"])
            if reconstructed != task["goal"]: raise RuntimeError("actual declaration reconstruction mismatch")
            explanations.append({"id": task["id"], "kernel": fresh["kernel"], "explanation": explain(reconstructed)})
        plans = {"format": "pcs-research-plan-v1", "nodes": [
            {"id": "identity-add", "goal": declaration(["n"], b("eq", b("add", n, zero), n), "Nat"), "depends_on": []},
            {"id": "identity-multiply", "goal": declaration(["n"], b("eq", b("mul", n, one), n), "Nat"), "depends_on": ["identity-add"]},
            {"id": "combined", "goal": cases[0][1], "depends_on": ["identity-add", "identity-multiply"]}]}
        result = {"supported": labels, "negative_controls": negative, "actual_declaration_explanations": explanations,
                  "research_plan": plans, "research_execution": investigate(env, plans),
                  "human_review": False, "general_English_equivalence_proved": False,
                  "fidelity_method": "independently authored typed meaning labels; exact supported IR and actual Lean elaboration"}
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"supported_fidelity": len(labels), "ambiguity_abstention_controls": len(negative),
                          "actual_declarations_explained": len(explanations), "research_proofs": result["research_execution"]["verified_results"]}))
    finally: env.close()


if __name__ == "__main__": main()
