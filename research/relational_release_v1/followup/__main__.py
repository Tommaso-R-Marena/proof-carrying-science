import argparse,json,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from pcs.jsonio import strict_json_loads
from research.llm_firewall_v1.monitor import digest
from research.causal_firewall_v1.authority import Authority as StrictAuthority
from research.local_weights_v1.runtime import MODELS,PINS,resource
from ..authority import Authority
from ..experiment import ROOT,Model,CapturedModel,case,source_hashes,save,encode

HERE=Path(__file__).resolve().parent
FORMAT='pcs-relational-fresh-pair-capture-v1'
def sources():
    d=source_hashes()
    for p in sorted(HERE.glob('*.py')):d[str(p.relative_to(ROOT))]=digest(p.read_bytes())
    return d
def protocol():
    return dict(format='pcs-relational-fresh-pair-protocol-v1',model=MODELS[0],condition='representation-aware',counts=list(range(5)),hidden_order=[1,0],
        fresh_engine_for_every_single_request=True,prompt_changes=False,
        exploratory_after_primary_not_preregistered_or_heldout=True,
        hypothesis='Test whether primary publication-presence differences survive reversed bit order and no cross-request cache.',
        qualification='10 complete observations and equal canonical traces; observed differences measured, not required')
def pack(out):
    files={p.relative_to(out).as_posix():p.read_text() for p in sorted(out.rglob('*')) if p.is_file() and p.suffix in {'.json','.lean','.py','.log'} and p.name!='captured.json'}
    save(out/'captured.json',dict(format=FORMAT,files=files,sha256={n:digest(b.encode()) for n,b in files.items()},authenticated=False))
def load(path):
    with Path(path).open('rb') as f:raw=f.read(16*1024*1024+1)
    if len(raw)>16*1024*1024:raise ValueError('Capture budget')
    d=strict_json_loads(raw.decode())
    if type(d) is not dict or set(d)!={'format','files','sha256','authenticated'} or d['format']!=FORMAT or type(d['files']) is not dict or type(d['sha256']) is not dict or set(d['files'])!=set(d['sha256']) or len(d['files'])>1000:raise ValueError('Exact supplementary capture required')
    result={};total=0
    for n,s in d['files'].items():
        if type(n) is not str or Path(n).is_absolute() or '..' in Path(n).parts or Path(n).as_posix()!=n or type(s) is not str:raise ValueError('Capture path/type')
        b=s.encode();total+=len(b)
        if len(b)>4*1024*1024 or total>16*1024*1024 or digest(b)!=d['sha256'][n]:raise ValueError('Capture bytes changed')
        result[n]=b
    return result
def summary(rs):
    pairs=[]
    for count in range(5):
        a,b=[next(r for r in rs if r['count']==count and r['hidden']==h) for h in [0,1]]
        pairs.append(dict(count=count,truth_trace_differs=a['truth_public']!=b['truth_public'],
            canonical_trace_equal=a['canonical_public']==b['canonical_public'],
            h0_valid=a['model_claim_correct'],h1_valid=b['model_claim_correct'],
            h0_trace=a['truth_public'],h1_trace=b['truth_public']))
    return dict(complete=len(rs)==10 and all(r['canonical_trace_equal'] for r in pairs),requests=len(rs),pairs=pairs,
        differing_truth_pairs=sum(r['truth_trace_differs'] for r in pairs),model_correct=sum(r['model_claim_correct'] for r in rs),
        canonical_utility=sum(r['canonical_utility'] for r in rs),fresh_engines=10,posthoc_exploratory=True)
def execute(out,weights=None,capture=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);frozen=sources();rs=[];snapshot=load(capture) if capture else None
    if snapshot is None:
        save(out/'registration.json',dict(utc=datetime.now(timezone.utc).isoformat(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256=frozen,protocol_sha256=digest(encode(protocol()))))
        (out/'protocol.json').write_bytes(encode(protocol()))
        for n in frozen:
            p=out/'sources'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    else:
        reg=json.loads(snapshot['registration.json'])
        if reg['source_sha256']!=frozen or snapshot['protocol.json']!=encode(protocol()) or digest(snapshot['protocol.json'])!=reg['protocol_sha256']:raise ValueError('Supplementary source/protocol differs')
        for n,h in frozen.items():
            if digest(snapshot['sources/'+n])!=h:raise ValueError('Supplementary embedded source differs')
    a=Authority(out/'authority');strict=StrictAuthority(out/'strict-authority')
    try:
        a.audit_objects();strict.audit_objects()
        for count in range(5):
            for hidden in [1,0]:
                prefix=f'engine-n{count}-h{hidden}'
                if snapshot is None:
                    with Model(weights,MODELS[0],out/prefix) as provider:r=case(out,a,strict,provider,0,'representation-aware',count,hidden)
                else:
                    b=json.loads(snapshot[prefix+'/binding.json'])
                    if b['weights']!=resource(MODELS[0]) or b['seals']!=15 or b['runtime_files']!=PINS['runtime_files'] or not b['weight_mappings']:raise ValueError('Supplementary weight binding differs')
                    provider=CapturedModel(snapshot,prefix,MODELS[0]);r=case(out,a,strict,provider,0,'representation-aware',count,hidden)
                    if json.loads(json.dumps(r))!=json.loads(snapshot[f'm0-representation-aware-n{count}-h{hidden}/result.json']):raise ValueError('Supplementary replay differs')
                rs.append(r)
        if sources()!=frozen:raise ValueError('Supplementary source changed')
        result=summary(rs)
        if snapshot is not None:result.update(replayed=True,new_neural_inference=False,weight_binding_authenticated=False)
        save(out/'summary.json',result)
        if snapshot is None:pack(out)
        return result
    finally:a.close();strict.close()
def main():
    p=argparse.ArgumentParser('Exploratory reversed-order fresh-engine falsification');s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('evaluate');q.add_argument('weights',type=Path);q.add_argument('out',type=Path)
    q=s.add_parser('replay');q.add_argument('capture',type=Path);q.add_argument('out',type=Path)
    a=p.parse_args();r=execute(a.out,weights=a.weights) if a.cmd=='evaluate' else execute(a.out,capture=a.capture)
    print(json.dumps(r));return 0 if r['complete'] else 20
if __name__=='__main__':raise SystemExit(main())
