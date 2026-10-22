from copy import deepcopy
from fractions import Fraction as F
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import pytest

from pcs.transport_trace_kernel_v1 import prepare
from research.flux_detective_v1.check import capture
from research.portable_transport_v2 import replay as authority
from .audit import pinned_tool
from .server import ASSET_ROOT,ASSETS,create_server

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def server(tmp_path):
    for name in ASSETS:shutil.copyfile(ASSET_ROOT/name,tmp_path/name)
    http=create_server(0,asset_root=tmp_path);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    yield http,tmp_path
    http.shutdown();http.server_close();thread.join(5)

def request(server,path,*,host=None,method='GET'):
    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    c.request(method,path,headers={} if host is None else {'Host':host});r=c.getresponse();data=r.read();result=(r.status,dict(r.getheaders()),data);c.close();return result

def test_frozen_asset_manifest_headers_and_no_verification_api(server):
    http,_=server;status,headers,body=request(http,'/manifest.json');assert status==200
    m=json.loads(body);assert not m['kernel_checked'] and not m['pcs_authority']
    assert set(m['files'])==set(ASSETS)
    assert "connect-src 'none'" in headers['Content-Security-Policy'] and headers['Cache-Control']=='no-store'
    for name,item in m['files'].items():
        status,_,data=request(http,'/'+name);assert status==200 and len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']

def test_serving_uses_the_captured_bytes_after_path_changes(server):
    http,path=server;before=request(http,'/engine.mjs')[2];(path/'engine.mjs').write_text('changed after capture')
    assert request(http,'/engine.mjs')[2]==before
    assert request(http,'/engine.mjs',method='HEAD')[2]==b''

def test_paths_rebinding_and_writes_refused(server):
    http,_=server
    for path in ['/../pyproject.toml','/.git/config','/%2e%2e/secret','/test_inspector.mjs','//other/path']:
        assert request(http,path)[0]==404
    assert request(http,'/',host='attacker.example')[0]==403
    assert request(http,'/',method='POST')[0]==405

def test_doctor_never_claims_a_kernel_result_without_lean():
    env=dict(os.environ,PATH='')
    p=subprocess.run([sys.executable,'-m','research.trace_lab_v1','doctor'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=10)
    assert p.returncode==0;p=json.loads(p.stdout)
    assert p['lean_path'] is None and p['lean_version'] is None and not p['kernel_checked'] and not p['gameplay_requires_lean']

def test_binary_substitution_refused_before_any_verdict(tmp_path):
    fake=tmp_path/'pretend-tool';fake.write_bytes(b'Lean version 4.28.0')
    for name in ['lean','leanchecker']:
        with pytest.raises(ValueError):pinned_tool(name,fake)

def node_json(path,*args):return json.loads(subprocess.check_output(['node',str(ROOT/path),*map(str,args)],cwd=ROOT))

@pytest.fixture(scope='module')
def cases():
    original=node_json('research/flux_detective_v1/fixtures.mjs',0,1,4294967295,20261021,*range(1000,1064))
    forge=node_json('research/flux_forge_v1/fixtures.mjs')
    return [x['bundle'] for x in original+forge]

def inspect_many(raws):
    p=subprocess.run(['node',str(Path(__file__).with_name('inspect_batch.mjs'))],input=json.dumps(raws),text=True,capture_output=True,cwd=ROOT,timeout=60)
    assert p.returncode==0,p.stderr;return json.loads(p.stdout)

def oracle(bundle):
    c,csv=capture(json.dumps(bundle).encode());d=prepare(c,csv)
    states=[[F(x) for x in row] for row in d['states']];volumes=list(map(F,d['model']['volumes']));initial=list(map(F,d['model']['initial']))
    amount=lambda row:sum(v*x for v,x in zip(volumes,row))
    energy=lambda row:sum(v*x*x for v,x in zip(volumes,row))
    fault=authority.find_fault(d)
    return d,fault,dict(mass=all(amount(row)==amount(initial) for row in states),bounds=all(min(initial)<=x<=max(initial) for row in states for x in row),historical_energy=all(energy(a)>=energy(b) for a,b in zip(states,states[1:])),declared_amount=str(amount(initial)),final_amount=str(amount(states[-1])),final_energy=str(energy(states[-1])))

def test_all_2520_imports_match_independent_exact_python_oracle(cases):
    assert len(cases)==2520
    results=inspect_many([json.dumps(b) for b in cases]);assert len(results)==2520
    for b,packet in zip(cases,results):
        assert 'error' not in packet,packet;r=packet['result'];d,fault,summaries=oracle(b)
        assert r['states']==d['states'] and r['times']==d['times'] and r['steps']==d['steps']
        assert r['fault']==fault and r['summaries']==summaries
        assert r['status']==('BROWSER_MODEL_MATCH' if fault is None else 'BROWSER_MODEL_MISMATCH')
        assert not r['kernel_checked'] and not r['pcs_authority'] and not r['empirical_validation']

def positive(cases):return next(b for b in cases[:3] if oracle(b)[1] is None)

def test_aliases_initial_time_and_recurrence_faults_match_receiver(cases):
    base=positive(cases);variants=[]
    for kind in ['initial','recurrence','time']:
        b=deepcopy(base);lines=b['trajectory'].strip().split('\n');k=1 if kind=='initial' else len(lines)-1;row=lines[k].split(',');row[0 if kind=='time' else 1]='100';lines[k]=','.join(row);b['trajectory']='\n'.join(lines)+'\n';variants.append(b)
    aliases=deepcopy(base);aliases['contract']['time_step']='25e-2';aliases['contract']['cells'][0]['initial_concentration']='01.00';aliases['contract']['cells'][1]['initial_concentration']='-0';aliases['trajectory']=aliases['trajectory'].replace('\n','\r\n');variants.append(aliases)
    for b,p in zip(variants,inspect_many([json.dumps(b) for b in variants])):
        assert p['result']['fault']==oracle(b)[1]

def test_quoted_csv_browser_subset_does_not_weaken_the_receiver(cases):
    b=deepcopy(positive(cases));b['trajectory']=b['trajectory'].replace('time_s','"time_s"')
    assert oracle(b)[1] is None
    assert 'Quoted CSV' in inspect_many([json.dumps(b)])[0]['error']

@pytest.mark.parametrize('good',[True,False])
def test_inspected_captured_case_is_independently_replayed_by_real_lean(good,cases,tmp_path):
    b=next(b for b in cases[:3] if (oracle(b)[1] is None)==good)
    raw=json.dumps(b);browser=inspect_many([raw])[0]['result'];c,csv=capture(raw.encode());r=authority.replay(c,csv)
    assert browser['fault']==r.get('fault') and not browser['kernel_checked']
    assert r['kernel_supported']==good and r['negative_kernel_checked']==(not good),r
    assert r['all_time_model_kernel_supported'] and r['sources_stable'] and not r['pcs_authority'] and not r['scientific_acceptance']
    assert all(set(a)<=authority.model.APPROVED_AXIOMS for a in r['axiom_closures'].values())
    authority.export(tmp_path/'evidence',r,c,csv)
    out=os.environ.get('PCS_LAB_EVIDENCE_DIR')
    if out:authority.export(Path(out)/('match' if good else 'mismatch'),r,c,csv)
