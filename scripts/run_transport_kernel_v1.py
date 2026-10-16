#!/usr/bin/env python3
"""Executed, synthetic transport assurance campaign; no external research input."""
from __future__ import annotations

import argparse
from fractions import Fraction
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs import transport_kernel_v1 as kernel
from pcs.canonical_json import canonicalize_jcs_bytes as encode
from run_scientific_workflow_v3 import run as signed_workflow_campaign, changed_last_row


def write(path, value):
    with path.open('xb') as f:f.write(encode(value))


def run(output):
    source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    initial_usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    sources=kernel._source_files()
    source_hashes={name:kernel.sha(raw) for name,raw in sources.items()}
    write(output/'PROTOCOL.json',{'format':'pcs-transport-kernel-campaign-v1','frozen_before_execution':True,
        'source_head':source_head,'source_tree_dirty':dirty,'source_sha256':source_hashes,
        'script_sha256':kernel.sha(Path(__file__).read_bytes()),'mathlib_revision':kernel.MATHLIB_REVISION,
        'scope':'all discrete times in declared finite matrix; no implementation/continuum/empirical theorem',
        'external_empirical_validation':False,'training':False,'spend':0,'private_keys_retained':False})
    contract=(ROOT/'examples/scientific_workflow_v3/contract.json').read_bytes()
    trajectory=(ROOT/'examples/scientific_workflow_v3/trajectory.csv').read_bytes()
    (output/'contract.json').write_bytes(contract)
    (output/'trajectory.csv').write_bytes(trajectory)
    receivers=[]
    def receive(name, options, expected, model_expected):
        destination=output/name
        command=[sys.executable,'-m','pcs.cli','transport-kernel-v1',*options,'--output',str(destination)]
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=240)
        (output/(name+'.log')).write_text(p.stdout+p.stderr)
        report=json.loads((destination/'report.json').read_bytes())
        if (p.returncode != (0 if expected else 1) or report['accepted'] is not expected
                or report['all_time_model_supported'] is not model_expected
                or report['scientific_acceptance'] is not False):
            raise RuntimeError('unexpected independent receiving outcome: '+name)
        if name.startswith('signed-') and report.get('pcs_package_valid') is not True:
            raise RuntimeError('signed attack failed package integrity instead of semantic replay: '+name)
        if name == 'raw-conservative-wrong-trajectory':
            checks={c['id']:c['outcome'] for c in report['bounded_replay']['checks']}
            if not (checks['amount_conservation'] == checks['maximum_principle'] == 'PASS'
                    and checks['step_replay'] == 'FAIL'):
                raise RuntimeError('wrong-trajectory control failed its intended independent predicates')
        receivers.append({'id':name,'expected':expected,'accepted':report['accepted'],
            'all_time_model_supported':report['all_time_model_supported'],'returncode':p.returncode,
            'report_sha256':kernel.sha((destination/'report.json').read_bytes()),
            'pcs_package_valid':report.get('pcs_package_valid'), 'scientific_acceptance':False})
    raw=['--contract',str(output/'contract.json'),'--trajectory',str(output/'trajectory.csv')]
    receive('raw-positive',raw,True,True)
    wrong=changed_last_row(trajectory,lambda row:[row[0],*('7/32' for _ in row[1:])])
    (output/'wrong-trajectory.csv').write_bytes(wrong)
    receive('raw-conservative-wrong-trajectory',['--contract',str(output/'contract.json'),
        '--trajectory',str(output/'wrong-trajectory.csv')],False,True)
    for name in ['matrix','volume','digest','boolean','proof-injection']:
        proposal=kernel.prepare(contract)
        if name=='matrix':proposal['matrix'][0][0]='1'
        if name=='volume':proposal['volumes'][0]='2'
        if name=='digest':proposal['contract_sha256']='0'*64
        if name=='boolean':proposal['matrix'][0][0]=True
        if name=='proof-injection':proposal['contract_sha256']+='\naxiom forged : False'
        file=output/(name+'-proposal.json');write(file,proposal)
        receive('proposal-'+name,raw+['--proposal',str(file)],False,False)
    unstable=json.loads(contract);unstable['time_step']='2'
    write(output/'unstable-contract.json',unstable)
    receive('CFL-rejected',['--contract',str(output/'unstable-contract.json')],False,False)
    boundary=json.loads(contract)
    boundary['cells']=[{'id':'A','volume':'1','initial_concentration':'1'},
                       {'id':'B','volume':'1','initial_concentration':'0'}]
    boundary['edges']=[{'left':'A','right':'B','conductance':'1'}]
    boundary['time_step']='1';boundary['steps']=2
    write(output/'boundary-contract.json',boundary)
    (output/'boundary-trajectory.csv').write_bytes(b'time_s,A,B\n0,1,0\n1,0,1\n2,1,0\n')
    receive('CFL-boundary-oscillation',['--contract',str(output/'boundary-contract.json'),
        '--trajectory',str(output/'boundary-trajectory.csv')],True,True)
    large=json.loads(contract)
    large['question']='Does the declared sixteen-cell discrete matrix preserve its exact invariants?'
    large['cells']=[{'id':f'Cell{i}','volume':str(Fraction(i+1,2)),
                     'initial_concentration':str(Fraction(i,15))} for i in range(16)]
    large['edges']=[{'left':f'Cell{i}','right':f'Cell{i+1}','conductance':'1/4'} for i in range(15)]
    large['time_step']='1/1024'
    write(output/'sixteen-cell-contract.json',large)
    receive('sixteen-cell-model-bound',['--contract',str(output/'sixteen-cell-contract.json')],True,True)
    # Existing signed v3 cases include real compiled dimensions and four genuine,
    # authentically re-signed attacks. The old implementation is not modified.
    base=output/'signed-v3-base'
    old=signed_workflow_campaign(base)
    public=base/'producer-public.pem';fp=old['producer_public_key_fingerprint']
    for name in ['positive','amount-leak','conservative-wrong-trajectory',
                 'producer-false-report','producer-falsified-dimensions']:
        receive('signed-'+name,['--bundle',str(base/(name+'.pcs.zip')),
            '--public-key',str(public),'--fingerprint',fp],name=='positive',name=='positive')
    false=kernel.prepare(contract)
    false['matrix'][0][0]=str(Fraction(false['matrix'][0][0])+Fraction(1,20))
    false['matrix'][0][1]=str(Fraction(false['matrix'][0][1])-Fraction(1,20))
    control=kernel.kernel_replay(false)
    write(output/'false-matrix-kernel-control.json',control)
    (output/'FalseMatrixRejected.lean').write_bytes(kernel._render(false,rejection=True))
    if control['status']!='CERTIFICATE_FALSIFIED' or not control['negative_kernel_checked'] or control['kernel_checked']:
        raise RuntimeError('false matrix certificate did not actually fail in Lean')
    if source_hashes != {name:kernel.sha(raw) for name,raw in kernel._source_files().items()}:
        raise RuntimeError('sources changed during campaign')
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    summary={'format':'pcs-transport-kernel-campaign-result-v1','passed':True,
        'source_head':source_head,'source_tree_dirty':dirty,'receivers':receivers,
        'separate_receiving_processes':len(receivers),'actual_false_matrix_kernel_rejection':True,
        'mathlib_revision':kernel.MATHLIB_REVISION,'general_theorems':len(kernel.GENERAL_THEOREMS),
        'per_model_theorems':len(kernel.REPLAY_THEOREMS),'wall_seconds':round(time.monotonic()-start,6),
        'child_cpu_seconds':usage.ru_utime+usage.ru_stime-initial_usage.ru_utime-initial_usage.ru_stime,
        'largest_child_rss_kib_linux':usage.ru_maxrss,'scientific_acceptance':False,
        'implementation_correspondence':'OPEN','continuum_accuracy':'OPEN','empirical_validity':'OPEN',
        'training':False,'external_empirical_validation':False,'private_keys_retained':False}
    write(output/'SUMMARY.json',summary)
    write(output/'SHA256.json',{'format':'pcs-transport-campaign-byte-inventory-v1',
        'external_validation':False,'files':{str(p.relative_to(output)):kernel.sha(p.read_bytes())
            for p in sorted(output.rglob('*')) if p.is_file()}})
    print(json.dumps({k:summary[k] for k in ['passed','separate_receiving_processes','wall_seconds','general_theorems','scientific_acceptance']}))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output.resolve())
