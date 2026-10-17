from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest
from pcs import transport_trace_kernel_v1 as trace
from pcs import transport_kernel_v1 as matrix
from pcs import scientific_workflow_v3 as workflow
from pcs.canonical_json import canonicalize_jcs_bytes as encode

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=(ROOT/'examples/scientific_workflow_v3/contract.json').read_bytes()
CSV=(ROOT/'examples/scientific_workflow_v3/trajectory.csv').read_bytes()


def require_kernel():
    ready=shutil.which('lean') and (ROOT/'.lake/packages/mathlib/.lake/build/lib/lean/Mathlib/Data/Real/Basic.olean').is_file()
    if not ready:
        if os.environ.get('PCS_REQUIRE_TRANSPORT_TRACE_KERNEL')=='1':pytest.fail('required trace kernel dependency missing')
        pytest.skip('pinned Mathlib kernel unavailable in this lane')


def bad_trace(kind):
    lines=CSV.decode().splitlines();row=lines[-1].split(',')
    if kind=='step':row[1:]=['7/32']*(len(row)-1)
    if kind=='time':row[0]='999'
    if kind=='initial':
        row=lines[1].split(',');row[1]='0';lines[1]=','.join(row);return ('\n'.join(lines)+'\n').encode()
    lines[-1]=','.join(row)
    return ('\n'.join(lines)+'\n').encode()


@pytest.mark.parametrize('field,value',[('dt',True),('dt','0\naxiom forged : False'),('steps',True),('steps',65),
    ('trajectory_sha256','0'*64+'\n#eval evil'),('times',[]),('states',[]),('dt','01')])
def test_generator_rejects_untrusted_shapes_and_injected_syntax(field,value):
    d=trace.prepare(CONTRACT,CSV);d[field]=value
    with pytest.raises(ValueError):trace.render(d)


def test_generator_has_exact_data_identity_and_never_embeds_csv_headers():
    d=trace.prepare(CONTRACT,CSV);text=trace.render(d).decode()
    assert hashlib.sha256(CSV).hexdigest() in text
    assert set(d)=={'format','model','trajectory_sha256','steps','dt','times','states'}
    assert 'native_decide' not in text and 'axiom ' not in text
    assert 'recorded_real_states' in text and 'recorded_states_and_times' in text


@pytest.mark.parametrize('raw',[CSV+b'0,1\n',b'time_s,wrong\n0,0\n',b'\xff',b'x'*(workflow.MAX_BYTES+1)])
def test_malformed_data_never_reaches_proof_execution(raw,monkeypatch):
    monkeypatch.setattr(trace,'kernel_replay',lambda *a,**kw:pytest.fail('invalid source data reached kernel'))
    assert not trace.replay(CONTRACT,raw)['accepted']


def test_parser_disagreement_never_reaches_proof_execution(monkeypatch):
    monkeypatch.setattr(workflow,'_observations',lambda *a:[])
    monkeypatch.setattr(trace,'kernel_replay',lambda *a,**k:pytest.fail('parser handoff reached kernel'))
    assert not trace.replay(CONTRACT,CSV)['accepted']


@pytest.fixture(scope='module')
def positive():
    require_kernel();r=trace.replay(CONTRACT,CSV)
    assert r['accepted'],r
    return r


def test_actual_recorded_values_and_times_have_complete_kernel_proofs(positive):
    assert positive['bounded_trajectory_kernel_supported'] is True
    names=matrix.GENERAL_THEOREMS+trace.GENERAL+matrix.REPLAY_THEOREMS+trace.LITERAL
    assert len(names)==30 and set(positive['kernel']['kernel_theorems'])==set(names)
    assert all(set(a)<=matrix.APPROVED_AXIOMS for a in positive['kernel']['kernel_theorems'].values())
    assert positive['scientific_acceptance'] is False and positive['pcs_authority'] is False
    assert all(positive[n]=='OPEN' for n in ['implementation_correspondence','continuum_accuracy','empirical_validity'])


@pytest.mark.parametrize('kind',['step','time','initial'])
def test_actual_false_trace_has_a_kernel_refutation_without_losing_model_truth(kind):
    require_kernel();r=trace.replay(CONTRACT,bad_trace(kind))
    assert not r['accepted'] and not r['bounded_trajectory_kernel_supported']
    assert r['all_time_model_supported'] is True
    assert r['kernel']['status']=='TRACE_FALSIFIED',r['kernel']
    assert r['kernel']['negative_kernel_checked'] is True
    assert set(r['kernel']['negative_kernel_theorems'])==set(matrix.REPLAY_THEOREMS+[trace.NEGATIVE])


def test_forged_python_success_cannot_authorize_wrong_literal_trace(monkeypatch):
    require_kernel()
    actual=workflow.evaluate
    def forged(contract,data):
        result=actual(contract,data);result['outcome']='PASS'
        for c in result['checks']:c['outcome']='PASS'
        return result
    monkeypatch.setattr(workflow,'evaluate',forged)
    r=trace.replay(CONTRACT,bad_trace('step'))
    assert r['model_replay']['accepted'] is True
    assert r['kernel']['negative_kernel_checked'] is True
    assert r['accepted'] is False


