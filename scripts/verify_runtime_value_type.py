#!/usr/bin/env python3
"""Freshly check Value::ty source extraction against a receiver-selected CertiForge checkout."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_lean_source import audit
from verify_runtime_refinement import check_window

NAMES = ("value_ty_source_bound", "value_ty_precedence_checked", "rust_value_ty", "rust_value_ty_zero_fuel")
PREFIX = "PCSForgeRefinement.Rust."


def verify(certiforge: Path):
    current = certiforge / "crates/certir-interpreter/src/lib.rs"
    snapshot = ROOT / "formal/source_reference/certiforge/crates/certir-interpreter/src/lib.rs.txt"
    binding = check_window(snapshot.read_bytes(), current.read_bytes(), 21, 26)
    module = ROOT / "formal/tools/RuntimeValueType.lean"
    findings = audit([module])
    if findings: raise ValueError("\n".join(findings))
    result = subprocess.run(["lake", "env", "lean", str(module)], cwd=ROOT / "formal", text=True, capture_output=True, timeout=120)
    if result.returncode: raise RuntimeError(result.stdout + result.stderr)
    names = re.findall(r"^'([^']+)' depends on axioms: \[([^\]]*)\]$", result.stdout, re.M)
    if {n for n,_ in names} != {PREFIX+n for n in NAMES} or len(names) != len(NAMES):
        raise ValueError("incomplete fresh axiom audit")
    used = {a.strip() for _,aa in names for a in aa.split(",") if a.strip()}
    if not used <= {"propext", "Classical.choice", "Quot.sound"}: raise ValueError("unapproved kernel axioms")
    return {"format":"pcs-rust-value-type-refinement-v1", "source_window":[21,26], "window_sha256":binding,
            "current_source_sha256":hashlib.sha256(current.read_bytes()).hexdigest(),
            "proof_source_sha256":hashlib.sha256(module.read_bytes()).hexdigest(),
            "kernel_theorems":{n:[a.strip() for a in aa.split(",") if a.strip()] for n,aa in names},
            "axiom_log":result.stdout, "rust_value_type_refinement_proved":True,
            "rust_top_level_eval_extracted":False, "rust_type_checker_extracted":False,
            "scope":"Value::ty helper only; all runtime values and every positive call-depth fuel. No native compiler or Rust semantics metatheorem is claimed.",
            "pcs_scientific_authority":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certiforge", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args=parser.parse_args()
    report=verify(args.certiforge.resolve())
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"fresh_theorems":len(report["kernel_theorems"]),"value_type_refinement_proved":True,"top_level_eval_extracted":False}))


if __name__=="__main__":main()
