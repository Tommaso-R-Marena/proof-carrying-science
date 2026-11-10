"""Deterministic proposers (no language model).

Two baselines produce the same kind of untrusted proposals as a model does:

``propose_rules``   cue-word rules over each sentence; never looks at the data values.
``propose_search``  the classic symbolic approach: for each printed number, enumerate anchored
                    (statistic, column, group) combinations and keep a combination only if it is the
                    unique one that reproduces the number.  It looks at the data, so a chance match
                    is possible; the verifier's gates and the benchmark measure how often.

Neither has any authority: every proposal goes through the same gates and the same Lean check.
"""
from __future__ import annotations

import itertools
import re
from fractions import Fraction

from .grounding import alias_present, column_aliases, sentence_spans, value_aliases
from .oracle import _decimal, _trim, evaluate, parse_table
from .spec import ClaimSpec, Cond, unit_factor

NUMBER = re.compile(r"(?<![0-9A-Za-z.,])[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?(?![0-9])|(?<![0-9A-Za-z.])(?:[0-9]+(?:\.[0-9]+)?)(?![0-9]|\.[0-9])")
MAX_GROUP_VALUES = 40


def sentences(text: str) -> list[tuple[int, str]]:
    return [(a, text[a:b]) for a, b in sentence_spans(text)]


def table_profile(data: bytes, manifest: dict) -> dict:
    """Column kinds and small categorical value sets, read with the same strict parser."""
    table = parse_table(data)
    if table is None:
        return {"numeric": [], "categorical": {}, "columns": []}
    header, rows = table
    na = {t.encode() for t in (manifest.get("na_tokens") or ["", "NA"])}
    numeric, categorical, names = [], {}, []
    for i, h in enumerate(header):
        try:
            name = _trim(h).decode("utf-8")
        except UnicodeDecodeError:
            continue
        names.append(name)
        cells = [_trim(r[i]) for r in rows]
        present = [c for c in cells if c not in na]
        if present and all(_decimal(c) is not None for c in present):
            numeric.append(name)
            # A numeric column is a grouping variable only where the manifest names its codes
            # (e.g. 0/1 = control/treated).  Its values are never listed otherwise, so that the
            # data dictionary shown to a proposer cannot leak measurements.
            named = ((manifest.get("values") or {}).get(name)) or {}
            codes = [d.decode("ascii") for d in sorted(set(present)) if d.decode("ascii", "replace") in named]
            if codes:
                categorical[name] = codes
        else:
            distinct = sorted(set(present))
            if 0 < len(distinct) <= MAX_GROUP_VALUES:
                try:
                    categorical[name] = [d.decode("utf-8") for d in distinct]
                except UnicodeDecodeError:
                    pass
    return {"numeric": numeric, "categorical": categorical, "columns": names}


def _anchored(sentence: str, manifest: dict, profile: dict):
    cols = [(c, a) for c in profile["numeric"] if (a := alias_present(sentence, column_aliases(manifest, c)))]
    groups = []
    for col, values in profile["categorical"].items():
        for v in values:
            if alias_present(sentence, value_aliases(manifest, col, v)):
                groups.append((col, v))
    return cols, groups


def _unit_after(sentence: str, end: int) -> str | None:
    m = re.match(r"\s{0,2}(%|kg\b|mg\b|g\b|km\b|cm\b|mm\b|m\b|min\b|h\b|s\b|d\b)", sentence[end:end + 10])
    return m.group(1) if m else None


def _reported_unit(manifest: dict, column: str | None, printed_unit: str | None) -> str | None:
    if column is None or printed_unit in (None, "%"):
        return None
    data_unit = ((manifest.get("columns") or {}).get(column) or {}).get("unit")
    return printed_unit if data_unit and printed_unit != data_unit and unit_factor(data_unit, printed_unit) is not None else None


def _filters(groups: list[tuple[str, str]]) -> list[tuple[Cond, ...]]:
    """No filter, each single anchored group, and pairs across different columns."""
    out: list[tuple[Cond, ...]] = [()]
    conds = [Cond("text_eq", c, v) for c, v in groups]
    out += [(c,) for c in conds]
    out += [(a, b) for a, b in itertools.combinations(conds, 2) if a.column != b.column]
    return out


def _nearest(cols: list[tuple[str, str]], sentence: str, pos: int) -> str | None:
    best, best_d = None, None
    for col, alias in cols:
        for m in re.finditer(re.escape(alias), sentence, re.IGNORECASE):
            d = abs(m.start() - pos) + (0 if m.start() < pos else 5)
            if best_d is None or d < best_d:
                best, best_d = col, d
    return best


def _proposal(sentence: str, start: int, spec: dict) -> dict:
    return {"quote": sentence, "quote_start": start, "spec": spec}


