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


ROOT = Path(__file__).resolve().parents[1]
V06_TESTS = [
    "tests/test_canonical_json_v06.py",
    "tests/test_strict_json.py",
    "tests/test_crypto_domains_v06.py",
    "tests/test_v06_crypto_schemas.py",
    "tests/test_certificate_v06.py",
    "tests/test_certificate_semantics_v06.py",
    "tests/test_replay_v06.py",
    "tests/test_normalized_wire_v06.py",
    "tests/test_normalized_set_v06.py",
    "tests/test_verifier_v06.py",
    "tests/test_cli_verify_v06.py",
    "tests/test_zip_verify_v06.py",
    "tests/test_bundle_v06.py",
    "tests/test_attest_v06.py",\n    "tests/test_policy_v06.py",\n    "tests/test_benchmark_v06.py",
    "tests/test_signing_v06.py",
    "tests/test_package_v06.py",
    "tests/test_v06_byte_contract.py",
]


def _run(name: str, cmd: list[str], run_dir: Path) -> dict:
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    elapsed = time.monotonic() - started
    out = {
        "name": name,
        "command": cmd,
        "exit_code": proc.returncode,
        "duration_seconds": round(elapsed, 3),
        "stdout_log": f"{name}.stdout.txt",
        "stderr_log": f"{name}.stderr.txt",
    }
    (run_dir / out["stdout_log"]).write_text(proc.stdout, encoding="utf-8")
    (run_dir / out["stderr_log"]).write_text(proc.stderr, encoding="utf-8")
    return out


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run and freeze the PCS v0.6 cross-language byte-contract gate."
    )
    parser.add_argument("--results-root", default="results/v06-contract-runs")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument(
        "--skip-full-suite",
        action="store_true",
        help="development convenience only; a release-candidate gate should run the full suite",
    )
    parser.add_argument("--stress-numbers", type=int, default=20000)
    parser.add_argument("--stress-objects", type=int, default=500)
    parser.add_argument("--stress-seed", type=int, default=20260929)
    args = parser.parse_args()

    for required in ("git", "node"):
        if shutil.which(required) is None:
            raise SystemExit(f"{required} is required for the v0.6 byte-contract gate")

    head = _git("rev-parse", "HEAD")
    if head.returncode != 0:
        raise SystemExit(head.stderr.strip() or "cannot resolve git HEAD")
    commit = head.stdout.strip()

    status = _git("status", "--porcelain")
    if status.returncode != 0:
        raise SystemExit(status.stderr.strip() or "cannot inspect git status")
    dirty_entries = [line for line in status.stdout.splitlines() if line.strip()]
    dirty = bool(dirty_entries)
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "refusing v0.6 contract gate from dirty tree; commit/stash or use --allow-dirty"
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (ROOT / args.results_root / f"{stamp}-{commit[:12]}").resolve()
    run_dir.mkdir(parents=True, exist_ok=False)

    node_version = subprocess.run(
        ["node", "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()

    steps: list[dict] = []
    steps.append(
        _run(
            "golden_reproduction",
            [sys.executable, "scripts/generate_v06_golden_contract.py"],
            run_dir,
        )
    )
    steps.append(
        _run(
            "v06_pytest",
            [sys.executable, "-m", "pytest", "-q", *V06_TESTS],
            run_dir,
        )
    )
    steps.append(
        _run(
            "node_cross_language",
            ["node", "scripts/check_jcs_cross_language.mjs"],
            run_dir,
        )
    )
    steps.append(
        _run(
            "node_golden_byte_contract",
            ["node", "scripts/check_v06_golden_contract.mjs"],
            run_dir,
        )
    )
    steps.append(
        _run(
            "jcs_differential_stress",
            [
                sys.executable,
                "scripts/stress_jcs_against_node.py",
                "--numbers",
                str(args.stress_numbers),
                "--objects",
                str(args.stress_objects),
                "--seed",
                str(args.stress_seed),
            ],
            run_dir,
        )
    )
    steps.append(
        _run(
            "adversarial_campaign",
            [sys.executable, "scripts/adversarial_campaign.py"],
            run_dir,
        )
    )
    if not args.skip_full_suite:
        steps.append(
            _run(
                "full_pytest",
                [sys.executable, "-m", "pytest", "-q"],
                run_dir,
            )
        )

    passed = (
        not dirty
        and not args.skip_full_suite
        and all(step["exit_code"] == 0 for step in steps)
    )

    result = {
        "format": "pcs-v06-byte-contract-gate-v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "repository": "Tommaso-R-Marena/proof-carrying-science",
        "commit": commit,
        "working_tree_dirty": dirty,
        "dirty_entries": dirty_entries,
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "node_version": node_version,
        "stress": {
            "numbers": args.stress_numbers,
            "objects": args.stress_objects,
            "seed": args.stress_seed,
        },
        "full_suite_required": True,
        "full_suite_skipped": args.skip_full_suite,
        "steps": steps,
        "gate_pass": passed,
        "interpretation": (
            "PASS means this exact commit reproduced the frozen v0.6 bytes, passed strict "
            "Python/browser canonicalization and parsing checks, domain-separated crypto "
            "tests, package byte-map adversarial checks, randomized Python-Node differential "
            "testing, independent Node verification of the frozen certificate/package bytes, "
            "the repository adversarial campaign, and the full Python suite. "
            "It is executable conformance evidence, not a proof of parser/SHA-256/Ed25519 "
            "correctness or scientific model adequacy."
        ),
    }
    (run_dir / "v06-byte-contract-gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_dir": str(run_dir), **result}, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
