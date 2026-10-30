"""Pinned fetch, semantic audit, actual-weight repeat, and checked SQL replay."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from research.progress_supervisor_v1.evidence import write
from research.real_model_safety_v1.audit import same
from .artifacts import LEGACY,EXPERIMENT_SHA,fetch,snapshot,verify
from .oracle import Oracle
from .protocol import FORMAT,sources
from .audit import legacy,reference,run_report,replay
from .session import Session


def repeat(weights,dependencies,output):
    output.mkdir(parents=True,exist_ok=False)
    before=sources()
    files=snapshot(weights,output/"snapshot")
    oracle=Oracle(output/"snapshot",profile="full")
    old,_=reference(oracle)
    requests=[]
    with (output/"stderr.log").open("xb") as log, Session(output/"snapshot",dependencies,log,oracle) as session:
        for episode in old["episodes"]:
            if episode["origin"]!="model":continue
            for i,turn in enumerate(episode["turns"]):
                req,response,raw=session.generate(turn["prompt"])
                g=response["generated"]
                match=all(g[k]==turn["generated"][k] for k in ("status","text","input_ids","generated_ids","ended_with_eos"))
                requests.append(dict(episode=episode["id"],turn=i,request=req,response=response,
                                     proposal_hex=raw.hex(),legacy_match=match))
                # Preserve each response before any later comparison can fail.
                write(output/f"response-{len(requests)-1:03d}.json",requests[-1])
            print(episode["id"],"checked",flush=True)
        final=session.close()
        verify(output/"snapshot");same(sources(),before)
        value=dict(format=FORMAT,reference_sha256=EXPERIMENT_SHA,sources=before,ready=session.ready,closed=final,
                   requests=requests,files=files,all_matched=all(r["legacy_match"] for r in requests),
                   training_eligibility="DO_NOT_TRAIN_WITHOUT_REVIEW")
        write(output/"run.json",value)
    run_report(output/"run.json",oracle)
    print("42 exact token/text/byte matches; clean worker shutdown",flush=True)


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    f=sub.add_parser("fetch");f.add_argument("output",type=Path);f.add_argument("--full",action="store_true")
    r=sub.add_parser("repeat");r.add_argument("weights",type=Path);r.add_argument("dependencies",type=Path);r.add_argument("output",type=Path)
    a=sub.add_parser("audit");a.add_argument("tokenizer",type=Path);a.add_argument("--legacy",type=Path,default=LEGACY);a.add_argument("--run",type=Path);a.add_argument("--replay",type=Path)
    args=parser.parse_args()
    if args.command=="fetch":fetch(args.output,"full" if args.full else "tokenizer")
    elif args.command=="repeat":repeat(args.weights.resolve(),args.dependencies.resolve(),args.output.resolve())
    else:
        oracle=Oracle(args.tokenizer)
        if args.replay:
            if not args.run:parser.error("--replay requires --run")
            replay(args.run,oracle,args.replay)
        elif args.run:run_report(args.run,oracle)
        else:legacy(args.legacy,oracle)
        print("42 prompt/token/text/proposal bindings checked",flush=True)


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,EOFError,subprocess.SubprocessError) as error:
        print(json.dumps(dict(format=FORMAT,status="REFUSED_OR_UNAVAILABLE",reason=type(error).__name__,
                              completed=False,pcs_authority=False)),file=sys.stderr)
        raise SystemExit(20)
