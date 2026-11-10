"""Untrusted exact-arithmetic oracle.

This module mirrors ``formal/ClaimCheck.lean`` in Python ``Fraction`` arithmetic.
Its only job is to *predict* the outcome that the Lean kernel is then asked to
confirm.  It has no authority: if it disagrees with the Lean definitions the
kernel rejects the theorem and the claim stays UNKNOWN.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from fractions import Fraction

from .spec import ClaimSpec, Cond, reported_half_unit

# Decimal cells: the grammar of ``decGo`` in the Lean checker (no digit-count limits).
CELL_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")

UNDEFINED_REASONS = (
    "sourceNotWellFormed", "csvMalformed", "columnNotFound", "nonNumericCell", "emptySelection",
    "degenerate", "badReportedLiteral", "badScale", "missingColumn",
)

UNDEFINED_EXPLANATIONS = {
    "csvMalformed": "The data file is not a strict rectangular CSV (ragged rows, a blank line, a stray quote or an unterminated quoted field).",
    "columnNotFound": "A column named in the claim is absent from the header, or the header contains it more than once.",
    "nonNumericCell": "A cell needed for the calculation is neither a decimal number nor one of the declared missing-value tokens.",
    "emptySelection": "The selected rows contain too few usable values for this statistic.",
    "degenerate": "The statistic divides by a variance that is exactly zero on the selected rows.",
    "badReportedLiteral": "The reported value is not a plain decimal literal.",
    "badScale": "The unit factor is not a positive number.",
    "missingColumn": "This statistic needs a target column.",
    "sourceNotWellFormed": "The embedded data numeral does not fit the stated byte length.",
}


@dataclass(frozen=True)
class Outcome:
    """Mirror of ``PCS.ClaimCheck.Outcome``."""

    defined: bool
    verdict: str | None = None        # "consistent" | "inconsistent"
    value_kind: str | None = None     # "rat" | "sqrt"
    value: Fraction | None = None     # the rational, or the radicand
    sign: int | None = None           # for sqrt values
    used: int | None = None
    missing: int | None = None
    reason: str | None = None         # for undefined outcomes

    def approx(self) -> float | None:
        if not self.defined:
            return None
        if self.value_kind == "rat":
            return float(self.value)
        return self.sign * float(self.value) ** 0.5


class _Bad(Exception):
    def __init__(self, reason: str):
        self.reason = reason


def parse_csv(data: bytes) -> list[list[bytes]] | None:
    """Strict CSV automaton; byte-for-byte the same language as ``csvGo`` in Lean."""
    if data[:3] == b"\xef\xbb\xbf":
        data = data[3:]
    rows: list[list[bytes]] = []
    row: list[bytes] = []
    fld = bytearray()
    mode = 0
    i, n = 0, len(data)

    def end_row() -> None:
        nonlocal row, fld
        row.append(bytes(fld))
        rows.append(row)
        row, fld = [], bytearray()

    while i < n:
        b = data[i]
        if mode == 0:
            if b == 34:
                mode = 2
            elif b == 44:
                row.append(b"")
            elif b == 10:
                if not row:
                    return None
                end_row()
            elif b == 13:
                if i + 1 < n and data[i + 1] == 10 and row:
                    end_row()
                    i += 1
                else:
                    return None
            else:
                fld.append(b)
                mode = 1
        elif mode == 1:
            if b == 44:
                row.append(bytes(fld)); fld = bytearray(); mode = 0
            elif b == 10:
                end_row(); mode = 0
            elif b == 13:
                if i + 1 < n and data[i + 1] == 10:
                    end_row(); mode = 0; i += 1
                else:
                    return None
            elif b == 34:
                return None
            else:
                fld.append(b)
        elif mode == 2:
            if b == 34:
                mode = 3
            else:
                fld.append(b)
        else:
            if b == 34:
                fld.append(34); mode = 2
            elif b == 44:
                row.append(bytes(fld)); fld = bytearray(); mode = 0
            elif b == 10:
                end_row(); mode = 0
            elif b == 13:
                if i + 1 < n and data[i + 1] == 10:
                    end_row(); mode = 0; i += 1
                else:
                    return None
            else:
                return None
        i += 1
    if mode == 0:
        if row:
            end_row()
    elif mode == 2:
        return None
    else:
        end_row()
    return rows


def parse_table(data: bytes) -> tuple[list[bytes], list[list[bytes]]] | None:
    rows = parse_csv(data)
    if not rows:
        return None
    header, body = rows[0], rows[1:]
    if any(len(r) != len(header) for r in body):
        return None
    return header, body


def _trim(cell: bytes) -> bytes:
    return cell.strip(b" \t")


def _decimal(cell: bytes) -> Fraction | None:
    try:
        text = cell.decode("ascii")
    except UnicodeDecodeError:
        return None
    if not CELL_RE.fullmatch(text):
        return None
    exp = text.lower().partition("e")[2]
    if exp and abs(int(exp)) > 400:
        return None
    return Fraction(text)


def _col_index(header: list[bytes], name: str) -> int:
    raw = name.encode("utf-8")
    hits = [i for i, h in enumerate(header) if _trim(h) == raw]
    if len(hits) != 1:
        raise _Bad("columnNotFound")
    return hits[0]


_CMP = {
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b, "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b, "gt": lambda a, b: a > b, "ge": lambda a, b: a >= b,
}


def _select(header, na: set[bytes], conds: tuple[Cond, ...], rows, *, missing_column_reason: str) -> list[list[bytes]]:
    try:
        idx = [_col_index(header, c.column) for c in conds]
    except _Bad:
        raise _Bad(missing_column_reason) from None
    out = []
    bad = False
    for row in rows:
        keep = True
        for cond, i in zip(conds, idx):
            cell = _trim(row[i])
            if cond.kind == "text_eq":
                ok = cell == cond.value.encode("utf-8")
            elif cond.kind == "text_ne":
                ok = cell != cond.value.encode("utf-8")
            else:
                if cell in na:
                    ok = False
                else:
                    x = _decimal(cell)
                    if x is None:
                        bad = True
                        ok = False
                        keep = False
                        break
                    ok = _CMP[cond.cmp](x, Fraction(cond.value))
            if not ok:
                keep = False
                break
        if keep:
            out.append(row)
    if bad:
        raise _Bad("nonNumericCell")
    return out


def _numeric(na, i, rows) -> tuple[list[Fraction], int]:
    xs, missing = [], 0
    for row in rows:
        cell = _trim(row[i])
        if cell in na:
            missing += 1
            continue
        x = _decimal(cell)
        if x is None:
            raise _Bad("nonNumericCell")
        xs.append(x)
    return xs, missing


def _ss(xs: list[Fraction]) -> Fraction:
    m = sum(xs, Fraction(0)) / len(xs)
    return sum(((x - m) * (x - m) for x in xs), Fraction(0))


def _sign(q: Fraction) -> int:
    return 1 if q > 0 else -1 if q < 0 else 0


def _stat(header, na, rows, spec: ClaimSpec):
    """Returns (kind, sign, value, used, missing)."""
    stat = spec.stat
    if stat == "count":
        if spec.column is None:
            return "rat", None, Fraction(len(rows)), len(rows), 0
        i = _col_index(header, spec.column)
        present = sum(1 for r in rows if _trim(r[i]) not in na)
        return "rat", None, Fraction(present), present, len(rows) - present
    if stat == "share":
        if not rows:
            raise _Bad("emptySelection")
        hit = _select(header, na, spec.sub_filter, rows, missing_column_reason="columnNotFound")
        return "rat", None, Fraction(len(hit), len(rows)), len(rows), 0
    if stat in ("pearson", "ols_slope", "ols_intercept"):
        if spec.column is None:
            raise _Bad("missingColumn")
        ix = _col_index(header, spec.x_column)
        iy = _col_index(header, spec.column)
        pairs, missing = [], 0
        for row in rows:
            cx, cy = _trim(row[ix]), _trim(row[iy])
            if cx in na or cy in na:
                missing += 1
                continue
            x, y = _decimal(cx), _decimal(cy)
            if x is None or y is None:
                raise _Bad("nonNumericCell")
            pairs.append((x, y))
        if len(pairs) < 2:
            raise _Bad("emptySelection")
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx = sum(xs, Fraction(0)) / len(xs)
        my = sum(ys, Fraction(0)) / len(ys)
        sxx, syy = _ss(xs), _ss(ys)
        sxy = sum(((x - mx) * (y - my) for x, y in pairs), Fraction(0))
        if sxx == 0:
            raise _Bad("degenerate")
        if stat == "pearson":
            if syy == 0:
                raise _Bad("degenerate")
            return "sqrt", _sign(sxy), sxy * sxy / (sxx * syy), len(pairs), missing
        if stat == "ols_slope":
            return "rat", None, sxy / sxx, len(pairs), missing
        return "rat", None, my - sxy / sxx * mx, len(pairs), missing
    if spec.column is None:
        raise _Bad("missingColumn")
    i = _col_index(header, spec.column)
    xs, missing = _numeric(na, i, rows)
    if not xs:
        raise _Bad("emptySelection")
    n = len(xs)
    if stat == "sum":
        return "rat", None, sum(xs, Fraction(0)), n, missing
    if stat == "mean":
        return "rat", None, sum(xs, Fraction(0)) / n, n, missing
    if stat == "median":
        s = sorted(xs)
        med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
        return "rat", None, med, n, missing
    if stat == "min":
        return "rat", None, min(xs), n, missing
    if stat == "max":
        return "rat", None, max(xs), n, missing
    if stat == "sd_pop":
        return "sqrt", 1, _ss(xs) / n, n, missing
    if n < 2:
        raise _Bad("emptySelection")
    if stat == "var_sample":
        return "rat", None, _ss(xs) / (n - 1), n, missing
    if stat == "sd_sample":
        return "sqrt", 1, _ss(xs) / (n - 1), n, missing
    if stat == "sem":
        return "sqrt", 1, _ss(xs) / (n - 1) / n, n, missing
    raise _Bad("missingColumn")


def sqrt_in_interval(lo: Fraction, hi: Fraction, s: int, q: Fraction) -> bool:
    """lo <= s*sqrt(q) <= hi decided in rationals (mirror of ``sqrtInInterval``)."""
    if s == 0 or q == 0:
        return lo <= 0 <= hi
    if s > 0:
        return (lo <= 0 or lo * lo <= q) and (0 <= hi and q <= hi * hi)
    return (lo <= 0 and q <= lo * lo) and (0 <= hi or hi * hi <= q)


def evaluate(data: bytes, spec: ClaimSpec, na_tokens: tuple[str, ...], scale: Fraction) -> Outcome:
    """Predict ``PCS.ClaimCheck.run`` for these bytes and this claim."""
    table = parse_table(data)
    if table is None:
        return Outcome(False, reason="csvMalformed")
    header, rows = table
    na = {t.encode("utf-8") for t in na_tokens}
    try:
        r = Fraction(spec.reported)
        half = reported_half_unit(spec.reported)
    except Exception:
        return Outcome(False, reason="badReportedLiteral")
    if scale <= 0:
        return Outcome(False, reason="badScale")
    try:
        selected = _select(header, na, spec.filter, rows, missing_column_reason="columnNotFound")
        kind, sign, value, used, missing = _stat(header, na, selected, spec)
    except _Bad as exc:
        return Outcome(False, reason=exc.reason)
    lo, hi = r - half, r + half
    if kind == "rat":
        ok = lo <= value * scale <= hi
    else:
        ok = sqrt_in_interval(lo / scale, hi / scale, sign, value)
    return Outcome(True, "consistent" if ok else "inconsistent", kind, value, sign, used, missing)
