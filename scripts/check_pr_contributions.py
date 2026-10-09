#!/usr/bin/env python3
"""Bind conditional archive/promotion validation to the protected PR gate.

This checks file provenance only. Hosted contribution workflows additionally
elaborate Lean or parse syntax; none of these checks establish scientific truth.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORIES = {"Tommaso-R-Marena/proof-carrying-science", "Tommaso-R-Marena/proof-carrying-science-site"}


def main() -> int:
    base = os.environ.get("GITHUB_BASE_SHA", "")
    if os.environ.get("GITHUB_REPOSITORY") not in REPOSITORIES or not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("Expected an owner repository and exact PR base SHA")
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "-z", base, "HEAD"], cwd=ROOT
    ).decode("utf-8").split("\0")
    archive = any(p.startswith("contributions/pcs-submissions/") for p in changed)
    promotion = any(p.startswith("contributions/pcs-promotions/") for p in changed)
    checks = []
    if archive:
        checks.append("check_contribution_bundle.py")
    if promotion:
        checks.append("check_promotion_bundle.py")
    for script in checks:
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)
    print("Protected contribution gate PASS: " + (", ".join(checks) if checks else "no contribution paths changed"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, subprocess.CalledProcessError, UnicodeError) as error:
        print("Protected contribution gate FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
