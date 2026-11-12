"""Positional binding: is THIS printed number worded as THIS statistic?

The v1 statistic-wording gate asks only whether a word such as "mean" or "range" occurs anywhere in
the sentence.  That lets a chooser read any number of the sentence as any statistic the sentence
mentions.  v1.1 requires the wording to be attached to the number itself: "mean … 6.07" with no
other number in between, "± 0.05", "5.01–8.03", "n = 124", "96 species" where the manifest says a
row is a species.  The patterns are deliberately narrow; a number they do not cover is left for a
person.  Syntactic only: a bound number can still mean something else.
"""
from __future__ import annotations

import re

from .space import family

_I = re.IGNORECASE
_DASH = r"(?:[–—−-]|\bto\b)"
_PATTERNS_BEFORE = {
    "mean": (r"\b(?:means?|averag(?:e|ed|es|ing))\b[^.;0-9]{0,60}$", _I),
    "median": (r"\bmedians?\b[^.;0-9]{0,60}$", _I),
    "sum": (r"\b(?:total(?:led|ling|s)?|sum(?:med|s)?|altogether|combined)\b[^.;0-9]{0,40}$", _I),
    "var_sample": (r"\bvariances?\b[^.;0-9]{0,30}$", _I),
    "pearson": (r"(?:\br\s?=\s?|\bcorrelat\w*[^.;0-9]{0,40})$", _I),
    "ols_slope": (r"\bslopes?\b[^.;0-9]{0,30}$", _I),
    "ols_intercept": (r"\bintercepts?\b[^.;0-9]{0,30}$", _I),
}
_PM = r"(?:±|\+/-|\+/−)\s{0,2}$"
_SD_NAME = r"\b(?:SDs?|s\.d\.|standard deviations?)\b[^.;0-9]{0,20}$"
_SE_NAME = r"\b(?:SEM?s?|s\.e\.(?:m\.)?|standard errors?)\b[^.;0-9]{0,20}$"


_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"


