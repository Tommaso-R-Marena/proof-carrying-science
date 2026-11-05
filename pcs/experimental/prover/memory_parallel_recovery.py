"""Three isolated CPU evaluation workers; fixed checkpoints, no reselection."""
import argparse,concurrent.futures,gc,hashlib,json,subprocess,sys,time
from pathlib import Path
from .memory_evaluation_recovery import read
from .memory_experiment import write
from .memory_cost import MeasuredMemoryEnvironment
from .induction_ir import digest

def run(folder,logs,cache,logged_metrics):
    folder=Path(folder);logs=Path(logs);cache=Path(cache);logs.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();registry_bytes=(folder/'registry.json').read_bytes();registry=json.loads(registry_bytes);logged=read(Path(logged_metrics))
    p=read(folder/'protocol.json');tasks=read(folder/'tasks.json')
    if digest(tasks)!=p['tasks_sha256'] or (folder/'summary.json').exists():raise ValueError('frozen inputs or completed recovery')
    index=read(folder/'evaluation-recovery-journal.json');names=[*logged['selection']]
    work=[(split,name) for split in ['selection','final'] for name in names if name not in index[split]]
    def job(pair):
        split,name=pair;log=logs/(split+'-'+name+'.log')
        with log.open('w') as output:
            subprocess.run([sys.executable,'-u','-m','pcs.experimental.prover.memory_evaluation_worker','--output',str(folder),
                '--split',split,'--policy',name,'--cache',str(cache/(split+'-'+name))],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=1800)
        receipt=read(folder/'evaluations'/split/(name+'.worker.json'))
        if receipt['frozen_registry_sha256']!=hashlib.sha256(registry_bytes).hexdigest():raise ValueError('worker selected a different checkpoint')
        path=folder/receipt['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:raise ValueError('worker artifact digest')
        old=logged[split][name];m=receipt['metrics']
        return split,name,{**receipt,'matches_original_verified_count':m['verified']==old['verified'],
            'matches_original_candidate_count':m['expansions']==old['expansions'],'original_logged_metrics':old}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(job,pair) for pair in work]
        for f in concurrent.futures.as_completed(futures):
            split,name,result=f.result();index[split][name]=result;write(folder/'evaluation-recovery-journal.json',index)
            print(split,name,result['metrics'],'independent archive complete',flush=True)
    if (folder/'registry.json').read_bytes()!=registry_bytes:raise ValueError('frozen selection changed')
    write(folder/'evaluations.json',{'format':'pcs-streamed-evaluation-index-v1','splits':index})
    replay=[];replay_calls=0;heldout=[t for t in tasks if t['split']=='final']
    for name in [registry['selected_local_experiment'],'selected_memory_structural','grounded_std_structural']:
        rows=read(folder/index['final'][name]['path'])
        for row in rows:
            if row['result']['status']!='verified':continue
            receipt=row['result']['receipt'];env=MeasuredMemoryEnvironment(receipt['library'],heldout=heldout,cache=cache/'independent-replay',timeout=30)
            try:
                fresh=env.verify(row['goal'],receipt['actions'])
                for key in ['proof','goal_sha256','library_sha256','primitive_catalog_sha256','memory_source_sha256','library_declarations','lean']:
                    if fresh.get(key)!=receipt.get(key):raise ValueError('fresh replay binding mismatch')
                replay_calls+=env.actual_calls
            finally:env.close()
            replay.append({'policy':name,'task_id':row['id'],'receipt_sha256':digest(fresh),'axioms':fresh['kernel']['axioms']})
        del rows;gc.collect()
    write(folder/'independent-final-replay.json',replay)
    summary={'metrics':{s:{n:e['metrics'] for n,e in entries.items()} for s,entries in index.items()},
        'selected':registry['selected_local_experiment'],'pool_size':len(read(folder/'candidate-pool.json')),
        'memory_size':len(read(folder/'library.json')['entries']),'trainable_parameters':{e['id']:e['parameters'] for e in registry['models']},
        'total_wall_seconds':time.monotonic()-start,'all_actual_Lean_calls':sum(e.get('actual_Lean_calls_including_construction',e['metrics']['lean_calls']) for entries in index.values() for e in entries.values())+replay_calls,
        'independent_replay_calls':replay_calls,'independent_replays':len(replay),'CPU_threads':2,'torch':__import__('torch').__version__,
        'gpu_used':False,'financial_spend':0,'resource_scope':'Recorded recovery policy calls and fresh replay only. Early sequential recovery construction and failed original-run aggregate costs are unavailable; no full-cycle total claimed.',
        'parallel_workers':3,'final_evaluation_repeated_for_archival_recovery':True,'checkpoint_selection_unchanged':True,
        'all_original_solve_counts_reproduced':all(e['matches_original_verified_count'] for rows in index.values() for e in rows.values()),
        'source_manifest_sha256':digest(read(folder/'source-manifest.json')),
        'claim':'Measured public mathematical transfer; no breakthrough, novelty or production promotion claim.'}
    write(folder/'summary.json',summary)
    write(folder/'EVIDENCE_SHA256.json',{str(x.relative_to(folder)):hashlib.sha256(x.read_bytes()).hexdigest() for x in folder.rglob('*') if x.is_file() and x.name!='EVIDENCE_SHA256.json'})
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--logs',required=True);p.add_argument('--cache',required=True);p.add_argument('--logged-metrics',required=True);a=p.parse_args();run(a.output,a.logs,a.cache,a.logged_metrics)
if __name__=='__main__':main()
