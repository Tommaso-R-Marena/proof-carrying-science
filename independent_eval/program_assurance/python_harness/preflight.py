"""Local preflight gates for independent_eval program assurance.

Implements the *substance* of proposals E-P01/E-P02 as a runnable harness gate
without modifying ``.github/`` workflows (forbidden for this workstream).

Exit codes:
  0 — all selected gates passed
  1 — one or more hard failures (collisions and/or path overlaps)
  2 — configuration / git errors that prevent a conclusive audit
"""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from . import paths as paths_mod
from .collision_scanner import scan_path_collisions, write_collision_report
from .nonoverlap_auditor import audit_branch_nonoverlap, write_nonoverlap_report
from .residual_trust import rollup_residual_trust, write_residual_trust_report


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=paths_mod.REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def run_preflight(
    *,
    check_collisions: bool = True,
    check_nonoverlap: bool = True,
    check_residual_trust: bool = True,
    fail_on_overlap: bool = True,
    fail_on_collision: bool = True,
    branches: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    results = paths_mod.RESULTS
    results.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "format": "pcs-independent-program-preflight-v1",
        "repo_head": _git_head(),
        "gates": {},
        "hard_failures": [],
        "soft_notes": [],
        "pass": True,
        "conclusive": True,
        "disclaimer": (
            "Local harness gate only. Does not modify CI workflows. "
            "Wiring into required GitHub checks remains a separate proposal."
        ),
    }

    if check_collisions:
        scan_root = (
            paths_mod.INDEPENDENT_EVAL
            if paths_mod.INDEPENDENT_EVAL.exists()
            else paths_mod.ROOT
        )
        collision = scan_path_collisions(scan_root)
        write_collision_report(collision, results / "path_collision_report.json")
        gate = {
            "id": "path_collision",
            "pass": not collision.has_collisions,
            "collision_group_count": len(collision.collision_groups),
            "file_count": collision.file_count,
        }
        report["gates"]["path_collision"] = gate
        if collision.has_collisions and fail_on_collision:
            report["hard_failures"].append(
                f"case-insensitive path collisions: {len(collision.collision_groups)} group(s)"
            )
            report["pass"] = False

    if check_nonoverlap:
        audited = audit_branch_nonoverlap(
            branches if branches is not None else paths_mod.SIBLING_BRANCHES, repo=paths_mod.REPO_ROOT
        )
        write_nonoverlap_report(audited, results / "branch_nonoverlap_report.json")
        gate = {
            "id": "branch_nonoverlap",
            "pass": not audited.has_overlaps and not audited.missing_branches and not audited.errors and bool(audited.changed_files),
            "has_overlaps": audited.has_overlaps,
            "missing_branches": list(audited.missing_branches),
            "error_count": len(audited.errors),
            "pair_count": len(audited.pair_overlaps),
        }
        report["gates"]["branch_nonoverlap"] = gate
        if audited.missing_branches or audited.errors or not audited.changed_files:
            report["conclusive"] = False
            report["pass"] = False
            report["soft_notes"].append("incomplete branch inventory; non-overlap is not established")
        if audited.errors:
            report["soft_notes"].append(
                f"git diff errors for {len(audited.errors)} branch(es); see report"
            )
            if not audited.changed_files:
                report["conclusive"] = False
        if audited.has_overlaps and fail_on_overlap:
            overlapping = [
                f"{pair.branch_a}∩{pair.branch_b}={len(pair.overlap)}"
                for pair in audited.pair_overlaps
                if pair.overlap
            ]
            report["hard_failures"].append(
                "changed-file overlaps vs main: " + ", ".join(overlapping)
            )
            report["pass"] = False

    if check_residual_trust:
        trust = rollup_residual_trust(repo=paths_mod.REPO_ROOT)
        write_residual_trust_report(trust, results / "residual_trust_rollup.json")
        report["gates"]["residual_trust"] = {
            "id": "residual_trust",
            "pass": True,
            "sources_present": trust["sources_present"],
            "sources_missing": trust["sources_missing"],
            "assumption_id_count": trust["assumption_id_count"],
            "tcb_closed": False,
        }
        report["soft_notes"].append(
            "residual-trust rollup is informational and does not claim TCB closure"
        )

    (results / "preflight.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-collisions", action="store_true")
    parser.add_argument("--skip-nonoverlap", action="store_true")
    parser.add_argument("--skip-residual-trust", action="store_true")
    parser.add_argument(
        "--allow-overlap",
        action="store_true",
        help="Report overlaps but do not hard-fail on them.",
    )
    parser.add_argument(
        "--allow-collision",
        action="store_true",
        help="Report collisions but do not hard-fail on them.",
    )
    args = parser.parse_args(argv)

    report = run_preflight(
        check_collisions=not args.skip_collisions,
        check_nonoverlap=not args.skip_nonoverlap,
        check_residual_trust=not args.skip_residual_trust,
        fail_on_overlap=not args.allow_overlap,
        fail_on_collision=not args.allow_collision,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["conclusive"]:
        return 2
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
