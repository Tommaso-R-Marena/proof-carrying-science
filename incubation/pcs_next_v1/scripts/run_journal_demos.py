#!/usr/bin/env python3
"""Run all public journal-backed demos and emit aggregate evidence."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

from pcs_next_v1.core.canonical import canonicalize
from pcs_next_v1.demos.edrug3d_demo import run_demo as edrug
from pcs_next_v1.demos.indomethacin_demo import run_demo as indo
from pcs_next_v1.demos.osp_ddi_demo import run_demo as osp
from pcs_next_v1.demos.provenance import verify_manifest
from pcs_next_v1.demos.theophylline_demo import run_demo as theoph
from pcs_next_v1.demos.paper_claim_demo import run_demo as paper_claim
from pcs_next_v1.demos.puromycin_demo import run_demo as puro
from pcs_next_v1.pilot.runner import PilotRunner
from pcs_next_v1.reviewer.assurance_card import export_card, render_html
from pcs_next_v1.reviewer.independent import review_package
from pcs_next_v1.trust.policy import pin_policy
from pcs_next_v1.core.canonical import loads_strict


def package_theoph_as_pilot(out: Path) -> dict:
    """Drive Theoph demo artifacts through the independent pilot pipeline."""
    project = out / "theophylline_pilot_project"
    project.mkdir(parents=True, exist_ok=True)
    # pointer artifacts
    src = ROOT / "fixtures/journal_demos/theophylline/raw/Theoph.csv"
    (project / "Theoph.csv").write_bytes(src.read_bytes())
    report = json.loads((out / "theophylline" / "theophylline_report.json").read_text())
    (project / "demo_report.json").write_text(json.dumps(report["aggregate_status"], indent=2) + "\n")
    (project / "analyze_theoph.py").write_text(
        "# Non-executing discovery target for journal demo\n"
        "import csv\n"
        "rows=list(csv.DictReader(open('Theoph.csv')))\n"
        "assert len(rows)==132\n",
        encoding="utf-8",
    )
    intake = {
        "format": "pcs-next-intake-v1",
        "project_id": "journal-theophylline-demo",
        "scientific_domain": "pharmacokinetics",
        "workflow_purpose": "Assure computational handling of classic published theophylline teaching data",
        "artifacts": [
            {"id": "theoph", "path": "Theoph.csv", "role": "input", "media_type": "text/csv"},
            {"id": "report", "path": "demo_report.json", "role": "output", "media_type": "application/json"},
            {"id": "code", "path": "analyze_theoph.py", "role": "code", "media_type": "text/x-python"},
        ],
        "claimed_conclusions": [
            {
                "id": "c1",
                "text": "Oral Bateman grid fits achieve median relative error < 0.35 for most subjects on Theoph.",
                "kind": "computational",
            },
            {
                "id": "c2",
                "text": "IV-bolus-only models are structurally inadequate for oral Theoph profiles.",
                "kind": "methodological",
            },
        ],
        "computational_assertions": [
            {"id": "a1", "statement": "NCA trapezoidal AUC is nonnegative for nonnegative concentrations", "method": "nca"}
        ],
        "assumptions": [
            {"id": "s1", "text": "Dataset matches R datasets::Theoph redistribution", "discharged": False},
            {"id": "s2", "text": "Oral dosing route as described in published sources", "discharged": False},
        ],
        "models": [{"id": "bateman", "class": "oral_one_compartment_first_order_absorption"}],
        "software_dependencies": [{"name": "python", "version": ">=3.11"}],
        "numerical_methods": [{"name": "trapezoidal_auc"}, {"name": "bateman_grid_search"}],
        "verification_boundaries": [
            "Computational/methodological claims only",
            "No clinical efficacy claims",
            "External lab validation OPEN",
        ],
        "expected_outputs": [{"id": "o1", "path": "demo_report.json"}],
        "data_handling_classification": "public",
        "publication_permissions": "public teaching dataset; cite Boeckmann/Sheiner/Beal and Pinheiro & Bates",
        "unresolved_questions": report.get("external_lab_validation", {}).get("reason", "OPEN"),
        "reviewer_identities": [{"id": "pcs-next-automated", "role": "demo"}],
    }
    # fix unresolved_questions type
    intake["unresolved_questions"] = [
        "Would an independent pharmacometrics lab reproduce these grid-fit thresholds?",
        "Should secondary redistributions require byte-identity with a canonical archive?",
    ]
    policy = pin_policy(
        loads_strict((ROOT / "fixtures/synthetic_pilot/acceptance_policy.json").read_bytes())
    )
    # customize policy id note
    raw = dict(policy.raw)
    raw["policy_id"] = "pcs-next-receiver-journal-demo"
    policy = pin_policy(raw)
    work = out / "theophylline_pilot_work"
    runner = PilotRunner(work, policy=policy, repo_root=REPO)
    assurance = runner.run_synthetic(project, intake)
    pkg = work / "package"
    pkg.mkdir(exist_ok=True)
    for name in ("intake.lock.json", "evidence_bundle.json"):
        (pkg / name).write_bytes((work / name).read_bytes())
    (pkg / "acceptance_policy.json").write_bytes(canonicalize(policy.raw) + b"\n")
    receipt = review_package(pkg, receiver_policy=policy)
    # Overlay journal-demo technical status onto the pilot assurance card.
    demo_status = report["aggregate_status"]
    assurance = dict(assurance)
    statuses = dict(assurance.get("statuses") or {})
    statuses["computational_replay"] = demo_status
    statuses["journal_demo"] = {
        "demo_id": report["demo_id"],
        "subjects_oral_pass": report.get("subjects_oral_pass"),
        "subjects_total": report.get("subjects_total"),
        "citations": report.get("citations"),
    }
    assurance["statuses"] = statuses
    card = export_card(
        assurance,
        work / "card",
        claims=intake["claimed_conclusions"],
    )
    # Ensure technical_verification is the journal aggregate, not null CSV check
    card["technical_verification"] = demo_status
    card["citations"] = report.get("citations")
    (work / "card" / "assurance_card.json").write_bytes(canonicalize(card) + b"\n")
    (work / "card" / "assurance_card.html").write_text(render_html(card), encoding="utf-8")
    (work / "assurance_report.json").write_bytes(canonicalize(assurance) + b"\n")
    return {"assurance": assurance, "receipt": receipt, "card": card}


def main() -> int:
    t0 = time.perf_counter()
    out = ROOT / "results" / "journal_demos"
    out.mkdir(parents=True, exist_ok=True)
    man = verify_manifest()
    reports = {
        "manifest": man,
        "theophylline": theoph(out / "theophylline"),
        "indomethacin": indo(out / "indomethacin"),
        "edrug3d": edrug(out / "edrug3d"),
        "osp_ddi": osp(out / "osp_ddi"),
        "paper_claims": paper_claim(out / "paper_claims"),
        "puromycin": puro(out / "puromycin"),
    }
    pilot = package_theoph_as_pilot(out)
    summary = {
        "format": "pcs-next-journal-demos-summary-v1",
        "seconds": time.perf_counter() - t0,
        "demos": {
            k: {
                "demo_id": v.get("demo_id"),
                "aggregate_status": (v.get("aggregate_status") or {}).get("status"),
                "external": (v.get("external_lab_validation") or v.get("scientific_note") or {}).get("status"),
            }
            for k, v in reports.items()
            if k != "manifest"
        },
        "theophylline_pilot": {
            "independent": pilot["receipt"]["status"],
            "external_lab": pilot["assurance"]["external_lab_validation"]["status"],
        },
        "honesty": [
            "Public/redistributed datasets only; licenses recorded in PROVENANCE.md",
            "No claim that journal authors ran PCS",
            "External laboratory validation remains OPEN",
        ],
    }
    (out / "SUMMARY.json").write_bytes(canonicalize(summary) + b"\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
