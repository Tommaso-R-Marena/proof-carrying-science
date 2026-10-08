"""Curated reproducible fixture evaluation. These are machine-generated fixtures, NOT human traces."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

HELD_OUT = {"neg_quantifier_order", "neg_variable_capture",
            "neg_lean_source_mismatch", "pos_unbounded_ne_normalization"}
def prepare(root: Path) -> dict:
    src=root/"expected.json"
    manifest=json.loads(src.read_text(encoding="utf-8"))
    if manifest.get("schema")!="pcs-semantic-fixtures-v1":
        raise ValueError("wrong fixture index")
    rows=[]; seen=set()
    for e in manifest["fixtures"]:
        if set(e)!={"name","authority","request","verdict","codes"}:
            raise ValueError("unexpected fixture fields")
        if e["name"] in seen or "/" in e["name"] or ".." in e["name"]:
            raise ValueError("duplicate/invalid fixture name")
        seen.add(e["name"])
        request=(root/e["request"]).resolve()
        if not request.is_relative_to(root.resolve()) or not request.is_file():
            raise ValueError("escaped/missing fixture")
        raw=request.read_bytes()
        if len(raw)>1_000_000: raise ValueError("oversized fixture")
        value=json.loads(raw)
        if value.get("schema")!="pcs-semantic-translation-v1":
            raise ValueError("wrong request schema")
        rows.append({"fixture_id":e["name"],"split":"evaluation" if e["name"] in HELD_OUT else "development",
                     "request_sha256":hashlib.sha256(raw).hexdigest(),"expected_verdict":e["verdict"],
                     "expected_failure_codes":e["codes"],"origin":"aristotle_generated_test_fixture",
                     "human_trajectory":False,"learned_model_supervision_approved":False})
    return {"format":"pcs-semantic-golden-evaluation-v1","scope":"machine-generated fixtures; no human data",
            "authority":"NOT_REPLAYED_BY_THIS_EXPORTER",
            "origin_commit":"aristotle-semantic-v1-snapshot","examples":rows,
            "counts":{"all":len(rows),"development":sum(r["split"]=="development" for r in rows),
                      "evaluation":sum(r["split"]=="evaluation" for r in rows)}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("fixture_root",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    data=prepare(a.fixture_root)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
