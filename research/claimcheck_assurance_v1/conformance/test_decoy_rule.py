"""The decoy rule as implemented against its Lean model (`ClaimCheckAssurance/Selection.lean`).

The implemented rule (`space.decoy_offsets`, `space.TokenAnalysis.rate`, `policy.TAU`) confirms a
printed number only if it is reproducible and (decoys reproduced + 1) / (decoys + 1) <= TAU, over the
100 nearest comparable numbers.  The model confirms position c only if it is reproducible and at
most k = 2 reproducible positions lie within 50 of it.  For many patterns of reproducible comparable
numbers, in two printed formats, this test checks with the real functions that
  1. every number the implemented rule confirms is confirmable in the model, so the proved bounds
     (at most 2 in any 51 consecutive comparable numbers) apply to the implemented rule;
  2. the implemented rule reaches the model's worst case: with reproducible pairs every 52 numbers
     about 3.8 % of comparable numbers are confirmable, not 2 %.
Tests, not proofs.  Run: python3 research/claimcheck_assurance_v1/conformance/test_decoy_rule.py
"""
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.claimcheck_v1_1.policy import TAU  # noqa: E402
from research.claimcheck_v1_1.space import TokenAnalysis, decoy_offsets  # noqa: E402

R_WINDOW, K = 50, 2


def implemented(R: set, j: int, unit: Fraction) -> bool:
    """The policy's rule for the printed number j * unit, with the real decoy and rate functions."""
    if j not in R:
        return False
    offsets = decoy_offsets(j * unit, unit / 2)
    hits = sum(1 for o in offsets if j + o in R)
    analysis = TokenAnalysis(eligible_readings=0, truncated=False, matching=[], decoys=len(offsets), decoys_reproduced=hits)
    return analysis.rate <= TAU


def model(R: set, j: int, lo: int) -> bool:
    """`confirmable R 50 2 (j - lo)` of Selection.lean (window clipped at the first comparable number)."""
    p = j - lo
    if j not in R:
        return False
    return sum(1 for q in range(max(0, p - R_WINDOW), p + R_WINDOW + 1) if q + lo in R) <= K


def patterns(lo: int, hi: int, rng: random.Random):
    span = range(lo, hi + 1)
    for density in (0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.3):
        for _ in range(6):
            yield f"random {density}", {j for j in span if rng.random() < density}
    for gap in (40, 51, 52, 53, 60, 101, 102):
        for width in (1, 2, 3):
            yield f"blocks of {width} every {gap}", {j for j in span if (j - lo) % gap < width}
    for _ in range(20):
        centres = rng.sample(list(span), 8)
        yield "clusters", {j for c in centres for j in range(c - rng.randrange(0, 4), c + rng.randrange(1, 5)) if lo <= j <= hi}


def main():
    rng = random.Random(20261115)
    report = {"formats": {}, "violations": 0}
    for name, lo, hi, unit in (("three-digit integers", 100, 999, Fraction(1)), ("x.xx", 100, 999, Fraction(1, 100))):
        worst, checked = None, 0
        for label, R in patterns(lo, hi, rng):
            impl = [j for j in range(lo, hi + 1) if implemented(R, j, unit)]
            for j in impl:
                checked += 1
                if not model(R, j, lo):
                    report["violations"] += 1
                    raise AssertionError((name, label, j))
            # the proved count bound, for the 900 comparable numbers of the format
            assert len(impl) <= (900 // 51 + 1) * K, (name, label, len(impl))
            if label == "blocks of 2 every 52":
                worst = {"confirmable": len(impl), "of": hi - lo + 1, "share": round(len(impl) / (hi - lo + 1), 4)}
        report["formats"][name] = {"confirmations_checked_against_the_model": checked, "pairs_every_52": worst}
        assert worst["share"] > 0.03, "the implemented rule no longer reaches the worst case: update Selection.lean's note"
    report["passed"] = True
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
