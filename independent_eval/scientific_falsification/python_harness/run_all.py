#!/usr/bin/env python3
"""Run Workstream B scientific-falsification evaluation campaigns."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .aristotle_candidates import write_candidates
from .canonical_seal import seal_artifact
from .discovery_metrics import run_discovery_benchmark, write_report as write_discovery
from .external_validity import score_protocol_file
from .falsification_scorecard import write_scorecard
from .inadequacy_eval import run_inadequacy_suite
from .metamorphic import DEFAULT_CAMPAIGN_CASE_IDS, run_metamorphic_campaign
from .paths import (
    CASEBOOK,
    DISCOVERY,
    EXTERNAL,
    INADEQUACY,
    REPO_ROOT,
    RESULTS,
    ROOT,
)

SELECTABLE = (
    "casebook",
    "inadequacy",
    "metamorphic",
    "discovery",
    "external_validity",
    "aristotle",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip regenerating fixtures (use committed casebook/inadequacy/discovery trees).",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=SELECTABLE,
        default=None,
        help=(
            "Run only selected surfaces (repeatable). Omitted surfaces are recorded "
            "as SKIPPED (not PASS). Default: all surfaces."
        ),
    )
    args = parser.parse_args(argv)
    selected = set(args.only) if args.only else set(SELECTABLE)

    RESULTS.mkdir(parents=True, exist_ok=True)
    if not args.skip_build:
        build = subprocess.run(
            [sys.executable, str(ROOT / "python_harness" / "build_fixtures.py")],
            cwd=str(REPO_ROOT),
            check=False,
        )
        if build.returncode != 0:
            return build.returncode

    reports: dict[str, object] = {
        "format": "pcs-independent-scientific-falsification-summary-v1",
        "repo_head": _git_head(),
        "root": str(ROOT.relative_to(REPO_ROOT)),
        "selected_surfaces": sorted(selected),
        "issues_accept": False,
    }

    # Casebook: certify/verify + negative controls on frozen fixtures (not examples copy).
    if "casebook" in selected:
        fixture_controls = _run_fixture_casebook(RESULTS / "work" / "casebook")
        reports["casebook_fixtures"] = {
            "case_count": fixture_controls["case_count"],
            "positives_ok": fixture_controls["positives_ok"],
            "negatives_rejected": fixture_controls["negatives_rejected"],
        }
        (RESULTS / "casebook_fixture_controls.json").write_text(
            json.dumps(fixture_controls, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        reports["casebook_fixtures"] = {"status": "SKIPPED"}

    # Examples-based alternate surface is optional; fixture casebook is authoritative.
    reports["casebook_examples"] = {
        "status": "skipped",
        "note": "Authoritative fixtures live under casebook/cases/; examples/ remain read-only upstream references.",
    }

    if "inadequacy" in selected:
        inadequacy = run_inadequacy_suite(
            INADEQUACY / "examples", RESULTS / "work" / "inadequacy"
        )
        reports["inadequacy"] = {
            "example_count": inadequacy["example_count"],
            "computational_pass_count": inadequacy["computational_pass_count"],
            "empirical_adequacy_established_count": inadequacy[
                "empirical_adequacy_established_count"
            ],
        }
        (RESULTS / "inadequacy.json").write_text(
            json.dumps(inadequacy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        reports["inadequacy"] = {"status": "SKIPPED"}

    if "metamorphic" in selected:
        metamorphic = run_metamorphic_campaign(
            CASEBOOK / "cases",
            RESULTS / "work" / "metamorphic",
            RESULTS,
            case_ids=DEFAULT_CAMPAIGN_CASE_IDS,
        )
        reports["metamorphic"] = {
            "case_count": metamorphic["case_count"],
            "cases_ok": metamorphic["cases_ok"],
            "oracles_all_passed_count": metamorphic["oracles_all_passed_count"],
            "case_ids": metamorphic["case_ids"],
            "per_case": [
                {
                    "case_id": c["case_id"],
                    "all_oracles_passed": c.get("all_oracles_passed"),
                    "valid_pass": c.get("valid_pass"),
                    "valid_total": c.get("valid_total"),
                    "invalid_pass": c.get("invalid_pass"),
                    "invalid_total": c.get("invalid_total"),
                }
                for c in metamorphic["per_case"]
            ],
        }
    else:
        reports["metamorphic"] = {"status": "SKIPPED"}

    if "discovery" in selected:
        discovery = run_discovery_benchmark(
            DISCOVERY / "projects",
            DISCOVERY / "ground_truth.json",
            RESULTS / "work" / "discovery",
        )
        write_discovery(discovery, RESULTS / "discovery_benchmark.json")
        reports["discovery"] = {
            "project_count": discovery["project_count"],
            "macro_precision": discovery["macro_precision"],
            "macro_recall": discovery["macro_recall"],
            "abstention_accuracy": discovery["abstention_accuracy"],
            "cli_success_count": discovery["cli_success_count"],
        }
    else:
        reports["discovery"] = {"status": "SKIPPED"}

    if "external_validity" in selected:
        protocol = EXTERNAL / "templates" / "external_validity_protocol_blank.json"
        rubric = EXTERNAL / "rubrics" / "completeness_rubric.json"
        score = score_protocol_file(protocol, rubric)
        reports["external_validity"] = {
            "completeness_score": score["completeness_score"],
            "empirical_adequacy_established": score["empirical_adequacy_established"],
            "results_status": score["results_status"],
        }
        (RESULTS / "external_validity_score.json").write_text(
            json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        reports["external_validity"] = {"status": "SKIPPED"}

    if "aristotle" in selected:
        aristotle = write_candidates()
        reports["aristotle_candidates"] = {
            "candidate_count": aristotle["candidate_count"],
            "status": "proposal_candidates_only",
            "empirical_adequacy_established_any": False,
        }
    else:
        reports["aristotle_candidates"] = {"status": "SKIPPED"}

    sealed = seal_artifact(reports)
    (RESULTS / "SUMMARY.json").write_text(
        json.dumps(sealed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    scorecard = write_scorecard(sealed)
    print(json.dumps(sealed, indent=2, sort_keys=True))
    print(
        f"SCORECARD_DIGEST "
        f"{(scorecard.get('artifact_integrity') or {}).get('digest_sha256')}"
    )
    return 0


def _run_fixture_casebook(work: Path) -> dict[str, object]:
    from .pcs_cli import certify, verify_certificate
    import shutil

    outcomes = []
    cases_root = CASEBOOK / "cases"
    for case_dir in sorted(p for p in cases_root.iterdir() if p.is_dir()):
        manifest = case_dir / "manifest.json"
        if not manifest.is_file():
            continue
        entry: dict[str, object] = {"id": case_dir.name}
        pos_out = work / case_dir.name / "positive"
        pos = certify(manifest, pos_out)
        ver = verify_certificate(pos_out / "certificate.json") if pos.ok else None
        entry["positive"] = {
            "certify_ok": pos.ok,
            "verify_ok": bool(ver and ver.ok),
        }
        # Negative: prefer packaged negative_controls/tampered predictions if present.
        neg_inputs = work / case_dir.name / "negative_inputs"
        if neg_inputs.exists():
            shutil.rmtree(neg_inputs)
        shutil.copytree(case_dir, neg_inputs)
        tampered = next(
            (neg_inputs / "negative_controls").glob("tampered_*.csv"),
            None,
        ) if (neg_inputs / "negative_controls").is_dir() else None
        if tampered is not None:
            # Point manifest predictions at tampered file.
            m = json.loads((neg_inputs / "manifest.json").read_text(encoding="utf-8"))
            for art in m.get("artifacts", []):
                if art.get("id") in {"pk_predictions", "predictions"} or str(
                    art.get("path", "")
                ).endswith(".csv"):
                    art["path"] = str(tampered.relative_to(neg_inputs))
            (neg_inputs / "manifest.json").write_text(
                json.dumps(m, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            ncert = certify(neg_inputs / "manifest.json", work / case_dir.name / "negative")
            # Reject if certify fails OR any claim not COMPUTATIONALLY_SUPPORTED.
            rejected = not ncert.ok
            if ncert.ok:
                cert = json.loads(
                    (work / case_dir.name / "negative" / "certificate.json").read_text(
                        encoding="utf-8"
                    )
                )
                statuses = [
                    c.get("assessment", {}).get("status") for c in cert.get("claims", [])
                ]
                rejected = any(s != "COMPUTATIONALLY_SUPPORTED" for s in statuses)
            entry["negative"] = {"attempted": True, "rejected_or_failed": rejected}
        else:
            # Generic: append junk to a csv if present.
            csv = next(neg_inputs.rglob("*.csv"), None)
            if csv is not None:
                csv.write_text(csv.read_text(encoding="utf-8") + "\n#tamper\n", encoding="utf-8")
                ncert = certify(neg_inputs / "manifest.json", work / case_dir.name / "negative")
                entry["negative"] = {
                    "attempted": True,
                    "rejected_or_failed": not ncert.ok,
                }
            else:
                entry["negative"] = {"attempted": False, "reason": "no csv negative"}
        outcomes.append(entry)

    return {
        "format": "pcs-independent-fixture-casebook-controls-v1",
        "case_count": len(outcomes),
        "outcomes": outcomes,
        "positives_ok": sum(
            1
            for o in outcomes
            if (o.get("positive") or {}).get("verify_ok")
            or (o.get("positive") or {}).get("certify_ok")
        ),
        "negatives_rejected": sum(
            1
            for o in outcomes
            if (o.get("negative") or {}).get("rejected_or_failed")
        ),
    }


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
