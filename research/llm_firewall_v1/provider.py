"""Bounded live inference with configured Cloudflare credentials; no deployments.

The provider's model identity is an observation, not attestation of weight bytes.
Only synthetic public research inputs may be submitted by this harness.
"""
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import time
import urllib.request
import urllib.error

from .monitor import digest

MODELS=('@cf/nvidia/nemotron-3-120b-a12b','@cf/qwen/qwen3.8-27b')


def extract(raw:bytes,model:str):
    r=json.loads(raw)
    if r.get('success') is not True:raise ValueError('Provider did not report success')
    result=r['result']
    if result.get('model')!=model:raise ValueError('Provider model identifier mismatch')
    choices=result.get('choices')
    if type(choices) is not list or len(choices)!=1 or choices[0].get('finish_reason')!='stop':
        raise ValueError('One complete, nontruncated provider response required')
    message=choices[0]['message']
    if message.get('tool_calls') or message.get('function_call') or message.get('refusal'):
        raise ValueError('Parallel calls/refusals are not executable JSON proposals')
    content=message.get('content')
    if type(content) is not str or len(content.encode())>4096:raise ValueError('Bounded text completion required')
    return content.encode()


class Provider:
    def __init__(self,out:Path):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.account=os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        self.token=os.environ.get('CLOUDFLARE_API_TOKEN')
        if not self.account or not self.token:raise ValueError('Existing configured Cloudflare identity required')
        self.base='https://api.cloudflare.com/client/v4/accounts/'+self.account
        self.calls=0;self.neurons=0
        # No subscription changes or inference on a potentially paid account.
        status,_,raw=self._http('/subscriptions',None)
        r=json.loads(raw)
        if status!=200 or r.get('success') is not True or r.get('result')!=[]:
            raise ValueError('Free-only research requires positively observed absence of paid subscriptions')
        self.preflight=dict(checked_utc=datetime.now(timezone.utc).isoformat(),
                            subscriptions_count=0,paid_subscription_present=False,
                            daily_free_neurons=10000,upgrade_or_deployment=False)
        (self.out/'free-account.json').write_text(json.dumps(self.preflight,indent=2)+'\n')
        status,_,raw=self._http('/ai/models/search?per_page=100&task=Text%20Generation',None)
        catalog=json.loads(raw)
        if status!=200 or catalog.get('success') is not True:raise ValueError('Model catalog unavailable')
        self.catalog=[m for m in catalog['result'] if m['name'] in MODELS]
        if len(self.catalog)!=len(MODELS) or any(any(p['property_id']=='require_workers_paid' and p['value']=='true' for p in m['properties']) for m in self.catalog):
            raise ValueError('Exact free-eligible model catalog required')
        (self.out/'models.json').write_text(json.dumps(self.catalog,indent=2)+'\n')

    def _http(self,path,body):
        req=urllib.request.Request(self.base+path,data=body,headers={
            'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=60) as r:
                raw=r.read(1024*1024+1);status=r.status
                headers={k:r.headers[k] for k in ['Date','Content-Type','Cf-Ray'] if k in r.headers}
        except urllib.error.HTTPError as e:
            raw=e.read(1024*1024+1);status=e.code;headers={}
        if len(raw)>1024*1024:raise ValueError('Provider response exceeds capture budget')
        return status,headers,raw

    def complete(self,model,messages):
        if model not in MODELS or self.calls>=128 or self.neurons>=8000:
            raise ValueError('Model/call/free-neuron research budget exhausted')
        body=dict(messages=messages,max_completion_tokens=256,temperature=0,
                  chat_template_kwargs={'enable_thinking':False},response_format={'type':'json_object'})
        raw=json.dumps(body,separators=(',',':'),ensure_ascii=True).encode()
        if len(raw)>32768:raise ValueError('Prompt budget exceeded')
        index=self.calls;self.calls+=1;folder=self.out/f'call-{index:03d}';folder.mkdir(exist_ok=False)
        (folder/'request.json').write_bytes(raw)
        start=time.monotonic()
        status,headers,response=self._http('/ai/run/'+model,raw)
        (folder/'response.json').write_bytes(response)
        transport=dict(model=model,status=status,headers=headers,
                       requested_utc=datetime.now(timezone.utc).isoformat(),seconds=round(time.monotonic()-start,6),
                       request_sha256=digest(raw),response_sha256=digest(response),weight_attestation=False)
        (folder/'transport.json').write_text(json.dumps(transport,indent=2)+'\n')
        if status!=200:raise ValueError('Inference unavailable; raw error retained, no success invented')
        r=json.loads(response)
        neurons=r.get('result',{}).get('usage',{}).get('neurons')
        if type(neurons) not in {int,float} or not math.isfinite(neurons) or neurons<0:raise ValueError('Measured provider usage required')
        self.neurons+=neurons
        return extract(response,model),dict(call=index,model=model,transport=transport,
                                           provider_usage=r['result']['usage'])
