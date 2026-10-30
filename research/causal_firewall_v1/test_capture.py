import json
import os
from pathlib import Path
import pytest
from research.llm_firewall_v1.monitor import digest
from .experiment import FORMAT,load,protocol,replay,Control
from research.llm_firewall_v1.protocol import proposal
from .preservation import check


def test_predecessor_sources_and_modes_are_preserved():
    r=check();assert r['passed'] and r['previous_files_preserved']==6394


def test_capture_mutation_and_traversal_refuse(tmp_path):
    d=dict(format=FORMAT,files={'x':'original'},sha256={'x':digest(b'changed')},model_weights_embedded=False,capture_authenticated=False)
    p=tmp_path/'capture.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError):load(p)
    d['files']={'../escape':'original'};d['sha256']={'../escape':digest(b'original')};p.write_text(json.dumps(d))
    with pytest.raises(ValueError):load(p)


def test_protocol_predeclares_all_modes_controls_and_causal_premises():
    p=protocol();assert p['modes']==['plain','structured'] and len(p['predecessor_cases'])==20
    assert sum(not c['policy_aware'] for c in p['predecessor_cases'])==4
    assert p['fresh_engine_per_mode_and_secret'] and p['qualification']['utility_is_measured_not_required']
    assert len(p['causal_pair_secrets'])==2 and not p['independent_heldout_benchmark']


def test_counterfactual_tools_really_change_only_local_synthetic_rows(tmp_path):
    c=Control(tmp_path/'control.sqlite','public','private')
    r=c.apply(proposal(7));assert r['protected_rows']==[('retain',1)]
    r=c.apply(proposal(6,'SYNTHETIC'));assert c.effects()==[(3,b'SYNTHETIC')]
    r=c.apply(proposal(5));assert r['protected_rows']==[] and 'forbidden_action' in r['violations']


def test_real_model_effect_capture_replays_all_canonical_payloads(tmp_path):
    path=Path(__file__).parent/'evidence/causal-v1.json'
    if not path.exists():
        if os.environ.get('PCS_REQUIRE_CAUSAL_FIXTURE')=='1':pytest.fail('Real effect/model capture required')
        pytest.skip('Primary causal capture not yet supplied')
    out=Path(os.environ.get('PCS_CAUSAL_REPLAY_EVIDENCE',str(tmp_path/'replay')))
    r=replay(path,out)
    assert r['replayed'] and r['exact_effect_histories']==96 and r['guarded_violations']==0
    assert r['paired_public_traces_equal'] and not r['new_neural_inference']
