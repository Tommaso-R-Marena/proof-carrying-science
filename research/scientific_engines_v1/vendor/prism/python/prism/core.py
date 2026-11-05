"""PRISM core: finite deterministic scientific problems with exact rational arithmetic.

Mirrors `PRISM/Models/Basic.lean`.  Version spaces are Python ints used as
bitmasks over model indices.  All arithmetic on queries and costs uses
`fractions.Fraction` (exact rationals); there is no floating point anywhere in
the decision procedures.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Sequence


INF = None  # the value "⊤" (impossible) is represented by None


def bits(mask: int) -> Iterable[int]:
    """Iterate over the indices of set bits (ascending)."""
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def popcount(mask: int) -> int:
    return bin(mask).count("1")


class Problem:
    """A finite deterministic problem.

    models:       list of model identifiers (strings)
    experiments:  list of experiment identifiers
    outcomes:     list (per experiment) of outcome identifiers
    obs[m][e]:    index into outcomes[e]
    q[m]:         Fraction (the query)
    cost[e]:      Fraction >= 0
    """

    def __init__(self, models: Sequence[str], experiments: Sequence[str],
                 outcomes: Sequence[Sequence[str]], obs: Sequence[Sequence[int]],
                 q: Sequence[Fraction], cost: Sequence[Fraction], meta: Optional[dict] = None):
        self.models = list(models)
        self.experiments = list(experiments)
        self.outcomes = [list(o) for o in outcomes]
        self.obs = [list(r) for r in obs]
        self.q = [Fraction(x) for x in q]
        self.cost = [Fraction(x) for x in cost]
        self.meta = dict(meta or {})
        n, k = len(self.models), len(self.experiments)
        if len(self.obs) != n or len(self.q) != n:
            raise ValueError("observation table / query length mismatch")
        if len(self.cost) != k or len(self.outcomes) != k:
            raise ValueError("experiment table length mismatch")
        for c in self.cost:
            if c < 0:
                raise ValueError("negative experiment cost")
        for m in range(n):
            if len(self.obs[m]) != k:
                raise ValueError(f"model {m}: observation row has wrong length")
            for e in range(k):
                if not (0 <= self.obs[m][e] < len(self.outcomes[e])):
                    raise ValueError(f"model {m}, experiment {e}: undeclared outcome")
        # cellmask[e][o] = set of all models predicting outcome o for experiment e
        self.cellmask: List[List[int]] = []
        for e in range(k):
            row = [0] * len(self.outcomes[e])
            for m in range(n):
                row[self.obs[m][e]] |= 1 << m
            self.cellmask.append(row)
        self.full = (1 << n) - 1

    # ------------------------------------------------------------------ basics
    @property
    def n(self) -> int:
        return len(self.models)

    @property
    def k(self) -> int:
        return len(self.experiments)

    def width(self, mask: int) -> Fraction:
        if mask == 0:
            return Fraction(0)
        lo = hi = None
        for m in bits(mask):
            v = self.q[m]
            if lo is None or v < lo:
                lo = v
            if hi is None or v > hi:
                hi = v
        return hi - lo

    def bounds(self, mask: int):
        """Return (lo, hi, argmin, argmax) — sharp bounds with attaining witnesses."""
        if mask == 0:
            raise ValueError("bounds of an empty version space are undefined (inconsistent)")
        lo = hi = None
        alo = ahi = None
        for m in bits(mask):
            v = self.q[m]
            if lo is None or v < lo:
                lo, alo = v, m
            if hi is None or v > hi:
                hi, ahi = v, m
        return lo, hi, alo, ahi

    def split(self, mask: int, e: int) -> Dict[int, int]:
        """Feasible outcomes of e on mask -> nonempty cells."""
        out = {}
        for o, cm in enumerate(self.cellmask[e]):
            c = mask & cm
            if c:
                out[o] = c
        return out

    def informative(self, mask: int, e: int) -> bool:
        cnt = 0
        for cm in self.cellmask[e]:
            if mask & cm:
                cnt += 1
                if cnt >= 2:
                    return True
        return False

    def obs_equiv(self, a: int, b: int) -> bool:
        return self.obs[a] == self.obs[b]

    def mask_of(self, idxs: Iterable[int]) -> int:
        r = 0
        for i in idxs:
            r |= 1 << i
        return r


# ---------------------------------------------------------------- policies
# A policy is either the string "stop" or a dict {"e": int, "next": {o: policy}}.
# Outcomes absent from "next" are treated as "stop" (exactly as a Lean policy whose
# continuation for that outcome is `.stop`).

STOP = "stop"


def simulate(P: Problem, pol, m: int, K: int):
    """Run policy with true model m from version space K.
    Returns (terminal mask, path cost, path length)."""
    cost = Fraction(0)
    length = 0
    while pol != STOP:
        e = pol["e"]
        o = P.obs[m][e]
        K &= P.cellmask[e][o]
        cost += P.cost[e]
        length += 1
        pol = pol["next"].get(o, STOP)
    return K, cost, length


def policy_size(pol) -> int:
    if pol == STOP:
        return 1
    return 1 + sum(policy_size(c) for c in pol["next"].values())


def policy_depth(pol) -> int:
    if pol == STOP:
        return 0
    return 1 + max([policy_depth(c) for c in pol["next"].values()] or [0])
