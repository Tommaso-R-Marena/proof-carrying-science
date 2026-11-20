"""Post-hoc slot audit. The reference builder never consumes public text or outputs."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from pathlib import Path

from research.proof_carrying_causal_reasoning_v1.external import typed_language as parser

HERE = Path(__file__).resolve().parent
CASES = "9c2b498c571a8a062cf52b3cb7e48492ba006f7dff5026df7dcc528e41a2c409"
PARSER = "5e94ee9f087d30a87339c72e8a38127f104d37eec7d5bf36d3b0ae7d9bb6988b"
DESIGN = "e459369bf5bc8290d954926cdd52c5fdcca5a74fe41b77eff3eeeb1df45b06c0"

# Existing parser-wide inference conventions. Keep them visible in a separate count.
CONVENTIONS = {"modular_intervention", "consistency", "positive_arm_support",
               "binary_events", "population_probabilities_rounded_to_percent"}


def references():
    """Transcribe the original author's parameter grid, row order and rational cell design."""
    result = {}
    pairs = [("bex", "lom"), ("pavo", "nuri"), ("tiv", "ezu")]
    for (x, y), (high, low), direction in product(pairs, [(80, 20), (24, 64)], ["increase", "decrease"]):
        marginal = ("marginal", x, None, 50)
        joint_pos = ("joint", y, x, high // 2)
        joint_neg = ("joint", y, "not " + x, low // 2)
        conditional_pos = ("conditional", y, x, high)
        conditional_neg = ("conditional", y, "not " + x, low)
        joint = [marginal, joint_pos, joint_neg]
        rates = [conditional_pos, conditional_neg]
        randomized = ["randomized:" + x]
        variants = [
            ("observational_association", "association", [], joint),
            ("confounded_intervention", "intervention", ["possible_unmeasured_common_cause"], joint),
            ("randomized", "intervention", randomized, rates),
            ("new_wording", "intervention", [*randomized, "fair_coin:" + x], rates),
            ("missing_cell", "intervention", randomized, [conditional_pos]),
            ("zero_conditioning", "association", [], [
                ("marginal", x, None, 0), ("joint", y, x, 0), ("joint", y, "not " + x, 25)]),
        ]
        for family, kind, background, facts in variants:
            slots = dict(kind=kind, treatment=x, outcome=y, direction=direction,
                         do_arms=(True, False) if kind == "intervention" else (),
                         stated_background=sorted(background), facts=sorted(facts))
            result[f"rc{len(result):03d}"] = family, slots
    return result


def slots(claim):
    facts = sorted((f.kind, f.event, f.condition, f.percent) for f in claim.facts)
    return dict(kind=claim.kind, treatment=claim.treatment, outcome=claim.outcome,
                direction=claim.direction, do_arms=claim.arms, facts=facts,
                stated_background=sorted(a for a in claim.assumptions if a not in CONVENTIONS))


def pinned(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"frozen input changed: {path.name}")
    return data


def report():
    cases = json.loads(pinned(HERE.parent / "cases.json", CASES))
    pinned(Path(parser.__file__), PARSER)
    expected = references()
    if [r["id"] for r in cases] != list(expected):
        raise ValueError("frozen design IDs and public corpus differ")
    outcomes, families, per_slot = Counter(), defaultdict(Counter), defaultdict(Counter)
    precision, conventions = Counter(), Counter()
    unparsed, mismatches, additional = defaultdict(list), {}, {}
    for row in cases:
        case_id = row["id"]
        family, gold = expected[case_id]
        if family != row["family"]:
            raise ValueError("frozen design family changed")
        # The parser sees public text only; no family, answer or adjudicated slots.
        try:
            claim = parser.interpret(row["public"])
        except parser.Unsupported as err:
            claim = None
            unparsed[str(err)].append(case_id)
        if claim is None:
            status = "no_claim"
            for key in gold:
                per_slot[key]["no_claim"] += 1
            precision["literal_facts_without_claim"] += len(gold["facts"])
        else:
            observed = slots(claim)
            diff = {k: {"expected": v, "observed": observed[k]} for k, v in gold.items() if v != observed[k]}
            for key in gold:
                per_slot[key]["mismatch" if key in diff else "match"] += 1
            if diff:
                mismatches[case_id] = diff
            if claim.edges or claim.latent or claim.methods:
                additional[case_id] = {"edges": claim.edges, "latent": claim.latent, "methods": claim.methods}
            status = "mismatch" if diff or case_id in additional else "all_match"
            conventions.update(a for a in claim.assumptions if a in CONVENTIONS)
            expected_facts = {(k, e, cond): Fraction(p, 100) for k, e, cond, p in gold["facts"]}
            for fact in claim.facts:
                literal = expected_facts.get((fact.kind, fact.event, fact.condition))
                if literal is None:
                    precision["unexpected_fact"] += 1
                    continue
                low, high = fact.bounds
                precision["matched_fact_keys"] += 1
                precision["matches_literal"] += Fraction(fact.percent, 100) == literal
                precision["contains_design_probability"] += low <= literal <= high
                precision["equals_exact_design_probability"] += low == literal == high
        outcomes[status] += 1
        families[family][status] += 1
    return {"pins": {"cases": CASES, "parser": PARSER, "original_design": DESIGN},
            "cases": len(cases), "claim_counts": outcomes, "counts_by_family": dict(families),
            "slot_counts": dict(per_slot), "probability_precision": precision,
            "inference_convention_counts": conventions, "unparsed_ids_by_reason": dict(unparsed),
            "slot_mismatches": mismatches, "unexpected_graph_or_methods": additional}


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
