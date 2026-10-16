from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

import pytest

from pcs import transport_kernel_v1 as receiver
from pcs import scientific_workflow_v3 as workflow
from pcs.canonical_json import canonicalize_jcs_bytes as encode

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT/'examples/scientific_workflow_v3'
CONTRACT = (EXAMPLE/'contract.json').read_bytes()
TRAJECTORY = (EXAMPLE/'trajectory.csv').read_bytes()


def test_independent_incidence_reconstruction_agrees_on_irregular_seeded_models():
    rng = random.Random(930174)
    for _ in range(40):
        c = json.loads(CONTRACT)
        n = rng.randint(2, 8)
        c['cells'] = [{'id': f'Cell{i}', 'volume': str(Fraction(rng.randint(1,9),rng.randint(1,4))),
                       'initial_concentration': str(Fraction(rng.randint(0,8),4))} for i in range(n)]
        c['edges'] = [{'left':f'Cell{i}', 'right':f'Cell{j}', 'conductance':str(Fraction(rng.randint(1,4),4))}
            for i in range(n) for j in range(i+1,n) if j == i+1 or rng.random() < .3]
        c['time_step'] = str(Fraction(1,64*n))
        raw = encode(c)
        model = receiver.prepare(raw)
        assert [[Fraction(x) for x in row] for row in model['matrix']] == workflow.transition_matrix(workflow.load_contract(raw))
        assert model['contract_sha256'] == hashlib.sha256(raw).hexdigest()
        assert len(model['matrix']) == n


@pytest.mark.parametrize('change', ['matrix','volume','initial','binding','bool','extra','proof-injection','nan'])
def test_untrusted_model_binding_is_checked_before_any_proof_execution(change, monkeypatch):
    model = receiver.prepare(CONTRACT)
    if change == 'matrix': model['matrix'][0][0] = '1'
    if change == 'volume': model['volumes'][0] = '2'
    if change == 'initial': model['initial'][0] = '0'
    if change == 'binding': model['contract_sha256'] = '0'*64
    if change == 'bool': model['matrix'][0][0] = True
    if change == 'extra': model['proof'] = 'axiom forged : False'
    if change == 'proof-injection': model['contract_sha256'] += '\naxiom forged : False'
    if change == 'nan': model['matrix'][0][0] = 'nan'
    monkeypatch.setattr(receiver, 'kernel_replay', lambda *a,**k: pytest.fail('untrusted mismatch reached compiler'))
    result = receiver.replay(CONTRACT, proposal_raw=encode(model))
    assert result['accepted'] is result['all_time_model_supported'] is False
    assert result['errors'] and not result['scientific_acceptance']


@pytest.mark.parametrize('bad', [True, '1/2\naxiom forged : False', '01', 'NaN', {'proof':'evil'}])
def test_literal_generator_accepts_only_canonical_exact_data(bad):
    model = receiver.prepare(CONTRACT)
    model['matrix'][0][0] = bad
    with pytest.raises(ValueError): receiver._render(model)


def test_new_source_bytes_cannot_reuse_a_certificate_for_another_contract(monkeypatch):
    proposal = encode(receiver.prepare(CONTRACT))
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k: pytest.fail('stale binding reached compiler'))
    result = receiver.replay(CONTRACT+b'\n',proposal_raw=proposal)
    assert not result['accepted'] and result['errors']


def test_cfl_violation_is_rejected_without_promoting_model_truth(monkeypatch):
    c=json.loads(CONTRACT);c['time_step']='2'
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k: pytest.fail('CFL failure reached compiler'))
    result=receiver.replay(encode(c),TRAJECTORY)
    assert not result['accepted'] and not result['all_time_model_supported']


def test_mathematical_support_does_not_authorize_a_false_trajectory(monkeypatch):
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k:{'kernel_checked':True})
    lines=TRAJECTORY.decode().splitlines();row=lines[-1].split(',');row[1]=str(Fraction(row[1])+1);lines[-1]=','.join(row)
    result=receiver.replay(CONTRACT, ('\n'.join(lines)+'\n').encode())
    assert result['all_time_model_supported'] and not result['bounded_trajectory_supported']
    assert not result['accepted']
    assert all(result[k]=='OPEN' for k in ['implementation_correspondence','continuum_accuracy','empirical_validity'])
    assert not result['scientific_acceptance'] and not result['pcs_authority']


@pytest.mark.parametrize('change', ['missing','duplicate','unapproved','wrong-name'])
def test_axiom_inventory_cannot_be_selected_by_a_producer(change):
    names=['A','B'];log="'A' depends on axioms: [propext]\n'B' does not depend on any axioms\n"
    if change=='missing':log=log.splitlines()[0]
    if change=='duplicate':log+="'A' depends on axioms: [propext]\n"
    if change=='unapproved':log=log.replace('propext','sorryAx')
    if change=='wrong-name':log=log.replace("'B'","'C'")
    with pytest.raises(ValueError):receiver._inventory(log,names)


