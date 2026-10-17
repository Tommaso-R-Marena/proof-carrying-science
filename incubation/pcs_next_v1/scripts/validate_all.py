#!/usr/bin/env python3
"""Self-contained validation entry point for PCS Next (no root CI edits)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], cwd: Path | None = None, env=None) -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    return {
        "cmd": cmd,
        "cwd": str(cwd or ROOT),
        "returncode": proc.returncode,
        "seconds": time.perf_counter() - t0,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def main() -> int:
    report = {
        "format": "pcs-next-validate-all-v1",
        "repo": str(REPO),
        "owned": str(ROOT),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "steps": [],
    }
    env = {**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + str(REPO), "PATH": os.environ.get("PATH", "") + os.pathsep + str(Path.home() / ".local/bin")}

    steps = [
        (["python3", str(ROOT / "scripts/check_noninterference.py"), "--repo", str(REPO)], REPO),
        (["python3", str(REPO / "scripts/check_repository_integrity.py")], REPO),
        (["python3", "-m", "pytest", "-q", str(ROOT / "tests")], ROOT),
        (["python3", str(ROOT / "scripts/run_synthetic_pilot.py")], ROOT),
        (["python3", str(ROOT / "scripts/run_benchmarks.py")], ROOT),
    ]
    overall = 0
    for cmd, cwd in steps:
        r = run(cmd, cwd=cwd, env=env)
        report["steps"].append(r)
        if r["returncode"] != 0:
            overall = 1
            # integrity may fail for unrelated reasons — record and continue
            if "check_repository_integrity" in " ".join(cmd):
                report.setdefault("upstream_gate_notes", []).append(
                    "repository integrity returned non-zero; recorded without modifying the gate"
                )

    # optional lean
    lake = subprocess.run(["bash", "-lc", "command -v lake"], capture_output=True, text=True)
    if lake.returncode == 0:
        r = run(["lake", "build"], cwd=ROOT / "formal", env=env)
        report["steps"].append(r)
        if r["returncode"] != 0:
            overall = 1
    else:
        report["steps"].append({"cmd": ["lake", "build"], "returncode": None, "status": "SKIPPED", "reason": "lake not installed"})

    out = RESULTS / "validate_all.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall == 0, "report": str(out)}, indent=2))
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
