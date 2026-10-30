"""Repeat *inference* in a fresh process, separately from formal replay.

Run from the repository root. A mismatch is recorded and exits nonzero; no
replacement response is selected. No effects or authority calls are made.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from research.progress_supervisor_v1.certificate import sha
from research.progress_supervisor_v1.evidence import write
from research.real_model_safety_v1.audit import same, validate
from research.real_model_safety_v1.run import read_message


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("evidence",type=Path)
    parser.add_argument("weights",type=Path)
    parser.add_argument("dependencies",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report,_=validate(args.evidence)
    args.output.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONPATH=str(args.dependencies.resolve()),HF_HUB_OFFLINE="1",
             TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
    with (args.output/"stderr.log").open("xb") as log:
        process=subprocess.Popen([sys.executable,"-m","research.real_model_safety_v1.model_process",
                                  str(args.weights.resolve())],stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,stderr=log,bufsize=0,env=env)
        replies=[]
        try:
            ready=read_message(process)
            same(ready["files"],report["model"]["files"])
            same(ready["versions"],report["model"]["versions"])
            for episode in report["episodes"]:
                if episode["origin"]!="model":continue
                for i,turn in enumerate(episode["turns"]):
                    process.stdin.write(json.dumps({"messages":turn["prompt"]}).encode()+b"\n")
                    process.stdin.flush()
                    reply=read_message(process)
                    fields=("status","text","input_ids","generated_ids","ended_with_eos")
                    equal=all(type(reply[k]) is type(turn["generated"][k]) and reply[k]==turn["generated"][k] for k in fields)
                    replies.append(dict(episode=episode["id"],turn=i,exact_match=equal,generated=reply))
                print(episode["id"],"repeated",flush=True)
            process.stdin.write(b'{"stop":true}\n');process.stdin.flush()
            closed=read_message(process)
            same(closed,dict(status="CLOSED",files_rechecked=True))
            process.stdin.close();process.wait(timeout=30)
            if process.returncode:raise ValueError("inference process failed")
            result=dict(format="pcs-real-weight-inference-repeat-v1",process="fresh CPU process, same host",
                        source_sha256=sha(Path(__file__).read_bytes()),
                        experiment_sha256=sha((args.evidence/"experiment.json").read_bytes()),
                        ready=ready,closed=closed,comparisons=replies,
                        matches=sum(r["exact_match"] for r in replies),requests=len(replies),
                        authority_replayed=False,independent_external_validation=False)
            write(args.output/"repeat.json",result)
            print(result["matches"],"/",result["requests"],"exact token/text matches",flush=True)
            return int(result["matches"]!=result["requests"])
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)


if __name__=="__main__":
    raise SystemExit(main())
