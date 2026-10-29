"""Independent certificate checker (host-language mirror of PRISM/Certificates/Checker.lean).

This module imports nothing from `prism.search`.  It recomputes every claim from
the problem data and the certificate.  The authoritative checker is the Lean
kernel (via `prism.lean_export`); this Python mirror is used for large-scale
differential testing and benchmarking, and its agreement with the Lean checker
is itself tested (tests/test_lean_agreement.py).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Tuple


class Reject(Exception):
    """Raised with a human-readable reason when a certificate is rejected."""


def _members(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def _width(P, S: int) -> Fraction:
    vals = [P.q[m] for m in _members(S)]
    return (max(vals) - min(vals)) if vals else Fraction(0)


def _cell(P, S: int, e: int, o: int) -> int:
    r = 0
    for m in _members(S):
        if P.obs[m][e] == o:
            r |= 1 << m
    return r


def _outcomes(P, S: int, e: int):
    return sorted({P.obs[m][e] for m in _members(S)})


def check_policy(P, pol, K: int, eps, bound) -> None:
    """Succeeds ε pol K ∧ CostLE pol K bound.

    The version space is pushed down the policy tree (structural recursion, as in
    the Lean `checkPolicy`): at a `stop` leaf reached by a nonempty set T with
    accumulated cost c we require width(T) <= eps and c <= bound.  Every model of K
    reaches exactly one leaf, so this is equivalent to per-model simulation."""
    eps, bound = Fraction(eps), Fraction(bound)
    # Outcome cells recomputed here from the raw observation table (not taken from
    # the producer's precomputed masks): cells[e][o] = {m : obs[m][e] = o}.
    cells = [dict() for _ in range(P.k)]
    for m in range(P.n):
        for e in range(P.k):
            o = P.obs[m][e]
            cells[e][o] = cells[e].get(o, 0) | (1 << m)
    stack = [(pol, K, Fraction(0), 0)]
    while stack:
        p, T, c, depth = stack.pop()
        if T == 0:
            continue
        if p == "stop":
            if _width(P, T) > eps:
                m = next(_members(T))
                raise Reject(f"policy fails at a leaf containing model {P.models[m]}: "
                             f"terminal width {_width(P, T)} > {eps}")
            if c > bound:
                m = next(_members(T))
                raise Reject(f"policy cost {c} exceeds claimed bound {bound} for model {P.models[m]}")
            continue
        if not isinstance(p, dict) or "e" not in p or "next" not in p or not isinstance(p["next"], dict):
            raise Reject("malformed policy node")
        e = p["e"]
        if not (isinstance(e, int) and not isinstance(e, bool) and 0 <= e < P.k):
            raise Reject("policy references unknown experiment")
        if depth > 1_000_000:
            raise Reject("policy path too long")
        for o, cm in cells[e].items():
            sub = T & cm
            if sub:
                stack.append((p["next"].get(o, "stop"), sub, c + P.cost[e], depth + 1))


def lb_of(table: List[Tuple[int, Fraction]], S: int) -> Fraction:
    for (T, b) in table:  # first matching entry, as in Lean `lbOf`
        if T == S:
            return Fraction(b)
    return Fraction(0)


def check_adversary(P, table: List[Tuple[int, Fraction]], eps) -> None:
    """Each entry satisfies Lean's `EntryOK`."""
    eps = Fraction(eps)
    for (S, _) in table:
        lb = lb_of(table, S)
        if lb < 0:
            raise Reject("negative adversary value")
        if lb == 0:
            continue
        if not (eps < _width(P, S)):
            raise Reject("adversary entry on an already-solved version space")
        for e in range(P.k):
            if not any(lb <= P.cost[e] + lb_of(table, _cell(P, S, e, o)) for o in _outcomes(P, S, e)):
                raise Reject(f"adversary condition fails for experiment {P.experiments[e]}")


def check_optimal(P, K: int, eps, cert: Dict, K_hi: int = None) -> Fraction:
    """Accept iff the sandwich certificate is valid; return the certified optimal cost.

    cert = {"policy", "bound", "core", "adversary": [(mask, lb), ...]}.
    If K_hi is given the policy is checked on K_hi and the caller is responsible
    for core ⊆ K ⊆ K_hi (Lean: checkSandwich_sound)."""
    eps = Fraction(eps)
    if eps < 0:
        raise Reject("negative tolerance")
    bound = Fraction(cert["bound"])
    core = cert["core"]
    if K_hi is None:
        if core & ~K:
            raise Reject("core is not contained in the version space")
        K_hi = K
    check_policy(P, cert["policy"], K_hi, eps, bound)
    table = [(S, Fraction(b)) for (S, b) in cert["adversary"]]
    check_adversary(P, table, eps)
    if not bound <= lb_of(table, core):
        raise Reject("adversary does not establish the claimed lower bound on the core")
    return bound


def check_impossible(P, K: int, eps, m1: int, m2: int) -> None:
    eps = Fraction(eps)
    if not ((K >> m1) & 1 and (K >> m2) & 1):
        raise Reject("witness not admissible")
    if P.obs[m1] != P.obs[m2]:
        raise Reject("witnesses are distinguishable by some experiment")
    if not (P.q[m1] - P.q[m2] > eps):
        raise Reject("query gap does not exceed tolerance")


def check_bounds(P, K: int, lo, hi, mlo: int, mhi: int) -> None:
    lo, hi = Fraction(lo), Fraction(hi)
    if not ((K >> mlo) & 1 and (K >> mhi) & 1):
        raise Reject("bound witness not admissible")
    if P.q[mlo] != lo or P.q[mhi] != hi:
        raise Reject("bound witnesses do not attain the bounds")
    for m in _members(K):
        if not (lo <= P.q[m] <= hi):
            raise Reject("an admissible model violates the claimed bounds")
