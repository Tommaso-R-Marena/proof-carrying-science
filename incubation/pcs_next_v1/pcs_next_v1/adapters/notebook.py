"""Jupyter notebook static inspection (no execution)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .python_static import PythonStaticAdapter


SUPPORTED = {
    "fragment": "pcs-next-notebook-static-v1",
    "executes_code": False,
    "limitations": [
        "Cell execution order from metadata may be missing; treated conservatively.",
        "Outputs are not trusted as provenance of computation.",
    ],
}


def inspect_notebook(path: str | Path) -> dict[str, Any]:
    nb = json.loads(Path(path).read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    code_cells = []
    exec_counts = []
    for i, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        code_cells.append({"index": i, "source": src, "execution_count": cell.get("execution_count")})
        exec_counts.append(cell.get("execution_count"))

    order_known = all(c is not None for c in exec_counts) and exec_counts == sorted(
        [c for c in exec_counts if c is not None]
    )
    # concatenate for static analysis
    combined = "\n\n".join(c["source"] for c in code_cells)
    tmp = Path(path).with_suffix(".pcs_next_extracted.py")
    try:
        tmp.write_text(combined, encoding="utf-8")
        py = PythonStaticAdapter().inspect(tmp)
    finally:
        if tmp.exists():
            tmp.unlink()

    return {
        "adapter": SUPPORTED["fragment"],
        "path": str(path),
        "n_code_cells": len(code_cells),
        "execution_order_reliable": bool(order_known),
        "python_static": py,
        "status": "CONDITIONAL" if not order_known else py.get("status"),
        "supported": SUPPORTED,
        "flags": ([] if order_known else ["missing_or_unreliable_execution_order"]) + list(py.get("flags", [])),
    }
