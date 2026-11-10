"""Deterministic source-grounding checks (question 2 of a ClaimCheck receipt).

These checks establish *syntactic* correspondence only: the quoted words are in
the paper, the number is printed there, and the columns and groups named by the
typed claim are mentioned in the same sentence under aliases declared by the
dataset's own manifest.  They never establish that a sentence *means* the typed
claim; that stays UNREVIEWED unless a named person confirms it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .spec import ClaimSpec, Cond, UNIT_FAMILIES

_WS = re.compile(r"\s+")
_UNIT_AFTER = re.compile(r"\s{0,2}(%|percent\b|kg\b|mg\b|µg\b|ug\b|g\b|km\b|cm\b|mm\b|µm\b|um\b|m\b|ms\b|min\b|h\b|s\b|d\b|mL\b|ml\b|µL\b|ul\b|L\b|l\b)")
_UNIT_CANON = {"percent": "%"}
_INTERPRETIVE = re.compile(
    r"\b(suggest\w*|indicat\w*|demonstrat\w*|caus\w*|due to|because|therefore|thus|hence|impl(?:y|ies|ied)|"
    r"significan\w*|confirm\w*|prov(?:e|es|ed|ing)|support\w*|effect\w*|leads? to|result(?:s|ed)? in|predict\w*|"
    r"associated with|driven by|explain\w*)\b", re.IGNORECASE)


# Wording that must accompany a non-count statistic in the same sentence.  A printed number that
# merely happens to equal some statistic of a column the sentence mentions (a figure number, a
# model coefficient) is not a report of that statistic.
_RANGE = r"[0-9]\s?[–—-]\s?[0-9]|\b(?:rang(?:e|es|ed|ing)|between|minimum|maximum|min\.?|max\.?|smallest|largest|lowest|highest|shortest|longest|up to|at least|at most)\b"
STAT_CUES = {
    "mean": r"\b(?:means?|averag(?:e|es|ed|ing))\b",
    "median": r"\bmedians?\b",
    "sum": r"\b(?:total(?:s|led|ling)?|sum(?:s|med)?|altogether|combined|overall)\b",
    "min": _RANGE, "max": _RANGE,
    "sd": r"±|\+/-|\bSDs?\b|\bs\.d\.|\bstandard deviations?\b",
    "var_sample": r"\bvariances?\b",
    "sem": r"±|\+/-|\bSEM?s?\b|\bs\.e\.(?:m\.)?|\bstandard errors?\b",
    "pearson": r"\bcorrelat\w*|\bPearson\b|\br\s?=|\bρ",
    "ols_slope": r"\bslopes?\b|\bregress\w*|\bper\b|\by\s?=",
    "ols_intercept": r"\bintercepts?\b|\bregress\w*|\by\s?=",
}
STAT_CUES["sd_sample"] = STAT_CUES["sd_pop"] = STAT_CUES["sd"]


@dataclass
class Grounding:
    ok: bool
    ok_without_statistic_cue: bool = False
    checks: dict = field(default_factory=dict)
    quote_start: int | None = None
    quote_end: int | None = None
    quote_text: str | None = None
    token_start: int | None = None
    token_end: int | None = None
    token_text: str | None = None
    detected_unit: str | None = None
    window_start: int | None = None
    window_end: int | None = None
    failures: list = field(default_factory=list)
    interpretive_terms: list = field(default_factory=list)


def _normalised_with_map(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace runs to one space, remembering each kept character's source index."""
    out, idx = [], []
    in_ws = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not in_ws and out:
                out.append(" ")
                idx.append(i)
            in_ws = True
        else:
            out.append(ch)
            idx.append(i)
            in_ws = False
    return "".join(out), idx


def locate_quote(source: str, quote: str) -> list[tuple[int, int]]:
    """All exact occurrences of ``quote`` in ``source`` up to whitespace runs, as source offsets."""
    needle = _WS.sub(" ", quote).strip()
    if len(needle) < 8:
        return []
    norm, idx = _normalised_with_map(source)
    spans, pos = [], norm.find(needle)
    while pos != -1:
        spans.append((idx[pos], idx[pos + len(needle) - 1] + 1))
        pos = norm.find(needle, pos + 1)
    return spans


