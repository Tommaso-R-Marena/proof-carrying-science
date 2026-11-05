"""Fresh Lean 4.28 check using read-only existing Mathlib oleans (no downloads).

Normal standalone development can instead use `lake build` in formal/. This
runner avoids downloading/copying Mathlib when a compatible cache already exists.
Only this experiment's formal/.lake/build directory is written.
"""

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess

try:
    from .formal_inputs import dependency_pins, verify_cache, audit_project_sources
except ImportError:  # Direct script invocation documented in README.
    from formal_inputs import dependency_pins, verify_cache, audit_project_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True,
                        help="Read-only repository containing .lake/packages/*/.lake/build/lib/lean")
    args = parser.parse_args()
    project = Path(__file__).resolve().parent / "formal"
    version = subprocess.check_output([str(args.lean), "--version"], text=True)
    if "version 4.28.0," not in version:
        raise SystemExit("Requires Lean 4.28.0")
    print(version.strip(), flush=True)
    pins = dependency_pins(project)
    audit_project_sources(project)
    caches = verify_cache(args.cache_root, pins)
    if not (args.cache_root / ".lake/packages/mathlib/.lake/build/lib/lean/Mathlib/Tactic.olean").is_file():
        raise SystemExit("Pinned prebuilt Mathlib cache required")
    output = project / ".lake" / "build" / "lib" / "lean"
    (output / "PCSAuthorizationHistoryV1").mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, LEAN_PATH=os.pathsep.join(map(str, [output, *caches])))
    for relative in ("PCSAuthorizationHistoryV1/History.lean", "PCSAuthorizationHistoryV1.lean"):
        source = project / relative
        print(f"source_sha256 {hashlib.sha256(source.read_bytes()).hexdigest()} {relative}", flush=True)
        subprocess.run([str(args.lean), "-o", str((output / relative).with_suffix(".olean")), relative],
                       cwd=project, env=environment, check=True)
    # Audit every theorem, including ones not printed by the preserved proof file.
    source = (project / "PCSAuthorizationHistoryV1" / "History.lean").read_text()
    theorems = re.findall(r"^theorem (\w+)", source, re.MULTILINE)
    audit = output.parent.parent / "AxiomAudit.lean"
    audit.write_text("import PCSAuthorizationHistoryV1\n" + "\n".join(
        f"#print axioms PCSAuthorizationHistoryV1.{name}" for name in theorems) + "\n")
    result = subprocess.run([str(args.lean), str(audit)], cwd=project, env=environment,
                            text=True, capture_output=True, check=True)
    print(result.stdout, end="", flush=True)
    lines = result.stdout.splitlines()
    if len(lines) != len(theorems):
        raise SystemExit("Unexpected/incomplete axiom audit output")
    for name, line in zip(theorems, lines):
        prefix = f"'PCSAuthorizationHistoryV1.{name}' "
        if not line.startswith(prefix):
            raise SystemExit("Unexpected axiom audit declaration")
        tail = line[len(prefix):]
        if tail == "does not depend on any axioms":
            continue
        match = re.fullmatch(r"depends on axioms: \[(.*)\]", tail)
        if not match or not set(match[1].split(", ")) <= {"propext", "Classical.choice", "Quot.sound"}:
            raise SystemExit("Unexpected axiom dependency")
    print(f"Fresh standalone library and all {len(theorems)} theorem axiom closures: PASS", flush=True)


if __name__ == "__main__":
    main()
