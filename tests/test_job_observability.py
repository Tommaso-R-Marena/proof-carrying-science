import json
import pytest
from pcs.experimental.prover.job_observability import JobTrace

def trace():return JobTrace('a'*32,'b'*40,'c'*64)

def test_bounded_correlated_events_and_real_wrapper_cost(capsys):
    t=trace();result=t.measure('memory_policy',lambda:{'status':'unknown','cost':{'all_Lean_execution_attempts':7}})
    assert result['status']=='unknown' and len(t.events)==2
    assert t.events[1]['recorded_Lean_execution_attempts']==7
    for line in capsys.readouterr().out.splitlines():
        event=json.loads(line.split(':',1)[1]);assert event['request_id']=='a'*32
        assert event['core_sha']=='b'*40 and event['pcs_authority'] is False
    assert t.events[1]['wall_seconds']>=0 and t.events[1]['cpu_seconds']>=0

def test_failure_is_logged_without_error_payload_or_false_receipt(capsys):
    t=trace()
    def operation():raise RuntimeError('test secret must not enter event logs')
    with pytest.raises(RuntimeError):t.measure('memory_policy',operation)
    assert t.events[-1]['status']=='failed'
    assert 'secret' not in capsys.readouterr().out

def test_forged_accounting_and_unapproved_stages_cannot_be_logged():
    with pytest.raises(ValueError):trace().emit('arbitrary_user_text','finished')
    with pytest.raises(ValueError):trace().emit('memory_policy','finished',lean_attempts=True)
    with pytest.raises(ValueError):trace().emit('memory_policy','finished',wall_seconds=float('nan'))
    t=trace()
    for _ in range(32):t.emit('memory_policy','started')
    with pytest.raises(ValueError):t.emit('memory_policy','started')
