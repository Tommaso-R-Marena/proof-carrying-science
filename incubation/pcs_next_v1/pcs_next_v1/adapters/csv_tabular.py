"""CSV / tabular experiment adapter."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


SUPPORTED = {
    "fragment": "pcs-next-csv-tabular-v1",
    "limitations": ["Schema/consistency only; not scientific validity."],
}


def inspect_csv(path: str | Path, *, required_columns: list[str] | None = None) -> dict[str, Any]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {"status": "REFUTED", "reason": "missing header", "supported": SUPPORTED}
        cols = list(reader.fieldnames)
        if len(cols) != len(set(cols)):
            return {"status": "REFUTED", "reason": "duplicate columns", "supported": SUPPORTED}
        rows = list(reader)
    missing = [c for c in (required_columns or []) if c not in cols]
    if missing:
        return {"status": "REFUTED", "reason": f"missing columns {missing}", "columns": cols, "supported": SUPPORTED}
    return {
        "adapter": SUPPORTED["fragment"],
        "columns": cols,
        "n_rows": len(rows),
        "status": "COMPUTATIONALLY_TESTED",
        "supported": SUPPORTED,
    }