def require_kernel():
    ready=shutil.which('lean') and (ROOT/'.lake/packages/mathlib/.lake/build/lib/lean/Mathlib/Data/Real/Basic.olean').is_file()
    if not ready:
        if os.environ.get('PCS_REQUIRE_TRANSPORT_KERNEL')=='1':pytest.fail('required pinned Mathlib/Lean environment unavailable')
        pytest.skip('Mathlib kernel dependency not installed in this lane')


@pytest.fixture(scope='module')
def genuine():
    require_kernel()
    result=receiver.replay(CONTRACT,TRAJECTORY,proposal_raw=encode(receiver.prepare(CONTRACT)))
    assert result['accepted'],result.get('kernel',result)
    return result


def test_actual_private_kernel_checks_all_real_states_and_all_time_theorems(genuine):
    assert genuine['all_time_model_supported'] and genuine['bounded_trajectory_supported']
    assert set(genuine['kernel']['kernel_theorems']) == set(receiver.GENERAL_THEOREMS+receiver.REPLAY_THEOREMS)
    assert len(genuine['kernel']['executions'])==2
    assert all(e['returncode']==0 for e in genuine['kernel']['executions'])
    assert not genuine['producer_proof_executed']
    assert not genuine['scientific_acceptance']


def test_actual_false_certificate_is_kernel_rejected():
    require_kernel()
    model=receiver.prepare(CONTRACT)
    model['matrix'][0][0]=str(Fraction(model['matrix'][0][0])+Fraction(1,20))
    model['matrix'][0][1]=str(Fraction(model['matrix'][0][1])-Fraction(1,20))
    rejected=receiver.kernel_replay(model)
    assert rejected['status']=='CERTIFICATE_FALSIFIED',rejected
    assert rejected['negative_kernel_checked']
    assert set(rejected['negative_kernel_theorems'])=={'PCSTransportReplay.matrix_rejected'}
    assert not rejected['kernel_checked']
    assert rejected['executions'][-2]['returncode']!=0
    assert rejected['executions'][-1]['returncode']==0


def test_exported_evidence_binds_actual_proof_sources_and_rejects_overwrite(genuine,tmp_path):
    out=tmp_path/'receipt'
    receiver.export_evidence(out,genuine,CONTRACT,TRAJECTORY)
    inventory=json.loads((out/'SHA256.json').read_bytes())
    assert all(hashlib.sha256((out/p).read_bytes()).hexdigest()==h for p,h in inventory.items())
    assert hashlib.sha256((out/'Replay.lean').read_bytes()).hexdigest()==genuine['kernel']['proof_sha256']
    assert hashlib.sha256((out/'receiving-source/PCSReal/Transport.lean').read_bytes()).hexdigest()==genuine['kernel']['formal_source_sha256']
    with pytest.raises(FileExistsError):receiver.export_evidence(out,genuine)


def test_cli_emits_a_rejection_receipt_for_tampered_model(tmp_path):
    model=receiver.prepare(CONTRACT);model['initial'][0]='0'
    proposal=tmp_path/'proposal.json';proposal.write_bytes(encode(model))
    out=tmp_path/'output'
    run=subprocess.run([sys.executable,'-m','pcs.cli','transport-kernel-v1','--contract',str(EXAMPLE/'contract.json'),
        '--proposal',str(proposal),'--output',str(out)],cwd=ROOT,capture_output=True,text=True,timeout=20)
    assert run.returncode==1,run.stdout+run.stderr
    assert not json.loads((out/'report.json').read_bytes())['all_time_model_supported']
    assert 'Traceback' not in run.stderr


@pytest.mark.parametrize('timeout',[True,0,-1,181,float('nan'),float('inf')])
def test_invalid_resource_budgets_never_acquire_model_support(timeout,monkeypatch):
    monkeypatch.setattr(receiver,'_environment',lambda *a:pytest.fail('invalid budget reached compiler environment'))
    r=receiver.replay(CONTRACT,timeout=timeout)
    assert not r['accepted'] and not r['all_time_model_supported'] and r['errors']


def test_unavailable_dependency_does_not_substitute_python_pass_for_proof(monkeypatch):
    def unavailable(*args):raise ValueError('pinned Mathlib unavailable')
    monkeypatch.setattr(receiver,'_environment',unavailable)
    r=receiver.replay(CONTRACT,TRAJECTORY)
    assert r['bounded_trajectory_supported'] and not r['all_time_model_supported'] and not r['accepted']
    assert r['kernel']['status']=='UNAVAILABLE_OR_EXHAUSTED'


