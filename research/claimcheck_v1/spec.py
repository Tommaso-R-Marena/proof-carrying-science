"""Typed claim representation (Claim IR) with strict, fail-closed validation.

A ``ClaimSpec`` is pure data.  It can be proposed by anyone (a rule, a language
model, a person); it never carries authority.  Everything a proposer could abuse
to force a match is either absent from the spec (missing-value tokens and unit
factors come from the dataset manifest and a fixed unit table) or independently
re-derived from the source (the reported literal and its precision).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

UNIVARIATE = ("sum", "mean", "median", "min", "max", "var_sample", "sd_sample", "sd_pop", "sem")
BIVARIATE = ("pearson", "ols_slope", "ols_intercept")
STATS = ("count", "share") + UNIVARIATE + BIVARIATE
# "sd" is accepted from proposers as "standard deviation, convention not stated".
PROPOSABLE_STATS = STATS + ("sd",)
CMPS = ("eq", "ne", "lt", "le", "gt", "ge")
COND_KINDS = ("text_eq", "text_ne", "num")

MAX_NAME_BYTES = 128
MAX_CONDS = 6
# A printed decimal literal.  Thousands separators, percent signs and units are not part of it.
REPORTED_RE = re.compile(r"[+-]?(?:\d{1,18}(?:\.\d{0,12})?|\.\d{1,12})(?:[eE][+-]?\d{1,3})?\Z")
DECIMAL_RE = REPORTED_RE


class SpecError(ValueError):
    """A proposal that is not a well-formed claim.  Never silently repaired."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _name(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise SpecError(f"{what} must be a non-empty string")
    raw = value.encode("utf-8")
    if len(raw) > MAX_NAME_BYTES:
        raise SpecError(f"{what} is longer than {MAX_NAME_BYTES} bytes")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise SpecError(f"{what} contains a control character")
    if value != value.strip(" \t"):
        raise SpecError(f"{what} has leading or trailing blanks")
    return value


def parse_decimal(text: str) -> Fraction:
    """Exact value of a decimal literal (same grammar as the Lean checker)."""
    if not isinstance(text, str) or not DECIMAL_RE.match(text):
        raise SpecError(f"not a decimal literal: {text!r}")
    mant, _, exp = text.lower().partition("e")
    if abs(int(exp or "0")) > 400:
        raise SpecError("exponent out of range")
    return Fraction(text)


def reported_half_unit(text: str) -> Fraction:
    """Half a unit in the last printed place of a decimal literal."""
    if not REPORTED_RE.match(text):
        raise SpecError(f"not a decimal literal: {text!r}")
    mant, _, exp = text.lower().partition("e")
    frac_digits = len(mant.partition(".")[2])
    return Fraction(10) ** (int(exp or "0") - frac_digits) / 2


@dataclass(frozen=True)
class Cond:
    kind: str
    column: str
    value: str
    cmp: str | None = None

    def to_json(self) -> dict:
        out = {"kind": self.kind, "column": self.column, "value": self.value}
        if self.kind == "num":
            out["cmp"] = self.cmp
        return out

    @classmethod
    def from_json(cls, raw: Any) -> "Cond":
        if not isinstance(raw, dict):
            raise SpecError("condition must be an object")
        kind = raw.get("kind")
        if kind not in COND_KINDS:
            raise SpecError(f"unsupported condition kind: {kind!r}")
        allowed = {"kind", "column", "value"} | ({"cmp"} if kind == "num" else set())
        if set(raw) - allowed or not {"kind", "column", "value"} <= set(raw):
            raise SpecError("condition has missing or unexpected fields")
        column = _name(raw["column"], "condition column")
        value = raw["value"]
        if kind == "num":
            if raw.get("cmp") not in CMPS:
                raise SpecError("numeric condition needs cmp in " + "/".join(CMPS))
            if not isinstance(value, str):
                raise SpecError("numeric condition value must be a decimal string")
            parse_decimal(value)
            return cls(kind, column, value, raw["cmp"])
        if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_NAME_BYTES:
            raise SpecError("text condition value must be a short string")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in value) or value != value.strip(" \t"):
            raise SpecError("text condition value has control characters or outer blanks")
        return cls(kind, column, value, None)


