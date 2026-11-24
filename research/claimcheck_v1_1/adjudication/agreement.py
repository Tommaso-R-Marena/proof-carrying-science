"""Agreement and timing from returned adjudication sheets (feasibility study, parts A and B).

    python -m research.claimcheck_v1_1.adjudication.agreement RETURNS_DIR [--out results.json]

RETURNS_DIR holds one directory per adjudicator, each with one directory per paper containing the
returned `sheet.csv`, and a `time_log.csv` (`paper,minutes_reading,minutes_classifying,notes`).
Computes, for the first two adjudicators (sorted by name):

* raw agreement and Cohen's kappa on the class T / F / N / A, with a percentile interval from a
  bootstrap over papers (numbers within a paper are not independent);
* the A share (labels A among all labels) per adjudicator and over both;
* the items they disagree on, for the resolver;
* minutes per paper per adjudicator (median, and each paper).

It reads human judgements and makes none.  It is not run on any real return yet: none exists.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from pathlib import Path

CLASSES = ("T", "F", "N", "A")


def read_sheets(folder: Path) -> dict[str, dict[str, str]]:
    """{paper: {item: class}} for one adjudicator; blank or unknown classes are kept as ''."""
    out: dict[str, dict[str, str]] = {}
    for sheet in sorted(folder.glob("*/sheet.csv")):
        with sheet.open(newline="", encoding="utf-8") as fh:
            out[sheet.parent.name] = {row["item"]: (row.get("class_T_F_N_A") or "").strip().upper() for row in csv.DictReader(fh)}
    return out


def read_times(folder: Path) -> dict[str, float]:
    path = folder / "time_log.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {r["paper"]: float(r["minutes_reading"] or 0) + float(r["minutes_classifying"] or 0) for r in csv.DictReader(fh)}


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == k for a, _ in pairs) / n) * (sum(b == k for _, b in pairs) / n) for k in CLASSES)
    return None if pe == 1 else (po - pe) / (1 - pe)


def analyse(returns: Path, seed: int = 20261119, resamples: int = 2000) -> dict:
    raters = sorted(p.name for p in returns.iterdir() if p.is_dir())
    if len(raters) < 2:
        raise SystemExit("need the returns of two adjudicators")
    a_name, b_name = raters[:2]
    a, b = read_sheets(returns / a_name), read_sheets(returns / b_name)
    papers = sorted(set(a) & set(b))
    by_paper = {p: [(a[p][i], b[p][i], i) for i in sorted(set(a[p]) & set(b[p]))] for p in papers}
    pairs = [(x, y) for p in papers for x, y, _ in by_paper[p]]
    invalid = [i for p in papers for x, y, i in by_paper[p] if x not in CLASSES or y not in CLASSES]
    rng = random.Random(seed)
    boot = []
    for _ in range(resamples if len(papers) > 1 else 0):
        sample = [rng.choice(papers) for _ in papers]
        k = kappa([(x, y) for p in sample for x, y, _ in by_paper[p]])
        if k is not None:
            boot.append(k)
    boot.sort()
    labels_a = [x for x, _ in pairs]
    labels_b = [y for _, y in pairs]
    times = {r: read_times(returns / r) for r in (a_name, b_name)}
    return {
        "adjudicators": [a_name, b_name], "papers": len(papers), "numbers": len(pairs),
        "invalid_or_missing_classes": invalid,
        "raw_agreement": round(sum(x == y for x, y in pairs) / len(pairs), 4) if pairs else None,
        "kappa": None if kappa(pairs) is None else round(kappa(pairs), 4),
        "kappa_interval_95_bootstrap_over_papers": [round(boot[int(0.025 * len(boot))], 4), round(boot[int(0.975 * len(boot)) - 1], 4)] if boot else None,
        "a_share": {a_name: round(labels_a.count("A") / len(labels_a), 4) if labels_a else None,
                    b_name: round(labels_b.count("A") / len(labels_b), 4) if labels_b else None,
                    "both": round((labels_a.count("A") + labels_b.count("A")) / (2 * len(pairs)), 4) if pairs else None},
        "for_the_resolver": [{"paper": p, "item": i, a_name: x, b_name: y} for p in papers for x, y, i in by_paper[p] if x != y],
        "minutes_per_paper": {r: {"median": statistics.median(t.values()) if t else None, "papers": t} for r, t in times.items()},
        "note": "development-set adjudication; enters no criterion",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("returns", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    result = analyse(args.returns)
    text = json.dumps(result, indent=1) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