def locate_token(text: str, literal: str) -> list[tuple[int, int, str]]:
    """Occurrences of a printed number equal to ``literal`` as a *maximal* numeric token.

    Thousands separators in the printed text ("3,750") are tolerated; the returned
    text is exactly what the source prints.
    """
    hits = []
    for m in re.finditer(r"(?<![0-9.,])[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?(?![0-9])|(?<![0-9.])(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?(?![0-9])", text):
        printed = m.group(0)
        start = m.start()
        if m.end() < len(text) - 1 and text[m.end()] == "." and text[m.end() + 1].isdigit():
            continue
        plain = printed.replace(",", "") if re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?", printed) else printed
        body = literal.lstrip("+-")
        if plain != body:
            continue
        minus = start > 0 and text[start - 1] in "-−" and not (start > 1 and (text[start - 2].isalnum() or text[start - 2] in ")]"))
        if literal.startswith("-") != minus:
            continue  # a printed minus sign must agree with the claimed sign; "10-20" is a range, not -20
        if minus:
            start -= 1
            printed = text[start:m.end()]
        hits.append((start, m.end(), printed))
    return hits


def sentence_window(source: str, start: int, end: int) -> tuple[int, int]:
    """The sentence(s) overlapping [start, end): bounded by blank lines or sentence punctuation."""
    left = start
    while left > 0:
        ch = source[left - 1]
        if ch == "\n" and left > 1 and source[left - 2] == "\n":
            break
        if ch in ".!?" and left < len(source) and source[left].isspace() and _starts_sentence(source, left):
            break
        left -= 1
    right = end
    while right < len(source):
        ch = source[right]
        if ch == "\n" and right + 1 < len(source) and source[right + 1] == "\n":
            break
        if ch in ".!?" and right + 1 < len(source) and source[right + 1].isspace() and _starts_sentence(source, right + 1):
            right += 1
            break
        right += 1
    while left < right and source[left].isspace():
        left += 1
    return left, right


def _starts_sentence(source: str, ws_index: int) -> bool:
    j = ws_index
    while j < len(source) and source[j] in " \t\n":
        j += 1
    return j < len(source) and (source[j].isupper() or source[j] in "([\"'“")


def default_aliases(name: str) -> list[str]:
    words = re.sub(r"[_\-.]+", " ", name).strip()
    out = [name, words]
    stripped = re.sub(r"\s+(mm|cm|m|g|kg|mg|pct|percent|years?|yrs?|days?|s|sec|min)$", "", words, flags=re.IGNORECASE)
    if stripped and stripped != words:
        out.append(stripped)
    return [a for i, a in enumerate(out) if a and a not in out[:i]]


def alias_present(window: str, aliases: list[str]) -> str | None:
    for alias in aliases:
        alias = alias.strip()
        if len(alias) < 2:
            continue
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![0-9])", window, re.IGNORECASE):
            return alias
    return None


def column_aliases(manifest: dict, column: str) -> list[str]:
    declared = ((manifest.get("columns") or {}).get(column) or {}).get("aliases") or []
    return list(declared) + default_aliases(column)


def value_aliases(manifest: dict, column: str, value: str) -> list[str]:
    declared = (((manifest.get("values") or {}).get(column) or {}).get(value)) or []
    return list(declared) + [value]


