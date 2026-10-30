"""Typed inference messages, separate from the unchanged Lean authority protocol."""
import os
from pathlib import Path
import re

from research.progress_supervisor_v1.certificate import encode
from .artifacts import digest,lock,LOCK_SHA
from .oracle import render

FORMAT="pcs-model-execution-v2"
VERSIONS={"torch":"2.7.1+cpu","transformers":"4.57.1","tokenizers":"0.22.2","safetensors":"0.8.0"}
OUTPUT={"status","text","input_ids","generated_ids","seconds","ended_with_eos"}
HERE=Path(__file__).resolve().parent


def sources():
    return {p.name:digest(p.read_bytes()) for p in sorted(HERE.glob("*.py")) if not p.name.startswith("test_")}


def session_id(value):
    if type(value) is not str or re.fullmatch("[0-9a-f]{32}",value) is None:
        raise ValueError("exact session identity required")


def sequence(value):
    if type(value) is not int or not 0<=value<=64:
        raise ValueError("exact bounded inference sequence required")


def request(session,seq,messages=None):
    session_id(session);sequence(seq)
    if messages is None:return dict(kind="close",session=session,sequence=seq)
    if seq==64:raise ValueError("inference request budget")
    render(messages)
    return dict(kind="generate",session=session,sequence=seq,messages=messages)


def check_request(value,session,seq):
    if type(value) is not dict:raise ValueError("typed inference request required")
    expected=request(session,seq,None if value.get("kind")=="close" else value.get("messages"))
    if value.keys()!=expected.keys():raise ValueError("exact inference request fields required")
    session_id(value["session"]);sequence(value["sequence"])
    if value!=expected:raise ValueError("session/sequence/request mismatch")
    return expected


def ready(session):
    session_id(session)
    return dict(format=FORMAT,kind="ready",session=session,files=lock(),lock_sha256=LOCK_SHA,
                versions=VERSIONS,sources=sources(),device="cpu",dtype="float32",threads=2)


def check_ready(value):
    from research.real_model_safety_v1.audit import same
    if type(value) is not dict:raise ValueError("typed ready frame required")
    same(value,ready(value.get("session")))
    return value["session"]


def output(req,generated):
    return dict(format=FORMAT,kind="output",session=req["session"],sequence=req["sequence"],
                request_sha256=digest(encode(req)),generated=generated)


def check_output(value,req,oracle):
    if type(value) is not dict or set(value)!={"format","kind","session","sequence","request_sha256","generated"}:
        raise ValueError("exact inference response fields required")
    sequence(value["sequence"])
    from research.real_model_safety_v1.audit import same
    generated=value["generated"]
    same({k:v for k,v in value.items() if k!="generated"},{k:v for k,v in output(req,generated).items() if k!="generated"})
    return oracle.validate(req["messages"],generated)


def closed(req):
    return dict(format=FORMAT,kind="closed",session=req["session"],sequence=req["sequence"],
                request_sha256=digest(encode(req)),files_rechecked=True,sources=sources())


def environment(dependencies):
    # Preserve inherited network proxy/CA/runtime guards, but remove the three
    # configured application credentials from the inference child's environment.
    # Same-user process access is NOT prevented by this hygiene measure.
    env={k:v for k,v in os.environ.items() if k not in
         {"PCS_LEAN_GITHUB_TOKEN","CLOUDFLARE_API_TOKEN","CLOUDFLARE_BUILDS_API_TOKEN",
          "PYTHONSTARTUP","PYTHONINSPECT"}}
    env.update(PYTHONPATH=str(dependencies),HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",
               TOKENIZERS_PARALLELISM="false",PYTHONDONTWRITEBYTECODE="1")
    return env
