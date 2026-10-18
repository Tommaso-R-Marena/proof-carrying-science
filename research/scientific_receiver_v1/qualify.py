"""Freshly check receiver sources and inventory the actual Lean environment.

Default mode uses Lake and this checkout's pinned dependency cache. Local
--dependency-checkout mode reads source-identical previously qualified import
objects without writing to that checkout; it never claims a fresh dependency
rebuild. Both modes freshly compile every new receiver module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "research/scientific_receiver_v1/formal"
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(out: Path, dependency_checkout: Path | None = None) -> dict:
    from scripts.audit_lean_source import audit

    out.mkdir(parents=True, exist_ok=False)
    sources = sorted(PROJECT.glob("*.lean")) + sorted((PROJECT / "PCSScientificReceiver").glob("*.lean"))
    findings = audit(sources)
    if findings:
        raise RuntimeError("forbidden formal source: " + repr(findings))
    pinned = sources + [PROJECT / name for name in ("lakefile.toml", "lake-manifest.json", "lean-toolchain")]
    before = {str(p.relative_to(ROOT)): sha(p) for p in pinned}
    env = os.environ.copy()
    lean = Path(shutil.which("lean") or "").resolve()
    if not lean.is_file():
        raise RuntimeError("pinned Lean must be on PATH")
    version = subprocess.check_output([str(lean), "--version"], text=True)
    if "version 4.28.0" not in version:
        raise RuntimeError("Lean 4.28.0 required")
    dependency_evidence = {}
    started = time.monotonic()
    if dependency_checkout:
        base = dependency_checkout.resolve()
        scopes = ["formal", "research/integration_v1/formal", "incubation/pcs_certified_numerics_v1", "incubation/pcs_conservation_algebra_v1"]
        paths = subprocess.check_output(["git", "ls-files", "--", *scopes], cwd=ROOT, text=True).splitlines()
        for name in paths:
            if not (base / name).is_file() or sha(ROOT / name) != sha(base / name):
                raise RuntimeError("read-only dependency source differs: " + name)
        pins = json.loads((ROOT / "lake-manifest.json").read_text())
        libraries = []
        revisions = {}
        for p in pins["packages"]:
            if p["type"] != "git":
                continue
            folder = base / ".lake/packages" / p["name"]
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip()
            dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=folder, text=True).strip()
            if head != p["rev"] or dirty:
                raise RuntimeError("dirty or unpinned dependency: " + p["name"])
            revisions[p["name"]] = head
            libraries.append(folder / ".lake/build/lib/lean")
        own = out / "fresh-lean"
        own.mkdir(parents=True, exist_ok=True)
        roots = [own, *(base / s / ".lake/build/lib/lean" for s in scopes[1:]), base / "formal/.lake/build/lib/lean", *libraries]
        env["LEAN_PATH"] = os.pathsep.join(map(str, roots))
        with (out / "build.log").open("w") as log:
            modules = ["Types", "Semantics", "Codec", "Receiver"]
            if (PROJECT / "PCSScientificReceiver/History.lean").is_file():
                modules.append("History")
            for module in modules + ["PCSScientificReceiver", "Main"]:
                relative = Path(module + ".lean") if module in {"PCSScientificReceiver", "Main"} else Path("PCSScientificReceiver") / (module + ".lean")
                target = (own / relative).with_suffix(".olean")
                target.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([str(lean), "-o", str(target), str(PROJECT / relative)], cwd=PROJECT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        command = [str(lean), "--run", str(PROJECT / "Main.lean")]
        audit_command = [str(lean), str(PROJECT / "Audit.lean")]
        dependency_evidence = {"mode": "read-only source-identical prebuilt imports", "fresh_dependency_rebuild": False,
                               "checkout_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base, text=True).strip(),
                               "source_files_compared": len(paths), "dependency_revisions": revisions}
    else:
        with (out / "build.log").open("w") as log:
            subprocess.run(["lake", "build", "PCSScientificReceiver", "+Main:olean"], cwd=PROJECT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        command = ["lake", "env", "lean", "--run", str(PROJECT / "Main.lean")]
        audit_command = ["lake", "env", "lean", str(PROJECT / "Audit.lean")]
        dependency_evidence = {"mode": "Lake pinned dependencies", "fresh_new_library_build": True}
    p = subprocess.run(audit_command, cwd=PROJECT, env=env, text=True, capture_output=True, check=True)
    output = p.stdout + p.stderr
    (out / "statements-and-axioms.log").write_text(output)
    closures = {n: sorted(set(re.findall(r"[A-Za-z_.]+", a))) for n, a in re.findall(r"'([^']+)' depends on axioms: \[([^]]*)\]", output, re.S)}
    closures.update({n: [] for n in re.findall(r"'([^']+)' does not depend on any axioms", output)})
    if not closures or any(set(a) - ALLOWED_AXIOMS for a in closures.values()):
        raise RuntimeError("empty or unapproved actual theorem closure")
    if before != {str(p.relative_to(ROOT)): sha(p) for p in pinned}:
        raise RuntimeError("source changed during qualification")
    report = {"format": "pcs-scientific-receiver-qualification-v1", "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_sha256": before, "lean_version": version.strip(), "lean_sha256": sha(lean),
              "dependency_evidence": dependency_evidence, "axiom_closures": dict(sorted(closures.items())),
              "theorems_including_generated": len(closures), "wall_seconds": time.monotonic() - started,
              "command": command, "cwd": str(PROJECT), "execution": "Lean --run compiled IR; not standalone native executable",
              "scientific_acceptance": False, "production_authority": False,
              "trust": "Lean kernel/compiler/runtime, import objects, toolchain, IO, JSON rendering, reviewed source/configuration, Git and host remain trusted. No independently protected root is established."}
    (out / "qualification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (out / "environment.json").write_text(json.dumps({"LEAN_PATH": env.get("LEAN_PATH", "")}) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dependency-checkout", type=Path)
    a = parser.parse_args()
    r = qualify(a.out.resolve(), a.dependency_checkout)
    print(json.dumps({"theorems": r["theorems_including_generated"], "production_authority": False}))
