from copy import deepcopy
from fractions import Fraction as F
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from . import core, evidence, experiment, kernel

ROOT=Path(__file__).resolve().parents[2]


def record(name, raw, result):
    target=os.environ.get('PCS_ENVELOPE_EVIDENCE_DIR')
    if target:evidence.export(Path(target)/name,raw,result)


@pytest.fixture(scope='module')
def positive():
    raw, errors=experiment.case(mode='drift',steps=4)
    r=kernel.replay(raw,'1/25')
    assert r['kernel_checked'],r
    record('tight-boundary',raw,r)
    return raw,errors,r


def test_real_kernel_checks_nonzero_tight_boundary_and_all_theorem_inventories(positive):
    raw,errors,r=positive
    assert r['status']=='ENVELOPE_WITHIN_TOLERANCE'
    assert list(map(F,r['proposal']['budgets']))==errors
    assert errors[-1]==F(1,25) and errors[-1]>0
    assert set(kernel.GENERAL)<=set(r['axiom_closures'])
    assert 'PCSEnvelopeReplay.uniform_bound' in r['axiom_closures']
    assert 'PCSEnvelopeReplay.recorded_real_bounds' in r['axiom_closures']
    assert all(set(a)<=kernel.model.APPROVED_AXIOMS for a in r['axiom_closures'].values())
    assert r['sources_stable'] and all(e['returncode']==0 for e in r['executions'])
    assert not r['pcs_authority'] and not r['scientific_acceptance'] and not r['empirical_validation']
    assert r['proposal']['kernel_checked'] is False  # proposal does not become an authority


@pytest.mark.parametrize('mode,tol,status',[('exact','0','ENVELOPE_WITHIN_TOLERANCE'),('round_loop','1/10','ENVELOPE_WITHIN_TOLERANCE'),('cancel','1/100','ENVELOPE_BUDGET_EXCEEDS_TOLERANCE')])
def test_real_kernel_exact_rounded_and_conservative_cases(mode,tol,status):
    raw,errors=experiment.case(width=3,steps=4,mode=mode)
    r=kernel.replay(raw,tol)
    assert r['kernel_checked'] and r['status']==status,r
    assert all(e<=F(b) for e,b in zip(errors,r['proposal']['budgets']))
    if mode=='round_loop':assert max(errors)>0
    if mode=='cancel':
        assert max(errors)<=F(tol)<F(r['proposal']['budgets'][-1])
        assert 'PCSEnvelopeReplay.budget_exceeds' in r['axiom_closures']
        assert 'PCSEnvelopeReplay.uniform_bound' not in r['axiom_closures']
    record(mode,raw,r)


@pytest.mark.parametrize('field',['eta','eps','budgets'])
def test_false_proposer_output_is_rejected_by_actual_lean(field,monkeypatch):
    raw,_=experiment.case(mode='cancel')
    actual=core.propose
    def dishonest(data,tolerance):
        p=actual(data,tolerance)
        p[field]='0' if field=='eta' else ['0']*len(p[field])
        return p
    monkeypatch.setattr(core,'propose',dishonest)
    r=kernel.replay(raw,'1')
    assert not r['kernel_checked'] and r['status']=='REFUSED',r
    assert r['executions'][-1]['returncode']!=0
    record('forged-'+field,raw,r)


def test_reviewer_ignores_forged_positive_result_and_runs_real_lean(positive,tmp_path):
    raw,_,r=positive
    evidence.export(tmp_path/'original',raw,r)
    # A fabricated affirmative record cannot substitute for the fresh kernel run.
    folder=tmp_path/'original'
    (folder/'result.json').write_text('{"kernel_checked":true,"pcs_authority":true}')
    inv=json.loads((folder/'SHA256.json').read_text())
    inv['result.json']=kernel.model.sha((folder/'result.json').read_bytes())
    (folder/'SHA256.json').write_text(json.dumps(inv))
    replay=evidence.verify(folder,out=tmp_path/'fresh')
    assert replay['kernel_checked'] and not replay['pcs_authority']
    assert replay['executions'] and replay['input_sha256']==kernel.model.sha(raw)
    assert (tmp_path/'fresh/input.json').read_bytes()==raw
    record('independent-review',raw,replay)


