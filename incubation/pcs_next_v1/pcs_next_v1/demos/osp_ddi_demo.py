"""OSP digitized DDI literature database demo.

Upstream: Open-Systems-Pharmacology/Database-for-observed-data v1.9
Values are digitized from cited peer-reviewed papers (see Reference column).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from .provenance import FIX, verify_manifest

RAW = FIX / "osp_ddi" / "raw" / "DDI.csv"


def load() -> list[dict[str, str]]:
    with RAW.open(newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def run_demo(out_dir: str | Path) -> dict[str, Any]:
    verify_manifest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = load()
    missing_ref = [r for r in rows if not (r.get("Reference") or "").strip()]
    # AUCR Avg should be positive when present
    bad_aucr = []
    aucr_vals = []
    for r in rows:
        raw = (r.get("AUCR Avg") or "").strip()
        if not raw:
            continue
        try:
            v = float(raw)
        except ValueError:
            bad_aucr.append({"id": r.get("ID"), "AUCR Avg": raw, "reason": "non-numeric"})
            continue
        aucr_vals.append(v)
        if v <= 0:
            bad_aucr.append({"id": r.get("ID"), "AUCR Avg": v, "reason": "non-positive"})

    # Mechanism vocabulary sanity
    mechanisms = sorted({(r.get("Mechanism") or "").strip() for r in rows if (r.get("Mechanism") or "").strip()})

    report = {
        "format": "pcs-next-journal-demo-report-v1",
        "demo_id": "osp-ddi-literature-digitization-checks",
        "citations": [
            "Open Systems Pharmacology. Database for observed data v1.9. https://github.com/Open-Systems-Pharmacology/Database-for-observed-data",
            "Each row retains its original paper Reference string for traceability.",
        ],
        "n_rows": len(rows),
        "n_missing_reference": len(missing_ref),
        "n_aucr_values": len(aucr_vals),
        "n_bad_aucr": len(bad_aucr),
        "mechanism_labels": mechanisms[:50],
        "bad_aucr_examples": bad_aucr[:20],
        "aggregate_status": status_record(
            AssuranceStatus.REFUTED if missing_ref or bad_aucr else AssuranceStatus.COMPUTATIONALLY_TESTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=(
                "Schema/provenance checks on digitized DDI table: "
                f"missing_ref={len(missing_ref)}, bad_aucr={len(bad_aucr)}"
            ),
            limitations=[
                "Digitized secondary data may differ from primary figures",
                "PCS does not re-digitize source papers in this demo",
                "Not a regulatory DDI qualification package",
            ],
        ),
        "external_lab_validation": status_record(
            AssuranceStatus.OPEN,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason="Independent re-digitization against primary papers not performed here.",
        ),
    }
    # If missing refs are zero and aucr ok, tested; else refuted for data-quality claims
    (out / "osp_ddi_report.json").write_bytes(canonicalize(report) + b"\n")
    return report
