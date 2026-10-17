"""Frozen, first-party finite-trace receiving campaign; no training or empirical data."""
from pathlib import Path
import argparse
from fractions import Fraction
import hashlib
import json
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs import transport_trace_kernel_v1 as trace
from pcs import transport_kernel_v1 as matrix
from pcs.canonical_json import canonicalize_jcs_bytes as encode


def run(output,signed_base):
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    frozen={n:matrix.sha(raw) for n,raw in trace.sources().items()}
    output.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        with (output/name).open('xb') as f:f.write(encode(value))
    write('PROTOCOL.json',{'format':'pcs-transport-trace-campaign-v1','source_head':head,
        'source_tree_dirty':dirty,'frozen_before_execution':True,'source_sha256':frozen,
        'script_sha256':matrix.sha(Path(__file__).read_bytes()),
        'signed_source_files':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:matrix.sha(p.read_bytes()) for p in [signed_base/'producer-public.pem',signed_base/'positive.pcs.zip',signed_base/'producer-false-report.pcs.zip',signed_base/'conservative-wrong-trajectory.pcs.zip']},
        'synthetic':True,'training':False,
        'empirical_validation':False,'spend':0})
    start=time.monotonic();rows=[]
    contract=(ROOT/'examples/scientific_workflow_v3/contract.json').read_bytes()
    csv=(ROOT/'examples/scientific_workflow_v3/trajectory.csv').read_bytes()
    (output/'contract.json').write_bytes(contract);(output/'trajectory.csv').write_bytes(csv)
    def receive(name,options,accepted,negative=False,signed=False):
        destination=output/name
        command=[sys.executable,'-m','pcs.cli','transport-trace-kernel-v1',*options,'--output',str(destination)]
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=420)
        (output/(name+'.log')).write_text(p.stdout+p.stderr)
        result=json.loads((destination/'report.json').read_bytes())
        assert result['accepted'] is accepted and p.returncode==(0 if accepted else 1),(name,result)
        assert result['scientific_acceptance'] is False
        if accepted:
            assert result['bounded_trajectory_kernel_supported'] is True
            assert set(result['kernel']['kernel_theorems'])==set(matrix.GENERAL_THEOREMS+trace.GENERAL+matrix.REPLAY_THEOREMS+trace.LITERAL)
        if negative:
            assert result['all_time_model_supported'] is True
            assert result['kernel']['status']=='TRACE_FALSIFIED' and result['kernel']['negative_kernel_checked'] is True
        if signed:assert result['pcs_package_valid'] is True
        rows.append({'case':name,'accepted':accepted,'actual_trace_refutation':negative,
            'pcs_package_valid':result.get('pcs_package_valid'),'report_sha256':matrix.sha((destination/'report.json').read_bytes())})
    raw=['--contract',str(output/'contract.json'),'--trajectory',str(output/'trajectory.csv')]
    receive('raw-positive',raw,True)
    for name in ['step','time','initial']:
        lines=csv.decode().splitlines();index=1 if name=='initial' else len(lines)-1
        row=lines[index].split(',')
        if name=='step':row[1:]=['7/32']*(len(row)-1)
        if name=='time':row[0]='999'
        if name=='initial':row[1]='0'
        lines[index]=','.join(row);path=output/('wrong-'+name+'.csv');path.write_bytes(('\n'.join(lines)+'\n').encode())
        receive('wrong-'+name,['--contract',str(output/'contract.json'),'--trajectory',str(path)],False,negative=True)
    (output/'bad-header.csv').write_bytes(b'time_s,unknown\n0,0\n')
    receive('bad-header',['--contract',str(output/'contract.json'),'--trajectory',str(output/'bad-header.csv')],False)
    boundary=json.loads(contract)
    boundary['cells']=[{'id':'A','volume':'1','initial_concentration':'1'},{'id':'B','volume':'1','initial_concentration':'0'}]
    boundary['edges']=[{'left':'A','right':'B','conductance':'1'}];boundary['steps']=64;boundary['time_step']='1'
    write('64-contract.json',boundary)
    (output/'64.csv').write_text('time_s,A,B\n'+''.join(f'{k},{1-k%2},{k%2}\n' for k in range(65)))
    receive('64-step-oscillation',['--contract',str(output/'64-contract.json'),'--trajectory',str(output/'64.csv')],True)
    large=json.loads(contract)
    large['cells']=[{'id':f'C{i}','volume':str(Fraction(i+1,2)),'initial_concentration':'1/4'} for i in range(16)]
    large['edges']=[{'left':f'C{i}','right':f'C{i+1}','conductance':'1/4'} for i in range(15)]
    large['time_step']='1/1024';large['steps']=1
    write('16-contract.json',large)
    (output/'16.csv').write_text('time_s,'+','.join(f'C{i}' for i in range(16))+'\n0,'+','.join(['1/4']*16)+'\n1/1024,'+','.join(['1/4']*16)+'\n')
    receive('16-cell-trace',['--contract',str(output/'16-contract.json'),'--trajectory',str(output/'16.csv')],True)
    fp=json.loads((signed_base/'SUMMARY.json').read_bytes())['producer_public_key_fingerprint']
    for name in ['positive','producer-false-report','conservative-wrong-trajectory']:
        receive('signed-'+name,['--bundle',str(signed_base/(name+'.pcs.zip')),'--public-key',str(signed_base/'producer-public.pem'),
            '--fingerprint',fp],name=='positive',signed=True)
    assert frozen=={n:matrix.sha(raw) for n,raw in trace.sources().items()}
    summary={'format':'pcs-transport-trace-campaign-result-v1','passed':True,'source_head':head,
        'source_tree_dirty':dirty,'receivers':rows,'receiving_processes':len(rows),
        'accepted':sum(r['accepted'] for r in rows),'expected_rejections':sum(not r['accepted'] for r in rows),
        'actual_trace_refutations':sum(r['actual_trace_refutation'] for r in rows),
        'wall_seconds':round(time.monotonic()-start,6),'child_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'scientific_acceptance':False,'implementation_correspondence':'OPEN','continuum_accuracy':'OPEN','empirical_validity':'OPEN'}
    write('SUMMARY.json',summary)
    write('SHA256.json',{'files':{str(p.relative_to(output)):matrix.sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}})
    print(json.dumps({k:summary[k] for k in ['passed','receiving_processes','accepted','expected_rejections','actual_trace_refutations','wall_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--signed-base',type=Path,required=True);a=p.parse_args();run(a.output,a.signed_base)
