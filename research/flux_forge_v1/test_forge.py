"""Exhaustive bounded pair oracle and independent whole-model matrix replay."""
from fractions import Fraction as F
import json
import os
from pathlib import Path
import subprocess

import pytest

from pcs import scientific_workflow_v3 as workflow
from pcs.transport_trace_kernel_v1 import prepare
from research.flux_detective_v1.check import capture
from research.portable_transport_v2 import replay as lean
from .experiment import run

ROOT=Path(__file__).resolve().parents[2]


def fixtures(*args):
    return json.loads(subprocess.check_output(['node',str(Path(__file__).with_name('fixtures.mjs')),*map(str,args)],cwd=ROOT))


def test_13200_pair_transfers_against_independent_exact_energy_oracle():
    rows=fixtures('pairs');assert len(rows)==400
    checked=0
    for r in rows:
        v,w,x,y=map(F,[r['v'],r['w'],r['x'],r['y']])
        lower,upper=F(r['low']),F(r['high'])
        for tick in range(-16,17):
            t=F(tick,8);a,b=x-t/v,y+t/w
            actual=0<=a<=1 and 0<=b<=1 and v*a*a+w*b*b<=v*x*x+w*y*y
            assert actual==(lower<=t<=upper),(r,t)
            assert v*a+w*b==v*x+w*y
            delta=v*a*a+w*b*b-v*x*x-w*y*y
            assert delta==(v+w)/(v*w)*t*(t-F(r['root']))
            checked+=1
    assert checked==13200


@pytest.fixture(scope='module')
def cases():return fixtures()


def test_1296_whole_model_exports_against_independent_matrix_and_invariant_oracle(cases):
    assert len(cases)==1296
    for item in cases:
        cbytes,csv=capture(json.dumps(item['bundle']).encode());data=prepare(cbytes,csv)
        contract=workflow.load_contract(cbytes);matrix=workflow.transition_matrix(contract)
        state=[list(map(F,row)) for row in data['states']]
        assert list(map(F,data['times']))==[k*F(data['dt']) for k in range(contract['steps']+1)]
        volume=[F(c['volume']) for c in contract['cells']]
        truth=[list(map(F,data['model']['initial']))]
        for _ in range(contract['steps']):truth.append([sum(p*x for p,x in zip(row,truth[-1])) for row in matrix])
        energies=[sum(v*x*x for v,x in zip(volume,row)) for row in state]
        base_energy=sum(v*x*x for v,x in zip(volume,truth[-1]))
        mass=[sum(v*x for v,x in zip(volume,row)) for row in state]
        lo,hi=min(state[0]),max(state[0]);bounds=all(lo<=x<=hi for row in state for x in row)
        historical=all(a>=b for a,b in zip(energies,energies[1:]));mass_ok=all(x==mass[0] for x in mass)
        exact=state==truth;strong=mass_ok and bounds and historical and energies[-1]<=base_energy
        fault=None
        for k in range(contract['steps']):
            for i,row in enumerate(matrix):
                expected=sum(p*x for p,x in zip(row,state[k]))
                if fault is None and state[k+1][i]!=expected:
                    obs=state[k+1][i];fault=dict(kind='recurrence',step=k,cell=i,observed=str(obs),expected=str(expected),residual=str(obs-expected))
        assert item['analysis']==dict(mass=mass_ok,bounds=bounds,energy=historical,energies=list(map(str,energies)),amount=str(mass[0]),fault=fault)
        s=item['summary'];t=F(s['amount']);left,right=item['left'],item['right']
        assert mass_ok
        assert s['inside']==(F(s['low'])<=t<=F(s['high']))==strong==s['stronger']
        assert s['energy_delta']==str(energies[-1]-base_energy)
        assert s['exact_model']==exact==(t==0)
        assert s['invariant_impostor']==(strong and not exact)
        # Independently reconstruct both interval endpoints, not only membership.
        v,w=volume[left],volume[right];x,y=truth[-1][left],truth[-1][right]
        root=2*v*w*(x-y)/(v+w)
        assert F(s['energy_root'])==root
        assert F(s['low'])==max(min(0,root),v*(x-hi),w*(lo-y))
        assert F(s['high'])==min(max(0,root),v*(x-lo),w*(hi-y))


def controls():
    items=fixtures(20261021)
    # Diverse widths, both orientations, zero, interior, endpoint and failed bounds.
    selected=[]
    predicates=[
        lambda x:x['level']==0 and x['left']==0 and x['right']==1 and x['summary']['amount']=='0',
        lambda x:x['level']==0 and x['left']==0 and x['right']==1 and x['summary']['invariant_impostor'],
        lambda x:x['level']==1 and x['left']==1 and x['right']==0 and x['summary']['invariant_impostor'],
        lambda x:x['level']==2 and x['left']==0 and x['right']==3 and x['summary']['invariant_impostor'],
        lambda x:x['level']==3 and x['left']==0 and x['right']==4 and x['summary']['invariant_impostor'],
        lambda x:x['level']==3 and x['left']==3 and x['right']==4 and x['summary']['exact_model'],
        lambda x:x['level']==4 and not x['analysis']['bounds'],
        lambda x:x['level']==5 and x['left']==0 and x['right']==1 and x['summary']['amount']==x['summary']['high'] and x['summary']['amount']!='0',
    ]
    for predicate in predicates:selected.append(next(x for x in items if predicate(x)))
    return selected


@pytest.mark.parametrize('index,item',list(enumerate(controls())))
def test_actual_lean_replay_of_eight_constructed_controls(index,item,tmp_path):
    c,csv=capture(json.dumps(item['bundle']).encode());r=lean.replay(c,csv)
    good=item['summary']['exact_model']
    assert r['kernel_supported']==good and r['negative_kernel_checked']==(not good),r
    assert r['all_time_model_kernel_supported'] and r['sources_stable']
    assert r.get('fault')==item['analysis']['fault']
    assert not r['pcs_authority'] and not r['scientific_acceptance']
    assert all(set(a)<=lean.model.APPROVED_AXIOMS for a in r['axiom_closures'].values())
    lean.export(tmp_path/'evidence',r,c,csv)
    retained=os.environ.get('PCS_FORGE_EVIDENCE_DIR')
    if retained:lean.export(Path(retained)/f'control-{index}',r,c,csv)


def test_recorded_policy_experiment_deduplicates_inputs_and_never_overwrites(tmp_path):
    out=tmp_path/'experiment';r=run(out)
    assert r['samples']==1296 and r['unique_model_trajectory_pairs']==582
    assert r['unique_policies']=={
      'summaries':{'accepted':332,'model_violations_accepted':314},
      'stronger_energy':{'accepted':294,'model_violations_accepted':276},
      'exact_model':{'accepted':18,'model_violations_accepted':0}}
    assert not r['kernel_checked'] and not r['pcs_authority'] and not r['empirical_validation']
    before=(out/'result.json').read_bytes()
    with pytest.raises(FileExistsError):run(out)
    assert (out/'result.json').read_bytes()==before
