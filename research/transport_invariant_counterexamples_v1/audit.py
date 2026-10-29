"""Fresh source compilation and same-kernel object replay of four theorems.

This Linux research CLI never grants PCS or scientific authority. It uses the
reviewed checkout/toolchain; hashes and subprocesses do not authenticate a host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = "ca63ee0a4560919395dc9605e9aa0ec484430d41"
MATHLIB = "8f9d9cff6bd728b17a24e163c9402775d9e6a365"
THEOREMS = ["PCSPortableInvariantFamily." + name for name in (
    "matrix_certified", "step_initial", "invariant_counterexample_family", "all_times")]
APPROVED = {"propext", "Classical.choice", "Quot.sound"}
SOURCE_PATHS = {
    "PCSReal/Transport.lean": ROOT / "formal/real/PCSReal/Transport.lean",
    "PCSReal/TransportTrace.lean": ROOT / "formal/real/PCSReal/TransportTrace.lean",
    "Certificate.lean": ROOT / "research/portable_transport_v2/Certificate.lean",
    "CounterexampleFamily.lean": Path(__file__).with_name("CounterexampleFamily.lean"),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, timeout=30).strip()


def preservation() -> dict:
    # The original additions-only predicate remains the standalone behavior.
    # A reviewed combined tree must satisfy its separately pinned whole-source
    # contract; never report that the historical predicate held on this tree.
    successor = ROOT / "docs/integration/2026-10-29/RECONCILIATION_V14.json"
    if successor.exists() or successor.is_symlink():
        from research.integration_v2.reconcile import check
        checked = check(require_committed=True)
        return {"base": BASE, "head": git("rev-parse", "HEAD"),
                "tree": git("rev-parse", "HEAD^{tree}"),
                "admitted_contract": checked["format"],
                "original_additions_only_predicate_claimed": False,
                "combined_source": checked}
    def tree(ref):
        raw = subprocess.check_output(["git", "ls-tree", "-rz", "-r", ref], cwd=ROOT, timeout=30)
        return {x.split(b"\t", 1)[1]: x.split(b"\t", 1)[0] for x in raw.split(b"\0") if x}
    old, new = tree(BASE), tree("HEAD")
    if any(new.get(name) != mode_blob for name, mode_blob in old.items()):
        raise ValueError("Predecessor file or mode changed")
    if git("status", "--porcelain"):
        raise ValueError("Clean committed checkout required")
    return {"base": BASE, "head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
            "predecessor_files_and_modes_preserved": len(old), "new_files": len(new) - len(old)}


def inventory(stdout: str) -> dict:
    # Require every named closure exactly once and reject unknown axioms.
    found = {}
    for line in stdout.splitlines():
        match = re.fullmatch(r"'([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)", line)
        if not match:
            continue
        name = match[1]
        axioms = sorted(x.strip() for x in (match[2] or "").split(",") if x.strip())
        if name in found or not set(axioms) <= APPROVED:
            raise ValueError("Duplicate or unapproved axiom closure")
        found[name] = axioms
    if set(found) != set(THEOREMS):
        raise ValueError("Complete exact family axiom inventory required")
    return found


def audit(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {"format": "pcs-transport-invariant-family-audit-v1", "kernel_checked": False,
              "fresh_object_replay_checked": False, "production_authority": False,
              "pcs_authority": False, "scientific_acceptance": False, "empirical_validation": False,
              "external_independent_verifier": False, "executions": []}
    def save():
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    try:
        before = preservation()
        frozen = {name: path.read_bytes() for name, path in SOURCE_PATHS.items()}
        hashes = {name: sha(raw) for name, raw in frozen.items()}
        result.update(preservation=before, source_sha256=hashes)
        mathlib = ROOT / ".lake/packages/mathlib"
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=mathlib, text=True, timeout=30).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=mathlib, text=True, timeout=30)
        if revision != MATHLIB or dirty.strip():
            raise ValueError("Clean pinned Mathlib required")
        def lake_value(name):
            return subprocess.check_output(["lake", "env", "printenv", name], cwd=ROOT, text=True, timeout=30).strip()
        lean = shutil.which("lean", path=lake_value("PATH"))
        if lean is None:
            raise ValueError("Qualified Lean unavailable")
        version = subprocess.check_output([lean, "--version"], text=True, timeout=30).strip()
        if "version 4.28.0" not in version or "7e01a1b" not in version:
            raise ValueError("Exact qualified Lean release required")
        checker = Path(lean).with_name("leanchecker")
        result.update(lean_version=version, lean_sha256=sha(Path(lean).read_bytes()),
                      checker_sha256=sha(checker.read_bytes()), mathlib_revision=revision)
        private = out / "source"
        private.mkdir()
        for name, raw in frozen.items():
            path = private / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        env = dict(os.environ, LEAN_PATH=str(private.resolve()) + os.pathsep + lake_value("LEAN_PATH"))
        env["PATH"] = str(Path(lean).parent) + os.pathsep + env.get("PATH", "")
        def run(command, timeout, limit=False):
            def cap():
                resource.setrlimit(resource.RLIMIT_AS, (6 * 1024**3, 6 * 1024**3))
            elapsed = time.monotonic()
            p = subprocess.run(list(map(str, command)), cwd=private, env=env, capture_output=True,
                               text=True, timeout=timeout, preexec_fn=cap if limit else None)
            row = {"command": list(map(str, command)), "exitcode": p.returncode,
                   "wall_seconds": time.monotonic() - elapsed, "stdout": p.stdout, "stderr": p.stderr}
            result["executions"].append(row)
            save()
            if p.returncode:
                raise ValueError("Actual source/object kernel replay rejected")
            return p.stdout
        stdout = ""
        for name in SOURCE_PATHS:
            path = (private / name).resolve()
            stdout = run([lean, "-j1", "-M2048", "-D", "Elab.async=false", "--root=" + str(private.resolve()),
                          "-o", path.with_suffix(".olean"), path], 120)
        result["axiom_closures"] = inventory(stdout)
        obj = private / "CounterexampleFamily.olean"
        object_hash = sha(obj.read_bytes())
        run([checker, "--verbose", "--fresh", "CounterexampleFamily"], 300, True)
        if hashes != {name: sha(path.read_bytes()) for name, path in SOURCE_PATHS.items()}:
            raise ValueError("Reviewed source changed during replay")
        if before != preservation() or sha(obj.read_bytes()) != object_hash:
            raise ValueError("Committed tree or compiled object changed during replay")
        result.update(kernel_checked=True, fresh_object_replay_checked=True, sources_stable=True,
                      compiled_object_sha256=object_hash)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        result.update(kernel_checked=False, fresh_object_replay_checked=False,
                      error=f"{type(e).__name__}: {e}")
    result["wall_seconds"] = time.monotonic() - started
    save()
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.out)
    print(json.dumps({key: result.get(key) for key in [
        "kernel_checked", "fresh_object_replay_checked", "wall_seconds", "error", "pcs_authority"]}))
    raise SystemExit(0 if result["kernel_checked"] and result["fresh_object_replay_checked"] else 1)


if __name__ == "__main__":
    main()
