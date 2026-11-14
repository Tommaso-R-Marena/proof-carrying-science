"""Build the planted-error variant of a benchmark document (deterministic, seeded by the slug).

    python -m research.claimcheck_v1.benchmark.mutate SPLIT_DIR/SLUG [...]

About half of the true, derivable numbers are changed in a copy of the article text so that they
become false: either the printed value is perturbed in its last digits, or (where a unit is printed
and convertible) the unit is swapped for a neighbouring one.  Every planted error is confirmed to be
an error by a calculation that shares no code with the system under test (csv module + Decimal).
The original article is never modified; the variant is a synthetic derivative and is labelled so.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from ..replay_independent import scale_for, second_opinion
from .harness import Document

SWAPS = {"mm": "cm", "cm": "mm", "g": "kg", "kg": "g", "mg": "g", "m": "cm", "min": "h", "h": "min", "s": "min"}
UNIT_AFTER = re.compile(r"(\s{0,2})(kg|mg|g|km|cm|mm|m|min|h|s)\b")


def _independent_verdict(doc: Document, spec: dict) -> str | None:
    """consistent / inconsistent / None, from the independent second calculation."""
    stat = "sd_sample" if spec["stat"] == "sd" else spec["stat"]
    full = {"filter": [], "sub_filter": [], "column": None, "x_column": None, "reported_unit": None, **spec}
    try:
        value, _used = second_opinion(doc.data, full, stat, doc.manifest)
        scale = scale_for(full, stat, doc.manifest)
    except Exception:  # noqa: BLE001
        return None
    rep = Decimal(full["reported"])
    mant, _, exp = full["reported"].lower().partition("e")
    half = Decimal(10) ** (int(exp or 0) - len(mant.partition(".")[2])) / 2
    sc = Decimal(scale.numerator) / Decimal(scale.denominator)
    return "consistent" if abs(value * sc - rep) <= half else "inconsistent"


def _perturb(token: str, rng: random.Random) -> str:
    plain = token.replace(",", "")
    if "." in plain:
        whole, frac = plain.split(".")
        digits = len(frac)
        bumped = Fraction(plain) + rng.choice([-1, 1]) * rng.randint(2, 7) * Fraction(1, 10 ** digits)
        if bumped <= 0:
            bumped = Fraction(plain) + rng.randint(2, 7) * Fraction(1, 10 ** digits)
        return f"{float(bumped):.{digits}f}"
    n = int(plain)
    new = n + rng.choice([-2, -1, 1, 2, 3]) if n > 3 else n + rng.randint(1, 3)
    return str(new)


def mutate(root: Path) -> dict:
    doc = Document(root, "original")
    rng = random.Random(int(hashlib.sha256(("claimcheck-mutation-v1:" + doc.slug).encode()).hexdigest(), 16))
    edits, items = [], []
    for item in sorted(doc.gold, key=lambda g: g["start"]):
        new = {k: v for k, v in item.items() if k not in ("start", "end", "context", "occurrence")}
        new["original_token"] = item["token"]
        plan = None
        if item["kind"] == "derivable" and item.get("truth") == "consistent" and rng.random() < 0.5:
            spec = item["gold"][0]
            after = UNIT_AFTER.match(doc.text[item["end"]:item["end"] + 8])
            col_unit = ((doc.manifest.get("columns") or {}).get(spec.get("column") or "") or {}).get("unit")
            if after and col_unit and after.group(2) == (spec.get("reported_unit") or col_unit) and after.group(2) in SWAPS and rng.random() < 0.5:
                unit = SWAPS[after.group(2)]
                cand = dict(spec, reported_unit=None if unit == col_unit else unit)
                if _independent_verdict(doc, cand) == "inconsistent":
                    plan = ("unit_swap", item["end"] + len(after.group(1)), item["end"] + len(after.group(0)), unit, [cand], item["token"])
            if plan is None:
                for _ in range(20):
                    token = _perturb(item["token"], rng)
                    cands = [dict(g, reported=token) for g in item["gold"]]
                    if token != item["token"].replace(",", "") and all(_independent_verdict(doc, c) == "inconsistent" for c in cands):
                        plan = ("value_change", item["start"], item["end"], token, cands, token)
                        break
        if plan:
            kind, a, b, replacement, gold, token = plan
            edits.append((a, b, replacement))
            new.update({"truth": "inconsistent", "gold": gold, "token": token, "planted": kind})
        items.append((item["start"], item["end"], new))
    # apply edits right to left; track offset shifts for every gold item
    text = doc.text
    for a, b, replacement in sorted(edits, reverse=True):
        text = text[:a] + replacement + text[b:]
    out_items = []
    for start, end, new in items:
        shift = sum(len(r) - (b - a) for a, b, r in edits if b <= start)
        own = next((len(r) - (b - a) for a, b, r in edits if a == start and b == end), 0)
        new["start"], new["end"] = start + shift, end + shift + own
        out_items.append(new)
    (root / "article.mutated.txt").write_text(text, encoding="utf-8", newline="")
    (root / "gold.mutated.json").write_text(json.dumps({
        "annotation": "derived deterministically from gold.json by benchmark/mutate.py; planted errors confirmed by an independent calculation",
        "synthetic_variant_of": "article.txt", "items": out_items}, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"slug": doc.slug, "planted": sum(1 for *_x, n in items if n.get("planted")), "items": len(items),
            "kinds": sorted(n["planted"] for *_x, n in items if n.get("planted"))}


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(json.dumps(mutate(Path(arg))))
