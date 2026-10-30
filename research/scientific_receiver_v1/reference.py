"""Independent Python byte parser and exact transition-by-transition reference.

No producer imports, generated source, evaluation, authority flags, or shared
acceptance logic. This is executable differential evidence, not Lean authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import Any


class Rejected(ValueError):
    """A bounded grammar or scoped scientific condition failed."""


@dataclass(frozen=True)
class Contract:
    referenceStep: int
    unitCode: bool
    physical: bool
    initialA: Fraction
    initialB: Fraction
    envValue: Fraction
    boxLo: Fraction
    boxHi: Fraction
    lower: Fraction
    upper: Fraction
    declaredTotal: Fraction
    firings: tuple[Fraction, ...]


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    result: dict[str, Any] | None = None


def _integer(token: bytes) -> int:
    if not token or len(token) > 20:
        raise Rejected("integer field length")
    digits = token[1:] if token[0] == 45 else token
    if not digits or any(char < 48 or char > 57 for char in digits):
        raise Rejected("integer grammar")
    if digits[0] == 48 and (len(digits) != 1 or token[0] == 45):
        raise Rejected("noncanonical integer")
    value = int(token)
    if abs(value) > 1000000000000000000:
        raise Rejected("integer magnitude")
    return value


def decode(raw: bytes) -> Contract:
    if type(raw) is not bytes or len(raw) > 8192 or not raw:
        raise Rejected("raw bytes resource bound")
    if any(char > 127 for char in raw):
        raise Rejected("ASCII required")
    fields = raw.split(b"|")
    if fields[0] != b"PCS-SCI-BOUND-V1":
        raise Rejected("protocol tag")
    if len(fields) < 32:
        raise Rejected("truncated contract")
    numbers = [_integer(field) for field in fields[1:]]
    if numbers[:9] != [1, 1, 0, 1, -1, 1, 1, 1, 0] or numbers[12:14] != [1, 1]:
        raise Rejected("fixed model declarations")
    if not 0 <= numbers[9] <= 64:
        raise Rejected("reference step bound")
    if numbers[10] not in (0, 1) or numbers[11] not in (0, 1):
        raise Rejected("boolean code")
    count = numbers[30]
    if not 0 <= count <= 64 or len(numbers) != 31 + 2 * count:
        raise Rejected("firing count or trailing fields")

    def rational(offset: int) -> Fraction:
        num, den = numbers[offset:offset + 2]
        if den <= 0 or gcd(abs(num), den) != 1:
            raise Rejected("noncanonical rational")
        return Fraction(num, den)

    return Contract(numbers[9], bool(numbers[10]), bool(numbers[11]),
                    *(rational(14 + 2 * index) for index in range(8)),
                    tuple(rational(31 + 2 * index) for index in range(count)))


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def replay(contract: Contract) -> dict[str, Any]:
    """Replay every transition and bind the declared expression to final A."""
    a, b = contract.initialA, contract.initialB
    if contract.referenceStep != len(contract.firings):
        raise Rejected("reference step does not equal schedule length")
    total = a + b
    if total != contract.declaredTotal:
        raise Rejected("incorrect declared total")
    if contract.physical and (a < 0 or b < 0):
        raise Rejected("negative initial physical state")
    for firing in contract.firings:
        if contract.physical and firing < 0:
            raise Rejected("negative physical firing")
        a = a - firing
        b = b + firing
        if contract.physical and (a < 0 or b < 0):
            raise Rejected("negative intermediate physical state")
        if a + b != total:
            raise Rejected("transition conservation failed")
    if contract.envValue != a:
        raise Rejected("environment does not equal final A")
    if not contract.boxLo <= a <= contract.boxHi:
        raise Rejected("final A outside declared box")
    if not contract.lower <= contract.boxLo <= contract.boxHi <= contract.upper:
        raise Rejected("declared box is not enclosed by claim")
    return {"finalA": _pair(a), "finalB": _pair(b), "total": _pair(total),
            "lowerA": _pair(contract.lower), "upperA": _pair(contract.upper),
            "lowerB": _pair(total - contract.upper),
            "upperB": _pair(total - contract.lower),
            "referenceStep": contract.referenceStep, "unitCode": contract.unitCode,
            "physical": contract.physical}


def assess(raw: bytes) -> Decision:
    try:
        return Decision(True, "accepted within exact declared discrete scope", replay(decode(raw)))
    except Rejected as exc:
        return Decision(False, str(exc))


def receive(raw: bytes) -> dict[str, Any] | None:
    return assess(raw).result
