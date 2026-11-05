"""Real tokenizer and IO faults. Synthetic protocol fixtures grant no authority."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from research.real_model_safety_v1.audit import load
from . import artifacts
from .artifacts import LEGACY,lock,snapshot,verify
from .audit import legacy
from .channel import Channel
from .oracle import Oracle,render,EOS
from .protocol import request,check_request,ready,check_ready,output,check_output,environment


@pytest.fixture(scope="session")
def tokenizer_dir():
    return Path(os.environ.get("PCS_TOKENIZER_DIR","/tmp/pcs-model-execution/tokenizer"))


@pytest.fixture(scope="session")
def oracle(tokenizer_dir):
    return Oracle(tokenizer_dir)


@pytest.fixture
def generation():
    return copy.deepcopy(load(LEGACY/"experiment.json")["episodes"][0]["turns"][0])


def test_original_42_outputs_have_correct_independent_semantics(oracle):
    _,captures=legacy(LEGACY,oracle)
    assert len(captures)==16


@pytest.mark.parametrize("attack",["output_token","input_token","eos","text","float_id","bool_id",
                                   "unknown_token","control_token","early_eos","early_stop",
                                   "nan","negative_time","bool_time","extra","empty","too_long"])
def test_generated_evidence_faults_refuse(oracle,generation,attack):
    g=generation["generated"]
    if attack=="output_token":g["generated_ids"][0]=42
    elif attack=="input_token":g["input_ids"][0]=42
    elif attack=="eos":g["ended_with_eos"]=False
    elif attack=="text":g["text"]='{"action":5}'
    elif attack=="float_id":g["generated_ids"][0]=float(g["generated_ids"][0])
    elif attack=="bool_id":g["input_ids"][0]=True
    elif attack=="unknown_token":g["generated_ids"][0]=151935
    elif attack=="control_token":g["generated_ids"][0]=151644
    elif attack=="early_eos":g["generated_ids"][0]=EOS
    elif attack=="early_stop":g["generated_ids"].pop();g["ended_with_eos"]=False
    elif attack=="nan":g["seconds"]=float("nan")
    elif attack=="negative_time":g["seconds"]=-1
    elif attack=="bool_time":g["seconds"]=True
    elif attack=="extra":g["verifier"]="ALLOW"
    elif attack=="empty":g["generated_ids"]=[]
    elif attack=="too_long":g["generated_ids"]=[1]*33
    with pytest.raises(ValueError):oracle.validate(generation["prompt"],g)


@pytest.mark.parametrize("attack",["sequence","bool_sequence","session","digest","extra","version"])
def test_response_correlation_faults_refuse(oracle,generation,attack):
    req=request("0"*32,0,generation["prompt"]);value=output(req,generation["generated"])
    if attack=="sequence":value["sequence"]=1
    elif attack=="bool_sequence":value["sequence"]=False
    elif attack=="session":value["session"]="1"*32
    elif attack=="digest":value["request_sha256"]="0"*64
    elif attack=="extra":value["verifier"]="ALLOW"
    elif attack=="version":value["format"]="v1"
    with pytest.raises(ValueError):check_output(value,req,oracle)


def test_checked_response_returns_exact_original_proposal_bytes(oracle,generation):
    req=request("0"*32,0,generation["prompt"])
    assert check_output(output(req,generation["generated"]),req,oracle).hex()==generation["proposal_hex"]


@pytest.mark.parametrize("attack",["weights","config","source","versions","extra","boolean_thread"])
def test_ready_metadata_faults_refuse(attack):
    r=ready("0"*32)
    if attack in ("weights","config"):r["files"]["model.safetensors" if attack=="weights" else "config.json"]["sha256"]="0"*64
    elif attack=="source":r["sources"]["worker.py"]="0"*64
    elif attack=="versions":r["versions"]=dict(r["versions"],torch="fake")
    elif attack=="extra":r["positive_verdict"]=True
    elif attack=="boolean_thread":r["threads"]=True
    with pytest.raises(ValueError):check_ready(r)


@pytest.mark.parametrize("value",[{},[],{"stop":1},{"kind":"generate","session":"0"*32,"sequence":False,"messages":[]},
                                 {"kind":"close","session":"0"*32,"sequence":1},
                                 {"kind":"close","session":"0"*32,"sequence":0,"verifier":"ALLOW"}])
def test_invalid_and_replayed_requests_refuse(value):
    with pytest.raises(ValueError):check_request(value,"0"*32,0)


@pytest.mark.parametrize("raw",[b'{"a":1,"a":2}\n',b'{"a":NaN}\n',b'\xff\n',b'x'*129+b'\n',b'['*1500+b'0'+b']'*1500+b'\n'])
def test_channel_rejects_ambiguous_oversized_or_invalid_json(raw):
    r,w=os.pipe()
    try:
        os.write(w,raw);os.close(w);w=None
        with pytest.raises(ValueError):Channel(r,limit=128).read()
    finally:
        os.close(r)
        if w is not None:os.close(w)


def test_channel_coalesced_frames_eof_and_trailing_output():
    r,w=os.pipe()
    try:
        os.write(w,b'{"a":1}\n{"b":2}\n');os.close(w)
        c=Channel(r);assert c.read()=={"a":1}
        with pytest.raises(ValueError):c.eof()
        assert c.read()=={"b":2};c.eof()
    finally:os.close(r)


def test_channel_partial_eof_and_read_and_write_deadlines():
    r,w=os.pipe()
    try:
        os.write(w,b'{"a":');c=Channel(r,timeout=.03)
        with pytest.raises(TimeoutError):c.read()
        os.close(w);w=None
        with pytest.raises(EOFError):c.read()
    finally:
        os.close(r)
        if w is not None:os.close(w)
    r,w=os.pipe()
    try:
        c=Channel(w,timeout=.03)
        with pytest.raises(BlockingIOError):
            while True:os.write(w,b'x'*4096)
        with pytest.raises(TimeoutError):c.write({"a":1})
    finally:os.close(r);os.close(w)


@pytest.mark.parametrize("value",[False,0,-1,float("nan"),float("inf"),301])
def test_channel_invalid_deadlines(value):
    with pytest.raises(ValueError):Channel(0,timeout=value)


@pytest.mark.parametrize("fault",["changed","missing","extra","symlink","directory","fifo"])
def test_exact_artifact_inventory_and_bytes(tokenizer_dir,tmp_path,fault):
    source=tmp_path/"source";shutil.copytree(tokenizer_dir,source)
    p=source/"tokenizer_config.json"
    if fault=="changed":p.write_bytes(b'x'*p.stat().st_size)
    elif fault=="missing":p.unlink()
    elif fault=="extra":(source/"unknown").write_bytes(b'')
    else:
        p.unlink()
        if fault=="symlink":p.symlink_to(tokenizer_dir/"tokenizer_config.json")
        elif fault=="directory":p.mkdir()
        else:os.mkfifo(p)
    with pytest.raises((ValueError,OSError)):verify(source,"tokenizer")


def test_snapshot_survives_original_path_substitution(tokenizer_dir,tmp_path,monkeypatch):
    source=tmp_path/"source";shutil.copytree(tokenizer_dir,source);destination=tmp_path/"copy"
    actual=artifacts.stream_file
    def copy_then_substitute(path,expected,target=None):
        result=actual(path,expected,target)
        if target is not None and path.name=="tokenizer.json":
            path.unlink();path.write_bytes(b"replaced original")
        return result
    monkeypatch.setattr(artifacts,"stream_file",copy_then_substitute)
    snapshot(source,destination,"tokenizer")
    assert (destination/"tokenizer.json").stat().st_size==lock("tokenizer")["tokenizer.json"]["bytes"]
    verify(destination,"tokenizer")
    with pytest.raises(ValueError):verify(source,"tokenizer")


def test_failed_snapshot_cleans_only_own_fresh_output(tokenizer_dir,tmp_path):
    source=tmp_path/"source";shutil.copytree(tokenizer_dir,source)
    (source/"tokenizer_config.json").write_bytes(b"bad")
    out=tmp_path/"out"
    with pytest.raises(ValueError):snapshot(source,out,"tokenizer")
    assert not out.exists() and source.exists()
    out.mkdir();(out/"keep").write_text("keep")
    with pytest.raises(FileExistsError):snapshot(tokenizer_dir,out,"tokenizer")
    assert (out/"keep").read_text()=="keep"


@pytest.mark.parametrize("attack",["generated_token","input_token","eos","config_digest"])
def test_parent_accepted_tamper_fixtures_now_refuse(oracle,attack,tmp_path):
    from research.real_model_safety_v1.audit import validate as parent_validate
    root=tmp_path/attack;shutil.copytree(LEGACY,root)
    report=load(root/"experiment.json");episode=report["episodes"][0]
    if attack=="generated_token":episode["turns"][0]["generated"]["generated_ids"][0]=42
    elif attack=="input_token":episode["turns"][0]["generated"]["input_ids"][0]=42
    elif attack=="eos":episode["turns"][0]["generated"]["ended_with_eos"]=False
    else:
        report["model"]["files"]["config.json"]["sha256"]="0"*64
        (root/"model.json").write_text(json.dumps(report["model"]))
    (root/"experiment.json").write_text(json.dumps(report))
    (root/episode["id"]/"episode.json").write_text(json.dumps(episode))
    parent_validate(root)  # Reproduce the actual parent metadata gap, not a mock.
    with pytest.raises(ValueError):legacy(root,oracle)


def test_inference_environment_omits_configured_app_credentials(monkeypatch,tmp_path):
    for key in ("PCS_LEAN_GITHUB_TOKEN","CLOUDFLARE_API_TOKEN","CLOUDFLARE_BUILDS_API_TOKEN"):
        monkeypatch.setenv(key,"synthetic sentinel")
    monkeypatch.setenv("HTTPS_PROXY","synthetic proxy");monkeypatch.setenv("SSL_CERT_FILE","synthetic CA")
    env=environment(tmp_path)
    assert all(k not in env for k in ("PCS_LEAN_GITHUB_TOKEN","CLOUDFLARE_API_TOKEN","CLOUDFLARE_BUILDS_API_TOKEN"))
    assert env["HTTPS_PROXY"]=="synthetic proxy" and env["SSL_CERT_FILE"]=="synthetic CA"


def test_actual_worker_refuses_incomplete_bundle_before_ready(tokenizer_dir):
    run=subprocess.run([sys.executable,"-m","research.real_model_execution_v2.worker",str(tokenizer_dir)],
                       capture_output=True,timeout=10)
    assert run.returncode!=0 and not run.stdout
    assert b"exact model directory inventory required" in run.stderr


def test_cli_missing_artifacts_returns_structured_refusal(tmp_path):
    run=subprocess.run([sys.executable,"-m","research.real_model_execution_v2","audit",str(tmp_path)],
                       capture_output=True,timeout=10)
    assert run.returncode==20 and not run.stdout
    value=json.loads(run.stderr)
    assert value["completed"] is False and value["pcs_authority"] is False


def test_frozen_transformers_unicode_differential_vectors(oracle):
    vectors=load(Path(__file__).parent/"observations/differential.json")
    assert len(vectors["cases"])==64
    for case in vectors["cases"]:
        assert oracle.inputs(case["messages"])==case["input_ids"]


@pytest.mark.parametrize("attack",["request_digest","sequence","tokens","text","closed","sources","manifest","all_matched"])
def test_new_report_tampering_refuses_before_effects(oracle,tmp_path,attack):
    from .audit import run_report
    value=load(Path(__file__).parent/"observations/run.json")
    if attack=="request_digest":value["requests"][0]["response"]["request_sha256"]="0"*64
    elif attack=="sequence":value["requests"][0]["response"]["sequence"]=False
    elif attack=="tokens":value["requests"][0]["response"]["generated"]["generated_ids"][0]=42
    elif attack=="text":value["requests"][0]["response"]["generated"]["text"]="forged"
    elif attack=="closed":value["closed"]["files_rechecked"]=False
    elif attack=="sources":value["sources"]["worker.py"]="0"*64
    elif attack=="manifest":value["files"]["config.json"]["bytes"]=726.0
    else:value["all_matched"]=False
    path=tmp_path/"report.json";path.write_text(json.dumps(value))
    with pytest.raises(ValueError):run_report(path,oracle)


def test_validated_report_hash_and_expected_bytes_survive_input_replacement(oracle,tmp_path):
    from .audit import run_report
    path=tmp_path/"report.json";path.write_bytes((Path(__file__).parent/"observations/run.json").read_bytes())
    _,bundle,sha=run_report(path,oracle)
    path.write_bytes(b"replaced after preflight")
    assert sha!=artifacts.digest(path.read_bytes()) and len(bundle)==16
    for name,_,expected,_ in bundle:
        assert expected==(LEGACY/name/"capture.json").read_bytes()


def test_eos_only_and_maximum_length_outputs_are_supported(oracle,generation):
    g=generation["generated"]
    for ids,ended in (([EOS],True),([16]*32,False)):
        g["generated_ids"]=ids;g["ended_with_eos"]=ended
        g["text"]=oracle.tokenizer.decode(ids,skip_special_tokens=True)
        assert oracle.validate(generation["prompt"],g)==g["text"].encode()
