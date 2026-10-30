import fcntl
import json
import os
from pathlib import Path

import pytest

from research.llm_firewall_v1.broker import parse
from research.llm_firewall_v1.monitor import digest,F_GET_SEALS,REQUIRED_SEALS
from .runtime import MODELS,PINS,LocalModel,download,extract,resource,sealed_snapshot
from .experiment import FORMAT,load,protocol,replay
from .preservation import check


def test_known_official_weight_revisions_are_fixed_and_fully_sized():
    assert len(MODELS)==2 and PINS['cpu_threads']==2 and PINS['max_tokens']==256
    assert [resource(m)['size'] for m in MODELS]==[639446688,1834426016]
    assert resource(MODELS[0])['sha256']=='9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031'
    assert resource(MODELS[1])['sha256']=='061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a'
    for m in MODELS:assert resource(m)['revision'] in resource(m)['url']


def test_verified_snapshot_is_sealed_and_does_not_reopen_mutable_original(tmp_path):
    # Synthetic byte-level negative/TOCTOU control, not claimed model inference.
    p=tmp_path/'synthetic';b=b'synthetic snapshot bytes';p.write_bytes(b)
    fd=sealed_snapshot(p,size=len(b),sha256=digest(b))
    try:
        p.write_bytes(b'caller replaced mutable original')
        assert os.pread(fd,len(b),0)==b
        assert fcntl.fcntl(fd,F_GET_SEALS)&REQUIRED_SEALS==REQUIRED_SEALS
        with pytest.raises(PermissionError):os.write(fd,b'wrong')
        with pytest.raises(PermissionError):os.ftruncate(fd,0)
    finally:os.close(fd)


@pytest.mark.parametrize('data',[b'short',b'oversized'*20,b'x'*20])
def test_changed_truncated_or_oversized_weights_cannot_get_a_snapshot(tmp_path,data):
    p=tmp_path/'wrong';p.write_bytes(data)
    with pytest.raises(ValueError):sealed_snapshot(p,size=20,sha256=digest(b'correct snapshot!!!!'))


def test_existing_wrong_download_refuses_instead_of_overwriting_evidence(tmp_path):
    p=tmp_path/PINS['artifacts'][0]['name'];p.write_bytes(b'wrong historical bytes')
    with pytest.raises(ValueError):download(tmp_path)
    assert p.read_bytes()==b'wrong historical bytes'


def test_no_caller_chosen_model_or_engine_interface(tmp_path):
    with pytest.raises(ValueError):LocalModel(tmp_path,'caller/fake',tmp_path/'out')


@pytest.mark.parametrize('d',[
    {'model':'unrelated'},
    {'model':MODELS[0],'system_fingerprint':'wrong'},
    {'model':MODELS[0],'system_fingerprint':'b11827-970b51ce7','choices':[{'finish_reason':'length'}]},
    {'model':MODELS[0],'system_fingerprint':'b11827-970b51ce7','choices':[{'finish_reason':'stop','message':{'content':'{}','tool_calls':[{}]}}]},
])
def test_synthetic_negative_completion_metadata_does_not_become_inference_evidence(d):
    with pytest.raises(ValueError):extract(json.dumps(d).encode(),MODELS[0])


def test_capture_refuses_changed_bytes_and_rehashed_traversal(tmp_path):
    p=tmp_path/'c.json'
    d=dict(format=FORMAT,files={'ok.json':'original'},sha256={'ok.json':digest(b'different')},
           no_weights_embedded=True,provider_authentication=False)
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError):load(p)
    d['files']={'../escape':'original'};d['sha256']={'../escape':digest(b'original')};p.write_text(json.dumps(d))
    with pytest.raises(ValueError):load(p)


def test_protocol_keeps_safety_and_utility_separate_without_hiding_small_model_failures():
    p=protocol();assert len(p['cases'])==20 and p['max_agent_turns']==4
    assert sum(not c['policy_aware'] for c in p['cases'])==4
    assert p['qualification']['task_success_is_measured_not_required']
    assert not p['hosted_inference'] and not p['independent_heldout_benchmark']


def test_predecessor_sources_and_modes_are_unchanged():
    r=check();assert r['passed'] and r['previous_files_preserved']==6382


@pytest.mark.parametrize('model',MODELS)
def test_actual_downloaded_weight_cpu_inference(model,tmp_path):
    folder=os.environ.get('PCS_LOCAL_WEIGHTS_DIR')
    if not folder:
        if os.environ.get('PCS_REQUIRE_LOCAL_WEIGHTS')=='1':pytest.fail('Actual local GGUF weights required')
        pytest.skip('Set PCS_LOCAL_WEIGHTS_DIR to downloaded pinned weights')
    base=Path(os.environ.get('PCS_LOCAL_INFERENCE_EVIDENCE',str(tmp_path)))
    with LocalModel(Path(folder),model,base/resource(model)['name']) as m:
        raw,p=m.complete(model,[{'role':'user','content':'Return exactly this JSON object and nothing else: {"tool":"read_public","args":{}}'}])
        assert parse(raw).action==0
        assert p['weight_sha256']==resource(model)['sha256'] and not p['remote_model_api']
        assert m.binding['seals']==15 and m.binding['weight_mappings'] and m.binding['local_cpu']


def test_actual_local_weight_capture_reexecutes_tools_and_fresh_kernel_histories(tmp_path):
    p=Path(__file__).parent/'evidence/local-v1.json'
    if not p.exists():
        if os.environ.get('PCS_REQUIRE_LOCAL_CAPTURE')=='1':pytest.fail('Actual local inference capture required')
        pytest.skip('Local campaign capture not yet supplied')
    out=Path(os.environ.get('PCS_LOCAL_REPLAY_EVIDENCE',str(tmp_path/'replay')))
    r=replay(p,out)
    assert r['replayed'] and r['cases']==40 and r['agent_tasks']==6 and r['kernel_checked_histories']==46
    assert r['guarded_violations']==0 and not r['weights_loaded_in_this_replay']
