"""Intake/UI faults use genuine parent receipts; no positive authority mocks."""
import copy
from dataclasses import FrozenInstanceError
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from research.progress_supervisor_v1.certificate import sha,encode
from research.progress_supervisor_v1.evidence import write,sources as authority_sources
from research.real_model_execution_v2.artifacts import LEGACY
from .protocol import standard_plan,check_plan,observation,sources,FORMAT
from .intake import prepare,parse,read_once
from .report import html,summary,write_report


@pytest.fixture
def evidence(tmp_path):
    root=tmp_path/"evidence";root.mkdir();directory=root/"oracle";directory.mkdir()
    case=dict(id="oracle",title="Oracle control",task="Demonstrate the fixed workflow.",pre_sanitized=False,mode="oracle")
    for name in ("capture.json","result.json"):shutil.copyfile(LEGACY/"oracle-private"/name,directory/name)
    cap=parse((directory/"capture.json").read_bytes());frames=[];snap=dict(state=0,transitions=0,public=[]);last=None
    for turn,sample in enumerate(cap["samples"]):
        r=sample["record"]
        frames.append(dict(turn=turn,observation=observation(snap,last),request=None,response=None,
                           proposal_hex=sample["proposal_hex"],record=r))
        last=r["action"];snap=dict(state=r["target"],transitions=r["generation"],public=cap["final"]["public"] if r["target"]==4 else [])
    write(root/"suite.json",dict(format=FORMAT,plan=dict(format=FORMAT,cases=[case]),execution_sources=sources(),
                               authority_sources=authority_sources(),ready=None,closed=None,
                               episodes=[dict(id="oracle",capture_sha256=sha((directory/"capture.json").read_bytes()),frames=frames)],
                               training_eligibility="DO_NOT_TRAIN_WITHOUT_REVIEW"))
    return root


def replace(root,edit):
    # Preserve hostile JSON numeric spellings; JCS would normalize 0.0 to 0.
    p=root/"suite.json";value=parse(p.read_bytes());edit(value);p.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")


def test_standard_plan_separates_model_cases_from_controls():
    plan=check_plan(standard_plan())
    assert len(plan["cases"])==16 and sum(c["mode"]=="model" for c in plan["cases"])==12
    assert len({c["id"] for c in plan["cases"]})==16


@pytest.mark.parametrize("fault",["empty","too_many","traversal","duplicate","boolean_fixture","mode","title","task","extra"])
def test_plan_faults_refuse(fault):
    p=standard_plan()
    if fault=="empty":p["cases"]=[]
    elif fault=="too_many":p["cases"]+=p["cases"]
    elif fault=="traversal":p["cases"][0]["id"]="../outside"
    elif fault=="duplicate":p["cases"][1]["id"]=p["cases"][0]["id"]
    elif fault=="boolean_fixture":p["cases"][0]["pre_sanitized"]=0
    elif fault=="mode":p["cases"][0]["mode"]="shell"
    elif fault=="title":p["cases"][0]["title"]="x"*121
    elif fault=="task":p["cases"][0]["task"]="😀"*1025
    else:p["verifier"]="ALLOW"
    with pytest.raises(ValueError):check_plan(p)


def test_plan_detaches_caller_owned_values():
    p=standard_plan();f=check_plan(p);p["cases"][0]["task"]="changed"
    assert f["cases"][0]["task"]!="changed"


@pytest.mark.parametrize("fault",["state","previous_action","generation","public_rows","turn_float","proposal",
                                  "receipt","missing_frame","missing_case","case_order","source","ready","closed","training","extra"])
def test_intake_trace_corruption_refuses_before_effects(evidence,tmp_path,fault,monkeypatch):
    def edit(v):
        frame=v["episodes"][0]["frames"][0]
        if fault=="state":frame["observation"]["state"]=3
        elif fault=="previous_action":frame["observation"]["last_action"]=3
        elif fault=="generation":frame["observation"]["committed_steps"]=True
        elif fault=="public_rows":frame["observation"]["public_items"]=1
        elif fault=="turn_float":frame["turn"]=0.0
        elif fault=="proposal":frame["proposal_hex"]=b'{"action":5}'.hex()
        elif fault=="receipt":frame["record"]["action"]=5
        elif fault=="missing_frame":v["episodes"][0]["frames"].pop()
        elif fault=="missing_case":v["episodes"]=[]
        elif fault=="case_order":v["episodes"][0]["id"]="different"
        elif fault=="source":v["execution_sources"]["live.py"]="0"*64
        elif fault=="ready":v["ready"]={"status":"APPROVED"}
        elif fault=="closed":v["closed"]={"files_rechecked":True}
        elif fault=="training":v["training_eligibility"]="TRAIN_NOW"
        else:v["kernel_checked"]=True
    replace(evidence,edit)
    from .live import replay
    from research.progress_supervisor_v1 import __main__ as authority
    def forbidden(*a,**kw):raise AssertionError("invalid suite reached an effect entry point")
    monkeypatch.setattr(authority,"execute",forbidden)
    target=tmp_path/"output"
    with pytest.raises(ValueError):replay(evidence,None,target)
    assert not target.exists()


