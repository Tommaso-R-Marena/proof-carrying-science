"""Layered experimental update policy: Lean finite gate AND analytic checks.

IMPORTANT: The all-integer checker is Python reference code, not kernel-
verified. Adding a second check to a Lean-authorized update does not turn
that second check into a Lean proof or securely isolated policy.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from proof_gate import Model, check, check_with_lean
from universal_relu import (
    Term, Net, single_neuron, all_integer_equal,
    universal_correctness_preserved, exact_interval_max_error
)

TARGET = Net((Term(1, 2, 1),))

@dataclass(frozen=True)
class LayeredDecision:
    accepted_reference: bool
    reason: str
    benchmark_pass: bool
    universal_no_forgetting: bool
    old_window_max_error: int
    proposed_window_max_error: int
    universal_counterexample: int | None
    exact_target_all_integers: bool

def evaluate_layered(old: Model, candidate: Model,
                     *, low: int = -20, high: int = 20) -> LayeredDecision:
    if type(low) is not int or type(high) is not int or low > high:
        raise ValueError("invalid exact integer window")
    a = single_neuron(old.relu, old.weight, old.bias)
    b = single_neuron(candidate.relu, candidate.weight, candidate.bias)
    primary = check(old, candidate)
    global_preservation = universal_correctness_preserved(a, b, TARGET)
    old_max, _ = exact_interval_max_error(a, TARGET, low, high)
    new_max, _ = exact_interval_max_error(b, TARGET, low, high)
    equality = all_integer_equal(b, TARGET).passes
    if not primary.accepted:
        reason = "REJECT:finite_lean_policy_reference"
    elif not global_preservation.passes:
        reason = "REJECT:lost_previously_correct_integer_input"
    elif new_max > old_max:
        reason = "REJECT:bounded_window_max_error_regression"
    else:
        reason = "PASS:reference_only_lean_still_required"
    return LayeredDecision(
        reason.startswith("PASS"), reason,
        primary.accepted, global_preservation.passes, old_max, new_max,
        global_preservation.counterexample, equality
    )

def authorize_layered(old: Model, candidate: Model,
                      formal_dir: Path, *, low: int = -20,
                      high: int = 20) -> LayeredDecision:
    """Fail closed unless both Python supplemental checks and Lean agree.

    Protected promotion to a real runtime would still require a separate,
    immutable execution root and a verified implementation of the all-integer
    reasoning algorithm. This routine does not update the active model.
    """
    reference = evaluate_layered(old, candidate, low=low, high=high)
    if not reference.accepted_reference:
        return reference
    if not check_with_lean(old, candidate, formal_dir):
        return LayeredDecision(False, "REJECT:lean_unavailable_or_negative",
                               reference.benchmark_pass,
                               reference.universal_no_forgetting,
                               reference.old_window_max_error,
                               reference.proposed_window_max_error,
                               reference.universal_counterexample,
                               reference.exact_target_all_integers)
    return LayeredDecision(True, "ACCEPT:experimental_layered_checks",
                           reference.benchmark_pass,
                           reference.universal_no_forgetting,
                           reference.old_window_max_error,
                           reference.proposed_window_max_error,
                           reference.universal_counterexample,
                           reference.exact_target_all_integers)
