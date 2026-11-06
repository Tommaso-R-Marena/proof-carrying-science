from copy import deepcopy
import pytest
from .experiment import rollout
from .scenarios import scenarios,safe_workflow
from .replay import replay_trace


def test_actual_replay_rejects_edited_success():
    r=scenarios()[0];e=rollout(r,safe_workflow(r['goal']),guarded=True)
    assert replay_trace(r,e['rows'],True)['success']
    forged=deepcopy(e['rows']);forged[-1]['info']['success']=False
    with pytest.raises(ValueError,match='success'):replay_trace(r,forged,True)


def test_actual_unguarded_counterexample_requires_same_enforcement_mode():
    r=next(r for r in scenarios() if r['goal']=='sensitive')
    e=rollout(r,['inspect','read_sensitive','draft','publish'],guarded=False)
    assert replay_trace(r,e['rows'],False)['unsafe_executions']>0
    with pytest.raises(ValueError):replay_trace(r,e['rows'],True)
