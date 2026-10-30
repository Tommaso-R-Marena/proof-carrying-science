"""Strict canonical JSON (RFC 8785 / JCS-inspired PCS Next profile).

Independent of production `pcs.canonical_json` so this candidate remains
reviewable in isolation. Cross-checked by differential tests when production
PCS is importable.
"""

from __future__ import annotations

import math
import re
from typing import Any

from .errors import ErrorCode, PcsNextError
from .hashing import sha256_hex

PROFILE = "pcs-next-jcs-rfc8785-v1"


class CanonicalError(PcsNextError):
    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(ErrorCode.CANONICAL_INVALID, message, details=details)


_ESCAPE = {
    ord('"'): '\\"',
    ord("\\"): "\\\\",
    ord("\b"): "\\b",
    ord("\f"): "\\f",
    ord("\n"): "\\n",
    ord("\r"): "\\r",
    ord("\t"): "\\t",
}


def _validate_string(value: str) -> None:
    for ch in value:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise CanonicalError("lone Unicode surrogate rejected")
        if 0xFDD0 <= cp <= 0xFDEF or (cp & 0xFFFF) in (0xFFFE, 0xFFFF):
            raise CanonicalError("Unicode noncharacter rejected")


def _escape_string(value: str) -> str:
    _validate_string(value)
    out: list[str] = ['"']
    for ch in value:
        cp = ord(ch)
        if cp in _ESCAPE:
            out.append(_ESCAPE[cp])
        elif cp < 0x20:
            out.append(f"\\u{cp:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _serialize_number(value: int | float) -> str:
    if isinstance(value, bool):
        raise CanonicalError("bool must not be serialized as number")
    if isinstance(value, int) and not isinstance(value, bool):
        # JSON numbers are IEEE binary64; integers outside safe range are rejected
        # for cross-language stability unless exactly representable.
        if abs(value) > (2**53):
            # Still allow if float(value) round-trips exactly.
            f = float(value)
            if int(f) != value or not math.isfinite(f):
                raise CanonicalError("integer not exactly representable in binary64", details={"value": str(value)})
            value = f
        else:
            return str(value)
    number = float(value)
    if not math.isfinite(number):
        raise CanonicalError("NaN/Infinity rejected")
    if number == 0.0:
        return "0"
    text = format(number, ".17g")
    # Normalize Python quirks toward JCS-like shortest form for common cases.
    if "e" in text or "E" in text:
        text = text.lower().replace("e+", "e")
        m = re.fullmatch(r"(-?)(\d+)(?:\.(\d+))?e(-?\d+)", text)
        if not m:
            return text
        sign, whole, frac, exp = m.group(1), m.group(2), m.group(3) or "", int(m.group(4))
        digits = (whole + frac).lstrip("0") or "0"
        # Keep scientific form when magnitude requires it.
        if abs(number) < 1e-6 or abs(number) >= 1e21:
            if len(digits) == 1:
                mantissa = digits
            else:
                mantissa = digits[0] + "." + digits[1:].rstrip("0")
            return f"{sign}{mantissa}e{exp + len(whole) - 1 + (0 if frac is None else 0)}"
    if text.endswith(".0"):
        text = text[:-2]
    return text


def canonicalize(value: Any) -> bytes:
    """Return UTF-8 canonical bytes; reject non-I-JSON values."""

    def enc(v: Any) -> str:
        if v is None:
            return "null"
        if v is True:
            return "true"
        if v is False:
            return "false"
        if isinstance(v, str):
            return _escape_string(v)
        if isinstance(v, int) and not isinstance(v, bool):
            return _serialize_number(v)
        if isinstance(v, float):
            return _serialize_number(v)
        if isinstance(v, list):
            return "[" + ",".join(enc(x) for x in v) + "]"
        if isinstance(v, dict):
            # Duplicate keys impossible in Python dict; reject non-str keys.
            items = []
            for key in v:
                if not isinstance(key, str):
                    raise CanonicalError("object keys must be strings", details={"key_type": type(key).__name__})
                _validate_string(key)
            for key in sorted(v.keys(), key=lambda s: s.encode("utf-16-be")):
                items.append(_escape_string(key) + ":" + enc(v[key]))
            return "{" + ",".join(items) + "}"
        raise CanonicalError(f"unsupported type: {type(v).__name__}")

    return enc(value).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return sha256_hex(canonicalize(value))


def loads_strict(text: str | bytes) -> Any:
    """Parse JSON rejecting duplicate keys and non-UTF8."""
    import json

    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CanonicalError("invalid UTF-8") from exc

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in pairs:
            if k in out:
                raise CanonicalError("duplicate JSON object key", details={"key": k})
            out[k] = v
        return out

    try:
        return json.loads(text, object_pairs_hook=object_pairs, parse_constant=lambda s: (_ for _ in ()).throw(CanonicalError(f"non-finite constant {s}")))
    except json.JSONDecodeError as exc:
        raise CanonicalError(f"JSON parse error: {exc}") from exc
