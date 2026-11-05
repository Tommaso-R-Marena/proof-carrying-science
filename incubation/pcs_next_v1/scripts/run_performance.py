#!/usr/bin/env python3
"""Performance measurements for journal-scale workloads."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pcs_next_v1.core.canonical import canonicalize
from pcs_next_v1.demos.edrug3d_demo import load_rows, check_half_life_consistency
from pcs_next_v1.demos.theophylline_demo import load_theoph, by_subject, fit_oral_subject
from pcs_next_v1.core.canonical import canonicalize as can


def timed(fn, *a, **k):
    t0 = time.perf_counter()
    out = fn(*a, **k)
    return out, time.perf_counter() - t0


def main() -> int:
    rows, t_load = timed(load_rows)
    checks = []
    t0 = time.perf_counter()
    for r in rows:
        c = check_half_life_consistency(r)
        if c:
            checks.append(c)
    t_check = time.perf_counter() - t0
    # cold theoph fits
    subj = by_subject(load_theoph())
    t0 = time.perf_counter()
    for srows in subj.values():
        fit_oral_subject(srows)
    t_theoph = time.perf_counter() - t0
    payload = {"n_checks": len(checks), "n_rows": len(rows)}
    t0 = time.perf_counter()
    for _ in range(100):
        can(payload)
    t_canon = time.perf_counter() - t0
    report = {
        "format": "pcs-next-performance-report-v1",
        "edrug3d_load_s": t_load,
        "edrug3d_consistency_s": t_check,
        "edrug3d_rows": len(rows),
        "edrug3d_complete_rows": len(checks),
        "theoph_all_subjects_fit_s": t_theoph,
        "canonical_100_iters_s": t_canon,
        "notes": ["Cold runs; no cache", "Not a claim of production SLA"],
    }
    out = ROOT / "results" / "performance_report.json"
    out.write_bytes(canonicalize(report) + b"\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
