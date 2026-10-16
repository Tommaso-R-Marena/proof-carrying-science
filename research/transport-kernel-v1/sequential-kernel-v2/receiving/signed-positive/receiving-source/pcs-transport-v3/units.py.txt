from __future__ import annotations
from collections import defaultdict
import re

# Dimensions: M=mass, L=length, T=time, N=amount-of-substance
#
# High-assurance grammar (mirrored exactly by the Lean authority, see
# formal/PCS/V2/Units.lean, `ExprDenotes` / `parseUnit`):
#
#   expr    := product ('/' product)*          (after deleting U+0020 spaces)
#   product := '' | term ('*' term)*
#   term    := name ('^' '-'? [0-9]+)?          (ASCII digits only)
#   name    := [A-Za-z0-9]+ and a key of _BASE
#
# The PASS/FAIL outcome depends only on the integer dimension vectors. The SI scale
# factors are diagnostic: floating-point overflow/underflow in them must never turn
# a dimensionally compatible pair into FAIL (counterexamples 7 and 8 in
# formal/PCS_FRONTIER_FORMALIZATION_REPORT.md).
_BASE = {
    "1": ({}, 1.0),
    "kg": ({"M": 1}, 1.0), "g": ({"M": 1}, 1e-3), "mg": ({"M": 1}, 1e-6), "ug": ({"M": 1}, 1e-9),
    "m": ({"L": 1}, 1.0), "cm": ({"L": 1}, 1e-2),
    "L": ({"L": 3}, 1e-3), "mL": ({"L": 3}, 1e-6), "uL": ({"L": 3}, 1e-9),
    "s": ({"T": 1}, 1.0), "min": ({"T": 1}, 60.0), "h": ({"T": 1}, 3600.0),
    "mol": ({"N": 1}, 1.0), "mmol": ({"N": 1}, 1e-3), "umol": ({"N": 1}, 1e-6),
    "M": ({"N": 1, "L": -3}, 1e3), "mM": ({"N": 1, "L": -3}, 1.0),
}
# `fullmatch` (not `match` with `$`, which also accepts a trailing newline) and
# ASCII `[0-9]` (not `\d`, which accepts every Unicode decimal digit).
_TERM = re.compile(r"([A-Za-z0-9]+)(?:\^(-?[0-9]+))?")


def _scale_pow(base: float, power: int) -> float | None:
    try:
        return base ** power
    except ArithmeticError:
        return None


def _scale_mul(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    try:
        return a * b
    except ArithmeticError:
        return None


def _scale_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    try:
        return a / b
    except ArithmeticError:
        return None


def _parse_product(text: str) -> tuple[dict[str, int], float | None]:
    dims = defaultdict(int)
    scale: float | None = 1.0
    if text in ("", "1"):
        return {}, 1.0
    for raw in text.split("*"):
        m = _TERM.fullmatch(raw)
        if not m:
            raise ValueError(f"unsupported unit term {raw!r}")
        name, p = m.groups()
        if name not in _BASE:
            raise ValueError(f"unknown unit {name!r}")
        power = int(p or "1")
        udims, uscale = _BASE[name]
        for k, v in udims.items():
            dims[k] += v * power
        scale = _scale_mul(scale, _scale_pow(uscale, power))
    return {k: v for k, v in dims.items() if v}, scale


def parse_unit(expr: str) -> tuple[dict[str, int], float | None]:
    expr = expr.replace(" ", "")
    parts = expr.split("/")
    dims, scale = _parse_product(parts[0])
    dims = defaultdict(int, dims)
    for denom in parts[1:]:
        dd, ds = _parse_product(denom)
        for k, v in dd.items():
            dims[k] -= v
        scale = _scale_div(scale, ds)
    return {k: v for k, v in dims.items() if v}, scale


def units_compatible(left: str, right: str) -> tuple[bool, dict]:
    ld, ls = parse_unit(left)
    rd, rs = parse_unit(right)
    return (ld == rd, {
        "left_dimensions": ld,
        "right_dimensions": rd,
        "left_si_scale": ls,
        "right_si_scale": rs,
        "conversion_left_to_right": (_scale_div(ls, rs) if ld == rd else None),
    })
