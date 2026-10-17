"""Fresh real-data certificate attacks, with genuine kernel refutations."""
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import argparse
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pcs import calibration_kernel_v1 as receiver
from pcs.experimental.calibration_proposer_v1 import propose
from pcs.canonical_json import canonicalize_jcs_bytes as encode
from run_experimental_calibration_v1 import groups,inputs


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    source={n:receiver.sha(b) for n,b in receiver.sources().items()}
    raw,full,_=inputs(next(iter(groups().values())))
    contract=json.loads(full);contract['models']=contract['models'][:1]
    contract['models'][0]['queries']=contract['models'][0]['queries'][:1]
    contract=encode(contract);certificate=propose(raw,contract)
    frozen={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_tree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
        'source_sha256':source,'runner_sha256':receiver.sha(Path(__file__).read_bytes()),
        'frozen_before_execution':True,'physical_source':'UCI Delft yacht hull zero, first declared model/query',
        'synthetic_corruptions_of_real_data_witnesses':True,'scientific_acceptance':False}
    (output/'PROTOCOL.json').write_bytes(encode(frozen));cases=[]
    for name in ['positive','coefficient','zero-sse','ls-dual','ls-gain','minimax-dual','minimax-gain',
                 'data-byte','rebound-data','injection','split-substitution','model-order']:
        data=raw;c=json.loads(contract);w=json.loads(certificate);m=w['models'][0]
        if name=='coefficient':m['coefficients'][0]=str(Fraction(m['coefficients'][0])+1)
        if name=='zero-sse':m['sse']='0'
        if name=='ls-dual':m['queries'][0]['weights'][0]=str(Fraction(m['queries'][0]['weights'][0])+1)
        if name=='ls-gain':m['queries'][0]['gain']='0'
        if name=='minimax-dual':m['queries'][0]['minimax']['dual'][0]=str(Fraction(m['queries'][0]['minimax']['dual'][0])+1)
        if name=='minimax-gain':m['queries'][0]['minimax']['gain']='0'
        if name in ['data-byte','rebound-data']:
            rows=data.decode().splitlines();x,y=rows[1].split(',');rows[1]=x+','+str(Fraction(y)+1)
            data=('\n'.join(rows)+'\n').encode()
            if name=='rebound-data':c['data_sha256']=receiver.sha(data)
        if name=='injection':m['sse']='0\naxiom forged : False'
        if name=='split-substitution':c['models'][0]['fit_rows']=list(range(1,14,2))
        if name=='model-order':c['models'][0]['degree']=2
        cr=encode(c);w['contract_sha256']=receiver.sha(cr);wr=encode(w)
        refuted=name in ['coefficient','zero-sse','ls-dual','ls-gain','minimax-dual','minimax-gain','rebound-data','split-substitution']
        cases.append((name,data,cr,wr,name=='positive',refuted))
    start=time.monotonic()
    def receive(case):
        name,data,c,w,accepted,refuted=case;directory=output/name;directory.mkdir()
        for filename,b in [('data.csv',data),('contract.json',c),('certificate.json',w)]:
            (directory/filename).write_bytes(b)
        p=subprocess.run([sys.executable,'-m','pcs.cli','calibration-kernel-v1',
            '--data',str(directory/'data.csv'),'--contract',str(directory/'contract.json'),
            '--certificate',str(directory/'certificate.json'),'--output',str(directory/'receiving')],
            cwd=ROOT,capture_output=True,text=True,timeout=360)
        (directory/'receiver.log').write_text(p.stdout+p.stderr)
        r=json.loads((directory/'receiving/report.json').read_bytes())
        assert r['accepted'] is accepted and p.returncode==(0 if accepted else 1),(name,r)
        assert r['scientific_acceptance'] is False
        actual=r.get('kernel',{}).get('negative_kernel_checked') is True
        assert actual is refuted,(name,r)
        if refuted:assert r['kernel']['status']=='CERTIFICATE_FALSIFIED'
        print(json.dumps({'case':name,'accepted':accepted,'kernel_refuted':actual}),flush=True)
        return {'case':name,'accepted':accepted,'kernel_refuted':actual,
                'report_sha256':receiver.sha((directory/'receiving/report.json').read_bytes())}
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(receive,cases))
    assert source=={n:receiver.sha(b) for n,b in receiver.sources().items()}
    summary={'format':'pcs-calibration-attacks-v1','passed':True,'receiving_processes':len(results),
        'accepted':sum(r['accepted'] for r in results),'expected_rejections':sum(not r['accepted'] for r in results),
        'actual_kernel_refutations':sum(r['kernel_refuted'] for r in results),'cases':results,
        'source_head':frozen['source_head'],'source_tree_dirty':frozen['source_tree_dirty'],
        'wall_seconds':round(time.monotonic()-start,6),'scientific_acceptance':False}
    (output/'SUMMARY.json').write_bytes(encode(summary))
    (output/'SHA256.json').write_bytes(encode({'files':{str(p.relative_to(output)):receiver.sha(p.read_bytes())
        for p in sorted(output.rglob('*')) if p.is_file()}}))
    print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.output)