@pytest.mark.parametrize('target',['input.json','Replay.lean','sources/Envelope.lean','request.json'])
def test_reviewer_rejects_rehashed_changes_before_execution(positive,tmp_path,monkeypatch,target):
    raw,_,r=positive
    evidence.export(tmp_path/'old',raw,r)
    p=tmp_path/'old'/target
    p.write_bytes(p.read_bytes()+b'\n-- changed' if target.endswith('.lean') else
                  b'{"format":"pcs-trace-envelope-request-v1","tolerance":"0"}' if target=='request.json' else b'{}')
    inv=json.loads((tmp_path/'old/SHA256.json').read_text());inv[target]=kernel.model.sha(p.read_bytes())
    (tmp_path/'old/SHA256.json').write_text(json.dumps(inv))
    monkeypatch.setattr(kernel,'replay',lambda *a,**kw:pytest.fail('Changed evidence reached replay'))
    with pytest.raises(ValueError):evidence.verify(tmp_path/'old')


def test_manifest_traversal_and_source_substitution_refused(positive,tmp_path):
    raw,_,r=positive;evidence.export(tmp_path/'old',raw,r)
    inv=json.loads((tmp_path/'old/SHA256.json').read_text());inv['../escape']='0'*64
    (tmp_path/'old/SHA256.json').write_text(json.dumps(inv))
    with pytest.raises(ValueError,match='inventory'):evidence.verify(tmp_path/'old')


def test_verification_exports_captured_bytes_after_the_input_path_changes(positive,tmp_path,monkeypatch):
    raw,_,r=positive;evidence.export(tmp_path/'old',raw,r)
    actual=kernel.replay
    def change_path(captured,tolerance,**kw):
        assert captured==raw
        (tmp_path/'old/input.json').write_bytes(b'changed after capture')
        return actual(captured,tolerance,**kw)
    monkeypatch.setattr(kernel,'replay',change_path)
    result=evidence.verify(tmp_path/'old',out=tmp_path/'new')
    assert result['kernel_checked'] and (tmp_path/'new/input.json').read_bytes()==raw
    record('captured-byte-review',raw,result)


def test_fake_affirmative_executable_is_refused_before_execution(tmp_path,monkeypatch):
    raw,_=experiment.case()
    fake=tmp_path/'lean';fake.write_bytes(b'#!/bin/sh\necho affirmative-verdict\n')
    monkeypatch.setattr(kernel.model,'_environment',lambda *a:(str(fake),dict(os.environ),'untrusted version text'))
    r=kernel.replay(raw,'1')
    assert not r['kernel_checked'] and r['executions']==[] and 'binary bytes required' in r['error']


def test_staged_source_mutation_invalidates_even_a_successful_actual_compile(positive,monkeypatch):
    raw,_,_=positive
    actual=kernel.subprocess.run
    def changed(command,**kw):
        if str(command[-1]).endswith('/Replay.lean'):
            p=Path(command[-1]);p.write_bytes(p.read_bytes()+b'\n-- changed staged source\n')
        return actual(command,**kw)
    monkeypatch.setattr(kernel.subprocess,'run',changed)
    r=kernel.replay(raw,'1/25')
    assert not r['kernel_checked'] and 'Staged proof source changed' in r['error'],r
    assert r['executions'][-1]['returncode']==0


@pytest.mark.parametrize('tol',[True,None,'-1','NaN','1/0','0.1; unsafe','1e999999'])
def test_bad_tolerances_fail_closed_without_kernel(tol,monkeypatch):
    raw,_=experiment.case()
    monkeypatch.setattr(kernel.model,'_environment',lambda *a:pytest.fail('Bad tolerance reached Lean'))
    r=kernel.replay(raw,tol)
    assert not r['kernel_checked'] and r['executions']==[]


@pytest.mark.parametrize('timeout',[True,0,-1,301,float('nan'),float('inf')])
def test_invalid_timeouts_refused(timeout):
    with pytest.raises(ValueError):kernel.replay(b'{}','0',timeout=timeout)


