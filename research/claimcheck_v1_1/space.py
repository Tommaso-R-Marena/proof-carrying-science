"""What a sentence's wording allows a chooser to claim, and how easily the data fits such claims.

ClaimCheck v1 decides the arithmetic of ONE proposed reading.  It cannot see how that reading was
chosen.  Someone who has looked at the data (a person, a search program, a model given the rows)
can pick, among all the readings the sentence's wording admits, one that happens to reproduce the
printed number.  This module makes that freedom explicit and measures it:

* ``readings_for_window`` enumerates the *eligible reading space* of a sentence: every statistic,
  column, row condition and unit that passes the lexical gates for that sentence, within a bounded
  grammar (at most two row conditions, every condition column and threshold named in the sentence).
* ``analyse_token`` reports, for one printed number, (a) which eligible readings reproduce it and
  (b) the *decoy coincidence rate*: of 100 nearby numbers with the same printed precision, how many
  would also be reproduced by some eligible reading.  A high rate means that a match is weak
  evidence that the reading is the right one.

Everything here is untrusted, exact (rational) arithmetic that mirrors the v1 oracle.  It never
produces a mathematical verdict; the policy uses it only to withhold an outward verdict.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from fractions import Fraction
from math import floor

from ..claimcheck_v1 import oracle as O
from ..claimcheck_v1.baseline import NUMBER
from ..claimcheck_v1.grounding import STAT_CUES, alias_present, column_aliases, ground, value_aliases
from ..claimcheck_v1.pipeline import LINEAR_UNIT_STATS
from ..claimcheck_v1.spec import ClaimSpec, Cond, reported_half_unit, unit_factor

MAX_CONDITIONS = 2          # row conditions an eligible reading may use
MAX_ANCHORED_CONDITIONS = 80
MAX_READINGS = 20000
MAX_DISTINCT_VALUES = 400
DECOYS_PER_SIDE = 50
UNIVARIATE = ("mean", "median", "min", "max", "sd_sample", "sd_pop", "sem", "var_sample", "sum")
FAMILY = {"sd": "sd", "sd_sample": "sd", "sd_pop": "sd"}


def family(stat: str) -> str:
    return FAMILY.get(stat, stat)


def _decode(raw: bytes) -> str | None:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


class Table:
    """One strict parse of the data file, with cached row selections."""

    def __init__(self, data: bytes, na_tokens):
        parsed = O.parse_table(data)
        self.ok = parsed is not None
        self.names: list[str] = []
        self.numeric: set[str] = set()
        self.values: dict[str, list[str]] = {}
        self._sel: dict = {}
        self._used: dict = {}
        if not self.ok:
            return
        self.header, self.rows = parsed
        self.na = {t.encode("utf-8") for t in na_tokens}
        self._index = {id(r): i for i, r in enumerate(self.rows)}
        seen = set()
        for i, h in enumerate(self.header):
            name = _decode(O._trim(h))
            if name is None or name in seen:
                continue
            seen.add(name)
            self.names.append(name)
            cells = [O._trim(r[i]) for r in self.rows]
            present = [c for c in cells if c not in self.na]
            if present and all(O._decimal(c) is not None for c in present):
                self.numeric.add(name)
            distinct = sorted(set(present))
            if len(distinct) <= MAX_DISTINCT_VALUES:
                self.values[name] = [v for v in (_decode(d) for d in distinct) if v is not None]
        self._col = {}
        for name in list(self.names):
            try:
                self._col[name] = O._col_index(self.header, name)
            except O._Bad:                      # a repeated header name cannot be addressed by a claim
                self.names.remove(name)
                self.numeric.discard(name)
                self.values.pop(name, None)

    def select(self, conds: tuple) -> tuple | None:
        """Row indices kept by a conjunction of conditions, or None if it cannot be evaluated."""
        key = tuple((c.kind, c.column, c.value, c.cmp) for c in conds)
        if key not in self._sel:
            try:
                rows = O._select(self.header, self.na, tuple(conds), self.rows, missing_column_reason="columnNotFound")
                self._sel[key] = tuple(self._index[id(r)] for r in rows)
            except O._Bad:
                self._sel[key] = None
        return self._sel[key]

    def used(self, rowset: tuple, column: str | None, x_column: str | None = None) -> tuple:
        """The rows of ``rowset`` that actually enter a statistic of these columns (missing dropped)."""
        if column is None:
            return rowset
        key = (rowset, column, x_column)
        if key not in self._used:
            cols = [self._col[c] for c in (column, x_column) if c is not None and c in self._col]
            self._used[key] = tuple(i for i in rowset if all(O._trim(self.rows[i][j]) not in self.na for j in cols))
        return self._used[key]

    def stat(self, spec: ClaimSpec, rowset: tuple):
        try:
            return O._stat(self.header, self.na, [self.rows[i] for i in rowset], spec)
        except O._Bad:
            return None


@dataclass(frozen=True)
class Reading:
    stat: str
    column: str | None
    x_column: str | None
    filter: tuple
    sub_filter: tuple
    kind: str
    sign: int | None
    value: Fraction
    used: int
    ident: tuple          # what is computed: (family, columns, rows that enter it)

    def spec(self, reported: str, reported_unit: str | None) -> ClaimSpec:
        return ClaimSpec(self.stat, reported, self.column, self.x_column, self.filter, self.sub_filter, reported_unit)


def cue_present(stat: str, window: str) -> bool:
    pattern = STAT_CUES.get(stat)
    if pattern is None:
        return True
    flags = re.IGNORECASE if stat not in ("sd", "sd_sample", "sd_pop", "sem") else 0
    return re.search(pattern, window, flags) is not None


def printed_numbers(window: str) -> list[tuple[int, int, str]]:
    """(start, end, literal) of every complete number printed in the sentence."""
    return [(m.start(), m.end(), m.group(0).replace(",", "")) for m in NUMBER.finditer(window)]


def is_group_label(table: Table, manifest: dict, column: str, value: str) -> bool:
    """A value may select rows only if it is a label: a cell of a non-numeric column, or a code of a
    numeric column to which the manifest gives a name.  ("mean of pH where pH = 6.07" would otherwise
    reproduce any number that occurs in the column.)"""
    if column not in table.names:
        return False
    if column not in table.numeric:
        return True
    return value in (((manifest.get("values") or {}).get(column)) or {})


def anchored_conditions(table: Table, manifest: dict, window: str) -> tuple[list[Cond], list[str]]:
    """Row conditions and columns that the sentence's own words name.

    v1.1 judges only one kind of row condition automatically: "column = group label", where the
    label (or an alias the manifest declares for it) is named in the sentence.  Numeric thresholds
    and "is not" conditions give a chooser so many row subsets that almost any number can be fitted;
    readings that use them are left for a person.
    """
    columns = [c for c in table.names if alias_present(window, column_aliases(manifest, c))]
    low = window.lower()
    conds: list[Cond] = []
    for col in table.names:
        for value in table.values.get(col, []):
            if not is_group_label(table, manifest, col, value):
                continue
            aliases = value_aliases(manifest, col, value)
            if not any(a.strip().lower() in low for a in aliases if len(a.strip()) >= 2):
                continue
            if alias_present(window, aliases):
                conds.append(Cond("text_eq", col, value))
    return conds, columns


def structurally_eligible(spec: ClaimSpec, table: Table, manifest: dict, window: str) -> list[str]:
    """v1.1 structural gates on top of the v1 lexical gates.  Returns the reasons a reading is NOT eligible."""
    problems = []
    conds = spec.filter + spec.sub_filter
    if len(spec.filter) > MAX_CONDITIONS or len(spec.sub_filter) > 1:
        problems.append(f"The reading uses more than {MAX_CONDITIONS} row conditions; v1.1 does not judge such readings automatically.")
    if any(c.kind != "text_eq" for c in conds):
        problems.append("The reading selects rows by a numeric threshold or an “is not” condition; v1.1 judges only selections by a group label named in the sentence.")
    if any(c.kind == "text_eq" and not is_group_label(table, manifest, c.column, c.value) for c in conds):
        problems.append("The reading selects rows by a value of a numeric column that the manifest does not declare as a group code.")
    if len({c.column for c in spec.filter}) != len(spec.filter):
        problems.append("The reading puts two conditions on the same column.")
    return problems


def readings_for_window(table: Table, manifest: dict, window: str) -> tuple[list[Reading], dict]:
    """Every eligible reading of a sentence (independent of which printed number is being read)."""
    info = {"anchored_columns": [], "anchored_conditions": 0, "distinct_row_sets": 0, "truncated": False}
    if not table.ok:
        return [], info
    conds, columns = anchored_conditions(table, manifest, window)
    info["anchored_columns"] = columns
    info["anchored_conditions"] = len(conds)
    if len(conds) > MAX_ANCHORED_CONDITIONS:
        info["truncated"] = True
        conds = conds[:MAX_ANCHORED_CONDITIONS]
    filters: list[tuple] = [()] + [(c,) for c in conds]
    filters += [(a, b) for a, b in itertools.combinations(conds, 2) if a.column != b.column]
    rowsets: dict[tuple, tuple] = {}
    for f in filters:
        rows = table.select(f)
        if rows is not None and rows not in rowsets:
            rowsets[rows] = f                      # the simplest filter that yields this set of rows
    info["distinct_row_sets"] = len(rowsets)
    numeric = [c for c in columns if c in table.numeric]
    text_conds = list(conds)
    out: dict[tuple, Reading] = {}

    def add(stat, column, x_column, flt, sub, rows, ident):
        if len(out) >= MAX_READINGS:
            info["truncated"] = True
            return
        key = (stat, ident)
        if key in out:
            return
        res = table.stat(ClaimSpec(stat, "0", column, x_column, flt, sub, None), rows)
        if res is None:
            return
        kind, sign, value, used, _missing = res
        out[key] = Reading(stat, column, x_column, flt, sub, kind, sign, value, used, ident)

    for rows, flt in rowsets.items():
        add("count", None, None, flt, (), rows, ("count", rows))
        for col in columns:
            counted = table.used(rows, col)
            if counted != rows:
                add("count", col, None, flt, (), rows, ("count", counted))
        for col in numeric:
            used = table.used(rows, col)
            for stat in UNIVARIATE:
                if cue_present(stat, window):
                    add(stat, col, None, flt, (), rows, (family(stat), col, None, used))
        for a, b in itertools.permutations(numeric, 2):
            used = table.used(rows, a, b)
            if cue_present("pearson", window) and a < b:
                add("pearson", a, b, flt, (), rows, ("pearson", a, b, used))
            for stat in ("ols_slope", "ols_intercept"):
                if cue_present(stat, window):
                    add(stat, a, b, flt, (), rows, (stat, a, b, used))
        for sub in text_conds:
            if any(sub.column == c.column for c in flt):
                continue
            hit = table.select(flt + (sub,))
            if hit is not None and rows:
                add("share", None, None, flt, (sub,), rows, ("share", rows, hit))
    return list(out.values()), info


def offsets(kind: str, sign, value: Fraction, scale: Fraction, reported: Fraction, half: Fraction) -> list[int]:
    """All k such that the reading reproduces the number ``reported + k·unit`` (unit = one last printed digit)."""
    unit = 2 * half
    if kind == "rat":
        t = (value * scale - reported) / unit + Fraction(1, 2)
        k0 = floor(t)
        return [k0, k0 - 1] if t == k0 else [k0]
    approx = (sign or 0) * float(value) ** 0.5 * float(scale)
    guess = floor((approx - float(reported)) / float(unit) + 0.5)
    hits = []
    for k in (guess - 1, guess, guess + 1):
        d = reported + k * unit
        if O.sqrt_in_interval((d - half) / scale, (d + half) / scale, sign, value):
            hits.append(k)
    return hits


def within(kind: str, sign, value: Fraction, scale: Fraction, reported: Fraction, tolerance: Fraction) -> bool:
    """Is |value·scale − reported| ≤ tolerance?  Exact."""
    if kind == "rat":
        return abs(value * scale - reported) <= tolerance
    return O.sqrt_in_interval((reported - tolerance) / scale, (reported + tolerance) / scale, sign, value)


def decoy_offsets(reported: Fraction, half: Fraction, wanted: int = 2 * DECOYS_PER_SIDE) -> list[int]:
    """Offsets (in units of the last printed digit) of the COMPARABLE numbers used as decoys.

    Comparable means: the same number of decimals and the same number of significant digits, so a
    decoy for "5" is another one-digit number and a decoy for "6.07" is another x.xx number.  The
    nearest ones are taken, at most ``wanted``.  A one-digit number has at most eight.
    """
    unit = 2 * half
    j = reported / unit
    if j.denominator != 1 or j == 0:
        return []
    sign, j = (1 if j > 0 else -1), abs(int(j))
    digits = len(str(j))
    lo, hi = 10 ** (digits - 1), 10 ** digits - 1
    near, step = [], 1
    while len(near) < wanted and (j - step >= lo or j + step <= hi):
        if j - step >= lo:
            near.append(-step)
        if j + step <= hi and len(near) < wanted:
            near.append(step)
        step += 1
    return sorted(sign * k for k in near)


@dataclass
class TokenAnalysis:
    eligible_readings: int
    truncated: bool
    matching: list            # [(Reading, reported_unit)] eligible readings that reproduce the printed number
    decoys: int
    decoys_reproduced: int
    examples: list = field(default_factory=list)   # a few (decoy literal offset, reading description)
    info: dict = field(default_factory=dict)

    @property
    def rate(self) -> Fraction:
        return Fraction(self.decoys_reproduced, self.decoys) if self.decoys else Fraction(1)


class SourceContext:
    """One source document, one data file, one manifest: caches the reading space per sentence."""

    def __init__(self, source_text: str, data: bytes, manifest: dict):
        self.source, self.data, self.manifest = source_text, data, manifest
        self.table = Table(data, tuple(manifest.get("na_tokens") or ["", "NA"]))
        self._windows: dict = {}
        self._ground: dict = {}

    def window_readings(self, w0: int, w1: int):
        key = (w0, w1)
        if key not in self._windows:
            self._windows[key] = readings_for_window(self.table, self.manifest, self.source[w0:w1])
        return self._windows[key]

    def data_unit(self, reading_or_spec) -> str | None:
        if reading_or_spec.stat == "share":
            return "fraction"
        return ((self.manifest.get("columns") or {}).get(reading_or_spec.column or "") or {}).get("unit")

    def unit_options(self, reading: Reading, detected_unit: str | None) -> list[tuple[str | None, Fraction]]:
        options = [None]
        if detected_unit is not None and reading.stat in LINEAR_UNIT_STATS + ("share",):
            options.append(detected_unit)
        out = []
        for ru in options:
            scale = unit_factor(self.data_unit(reading), ru)
            if scale is not None and scale > 0:
                out.append((ru, scale))
        return out

    def grounded(self, reading: Reading, reported: str, reported_unit: str | None, quote: str, quote_start: int | None) -> bool:
        """Does this reading pass every v1 lexical gate for this printed number?  (Independent of its value.)"""
        spec = reading.spec(reported, reported_unit)
        key = (repr(spec.to_json()), quote_start, quote)
        if key not in self._ground:
            self._ground[key] = ground(self.source, quote, spec, self.manifest, quote_start=quote_start).ok
        return self._ground[key]

    def analyse(self, *, w0: int, w1: int, reported: str, detected_unit: str | None, quote: str, quote_start: int | None,
                restrict=None) -> TokenAnalysis:
        """Eligible readings that reproduce the printed number, and the decoy coincidence rate.

        ``restrict`` (optional) limits the space to readings for which ``restrict(reading)`` is true;
        the policy uses it for the space pinned down by a corroborating sibling number.
        """
        readings, info = self.window_readings(w0, w1)
        r = Fraction(reported)
        half = reported_half_unit(reported)
        ks = decoy_offsets(r, half)
        wanted = set(ks)
        candidates: dict[int, list] = {}
        considered = 0
        for reading in readings:
            if restrict is not None and not restrict(reading):
                continue
            for ru, scale in self.unit_options(reading, detected_unit):
                considered += 1
                for k in offsets(reading.kind, reading.sign, reading.value, scale, r, half):
                    if k == 0 or k in wanted:
                        candidates.setdefault(k, []).append((reading, ru))
        matching = [(rd, ru) for rd, ru in candidates.get(0, []) if self.grounded(rd, reported, ru, quote, quote_start)]
        reproduced, examples = 0, []
        for k in ks:
            hit = next(((rd, ru) for rd, ru in candidates.get(k, []) if self.grounded(rd, reported, ru, quote, quote_start)), None)
            if hit is not None:
                reproduced += 1
                if len(examples) < 4:
                    examples.append((k, hit[0]))
        return TokenAnalysis(considered, bool(info.get("truncated")), matching, len(ks), reproduced, examples, dict(info))
