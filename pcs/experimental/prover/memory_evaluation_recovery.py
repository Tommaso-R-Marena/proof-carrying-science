"""Recover detailed evaluations after serialization failure; never refit/select.

Checkpoints and the original registry remain byte-identical. Each completed
policy is immediately archived and journaled; a restart verifies and reuses
those exact archived rows. Repeated final evaluation is explicitly disclosed.
"""
import argparse,gzip,hashlib,json,subprocess,time,gc
from pathlib import Path
from .environment import ROOT,search
from .induction_ir import digest
from .memory_model import MemoryNetwork
from .memory_cost import MeasuredMemoryEnvironment,MeasuredInductionEnvironment
from .memory_environment import structural_rank
from .memory_search import memory_search
from .memory_experiment import write,measured,metrics,lexical,tactic_baseline

def read(path):
    path=Path(path)
    if not path.exists():path=path.with_suffix(path.suffix+'.gz')
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text())

def recover(folder,logged_metrics):
    folder=Path(folder);logged=read(Path(logged_metrics));p=read(folder/'protocol.json');tasks=read(folder/'tasks.json')
    if digest(tasks)!=p['tasks_sha256'] or (folder/'summary.json').exists():raise ValueError('changed tasks or completed recovery')
    registry_bytes=(folder/'registry.json').read_bytes();registry=json.loads(registry_bytes)
    if not registry['selection_frozen_before_final'] or registry['production_authority'] is not False:raise ValueError('unfrozen registry')
    library=read(folder/'library.json');all_library=read(folder/'all-memory-library.json')
    if digest(library)!=registry['library_sha256']:raise ValueError('changed frozen library')
    models={e['id']:MemoryNetwork.load(folder/e['checkpoint'],e['sha256']) for e in registry['models']}
    splits={s:[t for t in tasks if t['split']==s] for s in ['selection','final']}
    envs=[];start=time.monotonic();replay_calls=0
    def make(lib=None):
        env=MeasuredMemoryEnvironment(lib,heldout=splits['selection']+splits['final'],timeout=30);envs.append(env);return env
    manifest={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(Path(__file__).parent.glob('*.py'))}
    write(folder/'recovery-source-manifest.json',manifest)
    try:
        base=make();selected=make(library);all_env=make(all_library);legacy=MeasuredInductionEnvironment(timeout=30);envs.append(legacy)
        policies={'original_symbolic':(legacy,None,search),'grounded_std_structural':(base,structural_rank,search),
            'lexical_retrieval':(base,lexical,search),'all_verified_memory':(all_env,structural_rank,search),
            'selected_memory_structural':(selected,structural_rank,search),'checked_successor_beam':(selected,structural_rank,memory_search)}
        policies.update({name:(selected,model.rank,search) for name,model in models.items()})
        journal=folder/'evaluation-recovery-journal.json';index=read(journal) if journal.exists() else {'selection':{},'final':{}}
        for split in ['selection','final']:
            for name in [*policies,'bounded_Std_simp_omega_grind']:
                if name in index[split]:
                    entry=index[split][name];path=folder/entry['path']
                    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('changed archived evaluation')
                    continue
                if name=='bounded_Std_simp_omega_grind':rows=[tactic_baseline(legacy,t) for t in splits[split]]
                else:
                    env,rank,engine=policies[name];rows=[measured(env,t,rank,p,engine=engine) for t in splits[split]]
                path=folder/'evaluations'/split/(name+'.json');write(path,rows)
                if not path.exists():path=path.with_suffix(path.suffix+'.gz')
                result=metrics(rows);old=logged[split][name]
                entry={'path':str(path.relative_to(folder)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'metrics':result,'matches_original_verified_count':result['verified']==old['verified'],
                    'matches_original_candidate_count':result['expansions']==old['expansions'],
                    'original_logged_metrics':old}
                index[split][name]=entry;write(journal,index)
                print(split,name,result,'recovery archived',flush=True)
                del rows;gc.collect()
            if (folder/'registry.json').read_bytes()!=registry_bytes:raise ValueError('frozen selection changed')
        write(folder/'evaluations.json',{'format':'pcs-streamed-evaluation-index-v1','splits':index})
        replay=[]
        for name in [registry['selected_local_experiment'],'selected_memory_structural','grounded_std_structural']:
            rows=read(folder/index['final'][name]['path'])
            for row in rows:
                receipt=row['result'].get('receipt')
                if row['result']['status']!='verified':continue
                fresh=MeasuredMemoryEnvironment(receipt['library'],heldout=splits['final'],cache=base.cache,timeout=30)
                try:
                    checked=fresh.verify(row['goal'],receipt['actions'])
                    for key in ['proof','goal_sha256','library_sha256','primitive_catalog_sha256','memory_source_sha256','library_declarations','lean']:
                        if checked.get(key)!=receipt.get(key):raise ValueError('independent recovery replay mismatch')
                    replay_calls+=fresh.actual_calls
                finally:fresh.close()
                replay.append({'policy':name,'task_id':row['id'],'receipt_sha256':digest(checked),'axioms':checked['kernel']['axioms']})
            del rows;gc.collect()
        write(folder/'independent-final-replay.json',replay)
        summary={'metrics':{split:{name:e['metrics'] for name,e in entries.items()} for split,entries in index.items()},
            'selected':registry['selected_local_experiment'],'pool_size':len(read(folder/'candidate-pool.json')),
            'memory_size':len(library['entries']),'trainable_parameters':{n:sum(x.numel() for x in m.parameters()) for n,m in models.items()},
            'combined_memory_utility':metrics(read(folder/'combined-memory-utility.json')),
            'without_memory_utility':metrics(read(folder/'utility-without-memory.json')),
            'total_wall_seconds':time.monotonic()-start,'all_actual_Lean_calls':sum(e.actual_calls for e in envs)+replay_calls,
            'compiler_attempts_including_failures':sum(e.compiler_attempts for e in envs),
            'worker_request_attempts':sum(e.worker_request_attempts for e in envs),'independent_replay_calls':replay_calls,
            'independent_replays':len(replay),'CPU_threads':__import__('torch').get_num_threads(),'torch':__import__('torch').__version__,
            'gpu_used':False,'financial_spend':0,'resource_scope':'Recovery evaluation/construction/replay only; original training/discovery/serialization aggregate costs were lost, not fabricated.',
            'final_evaluation_repeated_for_archival_recovery':True,'checkpoint_selection_unchanged':True,
            'all_original_solve_counts_reproduced':all(e['matches_original_verified_count'] for rows in index.values() for e in rows.values()),
            'source_manifest_sha256':digest(read(folder/'source-manifest.json')),
            'claim':'Measured public mathematical transfer; no breakthrough, novelty or production promotion claim.'}
        write(folder/'summary.json',summary)
        write(folder/'EVIDENCE_SHA256.json',{str(x.relative_to(folder)):hashlib.sha256(x.read_bytes()).hexdigest() for x in folder.rglob('*') if x.is_file() and x.name!='EVIDENCE_SHA256.json'})
        return summary
    finally:
        for env in envs:env.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--logged-metrics',required=True);a=p.parse_args();recover(a.output,a.logged_metrics)
if __name__=='__main__':main()