_CUES = [
    ("sd", re.compile(r"(±|\+/-|\bSD\b|\bs\.d\.|standard deviation)\s*(?:=|of|:)?\s*\(?$", re.IGNORECASE)),
    ("sem", re.compile(r"(\bSEM?\b|\bs\.e\.m?\.|standard error)\s*(?:=|of|:)?\s*\(?$", re.IGNORECASE)),
    ("median", re.compile(r"\bmedian\b[^.;]{0,60}$", re.IGNORECASE)),
    ("mean", re.compile(r"\b(mean|average|averaged|on average)\b[^.;]{0,60}$", re.IGNORECASE)),
    ("count", re.compile(r"\b[nN]\s*=\s*$")),
    ("pearson", re.compile(r"\b(r|Pearson(?:'s)? r|correlation(?: coefficient)?)\s*(?:=|of|was)\s*[-−]?$", re.IGNORECASE)),
    ("max", re.compile(r"\b(maximum|max\.?|up to|highest)\b[^.;]{0,30}$", re.IGNORECASE)),
    ("min", re.compile(r"\b(minimum|min\.?|lowest)\b[^.;]{0,30}$", re.IGNORECASE)),
]


def propose_rules(source_text: str, data: bytes, manifest: dict) -> list[dict]:
    profile = table_profile(data, manifest)
    out = []
    for start, sentence in sentences(source_text):
        cols, groups = _anchored(sentence, manifest, profile)
        single = {}
        for c, v in groups:
            single.setdefault(c, []).append(v)
        filt = [{"kind": "text_eq", "column": c, "value": vs[0]} for c, vs in single.items() if len(vs) == 1]
        for m in NUMBER.finditer(sentence):
            literal = m.group(0).replace(",", "")
            before = sentence[:m.start()]
            unit = _unit_after(sentence, m.end())
            if unit == "%":
                sub = [f for f in filt]
                if len(sub) == 1:
                    out.append(_proposal(sentence, start, {"stat": "share", "reported": literal, "reported_unit": "%", "sub_filter": sub}))
                continue
            stat = next((name for name, cue in _CUES if cue.search(before)), None)
            if stat is None:
                continue
            if stat == "count":
                out.append(_proposal(sentence, start, {"stat": "count", "reported": literal, "filter": filt}))
                continue
            if stat == "pearson":
                if len(cols) == 2:
                    sign = "-" if before.rstrip().endswith(("-", "−")) else ""
                    out.append(_proposal(sentence, start, {"stat": "pearson", "reported": sign + literal,
                                                           "column": cols[0][0], "x_column": cols[1][0], "filter": filt}))
                continue
            column = _nearest(cols, sentence, m.start())
            if column is None:
                continue
            spec = {"stat": stat, "reported": literal, "column": column, "filter": filt}
            ru = _reported_unit(manifest, column, unit)
            if ru:
                spec["reported_unit"] = ru
            out.append(_proposal(sentence, start, spec))
    return out


_SEARCH_STATS = ("mean", "median", "sd_sample", "min", "max", "sem", "sum")


def propose_search(source_text: str, data: bytes, manifest: dict) -> list[dict]:
    profile = table_profile(data, manifest)
    na = tuple(manifest.get("na_tokens") or ["", "NA"])
    out = []
    for start, sentence in sentences(source_text):
        cols, groups = _anchored(sentence, manifest, profile)
        filters = _filters(groups)
        for m in NUMBER.finditer(sentence):
            literal = m.group(0).replace(",", "")
            unit = _unit_after(sentence, m.end())
            candidates: list[dict] = []
            if unit == "%":
                for f in filters:
                    for col, v in groups:
                        if any(c.column == col for c in f):
                            continue
                        candidates.append({"stat": "share", "reported": literal, "reported_unit": "%",
                                           "filter": [c.to_json() for c in f],
                                           "sub_filter": [{"kind": "text_eq", "column": col, "value": v}]})
            else:
                if "." not in literal:
                    for f in filters:
                        candidates.append({"stat": "count", "reported": literal, "filter": [c.to_json() for c in f]})
                for col, _alias in cols:
                    for stat in _SEARCH_STATS:
                        for f in filters:
                            spec = {"stat": stat, "reported": literal, "column": col, "filter": [c.to_json() for c in f]}
                            ru = _reported_unit(manifest, col, unit)
                            if ru:
                                spec["reported_unit"] = ru
                            candidates.append(spec)
                if len(cols) >= 2:
                    for (a, _), (b, _) in itertools.combinations(cols, 2):
                        for f in filters:
                            for lit in (literal, "-" + literal):
                                candidates.append({"stat": "pearson", "reported": lit, "column": a, "x_column": b,
                                                   "filter": [c.to_json() for c in f]})
            matches = []
            for cand in candidates:
                try:
                    spec = ClaimSpec.from_json(cand)
                except ValueError:
                    continue
                data_unit = "fraction" if spec.stat == "share" else ((manifest.get("columns") or {}).get(spec.column or "") or {}).get("unit")
                scale = unit_factor(data_unit, spec.reported_unit)
                if scale is None:
                    continue
                o = evaluate(data, spec, na, scale)
                if o.defined and o.verdict == "consistent":
                    key = (o.value_kind, o.value, o.used, spec.stat in ("count", "share"))
                    if all(k != key for k, _ in matches):
                        matches.append((key, cand))
            if len(matches) == 1:
                out.append(_proposal(sentence, start, matches[0][1]))
    return out
