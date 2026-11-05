#!/usr/bin/env python3
"""Run all Workstream A black-box evaluation campaigns."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .adversarial_corpus import generate_corpus
from .intake_chronology import run_intake_chronology
from .jcs_differential import run_differential
from .paths import REPO_ROOT, RESULTS, ROOT
from .policy_confusion import run_policy_confusion
from .resource_bounds import run_resource_bounds
from .zip_differential import run_zip_differential


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-corpus", action="store_true")
    parser.add_argument("--skip-rust-build", action="store_true")
    args = parser.parse_args(argv)

    RESULTS.mkdir(parents=True, exist_ok=True)
    reports: dict[str, object] = {"repo_head": _git_head(), "format": "pcs-independent-protocol-eval-summary-v1"}

    if not args.skip_rust_build:
        reports["jcs_differential"] = run_differential()
    if not args.skip_corpus:
        reports["adversarial_corpus"] = {
            k: v
            for k, v in generate_corpus().items()
            if k != "cases"
        }
        # keep full corpus on disk; summary without huge case bodies in aggregate
        full = json.loads((RESULTS / "adversarial_corpus.json").read_text())
        reports["adversarial_corpus"]["case_count"] = full["case_count"]
        reports["adversarial_corpus"]["false_accepts"] = full["false_accepts"]
    reports["zip_differential"] = run_zip_differential(ROOT / "fixtures" / "zip" / "work")
    reports["intake_chronology"] = {
        "scenario_count": run_intake_chronology(ROOT / "fixtures" / "intake" / "work")["scenario_count"]
    }
    reports["policy_confusion"] = run_policy_confusion(ROOT / "fixtures" / "policy" / "work")
    reports["resource_bounds"] = run_resource_bounds(ROOT / "fixtures" / "resource" / "work")

    (RESULTS / "SUMMARY.json").write_text(json.dumps(reports, indent=2, sort_keys=True) + "\n")
    print(json.dumps(reports, indent=2, sort_keys=True))
    return 0


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