def test_time_fault_and_oversized_architecture_refused_without_kernel(monkeypatch):
    monkeypatch.setattr(kernel.model,'_environment',lambda *a:pytest.fail('Unsupported data reached Lean'))
    raw,_=experiment.case();b=json.loads(raw);rows=b['trajectory'].splitlines();cells=rows[-1].split(',');cells[0]='999';rows[-1]=','.join(cells);b['trajectory']='\n'.join(rows)+'\n'
    for raw in [json.dumps(b).encode(),experiment.case(width=9,steps=1)[0]]:
        r=kernel.replay(raw,'1');assert not r['kernel_checked'] and r['executions']==[]


def test_missing_time_budget_never_becomes_a_verdict():
    raw,_=experiment.case();r=kernel.replay(raw,'1',timeout=0.000001)
    assert not r['kernel_checked'] and r['status']=='REFUSED'


def test_exact_signed_rounding_and_ties():
    assert [experiment.quantize(F(x),0) for x in ['-5/2','-3/2','-1/2','1/2','3/2','5/2']]==[-2,-2,0,0,2,2]
    assert experiment.quantize(F('-12345/1000'),2)==F('-617/50')


def test_numeric_exponents_are_bounded_before_rational_allocation(monkeypatch):
    raw,_=experiment.case()
    monkeypatch.setattr(core,'rational',lambda *a:pytest.fail('Huge exponent reached rational allocation'))
    with pytest.raises(ValueError,match='exponent'):core.prepare(raw,'1e999999999')
    b=json.loads(raw);b['contract']['time_step']='1e999'
    with pytest.raises(ValueError,match='exponent'):core.prepare(json.dumps(b).encode(),'1')


@pytest.mark.parametrize('raw',[b'{}',b'[]',b'\xff',b'{"format":1,"format":2}',b'x'*262145])
def test_malformed_input_is_not_a_kernel_verdict(raw,monkeypatch):
    monkeypatch.setattr(kernel.model,'_environment',lambda *a:pytest.fail('Malformed input reached Lean'))
    r=kernel.replay(raw,'1')
    assert not r['kernel_checked'] and r['status']=='REFUSED' and not r['executions']


def test_frozen_source_changes_invalidate_an_actual_proof(positive,monkeypatch):
    raw,_,_=positive
    actual=kernel.sources;calls=0
    def changing():
        nonlocal calls
        calls+=1
        s=actual()
        if calls>1:s['core.py']+=b'\n# changed during replay\n'
        return s
    monkeypatch.setattr(kernel,'sources',changing)
    r=kernel.replay(raw,'1/25')
    assert not r['kernel_checked'] and 'sources changed' in r['error'],r
    assert r['executions'][-1]['returncode']==0  # a successful proof alone is insufficient


def test_deterministic_432_cases_against_independent_edge_flux_oracle():
    r=experiment.run()
    assert r['samples']==432 and r['envelope_violations']==0 and r['tight_drift_cases']==108
    assert r['conservative_budget_refusals']>0
    assert r['actual_within']>=r['budgets_met']
    assert not r['kernel_checked'] and not r['empirical_validation']


def test_nonstochastic_assumption_is_necessary():
    # Outside the supported contract: p=2I amplifies initial error 1 to 4,
    # despite zero local residual. The row-stochastic premise is essential.
    observed=[F(1),F(2),F(4)]
    assert all(b==2*a for a,b in zip(observed,observed[1:]))
    assert observed[-1]>observed[0]


def test_cli_analyze_is_diagnostic_only_and_no_overwrite(positive,tmp_path):
    raw,_,_=positive;p=tmp_path/'case.json';p.write_bytes(raw)
    cmd=[sys.executable,'-m','research.trace_envelope_v1']
    done=subprocess.run(cmd+['analyze',str(p),'--tolerance','1/25'],cwd=ROOT,text=True,capture_output=True,timeout=10)
    r=json.loads(done.stdout);assert done.returncode==0 and r['status']=='DIAGNOSTIC_ONLY' and not r['kernel_checked']
    existing=tmp_path/'old';existing.mkdir();marker=existing/'marker';marker.write_text('retain')
    done=subprocess.run(cmd+['check',str(p),str(existing),'--tolerance','1'],cwd=ROOT,text=True,capture_output=True,timeout=10)
    assert done.returncode==20 and not json.loads(done.stdout)['kernel_checked'] and marker.read_text()=='retain'
