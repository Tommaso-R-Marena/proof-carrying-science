"""Independent PGSI2-WIDE canonical-byte reference codec and frozen inference.

This module is NOT the Lean authority. Its purpose is to identify semantic
differences between external Python inference and the *actual* Lean model
that has passed the formal PGSI2-WIDE decoder and strong gate.

Reference format: PGSI2-WIDE|outBias|w1|b1|out1|w2|b2|out2|...
No delimiters may be added, trailing newlines are rejected, and integers
are signed canonical base-ten ASCII (no '+' prefix, '-0', or leading zero).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


class WireReject(ValueError):
    """Canonical wire or architecture constraint violation."""


_CANON_INT = re.compile(rb"(?:0|-?[1-9][0-9]*)\Z", re.ASCII)
_PREFIX = b"PGSI2-WIDE|"


@dataclass(frozen=True)
class Arch:
    max_width: int
    bound: int

    def __post_init__(self) -> None:
        if any(type(i) is not int or i < 0 for i in (self.max_width, self.bound)):
            raise ValueError("architecture limits must be nonnegative exact integers")


@dataclass(frozen=True)
class Unit:
    weight: int
    bias: int
    output: int

    def __post_init__(self) -> None:
        if any(type(i) is not int for i in (self.weight, self.bias, self.output)):
            raise TypeError("unit fields must be exact integers")


@dataclass(frozen=True)
class Wide:
    units: tuple[Unit, ...]
    output_bias: int

    def __post_init__(self) -> None:
        if type(self.units) is not tuple or not all(type(u) is Unit for u in self.units):
            raise TypeError("units must be a tuple of Unit")
        if type(self.output_bias) is not int:
            raise TypeError("output_bias must be an exact integer")

    def predict(self, x: int) -> int:
        if type(x) is not int:
            raise TypeError("x must be an exact integer")
        return self.output_bias + sum(
            unit.output * max(0, unit.weight * x + unit.bias)
            for unit in self.units
        )


def encode(model: Wide) -> bytes:
    if type(model) is not Wide:
        raise TypeError("expected Wide")
    fields = [model.output_bias]
    for u in model.units:
        fields.extend((u.weight, u.bias, u.output))
    return _PREFIX + b"|".join(str(z).encode("ascii") for z in fields)


def valid(model: Wide, arch: Arch) -> bool:
    if len(model.units) > arch.max_width or abs(model.output_bias) > arch.bound:
        return False
    return all(
        abs(value) <= arch.bound
        for unit in model.units
        for value in (unit.weight, unit.bias, unit.output)
    )


def decode(raw: bytes, arch: Arch, *, max_bytes: int | None = None) -> Wide:
    """Strict parser for Lean PGSI2-WIDE *within a selected host resource cap*.

    Any optional max_bytes restricts supported host messages; exceeding it is
    a fail-closed rejection, not evidence Lean would reject that canonical text.
    Python's own maximum decimal-digit conversion length is likewise a host
    availability restriction, NOT a Lean semantic theorem.
    """
    if type(raw) is not bytes or type(arch) is not Arch:
        raise TypeError("expected bytes and Arch")
    if max_bytes is not None:
        if type(max_bytes) is not int or max_bytes < 0:
            raise ValueError("max_bytes must be a nonnegative exact integer")
        if len(raw) > max_bytes:
            raise WireReject("host resource cap exceeded")
    if not raw.startswith(_PREFIX):
        raise WireReject("wrong tag or missing prefix")
    parts = raw[len(_PREFIX):].split(b"|")
    if not parts or len(parts) % 3 != 1:
        raise WireReject("wrong field count")
    if len(parts) - 1 > 3 * arch.max_width:
        raise WireReject("architecture width exceeded")
    vals: list[int] = []
    for token in parts:
        if not _CANON_INT.fullmatch(token):
            raise WireReject("noncanonical integer or non-ASCII payload")
        try:
            number = int(token)
        except ValueError as e:
            raise WireReject("host cannot parse magnitude") from e
        if str(number).encode("ascii") != token:
            raise WireReject("noncanonical integer")
        if abs(number) > arch.bound:
            raise WireReject("parameter out of architecture range")
        vals.append(number)
    model = Wide(tuple(
        Unit(*vals[i:i + 3]) for i in range(1, len(vals), 3)
    ), vals[0])
    if encode(model) != raw or not valid(model, arch):
        raise WireReject("roundtrip or architecture failed")
    return model


@dataclass(frozen=True)
class FrozenWideInference:
    artifact: bytes
    digest: str
    arch: Arch
    model: Wide

    def predict(self, x: int) -> int:
        # Uses exactly the decoded model from the frozen byte snapshot.
        return self.model.predict(x)


def freeze_reference(raw: bytes, arch: Arch, *,
                     expected_sha256: str | None = None,
                     max_bytes: int | None = None) -> FrozenWideInference:
    """Hold immutable decoded bytes in memory; no promotion-history authority.

    Checking a digest supplied by the same caller does not authenticate it.
    This function does not attest to any Lean acceptance or trusted process.
    """
    model = decode(raw, arch, max_bytes=max_bytes)
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise WireReject("expected artifact hash mismatch")
    return FrozenWideInference(raw, digest, arch, model)
