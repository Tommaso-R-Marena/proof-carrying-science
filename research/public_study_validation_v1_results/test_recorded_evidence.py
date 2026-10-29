"""Negative replay tests against the COMPLETE ACTUAL model study, not fake verdicts.

Run explicitly with PCS_PUBLIC_STUDY_EVIDENCE pointing at the retained capture.
Missing evidence fails; this is not a silently skipped qualification job.
"""
from pathlib import Path
import json
import os
import shutil
import pytest
from research.public_study_validation_v1 import study as s
from research.public_study_validation_v1_results import receiving


@pytest.fixture
def evidence(tmp_path):
    source=Path(os.environ['PCS_PUBLIC_STUDY_EVIDENCE'])
    if not (source/'measurements.json').is_file():pytest.fail('actual complete study evidence required')
    dest=tmp_path/'capture';dest.mkdir()
    for path in source.rglob('*.json'):
        # Runtime/native build logs are not inputs of study receiving preflight.
        if 'native-authority' in path.relative_to(source).parts:continue
        target=dest/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    return dest,tmp_path/'refused-receiver'


def update(path,fn):
    value=json.loads(path.read_bytes());fn(value);path.write_text(json.dumps(value))


@pytest.mark.parametrize('attack',[
    'registered_plan','source_hash','incomplete_census','duplicate_census',
    'proposal_bytes','missing_proposal','symlink_proposal','request_bytes',
    'response_bytes','weight_claim','runtime_claim','remote_api_claim',
    'fake_admitted_action','fake_final_effects','false_private_metric',
    'capture_proposal','traversal_path','ambiguous_registration',
])
def test_corruption_refused_before_receiving_effects(evidence,attack):
    root,out=evidence
    reg=root/'registration.json';rows=root/'measurements.json'
    if attack=='registered_plan':update(reg,lambda v:v['plan'].__setitem__('seed',43))
    elif attack=='source_hash':update(reg,lambda v:v['sources'].__setitem__('study',{}))
    elif attack=='incomplete_census':update(rows,lambda v:v.pop())
    elif attack=='duplicate_census':update(rows,lambda v:v.__setitem__(1,v[0]))
    elif attack=='proposal_bytes':(root/'proposal-000.json').write_bytes(b'{"action":2}')
    elif attack=='missing_proposal':(root/'proposal-000.json').unlink()
    elif attack=='symlink_proposal':
        path=root/'proposal-000.json';raw=path.read_bytes();path.unlink()
        target=root/'outside.json';target.write_bytes(raw);path.symlink_to(target)
    elif attack=='request_bytes':(root/'model-0/call-000/request.json').write_text('{}')
    elif attack=='response_bytes':(root/'model-0/call-000/response.json').write_text('{}')
    elif attack=='weight_claim':update(rows,lambda v:v[0]['provenance'].__setitem__('weight_sha256','0'*64))
    elif attack=='runtime_claim':update(rows,lambda v:v[0]['provenance'].__setitem__('runtime_commit','0'*40))
    elif attack=='remote_api_claim':update(rows,lambda v:v[0]['provenance'].__setitem__('remote_model_api',True))
    elif attack=='fake_admitted_action':update(rows,lambda v:v[0].__setitem__('guarded_action',3))
    elif attack=='fake_final_effects':update(rows,lambda v:v[0]['guarded_final'].__setitem__('state',5))
    elif attack=='false_private_metric':update(rows,lambda v:v[0].__setitem__('guarded_private_publication',True))
    elif attack=='capture_proposal':update(root/'guarded-000/capture.json',lambda v:v['samples'][2].__setitem__('proposal_hex',b'{"action":2}'.hex()))
    elif attack=='traversal_path':update(rows,lambda v:v[0].__setitem__('proposal_path','../proposal-000.json'))
    elif attack=='ambiguous_registration':
        raw=reg.read_text();reg.write_text('{"plan":{},'+raw[1:])
    with pytest.raises((ValueError,OSError,KeyError)):
        receiving.replay(root,out)
    assert not out.exists(), 'invalid study must be refused before receiving output/effects'


@pytest.mark.parametrize('header',['registration.json','measurements.json'])
def test_header_rewrite_during_preflight_is_refused_before_effects(evidence,monkeypatch,header):
    root,out=evidence
    original_read=s.read;changed=False
    def racing_read(path,limit=4*1024*1024):
        nonlocal changed
        raw=original_read(path,limit)
        if Path(path)==root/header and not changed:
            changed=True
            # Simulate a writer AFTER read returns its immutable original bytes.
            # No authority/verifier/model verdict is mocked or substituted.
            Path(path).write_bytes(b'{}')
        return raw
    monkeypatch.setattr(s,'read',racing_read)
    with pytest.raises(ValueError,match='input changed during complete preflight'):
        receiving.replay(root,out)
    assert changed and not out.exists()


def test_valid_study_freezes_exact_header_and_all_capture_bytes(evidence):
    root,_=evidence
    frozen=receiving.freeze(root)
    hashes=dict(frozen.input_sha256)
    assert hashes['registration.json']==receiving.p.sha(frozen.registration)
    assert hashes['measurements.json']==receiving.p.sha(frozen.measurements)
    assert len(frozen.captures)==72 and len(hashes)==290
    assert all(type(raw) is bytes for raw in frozen.captures)
