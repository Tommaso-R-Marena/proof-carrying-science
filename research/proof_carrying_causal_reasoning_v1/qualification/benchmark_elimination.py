"""Exact operator counts, independent reference masses and local median wall times."""

import argparse
import json
import platform
from fractions import Fraction
from functools import partial
from itertools import product
from pathlib import Path
from statistics import median
from time import perf_counter

from ..kernel.dag import CausalDAG
from ..kernel.elimination import exact_mass
from ..kernel.scm import BinarySCM

HERE = Path(__file__).with_name("elimination-results.json")


def benchmark_case(shape, size):
    names = tuple(f"x{i:03}" for i in range(size))
    # Index root 0, parents at larger indices. In an inward-oriented tree
    # the existing topological frontier processes all leaves before the root.
    if shape == "tree":
        parents = {
            v: [names[j] for j in (2 * i + 1, 2 * i + 2) if j < size]
            for i, v in enumerate(names)
        }
    else:
        parents = {v: list(names[i + 1 : i + 2]) for i, v in enumerate(names)}
    tables = {}
    for i, (v, ps) in enumerate(parents.items()):
        tables[v] = {
            bits: Fraction(
                1 + (i + sum((k + 2) * b for k, b in enumerate(bits))) % 7, 8
            )
            for bits in product((0, 1), repeat=len(ps))
        }

    def mechanism(v):
        return lambda env: tables[v][tuple(env[n] for n in parents[v])]

    scm = BinarySCM(CausalDAG.from_parents(parents), {v: mechanism(v) for v in names})
    probabilities = {}
    # Independent scalar oracle for disjoint subtrees (also chains). Never
    # use independence of parents for arbitrary DAGs with shared ancestors.
    for v in reversed(names):
        p = Fraction(0)
        for bits, cpt in tables[v].items():
            mass = cpt
            for bit, n in zip(bits, parents[v], strict=True):
                mass *= probabilities[n] if bit else 1 - probabilities[n]
            p += mass
        probabilities[v] = p
    return scm, names[0], probabilities[names[0]]


def timed(fn):
    sample = []
    for _ in range(3):
        start = perf_counter()
        result = fn()
        sample.append(perf_counter() - start)
    return result, round(1000 * median(sample), 3)


def suite():
    report = []
    for shape, sizes in (
        ("tree", (7, 15, 31, 63, 127, 255)),
        ("chain", (7, 15, 31, 63, 127, 255)),
    ):
        for size in sizes:
            scm, root, ref = benchmark_case(shape, size)
            ev = {root: 1}
            result, elapsed = timed(partial(exact_mass, scm, ev))
            if result.probability != ref:
                raise ValueError("mass differs from tree recurrence")
            row = {
                "shape": shape,
                "size": size,
                "mass": str(ref),
                "peak_bucket_variables": result.peak_bucket_variables,
                "assignments_scanned": result.assignments_scanned,
                "elimination_ms": elapsed,
            }
            if shape == "chain" or size <= 15:
                frontier, elapsed = timed(partial(scm.p_obs, ev))
                if frontier != ref:
                    raise ValueError("mass differs from tree recurrence")
                row["frontier_ms"] = elapsed
            if size <= 7:
                i = scm.graph.topological_order().index(root)
                full, elapsed = timed(
                    lambda scm=scm, i=i: sum(
                        v for bits, v in scm.observational_table().items() if bits[i]
                    )
                )
                if full != ref:
                    raise ValueError("mass differs from tree recurrence")
                row["whole_world_ms"] = elapsed
            report.append(row)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", action="store_true")
    args = p.parse_args()
    rows = suite()
    if args.record:
        with HERE.open("x") as out:
            json.dump(
                {
                    "python": platform.python_version(),
                    "machine": platform.machine(),
                    "rows": rows,
                },
                out,
                indent=2,
            )
            out.write("\n")
    else:

        def stable(rs):
            return [
                {k: v for k, v in row.items() if not k.endswith("_ms")} for row in rs
            ]

        if stable(rows) != stable(json.loads(HERE.read_bytes())["rows"]):
            raise ValueError("numeric or operator-count replay differs")
    for r in rows:
        print(
            r["shape"],
            r["size"],
            r["peak_bucket_variables"],
            r["assignments_scanned"],
            r["elimination_ms"],
            r.get("frontier_ms"),
        )
