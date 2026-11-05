"""Untrusted data-only producer and strict JSON convenience adapter.

This module computes witnesses by summing firings. The independent reference
never imports it. No generated source or producer PASS flag is accepted.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
import re
from typing import Any

TAG = "PCS-SCI-BOUND-V1"
MAX_OPERAND = 10**18
RATIONAL_FIELDS = ("initialA", "initialB", "envValue", "boxLo", "boxHi",
                   "lower", "upper", "declaredTotal")
_INTEGER = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z", re.ASCII)


@dataclass(frozen=True)
class Witness:
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


def _operand(value: int) -> None:
    if type(value) is not int or abs(value) > MAX_OPERAND:
        raise ValueError("integer operand exceeds protocol bounds")


def _rational(value: Fraction) -> list[str]:
    if not isinstance(value, Fraction):
        raise ValueError("producer requires Fraction values")
    _operand(value.numerator)
    _operand(value.denominator)
    return [str(value.numerator), str(value.denominator)]


def encode(witness: Witness) -> bytes:
    """Serialize bounded typed data; scientific acceptance belongs to receivers."""
    if type(witness.referenceStep) is not int or not 0 <= witness.referenceStep <= 64:
        raise ValueError("referenceStep must be an integer from 0 through 64")
    if type(witness.unitCode) is not bool or type(witness.physical) is not bool:
        raise ValueError("unitCode and physical must be booleans")
    if len(witness.firings) > 64:
        raise ValueError("too many firings")
    header = [1, 1, 0, 1, -1, 1, 1, 1, 0, witness.referenceStep,
              int(witness.unitCode), int(witness.physical), 1, 1]
    fields = [TAG, *(str(value) for value in header)]
    for name in RATIONAL_FIELDS:
        fields.extend(_rational(getattr(witness, name)))
    fields.append(str(len(witness.firings)))
    for firing in witness.firings:
        fields.extend(_rational(firing))
    if any(len(field) > 20 for field in fields):
        raise ValueError("field exceeds 20 characters")
    wire = "|".join(fields).encode("ascii")
    if len(wire) > 8192:
        raise ValueError("wire exceeds 8192 bytes")
    return wire


def build(initialA: Fraction, initialB: Fraction, firings: tuple[Fraction, ...], *,
          box: tuple[Fraction, Fraction] | None = None,
          claim: tuple[Fraction, Fraction] | None = None,
          unitCode: bool = False, physical: bool = False) -> Witness:
    """Construct evidence using a direct sum, independently of stepwise replay."""
    values = tuple(firings)
    final = initialA - sum(values, Fraction(0))
    lo, hi = box if box is not None else (final, final)
    lower, upper = claim if claim is not None else (lo, hi)
    witness = Witness(len(values), unitCode, physical, initialA, initialB,
                      final, lo, hi, lower, upper, initialA + initialB, values)
    encode(witness)  # Only grammar/resource validation, never a PASS decision.
    return witness


def to_json(witness: Witness) -> str:
    encode(witness)
    obj: dict[str, Any] = {"protocol": TAG, "referenceStep": witness.referenceStep,
                           "unitCode": witness.unitCode, "physical": witness.physical}
    obj.update({name: f"{getattr(witness, name).numerator}/{getattr(witness, name).denominator}"
                for name in RATIONAL_FIELDS})
    obj["firings"] = [f"{q.numerator}/{q.denominator}" for q in witness.firings]
    return json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_integer(text: str) -> int:
    if not _INTEGER.fullmatch(text) or len(text) > 20:
        raise ValueError("noncanonical JSON integer")
    value = int(text)
    _operand(value)
    return value


def _reject_number(text: str) -> None:
    raise ValueError(f"noninteger JSON number is unsupported: {text}")


def _json_rational(value: Any) -> Fraction:
    if type(value) is not str or value.count("/") != 1:
        raise ValueError("JSON rationals must be canonical numerator/denominator strings")
    numerator_text, denominator_text = value.split("/")
    numerator = _json_integer(numerator_text)
    denominator = _json_integer(denominator_text)
    if denominator <= 0 or math.gcd(abs(numerator), denominator) != 1:
        raise ValueError("JSON rational must be reduced with positive denominator")
    return Fraction(numerator, denominator)


def from_json(raw: str | bytes) -> Witness:
    """Reject duplicate/unknown keys, alternate rationals, floats and coercions."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="strict")
    obj = json.loads(raw, object_pairs_hook=_pairs, parse_int=_json_integer,
                     parse_float=_reject_number, parse_constant=_reject_number)
    expected = {"protocol", "referenceStep", "unitCode", "physical", "firings", *RATIONAL_FIELDS}
    if type(obj) is not dict or set(obj) != expected:
        raise ValueError("JSON must contain exactly the protocol and typed contract fields")
    if obj["protocol"] != TAG:
        raise ValueError("unsupported protocol")
    if type(obj["firings"]) is not list:
        raise ValueError("firings must be an array")
    witness = Witness(obj["referenceStep"], obj["unitCode"], obj["physical"],
                      *(_json_rational(obj[name]) for name in RATIONAL_FIELDS),
                      tuple(_json_rational(value) for value in obj["firings"]))
    encode(witness)
    return witness


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    wire = encode(from_json(args.json.read_bytes()))
    args.out.write_bytes(wire)


if __name__ == "__main__":
    main()
