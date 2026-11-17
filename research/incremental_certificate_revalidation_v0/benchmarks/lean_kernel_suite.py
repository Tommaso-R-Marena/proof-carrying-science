"""Real Lean 4.28.0 kernel-check timings (not synthetic sleep).

Times cold vs warm checking of formal/bench/BenchObligations.lean and compares
to a trivial no-op parse. Distinguishes toolchain startup from check cost.

Does NOT claim incremental certificate reuse yet — establishes a real Lean
workload baseline for later incremental experiments.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"
BENCH = FORMAL / "bench" / "BenchObligations.lean"
OUT = ROOT / "results" / "lean_kernel_benchmark_report.json"


def _lean_bin() -> str:
    env = os.environ.get("LEAN_BIN")
    if env:
        return env
    for cand in (
        Path.home() / ".local/lean-4.28.0/bin/lean",
        Path("/usr/local/bin/lean"),
        shutil.which("lean") or "",
    ):
        if cand and Path(cand).exists():
            return str(cand)
    raise FileNotFoundError("lean 4.28.0 not found; set LEAN_BIN")


def _time_lean(args: list[str], cwd: Path) -> float:
    t0 = time.perf_counter()
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    dt = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return dt


def main() -> None:
    lean = _lean_bin()
    # Cold: check file with no prior .olean in a temp copy of just this file's imports (Init only)
    cold_ms = _time_lean([lean, str(BENCH)], cwd=FORMAL)
    # Warm: immediate recheck (filesystem cache / OS page cache; still full elaborator)
    warm_ms = _time_lean([lean, str(BENCH)], cwd=FORMAL)
    warm2_ms = _time_lean([lean, str(BENCH)], cwd=FORMAL)
    # Startup baseline: lean --help
    help_ms = _time_lean([lean, "--help"], cwd=FORMAL)

    report = {
        "lean_bin": lean,
        "file": str(BENCH.relative_to(ROOT)),
        "not_synthetic_sleep": True,
        "cold_check_ms": cold_ms,
        "warm_check_ms": warm_ms,
        "warm_recheck_ms": warm2_ms,
        "lean_help_startup_ms": help_ms,
        "approx_check_minus_startup_ms": max(0.0, cold_ms - help_ms),
        "notes": (
            "Standalone BenchObligations.lean with native_decide Nat obligations. "
            "This is a Lean-kernel workload baseline, not yet an incremental "
            "certificate-revalidation experiment. Synthetic DelayedRegistry "
            "results remain separate historical evidence."
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
