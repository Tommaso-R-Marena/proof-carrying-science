"""Real fallback proof checks; only a negative initial error is fault injected."""
import subprocess
from pathlib import Path
from pcs import transport_trace_kernel_v1 as trace,transport_kernel_v1 as model

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=(ROOT/'examples/scientific_workflow_v3/contract.json').read_bytes()
CSV=(ROOT/'examples/scientific_workflow_v3/trajectory.csv').read_bytes()


def test_normalized_construction_keeps_exact_statement_and_following_theorems():
    data=trace.prepare(CONTRACT,CSV);a=trace.render(data);b=trace.render_normalized(data)
    signature=b'theorem trace_checked : PCSReal.TransportTrace.check matrix initial states times dt 16 = true := by'
    assert signature in a and signature in b
    suffix=b'theorem recorded_states_and_times'
    assert a[a.index(suffix):]==b[b.index(suffix):]
    segment=b[b.index(signature):b.index(suffix)]
    assert b'by decide +kernel, by decide +kernel, by decide +kernel' not in segment
    assert b'norm_num [states, matrix, step, Fin.sum_univ_succ]' in segment
    assert b'native_decide' not in b and b'sorry' not in b


def test_unknown_proof_construction_is_not_silently_adopted():
    import pytest
    with pytest.raises(ValueError):trace.successful_proof(trace.prepare(CONTRACT,CSV),{'proof_construction':'producer_verifier'})


def test_negative_first_attempt_has_genuinely_checked_normalized_fallback(monkeypatch,tmp_path):
    real_run=subprocess.run;injected=[]
    def negative_first(command,*args,**kwargs):
        if command and Path(str(command[-1])).name=='TraceReplay.lean' and not injected:
            injected.append(True)
            return subprocess.CompletedProcess(command,1,stdout='did not reduce to `isTrue` or `isFalse`',stderr='')
        return real_run(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'run',negative_first)
    result=trace.replay(CONTRACT,CSV,timeout=180)
    assert injected and result['accepted'] and result['kernel']['kernel_checked']
    assert result['kernel']['proof_construction']=='finite_norm_num'
    assert len(result['kernel']['kernel_theorems'])==30
    assert all(set(v)<=model.APPROVED_AXIOMS for v in result['kernel']['kernel_theorems'].values())
    trace.export(tmp_path/'evidence',result,CONTRACT,CSV)
    successful=(tmp_path/'evidence/TraceReplay.lean').read_bytes()
    assert model.sha(successful)==result['kernel']['proof_sha256']
    assert (tmp_path/'evidence/TraceReplayKernelAttempt.lean').read_bytes()==trace.render(result['trace_certificate'])


def test_real_positive_compile_does_not_authorize_changed_proof_bytes(monkeypatch):
    real_run=subprocess.run;changed=[]
    def replace_after_real_compile(command,*args,**kwargs):
        result=real_run(command,*args,**kwargs)
        if command and Path(str(command[-1])).name=='TraceReplay.lean' and result.returncode==0:
            path=Path(command[-1]);path.write_bytes(path.read_bytes()+b'\n-- replaced after checking\n')
            changed.append(True)
        return result
    monkeypatch.setattr(subprocess,'run',replace_after_real_compile)
    result=trace.replay(CONTRACT,CSV,timeout=180)
    assert changed and not result['accepted'] and not result['kernel']['kernel_checked']
    assert result['kernel']['status']=='UNAVAILABLE_OR_EXHAUSTED'
    assert 'generated proof source changed' in result['kernel']['error']
