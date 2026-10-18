"""Theophylline oral PK demo using classic published teaching dataset.

Citations (data origin, not PCS authorship):
- Boeckmann, Sheiner & Beal (1994), NONMEM Users Guide Part V
- Davidian & Giltinan (1995); Pinheiro & Bates (2000)

Scientific honesty:
- Data are oral theophylline concentrations.
- Applying an IV-bolus-only model is a deliberate misspecification → REFUTED.
- Grid-fit Bateman oral model is computational support only, not clinical validation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..adapters.pkpd import predict_concentration, verify_predictions
from ..core.canonical import canonicalize
from ..core.hashing import sha256_file
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from ..falsification.challenges import challenge_causal_overclaim, challenge_data_leakage
from ..falsification.registration import freeze_experiment_plan
from .nca import cmax_tmax, log_linear_terminal_half_life, trapezoidal_auc
from .oral_pk import fit_bateman_grid
from .provenance import FIX, verify_manifest

RAW = FIX / "theophylline" / "raw" / "Theoph.csv"


def load_theoph(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or RAW
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "subject": int(float(r["Subject"])),
                    "wt": float(r["Wt"]),
                    "dose": float(r["Dose"]),  # mg/kg
                    "time": float(r["Time"]),
                    "conc": float(r["conc"]),
                }
            )
    return rows


def by_subject(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r["subject"], []).append(r)
    for sid in out:
        out[sid] = sorted(out[sid], key=lambda x: x["time"])
    return out


def nca_per_subject(subj_rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = [r["time"] for r in subj_rows]
    concs = [r["conc"] for r in subj_rows]
    auc = trapezoidal_auc(times, concs)
    cmax, tmax = cmax_tmax(times, concs)
    t_half = log_linear_terminal_half_life(times, concs, n_terminal=3)
    return {
        "subject": subj_rows[0]["subject"],
        "dose_mg_per_kg": subj_rows[0]["dose"],
        "wt_kg": subj_rows[0]["wt"],
        "auc_0_t": auc,
        "cmax": cmax,
        "tmax": tmax,
        "terminal_t_half": t_half,
        "n_points": len(subj_rows),
    }


def falsify_iv_bolus_on_oral(subj_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Deliberate misspecification: treat oral profile as IV bolus."""
    dose = subj_rows[0]["dose"]
    # Naive V, CL guesses from Cmax/early points — still wrong structure
    cmax, _ = cmax_tmax([r["time"] for r in subj_rows], [r["conc"] for r in subj_rows])
    v = dose / max(cmax, 1e-6)
    cl = 0.1 * v
    model = {"dose": dose, "volume": v, "clearance": cl, "clearance_unit": "L/h", "evidence_kind": "observational"}
    rows = [(r["time"], r["conc"]) for r in subj_rows if r["time"] > 0]
    result = verify_predictions(model, rows, rel_tol=0.05, abs_tol=0.2)
    # Also structural challenge: oral data has rising phase → IV bolus cannot fit tmax>0 well
    tmax = max(subj_rows, key=lambda r: r["conc"])["time"]
    structural = status_record(
        AssuranceStatus.REFUTED if tmax > 0.2 else AssuranceStatus.OPEN,
        claim_class=ClaimClass.SCIENTIFIC_CLAIM,
        reason=f"oral absorption signature: tmax={tmax} h incompatible with pure IV-bolus assumption",
        assumptions=["Theoph dosing route is oral (published description)"],
        limitations=["Misspecification challenge, not a clinical diagnosis"],
    )
    return {"iv_fit_status": result, "structural": structural, "model_tried": model}