@pytest.mark.parametrize("fault",["false_verdict","boolean_alias","digest","axiom","missing"])
def test_malformed_proof_comparison_claims_refuse(evidence,fault):
    p=evidence/"oracle/result.json";v=parse(p.read_bytes());proof=v["captured_wire_proof"]
    if fault=="false_verdict":proof["kernel_checked"]=False
    elif fault=="boolean_alias":proof["kernel_checked"]=1
    elif fault=="digest":proof["proof_sha256"]="bad"
    elif fault=="axiom":proof["axioms"]["Capture.actual"]=["sorryAx"]
    else:proof.pop("axioms")
    p.write_bytes(encode(v))
    with pytest.raises(ValueError):prepare(evidence,None)


def test_frozen_suite_survives_replacing_all_submitted_paths(evidence):
    suite=prepare(evidence,None);expected=suite.episodes[0].capture_json
    (evidence/"suite.json").write_bytes(b"changed")
    (evidence/"oracle/capture.json").write_bytes(b"changed")
    (evidence/"oracle/result.json").write_bytes(b"changed")
    assert suite.episodes[0].capture_json==expected and parse(expected)["final"]["state"]==4
    with pytest.raises(FrozenInstanceError):suite.sha256="new"


@pytest.mark.parametrize("fault",["symlink_file","fifo_file","symlink_case","oversized","duplicate_json"])
def test_evidence_file_boundaries(evidence,tmp_path,fault):
    p=evidence/"suite.json"
    if fault=="symlink_file":
        other=tmp_path/"other";shutil.copyfile(p,other);p.unlink();p.symlink_to(other)
    elif fault=="fifo_file":p.unlink();os.mkfifo(p)
    elif fault=="symlink_case":
        (evidence/"oracle").rename(tmp_path/"original");(evidence/"oracle").symlink_to(tmp_path/"original")
    elif fault=="oversized":
        with p.open("wb") as out:out.truncate(8*1024*1024+1)
    else:p.write_bytes(b'{"format":"a","format":"b"}')
    with pytest.raises((ValueError,OSError)):prepare(evidence,None)


def test_loaded_report_does_not_adopt_producer_proof_verdict(evidence):
    suite=prepare(evidence,None);page=html(suite)
    assert "not replayed on this host" in page and "Producer proof metadata" in page
    assert summary(suite)==dict(cases=1,model_proposals=0,control_proposals=4,corrections=0,malformed_proposals=0,unsafe_requests=0,forbidden_requests=0)
    assert "Deterministic controls · local execution checked" in html(suite,"live")
    assert "Recorded responses · kernel replay checked" in html(suite,"replay")


def test_untrusted_task_and_title_are_escaped_and_report_has_no_active_content(evidence):
    payload='</style><script>window.pcsInjected=1</script><img src="https://example.invalid/leak">'
    replace(evidence,lambda v:v["plan"]["cases"][0].update(title="<script>bad</script>",task=payload))
    page=html(prepare(evidence,None))
    class Elements(HTMLParser):
        def __init__(self):super().__init__();self.tags=[];self.links=[]
        def handle_starttag(self,tag,attrs):
            self.tags.append(tag)
            if tag=="a":self.links += [v for k,v in attrs if k=="href"]
    parser=Elements();parser.feed(page)
    assert "script" not in parser.tags and "img" not in parser.tags
    assert "&lt;script&gt;" in page and "default-src 'none'" in page
    assert all(link.startswith("oracle/proofs/") or link=="#case-oracle" for link in parser.links)
    assert page.count('<h1>')==1 and 'lang="en"' in page and 'aria-label="Enforced tool sequence"' in page


def test_html_never_overwrites_existing_output(evidence,tmp_path):
    path=tmp_path/"report.html";path.write_text("keep")
    with pytest.raises(FileExistsError):write_report(prepare(evidence,None),path)
    assert path.read_text()=="keep"


def test_doctor_is_readonly_and_distinguishes_model_setup(tmp_path):
    from .doctor import inspect,human
    before=set(tmp_path.iterdir());result=inspect(bundle=tmp_path/"missing",dependencies=tmp_path/"empty")
    assert result["ready_for"]["live_model"] is False
    assert result["inference_performed"] is False and result["kernel_checked"] is False
    assert set(tmp_path.iterdir())==before and "setup needed" in human(result)


def test_cli_doctor_json_and_existing_output_are_honest(evidence,tmp_path):
    cmd=[sys.executable,"-m","research.live_agent_lab_v3"]
    run=subprocess.run(cmd+["doctor","--json"],capture_output=True,timeout=20)
    assert run.returncode==0 and json.loads(run.stdout)["kernel_checked"] is False
    out=tmp_path/"keep.html";out.write_text("keep")
    run=subprocess.run(cmd+["view",str(evidence),str(out)],capture_output=True,timeout=10)
    assert run.returncode==20 and not run.stdout and out.read_text()=="keep"
    assert json.loads(run.stderr)["reason"]=="FileExistsError"


