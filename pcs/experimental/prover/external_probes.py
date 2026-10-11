"""Extract previously untrained theorem types from the exact Lean standard library.

Reference bodies are used only to extract/audit types in a separate process;
they never enter model training, retrieved library entries or proof states.
"""
import hashlib
import json
from pathlib import Path
import subprocess
from .environment import LeanEnvironment,search
from .induction_environment import InductionEnvironment
from .abstraction_environment import AbstractionEnvironment
from .grounded_model import GroundedNetwork
from .reuse_model import ReuseNetwork
from .discovery import decode
from .ir import canonical_declaration,digest
from .language import explain
from .data import structural_fingerprint

SOURCES=[
 ("List.length_reverse","@List.length_reverse Nat","Init/Data/List/Lemmas.lean"),
 ("Nat.add_left_cancel","@Nat.add_left_cancel","Init/Data/Nat/Basic.lean"),
 ("Nat.succ_ne_zero","@Nat.succ_ne_zero","Init/Data/Nat/Basic.lean"),
]

def run(folder):
 folder=Path(folder);registry=json.loads((folder/"registry.json").read_text())
 entry=next(e for e in registry["models"] if e["id"]==registry["selected_local_experiment"])
 model=(GroundedNetwork if entry.get("network")=="grounded" else ReuseNetwork).load(folder/entry["checkpoint"],entry["sha256"])
 base=InductionEnvironment(timeout=30);lib=AbstractionEnvironment(json.loads((folder/"library.json").read_text()),timeout=30)
 source_root=Path(subprocess.check_output([base.lean,"--print-prefix"],text=True).strip())/"src/lean"
 training=json.loads((folder/"tasks.json").read_text())
 forbidden={structural_fingerprint(t["goal"]) for t in training}
 records=[]
 try:
  for i,(name,term,path) in enumerate(SOURCES):
   audit=base._source(f"def PCSExternal{i} := {term}\n#pcs_audit PCSExternal{i}\n","PCS_KERNEL:")
   body=decode(audit["expression"],{})
   goal=canonical_declaration({"format":"pcs-math-ir-v1","binders":[],"body":body})
   if structural_fingerprint(goal) in forbidden:raise ValueError("external probe duplicates an existing task")
   source=source_root/path
   record={"id":name,"source":"leanprover/lean4","source_revision":"7e01a1bf5c70fc6167d49c345d3bf80596e9a79b",
       "source_file":path,"source_file_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"license":"Apache-2.0",
       "goal":goal,"reference_type_audit":audit,"explanation":explain(goal)}
   records.append(record)
  # Freeze independently extracted types before any proposal-policy evaluation.
  (folder/"external-protocol.json").write_text(json.dumps({"tasks":records,"budget":96,"beam":4,
      "selection":"already frozen; no external-based tuning","reference_proofs_exposed_to_model":False},indent=2)+"\n")
  for record in records:
   record["results"]={}
   for name,env,rank in [("selected_model",lib,model.rank),("symbolic",base,None)]:
    env.observations.clear();result=search(env,record["goal"],rank,budget=96,beam=4)
    result.pop("attempts",None);record["results"][name]=result
  result={"format":"pcs-external-lean-probes-v1","source_project":"Lean 4.28 standard library; not Mathlib or a separate researcher project",
          "records":records,"pcs_authority":False,"claim":"Three independently extracted unseen standard-library signatures; no claim of broad external generalization."}
  (folder/"external-results.json").write_text(json.dumps(result,indent=2)+"\n")
  return result
 finally:base.close();lib.close()

if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser();p.add_argument("--models",required=True);a=p.parse_args()
 r=run(a.models);print(json.dumps({x["id"]:{n:v["status"] for n,v in x["results"].items()} for x in r["records"]}))
