"""Explicitly post-hoc, source-bound reproduction; never fresh primary scoring."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time

from research.scientific_intake_v1.intake import canonical
from .pipeline import run,replay,context


def experiment(source,output,*,role="POSTHOC_EXPOSED_SOURCE"):
    if role not in {"POSTHOC_EXPOSED_SOURCE","SECONDARY_PROSPECTIVE_NUMERICAL_ONLY"}:
        raise ValueError("unknown numerical experiment role")
    output=Path(output).absolute()
    if output.exists():raise ValueError("refuse experimental evidence overwrite")
    output.mkdir(parents=True,mode=0o700);started=time.monotonic()
    frozen=context()
    summary=run(source,output/"packet",check=True)
    replayed=replay(output/"packet")
    checks=json.loads((output/"packet/checks.json").read_text())
    result={"schema":"scientific-numerical-notation-experiment-v3","role":role,
            "utc":datetime.now(timezone.utc).isoformat(),"context":frozen,
            "context_sha256":hashlib.sha256(canonical(frozen)).hexdigest(),
            "summary":summary,"numerical":[r for r in checks if r.get("checker")=="nist-rounded-model-v3"],
            "independent_replay":replayed,"seconds":time.monotonic()-started,
            "primary_semantic_evaluation_changed":False,"scientific_meaning":"OPEN","authority":False,
            "generalization_scope":"None; exposed-source repair" if role=="POSTHOC_EXPOSED_SOURCE" else "One separately frozen source; numerical reconstruction only, not broad semantic generalization",
            "source_used_for_training":False,"external_expert_validation":False}
    if context()!=frozen:raise ValueError("runtime changed during numerical experiment")
    (output/"results.json").write_bytes(canonical(result)+b"\n")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--role",choices=["POSTHOC_EXPOSED_SOURCE","SECONDARY_PROSPECTIVE_NUMERICAL_ONLY"],default="POSTHOC_EXPOSED_SOURCE")
    a=p.parse_args();print(json.dumps(experiment(a.source,a.output,role=a.role),indent=2,sort_keys=True))


if __name__=="__main__":main()
