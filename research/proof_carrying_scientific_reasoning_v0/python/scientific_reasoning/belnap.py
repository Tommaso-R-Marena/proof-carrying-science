"""Belnap FOUR conjunction matching Lean ScientificReasoning.Belnap."""
from __future__ import annotations

from enum import Enum
from typing import Tuple


class TV(str, Enum):
    none = "none"
    onlyTrue = "onlyTrue"
    onlyFalse = "onlyFalse"
    both = "both"


def has_t(v: TV) -> bool:
    return v in (TV.onlyTrue, TV.both)


def has_f(v: TV) -> bool:
    return v in (TV.onlyFalse, TV.both)


def of_tf(t: bool, f: bool) -> TV:
    if t and not f:
        return TV.onlyTrue
    if f and not t:
        return TV.onlyFalse
    if t and f:
        return TV.both
    return TV.none


def band(a: TV, b: TV) -> TV:
    return of_tf(has_t(a) and has_t(b), has_f(a) or has_f(b))


def designated(v: TV) -> bool:
    return has_t(v)


ALL = (TV.none, TV.onlyTrue, TV.onlyFalse, TV.both)

# Expected 4×4 table (row a, col b) under component semantics
EXPECTED = {
    (TV.none, TV.none): TV.none,
    (TV.none, TV.onlyTrue): TV.none,
    (TV.none, TV.onlyFalse): TV.onlyFalse,
    (TV.none, TV.both): TV.onlyFalse,
    (TV.onlyTrue, TV.none): TV.none,
    (TV.onlyTrue, TV.onlyTrue): TV.onlyTrue,
    (TV.onlyTrue, TV.onlyFalse): TV.onlyFalse,
    (TV.onlyTrue, TV.both): TV.both,
    (TV.onlyFalse, TV.none): TV.onlyFalse,
    (TV.onlyFalse, TV.onlyTrue): TV.onlyFalse,
    (TV.onlyFalse, TV.onlyFalse): TV.onlyFalse,
    (TV.onlyFalse, TV.both): TV.onlyFalse,
    (TV.both, TV.none): TV.onlyFalse,
    (TV.both, TV.onlyTrue): TV.both,
    (TV.both, TV.onlyFalse): TV.onlyFalse,  # counterexample to old Lean table
    (TV.both, TV.both): TV.both,
}
