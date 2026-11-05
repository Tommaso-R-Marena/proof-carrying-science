"""Complete immutable intake; loaded evidence is never a kernel verdict."""
from dataclasses import dataclass
import os
from pathlib import Path
import re

from pcs.jsonio import strict_json_loads
from research.progress_supervisor_v1.certificate import encode,sha
from research.progress_supervisor_v1.evidence import sources as authority_sources
from research.progress_supervisor_v1.intake import preflight
from research.real_model_execution_v2.artifacts import regular,lock
from .protocol import request,check_ready,check_output,closed
from research.real_model_safety_v1.audit import same
from .protocol import FORMAT,check_plan,sources,observation,messages,control


def read_once(path,limit=8*1024*1024):
    with regular(path) as stream:
        before=os.fstat(stream.fileno())
        if before.st_size>limit:raise ValueError("Evidence file exceeds its byte budget")
        raw=stream.read(limit+1)
        after=os.fstat(stream.fileno())
        if len(raw)>limit or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError("Evidence changed while reading")
    return raw


def parse(raw):
    return strict_json_loads(raw.decode("utf-8",errors="strict"))


@dataclass(frozen=True)
class Episode:
    case_json: bytes
    capture_json: bytes
    expected_proofs_json: bytes
    frames_json: bytes


@dataclass(frozen=True)
class Suite:
    raw_json: bytes
    sha256: str
    episodes: tuple[Episode,...]


def prepare(root,oracle):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError("Use a regular evidence directory")
    raw=read_once(root/"suite.json");value=parse(raw)
    fields={"format","profile","plan","execution_sources","authority_sources","ready","closed","episodes","training_eligibility"}
    if type(value) is not dict or set(value)!=fields:raise ValueError("Unsupported lab evidence schema")
    same(value["format"],FORMAT);plan=check_plan(value["plan"])
    same(value["execution_sources"],sources());same(value["authority_sources"],authority_sources())
    same(value["training_eligibility"],"DO_NOT_TRAIN_WITHOUT_REVIEW")
    mode=value["profile"]
    if mode not in ("raw","trie") or (oracle is not None and oracle.mode!=mode):raise ValueError("Exact decoder profile required")
    model_cases=any(c["mode"]=="model" for c in plan["cases"])
    sid=check_ready(value["ready"],mode) if model_cases else None
    if not model_cases:same(value["ready"],None)
    if type(value["episodes"]) is not list or len(value["episodes"])!=len(plan["cases"]):
        raise ValueError("Complete episode inventory required")
    seq=0;episodes=[]
    for case,item in zip(plan["cases"],value["episodes"]):
        if type(item) is not dict or set(item)!={"id","capture_sha256","frames"}:raise ValueError("Exact episode schema required")
        same(item["id"],case["id"])
        directory=root/case["id"]
        if directory.is_symlink():raise ValueError("Symlink evidence directories are unsupported")
        capture_raw=read_once(directory/"capture.json",1024*1024)
        same(sha(capture_raw),item["capture_sha256"])
        cap=parse(capture_raw);frozen=preflight(cap)
        same(cap["pre_sanitized"],case["pre_sanitized"])
        steps=3 if case["pre_sanitized"] else 4
        if len(frozen.samples)!=steps:raise ValueError("Exact completed path required")
        same(cap["final"]["state"],4);same(cap["final"]["transitions"],steps)
        frames=item["frames"]
        if type(frames) is not list or len(frames)!=len(frozen.samples):raise ValueError("Complete live feedback trace required")
        snap=dict(state=0,transitions=0,public=[]);last=None
        for turn,(sample,frame) in enumerate(zip(cap["samples"],frames)):
            if type(frame) is not dict or set(frame)!={"turn","observation","request","response","proposal_hex","record"}:
                raise ValueError("Exact live frame schema required")
            same(frame["turn"],turn);observed=observation(snap,last);same(frame["observation"],observed)
            same(frame["record"],sample["record"]);same(frame["proposal_hex"],sample["proposal_hex"])
            same(sample["request_id"],f"turn-{turn:04d}")
            if case["mode"]=="model":
                req=request(sid,seq,messages(case,observed));same(frame["request"],req)
                decoded=check_output(frame["response"],req,oracle)
                same(decoded.hex(),frame["proposal_hex"]);seq+=1
            else:
                same(frame["request"],None);same(frame["response"],None)
                same(frame["proposal_hex"],control(case["mode"],snap["state"]).hex())
            r=sample["record"];last=r["action"]
            snap=dict(state=r["target"],transitions=r["generation"],public=cap["final"]["public"] if r["target"]==4 else [])
        result=parse(read_once(directory/"result.json"))
        expected={k:result[k] for k in ("final","captured_wire_proof","captured_rows_proof","captured_path_proof")}
        same(expected["final"],cap["final"])
        for key,inventory,names in (("captured_wire_proof","axioms",{"Capture.actual"}),
                                    ("captured_rows_proof","axioms",{"CaptureRows.actual"}),
                                    ("captured_path_proof","axiom_closures",{"CapturedPath.path","CapturedPath.bounded","CapturedPath.completed"})):
            proof=expected[key]
            if type(proof) is not dict or set(proof)!={"kernel_checked","proof_sha256",inventory,"pcs_authority"}:
                raise ValueError("Exact proof comparison metadata required")
            same(proof["kernel_checked"],True);same(proof["pcs_authority"],False)
            if type(proof["proof_sha256"]) is not str or re.fullmatch("[0-9a-f]{64}",proof["proof_sha256"]) is None:
                raise ValueError("Proof source digest required")
            inv=proof[inventory]
            if type(inv) is not dict or set(inv)!=names:raise ValueError("Exact named proof inventory required")
            for dependencies in inv.values():
                if type(dependencies) is not list or len(dependencies)>2 or any(type(d) is not str or d not in ("propext","Quot.sound") for d in dependencies) or len(set(dependencies))!=len(dependencies):
                    raise ValueError("Unsupported proof assumption claim")
        # These are detached comparison claims, not adopted authority. Actual
        # receiving execution generates and checks all proofs independently.
        episodes.append(Episode(encode(case),capture_raw,encode(expected),encode(frames)))
    same(value["closed"],closed(request(sid,seq),mode) if model_cases else None)
    return Suite(raw,sha(raw),tuple(episodes))
