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


def rank(a: Authority) -> int:
    return _RANK[a]


def meet(a: Authority, b: Authority) -> Authority:
    return a if rank(a) <= rank(b) else b