@pytest.mark.parametrize('timeout',[0,181,True,float('nan')])
def test_invalid_resource_budget_cannot_authorize_data(timeout):
    with pytest.raises(ValueError):trace.kernel_replay(trace.prepare(CONTRACT,CSV),timeout=timeout)


def test_export_preserves_actual_snapshot_and_proof_and_never_overwrites(positive,tmp_path):
    out=tmp_path/'receipt';trace.export(out,positive,CONTRACT,CSV)
    for name,digest in json.loads((out/'SHA256.json').read_bytes()).items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((out/'TraceReplay.lean').read_bytes()).hexdigest()==positive['kernel']['proof_sha256']
    with pytest.raises(FileExistsError):trace.export(out,positive,CONTRACT,CSV)


def test_source_substitution_prevents_export(positive,monkeypatch,tmp_path):
    actual=trace.sources
    monkeypatch.setattr(trace,'sources',lambda:{**actual(),'trace-receiver.py.txt':b'changed'})
    with pytest.raises(ValueError):trace.export(tmp_path/'must-not-exist',positive)
    assert not (tmp_path/'must-not-exist').exists()


def test_64_step_oscillation_and_literal_time_grid_are_kernel_checked():
    require_kernel();c=json.loads(CONTRACT)
    c['cells']=[{'id':'A','volume':'1','initial_concentration':'1'},{'id':'B','volume':'1','initial_concentration':'0'}]
    c['edges']=[{'left':'A','right':'B','conductance':'1'}];c['steps']=64;c['time_step']='1'
    csv=('time_s,A,B\n'+''.join(f'{k},{1-k%2},{k%2}\n' for k in range(65))).encode()
    r=trace.replay(encode(c),csv)
    assert r['accepted'],r


def test_16_cell_one_step_constant_trace_is_kernel_checked():
    require_kernel();c=json.loads(CONTRACT)
    c['cells']=[{'id':f'C{i}','volume':str(Fraction(i+1,2)),'initial_concentration':'1/4'} for i in range(16)]
    c['edges']=[{'left':f'C{i}','right':f'C{i+1}','conductance':'1/4'} for i in range(15)]
    c['time_step']='1/1024';c['steps']=1
    csv=('time_s,'+','.join(f'C{i}' for i in range(16))+'\n0,'+','.join(['1/4']*16)+'\n1/1024,'+','.join(['1/4']*16)+'\n').encode()
    r=trace.replay(encode(c),csv)
    assert r['accepted'],r


def test_existing_signed_package_composes_without_promoting_scientific_authority():
    require_kernel()
    base=ROOT/'research/transport-kernel-v1/sequential-kernel-v2/receiving/signed-v3-base'
    fp=json.loads((base/'SUMMARY.json').read_bytes())['producer_public_key_fingerprint']
    r=trace.replay_bundle(base/'positive.pcs.zip',base/'producer-public.pem',expected_fingerprint=fp)
    assert r['accepted'] and r['pcs_package_valid'] and r['bounded_trajectory_kernel_supported'],r
    assert not r['scientific_acceptance']


def test_signed_receiver_uses_original_bytes_snapshot(tmp_path,monkeypatch):
    source=tmp_path/'original.zip';source.write_bytes(b'captured')
    def verifier(snapshot,*args,**kwargs):
        assert Path(snapshot).read_bytes()==b'captured'
        source.write_bytes(b'replaced')
        return {'accepted':False,'scientific_acceptance':False}
    monkeypatch.setattr(matrix,'replay_bundle',verifier)
    r=trace.replay_bundle(source,'unused',expected_fingerprint='unused')
    assert not r['accepted'] and r['format']==trace.FORMAT


@pytest.mark.parametrize('which',['contract','trajectory','certificate','proof'])
def test_evidence_export_rejects_substituted_bytes_or_certificate(positive,tmp_path,which):
    r=deepcopy(positive);contract=CONTRACT;csv=CSV
    if which=='contract':contract+=b'\n'
    if which=='trajectory':csv+=b'\n'
    if which=='certificate':r['trace_certificate']['states'][-1][0]='0'
    if which=='proof':r['kernel']['proof_sha256']='0'*64
    with pytest.raises(ValueError):trace.export(tmp_path/'must-not-exist',r,contract,csv)
    assert not (tmp_path/'must-not-exist').exists()


def test_rejected_input_exports_its_exact_source_bytes(tmp_path):
    raw=b'time_s,wrong\n0,0\n';r=trace.replay(CONTRACT,raw)
    assert r['accepted'] is False
    trace.export(tmp_path/'rejected',r,CONTRACT,raw)
    assert (tmp_path/'rejected/trajectory.csv').read_bytes()==raw
    assert r['trajectory_sha256']==hashlib.sha256(raw).hexdigest()
