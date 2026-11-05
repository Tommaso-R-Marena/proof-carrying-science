"""Typed proof inputs and retained real-model evidence; no affirmative mocks."""
import json,os
from pathlib import Path
import pytest
from .receiver import render_rows,freeze,rows_from_suite


def row():return dict(state=2,tokens=[4913,1311,788,18,92,151645],raw_hex=b'{"action":3}'.hex(),selected=2)


def test_safe_fixed_proof_template_binds_all_pair_fields():
    proof=render_rows([row()])
    assert proof.startswith(b'import Data\nimport PairGate\n') and b'.selected 2' in proof
    assert b'151645' in proof and b'GateCapture.actual' in proof and b'by decide' in proof
    assert b'native_decide' not in proof and b'sorry' not in proof


@pytest.mark.parametrize('fault',['extra','state_bool','state_negative','state_big','token_bool','token_negative','token_big','token_empty','token_count','hex_upper','hex_odd','hex_injection','raw_size','selected_bool','selected_big','empty','count'])
def test_untrusted_witness_shapes_refuse(fault):
    r=row();rows=[r]
    if fault=='extra':r['verifier']='ALLOW'
    elif fault=='state_bool':r['state']=False
    elif fault=='state_negative':r['state']=-1
    elif fault=='state_big':r['state']=65536
    elif fault=='token_bool':r['tokens']=[True]
    elif fault=='token_negative':r['tokens']=[-1]
    elif fault=='token_big':r['tokens']=[151936]
    elif fault=='token_empty':r['tokens']=[]
    elif fault=='token_count':r['tokens']=[0]*33
    elif fault=='hex_upper':r['raw_hex']='FF'
    elif fault=='hex_odd':r['raw_hex']='f'
    elif fault=='hex_injection':r['raw_hex']='end GateCapture\naxiom bad : False'
    elif fault=='raw_size':r['raw_hex']='00'*4097
    elif fault=='selected_bool':r['selected']=True
    elif fault=='selected_big':r['selected']=65536
    elif fault=='empty':rows=[]
    else:rows=[r]*65
    with pytest.raises(ValueError):render_rows(rows)


def test_negative_control_is_explicitly_invalid_not_selected():
    r=row();r['selected']=None
    assert b'[.invalid]' in render_rows([r]) and b'.selected' not in render_rows([r])


def test_real_model_pairs_are_frozen_before_path_mutation(tmp_path):
    from shutil import copytree
    root=tmp_path/'input';copytree(Path(__file__).parents[1]/'structured_action_lab_v4/demo/trie',root)
    frozen=freeze(root,Path(os.environ['PCS_TOKENIZER_DIR']));rows=rows_from_suite(frozen)
    assert len(rows)==42 and sum(r['selected']==r['tokens'][3]-15 for r in rows)==8
    (root/'suite.json').write_bytes(b'changed')
    for p in root.glob('*/capture.json'):p.write_bytes(b'changed')
    assert rows_from_suite(frozen)==rows
    assert len(render_rows(rows))>1000


def test_raw_profile_never_silently_migrates_to_new_gate():
    root=Path(__file__).parents[1]/'structured_action_lab_v4/demo/raw'
    with pytest.raises(ValueError):freeze(root,Path(os.environ['PCS_TOKENIZER_DIR']))


def test_post_intake_rejection_expectation_refuses_before_outputs_or_sql(monkeypatch,tmp_path):
    # Adversarial data after intake; no compiler/verifier verdict is replaced.
    from types import SimpleNamespace
    from . import receiver
    frame=dict(record=dict(source=2,action=None),response=dict(generated=dict(generated_ids=row()['tokens'])),proposal_hex=b'{"action":5}'.hex())
    frozen=SimpleNamespace(episodes=[SimpleNamespace(case_json=json.dumps(dict(mode='model')).encode(),frames_json=json.dumps([frame]).encode())])
    monkeypatch.setattr(receiver,'freeze',lambda *args:frozen)
    output=tmp_path/'never-created'
    with pytest.raises(ValueError,match='selected action before effects'):
        receiver.receive(tmp_path/'input',tmp_path/'tokenizer',output)
    assert not output.exists()
