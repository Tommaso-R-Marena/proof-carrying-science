"""Run the same fail-closed PCS integration checks without CircleCI.

This is a local/isolated-runner tool, NOT a substitute for successful GitHub
required status checks or for an independent verifier's trust decision.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, argv: list[str], *, cwd: Path = ROOT) -> None:
    print(f"\n=== PCS trusted preflight: {label} ===", flush=True)
    print("command:", " ".join(argv), flush=True)
    completed = subprocess.run(argv, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed (exit {completed.returncode})")


def capture(*argv: str) -> str:
    result = subprocess.run(argv, cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> int:
    sha = ""
    report = {
        "format": "pcs-local-ci-diagnostic-v1",
        "authoritative_ci_status": False,
        "signed": False,
        "repo_sha": "",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "all_checks_passed": False,
    }
    stages: list[tuple[str, list[str], Path]] = []
    try:
        for executable in ["git", "node", "lean", "lake"]:
            if not shutil.which(executable):
                raise RuntimeError(f"missing executable: {executable} (install prerequisites first)")
        sha = capture("git", "rev-parse", "HEAD")
        report["repo_sha"] = sha
        if capture("git", "status", "--porcelain", "--untracked-files=no"):
            raise RuntimeError("tracked worktree is dirty; verify an exact committed source SHA")
        py = sys.executable
        with tempfile.TemporaryDirectory(prefix="pcs-ci-") as tmp:
            work = Path(tmp)
            stages = [
                ("git metadata and governance", [py, "scripts/check_repository_integrity.py"], ROOT),
                ("Python test suite", [py, "-m", "pytest", "-q"], ROOT),
                ("adversarial v0.5 baseline", [py, "scripts/adversarial_campaign.py"], ROOT),
                ("golden v0.6 package examples", [py, "scripts/run_golden_examples_v06.py", "-o", str(work / "golden")], ROOT),
                ("adversarial v0.6", [py, "scripts/adversarial_v06_hardening.py"], ROOT),
                ("certificate construction", [py, "-m", "pcs.cli", "certify", "examples/biopharma_demo/manifest.json", "-o", str(work / "certificate")], ROOT),
                ("certificate verification", [py, "-m", "pcs.cli", "verify", str(work / "certificate/certificate.json")], ROOT),
                ("claim policy gate", [py, "-m", "pcs.cli", "gate", str(work / "certificate/certificate.json"), "--claim", "C1", "--claim", "C2", "--claim", "C3"], ROOT),
                ("Lean default targets and proof hygiene", ["bash", "scripts/verify_lean.sh"], ROOT),
                ("frozen v0.6 cross-language byte contract", [py, "scripts/run_v06_contract_gate.py", "--results-root", str(work / "byte-contract")], ROOT),
            ]
            golden_checker = ROOT / "formal" / "tools" / "CheckGoldenFileLiterals.lean"
            if golden_checker.exists():
                stages.append(("Aristotle source-to-file golden literal equivalence", ["lake", "env", "lean", "--run", "tools/CheckGoldenFileLiterals.lean"], ROOT / "formal"))
            for label, cmd, cwd in stages:
                run(label, cmd, cwd=cwd)
                report["checks"].append({"name": label, "result": "PASS"})
            report["all_checks_passed"] = True
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        report["error"] = str(exc)
        report["checks"].append({"name": "execution", "result": "FAIL", "details": str(exc)})
        print("ERROR:", exc, file=sys.stderr, flush=True)
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        result_path = ROOT / "results" / "trusted-ci-diagnostic.json"
        result_path.parent.mkdir(exist_ok=True)
        result_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nDiagnostic record:", result_path, flush=True)
        print("Warning: this is an UNSIGNED LOCAL REPORT, not a GitHub Actions status.", flush=True)
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
