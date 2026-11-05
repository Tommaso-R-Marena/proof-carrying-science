"""Independent exact quadratic oracle; testing evidence, never proof authority.

On activation cells, old_error^2 - new_error^2 is quadratic. Check its exact
integer minimum, including unbounded tails. This avoids the certificate
producer's absolute-value partition and optimized activation sweep.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dominance import certificate
from receive import canonical, critical_sources, digest
from proof_gate import Model
from universal_relu import Net, Term, single_neuron

SEED = 202610170203


def minimum_witness(a, b, c, lo, hi):
    """Return an integer with Q(x)<0, or None when Q>=0 on the cell."""

    def value(x):
        return a * x * x + b * x + c

    def clip(x):
        if lo is not None:
            x = max(lo, x)
        if hi is not None:
            x = min(hi, x)
        return x

    points = {clip(0)}
    if lo is not None:
        points.add(lo)
    if hi is not None:
        points.add(hi)
    if a > 0:
        # Convex integer minimum lies at floor(vertex) or ceil(vertex), clipped.
        vertex = Fraction(-b, 2 * a)
        floor = vertex.numerator // vertex.denominator
        points.update((clip(floor), clip(floor + 1)))
    for x in sorted(points):
        if value(x) < 0:
            return x
    direction = None
    if lo is None and (a < 0 or (a == 0 and b > 0)):
        direction = -1
    elif hi is None and (a < 0 or (a == 0 and b < 0)):
        direction = 1
    if direction is not None:
        origin, step = clip(0), 1
        while value(origin + direction * step) >= 0:
            step *= 2
        return origin + direction * step
    return None


def quadratic_decision(old, new, target):
    cuts = set()
    # Independently construct activation thresholds with rational arithmetic.
    for n in (old, new, target):
        for t in n.terms:
            if not t.weight:
                continue
            root = Fraction(-t.bias, t.weight)
            if t.weight > 0:
                cuts.add(root.numerator // root.denominator)
            else:
                cuts.add(-((-root.numerator) // root.denominator) - 1)
    lows = [None] + [x + 1 for x in sorted(cuts)]
    highs = sorted(cuts) + [None]
    for lo, hi in zip(lows, highs, strict=True):
        x = lo if lo is not None else hi if hi is not None else 0
        # Original direct per-term branch scan, not the producer sweep.
        of, nf, tf = (n.affine(x) for n in (old, new, target))
        u, v = (of[0] - tf[0], of[1] - tf[1]), (nf[0] - tf[0], nf[1] - tf[1])
        witness = minimum_witness(
            u[0] ** 2 - v[0] ** 2,
            2 * (u[0] * u[1] - v[0] * v[1]),
            u[1] ** 2 - v[1] ** 2,
            lo,
            hi,
        )
        if witness is not None:
            assert abs(new.predict(witness) - target.predict(witness)) > abs(
                old.predict(witness) - target.predict(witness)
            )
            return False, witness
    return True, None


def run(output, decisions=None):
    output = Path(output)
    output.mkdir(mode=0o700, exist_ok=False)
    sources = critical_sources()
    own_sha = digest(Path(__file__))
    # Exhaust exact minima against direct enumeration, separately from nets.
    quadratic_cases = 0
    for a, b, c in itertools.product(range(-3, 4), repeat=3):
        for lo in range(-5, 6):
            for hi in range(lo, 6):
                w = minimum_witness(a, b, c, lo, hi)
                assert (w is None) == all(
                    a * x * x + b * x + c >= 0 for x in range(lo, hi + 1)
                )
                quadratic_cases += 1
    target = Net((Term(1, 2, 1),))
    models = [
        Model(r, w, b)
        for r, w, b in itertools.product((False, True), range(-3, 5), range(-3, 5))
    ]
    nets = [single_neuron(m.relu, m.weight, m.bias) for m in models]
    expected = None if decisions is None else json.loads(Path(decisions).read_text())
    if expected is not None:
        assert expected["models"] == [asdict(m) for m in models]
        assert len(expected["transitions"]) == 16384
    outcomes = {
        "bounded_quadratic_minima": quadratic_cases,
        "lattice_transitions": 0,
        "lattice_positive": 0,
        "random_multiunit_cases": 0,
        "mismatches": 0,
    }
    mismatch = []
    records = []

    def compare(ns, label):
        oracle, witness = quadratic_decision(*ns)
        c = certificate(*ns)
        if oracle != c["result"]["passes"]:
            mismatch.append(
                {"case": label, "oracle": oracle, "witness": witness, "certificate": c}
            )
        return oracle

    for i, old in enumerate(nets):
        for j, new in enumerate(nets):
            actual = compare((old, new, target), [i, j])
            if expected is not None:
                d = expected["transitions"][i * 128 + j]
                assert d["old"] == i and d["new"] == j and d["pointwise"] == actual
            outcomes["lattice_transitions"] += 1
            outcomes["lattice_positive"] += actual
    rng = random.Random(SEED)
    for i in range(1024):
        magnitude = 10**30 if i % 32 == 0 else 7
        ns = tuple(
            Net(
                tuple(
                    Term(*(rng.randint(-magnitude, magnitude) for _ in range(3)))
                    for _ in range(rng.randint(0, 8))
                ),
                rng.randint(-magnitude, magnitude),
            )
            for _ in range(3)
        )
        actual = compare(ns, ["random", i])
        records.append(actual)
        outcomes["random_multiunit_cases"] += 1
    outcomes["mismatches"] = len(mismatch)
    assert critical_sources() == sources and digest(Path(__file__)) == own_sha
    result = {
        "format": "pgsi-pointwise-quadratic-oracle-v1",
        "post_hoc": True,
        "seed": SEED,
        "source_sha256": sources,
        "oracle_source_sha256": own_sha,
        "kernel_decisions_sha256": None if decisions is None else digest(decisions),
        "outcomes": outcomes,
        "random_decisions_sha256": hashlib.sha256(canonical(records)).hexdigest(),
        "algorithm_kernel_proved": False,
        "promotion_authority": False,
        "external_scientific_validation": False,
        "mismatches": mismatch,
    }
    (output / "RESULT.json").write_bytes(canonical(result) + b"\n")
    print(json.dumps(result, sort_keys=True))
    if mismatch:
        raise AssertionError("Independent oracle mismatch: results retained")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--decisions", type=Path)
    args = p.parse_args()
    run(args.output, args.decisions)