def canonical_literal(literal: str) -> bool:
    """A plain quantity, not an identifier fragment such as "006"."""
    return re.fullmatch(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", literal) is not None


def part_of_a_date(window: str, start: int, end: int) -> bool:
    """"22 July 2015", "July 2015", "13/08/2016", "2016-08-13": a calendar date, not a quantity."""
    before, after = window[max(0, start - 14):start], window[end:end + 14]
    if re.search(rf"\b{_MONTH}\s$", before) or re.match(rf"\s{_MONTH}(?![A-Za-z])", after):
        return True
    if re.search(r"[0-9][/.-]$", before) and re.match(r"[/.-][0-9]", after):
        return True
    return bool(re.search(r"\b[0-9]{1,4}[/-][0-9]{1,2}[/-]$", before) or re.match(r"[/-][0-9]{1,2}[/-][0-9]{1,4}\b", after))


def row_unit_words(manifest: dict) -> list[str]:
    words = manifest.get("row_unit") or []
    return [w.strip().lower() for w in words if isinstance(w, str) and len(w.strip()) >= 3][:12]


def bound(stat: str, window: str, start: int, end: int, manifest: dict) -> str | None:
    """The wording that attaches the number at ``window[start:end]`` to ``stat``, or None."""
    before, after = window[max(0, start - 90):start], window[end:end + 60]
    if before.endswith(("-", "−")) and not re.search(r"[0-9)\]A-Za-z][-−]$", before):
        before = before[:-1]                                   # a sign belongs to the number
    fam = family(stat)
    if fam == "count":
        if re.search(r"\b[nN]\s?=\s?$", before):
            return "n ="
        m = re.match(r"\s+((?:[A-Za-z][A-Za-z-]*\s+){0,3}[A-Za-z][A-Za-z-]*)", after)
        if m:
            for word in m.group(1).lower().split():
                for unit in row_unit_words(manifest):
                    if word == unit or word in (unit + "s", unit + "es") or (unit.endswith("y") and word == unit[:-1] + "ies"):
                        return f"{word} (the manifest says a row is one {unit})"
        return None
    if fam == "share":
        if re.match(r"\s?(?:%|percent\b)", after):
            return "%"
        m = re.search(r"\b(?:proportion|fraction|share)\b[^.;0-9]{0,40}$", before, _I)
        return m.group(0).strip() if m else None
    if fam == "min":
        if re.match(rf"\s{{0,2}}{_DASH}\s{{0,2}}[0-9.]", after) and not re.search(rf"[0-9]\s{{0,2}}{_DASH}\s{{0,2}}$", before):
            return "left end of a printed range"
        m = re.search(r"\b(?:minimum|min\.?|lowest|smallest|at least)\b[^.;0-9]{0,30}$", before, _I)
        return m.group(0).strip() if m else None
    if fam == "max":
        if re.search(rf"[0-9]\s{{0,2}}{_DASH}\s{{0,2}}$", before) and not re.match(rf"\s{{0,2}}{_DASH}\s{{0,2}}[0-9.]", after):
            return "right end of a printed range"
        m = re.search(r"\b(?:maximum|max\.?|highest|largest|up to|at most)\b[^.;0-9]{0,30}$", before, _I)
        return m.group(0).strip() if m else None
    if fam in ("sd", "sem"):
        if re.match(r"\s{0,2}(?:±|\+/-|\+/−)", after):
            return None                                        # "78.4 ± 1.6": the number before ± is the centre, not the spread
        if re.search(_PM, before):
            return "±"
        name = _SD_NAME if fam == "sd" else _SE_NAME
        m = re.search(name, before)
        if m:
            return m.group(0).strip()
        m = re.match(r"\s{0,2}\(?\s?(SDs?|s\.d\.)" if fam == "sd" else r"\s{0,2}\(?\s?(SEM?|s\.e\.(?:m\.)?)", after)
        return m.group(1) if m else None
    pattern = _PATTERNS_BEFORE.get(stat)
    if pattern is None:
        return None
    m = re.search(pattern[0], before, pattern[1])
    return m.group(0).strip()[:40] if m else None


# ---- units printed after the number ---------------------------------------------------------------
_UNIT_AFTER = re.compile(
    r"\s{0,2}(°\s?[CF]\b|℃|%|‰|percent\b|kg\b|mg\b|µg\b|ug\b|g\b|km\b|cm\b|mm\b|µm\b|um\b|nm\b|m\b|ha\b|ms\b|min\b|hours?\b|hrs?\b|h\b|"
    r"seconds?\b|s\b|days?\b|d\b|weeks?\b|months?\b|years?\b|yrs?\b|mL\b|ml\b|µL\b|ul\b|L\b|l\b|k?Hz\b|m?V\b|k?J\b|k?Pa\b|mol\b|[mµ]M\b|ppm\b|ppb\b)")
_FAMILIES = {
    "temperature": {"°c", "°f", "℃", "c", "degc", "celsius", "k"},
    "mass": {"kg", "g", "mg", "µg", "ug"},
    "length": {"km", "m", "cm", "mm", "µm", "um", "nm"},
    "area": {"ha", "mm2", "mm^2", "mm²", "cm2", "cm^2", "cm²", "m2", "m^2", "m²", "km2", "km²"},
    "time": {"ms", "s", "second", "seconds", "min", "h", "hr", "hrs", "hour", "hours", "d", "day", "days", "week", "weeks", "month", "months",
             "year", "years", "yr", "yrs", "y"},
    "volume": {"l", "ml", "µl", "ul"},
    "fraction": {"%", "percent", "‰", "fraction", "proportion"},
}


def unit_family(unit: str | None) -> str | None:
    if unit is None:
        return None
    u = unit.strip().lower().replace(" ", "")
    for name, members in _FAMILIES.items():
        if u in members:
            return name
    return "other:" + u


def foreign_unit(stat: str, window: str, end: int, declared_unit: str | None) -> str | None:
    """A unit printed right after the number that this reading's quantity cannot have, or None.

    A count has no unit.  A statistic of a column whose manifest unit belongs to another family
    (a temperature after a number read as an area) is not that statistic.  When a unit is printed
    and the manifest declares none for the column, compatibility cannot be checked, and that too
    is reported (fail closed): the person who supplies the data can settle it by declaring the unit.
    """
    m = _UNIT_AFTER.match(window[end:end + 14])
    if not m:
        return None
    printed = m.group(1)
    fam = unit_family(printed)
    f = family(stat)
    if f == "count":
        return f"“{printed}” is printed after the number, and a count has no unit"
    if f == "share":
        return None if fam == "fraction" else f"“{printed}” is printed after the number, and a share is a fraction or a percentage"
    if f in ("pearson", "ols_slope", "var_sample"):
        return None
    if declared_unit is None:
        return f"“{printed}” is printed after the number, but the manifest declares no unit for this column, so the two cannot be compared"
    return None if unit_family(declared_unit) == fam else f"“{printed}” is printed after the number, but the manifest gives this column in {declared_unit}"