@dataclass(frozen=True)
class ClaimSpec:
    """One fully explicit, checkable statement about one data file."""

    stat: str
    reported: str
    column: str | None = None
    x_column: str | None = None
    filter: tuple[Cond, ...] = ()
    sub_filter: tuple[Cond, ...] = ()
    reported_unit: str | None = None  # e.g. "kg", "%"; the factor is looked up, never proposed

    def to_json(self) -> dict:
        return {
            "stat": self.stat,
            "reported": self.reported,
            "column": self.column,
            "x_column": self.x_column,
            "filter": [c.to_json() for c in self.filter],
            "sub_filter": [c.to_json() for c in self.sub_filter],
            "reported_unit": self.reported_unit,
        }

    def identity(self) -> str:
        return sha256_hex(canonical(self.to_json()))

    @classmethod
    def from_json(cls, raw: Any, *, allow_unspecified_sd: bool = False) -> "ClaimSpec":
        if not isinstance(raw, dict):
            raise SpecError("claim spec must be an object")
        known = {"stat", "reported", "column", "x_column", "filter", "sub_filter", "reported_unit"}
        if set(raw) - known:
            raise SpecError("claim spec has unexpected fields: " + ", ".join(sorted(set(raw) - known)))
        stat = raw.get("stat")
        allowed = PROPOSABLE_STATS if allow_unspecified_sd else STATS
        if stat not in allowed:
            raise SpecError(f"unsupported statistic: {stat!r}")
        reported = raw.get("reported")
        if not isinstance(reported, str) or not REPORTED_RE.match(reported):
            raise SpecError("reported must be the decimal literal exactly as printed")
        column = raw.get("column")
        x_column = raw.get("x_column")
        if column is not None:
            column = _name(column, "column")
        if x_column is not None:
            x_column = _name(x_column, "x_column")
        if stat in UNIVARIATE + BIVARIATE + ("sd",) and column is None:
            raise SpecError(f"{stat} needs a target column")
        if stat in BIVARIATE and x_column is None:
            raise SpecError(f"{stat} needs x_column")
        if stat not in BIVARIATE and x_column is not None:
            raise SpecError(f"x_column is only meaningful for {'/'.join(BIVARIATE)}")
        conds = []
        for key in ("filter", "sub_filter"):
            items = raw.get(key) or []
            if not isinstance(items, list) or len(items) > MAX_CONDS:
                raise SpecError(f"{key} must be a list of at most {MAX_CONDS} conditions")
            conds.append(tuple(Cond.from_json(item) for item in items))
        if stat == "share" and not conds[1]:
            raise SpecError("share needs a non-empty sub_filter")
        if stat != "share" and conds[1]:
            raise SpecError("sub_filter is only meaningful for share")
        unit = raw.get("reported_unit")
        if unit is not None and (not isinstance(unit, str) or not re.fullmatch(r"[A-Za-zµ%°/^0-9.\- ]{1,24}", unit)):
            raise SpecError("reported_unit is not a short unit symbol")
        return cls(stat, reported, column, x_column, conds[0], conds[1], unit)


# --- units --------------------------------------------------------------------------------------
# Exact factors to a base unit, per dimension.  A reported unit may differ from the data unit only
# within one family; the factor is looked up here and can never be supplied by a proposer.
UNIT_FAMILIES: dict[str, dict[str, Fraction]] = {
    "mass": {"kg": Fraction(1000), "g": Fraction(1), "mg": Fraction(1, 1000), "µg": Fraction(1, 10**6), "ug": Fraction(1, 10**6)},
    "length": {"km": Fraction(1000), "m": Fraction(1), "cm": Fraction(1, 100), "mm": Fraction(1, 1000), "µm": Fraction(1, 10**6), "um": Fraction(1, 10**6)},
    "time": {"d": Fraction(86400), "h": Fraction(3600), "min": Fraction(60), "s": Fraction(1), "ms": Fraction(1, 1000)},
    "volume": {"L": Fraction(1), "l": Fraction(1), "mL": Fraction(1, 1000), "ml": Fraction(1, 1000), "µL": Fraction(1, 10**6), "ul": Fraction(1, 10**6)},
    "fraction": {"fraction": Fraction(1), "%": Fraction(1, 100)},
}


def unit_factor(data_unit: str | None, reported_unit: str | None) -> Fraction | None:
    """Factor k with  reported_value = k * statistic_in_data_units, or None if not derivable."""
    if reported_unit is None or reported_unit == data_unit:
        return Fraction(1)
    if data_unit is None:
        return None
    for table in UNIT_FAMILIES.values():
        if data_unit in table and reported_unit in table:
            return table[data_unit] / table[reported_unit]
    return None
