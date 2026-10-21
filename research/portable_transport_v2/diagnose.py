"""Actual Lean experiments; never an artifact authorization interface.

Every proof candidate is checked in a fresh Lean process. Failed subprocesses
and incomplete/nonstandard axiom inventories cannot become affirmative results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import tempfile
import time

from pcs import transport_kernel_v1 as model
from pcs import transport_trace_kernel_v1 as trace

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(__file__).with_name("RawDecide.lean")
PROFILES = (
    ("original", 2_000_000, 8192),
    ("raw", 2_000_000, 8192),
    ("raw", 8_000_000, 8192),
    ("raw", 2_000_000, 32768),
    ("original", 2_000_000, 32),
    ("raw", 2_000_000, 32),
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def execute(lean, env, private, path, *, output=False):
    cmd = [lean, "-j1", "-M2048", "-D", "Elab.async=false", "--root=" + str(private)]
    if output:
        cmd += ["-o", str(path.with_suffix(".olean"))]
    cmd.append(str(path))
    start = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=private, env=env, capture_output=True,
                           text=True, timeout=180)
        return {"command": cmd, "exitcode": p.returncode,
                "stdout": p.stdout, "stderr": p.stderr,
                "wall_seconds": round(time.monotonic() - start, 6)}
    except subprocess.TimeoutExpired as e:
        def text(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        return {"command": cmd, "exitcode": None, "timeout": True,
                "stdout": text(e.stdout), "stderr": text(e.stderr),
                "wall_seconds": round(time.monotonic() - start, 6)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    frozen = trace.sources()
    raw_tactic = RAW.read_bytes()
    original = trace.render(trace.prepare(
        (ROOT / "examples/scientific_workflow_v3/contract.json").read_bytes(),
        (ROOT / "examples/scientific_workflow_v3/trajectory.csv").read_bytes()))
    before = {n: sha(v) for n, v in frozen.items()}
    protocol = {"profiles": PROFILES, "original_proof_sha256": sha(original),
                "source_sha256": before, "raw_tactic_sha256": sha(raw_tactic),
                "changes_to_authority": False, "artifact_authorized": False}
    (args.out / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    lean, env, version = model._environment(30)
    result = {"format": "pcs-portable-trace-kernel-diagnostic-v1", **protocol,
              "lean_version": version, "lean_sha256": sha(Path(lean).read_bytes()),
              "platform": platform.platform(),
              "stack_limit": resource.getrlimit(resource.RLIMIT_STACK),
              "source_compilations": [], "results": []}
    with tempfile.TemporaryDirectory(prefix="pcs-portable-trace-") as folder:
        private = Path(folder)
        (private / "PCSReal").mkdir()
        env = dict(env, LEAN_PATH=str(private) + os.pathsep + env["LEAN_PATH"])
        for name, source in [("PCSReal/Transport.lean", frozen["PCSReal/Transport.lean"]),
                             ("PCSReal/TransportTrace.lean", frozen["PCSReal/TransportTrace.lean"]),
                             ("RawDecide.lean", raw_tactic)]:
            path = private / name
            path.write_bytes(source)
            compiled = execute(lean, env, private, path, output=True)
            result["source_compilations"].append(compiled)
            if compiled["exitcode"] != 0:
                raise RuntimeError("Actual source compilation failed: " + json.dumps(compiled))
        for index, (kind, heartbeats, depth) in enumerate(PROFILES):
            proof = original.replace(b"maxHeartbeats 2000000", f"maxHeartbeats {heartbeats}".encode())
            proof = proof.replace(b"maxRecDepth 8192", f"maxRecDepth {depth}".encode())
            if kind == "raw":
                proof = b"import RawDecide\n" + proof.replace(b"by decide +kernel", b"by pcs_kernel_decide_raw")
            path = private / f"Replay{index}.lean"
            path.write_bytes(proof)
            (args.out / path.name).write_bytes(proof)
            row = {"kind": kind, "heartbeats": heartbeats, "max_rec_depth": depth,
                   "proof_sha256": sha(proof), **execute(lean, env, private, path),
                   "kernel_checked": False}
            if row["exitcode"] == 0:
                row["axiom_closures"] = model._inventory(row["stdout"], model.REPLAY_THEOREMS + trace.LITERAL)
                row["kernel_checked"] = True
            result["results"].append(row)
            (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps({k: row[k] for k in ["kind", "heartbeats", "max_rec_depth",
                                                "exitcode", "kernel_checked", "wall_seconds"]}), flush=True)
    result["sources_stable"] = before == {n: sha(v) for n, v in trace.sources().items()} and raw_tactic == RAW.read_bytes()
    if not result["sources_stable"]:
        raise RuntimeError("Diagnostic source changed")
    (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
