"""Certified univariate root isolation via interval subdivision.

Statuses for a candidate interval:
  - EXCLUDED: f(I) does not contain 0
  - POSSIBLE: 0 ∈ f(I) (does NOT prove existence)
  - EXISTS: continuous sign-change witness (f(lo)*f(hi) < 0) or exact zero endpoint
  - UNIQUE: EXISTS + derivative excludes zero (strict monotonicity)
  - UNRESOLVED: resource / width limit reached with 0 ∈ f(I)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from fractions import Fraction
from typing import List, Mapping, Optional

from certnum.ad.forward import differentiate
from certnum.expr.ast import Expr
from certnum.expr.eval import EvalError, eval_exact, eval_interval
from certnum.interval.interval import Interval


class RootStatus(Enum):
    EXCLUDED = auto()
    POSSIBLE = auto()
    EXISTS = auto()
    UNIQUE = auto()
    UNRESOLVED = auto()


@dataclass(frozen=True)
class RootCertificate:
    interval: Interval
    status: RootStatus
    f_lo: Optional[Fraction] = None
    f_hi: Optional[Fraction] = None
    deriv_excludes_zero: bool = False
    notes: str = ""

    def to_json(self) -> dict:
        return {
            "interval": self.interval.to_json(),
            "status": self.status.name,
            "f_lo": None if self.f_lo is None else str(self.f_lo),
            "f_hi": None if self.f_hi is None else str(self.f_hi),
            "deriv_excludes_zero": self.deriv_excludes_zero,
            "notes": self.notes,
        }


def _eval_endpoints(e: Expr, var: str, I: Interval):
    assert not I.is_empty
    try:
        flo = eval_exact(e, {var: I.lo})  # type: ignore[arg-type]
        fhi = eval_exact(e, {var: I.hi})  # type: ignore[arg-type]
        return flo, fhi
    except EvalError:
        return None


def classify_interval(e: Expr, var: str, I: Interval) -> RootCertificate:
    if I.is_empty:
        return RootCertificate(I, RootStatus.EXCLUDED, notes="empty")
    enc = eval_interval(e, {var: I})
    if not enc.is_ok:
        return RootCertificate(I, RootStatus.UNRESOLVED, notes=f"eval {enc.status}")
    if not enc.interval.contains_zero():
        return RootCertificate(I, RootStatus.EXCLUDED, notes="range excludes 0")

    ends = _eval_endpoints(e, var, I)
    if ends is None:
        return RootCertificate(I, RootStatus.POSSIBLE, notes="endpoint eval failed")
    flo, fhi = ends
    if flo == 0 or fhi == 0:
        # Exact root at endpoint — uniqueness not claimed without further work
        return RootCertificate(I, RootStatus.EXISTS, flo, fhi, notes="exact endpoint zero")

    exists = flo * fhi < 0
    # Derivative test for uniqueness
    try:
        de = differentiate(e, var)
        denc = eval_interval(de, {var: I})
        deriv_ok = denc.is_ok and denc.interval.excludes_zero()
    except ValueError:
        deriv_ok = False

    if exists and deriv_ok:
        return RootCertificate(I, RootStatus.UNIQUE, flo, fhi, True, "sign change + monotone")
    if exists:
        return RootCertificate(I, RootStatus.EXISTS, flo, fhi, False, "sign change")
    return RootCertificate(I, RootStatus.POSSIBLE, flo, fhi, deriv_ok, "0 in range, no sign change")


def isolate_roots(
    e: Expr,
    var: str,
    domain: Interval,
    *,
    max_width: Fraction = Fraction(1, 1000),
    max_boxes: int = 10000,
) -> List[RootCertificate]:
    """Branch-and-prune root isolation on a compact rational interval."""
    if domain.is_empty:
        return []
    stack = [domain]
    results: List[RootCertificate] = []
    seen = 0
    while stack and seen < max_boxes:
        I = stack.pop()
        seen += 1
        cert = classify_interval(e, var, I)
        if cert.status is RootStatus.EXCLUDED:
            results.append(cert)
            continue
        if cert.status in (RootStatus.UNIQUE, RootStatus.EXISTS) and I.width() <= max_width:
            results.append(cert)
            continue
        if I.width() <= max_width:
            # narrow but not resolved to existence/uniqueness
            results.append(
                RootCertificate(I, RootStatus.UNRESOLVED if cert.status is RootStatus.POSSIBLE else cert.status,
                                cert.f_lo, cert.f_hi, cert.deriv_excludes_zero, "width limit")
            )
            continue
        parts = I.bisect()
        if parts is None:
            results.append(cert)
            continue
        stack.extend(parts)
    # Merge only reported non-excluded interesting certificates for callers
    return [c for c in results if c.status is not RootStatus.EXCLUDED]
