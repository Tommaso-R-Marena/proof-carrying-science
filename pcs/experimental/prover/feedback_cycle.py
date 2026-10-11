"""Explicit authored/consented feedback cycle; no automatic registry promotion."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import time
from .cli import run
from .library import LibraryEnvironment
from .abstraction_environment import AbstractionEnvironment
from .grounded_model import GroundedNetwork
from .reuse_model import ReuseNetwork
from .data import intake_feedback
from .model import imitate
from .ir import digest

def cycle(statement,models,output,*,license,source_revision,heldout):
 output=Path(output);output.mkdir(parents=True,exist_ok=False);models=Path(models)
 registry=json.loads((models/"registry.json").read_text())
 entry=next(e for e in registry["models"] if e["id"]==registry["selected_local_experiment"])
 cls=GroundedNetwork if entry.get("network")=="grounded" else ReuseNetwork
 model=cls.load(models/entry["checkpoint"],entry["sha256"])
 env=AbstractionEnvironment(json.loads((models/"library.json").read_text()),timeout=30)
 start=time.monotonic()
 try:
  result=run(statement,models,budget=96,prepared_env=env)
  if result["status"]!="verified":raise ValueError("no checked feedback available: "+result["status"])
  example=intake_feedback(env,result["training_feedback"],heldout,license=license,source_revision=source_revision)
  report=imitate(model,[example],epochs=4,seed=53,candidate_provider=env.candidates)
  sha=model.save(output/"candidate.json",{"parent_sha256":entry["sha256"],"example_sha256":digest(example),"approval":"unapproved experimental candidate"})
  (output/"problem-result.json").write_text(json.dumps(result,indent=2)+"\n")
  (output/"independently-checked-example.json").write_text(json.dumps(example,indent=2)+"\n")
  summary={"format":"pcs-explicit-feedback-cycle-v1","parent_checkpoint_sha256":entry["sha256"],"candidate_sha256":sha,
    "training":report,"source_license":license,"source_revision":source_revision,"wall_seconds":time.monotonic()-start,
    "automatic_promotion":False,"heldout_evaluation_performed":False,"self_improvement_claim":False,
    "gpu_used":False,"financial_spend":0,"pcs_authority":False}
  (output/"report.json").write_text(json.dumps(summary,indent=2)+"\n")
  return summary
 finally:env.close()

if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("statement");p.add_argument("--models",required=True);p.add_argument("--output",required=True);p.add_argument("--license",required=True);p.add_argument("--source-revision",required=True);p.add_argument("--heldout",required=True);a=p.parse_args()
 tasks=json.loads(Path(a.heldout).read_text())
 print(json.dumps(cycle(a.statement,a.models,a.output,license=a.license,source_revision=a.source_revision,heldout=[t for t in tasks if t["split"]!="train"])))
