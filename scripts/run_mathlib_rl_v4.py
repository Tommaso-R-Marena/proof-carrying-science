#!/usr/bin/env python3
"""Fault-contained real sequential RL; immutable protocol and episode checkpoints."""
import argparse,gzip,hashlib,json,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pcs.experimental.prover.mathlib_environment_v4 import MathlibEnvironmentV4
from pcs.experimental.prover.premise_policy_v4 import PremisePolicy,save_training_checkpoint
from pcs.experimental.prover.premise_learning_v4 import MathlibRLEnvironment,actor_critic

def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--models',required=True);p.add_argument('--output',required=True);a=p.parse_args();models=Path(a.models);out=Path(a.output)
    if out.exists():raise ValueError('New immutable RL generation required')
    supervised=json.loads((models/'training-summary.json').read_text())['models']
    episodes=json.load(gzip.open(models/'checked-training.json.gz','rt'));catalog=json.load(gzip.open(models/'catalog.json.gz','rt'))
    out.mkdir(parents=True)
    write(out/'protocol.json',{'format':'pcs-mathlib-sequential-recovery-v4','episodes_per_seed':8,'seeds':[71,79],'sampling_seed_offset':100,'learning_rate':.0005,'gamma':.97,'entropy':.002,'max_steps':16,'selection':'all seeds kept; no final benchmark read or checkpoint promotion','supervised_protocol_sha256':hashlib.sha256((models/'protocol.json').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path('pcs/experimental/prover/premise_learning_v4.py').read_bytes()).hexdigest(),'failure_handling':'kernel/replay failures yield nonpositive terminal reward before gradients; every completed episode saves exact model, Adam and RNG checkpoint','previous_failure':'original extra kernel replay timeout retained under supervised experiment logs; no final evaluation outcomes used'})
    tasks=[{'id':e['id'],'split':'train','statement':e['statement']} for e in episodes]
    env=MathlibEnvironmentV4();rows=[]
    try:
        for seed in [71,79]:
            r=next(r for r in supervised if r['architecture']=='graph' and r['seed']==seed)
            model=PremisePolicy.load(models/r['checkpoint'],r['checkpoint_sha256'],catalog)
            before=(env.calls,env.worker_requests,env.cpu_seconds);started=time.monotonic()
            def persist(model,optimizer,results):
                save_training_checkpoint(out/f'graph-rl-{seed}-episode-{len(results):02}.json',model,optimizer,{'episodes_completed':len(results),'protocol_sha256':hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest()})
                with gzip.open(out/f'partial-trajectories-{seed}.json.gz','wt') as f:json.dump(results,f)
                print(json.dumps({'seed':seed,'episode':len(results),'status':results[-1]['status']}),flush=True)
            optimizer,stats=actor_critic(model,MathlibRLEnvironment(env,max_steps=16),tasks,episodes=8,seed=seed+100,on_episode=persist)
            path=out/f'graph-rl-{seed}.json';sha=model.save(path,{'experimental':True,'supervised_checkpoint_sha256':r['checkpoint_sha256'],'protocol_sha256':hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest(),'production_authority':False})
            with gzip.open(out/f'rl-trajectories-{seed}.json.gz','wt') as f:json.dump(stats,f)
            row={'seed':seed,'checkpoint':str(path),'checkpoint_sha256':sha,'weights_changed':stats['weights_changed'],'episodes':len(stats['episodes']),'verified_episodes':sum(e['status']=='verified' for e in stats['episodes']),'compiler_invocations':env.calls-before[0],'structured_worker_requests':env.worker_requests-before[1],'cpu_seconds':env.cpu_seconds-before[2],'wall_seconds':time.monotonic()-started}
            rows.append(row);write(out/'rl-summary.json',{'models':rows,'automatic_promotion':False})
    finally:env.close()
if __name__=='__main__':main()
