"""e-Drug3D FDA-approved drug PK property table demo (Zenodo CC BY 4.0).

Citation: Douguet D. (2024). Structures of FDA-approved drugs... Zenodo.
https://doi.org/10.5281/zenodo.17063565
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from .provenance import FIX, verify_manifest

RAW = FIX / "edrug3d" / "raw" / "e-Drug3D_2118_PK.csv"


def _parse_float(x: str) -> float | None:
    x = (x or "").strip()
    if not x:
        return None
    # take first number in cell
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", x.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def load_rows() -> list[dict[str, Any]]:
    text = RAW.read_text(encoding="utf-8", errors="replace").splitlines()
    # header uses " ; " separators
    header = [h.strip() for h in text[0].lstrip("#").split(";")]
    rows = []
    for line in text[1:]:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < len(header):
            parts += [""] * (len(header) - len(parts))
        row = dict(zip(header, parts))
        rows.append(row)
    return rows


def check_half_life_consistency(row: dict[str, Any], *, rel_tol: float = 0.5) -> dict[str, Any] | None:
    """If VD, Cl, t1/2 present: check t1/2 ≈ 0.693 * VD / Cl (1-compartment)."""
    # column names from file
    vd = _parse_float(row.get("VD(liter)", ""))
    cl = _parse_float(row.get("Cl(liter/hour)", ""))
    th = _parse_float(row.get("t1/2(hour)", ""))
    if vd is None or cl is None or th is None or cl <= 0 or vd <= 0 or th <= 0:
        return None
    pred = 0.693147 * vd / cl
    rel = abs(pred - th) / th
    ok = rel <= rel_tol
    return {
        "name": row.get("Name"),
        "VD": vd,
        "Cl": cl,
        "t_half_reported": th,
        "t_half_1cmt_pred": pred,
        "rel_err": rel,
        "consistent_1cmt": ok,
    }


def run_demo(out_dir: str | Path) -> dict[str, Any]:
    verify_manifest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    checks = []
    for row in rows:
        c = check_half_life_consistency(row)
        if c is not None:
            checks.append(c)
    consistent = sum(1 for c in checks if c["consistent_1cmt"])
    inconsistent = [c for c in checks if not c["consistent_1cmt"]][:20]
    report = {
        "format": "pcs-next-journal-demo-report-v1",
        "demo_id": "edrug3d-pk-half-life-consistency",
        "citations": [
            "Douguet D. Structures of FDA-approved drugs and their active metabolites and data sets of experimental PD and PK properties. Zenodo (2024). https://doi.org/10.5281/zenodo.17063565",
        ],
        "license": "CC BY 4.0",
        "n_rows": len(rows),
        "n_with_vd_cl_thalf": len(checks),
        "n_consistent_1cmt_rel50": consistent,
        "inconsistent_examples": inconsistent,
        "aggregate_status": status_record(
            AssuranceStatus.COMPUTATIONALLY_TESTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=(
                f"Checked 1-compartment t1/2↔VD/Cl relation on {len(checks)} complete rows; "
                f"{consistent} within 50% relative tolerance"
            ),
            assumptions=[
                "One-compartment relation is a diagnostic, not a claim that all drugs are 1-compartment",
                "Parsed first numeric token from heterogeneous cells",
                "50% relative tolerance accounts for multi-compartment / reported-range values",
            ],
            limitations=[
                "Inconsistency may reflect multi-compartment kinetics or reporting ranges — not automatically data error",
                "Not a clinical recommendation engine",
            ],
        ),
        "scientific_note": status_record(
            AssuranceStatus.OPEN,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason="Mapping property-table consistency to in vivo adequacy remains scientifically open",
        ),
    }
    (out / "edrug3d_report.json").write_bytes(canonicalize(report) + b"\n")
    return report
