#!/usr/bin/env python3
"""Clean-room style replay of journal demos + independent receipt regeneration.

Runs in-process but records environment identity and refuses producer PASS.
Not a substitute for a second physical laboratory.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

from pcs_next_v1.core.canonical import canonicalize
from pcs_next_v1.core.hashing import sha256_file
from pcs_next_v1.demos.provenance import verify_manifest
from pcs_next_v1.demos.theophylline_demo import run_demo as theoph
from pcs_next_v1.demos.puromycin_demo import run_demo as puro
from pcs_next_v1.oracles.canonical_diff import compare_to_production
from pcs_next_v1.oracles.nca_oracle import oracle_trapezoidal_auc
from pcs_next_v1.demos.nca import trapezoidal_auc
from pcs_next_v1.demos.theophylline_demo import load_theoph, by_subject


def main() -> int:
    t0 = time.perf_counter()
    out = ROOT / "results" / "cleanroom"
    out.mkdir(parents=True, exist_ok=True)
    man = verify_manifest()
    # Oracle correspondence on Theoph subject 1
    subj = by_subject(load_theoph())[1]
    times = [r["time"] for r in subj]
    concs = [r["conc"] for r in subj]
    a = trapezoidal_auc(times, concs)
    b = oracle_trapezoidal_auc(times, concs)
    nca_ok = abs(a - b) < 1e-12
    canon = compare_to_production({"demo": "pcs-next", "n": 2, "x": [1, 2], "flag": True})
    th = theoph(out / "theophylline")
    pu = puro(out / "puromycin")
    report = {
        "format": "pcs-next-cleanroom-replay-v1",
        "seconds": time.perf_counter() - t0,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "manifest_ok": man["ok"],
        "nca_oracle_match": nca_ok,
        "nca_values": {"impl": a, "oracle": b},
        "canonical_diff": canon,
        "theophylline_status": th["aggregate_status"]["status"],
        "puromycin_status": pu["aggregate_status"]["status"],
        "external_lab_validation": "OPEN",
        "limitations": [
            "Same host/process family as development — not an outside laboratory",
            "Producer PASS fields remain ignored by reviewer path",
        ],
        "source_commit_file": str((ROOT / "BASE_SHA.txt").resolve()),
        "base_sha_file_hash": sha256_file(ROOT / "BASE_SHA.txt"),
    }
    (out / "CLEANROOM_REPORT.json").write_bytes(canonicalize(report) + b"\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if nca_ok and man["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
