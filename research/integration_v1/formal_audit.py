"""Build an isolated library and query every public theorem's type/axiom closure."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def audit(project: Path, imports: list[str], prefix: str, out: Path):
    from scripts.audit_lean_source import audit as source_audit
    project = project.resolve()
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.']*", name) for name in [*imports, prefix]):
        raise ValueError("invalid Lean module or namespace identifier")
    out.mkdir(parents=True, exist_ok=False)
    relative = project.relative_to(ROOT).as_posix()
    paths = subprocess.check_output(["git", "ls-files", "--", relative], cwd=ROOT, text=True).splitlines()
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
               for p in paths if p.endswith(".lean")}
    if not sources:
        raise RuntimeError("no tracked project Lean sources")
    # The shared main formal project also contains unrelated, deliberately
    # untrusted prover tasks. Its protected authority keeps verify_lean.sh's
    # existing scope. Audit this requested library's source namespace here;
    # all newly imported Lean is additionally covered by source_gate.py.
    admission_sources = (list(sources) if relative != "formal" else
                         [p for p in sources if
                          (ROOT / p).relative_to(project).parts[0].startswith(prefix)])
    if not admission_sources:
        raise RuntimeError("selected library has no tracked Lean source namespace")
    findings = source_audit([ROOT / p for p in admission_sources])
    if findings:
        raise RuntimeError("forbidden active Lean source: " + "\n".join(findings))
    started = time.monotonic()
    build = subprocess.run(["lake", "build", *imports], cwd=project, capture_output=True, text=True)
    (out / "build.log").write_text(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError("actual Lean build failed: " + str(out / "build.log"))
    code = "\n".join("import " + name for name in imports) + "\nimport Lean\n"
    code += '''
set_option pp.universes true
set_option pp.fullNames true
open Lean Elab Command
run_cmd do
  let constants := (← getEnv).constants.toList
  for (name, info) in constants do
    match info with
    | .thmInfo _ =>
        if PREFIX.isPrefixOf name.toString then
          elabCommand (← `(#check $(mkIdent name)))
          elabCommand (← `(#print axioms $(mkIdent name)))
    | _ => pure ()
'''.replace("PREFIX", json.dumps(prefix + "."))
    # Scratch proof contains only the public environment queries shown above.
    with tempfile.TemporaryDirectory(prefix="pcs-formal-audit-") as temporary:
        query = Path(temporary) / "Query.lean"
        query.write_text(code)
        process = subprocess.run(["lake", "env", "lean", str(query)], cwd=project,
                                 capture_output=True, text=True)
    text = process.stdout + process.stderr
    (out / "statements-and-axioms.log").write_text(text)
    (out / "Query.lean").write_text(code)
    if process.returncode:
        raise RuntimeError("actual Lean environment audit failed: " + str(out))
    closures = {name: sorted(set(re.findall(r"[A-Za-z_.]+", axioms))) for name, axioms in
                re.findall(r"'([^']+)' depends on axioms: \[([^]]*)\]", text, re.S)}
    closures.update({name: [] for name in re.findall(r"'([^']+)' does not depend on any axioms", text)})
    if not closures or any(set(v) - {"propext", "Classical.choice", "Quot.sound"} for v in closures.values()):
        raise RuntimeError("empty theorem inventory or unapproved axiom closure")
    if sources != {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}:
        raise RuntimeError("source changed during qualification")
    result = {"format": "pcs-public-theorem-environment-audit-v1", "project": relative,
              "imports": imports, "prefix": prefix, "theorems": len(closures),
              "axiom_closures": dict(sorted(closures.items())), "source_sha256": sources,
              "admission_source_paths": admission_sources,
              "actual_lean_build": True, "source_unchanged_during_audit": True,
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "note": "Public theorem inventory includes compiler-generated theorem declarations; private dependencies are included in closure.",
              "production_authority": False}
    (out / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--import", dest="imports", required=True, action="append")
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.project, args.imports, args.prefix, args.out.resolve())
    print(json.dumps({"project": result["project"], "public_theorems": result["theorems"],
                      "actual_lean_build": True, "standard_axioms_only": True}))


if __name__ == "__main__":
    main()
