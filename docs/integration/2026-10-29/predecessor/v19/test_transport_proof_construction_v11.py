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
    assert result['kernel']['proof_construction']=='finite_fragments'
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
        if command and Path(str(command[-1])).name in {'TraceReplay.lean','TraceReplayPartitioned.lean','TraceReplayNormalized.lean','TraceReplayFragments.lean'} and result.returncode==0:
            path=Path(command[-1]);path.write_bytes(path.read_bytes()+b'\n-- replaced after checking\n')
            changed.append(True)
        return result
    monkeypatch.setattr(subprocess,'run',replace_after_real_compile)
    result=trace.replay(CONTRACT,CSV,timeout=180)
    assert changed and not result['accepted'] and not result['kernel']['kernel_checked']
    assert result['kernel']['status']=='UNAVAILABLE_OR_EXHAUSTED'
    assert 'generated proof source changed' in result['kernel']['error']


def test_partitioned_certificate_keeps_exact_input_and_final_statement():
    data=trace.prepare(CONTRACT,CSV);a=trace.render(data);b=trace.render_partitioned(data)
    signature=b'theorem trace_checked : PCSReal.TransportTrace.check matrix initial states times dt 16 = true := by'
    assert signature in a and signature in b
    suffix=b'theorem recorded_states_and_times'
    assert a[a.index(suffix):]==b[b.index(suffix):]
    start=b'namespace PCSTransportTraceReplay'
    end=b'theorem trace_checked'
    assert a[a.index(start):a.index(end)] in b
    assert b.count(b'private theorem recur_')==80
    assert b'native_decide' not in b and b'sorry' not in b


def test_legacy_negative_constructor_is_preserved():
    import pytest
    data=trace.prepare(CONTRACT,CSV)
    assert trace.successful_refutation(data,{})==trace.render(data,negative=True)
    with pytest.raises(ValueError):trace.successful_refutation(data,{'negative_proof_construction':'caller_verifier'})


def test_actual_refutation_export_is_bound_to_checked_source(tmp_path):
    import pytest
    from copy import deepcopy
    lines=CSV.decode().splitlines();row=lines[1].split(',');row[1]='0';lines[1]=','.join(row)
    raw=('\n'.join(lines)+'\n').encode()
    result=trace.replay(CONTRACT,raw,timeout=180)
    assert not result['accepted'] and result['kernel']['negative_kernel_checked'] is True
    trace.export(tmp_path/'negative',result,CONTRACT,raw)
    assert model.sha((tmp_path/'negative/TraceRejected.lean').read_bytes())==result['kernel']['negative_proof_sha256']
    altered=deepcopy(result);altered['kernel']['negative_proof_sha256']='0'*64
    with pytest.raises(ValueError,match='refutation differs'):trace.export(tmp_path/'refused',altered,CONTRACT,raw)
    assert not (tmp_path/'refused').exists()


def test_fragment_sources_keep_exact_data_and_final_statement():
    data=trace.prepare(CONTRACT,CSV);fragments=trace.render_fragments(data)
    assert len(fragments)==15
    assert all(raw.count(b'\ntheorem ')<=8 for name,raw in fragments.items()
               if name.startswith('TraceFacts'))
    original=trace.render(data)
    assert fragments['TraceLiteralData.lean'].startswith(original[:original.index(b'theorem trace_checked :')])
    driver=fragments['TraceReplayFragments.lean'];suffix=b'theorem recorded_states_and_times'
    assert driver[driver.index(suffix):]==original[original.index(suffix):]
    assert all(b'native_decide' not in raw and b'sorry' not in raw and b'Mathlib.Tactic.FinCases' not in raw for raw in fragments.values())


def test_caller_mutation_cannot_change_the_verified_fallback_snapshot(monkeypatch):
    from pcs.canonical_json import canonicalize_jcs_bytes
    data=trace.prepare(CONTRACT,CSV);original=model.sha(canonicalize_jcs_bytes(data))
    real_run=subprocess.run;mutated=[];forced=[]
    def racing(command,*args,**kwargs):
        name=Path(str(command[-1])).name if command else ''
        if name=='Transport.lean' and not mutated:
            data['states'][-1][0]='0';mutated.append(True)
        if name=='TraceReplay.lean' and not forced:
            forced.append(True)
            return subprocess.CompletedProcess(command,1,stdout='did not reduce to `isTrue` or `isFalse`',stderr='')
        return real_run(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'run',racing)
    result=trace.kernel_replay(data,timeout=180)
    assert mutated and forced and result['kernel_checked'] is True
    assert result['proof_construction']=='finite_fragments'
    assert result['trace_certificate_sha256']==original
    assert result['trace_certificate_sha256']!=model.sha(canonicalize_jcs_bytes(data))


def test_64_step_real_fallback_fits_the_original_single_deadline(monkeypatch,tmp_path):
    import json
    from pcs.canonical_json import canonicalize_jcs_bytes
    contract=json.loads(CONTRACT)
    contract['cells']=[{'id':'A','volume':'1','initial_concentration':'1'},
                       {'id':'B','volume':'1','initial_concentration':'0'}]
    contract['edges']=[{'left':'A','right':'B','conductance':'1'}]
    contract['steps']=64;contract['time_step']='1'
    contract_raw=canonicalize_jcs_bytes(contract)
    csv=('time_s,A,B\n'+''.join(f'{k},{1-k%2},{k%2}\n' for k in range(65))).encode()
    real_run=subprocess.run;injected=[]
    def negative_compact(command,*args,**kwargs):
        if command and Path(str(command[-1])).name=='TraceReplay.lean' and not injected:
            injected.append(True)
            return subprocess.CompletedProcess(command,1,stdout='did not reduce to `isTrue` or `isFalse`',stderr='')
        return real_run(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'run',negative_compact)
    result=trace.replay(contract_raw,csv,timeout=120)
    assert injected and result['accepted'],json.dumps(result,sort_keys=True)
    kernel=result['kernel']
    assert kernel['proof_construction']=='finite_fragments' and kernel['elapsed_seconds']<120
    assert len(kernel['kernel_theorems'])==30
    trace.export(tmp_path/'evidence',result,contract_raw,csv)
    for name,digest in kernel['proof_fragment_sha256'].items():
        exported='TraceReplay.lean' if name=='TraceReplayFragments.lean' else name
        assert model.sha((tmp_path/'evidence'/exported).read_bytes())==digest
