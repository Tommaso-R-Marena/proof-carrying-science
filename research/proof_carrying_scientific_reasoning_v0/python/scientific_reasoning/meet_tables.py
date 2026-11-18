"""Single source of truth for authority meet tables (Finding G).

Imported by both `authority.py` and `independent_checker/check_certificate_v1.py`
so the duplicated RANK/TIE tables cannot drift.
"""
from __future__ import annotations

RANK: dict[str, int] = {
    "disputed": 0,
    "hypothesis": 1,
    "empiricalAsserted": 2,
    "assumption": 2,
    "derived": 3,
    "mathVerified": 4,
}

TIE_ORDER: dict[str, int] = {
    "disputed": 0,
    "hypothesis": 1,
    "assumption": 2,
    "empiricalAsserted": 3,
    "derived": 4,
    "mathVerified": 5,
}


def meet_str(a: str, b: str) -> str:
    if a not in RANK or b not in RANK:
        raise ValueError(f"bad authority in meet: {a!r}, {b!r}")
    if RANK[a] < RANK[b]:
        return a
    if RANK[b] < RANK[a]:
        return b
    return a if TIE_ORDER[a] <= TIE_ORDER[b] else b