def ground(source: str, quote: str, spec: ClaimSpec, manifest: dict, *, quote_start: int | None = None) -> Grounding:
    g = Grounding(ok=False)
    spans = locate_quote(source, quote)
    g.checks["quote_in_source"] = bool(spans)
    if not spans:
        g.failures.append("The quoted text does not occur in the source document.")
        return g
    span = next((s for s in spans if s[0] == quote_start), spans[0])
    g.checks["quote_occurrences"] = len(spans)
    g.quote_start, g.quote_end = span
    g.quote_text = source[span[0]:span[1]]

    tokens = locate_token(g.quote_text, spec.reported)
    g.checks["reported_value_in_quote"] = bool(tokens)
    if not tokens:
        g.failures.append(f"The reported value {spec.reported} is not printed in the quoted text as a complete number.")
        return g
    t0, t1, printed = tokens[0]
    g.token_start, g.token_end, g.token_text = span[0] + t0, span[0] + t1, printed
    g.checks["reported_value_occurrences_in_quote"] = len(tokens)

    w0, w1 = sentence_window(source, span[0], span[1])
    g.window_start, g.window_end = w0, w1
    window = source[w0:w1]

    # units printed right after the number
    m = _UNIT_AFTER.match(source[g.token_end:g.token_end + 12])
    g.detected_unit = _UNIT_CANON.get(m.group(1), m.group(1)) if m else None
    data_unit = ((manifest.get("columns") or {}).get(spec.column or "") or {}).get("unit") if spec.stat != "share" else "fraction"
    effective = spec.reported_unit if spec.reported_unit is not None else data_unit
    unit_ok = True
    if spec.reported_unit is not None and g.detected_unit != spec.reported_unit:
        unit_ok = False
        g.failures.append(f"The claim says the value is in {spec.reported_unit!r}, but that unit is not printed after the number.")
    if g.detected_unit is not None and effective is not None and g.detected_unit != effective:
        same_family = any(g.detected_unit in fam and effective in fam for fam in UNIT_FAMILIES.values())
        if same_family:
            unit_ok = False
            g.failures.append(f"The source prints the unit {g.detected_unit!r} after the number, but the claim treats the value as {effective!r}.")
    if spec.stat == "share" and spec.reported_unit is None and g.detected_unit == "%":
        unit_ok = False
        g.failures.append("The source prints a percentage, but the claim treats the value as a fraction.")
    g.checks["unit_consistent_with_source"] = unit_ok

    # lexical anchors
    anchors, anchors_ok = [], True
    needed: list[tuple[str, list[str]]] = []
    if spec.column is not None:
        needed.append((f"column {spec.column}", column_aliases(manifest, spec.column)))
    if spec.x_column is not None:
        needed.append((f"column {spec.x_column}", column_aliases(manifest, spec.x_column)))
    for cond in spec.filter + spec.sub_filter:
        if cond.kind == "text_eq":
            needed.append((f"{cond.column} = {cond.value}", value_aliases(manifest, cond.column, cond.value)))
        elif cond.kind == "text_ne":
            needed.append((f"{cond.column} ≠ {cond.value}", value_aliases(manifest, cond.column, cond.value)))
        else:
            needed.append((f"{cond.column} {cond.cmp} {cond.value}", [cond.value]))
    for what, aliases in needed:
        hit = alias_present(window, aliases)
        anchors.append({"binds": what, "anchored_by": hit})
        if hit is None:
            anchors_ok = False
            g.failures.append(f"Nothing in the sentence names “{what}” (accepted wordings: {', '.join(aliases[:6])}).")
    g.checks["binding_anchors"] = anchors
    g.checks["binding_anchored"] = anchors_ok

    # the statistic itself must be named (counts and shares are exempt: "n = 18", "46 snails")
    cue_ok = True
    pattern = STAT_CUES.get(spec.stat)
    if pattern is not None:
        m = re.search(pattern, window, re.IGNORECASE if spec.stat not in ("sd", "sd_sample", "sd_pop", "sem") else 0)
        g.checks["statistic_named_in_sentence"] = m.group(0) if m else None
        if m is None:
            cue_ok = False
            g.failures.append(f"The sentence has no wording that names the statistic “{spec.stat}” (for example mean, median, SD, range).")

    g.interpretive_terms = sorted({m.group(0).lower() for m in _INTERPRETIVE.finditer(window)})
    g.ok_without_statistic_cue = unit_ok and anchors_ok
    g.ok = unit_ok and anchors_ok and cue_ok
    return g
