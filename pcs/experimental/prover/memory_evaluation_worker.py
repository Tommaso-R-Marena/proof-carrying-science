"""One independent frozen policy evaluation, bounded to a separate cache."""
import argparse,gc,hashlib,json,time
from pathlib import Path
from .memory_evaluation_recovery import read
from .memory_experiment import measured,metrics,write,lexical,tactic_baseline
from .memory_cost import MeasuredMemoryEnvironment,MeasuredInductionEnvironment
from .memory_environment import structural_rank
from .memory_model import MemoryNetwork
from .memory_search import memory_search
from .environment import search
from .induction_ir import digest

def run(folder,split,name,cache):
    folder=Path(folder);p=read(folder/'protocol.json');tasks=read(folder/'tasks.json');registry=read(folder/'registry.json')
    if split not in {'selection','final'} or digest(tasks)!=p['tasks_sha256']:raise ValueError('frozen evaluation inputs')
    heldout=[t for t in tasks if t['split'] in {'selection','final'}];chosen=[t for t in tasks if t['split']==split]
    names={'original_symbolic','grounded_std_structural','lexical_retrieval','all_verified_memory','selected_memory_structural','checked_successor_beam','bounded_Std_simp_omega_grind'}|{e['id'] for e in registry['models']}
    if name not in names:raise ValueError('unapproved frozen policy')
    path=folder/'evaluations'/split/(name+'.json');receipt_path=path.with_suffix('.worker.json')
    if receipt_path.exists():return read(receipt_path)
    started=time.monotonic()
    if name in {'original_symbolic','bounded_Std_simp_omega_grind'}:
        env=MeasuredInductionEnvironment(cache=cache,timeout=30);rank=None
    else:
        lib=read(folder/('all-memory-library.json' if name=='all_verified_memory' else 'library.json')) if name not in {'grounded_std_structural','lexical_retrieval'} else None
        env=MeasuredMemoryEnvironment(lib,heldout=heldout,cache=cache,timeout=30);rank=lexical if name=='lexical_retrieval' else structural_rank
        if name in {e['id'] for e in registry['models']}:
            entry=next(e for e in registry['models'] if e['id']==name);model=MemoryNetwork.load(folder/entry['checkpoint'],entry['sha256']);rank=model.rank
    try:
        rows=[tactic_baseline(env,t) if name=='bounded_Std_simp_omega_grind' else measured(env,t,rank,p,engine=memory_search if name=='checked_successor_beam' else search) for t in chosen]
        write(path,rows)
        if not path.exists():path=path.with_suffix(path.suffix+'.gz')
        receipt={'path':str(path.relative_to(folder)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'metrics':metrics(rows),'actual_Lean_calls_including_construction':env.actual_calls,
            'compiler_attempts':env.compiler_attempts,'worker_requests':env.worker_request_attempts,
            'wall_seconds_including_archive':time.monotonic()-started,'frozen_registry_sha256':hashlib.sha256((folder/'registry.json').read_bytes()).hexdigest()}
        write(receipt_path,receipt)
        print(json.dumps({'split':split,'policy':name,'metrics':receipt['metrics'],'archived':True}),flush=True)
        return receipt
    finally:env.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--split',required=True);p.add_argument('--policy',required=True);p.add_argument('--cache',required=True);a=p.parse_args();run(a.output,a.split,a.policy,Path(a.cache))
if __name__=='__main__':main()
