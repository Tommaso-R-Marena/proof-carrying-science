"""Same real sealed weights; syntax-only grammar leaves all eight tools available."""
import fcntl
import json
from pathlib import Path
import time

from research.llm_firewall_v1.broker import TOOLS
from research.llm_firewall_v1.monitor import digest,F_GET_SEALS,REQUIRED_SEALS
from research.local_weights_v1.runtime import LocalModel,MODELS,PINS,extract,resource


def tool_schema():
    variants=[]
    for a,name in enumerate(TOOLS):
        args={'type':'object','properties':{'text':{'type':'string','maxLength':1024}} if a in {2,3,4,6} else {},
              'required':['text'] if a in {2,3,4,6} else [],'additionalProperties':False}
        variants.append(dict(type='object',properties={'tool':{'const':name},'args':args},
                             required=['tool','args'],additionalProperties=False))
    return dict(oneOf=variants)


def body(model,messages,mode):
    if mode not in {'plain','structured'}:raise ValueError('Known format mode required')
    fmt={'type':'json_object'} if mode=='plain' else dict(type='json_schema',json_schema=dict(name='pcs_typed_intent',strict=True,schema=tool_schema()))
    return dict(model=model,messages=messages,temperature=0,seed=42,max_tokens=256,
                response_format=fmt,chat_template_kwargs={'enable_thinking':False})


class Model:
    def __init__(self,weights,model,out):
        self.engine=LocalModel(weights,model,out);self.model=model;self.out=Path(out);self.calls=0;self.mode='plain'
    def complete(self,messages):
        if self.calls>=96 or self.engine.process.poll() is not None:raise ValueError('Real model/call budget unavailable')
        if fcntl.fcntl(self.engine.fd,F_GET_SEALS)&REQUIRED_SEALS!=REQUIRED_SEALS:raise ValueError('Verified weight snapshot unavailable')
        d=body(self.model,messages,self.mode);raw=json.dumps(d,separators=(',',':')).encode()
        if len(raw)>32768:raise ValueError('Bounded prompt required')
        i=self.calls;self.calls+=1;p=self.out/f'call-{i:03d}';p.mkdir()
        (p/'request.json').write_bytes(raw);start=time.monotonic()
        response=self.engine.http('/v1/chat/completions',d);(p/'response.json').write_bytes(response)
        provenance=dict(call=i,model=self.model,mode=self.mode,weight_sha256=resource(self.model)['sha256'],
            runtime_commit=PINS['runtime_commit'],request_sha256=digest(raw),response_sha256=digest(response),
            seconds=round(time.monotonic()-start,6),usage=json.loads(response).get('usage'),remote_model_api=False)
        (p/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        return extract(response,self.model),provenance
    def close(self):self.engine.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
