"""Fail-closed independent gate for the Aristotle Omega/BDD reference models.

Run after `cd formal && lake build`. No uploaded log or model prediction can
replace compilation, a complete axiom inventory, or semantic negative controls.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_lean_source import active_code, audit

ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
MANIFEST = ROOT / "research/aristotle-omega-dd-v1/source-manifest.json"


def check_control_overlay(original: str, integrated: str) -> dict:
    """Keep every original assertion and executable control definition intact."""
    boundary = re.compile(r"(?m)^(?:def|structure|theorem|example|set_option|end|namespace|open)\b")

    def declarations(source: str) -> Counter:
        source = active_code(source)
        points = list(boundary.finditer(source))
        result = []
        for index, match in enumerate(points):
            stop = points[index + 1].start() if index + 1 < len(points) else len(source)
            text = source[match.start():stop].strip()
            kind = text.split()[0]
            if kind in {"def", "structure"}:
                result.append((kind, " ".join(text.split())))
            elif kind in {"theorem", "example"}:
                if ":=" not in text:
                    raise ValueError("Missing original control proof body")
                result.append((kind, " ".join(text.split(":=", 1)[0].split())))
        return Counter(result)

    original_declarations = declarations(original)
    integrated_declarations = declarations(integrated)
    for declaration, count in original_declarations.items():
        if integrated_declarations[declaration] < count:
            raise ValueError("Original control assertion or definition changed: " + declaration[1][:160])
    return {
        "original_declarations_preserved": sum(original_declarations.values()),
        "original_assertions_preserved": sum(
            count for (kind, _), count in original_declarations.items()
            if kind in {"theorem", "example"}
        ),
    }


def check_inventory(output: str, expected: list[str]) -> dict[str, list[str]]:
    rows = re.findall(
        r"^'([^ ]+)' (?:depends on axioms: \[([^\]]*)\]|(does not depend on any axioms))$",
        output, re.MULTILINE,
    )
    if len(rows) != len(expected) or {r[0] for r in rows} != set(expected):
        raise ValueError("Missing, duplicate or substituted theorem axiom inventory")
    result = {}
    for name, axioms, _empty in rows:
        used = sorted(a.strip() for a in axioms.split(",") if a.strip())
        if not set(used) <= ALLOWED_AXIOMS:
            raise ValueError(f"Unapproved axiom dependency: {name}: {used}")
        result[name] = used
    return result


def check_negative(returncode: int, output: str, propositions: list[str]) -> None:
    if returncode == 0 or output.count("Tactic `decide` proved that the proposition") != len(propositions):
        raise ValueError("False claim was not rejected by the semantic decision procedure")
    for proposition in propositions:
        if not re.search(r"Tactic `decide` proved that the proposition\s+" +
                         re.escape(proposition) + r"\s+is false", output):
            raise ValueError(f"Missing expected semantic rejection: {proposition}")
    # An import/syntax failure must never stand in for a successfully checked
    # reference computation followed by rejection of the deliberately false claim.
    if len(re.findall(r"\berror:", output)) != len(propositions):
        raise ValueError("Unexpected additional Lean errors in a negative control")


def verify(formal: Path, output: Path | None = None, returned_environment: bool = False) -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source_hashes = manifest["returned_sources"] if returned_environment else manifest["sources"]
    paths = [formal / p for p in source_hashes]
    for path in paths:
        if hashlib.sha256(path.read_bytes()).hexdigest() != source_hashes[path.relative_to(formal).as_posix()]:
            raise ValueError(f"Returned proof source identity changed: {path}")
    for name, key in [("lakefile.toml", "configuration_sha256"), ("lean-toolchain", "toolchain_sha256"),
                      ("lake-manifest.json", "lock_sha256")]:
        if returned_environment and name == "lakefile.toml":
            key = "returned_configuration_sha256"
        if hashlib.sha256((formal / name).read_bytes()).hexdigest() != manifest[key]:
            raise ValueError(f"Formal environment identity changed: {name}")
    overlay = None
    if not returned_environment:
        for name, digest in manifest["returned_sources"].items():
            original = ROOT / manifest["returned_control_archive"] if name == "PCSDecisionDiagram/Controls.lean" else formal / name
            if hashlib.sha256(original.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Original returned source identity changed: {name}")
        overlay = check_control_overlay((ROOT / manifest["returned_control_archive"]).read_text(encoding="utf-8"),
                                        (formal / "PCSDecisionDiagram/Controls.lean").read_text(encoding="utf-8"))
    findings = audit(paths)
    for path in paths:
        if re.search(r"Lean\s*\.\s*ofReduceBool|\brun_cmd\b|\binitialize\b|#eval|\belab\b|\bmacro\b",
                     active_code(path.read_text(encoding="utf-8"))):
            findings.append(f"Unexpected active proof escape/extension: {path}")
    if findings:
        raise ValueError("\n".join(findings))

    logs = {}
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(args, cwd=formal, capture_output=True, text=True, timeout=180)

    version = run("lean", "--version")
    if version.returncode or not re.search(r"version 4\.28\.0,.*commit 7e01a1bf5c70", version.stdout):
        raise ValueError("Expected the exact Lean 4.28.0 release environment")
    result = run("lake", "env", "lean", "PCSOmegaDDAudit.lean")
    logs["axioms.log"] = result.stdout + result.stderr
    if result.returncode:
        raise ValueError(logs["axioms.log"])
    inventories = check_inventory(result.stdout, manifest["principal_audit_names"])
    full_source = ROOT / (manifest["returned_integration_audit_path"] if returned_environment else "formal/PCSOmegaDDFullAudit.lean")
    audit_digest = manifest["returned_integration_audit_sha256"] if returned_environment else manifest["integration_audit_sha256"]
    if hashlib.sha256(full_source.read_bytes()).hexdigest() != audit_digest:
        raise ValueError("Integration axiom audit identity changed")
    # Declaration inspection only: no native proof decision.
    result = run("lake", "env", "lean", str(full_source))
    logs["all-axioms.log"] = result.stdout + result.stderr
    if result.returncode:
        raise ValueError(logs["all-axioms.log"])
    all_inventories = check_inventory(result.stdout, manifest["original_positive_theorem_names"] if returned_environment else manifest["all_positive_theorem_names"])
    controls = {
        "FalseEquivalence.lean": ["check (A.imp B) (B.imp A) = none"],
        "FalseWeightedMinimum.lean": ["some 1 = some 0", "some [1] = some [0]"],
    }
    for file, propositions in controls.items():
        negative = run("lake", "env", "lean", "PCSNegative/" + file)
        logs[file + ".log"] = negative.stdout + negative.stderr
        check_negative(negative.returncode, logs[file + ".log"], propositions)
    report = {
        "format": "pcs-omega-dd-independent-gate-v1", "run_id": manifest["run_id"],
        "archive_sha256": manifest["archive_sha256"], "lean_version": version.stdout.strip(),
        "source_files": len(paths), "principal_axiom_inventories": inventories,
        "original_positive_theorems": len(manifest["original_positive_theorem_names"]),
        "certificate_helper_theorems": 0 if returned_environment else len(manifest["certificate_helper_theorem_names"]),
        "control_overlay": overlay,
        "all_positive_theorem_axiom_inventories": all_inventories,
        "negative_files": len(controls), "false_claims_rejected": sum(map(len, controls.values())),
        "source_admission_audit": "passed", "implementation_refinement_proved": False,
        "pcs_authority": False,
        "configuration": "returned" if returned_environment else "integrated",
    }
    if output:
        output.mkdir(parents=True, exist_ok=False)
        for name, log in logs.items():
            (output / name).write_text(log)
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-dir", type=Path, default=ROOT / "formal")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--returned-environment", action="store_true",
                        help="Inspect exact returned configuration, separate from the production CI gate")
    args = parser.parse_args()
    print(json.dumps(verify(args.formal_dir.resolve(), args.output, args.returned_environment), indent=2))
