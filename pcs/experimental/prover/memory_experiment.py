"""Frozen verifier-cost memory experiment; CPU-first, actual Lean and gradients."""
import argparse,copy,gzip,hashlib,json,random,subprocess,tarfile,time,tempfile,os
from pathlib import Path
import torch
from .environment import ROOT,search,LeanEnvironment
from .induction_environment import InductionEnvironment
from .induction_ir import digest,theorem
from .memory_environment import MemoryEnvironment,structural_rank,replay_memory_receipt
from .memory_discovery import admitted_pool,marginal_utility,choose_memory
from .memory_model import MemoryNetwork,fit_utility
from .memory_search import memory_search
from .memory_cost import MeasuredMemoryEnvironment,MeasuredInductionEnvironment
from .model import imitate,actor_critic
from .library import FORMAT

def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    # Stream bounded buffers instead of allocating the full JSON string, a
    # second UTF-8 copy and a compressed copy simultaneously.
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as stage:
        raw_path=Path(stage.name);buffer=[];size=0;buffer_size=0
        try:
            for part in json.JSONEncoder(sort_keys=True,indent=2).iterencode(value):
                buffer.append(part);buffer_size+=len(part)
                if buffer_size>=65536:
                    data=''.join(buffer).encode();stage.write(data);size+=len(data);buffer=[];buffer_size=0
            data=(''.join(buffer)+'\n').encode();stage.write(data);size+=len(data)
        except BaseException:raw_path.unlink(missing_ok=True);raise
    try:
        if size<=512000:os.replace(raw_path,p)
        else:
            compressed=p.with_suffix(p.suffix+'.gz')
            with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as target:
                target_path=Path(target.name)
                with gzip.GzipFile(filename='',fileobj=target,mode='wb',mtime=0) as stream,raw_path.open('rb') as source:
                    while chunk:=source.read(1048576):stream.write(chunk)
            os.replace(target_path,compressed)
    finally:raw_path.unlink(missing_ok=True)

def measured(env,task,rank,protocol,*,engine=search):
    env.observations.clear();calls,seconds,start=env.actual_calls,env.seconds,time.monotonic()
    result=engine(env,task['goal'],rank,budget=protocol['budget'],beam=protocol['beam'],depth=protocol['depth'])
    return {**task,'result':result,'cost':{'all_lean_calls':env.actual_calls-calls,
             'lean_seconds':env.seconds-seconds,'wall_seconds':time.monotonic()-start}}

def metrics(records):
    return {'verified':sum(r['result']['status']=='verified' for r in records),'tasks':len(records),
            'expansions':sum(r['result'].get('expansions',0) for r in records),
            'lean_calls':sum(r['cost']['all_lean_calls'] for r in records),
            'wall_seconds':sum(r['cost']['wall_seconds'] for r in records)}

def lexical(state,options):
    def constants(e):
        own={e['value'].split(':')[0]} if e['kind']=='constant' else set()
        return own.union(*(constants(c) for c in e['children']))
    symbols=constants(state['goals'][0]['expression']);catalog={e['name']:e['expression'] for e in state.get('available_lemmas',[])}
    scores=structural_rank(state,options)
    for i,a in enumerate(options):
        if a['argument'] in catalog and a['kind'] in {'apply','rewrite','rewrite_back'}:
            overlap=len(symbols & constants(catalog[a['argument']]))
            scores[i]=float(overlap) # no binding/scope or antecedent analysis
    return scores

