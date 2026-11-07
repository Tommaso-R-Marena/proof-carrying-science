"""Real Lean source/axiom audit of partial-expression semantics, not Python."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

from research.scientific_understanding_v2.verify_formal import inspect_source,parse_axiom_audit

THEOREMS=("division_to_inverse","rewrite_preserves_partial_evaluation","rewrite_preserves_definedness",
          "self_division_under_nonzero","self_division_undefined_at_zero","cancellation_changes_domain")
ALLOWED_AXIOMS={"propext","Classical.choice","Quot.sound"}


def verify():
    source=Path(__file__).parent/"formal/PartialExpressions.lean"
    receipt={"schema":"scientific-partial-expression-proof-v3","authority":False,"status":"UNKNOWN",
             "scope":"Structural division-to-guarded-inverse rewriting preserves partial rational evaluation, including undefined points",
             "Python_Lean_refinement":"OPEN","source_interpretation":"OPEN","scientific_adequacy":"OPEN",
             "checked_at_utc":datetime.now(timezone.utc).isoformat(),"allowed_standard_axioms":sorted(ALLOWED_AXIOMS)}
    inspection=inspect_source(source,THEOREMS);receipt.update(inspection)
    compiler=shutil.which("lean")
    if compiler is None:receipt["reason"]="Pinned Lean unavailable";return receipt
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt.update(compiler_sha256=sha(compiler),source_sha256=sha(source))
    try:
        receipt["version"]=subprocess.check_output([compiler,"--version"],text=True,timeout=15).strip()
        shared=Path(compiler).resolve().parent.parent/"lib/lean/libleanshared.so"
        receipt["shared_library_sha256"]=sha(shared)
        env={"PATH":str(Path(compiler).parent)+":/usr/bin:/bin","LANG":"C.UTF-8","LEAN_NUM_THREADS":"1"}
        p=subprocess.run([compiler,"-M1024","-j1",str(source.resolve())],env=env,cwd=source.parent,capture_output=True,text=True,timeout=120)
        receipt.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr,axiom_audit=parse_axiom_audit(p.stdout))
        audits=receipt["axiom_audit"]
        valid=("version 4.28.0," in receipt["version"] and p.returncode==0 and inspection["required_theorems_present"]
               and not inspection["forbidden_tokens"] and not inspection["unexpected_imports"]
               and set(inspection["theorem_declarations"])==set(THEOREMS)
               and all(t in audits and set(audits[t]["axioms"])<=ALLOWED_AXIOMS for t in THEOREMS)
               and receipt["source_sha256"]==sha(source) and receipt["compiler_sha256"]==sha(compiler))
        receipt["status"]="KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS" if valid else "REFUTED"
    except (OSError,subprocess.SubprocessError) as exc:receipt["reason"]=type(exc).__name__
    return receipt


if __name__=="__main__":
    import json
    r=verify();print(json.dumps(r,indent=2,sort_keys=True));raise SystemExit(0 if r["status"]=="KERNEL_CHECKED_ABSTRACT_PARTIAL_SEMANTICS" else 1)
