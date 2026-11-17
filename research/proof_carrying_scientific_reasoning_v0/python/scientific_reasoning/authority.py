from __future__ import annotations

from .syntax import Authority

_RANK = {
    Authority.disputed: 0,
    Authority.hypothesis: 1,
    Authority.empiricalAsserted: 2,
    Authority.assumption: 2,
    Authority.derived: 3,
    Authority.mathVerified: 4,
}

# Finding G: commutative tie-break when ranks equal
_TIE = {
    Authority.disputed: 0,
    Authority.hypothesis: 1,
    Authority.assumption: 2,
    Authority.empiricalAsserted: 3,
    Authority.derived: 4,
    Authority.mathVerified: 5,
}


def rank(a: Authority) -> int:
    return _RANK[a]


def meet(a: Authority, b: Authority) -> Authority:
    if rank(a) < rank(b):
        return a
    if rank(b) < rank(a):
        return b
    return a if _TIE[a] <= _TIE[b] else b
