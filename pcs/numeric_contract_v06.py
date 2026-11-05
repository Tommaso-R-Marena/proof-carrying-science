from __future__ import annotations

import math
from typing import Any

from .canonical_json import CanonicalJSONError, canonical_number_text


class V06NumericContractError(ValueError):
    pass


def canonical_nonnegative_number_text_v06(value: Any, *, label: str) -> str:
    """Encode a non-negative finite scalar as canonical JCS-number text inside a string.

    PCS's verified Lean JSON fragment intentionally excludes non-integral JSON number
    tokens. Scientific parameters that are semantically non-integral therefore cross
    the signed certificate boundary as canonical decimal strings. Numeric manifest
    input remains ergonomic; certificate bytes remain within the formally verified
    JSON fragment.

    String input is accepted only when it is already the unique canonical spelling of
    the same binary64 value, so aliases cannot produce distinct signed predicates with
    the same executable tolerance.
    """
    if isinstance(value, bool):
        raise V06NumericContractError(f"{label} must be a non-negative finite number")

    if isinstance(value, str):
        if not value or value.strip() != value:
            raise V06NumericContractError(f"{label} numeric text must be canonical")
        try:
            number = float(value)
        except (ValueError, OverflowError) as exc:
            raise V06NumericContractError(
                f"{label} must be canonical non-negative finite numeric text"
            ) from exc
        if not math.isfinite(number) or number < 0:
            raise V06NumericContractError(
                f"{label} must be a non-negative finite number"
            )
        try:
            canonical = canonical_number_text(number)
        except CanonicalJSONError as exc:
            raise V06NumericContractError(str(exc)) from exc
        if canonical != value:
            raise V06NumericContractError(
                f"{label} numeric text is not canonical; expected {canonical!r}"
            )
        return canonical

    if not isinstance(value, (int, float)):
        raise V06NumericContractError(f"{label} must be a non-negative finite number")

    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise V06NumericContractError(
            f"{label} must be a non-negative finite number"
        ) from exc
    if not math.isfinite(number) or number < 0:
        raise V06NumericContractError(
            f"{label} must be a non-negative finite number"
        )
    try:
        return canonical_number_text(value)
    except CanonicalJSONError as exc:
        raise V06NumericContractError(str(exc)) from exc


def normalize_certificate_metadata_scalar_v06(value: Any, *, label: str) -> Any:
    """Keep certificate metadata inside Lean's verified JSON numeric fragment."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        if abs(value) > 2**53:
            raise V06NumericContractError(
                f"{label} integer exceeds the PCS safe-integer bound"
            )
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise V06NumericContractError(f"{label} must be finite")
        if not value.is_integer():
            raise V06NumericContractError(
                f"{label} is non-integral; encode non-integral metadata as a string"
            )
        integer = int(value)
        if abs(integer) > 2**53:
            raise V06NumericContractError(
                f"{label} integer exceeds the PCS safe-integer bound"
            )
        return integer
    raise V06NumericContractError(
        f"{label} must be a string, safe integer, boolean, or null"
    )
