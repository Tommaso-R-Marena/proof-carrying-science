"""Check sealed experiment bytes, splits, metrics and safe checkpoint loading."""
import gzip,hashlib,json,tarfile
from pathlib import Path
from pcs.experimental.prover.induction_ir import digest
from pcs.experimental.prover.data import structural_fingerprint
from pcs.experimental.prover.memory_model import MemoryNetwork
from pcs.experimental.prover.memory_experiment import metrics

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    if not path.exists():path=path.with_suffix(path.suffix+'.gz')
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text())
def check():
    folder=ROOT/'research/verified-memory-v1';seal=read(folder/'EVIDENCE_SHA256.json')
    assert seal=={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and p.name!='EVIDENCE_SHA256.json'}
    tasks=read(folder/'tasks.json');protocol=read(folder/'protocol.json');assert digest(tasks)==protocol['tasks_sha256']
    sets={s:{structural_fingerprint(t['goal']) for t in tasks if t['split']==s} for s in protocol['splits']}
    assert all(not a&b for i,a in enumerate(sets.values()) for j,b in enumerate(sets.values()) if i<j)
    registry=read(folder/'registry.json');assert registry['production_authority'] is False and registry['selection_frozen_before_final'] is True
    assert digest(read(folder/'library.json'))==registry['library_sha256']
    manifest=read(folder/'source-manifest.json')
    with tarfile.open(folder/'source-overlay.tar.gz') as tar:
        members={m.name:m for m in tar if m.isfile()};assert set(members)==set(manifest)
        for name,sha in manifest.items():assert hashlib.sha256(tar.extractfile(members[name]).read()).hexdigest()==sha
    for entry in registry['models']:
        assert Path(entry['checkpoint']).name==entry['checkpoint']
        model=MemoryNetwork.load(folder/entry['checkpoint'],entry['sha256'])
        assert sum(p.numel() for p in model.parameters())==entry['parameters']
    summary=read(folder/'summary.json');evaluations=read(folder/'evaluations.json')
    policies_by_split=evaluations['splits'] if evaluations.get('format')=='pcs-streamed-evaluation-index-v1' else evaluations
    for split,policies in policies_by_split.items():
        for name,stored in policies.items():
            if type(stored) is dict:
                path=folder/stored['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==stored['sha256'];rows=read(path)
            else:rows=stored
            assert {r['id'] for r in rows}=={t['id'] for t in tasks if t['split']==split}
            assert metrics(rows)==summary['metrics'][split][name]
            for r in rows:
                assert r['result'].get('expansions',0)<=protocol['budget']
                if r['result']['status']=='verified':
                    receipt=r['result']['receipt'];assert receipt['goal_sha256']==digest(r['goal'])
                    assert set(receipt['kernel']['axioms'])<={'propext','Classical.choice','Quot.sound'}
            del rows
    training=read(folder/'training.json')
    assert all(r['weights_changed'] for name,r in training.items() if name.startswith('rl'))
    assert all('message.weight' in r['changed_parameters'] for name,r in training.items() if name.startswith('utility-'))
    replay=read(folder/'independent-final-replay.json');assert len(replay)==summary['independent_replays']
    print(json.dumps({'sealed_evidence':True,'models':len(registry['models']),'independent_replays':len(replay),
                      'scope':'Byte integrity, data separation and metric consistency; kernel replay remains a separate check.'}))
if __name__=='__main__':check()
