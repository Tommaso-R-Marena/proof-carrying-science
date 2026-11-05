"""Fresh-kernel induction/reuse/public-path gate; no model assertions are authority."""
import base64
import gzip
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from pcs.experimental.prover.abstraction_environment import AbstractionEnvironment
from pcs.experimental.prover.cli import run
from pcs.experimental.prover.ir import digest

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/"research/induction-abstraction-v2"
STATEMENT="For all lists of natural numbers xs, ys and zs, if ((xs appended to ys) appended to zs) equals (xs appended to (ys appended to zs)) then the length of ((xs appended to ys) appended to zs) equals the length of (xs appended to (ys appended to zs))."

def public_evidence(variables):
    output=subprocess.check_output([sys.executable,"-m","pcs.experimental.prover.public_job"],cwd=ROOT,env=variables,text=True,timeout=120)
    markers=[s for s in output.splitlines() if s.startswith("PCS_LEAN_RESULT_GZIP_V1:")]
    assert len(markers)==1
    compressed=base64.b64decode(markers[0].split(":",1)[1],validate=True)
    assert len(compressed)<=48000 and len(markers[0])<65536
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        raw=stream.read(1000001)
    assert len(raw)<=1000000
    evidence=json.loads(raw)
    assert evidence["request_id"]==variables["PCS_PUBLIC_REQUEST_ID"]
    assert evidence["source_sha256"]==digest(variables["PCS_PUBLIC_STATEMENT"])
    assert evidence["core_sha"]==subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    return evidence,len(markers[0])

def check():
    started=time.monotonic()
    library=json.loads((FOLDER/"library.json").read_text())
    env=AbstractionEnvironment(library,timeout=30)
    independently_checked=0
    try:
        # A separate Lean process checks every admitted fixed library lemma.
        for entry in library["entries"]:
            env.verify(entry["goal"],entry["actions"])
            independently_checked+=1
        result=run(STATEMENT,FOLDER,prepared_env=env)
        assert result["status"]=="verified" and len(result["search"]["receipt"]["actions"])>=5
        receipt=result["search"]["receipt"]
        checked=env.verify(result["formalization"]["candidates"][0]["ir"],receipt["actions"])
        assert checked["goal_sha256"]==receipt["goal_sha256"]
    finally:env.close()
    # Execute the exact public entry point, including log/result packaging.
    actions=[{"kind":"intro","argument":"h0"},{"kind":"intro","argument":"h1"},
             {"kind":"intro","argument":"h2"},{"kind":"constructor","argument":None},
             {"kind":"exact","argument":"h2.2"},{"kind":"exact","argument":"h2.1"}]
    statement="For all propositions A and B, if (A and B) then (B and A)."
    variables={**os.environ,"PCS_PUBLIC_REQUEST_ID":"a"*32,"PCS_PUBLIC_STATEMENT":statement,
               "PCS_PUBLIC_INTERPRETATION":"0","PCS_PUBLIC_PROOF_ACTIONS":json.dumps(actions),"PCS_PUBLIC_MODEL_FAMILY":""}
    evidence,_=public_evidence(variables)
    assert evidence["result"]["status"]=="verified" and evidence["actions_sha256"]==digest(actions)
    assert evidence["previous"] is None and evidence["automatic_training_authorization"] is False
    # The full hosted code path also includes library construction, all three
    # policies and their complete result; a codec-only fixture is insufficient.
    variables.update(PCS_PUBLIC_REQUEST_ID="b"*32,PCS_PUBLIC_STATEMENT=STATEMENT,
                     PCS_PUBLIC_PROOF_ACTIONS="",PCS_PUBLIC_MODEL_FAMILY="induction-abstraction-v2")
    model_evidence,line_bytes=public_evidence(variables)
    assert model_evidence["model_family"]=="induction-abstraction-v2"
    assert model_evidence["automatic_training_authorization"] is False
    meaning=model_evidence["result"]["formalization"]["candidates"][0]
    replay=AbstractionEnvironment(library,timeout=30)
    try:
        for key in ["result","previous","baseline"]:
            item=model_evidence[key]
            assert item["status"]=="verified" and item["pcs_authority"] is False
            proof=item["search"]["receipt"]
            assert len(proof["actions"])>=5 and proof["goal_sha256"]==meaning["interpretation_sha256"]
            checked=replay.verify(meaning["ir"],proof["actions"])
            assert checked["goal_sha256"]==proof["goal_sha256"]
    finally:replay.close()
    print(json.dumps({"fresh_library_proofs":independently_checked,"unseen_model_actions":len(receipt["actions"]),
                      "exact_public_human_path":True,"exact_public_three_policy_path":True,
                      "public_model_log_line_bytes":line_bytes,"wall_seconds":time.monotonic()-started}))
if __name__=="__main__":check()
