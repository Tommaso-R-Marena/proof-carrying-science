#!/usr/bin/env python3
"""Run adapter↔oracle differentials and write a report under results/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pcs_next_v1.adapters.units import clearance_to_L_per_h  # noqa: E402
from pcs_next_v1.adapters.conservation import check_transfer_preserves_total  # noqa: E402
from pcs_next_v1.adapters.metamorphic_pk import check_dose_homogeneity  # noqa: E402
from pcs_next_v1.core.canonical import canonicalize  # noqa: E402
from pcs_next_v1.demos.nca import trapezoidal_auc  # noqa: E402
from pcs_next_v1.demos.oral_pk import bateman  # noqa: E402
from pcs_next_v1.oracles.bateman_oracle import oracle_bateman, oracle_michaelis_menten  # noqa: E402
from pcs_next_v1.oracles.nca_oracle import oracle_trapezoidal_auc  # noqa: E402
from pcs_next_v1.oracles.units_oracle import oracle_clearance_to_L_per_h  # noqa: E402
from pcs_next_v1.oracles.bateman_oracle import mm_sse  # noqa: E402
from pcs_next_v1.demos.puromycin_demo import fit_mm  # noqa: E402


def main() -> int:
    mismatches = []
    # Units
    for unit in ("L/h", "mL/min", "mL/h", "L/min"):
        for v in (0.0, 0.25, 1.0, 10.0, 100.0):
            if abs(clearance_to_L_per_h(v, unit) - oracle_clearance_to_L_per_h(v, unit)) > 1e-15:
                mismatches.append({"kind": "units", "unit": unit, "v": v})
    # NCA
    times = [0.0, 0.5, 1.0, 2.0, 4.0]
    concs = [0.0, 1.2, 2.0, 1.1, 0.4]
    if abs(trapezoidal_auc(times, concs) - oracle_trapezoidal_auc(times, concs)) > 1e-12:
        mismatches.append({"kind": "nca"})
    # Bateman
    for t in (0.0, 0.25, 1.0, 3.0, 8.0):
        if abs(bateman(t, dose=4.0, v=0.5, ka=1.5, ke=0.1) - oracle_bateman(t, 4.0, 0.5, 1.5, 0.1)) > 1e-12:
            mismatches.append({"kind": "bateman", "t": t})
    # MM oracle vs fit grid SSE at oracle point
    concs_m = [0.02, 0.06, 0.11, 0.22, 0.56, 1.1]
    rates = [oracle_michaelis_menten(c, 212, 0.06) for c in concs_m]
    fit = fit_mm(concs_m, rates)
    if fit["vmax"] != 212 or abs(fit["km"] - 0.06) > 1e-12:
        # grid may snap; require SSE near zero at true params
        if mm_sse(212, 0.06, concs_m, rates) > 1e-18:
            mismatches.append({"kind": "mm_oracle_sse"})
    # Metamorphic + conservation runtime mirrors
    if check_dose_homogeneity(50, 5, 0.5, [0, 1, 2, 4], scale=3.0)["status"] != "COMPUTATIONALLY_TESTED":
        mismatches.append({"kind": "metamorphic"})
    if check_transfer_preserves_total(9, 1, 4)["status"] != "COMPUTATIONALLY_TESTED":
        mismatches.append({"kind": "conservation"})

    report = {
        "format": "pcs-next-differential-oracles-v1",
        "n_mismatches": len(mismatches),
        "mismatches": mismatches,
        "status": "COMPUTATIONALLY_TESTED" if not mismatches else "REFUTED",
        "limitations": [
            "Same-host differentials; not an independent external laboratory.",
            "MM fit uses a coarse grid; oracle SSE is the authoritative equality check.",
        ],
    }
    out = ROOT / "results" / "differential_oracles.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonicalize(report) + b"\n")
    print(json.dumps({"status": report["status"], "n_mismatches": report["n_mismatches"]}, indent=2))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
