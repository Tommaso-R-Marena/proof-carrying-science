"""Exact Bellman dynamic programming for the minimax experiment-cost value.

This is the *untrusted* search component mirroring the Lean definition
`Problem.value` (PRISM/Optimality/Bellman.lean).  Its outputs (policies,
adversary tables) are only trusted after independent checking.
"""
from __future__ import annotations

import sys
import time
from fractions import Fraction
from typing import Dict, Optional

from ..core import INF, STOP, Problem

sys.setrecursionlimit(100000)


def add(a, b):
    if a is INF or b is INF:
        return INF
    return a + b


def lt(a, b):
    """a < b on Fraction ∪ {INF}."""
    if a is INF:
        return False
    if b is INF:
        return True
    return a < b


def vmax(a, b):
    if a is INF or b is INF:
        return INF
    return a if a >= b else b


class BudgetExceeded(Exception):
    pass


class Bellman:
    """Memoized exact DP.  `memo` maps version-space masks to (value, best experiment)."""

    def __init__(self, P: Problem, eps, budget_states: Optional[int] = None,
                 time_limit: Optional[float] = None):
        self.P = P
        self.eps = Fraction(eps)
        self.memo: Dict[int, tuple] = {}
        self.budget = budget_states
        self.expanded = 0
        self.deadline = None if time_limit is None else time.perf_counter() + time_limit

    def _tick(self):
        self.expanded += 1
        if self.budget is not None and self.expanded > self.budget:
            raise BudgetExceeded()
        if self.deadline is not None and (self.expanded & 255) == 0 and time.perf_counter() > self.deadline:
            raise BudgetExceeded()

    def value(self, K: int):
        r = self.memo.get(K)
        if r is not None:
            return r[0]
        P = self.P
        if P.width(K) <= self.eps:
            self.memo[K] = (Fraction(0), None)
            return Fraction(0)
        self._tick()
        best, best_e = INF, None
        for e in range(P.k):
            cells = P.split(K, e)
            if len(cells) < 2:
                continue  # uninformative: never needed (Lean: exists_optimal_onlyInformative)
            ce = P.cost[e]
            if best is not INF and ce >= best:
                continue  # cannot strictly improve (all values are >= 0)
            worst = Fraction(0)
            for c in cells.values():
                worst = vmax(worst, self.value(c))
                if worst is INF or (best is not INF and ce + worst >= best):
                    break
            tot = add(ce, worst)
            if lt(tot, best):
                best, best_e = tot, e
        self.memo[K] = (best, best_e)
        return best

    # -------------------------------------------------------------- outputs
    def policy(self, K: int):
        """Extract an optimal policy (requires value(K) finite).

        Pruning in `value` only skips experiments that cannot *strictly* improve on
        the state's own running best, and child values are always computed without
        any inherited bound, so every memoized (value, argmin) pair is exact."""
        v = self.value(K)
        if v is INF:
            raise ValueError("no successful policy exists (value = ⊤)")
        return self._policy(K)

    def _policy(self, K: int):
        _, e = self.memo[K]
        if e is None:
            return STOP
        nxt = {}
        for o, c in self.P.split(K, e).items():
            self.value(c)
            nxt[o] = self._policy(c)
        return {"e": e, "next": nxt}

    def adversary_table(self, core: int, B):
        """Adversary certificate table for a lower bound B <= value(core).

        Entries are (mask, lb) with lb = min(value, B) > 0, closed under outcome
        choices that keep the adversary condition valid (Lean: `truncValue`,
        `adversary_complete`)."""
        P = self.P
        B = Fraction(B)

        def trunc(S):
            v = self.value(S)
            if v is INF:
                return B
            return min(v, B)

        table: Dict[int, Fraction] = {}
        stack = [core]
        while stack:
            S = stack.pop()
            if S in table:
                continue
            lb = trunc(S)
            if lb == 0:
                continue
            table[S] = lb
            for e in range(P.k):
                cells = P.split(S, e)
                if len(cells) < 2:
                    continue  # uninformative experiment: condition holds with cell = S
                ce = P.cost[e]
                chosen = None
                for c in cells.values():
                    if c in table and lb <= ce + table[c]:
                        chosen = c
                        break
                if chosen is None:
                    chosen = max(cells.values(), key=lambda c: (trunc(c), -bin(c).count("1")))
                    if not (lb <= ce + trunc(chosen)):
                        raise AssertionError("adversary extraction invariant violated")
                if trunc(chosen) > 0:
                    stack.append(chosen)
        return table


def solve(P: Problem, K: int, eps, budget_states=None):
    """Return (value, policy or None, solver)."""
    B = Bellman(P, Fraction(eps), budget_states)
    v = B.value(K)
    pol = None if v is INF else B.policy(K)
    return v, pol, B


class NaiveBellman(Bellman):
    """Straightforward DP baseline: memoized Bellman recursion over all informative
    experiments, without branch pruning."""

    def value(self, K: int):
        r = self.memo.get(K)
        if r is not None:
            return r[0]
        P = self.P
        if P.width(K) <= self.eps:
            self.memo[K] = (Fraction(0), None)
            return Fraction(0)
        self._tick()
        best, best_e = INF, None
        for e in range(P.k):
            cells = P.split(K, e)
            if len(cells) < 2:
                continue
            worst = Fraction(0)
            for c in cells.values():
                worst = vmax(worst, self.value(c))
            tot = add(P.cost[e], worst)
            if lt(tot, best):
                best, best_e = tot, e
        self.memo[K] = (best, best_e)
        return best
