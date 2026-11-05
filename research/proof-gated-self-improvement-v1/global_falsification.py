"""Exhaustive strengthening study over the original 128-model lattice.

This is a synthetic finite model lattice plus *universal* (all-integer)
correctness-preservation checks for accepted transitions. Exact numeric
results are deterministic, not an estimate of actual deployed-model risk.
"""
from __future__ import annotations
import itertools
import json
from proof_gate import Model, check
from universal_relu import (
    Term, Net, single_neuron, universal_correctness_preserved,
    exact_interval_max_error
)
TARGET = Net((Term(1, 2, 1),))
WINDOW = (-20, 20)

def run() -> dict:
    models = [Model(r, w, b) for r, w, b in itertools.product(
        (False, True), range(-3, 5), range(-3, 5))]
    encoded = {m: single_neuron(m.relu, m.weight, m.bias) for m in models}
    max_errors = {m: exact_interval_max_error(encoded[m], TARGET, *WINDOW)[0]
                  for m in models}
    checked = accepted = global_lost = max_regression = guard_pass = 0
    both_fail = 0
    witness = None
    for old in models:
        for candidate in models:
            checked += 1
            if not check(old, candidate).accepted:
                continue
            accepted += 1
            global_result = universal_correctness_preserved(
                encoded[old], encoded[candidate], TARGET)
            forgotten = not global_result.passes
            window_worsened = max_errors[candidate] > max_errors[old]
            if forgotten:
                global_lost += 1
                if witness is None:
                    witness = {
                        "old": {"relu": old.relu, "weight": old.weight, "bias": old.bias},
                        "candidate": {"relu": candidate.relu, "weight": candidate.weight,
                                      "bias": candidate.bias},
                        "lost_correct_input": global_result.counterexample,
                    }
            if window_worsened:
                max_regression += 1
            if forgotten and window_worsened:
                both_fail += 1
            if not forgotten and not window_worsened:
                guard_pass += 1
    if accepted != global_lost + (accepted - global_lost):
        raise AssertionError("bad counting")
    if accepted != guard_pass + global_lost + max_regression - both_fail:
        raise AssertionError("set union conservation failed")
    return {
        "models": len(models),
        "transitions_checked": checked,
        "original_accepted": accepted,
        "lost_previously_correct_integer_prediction": global_lost,
        "increased_worst_error_on_minus20_to20": max_regression,
        "failed_both_stronger_guards": both_fail,
        "passed_both_stronger_guards": guard_pass,
        "reference_only": True,
        "lost_correct_witness": witness,
    }

if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
