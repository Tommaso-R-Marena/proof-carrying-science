"""Exact rational interval arithmetic (Python mirror of Lean CertNum.Interval).

All endpoints are fractions.Fraction. Floating-point is never used as a proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from fractions import Fraction
from typing import Iterator, Optional, Tuple


class EnclStatus(Enum):
    OK = auto()
    EMPTY_DOMAIN = auto()
    UNDEFINED = auto()
    UNBOUNDED = auto()
    UNSUPPORTED = auto()
    INSUFFICIENT_PRECISION = auto()
    RESOURCE_EXHAUSTED = auto()


class SignClass(Enum):
    ALL_NEGATIVE = auto()
    ALL_NONPOSITIVE = auto()
    ALL_POSITIVE = auto()
    ALL_NONNEGATIVE = auto()
    CONTAINS_ZERO = auto()
    EMPTY = auto()


def _q(x) -> Fraction:
    if isinstance(x, Fraction):
        return x
    return Fraction(x)


@dataclass(frozen=True)
class Enclosure:
    status: EnclStatus
    interval: "Interval"

    @staticmethod
    def ok(I: "Interval") -> "Enclosure":
        return Enclosure(EnclStatus.OK, I)

    @staticmethod
    def fail(status: EnclStatus) -> "Enclosure":
        return Enclosure(status, Interval.empty())

    @property
    def is_ok(self) -> bool:
        return self.status is EnclStatus.OK


@dataclass(frozen=True)
class Interval:
    """Closed rational interval, possibly empty."""

    lo: Optional[Fraction]
    hi: Optional[Fraction]

    def __post_init__(self) -> None:
        if self.lo is None and self.hi is None:
            return
        if self.lo is None or self.hi is None:
            raise ValueError("partial endpoints are not allowed; use empty()")
        if self.lo > self.hi:
            raise ValueError(f"ill-formed interval [{self.lo}, {self.hi}]")

    @staticmethod
    def empty() -> "Interval":
        return Interval(None, None)

    @staticmethod
    def mk(lo, hi) -> "Interval":
        a, b = _q(lo), _q(hi)
        if a <= b:
            return Interval(a, b)
        return Interval.empty()

    @staticmethod
    def singleton(q) -> "Interval":
        v = _q(q)
        return Interval(v, v)

    @staticmethod
    def of_bounds(a, b) -> "Interval":
        x, y = _q(a), _q(b)
        return Interval.mk(min(x, y), max(x, y))

    @property
    def is_empty(self) -> bool:
        return self.lo is None

    def __contains__(self, x) -> bool:
        if self.is_empty:
            return False
        v = _q(x)
        return self.lo <= v <= self.hi  # type: ignore[operator]

    def subset(self, other: "Interval") -> bool:
        if self.is_empty:
            return True
        if other.is_empty:
            return False
        return other.lo <= self.lo and self.hi <= other.hi  # type: ignore[operator]

    def width(self) -> Fraction:
        if self.is_empty:
            return Fraction(0)
        return self.hi - self.lo  # type: ignore[operator]

    def midpoint(self) -> Optional[Fraction]:
        if self.is_empty:
            return None
        return (self.lo + self.hi) / 2  # type: ignore[operator]

    def sign_class(self) -> SignClass:
        if self.is_empty:
            return SignClass.EMPTY
        lo, hi = self.lo, self.hi
        assert lo is not None and hi is not None
        if hi < 0:
            return SignClass.ALL_NEGATIVE
        if lo > 0:
            return SignClass.ALL_POSITIVE
        if lo <= 0 <= hi:
            return SignClass.CONTAINS_ZERO
        if hi <= 0:
            return SignClass.ALL_NONPOSITIVE
        return SignClass.ALL_NONNEGATIVE

    def contains_zero(self) -> bool:
        return (not self.is_empty) and self.lo <= 0 <= self.hi  # type: ignore[operator]

    def excludes_zero(self) -> bool:
        return (not self.is_empty) and (self.hi < 0 or 0 < self.lo)  # type: ignore[operator]

    def neg(self) -> "Interval":
        if self.is_empty:
            return Interval.empty()
        return Interval.mk(-self.hi, -self.lo)  # type: ignore[operator]

    def abs(self) -> "Interval":
        if self.is_empty:
            return Interval.empty()
        lo, hi = self.lo, self.hi
        assert lo is not None and hi is not None
        if lo >= 0:
            return Interval.mk(lo, hi)
        if hi <= 0:
            return Interval.mk(-hi, -lo)
        return Interval.mk(0, max(-lo, hi))

    def add(self, other: "Interval") -> "Interval":
        if self.is_empty or other.is_empty:
            return Interval.empty()
        return Interval.mk(self.lo + other.lo, self.hi + other.hi)  # type: ignore[operator]

    def sub(self, other: "Interval") -> "Interval":
        return self.add(other.neg())

    def mul(self, other: "Interval") -> "Interval":
        if self.is_empty or other.is_empty:
            return Interval.empty()
        a, b, c, d = self.lo, self.hi, other.lo, other.hi
        assert a is not None and b is not None and c is not None and d is not None
        corners = (a * c, a * d, b * c, b * d)
        return Interval.mk(min(corners), max(corners))

    def square(self) -> "Interval":
        if self.is_empty:
            return Interval.empty()
        lo, hi = self.lo, self.hi
        assert lo is not None and hi is not None
        if lo >= 0:
            return Interval.mk(lo * lo, hi * hi)
        if hi <= 0:
            return Interval.mk(hi * hi, lo * lo)
        return Interval.mk(0, max(lo * lo, hi * hi))

    def recip(self) -> Enclosure:
        if self.is_empty:
            return Enclosure.fail(EnclStatus.EMPTY_DOMAIN)
        if not self.excludes_zero():
            return Enclosure.fail(EnclStatus.UNDEFINED)
        lo, hi = self.lo, self.hi
        assert lo is not None and hi is not None
        return Enclosure.ok(Interval.mk(1 / hi, 1 / lo))

    def div(self, other: "Interval") -> Enclosure:
        r = other.recip()
        if not r.is_ok:
            return r
        return Enclosure.ok(self.mul(r.interval))

    def pow_nat(self, n: int) -> "Interval":
        if n < 0:
            raise ValueError("pow_nat requires n >= 0")
        if n == 0:
            return Interval.singleton(1)
        out = Interval.singleton(1)
        base = self
        k = n
        # binary exponentiation for efficiency (still exact)
        while k > 0:
            if k & 1:
                out = out.mul(base)
            k >>= 1
            if k:
                base = base.mul(base)
        return out

    def pow_int(self, k: int) -> Enclosure:
        if k >= 0:
            return Enclosure.ok(self.pow_nat(k))
        r = self.recip()
        if not r.is_ok:
            return r
        return Enclosure.ok(r.interval.pow_nat(-k))

    def inter(self, other: "Interval") -> "Interval":
        if self.is_empty or other.is_empty:
            return Interval.empty()
        return Interval.mk(max(self.lo, other.lo), min(self.hi, other.hi))  # type: ignore[operator]

    def hull(self, other: "Interval") -> "Interval":
        if self.is_empty:
            return other
        if other.is_empty:
            return self
        return Interval.mk(min(self.lo, other.lo), max(self.hi, other.hi))  # type: ignore[operator]

    def bisect(self) -> Optional[Tuple["Interval", "Interval"]]:
        if self.is_empty:
            return None
        m = self.midpoint()
        assert m is not None
        return Interval.mk(self.lo, m), Interval.mk(m, self.hi)

    def definitely_lt(self, other: "Interval") -> bool:
        if self.is_empty or other.is_empty:
            return False
        return self.hi < other.lo  # type: ignore[operator]

    def to_json(self) -> dict:
        if self.is_empty:
            return {"empty": True}
        return {"lo": str(self.lo), "hi": str(self.hi)}

    @staticmethod
    def from_json(obj: dict) -> "Interval":
        if obj.get("empty"):
            return Interval.empty()
        return Interval.mk(Fraction(obj["lo"]), Fraction(obj["hi"]))

    def __repr__(self) -> str:
        if self.is_empty:
            return "Interval(∅)"
        return f"Interval([{self.lo}, {self.hi}])"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return self.lo == other.lo and self.hi == other.hi


def sample_points(I: Interval, n: int = 5) -> Iterator[Fraction]:
    """Diagnostic grid (not a certificate)."""
    if I.is_empty or n <= 0:
        return
    if n == 1:
        yield I.midpoint()  # type: ignore[misc]
        return
    lo, hi = I.lo, I.hi
    assert lo is not None and hi is not None
    for i in range(n):
        t = Fraction(i, n - 1)
        yield lo + t * (hi - lo)
