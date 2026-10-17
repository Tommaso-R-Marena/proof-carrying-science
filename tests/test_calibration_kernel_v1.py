from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

import pytest
from pcs import calibration_kernel_v1 as calibration
from pcs.canonical_json import canonicalize_jcs_bytes as encode
from pcs.experimental.calibration_proposer_v1 import propose

DATA=b'x,y\n0,1\n1,4\n2,8\n'
CONTRACT=encode({'format':calibration.FORMAT,'data_sha256':calibration.sha(DATA),
    'models':[{'degree':1,'fit_rows':[0,1,2],'queries':['4']}]})
CERTIFICATE=propose(DATA,CONTRACT)


def required_kernel():
    ready=shutil.which('lean') and (calibration.ROOT/'.lake/packages/mathlib/.lake/build/lib/lean/Mathlib/Data/Real/Basic.olean').is_file()
    if not ready:
        if os.environ.get('PCS_REQUIRE_CALIBRATION_KERNEL')=='1':pytest.fail('required calibration kernel missing')
        pytest.skip('genuine pinned Mathlib unavailable in this lane')


@pytest.fixture(scope='module')
def positive():
    required_kernel();r=calibration.replay(DATA,CONTRACT,CERTIFICATE)
    assert r['accepted'],r
    return r


def test_actual_certificate_proves_real_global_optimum_and_sharp_radius(positive):
    _,literal=calibration.render(positive['prepared'])
    assert len(literal)==17
    assert set(positive['kernel']['kernel_theorems'])==set(calibration.GENERAL+literal)
    assert positive['kernel']['status']=='KERNEL_CHECKED'
    assert all(set(a)<=calibration.infrastructure.APPROVED_AXIOMS for a in positive['kernel']['kernel_theorems'].values())
    assert not positive['scientific_acceptance'] and not positive['pcs_authority']
    assert positive['physical_model_validity']=='OPEN'
    assert positive['measurement_error_bound']=='ASSUMED_SCENARIO_ONLY'


@pytest.mark.parametrize('kind',['coefficient','sse','dual','gain','minimax-dual','minimax-gain'])
def test_actual_kernel_rejects_forged_numerics_and_too_small_uncertainty(kind):
    required_kernel();cert=json.loads(CERTIFICATE)
    m=cert['models'][0]
    if kind=='coefficient':m['coefficients'][0]='0'
    if kind=='sse':m['sse']='0'
    if kind=='dual':m['queries'][0]['weights'][0]='0'
    if kind=='gain':m['queries'][0]['gain']='0'
    if kind=='minimax-dual':m['queries'][0]['minimax']['dual'][0]='0'
    if kind=='minimax-gain':m['queries'][0]['minimax']['gain']='0'
    r=calibration.replay(DATA,CONTRACT,encode(cert))
    assert not r['accepted'] and not r['kernel']['kernel_checked']
    assert r['kernel']['status']=='CERTIFICATE_OR_SOURCE_REJECTED',r


@pytest.mark.parametrize('kind',['degree','bool-degree','duplicate-row','unordered-row','outside-row',
    'injection','noncanonical','float','bool','extra','missing-query','too-many-queries'])
def test_malformed_witness_never_reaches_kernel(kind,monkeypatch):
    c=json.loads(CONTRACT);w=json.loads(CERTIFICATE);m=c['models'][0];p=w['models'][0]
    if kind=='degree':m['degree']=4
    if kind=='bool-degree':m['degree']=True
    if kind=='duplicate-row':m['fit_rows']=[0,1,1]
    if kind=='unordered-row':m['fit_rows']=[1,0,2]
    if kind=='outside-row':m['fit_rows']=[0,1,99]
    if kind=='injection':p['sse']='0\naxiom forged : False'
    if kind=='noncanonical':p['sse']='01'
    if kind=='float':p['sse']=0.0
    if kind=='bool':p['sse']=True
    if kind=='extra':p['authority']='ACCEPT'
    if kind=='missing-query':p['queries']=[]
    if kind=='too-many-queries':m['queries']=['4']*9
    contract=encode(c);w['contract_sha256']=calibration.sha(contract)
    monkeypatch.setattr(calibration,'kernel_replay',lambda *a,**k:pytest.fail('malformed witness reached kernel'))
    assert calibration.replay(DATA,contract,encode(w))['accepted'] is False


@pytest.mark.parametrize('raw',[DATA+b'3,9,0\n',b'x,y\n0,NaN\n1,2\n',b'x,y\n0,1\n',b'unknown,y\n0,1\n1,2\n',b'\xff',b'x'*(calibration.MAX_BYTES+1)])
def test_malformed_and_substituted_observations_cannot_authorize(raw,monkeypatch):
    monkeypatch.setattr(calibration,'kernel_replay',lambda *a,**k:pytest.fail('bad input reached kernel'))
    assert not calibration.replay(raw,CONTRACT,CERTIFICATE)['accepted']


