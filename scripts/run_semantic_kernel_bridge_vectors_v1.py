"""Run every Aristotle signed semantic fixture through the PCS production Python adapter.

Requires actual Lean 4.28 compiled executable; never regenerates fake passes.
This is cross-language operational regression, not kernel proof of compiler correctness.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs.semantic_kernel_bridge_v1 import evaluate,digest

DIR=ROOT/"formal/fixtures/semantic_translation_v1"
BIN=ROOT/"formal/.lake/build/bin/pcs-semantic-check"

def main()->int:
    if not BIN.is_file() or not (DIR/"expected.json").is_file():
        raise SystemExit("BLOCKED_MISSING_LEAN_BINARY_OR_FIXTURES")
    index=json.loads((DIR/"expected.json").read_text(encoding="utf-8"))
    if index.get("schema")!="pcs-semantic-fixtures-v1" or len(index.get("fixtures",[]))!=36:
        raise SystemExit("INVALID_FIXTURE_INDEX")
    binary_sha=digest(BIN.read_bytes())
    actual=[]
    for record in index["fixtures"]:
        authority=(DIR/record["authority"]).resolve()
        request=(DIR/record["request"]).resolve()
        if not authority.is_relative_to(DIR.resolve()) or not request.is_relative_to(DIR.resolve()):
            raise SystemExit("ESCAPED_FIXTURE_PATH")
        a,r=authority.read_bytes(),request.read_bytes()
        decision=evaluate(BIN,binary_sha256=binary_sha,
                          authority_bytes=a,authority_sha256=digest(a),request_bytes=r)
        expected={"ACCEPTED":"CHECKER_ACCEPTED_BOUNDED",
                  "REJECTED":"REJECTED","NEEDS_CLARIFICATION":"NEEDS_CLARIFICATION"}[record["verdict"]]
        codes={item["code"] for item in decision["diagnostics"]}
        if decision["state"]!=expected or not set(record["codes"]).issubset(codes):
            raise SystemExit("SEMANTIC_VECTOR_FAILED "+record["name"]+
                             " expected="+expected+" got="+decision["state"]+
                             " diagnostics="+str(sorted(codes)))
        if decision["pcs_scientific_authority"] or decision["independent_kernel_receipt"]:
            raise SystemExit("UNAUTHORIZED_AUTHORITY_ASSERTION")
        actual.append({"fixture":record["name"],"status":decision["state"],
                       "request_sha256":decision["request_sha256"]})
    summary={"format":"pcs-semantic-cross-language-fixtures-v1",
             "binary_sha256":binary_sha,"source_fixture_index_sha256":digest((DIR/"expected.json").read_bytes()),
             "fixture_count":len(actual),"passed":len(actual),
             "pcs_scientific_authority":False,"independent_kernel_receipt":False,
             "results":actual}
    print(json.dumps(summary,sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
