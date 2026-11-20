import json
from dataclasses import replace

from research.proof_carrying_causal_reasoning_v1.qualification.language_ii.reviewer.slot_fidelity import replay


def test_pinned_original_output_matches_record():
    result = replay.report()
    assert result == json.loads((replay.HERE / "results.json").read_bytes())
    assert result["claim_counts"] == {"all_match": 48, "no_claim": 24}
    assert sum(result["probability_precision"][k] for k in
               ("literal_facts_without_claim", "matched_fact_keys")) == 168


def test_mutated_claims_and_added_assumptions_are_detected(monkeypatch):
    interpret = replay.parser.interpret

    def mutated(public):
        claim = interpret(public)
        modified = replace(claim.facts[0], percent=(claim.facts[0].percent + 1) % 101)
        return replace(claim, treatment=claim.outcome, outcome=claim.treatment,
                       direction="decrease" if claim.direction == "increase" else "increase",
                       facts=(modified, *claim.facts[1:]),
                       assumptions=(*claim.assumptions, "invented_exchangeability"))

    monkeypatch.setattr(replay.parser, "interpret", mutated)
    result = replay.report()
    assert result["claim_counts"] == {"mismatch": 48, "no_claim": 24}
    assert all(set(m) == {"treatment", "outcome", "direction", "facts", "stated_background"}
               for m in result["slot_mismatches"].values())
    assert result["probability_precision"]["matches_literal"] == 60


def test_negated_arm_and_intervention_vs_observation_are_scored(monkeypatch):
    interpret = replay.parser.interpret

    def mutated(public):
        claim = interpret(public)
        facts = tuple(replace(f, condition=f.condition.removeprefix("not "))
                      if f.condition and f.condition.startswith("not ") else f for f in claim.facts)
        return replace(claim, kind="association", arms=(), facts=facts)

    monkeypatch.setattr(replay.parser, "interpret", mutated)
    result = replay.report()
    assert result["slot_counts"]["do_arms"]["mismatch"] == 24
    assert result["slot_counts"]["kind"]["mismatch"] == 24
    assert result["slot_counts"]["facts"]["mismatch"] == 36
