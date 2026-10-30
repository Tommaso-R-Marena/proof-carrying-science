"""Untrusted exact certificate producer for whole-integer error dominance.

No Python decision authorizes promotion. Positive and negative claims must be
replayed by the separate Lean checker. Flat integer ReLU sums only.
"""

from __future__ import annotations

from pathlib import Path
import sys

RESEARCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RESEARCH))
from affine_certificates import model_hash
from universal_relu import Cell, Net, Term, piecewise_cells


def nonnegative(cell: Cell, f: tuple[int, int]) -> bool:
    a, b = f
    if a == 0:
        return b >= 0
    if a > 0:
        return cell.low is not None and a * cell.low + b >= 0
    return cell.high is not None and a * cell.high + b >= 0


def absolute(cell: Cell, f: tuple[int, int]) -> tuple[int, int]:
    if nonnegative(cell, f):
        return f
    negative = (-f[0], -f[1])
    if nonnegative(cell, negative):
        return negative
    raise ValueError("Unresolved error sign: partition must be refined")


def refined_rows(old: Net, new: Net, target: Net):
    """Split activation cells further at BOTH error zero crossings.

    Using only activation boundaries is insufficient: absolute error can change
    affine branch strictly inside a cell. Zero belongs to the nonpositive branch
    of the sign partition, consistently with the original activation codec.
    """
    _, original = piecewise_cells(old, new, target)
    result = []
    for cell, forms in original:
        cuts = set()
        for a, b in forms[:2]:
            cut = Term(1, a - forms[2][0], b - forms[2][1]).cut()
            if (
                cut is not None
                and (cell.low is None or cell.low <= cut)
                and (cell.high is None or cut < cell.high)
            ):
                cuts.add(cut)
        low = cell.low
        for cut in sorted(cuts):
            result.append((Cell(low, cut), forms))
            low = cut + 1
        result.append((Cell(low, cell.high), forms))
    return result


def violation(cell: Cell, f: tuple[int, int]) -> int:
    a, b = f
    points = {cell.point()}
    if cell.low is not None:
        points.add(cell.low)
    if cell.high is not None:
        points.add(cell.high)
    if a > 0:
        points.add((-b - 1) // a)
    elif a < 0:
        points.add(b // (-a) + 1)
    for x in sorted(points):
        if cell.contains(x) and a * x + b < 0:
            return x
    raise AssertionError("No witness for claimed negative affine value")


def certificate(old: Net, new: Net, target: Net) -> dict:
    ns = (old, new, target)
    if any(type(n) is not Net for n in ns):
        raise TypeError("Exact integer models required")
    rows = refined_rows(*ns)
    witness = None
    for cell, (of, nf, tf) in rows:
        oa = absolute(cell, (of[0] - tf[0], of[1] - tf[1]))
        na = absolute(cell, (nf[0] - tf[0], nf[1] - tf[1]))
        margin = (oa[0] - na[0], oa[1] - na[1])
        if not nonnegative(cell, margin):
            witness = violation(cell, margin)
            if not abs(new.predict(witness) - target.predict(witness)) > abs(
                old.predict(witness) - target.predict(witness)
            ):
                raise AssertionError("Invalid dominance counterexample")
            break
    return {
        "format": "pgsi-pointwise-dominance-v1",
        "model_sha256": [model_hash(n) for n in ns],
        "cells": [
            {"low": c.low, "high": c.high, "affine": [list(f) for f in fs]}
            for c, fs in rows
        ],
        "result": {"passes": witness is None, "counterexample": witness},
        "kernel_proved": False,
    }
