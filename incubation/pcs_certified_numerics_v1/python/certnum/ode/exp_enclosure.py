"""Certified rational enclosures for exp on compact domains via Taylor + remainder.

For z ∈ [lo, hi] with hi ≥ lo ≥ 0 (nonnegative argument):
  exp(z) = Σ_{k=0}^{n-1} z^k/k! + z^n/n! * exp(ξ) for some ξ ∈ [0,z].

Bound exp(ξ) ≤ exp(hi) is circular; instead use a priori bound:
  On [0, H], exp(ξ) ≤ Σ_{k=0}^{m-1} H^k/k! + H^m/m! * B where we choose B ≥ exp(H)
  by taking B = 2 * Σ_{k=0}^{m-1} H^k/k! when H^m/m! * B is controlled, or
  more simply use the continued geometric majorant:

  For z ∈ [0, H] with H < 1: remainder ≤ H^n / (n! * (1-H)) after n terms? 
  Better standard bound: exp(z) ≤ 1/(1-z) for z∈[0,1) is false.
  
  We use: for z ≥ 0, exp(z) ≤ Σ_{k=0}^{n-1} z^k/k! + z^n/(n! (1 - z/(n+1))) 
  when z < n+1, since the tail is geometric with ratio z/(n+1).

For negative arguments, use exp(-u) = 1/exp(u) with u>0 and reciprocal.
Host math.exp is used only for diagnostic comparison, never as a certificate.
"""

from __future__ import annotations

from fractions import Fraction
from math import factorial
from typing import Tuple

from certnum.interval.interval import Enclosure, EnclStatus, Interval


def _taylor_partial(z: Fraction, n: int) -> Fraction:
    s = Fraction(0)
    term = Fraction(1)
    for k in range(n):
        s += term
        term = term * z / (k + 1)
    return s


def exp_enclosure_nonneg(z: Fraction, *, order: int = 16) -> Enclosure:
    """Enclosure of exp(z) for z ≥ 0."""
    if z < 0:
        return Enclosure.fail(EnclStatus.UNSUPPORTED)
    if z == 0:
        return Enclosure.ok(Interval.singleton(1))
    n = order
    # Require z < n for geometric tail with ratio z/n
    if z >= n:
        # increase order
        n = int(z) + 8
    partial = _taylor_partial(z, n)
    # Tail: Σ_{k=n}^∞ z^k/k! ≤ z^n/n! * Σ_{j=0}^∞ (z/n)^j = (z^n/n!) / (1 - z/n)
    zn_over_nfact = Fraction(1)
    for k in range(1, n + 1):
        zn_over_nfact *= z / k
    ratio = z / n
    if ratio >= 1:
        return Enclosure.fail(EnclStatus.INSUFFICIENT_PRECISION)
    tail = zn_over_nfact / (1 - ratio)
    lo = partial  # truncating positive series underestimates
    hi = partial + tail
    return Enclosure.ok(Interval.mk(lo, hi))


def exp_enclosure(z: Fraction, *, order: int = 16) -> Enclosure:
    if z >= 0:
        return exp_enclosure_nonneg(z, order=order)
    # exp(-u) = 1/exp(u)
    enc = exp_enclosure_nonneg(-z, order=order)
    if not enc.is_ok:
        return enc
    return enc.interval.recip()


def exp_interval(I: Interval, *, order: int = 16) -> Enclosure:
    if I.is_empty:
        return Enclosure.fail(EnclStatus.EMPTY_DOMAIN)
    # exp monotone: enclose via endpoints
    a = exp_enclosure(I.lo, order=order)  # type: ignore[arg-type]
    b = exp_enclosure(I.hi, order=order)  # type: ignore[arg-type]
    if not a.is_ok:
        return a
    if not b.is_ok:
        return b
    return Enclosure.ok(a.interval.hull(b.interval))
