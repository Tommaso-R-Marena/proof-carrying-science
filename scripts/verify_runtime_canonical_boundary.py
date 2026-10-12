#!/usr/bin/env python3
"""Audit the necessary canonical-input precondition against actual selected Rust source windows."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_lean_source import audit
from verify_runtime_refinement import check_sources
from verify_omega_dd_formal import check_inventory

NAMES=["PCSRuntimeCanonicalInputs."+name for name in ("checked_certificate_and_types", "matching_type_tag_is_insufficient",
       "transcribed_top_level_disagrees", "source_extracted_expression_disagrees", "canonical_input_preserves_rewrite")]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certiforge",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    windows=check_sources({"proof-carrying-science":ROOT,"certiforge":args.certiforge.resolve()})
    module=ROOT/"formal/tools/RuntimeCanonicalInputs.lean"
    problems=audit([module])
    if problems:raise ValueError("\n".join(problems))
    result=subprocess.run(["lake","env","lean",str(module)],cwd=ROOT/"formal",text=True,capture_output=True,timeout=120)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    axioms=check_inventory(result.stdout,NAMES)
    report={"format":"pcs-runtime-canonical-input-boundary-v1","kernel_theorems":axioms,
            "actual_certiforge_windows":[w for w in windows if w["component"]=="certiforge"],
            "source_sha256":hashlib.sha256(module.read_bytes()).hexdigest(),"axiom_log":result.stdout,
            "scope":"Canonical input is a necessary hypothesis. Expression-level counterexample uses unchanged source-extracted Rust semantics. The top-level counterexample is about the archived unguarded transcription at CertiForge 415a1de40eaeadc366ac2d824c05ee52bb2bd66e, not the new tested checked wrapper. No source-bound proof of the new wrapper, and no contradiction of the existing canonical-input theorem.",
            "rust_top_level_eval_extracted":False,"pcs_scientific_authority":False}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"fresh_theorems":len(axioms),"canonical_precondition_necessary":True,"top_level_eval_extracted":False}))


if __name__=="__main__":main()