def test_duplicate_json_keys_rejected_before_kernel(monkeypatch):
    monkeypatch.setattr(calibration,'kernel_replay',lambda *a,**k:pytest.fail('duplicate keys reached kernel'))
    assert not calibration.replay(DATA,b'{"format":1,"format":2}',CERTIFICATE)['accepted']


@pytest.mark.parametrize('timeout',[0,301,True,float('nan'),float('inf')])
def test_invalid_budget_never_authorizes(timeout):
    prepared=calibration.prepare(DATA,CONTRACT,CERTIFICATE)
    with pytest.raises(ValueError):calibration.kernel_replay(prepared,timeout=timeout)


def test_evidence_is_bound_to_exact_sources_and_regenerated_proofs(positive,tmp_path):
    destination=tmp_path/'receipt';calibration.export(destination,positive,DATA,CONTRACT,CERTIFICATE)
    for name,digest in json.loads((destination/'SHA256.json').read_bytes()).items():
        assert calibration.sha((destination/name).read_bytes())==digest
    assert calibration.sha((destination/'Replay.lean').read_bytes())==positive['kernel']['proof_sha256']
    with pytest.raises(FileExistsError):calibration.export(destination,positive,DATA,CONTRACT,CERTIFICATE)


@pytest.mark.parametrize('field',['prepared','proof','source'])
def test_export_refuses_proof_data_or_receiving_source_substitution(positive,tmp_path,monkeypatch,field):
    r=deepcopy(positive)
    if field=='prepared':r['prepared']['models'][0]['coefficients'][0]='0'
    if field=='proof':r['kernel']['proof_sha256']='0'*64
    if field=='source':
        actual=calibration.sources
        monkeypatch.setattr(calibration,'sources',lambda:{**actual(),'PCSReal/Calibration.lean':b'substituted'})
    with pytest.raises(ValueError):calibration.export(tmp_path/'must-not-exist',r,DATA,CONTRACT,CERTIFICATE)
    assert not (tmp_path/'must-not-exist').exists()


def test_frozen_real_experiment_uses_all_rows_and_no_heldout_training():
    import importlib.util
    spec=importlib.util.spec_from_file_location('calibration_experiment',calibration.ROOT/'scripts/run_experimental_calibration_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    groups=module.groups();seen=[]
    for rows in groups.values():
        data,contract,cert=module.inputs(rows);c=json.loads(contract)
        prepared=calibration.prepare(data,contract,cert)
        assert len(prepared['models'])==6
        for m in c['models'][::2]:assert m['fit_rows']==list(range(0,14,2))
        seen.extend(r[2] for r in rows)
    assert len(seen)==len(set(seen))==308


def test_generated_source_contains_no_submitted_executable_text():
    prepared=calibration.prepare(DATA,CONTRACT,CERTIFICATE);raw,names=calibration.render(prepared)
    assert b'native_decide' not in raw and b'axiom ' not in raw and b'#eval' not in raw
    assert 'PCSCalibrationReplay.M0.Q0.sharp_radius' in names


def test_wrapped_audit_reports_require_exact_identities_and_approved_axioms():
    name=calibration.GENERAL[0]
    good=f"'{name}' depends on axioms: [propext,\n Classical.choice, Quot.sound]"
    assert set(calibration.inventory(good,[name])[name])==calibration.infrastructure.APPROVED_AXIOMS
    for bad in [good+'\n'+good,good.replace('Quot.sound','sorryAx'),
                good.replace(name,'Unrelated.theorem'),good+"\n'Unexpected.extra' does not depend on any axioms",'']:
        with pytest.raises(ValueError):calibration.inventory(bad,[name])


def test_resource_exhaustion_never_grants_mathematical_support(monkeypatch):
    import subprocess
    def exhausted(*a,**k):raise subprocess.TimeoutExpired('deliberate resource control',1)
    monkeypatch.setattr(calibration.infrastructure,'_environment',exhausted)
    r=calibration.replay(DATA,CONTRACT,CERTIFICATE)
    assert not r['accepted'] and not r['mathematical_support']
    assert r['kernel']['status']=='UNAVAILABLE_OR_EXHAUSTED'
    assert all(c['status']=='OPEN' for c in r['claims'])


def test_ols_only_request_cannot_claim_unrequested_minimax_support():
    required_kernel();c=json.loads(CONTRACT);c['models'][0]['queries']=[]
    contract=encode(c);r=calibration.replay(DATA,contract,propose(DATA,contract))
    assert r['accepted'],r
    assert r['claims'][0]['status']=='KERNEL_SUPPORTED'
    assert all(c['status']=='NOT_REQUESTED' for c in r['claims'][1:3])