def test_source_substitution_before_export_rejects_before_creating_output(genuine,tmp_path,monkeypatch):
    sources=receiver._source_files();sources['PCSReal/Transport.lean']+=b'\n-- changed snapshot\n'
    monkeypatch.setattr(receiver,'_source_files',lambda:sources)
    out=tmp_path/'receipt'
    with pytest.raises(ValueError,match='sources changed'):receiver.export_evidence(out,genuine)
    assert not out.exists()


def test_truthy_nonboolean_report_cannot_grant_kernel_support(monkeypatch):
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k:{'kernel_checked':1})
    r=receiver.replay(CONTRACT)
    assert not r['all_time_model_supported'] and not r['accepted']


@pytest.fixture(scope='module')
def signed_case(tmp_path_factory):
    require_kernel()
    from pcs.signing import generate_keypair
    directory=tmp_path_factory.mktemp('transport-signed')
    project=directory/'project';shutil.copytree(EXAMPLE,project)
    private,public=directory/'private.pem',directory/'public.pem'
    fingerprint=generate_keypair(private,public)['fingerprint']
    bundle=directory/'positive.pcs.zip'
    workflow.build_bundle(project,directory/'work',bundle,private,public,
        expected_fingerprint=fingerprint,confirm_reviewed_draft=True)
    private.unlink()
    return bundle,public,fingerprint


def test_signed_receiving_stages_use_one_snapshot_when_original_zip_changes(signed_case,genuine,tmp_path,monkeypatch):
    bundle,public,fingerprint=signed_case
    original=tmp_path/'original.pcs.zip';original.write_bytes(bundle.read_bytes())
    digest=hashlib.sha256(original.read_bytes()).hexdigest()
    verify=workflow.verify_bundle
    def changing_input(snapshot,*a,**kw):
        assert Path(snapshot)!=original
        result=verify(snapshot,*a,**kw)
        original.write_bytes(b'changed after package verification; not a ZIP')
        return result
    monkeypatch.setattr(workflow,'verify_bundle',changing_input)
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k:genuine['kernel'])
    result=receiver.replay_bundle(original,public,expected_fingerprint=fingerprint)
    assert result['accepted'],result
    assert result['bundle_sha256']==digest==result['existing_workflow']['bundle_sha256']
    assert result['model']['contract_sha256']==genuine['contract_sha256']
    assert original.read_bytes().startswith(b'changed')
    assert result['base_numerical_claim']==result['base_continuum_claim']==result['base_empirical_claim']=='OPEN'


def test_verified_contract_handoff_mismatch_rejects_before_kernel(signed_case,monkeypatch):
    bundle,public,fingerprint=signed_case
    verify=workflow.verify_bundle
    def wrong_handoff(*a,**kw):
        result=verify(*a,**kw);result['domain_replay']['contract_sha256']='0'*64
        return result
    monkeypatch.setattr(workflow,'verify_bundle',wrong_handoff)
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k:pytest.fail('mismatched signed source reached kernel'))
    result=receiver.replay_bundle(bundle,public,expected_fingerprint=fingerprint)
    assert result['pcs_package_valid'] and not result['accepted'] and not result['all_time_model_supported']
    assert 'different bytes' in result['errors'][0]


def test_oversized_signed_input_is_rejected_before_authority(tmp_path,monkeypatch):
    bundle=tmp_path/'oversized.zip';bundle.write_bytes(b'1234')
    monkeypatch.setattr(receiver,'MAX_BUNDLE_BYTES',3)
    monkeypatch.setattr(workflow,'verify_bundle',lambda *a,**k:pytest.fail('oversized ZIP reached authority'))
    result=receiver.replay_bundle(bundle,None,expected_fingerprint='0'*64)
    assert not result['pcs_package_valid'] and not result['accepted']
    assert 'receiving bound' in result['errors'][0]


@pytest.mark.parametrize('component',['matrix','volume','initial','contract-digest'])
def test_current_input_model_handoff_cannot_mix_two_supported_models(component,monkeypatch):
    model=receiver.prepare(CONTRACT)
    if component=='matrix':
        n=len(model['volumes']);model['matrix']=[[str(int(i==j)) for j in range(n)] for i in range(n)]
    if component=='volume':model['volumes']=[str(2*Fraction(v)) for v in model['volumes']]
    if component=='initial':model['initial']=['0']*len(model['initial'])
    if component=='contract-digest':model['contract_sha256']='0'*64
    monkeypatch.setattr(receiver,'prepare',lambda *a:model)
    monkeypatch.setattr(receiver,'kernel_replay',lambda *a,**k:pytest.fail('mismatched model handoff reached kernel'))
    result=receiver.replay(CONTRACT,TRAJECTORY)
    assert not result['accepted'] and not result['all_time_model_supported'] and not result['model_handoff_checked']
    assert 'model handoff' in result['errors'][0]
