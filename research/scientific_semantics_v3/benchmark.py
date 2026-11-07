"""Prospective, matched-source comparison; final inputs require explicit unlock.

The original v2 evaluation is never rewritten. v2 and v3 are scored under the
same new independently prepared protocol here. Final runs refuse unbound source
or annotation changes. Researcher/protocol selection happens on development.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time

from research.scientific_intake_v1.intake import canonical
from .corpus import materialize,source_freeze,FROZEN_SHA256
from .reference import load_reference,load_protocol
from .evaluation import grade,adapt_v2
from .pipeline import run,replay,context,snapshot_artifacts
from .retrieval import evaluate_references


def software_freeze():
    base=Path(__file__).parent
    return {"schema":"scientific-semantics-software-freeze-v3","context":context(),
            "protocol_sha256":hashlib.sha256((base/"reference/protocol.json").read_bytes()).hexdigest(),
            "source_freeze_sha256":FROZEN_SHA256,
            "annotation_freeze_sha256":hashlib.sha256((base/"reference/annotation-freeze.json").read_bytes()).hexdigest(),
            "retrieval_selection":{"default":"tfidf","pool":"combined","basis":"Frozen independent development probes; best top1 on development, no neural routing"},
            "numerical_tolerance":{"relative":1e-7,"rounding_interval_assumption":"nearest at last printed digit; tabulated observations exact"},
            "final_data_used_for_training_or_selection":False,
            "external_expert_validation":False,"authority":False}


def run_benchmark(output,*,split="development",allow_final=False,source_root=None,reference_root=None,expected_software_sha256=None):
    if split=="final" and not allow_final:raise ValueError("final evaluation requires explicit post-freeze opt-in")
    output=Path(output).absolute()
    if output.exists():raise ValueError("refuse benchmark overwrite")
    freeze=software_freeze();encoded=canonical(freeze)+b"\n";freeze_sha=hashlib.sha256(encoded).hexdigest()
    if expected_software_sha256 and freeze_sha!=expected_software_sha256:raise ValueError("software changed after pre-final freeze")
    if split=="final" and expected_software_sha256 is None:raise ValueError("final run requires precommitted software freeze digest")
    refs=load_reference(split,allow_final=allow_final,reference_root=reference_root)
    output.mkdir(parents=True,mode=0o700)
    (output/"software-freeze.json").write_bytes(encoded)
    (output/"started.json").write_bytes(canonical({"utc":datetime.now(timezone.utc).isoformat(),"split":split,"software_sha256":freeze_sha})+b"\n")
    records=materialize(output/"projects",split,allow_final=allow_final,source_root=source_root)
    cases=[];started=time.monotonic()
    for project in records:
        case_start=time.monotonic();packet=output/project["id"]
        summary=run(project["root"],packet,check=True)
        meanings=json.loads((packet/"semantics.json").read_text());checks=json.loads((packet/"checks.json").read_text())
        inventory,artifacts=snapshot_artifacts(packet/"baseline")
        old=json.loads((packet/"baseline/interpretations.json").read_text())
        selected=[r for r in refs if r["project_id"]==project["id"]]
        baseline=grade(selected,adapt_v2(old,inventory),artifacts)
        new=grade(selected,meanings,artifacts,checks)
        retrieval=[]
        for pool in ["v2","structural","combined"]:
            for mode in ["bm25","tfidf","normalized_bm25","hybrid","neural"]:
                measured=evaluate_references(selected,inventory,mode=mode,pool=pool,interpretation=old)
                retrieval.append({"pool":pool,"mode":mode,"result":measured})
        replay_start=time.monotonic();replayed=replay(packet)
        cases.append({"project_id":project["id"],"summary":summary,"baseline_v2_new_protocol":baseline,
                      "semantics_v3_new_protocol":new,"retrieval":retrieval,"independent_replay":replayed,
                      "replay_seconds":time.monotonic()-replay_start,"total_case_seconds":time.monotonic()-case_start,
                      "numerical":[c for c in checks if c.get("checker")=="nist-rounded-model-v3"],
                      "check_statuses":dict(Counter(c["status"] for c in checks)),
                      "old_check_statuses":json.loads((packet/"baseline/summary.json").read_text())["checks"]})
        (output/"partial.json").write_bytes(canonical({"split":split,"completed_cases":cases})+b"\n")
    result={"schema":"scientific-semantics-prospective-benchmark-v3","split":split,"software_sha256":freeze_sha,
            "source_freeze_sha256":FROZEN_SHA256,"cases":cases,"seconds":time.monotonic()-started,
            "parent_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "child_maxrss_kib":resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            "authority":False,"external_expert_validation":False,"training_on_sources":False,
            "test_set_reused_for_development":split=="development",
            "interpretation_scope":"Selected source declarations and reported findings; not arbitrary paper understanding",
            "protocol":load_protocol()}
    (output/"results.json").write_bytes(canonical(result)+b"\n")
    return result