def tactic_baseline(env,task):
    start,calls,seconds=time.monotonic(),env.actual_calls,env.seconds;attempts=[];receipt=None
    # Strong ordinary Lean tactics; these are fixed trusted commands, not an
    # arbitrary submitted tactic interface. Each complete proof is audited.
    for tactic in ['simp_all','omega','grind']:
        proof='  repeat intro\n  '+tactic
        try:
            kernel=env._source(f'theorem pcs_std_baseline : {theorem(task["goal"])} := by\n{proof}\n#pcs_audit pcs_std_baseline\n','PCS_KERNEL:')
            if not set(kernel['axioms'])<={'propext','Classical.choice','Quot.sound'}:raise RuntimeError('unapproved baseline axioms')
            receipt={'format':'pcs-std-baseline-proof-v1','goal_sha256':digest(task['goal']),
                'statement':theorem(task['goal']),'proof':proof,'kernel':kernel,'lean':env.version,'pcs_scientific_authority':False}
            attempts.append({'tactic':tactic,'status':'verified'});break
        except RuntimeError as ex:attempts.append({'tactic':tactic,'status':'failed','error':str(ex)[-1000:]})
    return {**task,'result':{'status':'verified' if receipt else 'unknown','receipt':receipt,
            'expansions':len(attempts),'attempts':attempts},'cost':{'all_lean_calls':env.actual_calls-calls,
            'lean_seconds':env.seconds-seconds,'wall_seconds':time.monotonic()-start}}

