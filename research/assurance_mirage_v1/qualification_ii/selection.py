"""Repeated selection of noisy instruments with disjoint qualification and test draws."""

from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
from itertools import accumulate
from math import comb, sqrt
from random import Random
from statistics import mean, stdev


MASTER = "pcs-220-qualification-ii-18983"
PREFIXES = (1, 4, 16, 64)
TRIALS = 256
INCUMBENT = Fraction(3, 4)
METHODS = ("reuse", "split")


def stream(arm, trial, phase, who):
    key = f"{MASTER}|{arm}|{trial}|{phase}|{who}".encode()
    return Random(int.from_bytes(sha256(key).digest(), "big"))


def target(arm, trial, phase, size):
    rng = stream(arm, trial, phase, "target")
    return [bool(rng.getrandbits(1)) for _ in range(size)]


def instrument(arm, trial, phase, who, labels):
    rng = stream(arm, trial, phase, who)
    accuracy = arm if who else INCUMBENT
    threshold = accuracy * 16
    assert threshold.denominator == 1
    return [label if rng.getrandbits(4) < threshold.numerator else not label for label in labels]


def correct(readings, labels):
    return sum(x == y for x, y in zip(readings, labels, strict=True))


def choose(phase_scores, k, method):
    """Return a candidate index. Zero denotes retention of the incumbent."""
    screen = [sum(halves) if method == "reuse" else halves[0]
              for halves in phase_scores[:k + 1]]
    best = max(range(1, len(screen)), key=screen.__getitem__)
    if screen[best] <= screen[0]:
        return 0
    if method == "split" and phase_scores[best][1] <= phase_scores[0][1]:
        return 0
    return best


def trial(arm, trial_id):
    labels = target(arm, trial_id, "qualification", 32)
    scores = []
    for who in range(max(PREFIXES) + 1):
        vote = instrument(arm, trial_id, "qualification", who, labels)
        scores.append((correct(vote[:16], labels[:16]), correct(vote[16:], labels[16:])))
    winners = {(method, k): choose(scores, k, method) for method in METHODS for k in PREFIXES}

    held_out = target(arm, trial_id, "final", 256)
    final = {who: correct(instrument(arm, trial_id, "final", who, held_out), held_out)
             for who in set(winners.values()) | {0}}
    return {key: (int(who != 0), sum(scores[who]), sum(scores[0]), final[who], final[0])
            for key, who in winners.items()}


def binomial(n, p):
    return [comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(n + 1)]


@lru_cache(maxsize=None)
def strict_screen(n, k, p0, p1):
    """Exact promotion probability and expected positive gain in correct count."""
    incumbent = binomial(n, p0)
    cdf = list(accumulate(binomial(n, p1)))
    above = [1 - f ** k for f in cdf]
    promote = sum(mass * above[b] for b, mass in enumerate(incumbent))
    gain = sum(mass * sum(above[b:n]) for b, mass in enumerate(incumbent))
    return promote, gain


def theory(method, k, quality, panel_size=32):
    if method == "reuse":
        promote, gain = strict_screen(panel_size, k, INCUMBENT, quality)
    else:
        if panel_size % 2:
            raise ValueError("confirmation requires equal panel halves")
        half = panel_size // 2
        screen, screen_gain = strict_screen(half, k, INCUMBENT, quality)
        confirm, confirm_gain = strict_screen(half, 1, INCUMBENT, quality)
        promote = screen * confirm
        gain = screen_gain * confirm + screen * confirm_gain
    return {
        "promotion_probability": round(float(promote), 8),
        "panel_accuracy_gain": round(float(gain / panel_size), 8),
        "population_accuracy_gain": round(float((quality - INCUMBENT) * promote), 8),
    }


def summary(rows):
    promotes, panel, panel0, final, final0 = zip(*rows)
    changes = [(a - b) / 256 for a, b in zip(final, final0)]
    gains = [(a - b) / 32 for a, b in zip(panel, panel0)]
    return {
        "promotions": sum(promotes), "replicates": len(rows),
        "panel_correct_selected": sum(panel), "panel_correct_incumbent": sum(panel0),
        "final_correct_selected": sum(final), "final_correct_incumbent": sum(final0),
        "mean_panel_accuracy_gain": round(mean(gains), 8),
        "mean_final_accuracy_gain": round(mean(changes), 8),
        "panel_minus_final_gain": round(mean(gains) - mean(changes), 8),
        "mc_se_final_gain": round(stdev(changes) / sqrt(len(rows)), 8),
    }


def study():
    report = {}
    for name, quality in (("weaker", Fraction(11, 16)), ("equal", Fraction(3, 4))):
        trials = [trial(quality, i) for i in range(TRIALS)]
        report[name] = {
            method: {str(k): {"measured": summary([t[method, k] for t in trials]),
                              "analytic": theory(method, k, quality)} for k in PREFIXES}
            for method in METHODS
        }
    return report
