"""Check real-model request bindings and re-execute captured typed proposals.

These checks do not attest that an external trusted observer witnessed generation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from .replay import read,replay_trace
from .real_model import messages,parse_action,MODEL,runtime
from .environment import ToolEnvironment


def replay_pilot(directory):
    root=Path(directory);plan=read(root/'plan.json');summary=read(root/'summary.json')
    if summary['status']!='EXECUTED':raise ValueError('pilot not executed')
    binding=read(root/'backend/binding.json');expected_weight=runtime.resource(MODEL)['sha256']
    if binding['weight_snapshot_sha256']!=expected_weight:raise ValueError('weight binding mismatch')
    if binding['runtime_files']!=runtime.PINS['runtime_files'] or binding['runtime_commit']!=runtime.PINS['runtime_commit']:
        raise ValueError('runtime binding mismatch')
    count=actions=0
    for record,row in zip(plan['cases'],summary['cases'],strict=True):
        if record['id']!=row['id']:raise ValueError('case identity mismatch')
        with tempfile.TemporaryDirectory(prefix='safety-model-receiving-') as folder:
            env=ToolEnvironment(record,folder,guarded=True,max_steps=8);obs,_,_,_=env.step('inspect')
            for call in row['calls']:
                capture=root/'backend'/('call-'+str(count).zfill(3))
                request=(capture/'request.json').read_bytes();response=(capture/'response.json').read_bytes()
                provenance=read(capture/'provenance.json')
                if provenance!=call['provenance'] or provenance['call']!=count or provenance['runtime_commit']!=binding['runtime_commit'] or provenance['weight_sha256']!=expected_weight:raise ValueError('provenance mismatch')
                for name,raw in [('request',request),('response',response)]:
                    if hashlib.sha256(raw).hexdigest()!=provenance[name+'_sha256']:raise ValueError('capture digest mismatch')
                expected=json.dumps(runtime.request_body(MODEL,messages(obs)),separators=(',',':')).encode()
                if request!=expected:raise ValueError('request not bound to actual observation')
                extracted=runtime.extract(response,MODEL)
                if extracted.decode('utf-8',errors='replace')!=call['raw_model_text']:raise ValueError('recorded model text mismatch')
                try:action=parse_action(extracted)
                except ValueError:action=None
                if action!=call['action']:raise ValueError('parsed proposal mismatch')
                count+=1
                if action is None:break
                obs,_,_,_=env.step(action)
        for name,guarded in [('guard_only',True),('unguarded_same_plan',False),('guard_predictor_same_plan',True)]:
            if name in row:
                outcome=replay_trace(record,row[name]['trace'],guarded)
                if outcome['success']!=row[name]['success'] or outcome['unsafe_executions']!=row[name]['unsafe_executions']:
                    raise ValueError('pilot summary mismatch')
                actions+=outcome['actions']
    if count!=summary['actual_model_calls']:raise ValueError('model call count mismatch')
    return {'requests_bound':count,'replayed_tool_actions':actions,'authority':'NONE',
      'scope':'Capture hashes and actual tool-effect replay; not attestation of model origin or general safety'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True)
    print(json.dumps(replay_pilot(p.parse_args().directory),sort_keys=True))
if __name__=='__main__':main()