def run(folder):
    folder=Path(folder);p=json.loads((folder/'protocol.json').read_text());tasks=json.loads((folder/'tasks.json').read_text())
    if digest(tasks)!=p['tasks_sha256'] or (folder/'summary.json').exists():raise ValueError('frozen inputs changed or completed experiment exists')
    splits={s:[t for t in tasks if t['split']==s] for s in ['train','utility','selection','final']}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=[*Path(__file__).parent.glob('*.py'),ROOT/'formal/PCSProofProbe.lean',ROOT/'formal/PCSProofWorker.lean',ROOT/'formal/PCSReuseWorker.lean']
    manifest={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(paths)}
    write(folder/'source-manifest.json',manifest)
    with tarfile.open(folder/'source-overlay.tar.gz','w:gz') as archive:
        for x in sorted(paths):archive.add(x,arcname=str(x.relative_to(ROOT)))
    start=time.monotonic();envs=[];replay_calls=0;training_reports={};models={}
    def make(library=None):
        e=MeasuredMemoryEnvironment(library,heldout=splits['selection']+splits['final'],timeout=30);envs.append(e);return e
    try:
        base=make();legacy=MeasuredInductionEnvironment(timeout=30);envs.append(legacy)
        records=[measured(base,t,structural_rank,p) for t in splits['train']]
        write(folder/'training-source-trajectories.json',records)
        print('Training coverage',metrics(records),flush=True)
        pool,audit=admitted_pool(base,records,splits['selection']+splits['final'],maximum=p['candidate_limit'],budget=p['budget'],source_revision=revision)
        write(folder/'admission-audit.json',audit);write(folder/'candidate-pool.json',pool)
        print('Verified candidates',len(pool),'proposals',len(audit),flush=True)
        utility_base=[measured(base,t,structural_rank,p) for t in splits['utility']]
        write(folder/'utility-without-memory.json',utility_base)
        measurements={};utility_examples=[]
        for candidate in pool:
            single=make({'format':FORMAT,'entries':[candidate['entry']]});rows=[]
            for b,t in zip(utility_base,splits['utility']):
                with_lemma=measured(single,t,structural_rank,p);delta,saved=marginal_utility(b,with_lemma,p['budget'])
                state=single.observe(t['goal'],[])['states'][-1]
                row={'split':'utility','task_id':t['id'],'candidate_sha256':candidate['identity'],
                     'solve_delta':delta,'calls_saved':saved,'without':b,'with':with_lemma,
                     'label_source':'paired_actual_Lean_search','state':state,
                     'action':{'kind':'apply','argument':'PCSReuseL0'}}
                rows.append(row);utility_examples.append(row)
            measurements[candidate['identity']]=rows
            print('Marginal utility',candidate['identity'][:12],sum(r['solve_delta'] for r in rows),sum(r['calls_saved'] for r in rows),flush=True)
            single.close()
        write(folder/'paired-utility.json',measurements)
        library,selected=choose_memory(pool,measurements,capacity=p['memory_capacity'])
        write(folder/'library.json',library);write(folder/'selected-memory.json',selected)
        selected_env=make(library)
        # Synergy is measured, not inferred from sums of marginal scores.
        synergy=[measured(selected_env,t,structural_rank,p) for t in splits['utility']]
        write(folder/'combined-memory-utility.json',synergy)
        all_library={'format':FORMAT,'entries':[x['entry'] for x in pool[:6]]};all_env=make(all_library)
        write(folder/'all-memory-library.json',all_library)
        training=[]
        for t,r in zip(splits['train'],records):
            if r['result']['status']=='verified':
                actions=r['result']['receipt']['actions'];observed=selected_env.observe(t['goal'],actions)
                receipt=selected_env.verify(t['goal'],actions)
                training.append({**t,'result':{**r['result'],'states':observed['states'],'receipt':receipt}})
            learned_record=measured(selected_env,t,structural_rank,p)
            training.append(learned_record)
        write(folder/'imitation-trajectories.json',training)
        registry=[]
        for seed in p['seeds']:
            torch.manual_seed(seed);m=MemoryNetwork();models[f'untrained-{seed}']=copy.deepcopy(m)
            print('Fit actual paired utility',seed,flush=True)
            training_reports[f'utility-{seed}']=fit_utility(m,utility_examples,epochs=10,seed=seed)
            m.save(folder/f'utility-stage-{seed}.json',{'stage':'utility_complete','seed':seed,'source_manifest_sha256':digest(manifest),'protocol_sha256':digest(p)})
            write(folder/'training-progress.json',training_reports)
            print('Fit checked imitation',seed,flush=True)
            training_reports[f'imitation-{seed}']=imitate(m,training,epochs=p['epochs'],seed=seed,candidate_provider=selected_env.candidates)
            models[f'supervised-{seed}']=copy.deepcopy(m)
            m.save(folder/f'supervised-stage-{seed}.json',{'stage':'imitation_complete','seed':seed,'source_manifest_sha256':digest(manifest),'protocol_sha256':digest(p)})
            write(folder/'training-progress.json',training_reports)
            torch.manual_seed(seed);bag=MemoryNetwork(architecture='bag')
            training_reports[f'bag-{seed}']=fit_utility(bag,utility_examples,epochs=10,seed=seed)
            training_reports[f'bag-imitation-{seed}']=imitate(bag,training,epochs=p['epochs'],seed=seed,candidate_provider=selected_env.candidates)
            models[f'bag-{seed}']=bag
            for generation in range(1,p['generations']+1):
                report=actor_critic(m,selected_env,splits['train'],episodes=p['rl_episodes_per_generation'],seed=seed+generation)
                training_reports[f'rl{generation}-{seed}']=report;models[f'rl{generation}-{seed}']=copy.deepcopy(m)
                m.save(folder/f'rl-stage-{generation}-{seed}.json',{'stage':'rl_generation_complete','seed':seed,'generation':generation,'source_manifest_sha256':digest(manifest),'protocol_sha256':digest(p)})
                write(folder/'training-progress.json',training_reports)
                print('Actual RL',seed,generation,report.get('weights_changed'),flush=True)
        write(folder/'training.json',training_reports)
        for name,model in models.items():
            sha=model.save(folder/(name+'.json'),{'source_manifest_sha256':digest(manifest),
                'protocol_sha256':digest(p),'training_sha256':digest(training),'utility_sha256':digest(utility_examples),
                'library_sha256':selected_env.library_sha256,'primitive_catalog_sha256':selected_env.primitive_catalog_sha256,
                'experimental':True,'production_authority':False})
            registry.append({'id':name,'checkpoint':name+'.json','sha256':sha,
                             'parameters':sum(x.numel() for x in model.parameters()),'architecture':model.architecture})
        evaluations={};policies={'original_symbolic':(legacy,None,search),'grounded_std_structural':(base,structural_rank,search),
            'lexical_retrieval':(base,lexical,search),'all_verified_memory':(all_env,structural_rank,search),
            'selected_memory_structural':(selected_env,structural_rank,search),
            'checked_successor_beam':(selected_env,structural_rank,memory_search)}
        policies.update({name:(selected_env,m.rank,search) for name,m in models.items()})
        def archive_rows(split,name,rows):
            path=folder/'evaluations'/split/(name+'.json');write(path,rows)
            if not path.exists():path=path.with_suffix(path.suffix+'.gz')
            return {'path':str(path.relative_to(folder)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'metrics':metrics(rows)}
        def archived_rows(entry):
            path=folder/entry['path']
            return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text())
        selected_model=None
        for split in ['selection','final']:
            evaluations[split]={}
            for name,(e,rank,engine) in policies.items():
                rows=[measured(e,t,rank,p,engine=engine) for t in splits[split]]
                evaluations[split][name]=archive_rows(split,name,rows);print(split,name,metrics(rows),flush=True)
                del rows
            rows=[tactic_baseline(legacy,t) for t in splits[split]]
            evaluations[split]['bounded_Std_simp_omega_grind']=archive_rows(split,'bounded_Std_simp_omega_grind',rows);print(split,'Std',metrics(rows),flush=True)
            del rows
            if split=='selection':
                eligible=[n for n in models if not n.startswith('untrained')]
                selected_model=max(eligible,key=lambda n:(evaluations[split][n]['metrics']['verified'],-evaluations[split][n]['metrics']['lean_calls']))
                write(folder/'registry.json',{'format':'pcs-verified-memory-registry-v1','models':registry,
                    'selected_local_experiment':selected_model,'library_sha256':selected_env.library_sha256,
                    'primitive_catalog_sha256':selected_env.primitive_catalog_sha256,'selection_frozen_before_final':True,
                    'environment':'MemoryEnvironment','production_authority':False})
        write(folder/'evaluations.json',{'format':'pcs-streamed-evaluation-index-v1','splits':evaluations})
        replay=[]
        for name in [selected_model,'selected_memory_structural','grounded_std_structural']:
            for r in archived_rows(evaluations['final'][name]):
                if r['result']['status']!='verified':continue
                receipt=r['result']['receipt'];fresh=MeasuredMemoryEnvironment(receipt['library'],heldout=splits['final'],cache=base.cache,timeout=30)
                try:
                    checked=fresh.verify(r['goal'],receipt['actions'])
                    for key in ['proof','goal_sha256','library_sha256','primitive_catalog_sha256','memory_source_sha256','library_declarations','lean']:
                        if checked.get(key)!=receipt.get(key):raise ValueError('independent replay binding mismatch')
                    replay_calls+=fresh.actual_calls
                finally:fresh.close()
                replay.append({'policy':name,'task_id':r['id'],'receipt_sha256':digest(checked),'axioms':checked['kernel']['axioms']})
        write(folder/'independent-final-replay.json',replay)
        summary={'metrics':{s:{n:entry['metrics'] for n,entry in rows.items()} for s,rows in evaluations.items()},
                 'selected':selected_model,'pool_size':len(pool),'memory_size':len(library['entries']),
                 'trainable_parameters':{n:sum(x.numel() for x in m.parameters()) for n,m in models.items()},
                 'combined_memory_utility':metrics(synergy),'without_memory_utility':metrics(utility_base),
                 'total_wall_seconds':time.monotonic()-start,'all_actual_Lean_calls':sum(e.actual_calls for e in envs)+replay_calls,
                 'compiler_attempts_including_failures':sum(e.compiler_attempts for e in envs),'worker_request_attempts':sum(e.worker_request_attempts for e in envs),'independent_replay_calls':replay_calls,'independent_replays':len(replay),'torch':torch.__version__,'CPU_threads':torch.get_num_threads(),
                 'gpu_used':False,'financial_spend':0,'source_manifest_sha256':digest(manifest),
                 'claim':'Measured public mathematical transfer; no automatic breakthrough, novelty, intelligence or production promotion claim.'}
        write(folder/'summary.json',summary)
        write(folder/'EVIDENCE_SHA256.json',{str(x.relative_to(folder)):hashlib.sha256(x.read_bytes()).hexdigest() for x in folder.rglob('*') if x.is_file() and x.name!='EVIDENCE_SHA256.json'})
        return summary
    finally:
        for e in envs:e.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
if __name__=='__main__':main()
