from __future__ import annotations

import json
from pathlib import Path


class ScaffoldError(ValueError):
    pass


_MODEL = {
    "model_type": "one_compartment_iv_bolus",
    "dose": {"value": 100.0, "unit": "mg"},
    "volume": {"value": 20.0, "unit": "L"},
    "clearance": {"value": 2.0, "unit": "L/h"},
    "time_unit": "h",
    "concentration_unit": "mg/L",
    "pd": {
        "model_type": "direct_emax",
        "effect_unit": "1",
        "e0": {"value": 0.0, "unit": "1"},
        "emax": {"value": 1.0, "unit": "1"},
        "ec50": {"value": 2.0, "unit": "mg/L"},
    },
}


def _predictions() -> str:
    import math
    dose, vol, cl = 100.0, 20.0, 2.0
    e0, emax, ec50 = 0.0, 1.0, 2.0
    rows = ["time,concentration,effect"]
    for t in (0.0, 1.0, 2.0, 4.0, 8.0):
        c = (dose / vol) * math.exp(-(cl / vol) * t)
        e = e0 + emax * c / (ec50 + c)
        rows.append(f"{t:.12g},{c:.16g},{e:.16g}")
    return "\n".join(rows) + "\n"


def _manifest(subject: str) -> dict:
    return {
        "subject": subject,
        "assumptions": [{"id":"A_PKPD_MODEL","statement":"The restricted one-compartment IV-bolus PK plus direct Emax PD equations are the declared computational model; no claim of biological or clinical adequacy is made.","rationale":"Separates computational assurance from empirical model validation.","scope":["C_PKPD_CONTRACT","C_PKPD_REPLAY"]}],
        "claims": [
            {"id":"C_PKPD_CONTRACT","statement":"The PK/PD model artifact satisfies the restricted positivity and dimensional contract.","kind":"computational","required_evidence":["E_PKPD_CONTRACT"],"assumptions":["A_PKPD_MODEL"],"predicate":{"type":"pkpd_contract","model_artifact":"pkpd_model"}},
            {"id":"C_PKPD_REPLAY","statement":"The prediction artifact matches the declared restricted PK/PD equations within the stated numeric tolerance.","kind":"computational","required_evidence":["E_PKPD_REPLAY"],"assumptions":["A_PKPD_MODEL"],"predicate":{"type":"pkpd_reference_match","model_artifact":"pkpd_model","output_artifact":"pkpd_predictions","time_column":"time","concentration_column":"concentration","effect_column":"effect","rel_tol":1e-9,"abs_tol":1e-12}}
        ],
        "artifacts": [
            {"id":"pkpd_model","path":"model.json","role":"restricted-pkpd-model","media_type":"application/json"},
            {"id":"pkpd_predictions","path":"predictions.csv","role":"pkpd-predictions","media_type":"text/csv"}
        ],
        "checks": [
            {"id":"E_PKPD_CONTRACT","type":"pkpd_contract","claim_ids":["C_PKPD_CONTRACT"],"model_artifact":"pkpd_model"},
            {"id":"E_PKPD_REPLAY","type":"pkpd_reference_match","claim_ids":["C_PKPD_REPLAY"],"model_artifact":"pkpd_model","output_artifact":"pkpd_predictions","time_column":"time","concentration_column":"concentration","effect_column":"effect","rel_tol":1e-9,"abs_tol":1e-12}
        ],
        "workflow":{"nodes":[{"id":"N_PKPD","operation":"restricted_one_compartment_iv_bolus_direct_emax","inputs":["pkpd_model"],"outputs":["pkpd_predictions"],"contract":{"equations":["C(t)=(Dose/V)*exp(-(CL/V)*t)","E(C)=E0+Emax*C/(EC50+C)"],"validation_scope":"computational replay only; not empirical adequacy"}}]}
    }


def _pilot_intake(subject: str, manifest: dict) -> dict:
    return {
        "intake_format": "pcs-pilot-intake-v1",
        "pilot_id": f"{subject}-intake",
        "workflow_summary": (
            "Restricted one-compartment IV-bolus PK plus direct Emax PD computational assurance starter."
        ),
        "claims": [
            {
                "id": c["id"],
                "statement": c["statement"],
                "desired_assurance": c["kind"],
                "rationale": "Frozen before attestation so the target claim cannot be weakened after seeing results.",
            }
            for c in manifest["claims"]
        ],
        "assumptions": [
            {"id": a["id"], "statement": a["statement"]}
            for a in manifest.get("assumptions", [])
        ],
        "data_classification": "synthetic",
        "notes": "Starter intake. Replace with the design partner's agreed claims before running a real pilot.",
    }


def init_project(destination: str | Path, *, template: str = "pkpd", subject: str | None = None, force: bool = False) -> dict[str, object]:
    if template != "pkpd":
        raise ScaffoldError(f"unsupported template: {template!r}")
    root = Path(destination).resolve()
    if root.exists() and any(root.iterdir()) and not force:
        raise ScaffoldError(f"destination is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    subject = subject or root.name
    readme = (
        "# PCS PK/PD starter\n\n"
        "This starter demonstrates computational assurance for a restricted one-compartment IV-bolus PK model with a direct Emax PD layer.\n\n"
        "Replace the synthetic model and output with your bounded workflow, freeze the agreed claims, then run:\n\n"
        "    pcs freeze-intake pilot_intake.json -o pilot_intake.lock.json\n"
        "    pcs attest manifest.json -o evidence --intake-lock pilot_intake.lock.json\n"
        "    pcs verify evidence/certificate.json\n\n"
        "Passing checks establish only the declared computational properties. They do not establish biological or clinical adequacy.\n"
    )
    manifest = _manifest(subject)
    files = {
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        "pilot_intake.json": json.dumps(_pilot_intake(subject, manifest), indent=2, sort_keys=True) + "\n",
        "model.json": json.dumps(_MODEL, indent=2, sort_keys=True) + "\n",
        "predictions.csv": _predictions(),
        "README.md": readme,
    }
    for rel, content in files.items():
        (root / rel).write_text(content, encoding="utf-8")
    return {"destination": str(root), "template": template, "subject": subject, "files": sorted(files)}
