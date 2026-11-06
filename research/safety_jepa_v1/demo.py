"""Run one synthetic guarded workflow; no real files or services are targeted."""
import argparse
import json
from pathlib import Path
from .environment import ToolEnvironment
from .experiment import choose,safe_next,write
from .model import SafetyJEPA
from .scenarios import scenarios


def run(output,scenario_id=None,policy='guards_only',checkpoint=None,expected_sha=None,threshold=.5):
    if policy not in ('guards_only','deterministic','supervised','jepa','rl','jepa_rl','transferred','proof_guided'):
        raise ValueError('unsupported research proposer')
    record=next((r for r in scenarios() if r['id']==scenario_id),None) if scenario_id else next(r for r in scenarios() if r['split']=='test')
    if record is None:raise ValueError('unknown authored scenario')
    model=None
    if policy not in ('guards_only','deterministic'):
        if not checkpoint or not expected_sha:raise ValueError('checkpoint and exact SHA256 required')
        model=SafetyJEPA.load(checkpoint,expected_sha)
    root=Path(output)
    if root.exists():raise ValueError('refuse demo overwrite')
    root.mkdir(parents=True)
    env=ToolEnvironment(record,root/'synthetic-files',guarded=True,max_steps=8)
    env.step('inspect');cursor=1
    while not env.done:
        obs=env.observe();remaining=record['attack_sequence'][cursor:]
        proposed=remaining[0] if remaining else safe_next(obs)
        if policy=='deterministic':action=safe_next(obs)
        elif policy=='guards_only':action=proposed
        else:
            try:action,_=choose(model,obs,policy,proposed,remaining,threshold)
            except (ValueError,RuntimeError,OSError):action=safe_next(obs)
        env.step(action);cursor+=1
    summary={'scenario':record['id'],'proposer':policy,'task_completed':env.success,
        'unsafe_executions':env.unsafe_executions,'refused_proposals':sum(t['denied'] for t in env.trace),
        'actions':env.steps,'trace':env.trace,'synthetic_files_only':True,'authority':'NONE'}
    write(root/'result.json',summary);return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--scenario');p.add_argument('--policy',default='guards_only')
    p.add_argument('--checkpoint');p.add_argument('--sha256');a=p.parse_args()
    result=run(a.output,a.scenario,a.policy,a.checkpoint,a.sha256)
    print(json.dumps({k:v for k,v in result.items() if k!='trace'},sort_keys=True))
if __name__=='__main__':main()
