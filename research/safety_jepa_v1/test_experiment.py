"""Actual executor/data boundaries; no affirmative verifier mocks."""
from pathlib import Path
import tempfile
import pytest
from .experiment import collect,rollout,independent_leaks,symbolic_risk,safe_next,run
from .scenarios import scenarios,safe_workflow


def test_training_firewall_without_executing_tools():
    with pytest.raises(ValueError,match='training-only'):collect([next(r for r in scenarios() if r['split']=='test')])


def test_actual_training_traces_bound_and_no_fake_safe_risk_labels():
    rows=[r for r in scenarios() if r['split']=='train'][:1]
    corpus=collect(rows)
    assert corpus['transitions'] and all(t['split']=='train' for t in corpus['transitions'])
    assert any(t['unsafe'] for t in corpus['transitions'])
    assert all(t['source_sha256'] and len(t['source_sha256'])==64 for t in corpus['transitions'])
    assert corpus['traces'][0]['success']


def test_actual_confined_marker_leaks_are_independent_of_guard_mode():
    row=next(r for r in scenarios() if r['goal']=='sensitive')
    seq=['inspect','read_sensitive','draft','publish']
    assert rollout(row,seq,guarded=False)['actual_leak_sinks']==['output.txt']
    assert not rollout(row,seq,guarded=True)['actual_leak_sinks']


def test_symbolic_forecast_and_legitimate_lookalike():
    row=next(r for r in scenarios() if r['goal']=='sensitive')
    observed=rollout(row,['inspect'],guarded=True)['rows'][0]['next_obs']
    assert symbolic_risk(observed,['read_sensitive','draft','publish'])
    assert not symbolic_risk(observed,safe_workflow('sensitive',inspect=False))
    assert safe_next(observed)=='read_sensitive'


def test_run_rejects_invalid_resource_configuration_before_files(tmp_path):
    with pytest.raises(ValueError,match='invalid seeds'):run(tmp_path/'bad',seeds=(17,17))
    assert not (tmp_path/'bad').exists()


def test_predictor_unavailable_retains_actual_guard_and_safe_fallback():
    from .experiment import evaluate
    record=[r for r in scenarios() if r['split']=='validation'][:1]
    guarded=evaluate(None,record,'jepa',guarded=True)
    assert guarded['completed']==1 and guarded['unsafe_executions']==0
    assert guarded['rows'][0]['predictor_failures']>0
    unprotected=evaluate(None,record,'jepa',guarded=False)
    assert unprotected['completed']==0 and unprotected['unsafe_executions']==0


def test_nonfinite_predictor_is_not_an_authorization_source():
    from .experiment import evaluate
    class FailedPredictor:
        def forecast(self,*_):return float('nan')
    record=[r for r in scenarios() if r['split']=='validation'][:1]
    outcome=evaluate(FailedPredictor(),record,'jepa',guarded=True)
    assert outcome['completed']==1 and outcome['unsafe_executions']==0
    assert outcome['rows'][0]['predictor_failures']>0
