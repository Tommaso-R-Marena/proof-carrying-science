"""Portable, reviewable UTF-8 captures; never execute embedded source files."""
import json
from pathlib import Path

from pcs.jsonio import strict_json_loads
from .monitor import digest

FORMAT='pcs-llm-firewall-captured-evidence-v1'


def freeze(folder:Path):
    folder=Path(folder)
    names=['registration.json','protocol.json','summary.json','provider/free-account.json','provider/models.json']
    names += [p.relative_to(folder).as_posix() for p in sorted((folder/'sources').rglob('*')) if p.is_file()]
    names += [p.relative_to(folder).as_posix() for p in sorted((folder/'provider').glob('call-*/*.json'))]
    names += [p.relative_to(folder).as_posix() for p in sorted(folder.glob('m*/result.json'))]
    files={n:(folder/n).read_bytes().decode('utf-8') for n in names}
    capture=dict(format=FORMAT,files=files,sha256={n:digest(raw.encode('utf-8')) for n,raw in files.items()},
                 external_provider_authenticated=False,weight_attestation=False)
    out=folder/'captured.json'
    with out.open('x',encoding='utf-8') as f:json.dump(capture,f,indent=2,ensure_ascii=True);f.write('\n')
    return out


def load(path:Path):
    with Path(path).open('rb') as f:raw=f.read(16*1024*1024+1)
    if len(raw)>16*1024*1024:raise ValueError('Bounded capture required')
    c=strict_json_loads(raw.decode('utf-8'))
    if type(c) is not dict or set(c)!={'format','files','sha256','external_provider_authenticated','weight_attestation'} or c['format']!=FORMAT:
        raise ValueError('Exact versioned capture format required')
    files,hashes=c['files'],c['sha256']
    if type(files) is not dict or type(hashes) is not dict or set(files)!=set(hashes) or len(files)>1000:
        raise ValueError('Exact bounded capture inventory required')
    snapshot={};total=0
    for name,text in files.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or p.as_posix()!=name or type(text) is not str:
            raise ValueError('Exact relative UTF-8 capture paths required')
        b=text.encode('utf-8');total+=len(b)
        if len(b)>1024*1024 or total>16*1024*1024 or digest(b)!=hashes[name]:raise ValueError('Capture bytes changed or oversized')
        snapshot[name]=b
    return snapshot
