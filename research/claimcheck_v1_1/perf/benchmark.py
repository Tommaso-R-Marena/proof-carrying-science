"""Kernel cost by table size and statistic: wall time and peak memory of one Lean run per claim.

    python -m research.claimcheck_v1_1.perf.benchmark --out research/claimcheck_v1_1/perf/results.json

Synthetic tables (deterministic), one claim per proof file, the real Lean 4.28.0 kernel, one process
at a time.  Each Lean process runs under an address-space limit and a time limit; a run that hits
either is recorded as not established, which is also what the pipeline reports in that case.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

from ...claimcheck_v1.lean import find_lean, lean_version, obligation_source
from ...claimcheck_v1.oracle import evaluate
from ...claimcheck_v1.spec import ClaimSpec

SIZES = (50, 100, 200, 400, 800, 1600, 2400)
STATS = ("count", "mean", "min", "sd_sample", "median", "pearson")
CHILD = r"""
import json, resource, subprocess, sys, time
limit = int(sys.argv[3])
def cap():
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
t = time.monotonic()
try:
    p = subprocess.run([sys.argv[1], sys.argv[2]], capture_output=True, text=True, timeout=float(sys.argv[4]), preexec_fn=cap)
    code, out, err, timed_out = p.returncode, p.stdout, p.stderr, False
except subprocess.TimeoutExpired:
    code, out, err, timed_out = None, "", "", True
print(json.dumps({"seconds": round(time.monotonic() - t, 2), "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
                  "returncode": code, "timed_out": timed_out, "stdout": out[-300:], "stderr": err[-300:]}))
"""


def table(rows: int) -> bytes:
    """Deterministic table: a group label, two correlated two-decimal measurements, an integer."""
    lines = ["id,grp,x,y,k"]
    state = 12345
    for i in range(rows):
        state = (state * 1103515245 + 12345) % 2**31
        x = 1000 + state % 9000                       # 10.00 .. 99.99
        state = (state * 1103515245 + 12345) % 2**31
        y = x * 3 // 2 + state % 500
        lines.append(f"{i + 1},{'ABC'[i % 3]},{x // 100}.{x % 100:02d},{y // 100}.{y % 100:02d},{state % 17}")
    return ("\n".join(lines) + "\n").encode()


def measure(lean: str, data: bytes, stat: str, limit_bytes: int, timeout: int) -> dict:
    spec = ClaimSpec(stat, "1", None if stat == "count" else "x", "y" if stat == "pearson" else None)
    outcome = evaluate(data, spec, ("", "NA"), Fraction(1))
    source = obligation_source(data, spec, ("", "NA"), Fraction(1), outcome)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "Obligation.lean"
        path.write_text(source, encoding="utf-8")
        proc = subprocess.run([sys.executable, "-c", CHILD, lean, str(path), str(limit_bytes), str(timeout)], capture_output=True, text=True, cwd=tmp)
    res = json.loads(proc.stdout)
    accepted = res["returncode"] == 0 and not res["stderr"].strip() and res["stdout"].strip().startswith("'pcs_claim_0' depends on axioms")
    return {"statistic": stat, "seconds": res["seconds"], "peak_rss_mb": res["peak_rss_mb"], "kernel_accepted": accepted,
            "why_not": None if accepted else ("time limit" if res["timed_out"] else (res["stdout"] or res["stderr"] or "killed or memory limit").strip()[:120])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--memory-limit-gb", type=float, default=11)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--sizes", default=",".join(map(str, SIZES)))
    args = ap.parse_args(argv)
    lean = find_lean()
    out = {"lean": lean_version(lean), "host": platform.platform(), "cpus": os.cpu_count(),
           "memory_limit_gb_per_lean_process": args.memory_limit_gb, "time_limit_seconds": args.timeout,
           "note": "One claim per proof file. Synthetic two-decimal data. Peak RSS is the Lean process's maximum resident set size.", "runs": []}
    for rows in [int(x) for x in args.sizes.split(",")]:
        data = table(rows)
        for stat in STATS:
            rec = {"rows": rows, "bytes": len(data), **measure(lean, data, stat, int(args.memory_limit_gb * 2**30), args.timeout)}
            out["runs"].append(rec)
            print(json.dumps(rec), flush=True)
            Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
