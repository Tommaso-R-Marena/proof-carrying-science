"""Exhaustive falsification of out-of-corpus improvement on the SAME target.

Frozen scope: 128 models (2 activations x 8 weights x 8 biases). We evaluate all
16,384 old/new transitions, with the original seven-input gate and a held-out
domain containing the integers [-20,-4] and [4,20]. No randomness or fitting.
This is a synthetic distribution shift counterexample, not a statistical
estimate of deployment failures or a prospective blind experiment.
"""
from __future__ import annotations

import itertools
import json

from proof_gate import Model, DOMAIN, check, loss, target

HOLDOUT = tuple(range(-20, -3)) + tuple(range(4, 21))

def holdout_loss(m: Model) -> int:
    return sum(abs(m.predict(x) - target(x)) for x in HOLDOUT)

def run() -> dict:
    models = [Model(relu, w, b) for relu, w, b in
              itertools.product((False, True), range(-3, 5), range(-3, 5))]
    errors = {m: holdout_loss(m) for m in models}
    verified = 0
    regressions = 0
    best: tuple[int, Model, Model] | None = None
    for a in models:
        for b in models:
            if check(a, b).accepted:
                verified += 1
                delta = errors[b] - errors[a]
                if delta > 0:
                    regressions += 1
                    if best is None or delta > best[0]:
                        best = (delta, a, b)
    assert best is not None
    _, old, candidate = best
    return {
        "model_count": len(models),
        "transitions": len(models) ** 2,
        "accepted": verified,
        "accepted_with_heldout_regression": regressions,
        "holdout_inputs": list(HOLDOUT),
        "original_inputs": list(DOMAIN),
        "same_target_function": "relu(2*x+1)",
        "max_regression_witness": {
            "old": vars(old), "candidate": vars(candidate),
            "old_training_loss": loss(old),
            "candidate_training_loss": loss(candidate),
            "old_holdout_loss": errors[old],
            "candidate_holdout_loss": errors[candidate],
            "holdout_error_increase": errors[candidate] - errors[old],
        },
        "conclusion": "Finite certificate does not imply held-out improvement"
    }

if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
