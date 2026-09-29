from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pcs.environment import snapshot_environment


ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _run(name: str, cmd: list[str], cwd: Path, run_dir: Path) -> dict:
    started = time.monotonic()
    p = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    elapsed = time.monotonic() - started
    log = {
        "name": name,
        "command": cmd,
        "cwd": str(cwd),
        "exit_code": p.returncode,
        "duration_seconds": round(elapsed, 3),
        "stdout_log": f"{name}.stdout.txt",
        "stderr_log": f"{name}.stderr.txt",
    }
    (run_dir / log["stdout_log"]).write_text(p.stdout, encoding="utf-8")
    (run_dir / log["stderr_log"]).write_text(p.stderr, encoding="utf-8")
    return log


def _formal_placeholder_audit() -> dict:
    targets = [ROOT / "formal" / "PCS.lean", ROOT / "formal" / "PCS"]
    hits: list[str] = []
    for target in targets:
        paths = [target] if target.is_file() else sorted(target.rglob("*.lean"))
        for path in paths:
            if not path.is_file():
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if "sorry" in line or "admit" in line:
                    hits.append(f"{path.relative_to(ROOT)}:{i}:{line.strip()}")
    return {"pass": not hits, "hits": hits}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the PCS local release gate and freeze execution evidence."
    )
    parser.add_argument(
        "--results-root",
        default="results/runs",
        help="directory under repository root for frozen run artifacts",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="permit execution from a dirty Git working tree (recorded as non-release evidence)",
    )
    parser.add_argument(
        "--require-lean",
        action="store_true",
        help="make missing/failing lake build a release-gate failure",
    )
    args = parser.parse_args()

    if shutil.which("git") is None:
        raise SystemExit("git is required to identify the exact release candidate")

    sha_proc = _git("rev-parse", "HEAD")
    if sha_proc.returncode != 0:
        raise SystemExit(f"cannot resolve git HEAD: {sha_proc.stderr.strip()}")
    commit = sha_proc.stdout.strip()

    status_proc = _git("status", "--porcelain")
    if status_proc.returncode != 0:
        raise SystemExit(f"cannot inspect git working tree: {status_proc.stderr.strip()}")
    dirty_lines = [line for line in status_proc.stdout.splitlines() if line.strip()]
    dirty = bool(dirty_lines)
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "refusing release-gate execution from a dirty working tree; commit/stash changes or use --allow-dirty"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (ROOT / args.results_root / f"{stamp}-{commit[:12]}").resolve()
    run_dir.mkdir(parents=True, exist_ok=False)

    runtime = snapshot_environment()
    (run_dir / "runtime.json").write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    steps: list[dict] = []
    steps.append(
        _run(
            "doctor",
            [sys.executable, "-m", "pcs.cli", "doctor"],
            ROOT,
            run_dir,
        )
    )
    steps.append(
        _run(
            "pytest",
            [sys.executable, "-m", "pytest", "-q"],
            ROOT,
            run_dir,
        )
    )
    steps.append(
        _run(
            "adversarial_campaign",
            [sys.executable, "scripts/adversarial_campaign.py"],
            ROOT,
            run_dir,
        )
    )
    demo_dir = run_dir / "reference-demo"
    steps.append(
        _run(
            "reference_demo",
            [
                sys.executable,
                "scripts/run_reference_demo.py",
                "--output",
                str(demo_dir),
                "--force",
            ],
            ROOT,
            run_dir,
        )
    )

    demo_summary_path = demo_dir / "demo-summary.json"
    normalized_refinement_ready = False
    normalized_refinement_status = "MISSING"
    if demo_summary_path.is_file():
        try:
            demo_summary = json.loads(demo_summary_path.read_text(encoding="utf-8"))
            normalized_refinement_status = (
                demo_summary.get("assurance_dimensions", {}).get("normalized_refinement", "MISSING")
            )
            normalized_refinement_ready = normalized_refinement_status == "PASS"
        except Exception:
            normalized_refinement_status = "INVALID_SUMMARY"

    placeholder_audit = _formal_placeholder_audit()
    (run_dir / "formal-placeholder-audit.json").write_text(
        json.dumps(placeholder_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lake_path = shutil.which("lake")
    if lake_path:
        lean_step = _run("lake_build", [lake_path, "build"], ROOT / "formal", run_dir)
        lean_status = "PASS" if lean_step["exit_code"] == 0 else "FAIL"
        steps.append(lean_step)
    else:
        lean_status = "NOT_AVAILABLE"

    required_step_names = {"doctor", "pytest", "adversarial_campaign", "reference_demo"}
    python_ready = (
        not dirty
        and placeholder_audit["pass"]
        and normalized_refinement_ready
        and all(
            step["exit_code"] == 0
            for step in steps
            if step["name"] in required_step_names
        )
    )
    formal_ready = placeholder_audit["pass"] and lean_status == "PASS"

    release_pass = python_ready and (formal_ready if args.require_lean else True)

    result = {
        "format": "pcs-release-gate-v2",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "repository": "Tommaso-R-Marena/proof-carrying-science",
        "commit": commit,
        "working_tree_dirty": dirty,
        "dirty_entries": dirty_lines,
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "runtime_semantic_hash": runtime.get("semantic_hash"),
        "steps": steps,
        "formal_placeholder_audit": placeholder_audit,
        "reference_normalized_refinement": normalized_refinement_status,
        "lean_build": lean_status,
        "python_pilot_release_ready": python_ready,
        "formal_kernel_machine_checked": formal_ready,
        "release_gate_pass": release_pass,
        "interpretation": (
            "A passing Python pilot gate requires the reference attestation's normalized-refinement handoff to verify; "
            "it is execution evidence for this exact commit and environment; "
            "it is not a security proof, biological/clinical validation, regulatory approval, or a substitute "
            "for a successful Lean build when formal-kernel claims are made."
        ),
    }
    (run_dir / "release-gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_dir": str(run_dir), **result}, indent=2, sort_keys=True))
    return 0 if release_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
