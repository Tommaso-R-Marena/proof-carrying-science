"""Core-guided optimality-sandwich search (counterexample-guided refinement).

Goal: certify an exactly optimal adaptive policy for a (possibly huge) version
space K while running the expensive Bellman DP only on a small *core* C ⊆ K.

Loop:
  1. Solve the core exactly: v = value(C), policy π optimal for C,
     adversary table A proving value(C) >= v.
  2. Validate π on the over-approximation K_hi ⊇ K by simulation (linear in |K_hi|
     times the policy depth — no sub-version-space enumeration).
  3. If π succeeds on K_hi with worst-case cost <= v: the sandwich theorem
     (Lean: `checkSandwich_sound`) gives exact optimality on every K with
     C ⊆ K ⊆ K_hi.  Emit certificate (π, v, C, A).
  4. Otherwise add counterexample models to C and repeat.  Each round adds at
     least one new model (proved in docs/THEOREMS.md, "progress lemma"), so the
     loop terminates after at most |K| rounds; in the worst case C = K and the
     method degenerates to plain DP (plus overhead) — this is reported honestly
     in the benchmarks.

If value(C) = ⊤ the core already contains an observationally equivalent pair with
query gap > ε; we return a two-model impossibility certificate (valid for K by
monotonicity, Lean: `impossibility`).
"""
from __future__ import annotations

import time
from fractions import Fraction
from typing import Optional

from ..core import INF, STOP, Problem, bits, popcount
from .bellman import Bellman, BudgetExceeded


def find_equiv_gap_pair(P: Problem, K: int, eps: Fraction):
    """Two observationally equivalent models in K with query gap > eps, or None."""
    classes = {}
    for m in bits(K):
        sig = tuple(P.obs[m])
        lo_hi = classes.get(sig)
        if lo_hi is None:
            classes[sig] = [m, m]
        else:
            if P.q[m] < P.q[lo_hi[0]]:
                lo_hi[0] = m
            if P.q[m] > P.q[lo_hi[1]]:
                lo_hi[1] = m
    for lo, hi in classes.values():
        if P.q[hi] - P.q[lo] > eps:
            return hi, lo
    return None


def validate(P: Problem, pol, K: int, bound: Fraction, eps: Fraction, core: int = 0,
             limit: Optional[int] = None):
    """Simulate pol on every model of K.  Return a list of counterexample models
    not in `core` (empty iff pol succeeds on K with worst-case cost <= bound).

    Progress lemma: if pol succeeds on `core` with cost <= bound, every failure
    yields at least one model outside the core: a cost failure happens only for
    models outside the core, and a width failure at terminal set T means the
    extreme-query models of T cannot both lie in the core (pol succeeds there)."""
    # Push the whole set K down the policy tree once (each model visits one
    # root-to-leaf path), evaluating width once per leaf: O(|K| * depth) bit
    # operations plus O(|leaf|) per leaf, instead of per-model terminal scans.
    bad = []
    stack = [(pol, K, Fraction(0))]
    while stack:
        p, T, c = stack.pop()
        if p == STOP:
            if c > bound:
                cand = [x for x in bits(T) if not (core >> x) & 1][:1]
            elif P.width(T) > eps:
                lo, hi, alo, ahi = P.bounds(T)
                cand = [x for x in (alo, ahi) if not (core >> x) & 1]
                if not cand:
                    cand = [x for x in bits(T) if not (core >> x) & 1][:1]
            else:
                continue
            bad.extend(cand)
            if limit is not None and len(bad) >= limit:
                break
            continue
        e = p["e"]
        c2 = c + P.cost[e]
        for o, cell in P.split(T, e).items():
            stack.append((p["next"].get(o, STOP), cell, c2))
    return bad


def initial_core(P: Problem, K: int):
    lo, hi, alo, ahi = P.bounds(K)
    return (1 << alo) | (1 << ahi)


def sandwich_certify(P: Problem, K: int, eps, init_core: Optional[int] = None,
                     max_rounds: int = 10_000, budget_states: Optional[int] = None,
                     time_limit: Optional[float] = None, limit: Optional[int] = 2):
    """Returns a dict with status in {"optimal","impossible","unresolved"}."""
    eps = Fraction(eps)
    t0 = time.perf_counter()
    if K == 0:
        return {"status": "inconsistent"}
    dp = Bellman(P, eps, budget_states, time_limit)
    core = init_core if init_core is not None else initial_core(P, K)
    core &= K
    rounds = 0
    best_lower = Fraction(0)
    best_upper = None
    while rounds < max_rounds:
        rounds += 1
        try:
            v = dp.value(core)
        except BudgetExceeded:
            return {"status": "unresolved", "lower": best_lower, "upper": best_upper,
                    "rounds": rounds, "core_size": popcount(core),
                    "dp_states": dp.expanded, "reason": "state budget exhausted"}
        if v is INF:
            pair = find_equiv_gap_pair(P, core, eps)
            assert pair is not None
            return {"status": "impossible", "pair": pair, "rounds": rounds,
                    "core_size": popcount(core), "dp_states": dp.expanded}
        best_lower = max(best_lower, v)
        pol = dp.policy(core)
        if time_limit is not None and time.perf_counter() - t0 > time_limit:
            return {"status": "unresolved", "lower": best_lower, "upper": best_upper,
                    "rounds": rounds, "core_size": popcount(core), "dp_states": dp.expanded,
                    "reason": "time limit"}
        bad = validate(P, pol, K, v, eps, core, limit)
        if not bad:
            table = dp.adversary_table(core, v)
            return {"status": "optimal", "value": v, "policy": pol, "core": core,
                    "adversary": table, "rounds": rounds, "core_size": popcount(core),
                    "dp_states": dp.expanded, "time": time.perf_counter() - t0}
        new = [m for m in dict.fromkeys(bad) if not (core >> m) & 1]
        assert new, "progress lemma violated"
        for m in new:
            core |= 1 << m
        if time_limit is not None and time.perf_counter() - t0 > time_limit:
            return {"status": "unresolved", "lower": best_lower, "upper": best_upper,
                    "rounds": rounds, "core_size": popcount(core), "dp_states": dp.expanded,
                    "reason": "time limit"}
    return {"status": "unresolved", "lower": best_lower, "upper": best_upper,
            "rounds": rounds, "core_size": popcount(core), "dp_states": dp.expanded,
            "reason": "round limit"}
