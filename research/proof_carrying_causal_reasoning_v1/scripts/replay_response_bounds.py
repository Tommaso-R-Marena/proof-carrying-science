"""Cross-check the Lean interval receiver against independently enumerated SCM tables."""

import json
import subprocess
from collections import defaultdict
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEAN = ROOT / "lean"


def supported_laws(n):
    """Enumerate response multiplicities, recording actual randomized-trial observations."""
    inventory = defaultdict(dict)
    pairs = tuple(product((0, 1), repeat=2))
    for never in range(n + 1):
        for helped in range(n - never + 1):
            for harmed in range(n - never - helped + 1):
                table = (never, helped, harmed, n - never - helped - harmed)
                arms = [0, 0]
                effects = 0
                for (y0, y1), weight in zip(pairs, table, strict=True):
                    for treatment, factual_outcome in enumerate((y0, y1)):
                        arms[treatment] += weight * factual_outcome
                    if y1 > y0:
                        effects += weight
                inventory[tuple(arms)][effects] = table
    return inventory


def main():
    subprocess.run(["lake", "build", "PcsPccr.SharpResponseBounds"], cwd=LEAN, check=True,
                   stdout=subprocess.DEVNULL)
    cases = []
    expected = []
    counts = defaultdict(int)
    for n in range(1, 9):
        laws = supported_laws(n)
        for (c, r), effects in laws.items():
            counts["margin_pairs"] += 1
            counts["tables"] += len(effects)
            for lo, hi in product(range(n + 2), repeat=2):
                cases.append(f"{n} {c} {r} {lo} {hi}")
                if (lo, hi) == (min(effects), max(effects)):
                    if len(effects) != hi - lo + 1:
                        raise AssertionError("noncontiguous empirical effect set")
                    endpoints = (*effects[lo], *effects[hi])
                    expected.append("ACCEPT " + " ".join(map(str, endpoints)))
                    counts["accepted_exact_with_two_witnesses"] += 1
                else:
                    expected.append("REJECT")
                    counts["rejected_interval_mutations"] += 1
    for line in ["0 0 0 0 0", "2 3 1 0 1", "2 1 3 0 1"]:
        cases.append(line)
        expected.append("REJECT")
        counts["infeasible_populations"] += 1
    for line in ["", "2 1 1", "02 1 1 0 1", "2 1 1 0 -1", "2 1 1 0 1 extra",
                 "2 1 1 0 9999999999999999999", "2 1 1 1e1 1", "2 1 1 0  1"]:
        cases.append(line)
        expected.append("MALFORMED")
        counts["malformed_inputs"] += 1
    proc = subprocess.run(
        ["lake", "env", "lean", "--run", "CheckResponseBounds.lean"], cwd=LEAN,
        input="\n".join(cases) + "\n", capture_output=True, text=True, check=True,
    )
    actual = proc.stdout.splitlines()
    if len(actual) != len(expected):
        raise AssertionError(f"expected {len(expected)} replies, got {len(actual)}")
    for line, want, got in zip(cases, expected, actual, strict=True):
        if want != got:
            raise AssertionError(f"{line!r}: expected {want}, got {got}")
    print(json.dumps(dict(counts, checked_lines=len(expected), max_arm_size=8), sort_keys=True))


if __name__ == "__main__":
    main()
