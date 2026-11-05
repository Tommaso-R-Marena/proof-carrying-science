"""Actual controlled-English memory-policy execution and checked feedback."""
import argparse,json,time
from pathlib import Path
from .induction_language import formalize,explain
from .induction_ir import digest
from .memory_environment import MemoryEnvironment,structural_rank
from .memory_model import MemoryNetwork
from .memory_cost import MeasuredMemoryEnvironment,MeasuredInductionEnvironment
from .environment import search
from .data import claim_graph
from .memory_falsify import falsify

def run_std(statement,*,interpretation=None):
    """A strong, explicitly symbolic baseline; no model supplied tactics."""
    from .memory_experiment import tactic_baseline
    formal=formalize(statement);result={'formalization':formal,'pcs_authority':False,'model':'bounded_Std_simp_omega_grind'}
    if formal['status']=='unsupported':return {**result,'status':'unsupported_formalization'}
    if formal['status']=='ambiguous' and interpretation is None:return {**result,'status':'ambiguous_interpretation'}
    index=0 if interpretation is None else interpretation
    if type(index) is not int or not 0<=index<len(formal['candidates']):raise ValueError('invalid selected interpretation')
    env=MeasuredInductionEnvironment(timeout=30)
    try:
        goal=formal['candidates'][index]['ir'];row=tactic_baseline(env,{'goal':goal})
        return {**result,'status':row['result']['status'],'search':row['result'],'cost':row['cost'],'explanation':explain(goal)}
    finally:env.close()

def load(folder):
    folder=Path(folder);registry=json.loads((folder/'registry.json').read_text())
    if registry.get('format')!='pcs-verified-memory-registry-v1' or registry.get('production_authority') is not False:raise ValueError('unapproved memory registry')
    entry=next(m for m in registry['models'] if m['id']==registry['selected_local_experiment'])
    if Path(entry['checkpoint']).name!=entry['checkpoint']:raise ValueError('checkpoint path')
    library=json.loads((folder/'library.json').read_text())
    if digest(library)!=registry['library_sha256']:raise ValueError('memory generation mismatch')
    model=MemoryNetwork.load(folder/entry['checkpoint'],entry['sha256'])
    metadata=json.loads((folder/entry['checkpoint']).read_text())['metadata']
    if metadata['library_sha256']!=registry['library_sha256'] or metadata['primitive_catalog_sha256']!=registry['primitive_catalog_sha256']:
        raise ValueError('checkpoint catalog binding mismatch')
    return registry,entry,library,model

def run(statement,folder,*,interpretation=None,budget=96,policy='learned',actions=None,feedback=True):
    if type(budget) is not int or not 1<=budget<=96:raise ValueError('memory search budget outside bound')
    if policy not in {'learned','same_memory_structural','no_memory_structural','exact_actions'}:raise ValueError('unsupported memory policy')
    if actions is not None and policy!='exact_actions':raise ValueError('exact actions require explicit mode')
    formal=formalize(statement);result={'format':'pcs-lean-learning-loop-v1','formalization':formal,
        'pcs_authority':False,'training_feedback':None,'mode':policy,'model':'verified-memory-v1'}
    if formal['status']=='unsupported':return {**result,'status':'unsupported_formalization'}
    if formal['status']=='ambiguous' and interpretation is None:return {**result,'status':'ambiguous_interpretation'}
    index=0 if interpretation is None else interpretation
    if type(index) is not int or not 0<=index<len(formal['candidates']):raise ValueError('invalid selected interpretation')
    registry,entry,library,model=load(folder)
    if policy=='no_memory_structural':library=None
    started=time.monotonic();env=MeasuredMemoryEnvironment(library,timeout=30)
    try:
        if env.primitive_catalog_sha256!=registry['primitive_catalog_sha256']:raise ValueError('approved primitive catalog changed')
        goal=formal['candidates'][index]['ir']
        if actions is not None:
            observed=env.observe(goal,actions)
            proof=env.verify(goal,actions) if observed['status']=='closed' else None
            searched={'status':'verified' if proof else 'unknown','receipt':proof,
                'states':observed['states'],'expansions':len(actions),'attempts':[],'lean_invocations':env.invocations}
        else:searched=search(env,goal,model.rank if policy=='learned' else structural_rank,budget=budget,beam=4,depth=18)
        counter=falsify(env,goal,limit=32) if searched['status']=='unknown' and actions is None else None
        status='verified_counterexample' if counter and counter['status']=='verified_counterexample' else searched['status']
        result.update(status=status,search=searched,explanation=explain(goal),counterexample=counter,
            checkpoint_sha256=entry['sha256'] if policy=='learned' else None,
            memory_sha256=env.library_sha256,primitive_catalog_sha256=env.primitive_catalog_sha256,
            cost={'all_Lean_execution_attempts':env.actual_calls,'compiler_attempts':env.compiler_attempts,
                  'worker_request_attempts':env.worker_request_attempts,'cold_wall_seconds':time.monotonic()-started},
            claim_graph=claim_graph(statement,goal,searched['receipt']))
        if searched['receipt'] and feedback:
            result['training_feedback']={'goal':goal,'receipt':searched['receipt'],'original_statement':statement,
                'hint_exposure':None,'eligible_for_training':False,
                'required':'Explicit source license/consent and independent memory-aware kernel replay, with held-out exclusion.'}
        return result
    finally:env.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('statement');p.add_argument('--models',default='research/verified-memory-v1');p.add_argument('--output',required=True);p.add_argument('--interpretation',type=int);p.add_argument('--policy',choices=['learned','same_memory_structural','no_memory_structural'],default='learned');a=p.parse_args()
    r=run(a.statement,a.models,interpretation=a.interpretation,policy=a.policy)
    Path(a.output).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'model':r['model'],'artifact':a.output}))
if __name__=='__main__':main()
