from __future__ import annotations
import csv
from pathlib import Path


def csv_key_disjoint(left: str | Path, right: str | Path, key: str) -> tuple[bool, dict]:
    def load(path: str | Path) -> set[str]:
        with Path(path).open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or key not in reader.fieldnames:
                raise ValueError(f"missing key column {key!r} in {path}")
            return {row[key] for row in reader}

    a, b = load(left), load(right)
    overlap = sorted(a & b)
    return (not overlap, {
        "key": key,
        "left_unique": len(a),
        "right_unique": len(b),
        "overlap_count": len(overlap),
        "overlap_sample": overlap[:20],
    })
