"""Check frozen bytes, splits, measured outcomes and safe checkpoint loading."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
from pcs.experimental.prover.ir import digest
from pcs.experimental.prover.reuse_model import ReuseNetwork
from pcs.experimental.prover.grounded_model import GroundedNetwork
from pcs.experimental.prover.reuse_experiment import metrics
from pcs.experimental.prover.data import structural_fingerprint

ROOT=Path(__file__).resolve().parents[1]
def read(path):
 return json.loads(path.read_text() if path.exists() else gzip.decompress(path.with_suffix(path.suffix+".gz").read_bytes()))
def check():
 count=0
 for generation in [1,2]:
  p=ROOT/f"research/induction-abstraction-v{generation}"
  seal=read(p/"EVIDENCE_SHA256.json")
  actual={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob("*") if f.is_file() and f.name!="EVIDENCE_SHA256.json"}
  assert seal==actual,"evidence bytes/membership changed"
  tasks=read(p/"tasks.json");protocol=read(p/"protocol.json");assert digest(tasks)==protocol["tasks_sha256"]
  training={structural_fingerprint(t["goal"]) for t in tasks if t["split"]=="train"}
  heldout={structural_fingerprint(t["goal"]) for t in tasks if t["split"]!="train"}
  assert not training&heldout
  registry=read(p/"registry.json");assert registry["production_authority"] is False
  assert registry["selection_frozen_before_final"] is True
  assert digest(read(p/"library.json"))==registry["library_sha256"]
  manifest=read(p/"source-manifest.json")
  with tarfile.open(p/"source-overlay.tar.gz") as archive:
   members={m.name:m for m in archive.getmembers() if m.isfile()}
   assert set(members)==set(manifest)
   for name,sha in manifest.items():assert hashlib.sha256(archive.extractfile(members[name]).read()).hexdigest()==sha
  for e in registry["models"]:
   assert Path(e["checkpoint"]).name==e["checkpoint"] and e["pcs_authority"] is False
   model=(GroundedNetwork if e.get("network")=="grounded" else ReuseNetwork).load(p/e["checkpoint"],e["sha256"])
   assert sum(v.numel() for v in model.parameters())==e["parameters"];count+=1
  evaluation=read(p/"evaluations.json");summary=read(p/"summary.json")
  for split,policies in evaluation.items():
   for name,rows in policies.items():
    assert all(summary["metrics"][split][name][k]==v for k,v in metrics(rows).items())
    assert all(r["result"]["expansions"]<=protocol["budget"] for r in rows)
    for r in rows:
     if r["result"]["status"]=="verified":
      receipt=r["result"]["receipt"];assert receipt["goal_sha256"]==digest(r["goal"])
      assert set(receipt["kernel"]["axioms"])<={"propext","Classical.choice","Quot.sound"}
  reports=read(p/"training.json")
  assert all(r["weights_changed"] for name,r in reports.items() if name.startswith("rl"))
  assert all("message.weight" in r["changed_parameters"] for name,r in reports.items() if name.startswith("graph"))
 print(json.dumps({"artifact_integrity":True,"checkpoints":count,"scope":"Bytes, provenance and metric consistency; mathematical authority additionally requires independent Lean replay."}))
if __name__=="__main__":check()
