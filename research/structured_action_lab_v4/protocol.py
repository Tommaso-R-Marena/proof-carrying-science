"""Explicit new profile identity; never impersonates the frozen v2 worker."""
from pathlib import Path
from research.real_model_execution_v2 import protocol as base
from research.real_model_safety_v1.audit import same
from research.progress_supervisor_v1.certificate import sha
from research.live_agent_lab_v3.protocol import sources as lab_sources

from research.live_agent_lab_v3.protocol import check_plan,observation,messages,control,ACTIONS,STAGES

FORMAT="pcs-structured-actions-v4"
HERE=Path(__file__).resolve().parent
CORE=("codec.py","protocol.py","worker.py","session.py","experiment.py","intake.py","ActionCodec.lean")
request=base.request
check_request=base.check_request
environment=base.environment


def sources():
    return dict(implementation={n:sha((HERE/n).read_bytes()) for n in CORE},base_worker=base.sources(),live_lab=lab_sources())


def ready(sid,mode):
    if mode not in ("raw","trie"):raise ValueError("Explicit raw/trie profile required")
    value=base.ready(sid);value.update(format=FORMAT,profile=mode,sources=sources());return value


def check_ready(value,mode):
    if type(value) is not dict:raise ValueError("Typed ready frame required")
    same(value,ready(value.get("session"),mode));return value["session"]


def output(req,generated,mode):
    value=base.output(req,generated);value.update(format=FORMAT,profile=mode);return value


def check_output(value,req,oracle):
    if type(value) is not dict or set(value)!=set(output(req,None,oracle.mode)):raise ValueError("Exact response fields required")
    base.sequence(value["sequence"])
    same({k:v for k,v in value.items() if k!="generated"},{k:v for k,v in output(req,None,oracle.mode).items() if k!="generated"})
    return oracle.validate(req["messages"],value["generated"])


def closed(req,mode):
    value=base.closed(req);value.update(format=FORMAT,profile=mode,sources=sources());return value
