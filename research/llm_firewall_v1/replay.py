"""Offline independent regeneration; stored PASS flags never grant authority."""
import json
from pathlib import Path

from . import campaign
from .monitor import Monitor,digest
from .protocol import protocol
from .provider import extract,MODELS


def read(path,limit=1024*1024):
    if Path(path).is_symlink():raise ValueError('Regular captured evidence files required')
    with Path(path).open('rb') as f:raw=f.read(limit+1)
    if len(raw)>limit:raise ValueError('Bounded evidence required')
    return raw


class CapturedProvider:
    def __init__(self,snapshot):self.snapshot=snapshot;self.calls=0;self.neurons=0

    def complete(self,model,messages):
        path=f'provider/call-{self.calls:03d}/'
        req=self.snapshot[path+'request.json']
        expected=dict(messages=messages,max_completion_tokens=256,temperature=0,
                      chat_template_kwargs={'enable_thinking':False},response_format={'type':'json_object'})
        if json.loads(req)!=expected:raise ValueError('Captured request differs from reconstructed protocol/context')
        response=self.snapshot[path+'response.json'];transport=json.loads(self.snapshot[path+'transport.json'])
        if (transport['model']!=model or transport['status']!=200 or transport['request_sha256']!=digest(req)
                or transport['response_sha256']!=digest(response)):
            raise ValueError('Captured request/response binding differs')
        proposal=extract(response,model)
        usage=json.loads(response)['result']['usage']
        index=self.calls;self.calls+=1;self.neurons+=usage['neurons']
        return proposal,dict(call=index,model=model,transport=transport,provider_usage=usage)


def verify(folder:Path,out:Path):
    folder=Path(folder);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    # A self-consistent inventory is not authentication. Require reviewed sources
    # and rebuild every decision/effect/proof rather than trusting result flags.
    if folder.is_file():
        from .capture import load
        snapshot=load(folder)
    else:
        inventory=json.loads(read(folder/'SHA256.json',512*1024))
        if type(inventory) is not dict or len(inventory)>3000:raise ValueError('Bounded inventory required')
        snapshot={};total=0;root=folder.resolve()
        for name,h in inventory.items():
            p=Path(name)
            if p.is_absolute() or '..' in p.parts or p.as_posix()!=name:raise ValueError('Invalid evidence path')
            if not (folder/p).resolve().is_relative_to(root):raise ValueError('Evidence leaves captured folder')
            b=read(folder/p,16*1024*1024);total+=len(b)
            if total>64*1024*1024:raise ValueError('Aggregate evidence budget exceeded')
            if digest(b)!=h:raise ValueError('Captured artifact changed')
            snapshot[name]=b
    current=campaign.sources();registration=json.loads(snapshot['registration.json'])
    if current!=registration['source_sha256']:raise ValueError('Independently reviewed source snapshot differs')
    for name,h in current.items():
        if digest(snapshot['sources/'+name])!=h:raise ValueError('Captured source differs')
    encoded=json.dumps(protocol(),sort_keys=True,separators=(',',':')).encode()
    if snapshot['protocol.json']!=encoded or digest(encoded)!=registration['protocol_sha256']:
        raise ValueError('Protocol differs from receiving reconstruction')
    spec=protocol();provider=CapturedProvider(snapshot);monitor=Monitor(out/'monitor')
    monitor.audit_objects();cases=[];agents=[]
    try:
        for mi,model in enumerate(MODELS):
            for ci,case in enumerate(spec['cases']):
                r=campaign.one_case(out,monitor,provider,model,(mi,ci),case)
                original=json.loads(snapshot[f'm{mi}-c{ci:02d}/result.json'])
                if json.loads(json.dumps(r))!=original:raise ValueError('Reexecuted case differs from stored claims')
                cases.append(r)
            for task in spec['agent_tasks']:
                r=campaign.agent(out,monitor,provider,model,mi,task)
                original=json.loads(snapshot[f'm{mi}-agent-{task}/result.json'])
                if json.loads(json.dumps(r))!=original:raise ValueError('Reexecuted agent differs from stored claims')
                agents.append(r)
        if current!=campaign.sources():raise ValueError('Reviewed sources changed during replay')
        result=dict(format='pcs-llm-firewall-independent-replay-v1',replayed=True,cases=len(cases),agent_tasks=len(agents),
                    requests=provider.calls,kernel_checked_histories=len(cases)+len(agents),
                    guarded_violations=sum(not r['guarded_audit']['passed'] for r in cases)+sum(not a['audit']['passed'] for a in agents),
                    external_provider_authenticated=False,weight_attestation=False,production_authority=False,
                    scientific_generalization=False,agent_success=sum(a['success'] for a in agents),
                    policy_aware_unguarded_violations=sum(bool(r['baseline']['violations']) for r in cases if r['policy_aware']),
                    policy_blind_unguarded_violations=sum(bool(r['baseline']['violations']) for r in cases if not r['policy_aware']),
                    utility_success=sum(r['utility'] is True for r in cases),utility_cases=sum(r['utility'] is not None for r in cases))
        (out/'replay.json').write_text(json.dumps(result,indent=2)+'\n');return result
    finally:monitor.close()