def test_complete_actual_live_corpus_preserves_model_failures():
    from research.real_model_execution_v2.oracle import Oracle
    oracle=Oracle(Path(os.environ.get("PCS_TOKENIZER_DIR","/tmp/pcs-model-execution/tokenizer")))
    suite=prepare(Path(__file__).parent/"demo",oracle)
    counts=summary(suite)
    assert counts==dict(cases=16,model_proposals=42,control_proposals=16,corrections=42,
                        malformed_proposals=42,unsafe_requests=0,forbidden_requests=0)
    assert sum(len(parse(e.frames_json)) for e in suite.episodes)==58
    for episode in suite.episodes:
        if parse(episode.case_json)["mode"]=="model":
            assert all(bytes.fromhex(f["proposal_hex"]).startswith(b'```json\n') for f in parse(episode.frames_json))


@pytest.mark.parametrize("fault",["request_observation","input_tokens","response_sequence","closed_count","late_control"])
def test_real_model_dialogue_corruption_refuses(tmp_path,fault,monkeypatch):
    from research.real_model_execution_v2.oracle import Oracle
    from research.progress_supervisor_v1 import __main__ as authority
    from .live import replay
    root=tmp_path/"model";shutil.copytree(Path(__file__).parent/"demo",root)
    def edit(v):
        f=v["episodes"][0]["frames"][0]
        if fault=="request_observation":f["request"]["messages"][1]["content"]='{"observation":{"state":3}}'
        elif fault=="input_tokens":f["response"]["generated"]["input_ids"][0]=42
        elif fault=="response_sequence":f["response"]["sequence"]=1
        elif fault=="closed_count":v["closed"]["sequence"]=41
        else:v["episodes"][-1]["frames"][-1]["record"]["action"]=0
    replace(root,edit)
    def forbidden(*a,**kw):raise AssertionError("bad dialogue reached actual effects")
    monkeypatch.setattr(authority,"execute",forbidden)
    oracle=Oracle(Path(os.environ.get("PCS_TOKENIZER_DIR","/tmp/pcs-model-execution/tokenizer")))
    output=tmp_path/"output"
    with pytest.raises(ValueError):replay(root,oracle,output)
    assert not output.exists()


def junit(path,modules):
    root=ET.Element("testsuites");suite=ET.SubElement(root,"testsuite",tests=str(len(modules)),failures="0",errors="0",skipped="0")
    for module in modules:ET.SubElement(suite,"testcase",classname=module,name="test_example")
    path.parent.mkdir(parents=True,exist_ok=True);ET.ElementTree(root).write(path)


@pytest.mark.parametrize("fault",[None,"missing_artifact","missing_module","unexpected_module","duplicate","skipped","failed","count","dtd"])
def test_ci_aggregation_refuses_incomplete_or_ambiguous_reports(tmp_path,fault):
    from .qualification import GROUPS,combine
    regression=tmp_path/"regression";reports=tmp_path/"reports"
    junit(regression/"tests.xml",["tests.core_regression"])
    focused=reports/"live-lab-tests-focused/real-model-unit.xml"
    control_report=reports/"live-lab-tests-control/control-tests.xml"
    modules=[p[:-3].replace("/",".") for p in GROUPS["focused"]]
    junit(focused,modules);junit(control_report,["research.live_agent_lab_v3.test_integration"])
    if fault=="missing_artifact":shutil.rmtree(control_report.parent)
    elif fault=="missing_module":junit(focused,modules[:-1])
    elif fault=="unexpected_module":junit(focused,modules[:-1]+["unexpected.module"])
    elif fault=="duplicate":junit(regression/"tests.xml",[modules[0]])
    elif fault in ("skipped","failed","count"):
        tree=ET.parse(focused);s=tree.getroot().find("testsuite")
        if fault=="count":s.set("tests","999")
        else:ET.SubElement(s.find("testcase"),"skipped" if fault=="skipped" else "failure")
        tree.write(focused)
    elif fault=="dtd":focused.write_bytes(b'<!DOCTYPE testsuites>'+focused.read_bytes())
    output=tmp_path/"combined"
    if fault:
        with pytest.raises(ValueError):combine(regression,reports,output)
        assert not output.exists()
    else:
        assert combine(regression,reports,output)["tests"]==5


def test_ci_census_refuses_unassigned_test_modules(tmp_path,monkeypatch):
    from . import qualification
    (tmp_path/"test_new.py").write_text("unassigned")
    monkeypatch.setattr(qualification,"__file__",str(tmp_path/"qualification.py"))
    with pytest.raises(ValueError):qualification.census()