def fit_oral_subject(subj_rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = [r["time"] for r in subj_rows]
    concs = [r["conc"] for r in subj_rows]
    dose = subj_rows[0]["dose"]
    fit = fit_bateman_grid(times, concs, dose)
    # residual relative error
    rel = []
    for c, p in zip(concs, fit["predictions"]):
        if c > 0.5:
            rel.append(abs(c - p) / c)
    med_rel = sorted(rel)[len(rel) // 2] if rel else None
    status = (
        AssuranceStatus.COMPUTATIONALLY_TESTED
        if med_rel is not None and med_rel < 0.35
        else AssuranceStatus.CONDITIONAL
    )
    return {
        "fit": {k: fit[k] for k in ("ka", "ke", "V", "sse", "rmse", "proposals")},
        "median_rel_error_gt_0.5": med_rel,
        "status": status_record(
            status,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="deterministic Bateman grid fit on published oral theophylline concentrations",
            assumptions=[
                "One-compartment first-order absorption",
                "F=1 (relative bioavailability absorbed into V)",
                "Grid resolution may miss better parameters",
            ],
            limitations=[
                "Not clinical validation",
                "Not a mixed-effects population model (contrast Pinheiro & Bates 2000)",
            ],
        ),
    }


def run_demo(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    verify_manifest()
    rows = load_theoph()
    subjects = by_subject(rows)

    plan = freeze_experiment_plan(
        {
            "experiment_id": "theoph-oral-bateman-grid-v1",
            "hypotheses": [
                "Oral Bateman model yields median relative error < 0.35 on concentrations > 0.5 mg/L for most subjects",
                "IV-bolus-only model is structurally inadequate for oral Theoph profiles",
            ],
            "outcomes": ["per-subject RMSE", "IV misspecification status"],
            "metrics": ["median_rel_error", "auc_0_t", "cmax", "tmax"],
            "split_rules": {"type": "by_subject", "no_subject_leakage": True},
            "baselines": ["IV bolus closed form", "NCA trapezoidal AUC"],
            "stopping_criteria": {"max_subjects": 12, "grid_proposals_cap": 500},
            "randomization": {"seed": None, "note": "deterministic grid; no RNG"},
            "negative_controls": ["IV bolus on oral data", "causal overclaim language"],
            "planned_comparisons": ["oral_fit vs iv_misspecification"],
            "analysis_class": "confirmatory",
        }
    )

    # subject-wise train/test ids for leakage challenge (even IDs train)
    train_ids = [str(s) for s in subjects if s % 2 == 0]
    test_ids = [str(s) for s in subjects if s % 2 == 1]
    leakage_ok = challenge_data_leakage(train_ids, test_ids).to_status()
    leakage_bad = challenge_data_leakage(train_ids, train_ids[:1] + test_ids).to_status()

    causal = challenge_causal_overclaim(
        "Theophylline causes asthma cure because concentration correlates with time",
        "observational",
    ).to_status()

    per_subj = []
    oral_ok = 0
    for sid, srows in sorted(subjects.items()):
        nca = nca_per_subject(srows)
        oral = fit_oral_subject(srows)
        iv = falsify_iv_bolus_on_oral(srows)
        if oral["status"]["status"] == AssuranceStatus.COMPUTATIONALLY_TESTED.value:
            oral_ok += 1
        per_subj.append({"nca": nca, "oral": oral, "iv_misspecification": iv})

    report = {
        "format": "pcs-next-journal-demo-report-v1",
        "demo_id": "theophylline-pinheiro-bates-teaching-set",
        "citations": [
            "Boeckmann AJ, Sheiner LB, Beal SL. NONMEM Users Guide Part V. 1994.",
            "Davidian M, Giltinan DM. Nonlinear Models for Repeated Measurement Data. 1995.",
            "Pinheiro JC, Bates DM. Mixed-effects Models in S and S-PLUS. 2000.",
        ],
        "data_path": str(RAW.relative_to(FIX.parent.parent)),
        "data_sha256": sha256_file(RAW),
        "n_rows": len(rows),
        "n_subjects": len(subjects),
        "experiment_plan": plan,
        "leakage_split_ok": leakage_ok,
        "leakage_injected_failure": leakage_bad,
        "causal_overclaim": causal,
        "subjects_oral_pass": oral_ok,
        "subjects_total": len(subjects),
        "per_subject": per_subj,
        "aggregate_status": status_record(
            AssuranceStatus.COMPUTATIONALLY_TESTED if oral_ok >= 8 else AssuranceStatus.CONDITIONAL,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"{oral_ok}/{len(subjects)} subjects met oral grid-fit relative-error threshold",
            limitations=[
                "Teaching-dataset demonstration only",
                "External laboratory validation OPEN",
                "Not equivalent to published NLME analyses in Pinheiro & Bates",
            ],
        ),
        "external_lab_validation": status_record(
            AssuranceStatus.OPEN,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason="No outside laboratory re-ran this demo under PCS Next.",
        ),
    }
    (out / "theophylline_report.json").write_bytes(canonicalize(report) + b"\n")
    # compact reviewer card material
    card = {
        "format": "pcs-next-assurance-card-v1",
        "project_id": "journal-demo-theophylline",
        "technical_verification": report["aggregate_status"],
        "scientific_validation": report["external_lab_validation"],
        "formal": status_record(
            AssuranceStatus.CONDITIONAL,
            claim_class=ClaimClass.FORMAL_THEOREM,
            reason="NCA trapezoid nonnegativity covered in isolated Lean; oral fit is computational",
        ),
        "independent": {"status": "OPEN", "limitations": ["Second-process replay available via scripts; not external lab"]},
        "unresolved_questions": [
            "Would a pharmacometrician accept grid-search Bateman fits as sufficient computational evidence?",
            "How should digitized secondary tables be weighted versus primary raw electronic records?",
        ],
        "disclaimer": "Technical verification of fits to a public teaching dataset is not clinical approval.",
        "citations": report["citations"],
    }
    (out / "assurance_card.json").write_bytes(canonicalize(card) + b"\n")
    return report
