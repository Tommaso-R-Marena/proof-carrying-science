"""Baselines: one-step greedy planning and the best nonadaptive design."""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations

from ..core import INF, STOP, Problem, bits


def one_step_risk(P: Problem, K: int, e: int) -> Fraction:
    """R(K,e) = max over feasible outcomes of the posterior width."""
    return max(P.width(c) for c in P.split(K, e).values())


def greedy_policy(P: Problem, K: int, eps):
    """Recursive one-step greedy: pick the informative experiment minimizing
    (R(K,e), cost, index).  Returns policy or None if greedy gets stuck."""
    eps = Fraction(eps)

    def rec(S):
        if P.width(S) <= eps:
            return STOP
        cands = [e for e in range(P.k) if P.informative(S, e)]
        if not cands:
            return None
        e = min(cands, key=lambda e: (one_step_risk(P, S, e), P.cost[e], e))
        nxt = {}
        for o, c in P.split(S, e).items():
            sub = rec(c)
            if sub is None:
                return None
            nxt[o] = sub
        return {"e": e, "next": nxt}

    return rec(K)


def worst_cost(P: Problem, pol, K: int) -> Fraction:
    from ..core import simulate
    return max((simulate(P, pol, m, K)[1] for m in bits(K)), default=Fraction(0))


def best_nonadaptive(P: Problem, K: int, eps, max_k: int = 20):
    """Minimum-cost set T of experiments such that running all of T (in any order)
    leaves every model's class with width <= eps.  Exhaustive over subsets
    (only for k <= max_k).  Returns (cost, T) or (INF, None)."""
    eps = Fraction(eps)
    if P.k > max_k:
        raise ValueError("too many experiments for exhaustive nonadaptive search")
    best = (INF, None)
    exps = list(range(P.k))
    order = sorted(range(1 << P.k), key=lambda s: sum(P.cost[e] for e in exps if (s >> e) & 1))
    for s in order:
        T = [e for e in exps if (s >> e) & 1]
        c = sum((P.cost[e] for e in T), Fraction(0))
        if best[0] is not INF and c >= best[0]:
            break
        classes = {}
        for m in bits(K):
            classes.setdefault(tuple(P.obs[m][e] for e in T), []).append(P.q[m])
        if all(max(v) - min(v) <= eps for v in classes.values()):
            best = (c, T)
            break
    return best
