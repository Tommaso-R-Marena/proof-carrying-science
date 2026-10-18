#!/usr/bin/env python3
"""Frozen micro-benchmarks for enclosure tightness and BnB cost."""

from __future__ import annotations

import json
import time
from fractions import Fraction
from pathlib import Path

from certnum.expr.eval import eval_interval, mean_value_enclosure
from certnum.expr.parse import parse_expr
from certnum.interval.interval import Interval
from certnum.opt.branch_bound import optimize
from certnum.root.isolation import isolate_roots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "results" / "microbench.json"


def main() -> None:
    results = []

    # Enclosure tightness: x*(1-x) on [0,1]
    e = parse_expr("x*(1-x)")
    box = {"x": Interval.mk(0, 1)}
    nat = eval_interval(e, box).interval
    mv = mean_value_enclosure(e, box).interval
    results.append(
        {
            "name": "dependency_x_one_minus_x",
            "natural_width": str(nat.width()),
            "mean_value_width": str(mv.width()),
            "mv_tighter_or_equal": mv.width() <= nat.width(),
        }
    )

    # Root isolation timing
    e2 = parse_expr("x^2 - 2")
    t0 = time.perf_counter()
    roots = isolate_roots(e2, "x", Interval.mk(0, 2), max_width=Fraction(1, 1000))
    dt = time.perf_counter() - t0
    results.append(
        {
            "name": "root_x2_minus_2",
            "n_certs": len(roots),
            "statuses": [r.status.name for r in roots],
            "seconds": dt,
        }
    )

    # Optimization
    e3 = parse_expr("(x-1)^2 + (y+1/2)^2")
    domain = {"x": Interval.mk(-1, 2), "y": Interval.mk(-2, 1)}
    t0 = time.perf_counter()
    opt = optimize(e3, domain, tol=Fraction(1, 20), method="natural")
    dt = time.perf_counter() - t0
    results.append(
        {
            "name": "opt_quadratic_2d",
            "L": str(opt.lower_bound),
            "U": str(opt.upper_bound),
            "gap": str(opt.gap),
            "subdivisions": opt.subdivisions,
            "seconds": dt,
        }
    )

    # Counterexample note: natural can beat MV on monotone problems
    e4 = parse_expr("x")
    box4 = {"x": Interval.mk(0, 1)}
    nat4 = eval_interval(e4, box4).interval
    mv4 = mean_value_enclosure(e4, box4).interval
    results.append(
        {
            "name": "mv_not_always_tighter",
            "natural_width": str(nat4.width()),
            "mean_value_width": str(mv4.width()),
            "note": "On identity, natural is exact; MV equals natural here.",
            "mv_strictly_tighter": mv4.width() < nat4.width(),
        }
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"results": results}, indent=2))
    print(json.dumps(results, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
