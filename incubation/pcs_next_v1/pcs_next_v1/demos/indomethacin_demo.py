"""Indomethacin IV PK demo (R datasets::Indometh).

Classic teaching data often require biexponential disposition.
This demo treats monoexponential fit as a negative control and uses a
deterministic biexponential grid as the supported computational fragment.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from .nca import log_linear_terminal_half_life, trapezoidal_auc
from .provenance import FIX, verify_manifest

RAW = FIX / "indomethacin" / "raw" / "Indometh.csv"


def load() -> list[dict[str, Any]]:
    rows = []
    with RAW.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "subject": int(float(r["Subject"])),
                    "time": float(r["time"]),
                    "conc": float(r["conc"]),
                }
            )
    return rows


def monoexponential_sse(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pts = [(r["time"], r["conc"]) for r in rows if r["time"] > 0 and r["conc"] > 0]
    xs = [t for t, _ in pts]
    ys = [math.log(c) for _, c in pts]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs) or 1.0
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    intercept = my - slope * mx
    k = -slope
    c0 = math.exp(intercept)
    sse = 0.0
    preds = []
    for t, c in pts:
        p = c0 * math.exp(-k * t)
        preds.append(p)
        sse += (p - c) ** 2
    rmse = math.sqrt(sse / len(pts))
    med_rel = sorted(abs(c - p) / c for (t, c), p in zip(pts, preds) if c > 0.2)
    med = med_rel[len(med_rel) // 2] if med_rel else 999.0
    return {
        "k": k,
        "c0": c0,
        "rmse": rmse,
        "median_rel": med,
        "status": status_record(
            AssuranceStatus.REFUTED if med > 0.35 else AssuranceStatus.COMPUTATIONALLY_TESTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"monoexponential median_rel={med:.3f}",
            limitations=["Negative control for Indometh; literature typically biexponential"],
        ),
    }


def biexponential(t: float, A: float, alpha: float, B: float, beta: float) -> float:
    return A * math.exp(-alpha * t) + B * math.exp(-beta * t)


def fit_biexponential(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pts = [(r["time"], r["conc"]) for r in rows if r["conc"] > 0]
    # Deterministic coarse grid
    alphas = [1.5, 2.0, 3.0, 4.0, 6.0]
    betas = [0.05, 0.08, 0.1, 0.15, 0.25]
    As = [1.0, 1.5, 2.0, 3.0, 4.0]
    Bs = [0.2, 0.4, 0.6, 0.8, 1.0]
    best = None
    best_sse = float("inf")
    proposals = 0
    for A in As:
        for alpha in alphas:
            for B in Bs:
                for beta in betas:
                    if alpha <= beta:
                        continue
                    proposals += 1
                    sse = 0.0
                    for t, c in pts:
                        sse += (biexponential(t, A, alpha, B, beta) - c) ** 2
                    if sse < best_sse:
                        best_sse = sse
                        best = {"A": A, "alpha": alpha, "B": B, "beta": beta, "sse": sse}
    assert best is not None
    preds = [biexponential(t, best["A"], best["alpha"], best["B"], best["beta"]) for t, _ in pts]
    rels = [abs(c - p) / c for (t, c), p in zip(pts, preds) if c > 0.2]
    med = sorted(rels)[len(rels) // 2] if rels else 999.0
    rmse = math.sqrt(best_sse / len(pts))
    st = (
        AssuranceStatus.COMPUTATIONALLY_TESTED
        if med < 0.35
        else AssuranceStatus.CONDITIONAL
    )
    return {
        **best,
        "rmse": rmse,
        "median_rel": med,
        "proposals": proposals,
        "status": status_record(
            st,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"biexponential grid median_rel={med:.3f}",
            assumptions=["IV two-exponential disposition", "Deterministic coarse grid"],
            limitations=["Not NLME; not clinical validation"],
        ),
    }


def run_demo(out_dir: str | Path) -> dict[str, Any]:
    verify_manifest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = load()
    by: dict[int, list] = {}
    for r in rows:
        by.setdefault(r["subject"], []).append(r)
    results = []
    bi_pass = 0
    mono_refute = 0
    for sid, srows in sorted(by.items()):
        srows = sorted(srows, key=lambda x: x["time"])
        mono = monoexponential_sse(srows)
        bi = fit_biexponential(srows)
        if bi["status"]["status"] == AssuranceStatus.COMPUTATIONALLY_TESTED.value:
            bi_pass += 1
        if mono["status"]["status"] == AssuranceStatus.REFUTED.value:
            mono_refute += 1
        auc = trapezoidal_auc([r["time"] for r in srows], [r["conc"] for r in srows])
        t_half = log_linear_terminal_half_life([r["time"] for r in srows], [r["conc"] for r in srows])
        results.append(
            {
                "subject": sid,
                "auc": auc,
                "t_half": t_half,
                "mono": {"median_rel": mono["median_rel"], "status": mono["status"]["status"]},
                "biexponential": {
                    "median_rel": bi["median_rel"],
                    "status": bi["status"]["status"],
                    "params": {k: bi[k] for k in ("A", "alpha", "B", "beta", "rmse")},
                },
            }
        )
    report = {
        "format": "pcs-next-journal-demo-report-v1",
        "demo_id": "indomethacin-iv-biexponential-with-mono-negative-control",
        "citations": [
            "Kwan KC et al., indomethacin kinetics (classic PK literature; R datasets::Indometh redistribution).",
            "Pinheiro & Bates companion dataset distribution.",
        ],
        "n_subjects": len(by),
        "biexponential_pass": bi_pass,
        "monoexponential_refuted": mono_refute,
        "per_subject": results,
        "negative_control": status_record(
            AssuranceStatus.REFUTED if mono_refute == len(by) else AssuranceStatus.CONDITIONAL,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason=f"monoexponential inadequate for {mono_refute}/{len(by)} subjects — expected from biexponential literature",
        ),
        "aggregate_status": status_record(
            AssuranceStatus.COMPUTATIONALLY_TESTED if bi_pass >= 4 else AssuranceStatus.CONDITIONAL,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"biexponential grid passed for {bi_pass}/{len(by)} subjects; mono negative control refuted {mono_refute}/{len(by)}",
            limitations=["Grid resolution limits", "Not clinical validation", "External lab OPEN"],
        ),
        "external_lab_validation": status_record(
            AssuranceStatus.OPEN,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason="No outside laboratory completed this demo.",
        ),
    }
    (out / "indomethacin_report.json").write_bytes(canonicalize(report) + b"\n")
    return report
