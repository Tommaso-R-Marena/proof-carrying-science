"""Calibration and uncertainty diagnostics with explicit assumptions."""

from __future__ import annotations

import math
import random
from typing import Any


def expected_calibration_error(probs: list[float], outcomes: list[int], *, bins: int = 10) -> dict[str, Any]:
    assert len(probs) == len(outcomes)
    if not probs:
        return {"ece": None, "status": "UNKNOWN", "assumption": "non-empty sample"}
    bins = max(1, bins)
    totals = [0] * bins
    correct = [0.0] * bins
    conf_sum = [0.0] * bins
    for p, y in zip(probs, outcomes):
        i = min(bins - 1, int(p * bins))
        totals[i] += 1
        correct[i] += float(y)
        conf_sum[i] += p
    ece = 0.0
    n = len(probs)
    for i in range(bins):
        if totals[i] == 0:
            continue
        acc = correct[i] / totals[i]
        conf = conf_sum[i] / totals[i]
        ece += (totals[i] / n) * abs(acc - conf)
    return {
        "ece": ece,
        "bins": bins,
        "n": n,
        "assumptions": [
            "Outcomes are binary labels in {0,1}.",
            "Probabilities are comparable across instances.",
            "ECE is descriptive, not a formal frequentist guarantee.",
        ],
    }


def bootstrap_mean_ci(values: list[float], *, n_boot: int = 500, seed: int = 0, alpha: float = 0.05) -> dict[str, Any]:
    if not values:
        return {"status": "UNKNOWN"}
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot) - 1]
    return {
        "mean": sum(values) / n,
        "ci": [lo, hi],
        "alpha": alpha,
        "n_boot": n_boot,
        "seed": seed,
        "assumptions": [
            "i.i.d. observations",
            "percentile bootstrap may undercover in small n",
            "dependent data invalidates this interval",
        ],
    }


def sensitivity_grid(base: float, deltas: list[float], fn) -> dict[str, Any]:
    rows = []
    for d in deltas:
        rows.append({"delta": d, "value": fn(base + d)})
    return {"base": base, "rows": rows, "assumptions": ["local one-at-a-time sensitivity only"]}


def paired_sign_test(a: list[float], b: list[float]) -> dict[str, Any]:
    if len(a) != len(b) or not a:
        return {"status": "UNKNOWN"}
    pos = sum(1 for x, y in zip(a, b) if x > y)
    neg = sum(1 for x, y in zip(a, b) if x < y)
    n = pos + neg
    if n == 0:
        return {"status": "OPEN", "reason": "all ties"}
    # exact binomial two-sided p under p=0.5
    def binom_cdf(k, n):
        # sum_{i=0}^k C(n,i) / 2^n
        s = 0.0
        for i in range(k + 1):
            s += math.comb(n, i)
        return s / (2**n)

    p = 2 * min(binom_cdf(min(pos, neg), n), 1 - binom_cdf(min(pos, neg), n) + math.comb(n, min(pos, neg)) / (2**n))
    p = min(1.0, p)
    return {
        "pos": pos,
        "neg": neg,
        "n_nonzero": n,
        "p_approx": p,
        "assumptions": ["i.i.d. paired differences; continuous noise; no multiple-comparison correction"],
    }
