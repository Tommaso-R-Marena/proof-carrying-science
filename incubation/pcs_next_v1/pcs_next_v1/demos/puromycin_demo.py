"""Puromycin Michaelis–Menten demo (Bates & Watts / R datasets::Puromycin).

Velocity = Vmax * conc / (Km + conc), separately for treated vs untreated.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from ..oracles.bateman_oracle import mm_sse, oracle_michaelis_menten
from .provenance import FIX, verify_manifest

RAW = FIX / "puromycin" / "raw" / "Puromycin.csv"


def load() -> list[dict[str, Any]]:
    rows = []
    with RAW.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "conc": float(r["conc"]),
                    "rate": float(r["rate"]),
                    "state": r["state"].strip(),
                }
            )
    return rows


def fit_mm(concs: list[float], rates: list[float]) -> dict[str, Any]:
    vmax_grid = [100, 150, 200, 212, 250, 300]
    km_grid = [0.02, 0.04, 0.05, 0.06, 0.08, 0.1, 0.15]
    best = None
    best_sse = float("inf")
    for vmax in vmax_grid:
        for km in km_grid:
            err = mm_sse(vmax, km, concs, rates)
            if err < best_sse:
                best_sse = err
                best = {"vmax": vmax, "km": km, "sse": err}
    assert best is not None
    preds = [oracle_michaelis_menten(c, best["vmax"], best["km"]) for c in concs]
    rels = [abs(r - p) / r for r, p in zip(rates, preds) if r > 0]
    med = sorted(rels)[len(rels) // 2]
    rmse = math.sqrt(best_sse / len(rates))
    st = AssuranceStatus.COMPUTATIONALLY_TESTED if med < 0.25 else AssuranceStatus.CONDITIONAL
    return {
        **best,
        "rmse": rmse,
        "median_rel": med,
        "status": status_record(
            st,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"MM grid median_rel={med:.3f}",
            assumptions=["Michaelis–Menten single-substrate kinetics", "Deterministic coarse grid"],
            limitations=["Not a statistical mixed model; not biochemical discovery"],
        ),
    }


def falsify_linear(concs: list[float], rates: list[float]) -> dict[str, Any]:
    """Negative control: force through origin linear rate = k*conc."""
    # LS slope
    num = sum(c * r for c, r in zip(concs, rates))
    den = sum(c * c for c in concs) or 1.0
    k = num / den
    rels = [abs(r - k * c) / r for c, r in zip(concs, rates) if r > 0]
    med = sorted(rels)[len(rels) // 2]
    return status_record(
        AssuranceStatus.REFUTED if med > 0.25 else AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason=f"linear-through-origin median_rel={med:.3f} (negative control vs MM saturation)",
        limitations=["Deliberate misspecification control"],
    )


def register_group_params(rows: list[dict[str, Any]] | None = None) -> dict[str, dict[str, float]]:
    """Fit MM parameters per state group — used as a registration pin for label checks."""
    data = rows if rows is not None else load()
    groups: dict[str, list] = {}
    for r in data:
        groups.setdefault(r["state"], []).append(r)
    reg: dict[str, dict[str, float]] = {}
    for state, grows in groups.items():
        fit = fit_mm([g["conc"] for g in grows], [g["rate"] for g in grows])
        reg[state] = {"vmax": float(fit["vmax"]), "km": float(fit["km"])}
    return reg


def check_labels_against_registration(
    rows: list[dict[str, Any]],
    registration: dict[str, dict[str, float]],
    *,
    rel_tol: float = 0.15,
) -> dict[str, Any]:
    from ..adapters.tabular_integrity import check_registered_group_params

    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["state"], []).append(r)
    observed: dict[str, dict[str, float]] = {}
    for state, grows in groups.items():
        fit = fit_mm([g["conc"] for g in grows], [g["rate"] for g in grows])
        observed[state] = {"vmax": float(fit["vmax"]), "km": float(fit["km"])}
    return check_registered_group_params(observed, registration, rel_tol=rel_tol)


def run_demo(out_dir: str | Path) -> dict[str, Any]:
    verify_manifest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = load()
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["state"], []).append(r)
    per = {}
    passes = 0
    for state, grows in groups.items():
        concs = [g["conc"] for g in grows]
        rates = [g["rate"] for g in grows]
        fit = fit_mm(concs, rates)
        lin = falsify_linear(concs, rates)
        if fit["status"]["status"] == AssuranceStatus.COMPUTATIONALLY_TESTED.value:
            passes += 1
        per[state] = {
            "n": len(grows),
            "fit": {k: fit[k] for k in ("vmax", "km", "rmse", "median_rel")},
            "status": fit["status"],
            "linear_negative_control": lin,
        }
    report = {
        "format": "pcs-next-journal-demo-report-v1",
        "demo_id": "puromycin-michaelis-menten-bates-watts",
        "citations": [
            "Bates DM, Watts DG. Nonlinear Regression Analysis and Its Applications. Wiley, 1988.",
            "R datasets::Puromycin (Treated/untreated enzyme velocity vs substrate concentration).",
        ],
        "n_rows": len(rows),
        "groups": per,
        "groups_pass": passes,
        "aggregate_status": status_record(
            AssuranceStatus.COMPUTATIONALLY_TESTED if passes == len(groups) else AssuranceStatus.CONDITIONAL,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"MM grid passed for {passes}/{len(groups)} state groups; linear control assessed",
            limitations=["Teaching dataset demonstration", "External lab OPEN"],
        ),
        "external_lab_validation": status_record(
            AssuranceStatus.OPEN,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason="No outside laboratory completed this demo.",
        ),
    }
    (out / "puromycin_report.json").write_bytes(canonicalize(report) + b"\n")
    return report
