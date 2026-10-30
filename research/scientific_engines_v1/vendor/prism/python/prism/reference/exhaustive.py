"""Independent exhaustive reference solvers for small instances.

Deliberately written without bitmasks, memoization or any code shared with the
Bellman solver, so that differential testing compares genuinely different
implementations of the same specification.
"""
from __future__ import annotations

from fractions import Fraction
from typing import FrozenSet, Iterator

INFTY = float("inf")  # only used as a sentinel for comparisons, never in arithmetic results


def _width(P, S: FrozenSet[int]) -> Fraction:
    if not S:
        return Fraction(0)
    vals = [P.q[m] for m in S]
    return max(vals) - min(vals)


def _cells(P, S, e):
    out = {}
    for m in S:
        out.setdefault(P.obs[m][e], set()).add(m)
    return {o: frozenset(c) for o, c in out.items()}


def reference_value(P, S, eps, used=frozenset()):
    """Minimax cost over all policies that never repeat an experiment on a path
    (repetition is provably useless).  Returns Fraction or None (= impossible)."""
    S = frozenset(S)
    eps = Fraction(eps)
    if _width(P, S) <= eps:
        return Fraction(0)
    best = None
    for e in range(P.k):
        if e in used:
            continue
        worst = Fraction(0)
        ok = True
        for c in _cells(P, S, e).values():
            v = reference_value(P, c, eps, used | {e})
            if v is None:
                ok = False
                break
            worst = max(worst, v)
        if ok:
            tot = P.cost[e] + worst
            if best is None or tot < best:
                best = tot
    return best


def enumerate_policies(P, S, used=frozenset(), depth=None) -> Iterator:
    """Enumerate *all* decision trees over feasible outcomes without repeated
    experiments on a path (tiny instances only)."""
    S = frozenset(S)
    yield "stop"
    if depth == 0:
        return
    for e in range(P.k):
        if e in used:
            continue
        cells = _cells(P, S, e)
        outs = sorted(cells)
        subs = [list(enumerate_policies(P, cells[o], used | {e},
                                        None if depth is None else depth - 1)) for o in outs]

        def product(i):
            if i == len(outs):
                yield {}
                return
            for sp in subs[i]:
                for rest in product(i + 1):
                    d = dict(rest)
                    d[outs[i]] = sp
                    yield d

        for nxt in product(0):
            yield {"e": e, "next": nxt}


def brute_force_value(P, S, eps):
    """Minimum worst-case cost over the explicit enumeration of all policies."""
    S = frozenset(S)
    eps = Fraction(eps)
    best = None
    count = 0
    for pol in enumerate_policies(P, S):
        count += 1
        worst = Fraction(0)
        ok = True
        for m in S:
            T, c = set(S), Fraction(0)
            p = pol
            while p != "stop":
                e = p["e"]
                o = P.obs[m][e]
                T = {x for x in T if P.obs[x][e] == o}
                c += P.cost[e]
                p = p["next"].get(o, "stop")
            if _width(P, frozenset(T)) > eps:
                ok = False
                break
            worst = max(worst, c)
        if ok and (best is None or worst < best):
            best = worst
    return best, count
