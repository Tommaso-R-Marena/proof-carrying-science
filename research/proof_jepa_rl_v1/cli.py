"""Small command-line entry point for real learned proposals and Lean replay."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pcs.experimental.prover.environment import search
from pcs.jsonio import strict_json_loads
from pcs.experimental.prover.language import formalize
from .data import tasks, replay_receipt, receipt_claim_graph, verifier_identity
from .experiment import LeanEnvironment, run, write_json
from .model import ProofJEPA


def read_evidence(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(16_000_001)
    if len(raw)>16_000_000:
        raise ValueError('evidence exceeds bound')
    return strict_json_loads(raw.decode('utf-8'))


def main():
    p=argparse.ArgumentParser(description='Experimental proof search; every success is checked by Lean 4.28.0.')
    sub=p.add_subparsers(dest='command',required=True)
    train=sub.add_parser('train')
    train.add_argument('--output',required=True)
    train.add_argument('--seeds',type=int,nargs='+',default=[17,31,47])
    train.add_argument('--epochs',type=int,default=6)
    train.add_argument('--rl-episodes',type=int,default=24)
    train.add_argument('--budget',type=int,default=32)
    solve=sub.add_parser('solve')
    goal=solve.add_mutually_exclusive_group(required=True)
    goal.add_argument('--task-id'); goal.add_argument('--statement')
    solve.add_argument('--checkpoint',required=True); solve.add_argument('--sha256',required=True)
    solve.add_argument('--budget',type=int,default=32)
    solve.add_argument('--output',required=True); solve.add_argument('--cache',required=True)
    replay=sub.add_parser('replay')
    replay.add_argument('--evidence',required=True); replay.add_argument('--cache',required=True)
    args=p.parse_args()
    if args.command=='train':
        run(args.output,seeds=tuple(args.seeds),epochs=args.epochs,rl_episodes=args.rl_episodes,budget=args.budget)
        return
    if args.command=='solve':
        if Path(args.output).exists(): raise ValueError('refuse evidence overwrite')
        model=ProofJEPA.load(args.checkpoint,args.sha256)
        if args.task_id:
            record=next((r for r in tasks() if r['id']==args.task_id),None)
            if record is None: raise ValueError('unknown authored task')
        else:
            parsed=formalize(args.statement)
            if parsed['status']!='supported' or len(parsed['candidates'])!=1:
                raise ValueError('statement is outside the unambiguous supported typed language')
            record={'id':'user-statement','split':'user','family':'user', 'goal':parsed['candidates'][0]['ir'],'original_statement':args.statement}
        env=LeanEnvironment(cache=args.cache,timeout=30)
        try:
            identity=verifier_identity(env)
            result=search(env,record['goal'],model.rank,budget=args.budget,beam=4,depth=16)
            if result['status']=='verified':
                result['receipt']=replay_receipt(env,record,result['receipt'],identity)
            evidence={'format':'pcs-proof-jepa-search-v1','authority':'NONE','record':record,
                      'checkpoint_sha256':args.sha256,'verifier':identity,'result':result,
                      'claim_graph':receipt_claim_graph(record,result['receipt'])}
            write_json(args.output,evidence)
            print(json.dumps({'status':result['status'],'expansions':result['expansions'],
                              'evidence':args.output,'scientific_authority':False}))
        finally: env.close()
    else:
        evidence=read_evidence(args.evidence)
        if evidence['format']!='pcs-proof-jepa-search-v1' or evidence['authority']!='NONE':
            raise ValueError('unsupported evidence')
        receipt=evidence['result']['receipt']
        if receipt is None: raise ValueError('unknown search has no proof to replay')
        env=LeanEnvironment(cache=args.cache,timeout=30)
        try:
            fresh=replay_receipt(env,evidence['record'],receipt,evidence['verifier'])
            print(json.dumps({'status':'kernel-replayed','goal_sha256':fresh['goal_sha256'],
                              'axioms':fresh['kernel']['axioms'],'scientific_authority':False}))
        finally: env.close()
if __name__=='__main__': main()
