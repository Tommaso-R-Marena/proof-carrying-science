"""Independent certificate checker — does not import scientific_reasoning.evaluator.

Reimplements Hyp/AndI/AndE validation from the JSON certificate structure.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


RANK = {
    "disputed": 0,
    "hypothesis": 1,
    "empiricalAsserted": 2,
    "assumption": 2,
    "derived": 3,
    "mathVerified": 4,
}


def meet(a: str, b: str) -> str:
    return a if RANK[a] <= RANK[b] else b


class CheckError(Exception):
    pass


def _premise_map(premises: List[dict]) -> Dict[int, dict]:
    m: Dict[int, dict] = {}
    for p in premises:
        i = p["id"]
        if i in m:
            raise CheckError(f"duplicate premise id {i}")
        m[i] = p
    return m


def check(cert: dict) -> None:
    premises = cert["premises"]
    pm = _premise_map(premises)
    steps = cert["steps"]
    if not steps:
        raise CheckError("empty steps")
    # Replay steps: only validate local rule shapes against recorded judgments.
    for s in steps:
        rule = s["rule"]
        formula = s["formula"]
        support = s["support"]
        auth = s["authority"]
        if rule == "hyp":
            if len(support) != 1:
                raise CheckError("hyp support must be singleton")
            p = pm.get(support[0])
            if p is None:
                raise CheckError("hyp unknown premise")
            if p["formula"] != formula or p["authority"] != auth:
                raise CheckError("hyp mismatch")
        elif rule == "andI":
            if not (isinstance(formula, list) or isinstance(formula, tuple)):
                # JSON uses lists
                pass
            if not (isinstance(formula, (list, tuple)) and formula and formula[0] == "and"):
                raise CheckError("andI conclusion must be and")
            if auth not in RANK:
                raise CheckError("bad authority")
            # support must be concatenation of some prior step supports — checked weakly:
            if not support:
                raise CheckError("andI empty support")
        elif rule in ("andE1", "andE2"):
            if auth not in RANK:
                raise CheckError("bad authority")
        else:
            raise CheckError(f"unknown rule {rule}")
        # Authority non-escalation vs used premises
        for i in support:
            p = pm.get(i)
            if p is None:
                raise CheckError(f"support id {i} not in premises")
            if RANK[auth] > RANK[p["authority"]] and p["authority"] != "mathVerified":
                # derived may sit between; require auth rank <= max of supports' ranks
                pass
        max_rank = max(RANK[pm[i]["authority"]] for i in support)
        if RANK[auth] > max_rank:
            raise CheckError("authority escalation")
    last = steps[-1]
    if last["formula"] != cert["conclusion"]:
        raise CheckError("conclusion mismatch")
    if list(last["support"]) != list(cert["final_support"]):
        raise CheckError("final_support mismatch")
    if last["authority"] != cert["final_authority"]:
        raise CheckError("final_authority mismatch")


def check_path(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        check(json.load(f))


if __name__ == "__main__":
    import sys

    check_path(sys.argv[1])
    print("OK")
