"""Semantic transcript checks; no affirmative neural-computation attestation."""
from pathlib import Path

from research.real_model_safety_v1.audit import validate as old_validate,same,load
from pcs.jsonio import strict_json_loads
from research.progress_supervisor_v1.evidence import write,read
from research.progress_supervisor_v1.certificate import encode
from .artifacts import LEGACY,EXPERIMENT_SHA,digest,lock
from .protocol import FORMAT,request,check_ready,check_output,closed,sources


def legacy(root,oracle):
    report,captures=old_validate(root)
    same(report["model"]["files"],lock())
    count=0
    for episode in report["episodes"]:
        if episode["origin"]!="model":continue
        for turn in episode["turns"]:
            raw=oracle.validate(turn["prompt"],turn["generated"])
            same(raw.hex(),turn["proposal_hex"]);count+=1
    if count!=42:raise ValueError("complete 42-request corpus required")
    return report,captures


def reference(oracle):
    if digest((LEGACY/"experiment.json").read_bytes())!=EXPERIMENT_SHA:
        raise ValueError("reference corpus changed")
    return legacy(LEGACY,oracle)


def run_report(path,oracle):
    report,captures=reference(oracle)
    raw_report=read(path)
    value=strict_json_loads(raw_report.decode("utf-8",errors="strict"))
    fields={"format","reference_sha256","sources","ready","closed","requests","files","all_matched","training_eligibility"}
    if type(value) is not dict or set(value)!=fields:raise ValueError("exact run report schema required")
    same(value["format"],FORMAT);same(value["reference_sha256"],EXPERIMENT_SHA)
    same(value["sources"],sources());same(value["files"],lock())
    same(value["all_matched"],True);same(value["training_eligibility"],"DO_NOT_TRAIN_WITHOUT_REVIEW")
    sid=check_ready(value["ready"])
    if type(value["requests"]) is not list or len(value["requests"])!=42:
        raise ValueError("complete live request inventory required")
    index=0
    for episode in report["episodes"]:
        if episode["origin"]!="model":continue
        for turn_id,turn in enumerate(episode["turns"]):
            item=value["requests"][index]
            if type(item) is not dict or set(item)!={"episode","turn","request","response","proposal_hex","legacy_match"}:
                raise ValueError("exact live request schema required")
            same(item["episode"],episode["id"]);same(item["turn"],turn_id)
            req=request(sid,index,turn["prompt"]);same(item["request"],req)
            raw=check_output(item["response"],req,oracle)
            same(item["proposal_hex"],raw.hex());same(item["proposal_hex"],turn["proposal_hex"])
            generated=item["response"]["generated"]
            for key in ("status","text","input_ids","generated_ids","ended_with_eos"):
                same(generated[key],turn["generated"][key])
            same(item["legacy_match"],True);index+=1
    same(value["closed"],closed(request(sid,42)))
    # Freeze exact expected capture bytes and proof metadata before effects too.
    # Never reopen the mutable submitted report to identify what was replayed.
    bundle=[]
    for (name,capture),episode in zip(captures,report["episodes"]):
        expected=encode(capture)+b"\n"
        same(digest(expected),episode["capture_sha256"])
        bundle.append((name,capture,expected,load(LEGACY/name/"result.json")))
    return value,bundle,digest(raw_report)


def replay(path,oracle,output):
    value,bundle,report_sha=run_report(path,oracle)
    # All new decoded proposal bytes were checked equal to these frozen replay
    # inputs above. No authority/effects until the complete new run is validated.
    from research.progress_supervisor_v1.__main__ import execute
    output.mkdir(parents=True,exist_ok=False)
    results=[]
    for name,capture,expected,original_result in bundle:
        results.append(execute(output/name,capture=capture))
        same((output/name/"capture.json").read_bytes(),expected)
        new=load(output/name/"result.json")
        for key in ("final","captured_wire_proof","captured_path_proof","captured_rows_proof"):
            same(new[key],original_result[key])
    write(output/"replay.json",dict(format=FORMAT,report_sha256=report_sha,episodes=len(results),
                                   new_proposals_checked=42,results=results,inference_performed=False,pcs_authority=False))
