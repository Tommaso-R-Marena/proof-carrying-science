"""Strict molecular-formula tokenization matching PCS chemistry checks."""

from __future__ import annotations

import re
from typing import Dict

_TOKEN = re.compile(r"([A-Z][a-z]?)([0-9]*)")


def parse_formula(formula: str) -> Dict[str, int]:
    """Parse an ASCII molecular formula into element → count.

    Rejects empty strings, non-covering tokens, Unicode digits, and trailing junk.
    Absent counts mean 1. Zero counts are rejected.
    """
    if not isinstance(formula, str) or not formula:
        raise ValueError("formula must be a nonempty ASCII string")
    if any(ord(c) > 127 for c in formula):
        raise ValueError("formula must be ASCII")
    counts: Dict[str, int] = {}
    pos = 0
    for match in _TOKEN.finditer(formula):
        if match.start() != pos:
            raise ValueError(f"unrecognized formula fragment at {pos}")
        element, digits = match.group(1), match.group(2)
        count = 1 if digits == "" else int(digits)
        if count <= 0:
            raise ValueError("element counts must be positive")
        counts[element] = counts.get(element, 0) + count
        pos = match.end()
    if pos != len(formula):
        raise ValueError("formula tokens do not cover the whole string")
    if not counts:
        raise ValueError("formula produced no elements")
    return counts
