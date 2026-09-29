from __future__ import annotations

import json
import math
from hashlib import sha256
from typing import Any


JCS_PROFILE = "pcs-jcs-rfc8785-v1"


class CanonicalJSONError(ValueError):
    """Raised when a value cannot be represented by the PCS RFC 8785 profile."""


def _validate_unicode_string(value: str) -> None:
    for ch in value:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise CanonicalJSONError("lone Unicode surrogate is not permitted by I-JSON/JCS")
        if 0xFDD0 <= cp <= 0xFDEF or (cp & 0xFFFF) in (0xFFFE, 0xFFFF):
            raise CanonicalJSONError("Unicode noncharacter is not permitted by the PCS I-JSON profile")


def _utf16_sort_key(value: str) -> bytes:
    _validate_unicode_string(value)
    return value.encode("utf-16-be")


def _parse_shortest_decimal(text: str) -> tuple[str, int]:
    if "e" in text:
        mantissa, exponent_text = text.split("e", 1)
        exponent = int(exponent_text)
    else:
        mantissa = text
        exponent = 0
    if "." in mantissa:
        integer, fraction = mantissa.split(".", 1)
        return integer + fraction, len(integer) + exponent
    return mantissa, len(mantissa) + exponent


def _serialize_number(value: int | float) -> str:
    """Serialize a Python number with ECMAScript/JCS binary64 spelling."""
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise CanonicalJSONError("JSON number is not representable as IEEE-754 binary64") from exc
    if not math.isfinite(number):
        raise CanonicalJSONError("NaN and Infinity are not permitted by JCS")
    if number == 0.0:
        return "0"

    shortest = repr(number).lower()
    sign = ""
    if shortest.startswith("-"):
        sign = "-"
        shortest = shortest[1:]

    if "e" not in shortest and "." in shortest:
        shortest = shortest.rstrip("0").rstrip(".")

    magnitude = abs(number)
    if 1e-6 <= magnitude < 1e21:
        digits, decimal_position = _parse_shortest_decimal(shortest)
        if decimal_position <= 0:
            body = "0." + ("0" * (-decimal_position)) + digits
        elif decimal_position >= len(digits):
            body = digits + ("0" * (decimal_position - len(digits)))
        else:
            body = digits[:decimal_position] + "." + digits[decimal_position:]
        return sign + body

    if "e" in shortest:
        mantissa, exponent_text = shortest.split("e", 1)
        exponent = int(exponent_text)
        if mantissa.endswith(".0"):
            mantissa = mantissa[:-2]
        exponent_sign = "+" if exponent >= 0 else ""
        return f"{sign}{mantissa}e{exponent_sign}{exponent}"

    digits, decimal_position = _parse_shortest_decimal(shortest)
    first_nonzero = next(i for i, digit in enumerate(digits) if digit != "0")
    significant = digits[first_nonzero:]
    exponent = decimal_position - first_nonzero - 1
    mantissa = significant[0]
    if len(significant) > 1:
        mantissa += "." + significant[1:]
    exponent_sign = "+" if exponent >= 0 else ""
    return f"{sign}{mantissa}e{exponent_sign}{exponent}"


def canonicalize_jcs(value: Any) -> str:
    """Return RFC 8785 canonical JSON text for an already-parsed JSON value."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _serialize_number(value)
    if isinstance(value, str):
        _validate_unicode_string(value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(canonicalize_jcs(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalJSONError("JSON object keys must be strings")
        keys = sorted(value, key=_utf16_sort_key)
        return "{" + ",".join(
            canonicalize_jcs(key) + ":" + canonicalize_jcs(value[key])
            for key in keys
        ) + "}"
    raise CanonicalJSONError(f"unsupported JSON value type: {type(value).__name__}")


def canonicalize_jcs_bytes(value: Any) -> bytes:
    try:
        return canonicalize_jcs(value).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalJSONError("canonical JSON is not valid UTF-8") from exc


def jcs_sha256(value: Any) -> str:
    return sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CanonicalJSONError(f"duplicate JSON object key: {key!r}")
        out[key] = value
    return out


def _reject_constant(value: str) -> Any:
    raise CanonicalJSONError(f"non-finite JSON numeric constant is not allowed: {value}")


def parse_jcs_json(text: str) -> Any:
    """Parse JSON specifically for canonicalization using the ECMAScript number model."""
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_int=float,
            parse_float=float,
            parse_constant=_reject_constant,
        )
    except CanonicalJSONError:
        raise
    except (json.JSONDecodeError, OverflowError, ValueError) as exc:
        raise CanonicalJSONError(f"invalid JCS JSON: {exc}") from exc

    canonicalize_jcs(value)
    return value


def canonicalize_jcs_text(text: str) -> bytes:
    return canonicalize_jcs_bytes(parse_jcs_json(text))
