"""Independent actual effects, not attestation that a model generated proposals."""
import argparse
import gzip
import json
import re
from pathlib import Path
import tempfile
from pcs.jsonio import strict_json_loads
from .environment import ToolEnvironment

LIMIT=128_000_000
FIELDS=('action','admitted','denied','unsafe_proposal','unsafe_execution','leak','success',
 'stage_before','stage_after','terminal','policy_sha256','model_sha256','shield_sha256',
 'files_before','files_after','error')


def read(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rb') as stream:raw=stream.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError('decoded artifact exceeds bound')
    return strict_json_loads(raw.decode('utf-8'))


def normalized_error(message):
    # Fresh receiver roots differ. Preserve exception/errno and fixed filename,
    # while treating the recorded temporary absolute directory as location metadata.
    if message is None:return None
    return re.sub(r"'(/[^']+)'",lambda m:repr(Path(m.group(1)).name),message)


def replay_trace(record,trace,guarded,initial_inspect=False):
    with tempfile.TemporaryDirectory(prefix='safety-receiving-') as directory:
        env=ToolEnvironment(record,directory,guarded=guarded,max_steps=8)
        if initial_inspect:env.step('inspect')
        for original in trace:
            expected=original.get('info',original)
            _,_,_,actual=env.step(expected['action'])
            for field in FIELDS:
                left,right=actual[field],expected[field]
                if field=='error':left,right=normalized_error(left),normalized_error(right)
                if left!=right:raise ValueError('effect replay mismatch: '+field)
        return {'actions':len(trace)+int(initial_inspect),'unsafe_executions':env.unsafe_executions,'success':env.success}


def replay_run(directory):
    root=Path(directory)
    records={r['id']:r for r in read(root/'scenarios.json')}
    training=read(root/'training.json.gz');results=read(root/'results.json.gz')
    episodes=actions=0
    for trace in training['traces']:
        replay_trace(records[trace['scenario_id']],trace['rows'],trace['guarded'])
        episodes+=1;actions+=len(trace['rows'])
    for path in sorted(root.glob('*-rl.json.gz')):
        learning=read(path)
        for episode in learning['traces']:
            outcome=replay_trace(records[episode['id']],episode['rows'],True,initial_inspect=True)
            if outcome['success']!=episode['success']:raise ValueError('RL outcome mismatch')
            episodes+=1;actions+=outcome['actions']
        for feedback in learning['counterexamples']:
            trace=feedback.get('actual_unguarded_counterfactual')
            if trace is not None:
                outcome=replay_trace(records[trace['scenario_id']],trace['rows'],False)
                episodes+=1;actions+=outcome['actions']
    for key,entry in results['experiments'].items():
        test=entry['test'];guarded=key not in ('unguarded','predictor_only')
        summary={'completed':0,'unsafe_executions':0,'denied_proposals':0,'steps':0}
        for row in test['rows']:
            actual=replay_trace(records[row['id']],row['trace'],guarded)
            if actual['success']!=row['success'] or actual['unsafe_executions']!=row['unsafe_executions']:
                raise ValueError('untrusted episode summary mismatch')
            summary['completed']+=int(actual['success']);summary['unsafe_executions']+=actual['unsafe_executions']
            summary['denied_proposals']+=sum(t['denied'] for t in row['trace']);summary['steps']+=len(row['trace'])
            episodes+=1;actions+=len(row['trace'])
        if any(summary[k]!=test[k] for k in summary):raise ValueError('untrusted aggregate mismatch')
    return {'format':'pcs-safety-jepa-independent-effects-v1','episodes':episodes,'actions':actions,
      'matched':True,'authority':'NONE','scope':'Actual fixed-policy tool-effect replay; host and neural generation remain unproved'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True)
    print(json.dumps(replay_run(p.parse_args().directory),sort_keys=True))
if __name__=='__main__':main()
