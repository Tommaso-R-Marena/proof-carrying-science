"""Live proposals from actual broker observations, followed by real checked SQL."""
from contextlib import ExitStack,nullcontext

from research.progress_supervisor_v1.broker import Broker
from research.progress_supervisor_v1.certificate import sha
from research.progress_supervisor_v1.evidence import publish,write,EXTERNAL_ORIGIN,sources as authority_sources
from research.real_model_execution_v2.artifacts import verify
from research.real_model_execution_v2.oracle import Oracle
from research.real_model_execution_v2.session import Session
from research.real_model_safety_v1.audit import same
from .protocol import FORMAT,check_plan,sources,observation,messages,control,ACTIONS,STAGES
from .intake import prepare,parse


def run(bundle,dependencies,output,plan,progress=print):
    plan=check_plan(plan);before=sources();authority_before=authority_sources()
    output.mkdir(parents=True,exist_ok=False)
    write(output/"plan.json",plan)  # Freeze tasks before inference and effects.
    first_case=plan["cases"][0];(output/first_case["id"]).mkdir()
    model_needed=any(c["mode"]=="model" for c in plan["cases"])
    if model_needed:
        if bundle is None or dependencies is None:raise ValueError("Live model cases require a prepared bundle and dependency directory")
        verify(bundle);oracle=Oracle(bundle,profile="full")
    else:oracle=None
    with ExitStack() as stack:
        # Qualify the native authority before starting model computation, avoiding
        # CPU contention during its unchanged fresh kernel-check deadline.
        first=stack.enter_context(Broker(output/first_case["id"]/"effects.sqlite",output/"authority",
                                         pre_sanitized=first_case["pre_sanitized"]))
        log=stack.enter_context((output/"model-stderr.log").open("xb"))
        session=stack.enter_context(Session(bundle,dependencies,log,oracle)) if model_needed else None
        episodes=[]
        for index,case in enumerate(plan["cases"]):
            directory=output/case["id"]
            if index:directory.mkdir()
            context=nullcontext(first) if not index else Broker(directory/"effects.sqlite",output/"authority",pre_sanitized=case["pre_sanitized"])
            with context as broker:
                samples=[];frames=[];last=None
                for turn in range(4):
                    snap=broker.snapshot()
                    if snap["state"]==4:break
                    observed=observation(snap,last)
                    if case["mode"]=="model":req,response,raw=session.generate(messages(case,observed))
                    else:req,response,raw=None,None,control(case["mode"],snap["state"])
                    frame=dict(turn=turn,observation=observed,request=req,response=response,proposal_hex=raw.hex())
                    write(directory/f"proposal-{turn}.json",frame)
                    rid=f"turn-{turn:04d}";record=broker.step(raw,rid)
                    frame["record"]=record;frames.append(frame);last=record["action"]
                    samples.append(dict(request_id=rid,proposal_hex=raw.hex(),record=record))
                    proposed=ACTIONS.get(record["proposal"],"Invalid or unsupported proposal")
                    progress(f"{case['id']} · {turn+1}: model asked for {proposed}; PCS executed {ACTIONS[last]}; {STAGES[record['target']]}")
                publish(directory,broker,samples,authority_before,pre_sanitized=case["pre_sanitized"],replayed=False,data_origin=EXTERNAL_ORIGIN)
            episodes.append(dict(id=case["id"],capture_sha256=sha((directory/"capture.json").read_bytes()),frames=frames))
        final=session.close() if session else None
        if model_needed:verify(bundle)
        same(sources(),before);same(authority_sources(),authority_before)
        value=dict(format=FORMAT,plan=plan,execution_sources=before,authority_sources=authority_before,
                   ready=session.ready if session else None,closed=final,episodes=episodes,
                   training_eligibility="DO_NOT_TRAIN_WITHOUT_REVIEW")
        write(output/"suite.json",value)
    return prepare(output,oracle)


def replay(root,oracle,output):
    frozen=prepare(root,oracle)  # Entire suite before creating outputs/effects.
    from research.progress_supervisor_v1.__main__ import execute
    output.mkdir(parents=True,exist_ok=False)
    for episode in frozen.episodes:
        case=parse(episode.case_json);target=output/case["id"]
        execute(target,capture=parse(episode.capture_json))
        same((target/"capture.json").read_bytes(),episode.capture_json)
        expected=parse(episode.expected_proofs_json);actual=parse((target/"result.json").read_bytes())
        same({k:actual[k] for k in expected},expected)
    # Original dialogue is copied as data only; no fresh inference is claimed.
    (output/"suite.json").write_bytes(frozen.raw_json)
    write(output/"replay.json",dict(format=FORMAT,suite_sha256=frozen.sha256,episodes=len(frozen.episodes),
                                    inference_performed=False,pcs_authority=False))
    return frozen
