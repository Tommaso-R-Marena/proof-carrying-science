#!/usr/bin/env python3
"""Immutable external-source comparison; all seeds retained, no promotion."""
import argparse,gzip,hashlib,json,math,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from pcs.experimental.prover.mathlib_environment_v4 import MathlibEnvironmentV4
from pcs.experimental.prover.premise_policy_v4 import PremisePolicy
from pcs.experimental.prover.benchmark_mathlib_v4 import verify_benchmark,filter_premises

METHODS=['symbolic_structural','symbolic_lexical','untrained_graph_71','graph_71','graph_79','bag_71','bag_79','rl_71','rl_79','strong_portfolio']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

class TimedRanker:
    def __init__(self,model):self.model=model;self.seconds=0.;self.calls=0
    def rank(self,state,options):
        start=time.monotonic()
        try:return self.model.rank(state,options)
        finally:self.seconds+=time.monotonic()-start;self.calls+=1

def main():
    p=argparse.ArgumentParser();p.add_argument('--models',required=True);p.add_argument('--rl');p.add_argument('--output',required=True);args=p.parse_args()
    models=Path(args.models);out=Path(args.output)
    if out.exists():raise ValueError('Final evaluation generation immutable; choose a new directory')
    # Integrity/exposure and configuration freeze precede ANY final solve.
    integrity=verify_benchmark(Path('benchmarks/mathlib-v4'),mathlib=Path('.lake/packages/mathlib'),expected_seal='f03dd1014cee61b2f4bd62d49e730a007a7f5427ef5a191f988a7ca59409e9a4')
    trained=json.loads((models/'training-summary.json').read_text())['models']
    rl_folder=Path(args.rl) if args.rl else models
    rl=json.loads((rl_folder/'rl-summary.json').read_text())['models']
    rows={r['architecture']+'_'+str(r['seed']):{**r,'resolved_checkpoint':str(models/r['checkpoint'])} for r in trained}
    rows.update({'rl_'+str(r['seed']):{**r,'resolved_checkpoint':str(Path(r['checkpoint']) if args.rl else models/r['checkpoint'])} for r in rl})
    for row in rows.values():
        if sha(row['resolved_checkpoint'])!=row['checkpoint_sha256']:raise ValueError('model checkpoint digest changed')
    tasks=json.loads(Path('benchmarks/mathlib-v4/tasks.json').read_text())
    out.mkdir(parents=True)
    write(out/'protocol.json',{'format':'pcs-mathlib-v4-comparison-protocol','methods':METHODS,'benchmark_protocol_sha256':sha('benchmarks/mathlib-v4/protocol.json'),'environment_overlay_sha256':sha('benchmarks/mathlib-v4-environment-v1/evaluation-environment.json'),'training_protocol_sha256':sha(models/'protocol.json'),'checkpoints':rows,'budget':{'attempts':48,'depth':18,'beam':4,'premises':6,'seconds':90},'source_sha256':sha(__file__),'engine_sha256':sha('pcs/experimental/prover/mathlib_environment_v4.py'),'worker_sha256':sha('formal/PCSMathlibWorkerV4.lean'),'source_classification':'22 public external-source statements, developer-exposed, not blind or new mathematics; imported automation can transitively know target facts','selection':'All outcomes retained; no checkpoint tuning/selection/promotion; no later architecture change evaluated on this final set','cache_policy':'Transition cache cleared before every method/task; fixed resident import initialization measured separately'})
    write(out/'integrity.json',integrity)
    tick=time.monotonic();env=MathlibEnvironmentV4(timeout=12)
    construction={'wall_seconds':time.monotonic()-tick,'compiler_invocations':env.calls,'worker_requests':env.worker_requests,'catalog_from_cache':env.catalog_from_cache,'catalog_sha256':env.catalog_sha256,'catalog_entries':len(env.catalog),'cpu_seconds':env.cpu_seconds}
    kept,exclusions=filter_premises(env.catalog,tasks)
    env.excluded_names=frozenset(r['name'] for r in exclusions['rejected'])
    write(out/'premise-exclusions.json',exclusions);write(out/'construction.json',construction)
    loaded={}
    for name,row in rows.items():loaded[name]=PremisePolicy.load(row['resolved_checkpoint'],row['checkpoint_sha256'],env.catalog)
    torch.manual_seed(71);loaded['untrained_graph_71']=PremisePolicy(env.catalog,architecture='graph')
    results=[];start=time.monotonic()
    try:
        for task in tasks:
            for method in METHODS:
                env._states.clear();before_calls=env.calls;before_requests=env.worker_requests;before_cpu=env.cpu_seconds
                ranker=TimedRanker(loaded[method]) if method in loaded else None
                started=time.monotonic()
                try:
                    result=env.portfolio(task['statement']) if method=='strong_portfolio' else env.solve(task['statement'],ranker=ranker,budget=48,depth=18,beam=4,premises=6,wall=90,mode='lexical' if method=='symbolic_lexical' else 'structural')
                except (RuntimeError,ValueError) as error:
                    result={'status':'unknown','receipt':None,'error':str(error)[-2000:],'expansions':None,'pcs_authority':False}
                measured={'wall_seconds':time.monotonic()-started,'compiler_invocations':env.calls-before_calls,'structured_worker_requests':env.worker_requests-before_requests,'physical_lean_calls':env.calls-before_calls+env.worker_requests-before_requests,'cpu_seconds':env.cpu_seconds-before_cpu,'model_inference_seconds':ranker.seconds if ranker else 0.,'model_inference_calls':ranker.calls if ranker else 0,'max_child_rss_kib':env.max_child_rss_kib}
                row={'task_id':task['id'],'declaration':task['declaration'],'family':task['family'],'method':method,'result':result,'measured':measured};results.append(row)
                with gzip.open(out/'matrix.json.gz','wt') as f:json.dump(results,f)
                print(json.dumps({'task':task['id'],'method':method,'status':result['status'],'seconds':measured['wall_seconds'],'lean_calls':measured['physical_lean_calls']}),flush=True)
        solved={m:{r['task_id'] for r in results if r['method']==m and r['result']['status']=='verified'} for m in METHODS}
        totals={m:{'solved':len(solved[m]),'tasks':len(tasks),'unique_beyond_strong_portfolio':sorted(solved[m]-solved['strong_portfolio']),'wall_seconds':sum(r['measured']['wall_seconds'] for r in results if r['method']==m),'physical_lean_calls':sum(r['measured']['physical_lean_calls'] for r in results if r['method']==m)} for m in METHODS}
        write(out/'summary.json',{'format':'pcs-mathlib-generalization-v4-results','totals':totals,'comparisons':len(results),'distinct_verified_statements':len(set().union(*solved.values())),'total_wall_seconds_excluding_construction':time.monotonic()-start,'no_automatic_promotion':True,'confidence_scope':'Two seeds; small public source-selected sample, not broad generalization or mathematical novelty','production_authority':False})
    finally:env.close()

if __name__=='__main__':main()
