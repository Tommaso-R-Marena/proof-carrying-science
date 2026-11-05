"""Certified rational enclosures for sqrt (on ≥0) and log (on positive domains).

sqrt: for z ∈ [a,b] with 0 ≤ a ≤ b, use monotone enclosure via endpoint
Newton lower/upper bounds that are rational and proved by squaring.

For a ≥ 0, a lower bound ℓ ≥ 0 for √a satisfies ℓ² ≤ a; an upper bound u ≥ 0
satisfies a ≤ u². We construct these by truncated Newton from a rational guess,
then verify by exact rational squaring (authoritative).

log: for z ∈ [a,b] ⊂ (0,∞) with arguments near 1, use the alternating series
for log(1+u) with |u|<1 and explicit remainder. For general positive domains,
reduce via log(z) = log(z/2^k) + k*log(2) with a certified log(2) enclosure
from the series for log(1+1/3)+log(1+1/7)+... or atan-style Machin-like
rational combinations. v1 uses a direct series on reduced u = (z-1)/(z+1)
(artanh series) which converges for z>0:

  log(z) = 2 Σ_{n=0}^{∞} u^{2n+1}/(2n+1),  u=(z-1)/(z+1), |u|<1 for z>0.

Host math.sqrt / math.log are diagnostics only.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional, Tuple

from certnum.interval.interval import Enclosure, EnclStatus, Interval


def _newton_sqrt_bounds(a: Fraction, steps: int = 12) -> Tuple[Fraction, Fraction]:
    """Return (lo, hi) with 0 ≤ lo ≤ √a ≤ hi, verified by lo² ≤ a ≤ hi²."""
    if a < 0:
        raise ValueError("a >= 0")
    if a == 0:
        return Fraction(0), Fraction(0)
    # Initial guess: crude
    x = Fraction(1) if a < 1 else a
    for _ in range(steps):
        if x == 0:
            x = Fraction(1)
        x = (x + a / x) / 2
    # After Newton from above for a>0, x is typically an upper bound if started high;
    # construct certified pair by checking squares.
    # Lower: take floor-like by decreasing until square ≤ a
    hi = x if x * x >= a else a + 1
    # Ensure hi² ≥ a
    while hi * hi < a:
        hi += Fraction(1, 10**6)  # shouldn't loop in practice; use doubling
        hi *= 2
        if hi > a + 1 and a > 1:
            hi = a
            break
    if hi * hi < a:
        hi = a  # a ≤ a² only if a≥1; fallback
        while hi * hi < a:
            hi += 1
    # Lower bound: a/hi ≤ √a when hi ≥ √a
    lo = a / hi if hi != 0 else Fraction(0)
    if lo < 0:
        lo = Fraction(0)
    # Tighten lo by one Newton step from below: lo' = (lo + a/lo)/2 may overshoot;
    # keep only if still lo² ≤ a
    cand = (lo + a / lo) / 2 if lo > 0 else lo
    if cand * cand <= a:
        lo = cand
    # Final verification gate (authoritative: exact rational squaring)
    if not (lo * lo <= a and a <= hi * hi and lo >= 0 and hi >= 0):
        return Fraction(0), max(Fraction(1), a)
    return lo, hi


def sqrt_enclosure(z: Fraction, *, steps: int = 12) -> Enclosure:
    if z < 0:
        return Enclosure.fail(EnclStatus.UNDEFINED)
    lo, hi = _newton_sqrt_bounds(z, steps=steps)
    return Enclosure.ok(Interval.mk(lo, hi))


def sqrt_interval(I: Interval, *, steps: int = 12) -> Enclosure:
    if I.is_empty:
        return Enclosure.fail(EnclStatus.EMPTY_DOMAIN)
    if I.lo < 0:  # type: ignore[operator]
        return Enclosure.fail(EnclStatus.UNDEFINED)
    a = sqrt_enclosure(I.lo, steps=steps)  # type: ignore[arg-type]
    b = sqrt_enclosure(I.hi, steps=steps)  # type: ignore[arg-type]
    if not a.is_ok or not b.is_ok:
        return Enclosure.fail(EnclStatus.UNDEFINED)
    return Enclosure.ok(a.interval.hull(b.interval))


def _log_series_u(u: Fraction, order: int = 24) -> Enclosure:
    """Enclosure of log((1+u)/(1-u)) = 2 Σ u^{2n+1}/(2n+1) for |u|<1."""
    if abs(u) >= 1:
        return Enclosure.fail(EnclStatus.UNSUPPORTED)
    s = Fraction(0)
    term_u = u
    for n in range(order):
        s += term_u / (2 * n + 1)
        term_u *= u * u
    # Remainder: 2 * Σ_{n=N}^{∞} |u|^{2n+1}/(2n+1) ≤ 2 * |u|^{2N+1}/((2N+1)(1-u²))
    N = order
    abs_u = abs(u)
    rem_base = abs_u ** (2 * N + 1)
    den = (2 * N + 1) * (1 - abs_u * abs_u)
    if den <= 0:
        return Enclosure.fail(EnclStatus.INSUFFICIENT_PRECISION)
    rem = 2 * rem_base / den
    partial = 2 * s
    return Enclosure.ok(Interval.mk(partial - rem, partial + rem))


def log_enclosure(z: Fraction, *, order: int = 24) -> Enclosure:
    if z <= 0:
        return Enclosure.fail(EnclStatus.UNDEFINED)
    if z == 1:
        return Enclosure.ok(Interval.singleton(0))
    u = (z - 1) / (z + 1)
    return _log_series_u(u, order=order)


def log_interval(I: Interval, *, order: int = 24) -> Enclosure:
    if I.is_empty:
        return Enclosure.fail(EnclStatus.EMPTY_DOMAIN)
    if not (I.lo is not None and I.lo > 0):
        return Enclosure.fail(EnclStatus.UNDEFINED)
    a = log_enclosure(I.lo, order=order)  # type: ignore[arg-type]
    b = log_enclosure(I.hi, order=order)  # type: ignore[arg-type]
    if not a.is_ok or not b.is_ok:
        return a if not a.is_ok else b
    return Enclosure.ok(a.interval.hull(b.interval))
