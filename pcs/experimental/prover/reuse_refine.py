"""Verified failure-driven refinement with untouched compositional evaluation.

The initial public audits become explicitly exposed development/training data.
New validation/final problems, source and selection protocol are frozen before
fitting. Feedback must be independently replayed; only validation selects a
candidate. Final problems have no attached solutions and never supply gradients.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import time

import torch

from .data import intake_feedback, structural_fingerprint
from .environment import search
from .ir import digest
from .language import formalize
from .library import LibraryEnvironment, replay_library_receipt
from .model import imitate
from .portfolio import search_portfolio, _BasicActionView
from .reuse_model import ReuseNetwork
from .reuse_experiment import metrics, write


def refine(experiment, output, epochs=16, seeds=(17,31,47)):
    folder, output = Path(experiment), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started=time.monotonic()
    registry=json.loads((folder/'registry.json').read_text())
    parent=next(e for e in registry['models'] if e['id']==registry['selected_local_experiment'])
    archived=json.loads(gzip.decompress((folder/'retrieval-audit/evaluations.json.gz').read_bytes()))
    statements=[
        ('validation','nat_reflexive_order','For all natural numbers n, n is less than or equal to n.'),
        ('validation','int_reflexive_order','For all integers z, z is less than or equal to z.'),
        ('validation','double_function_rule','For all predicates on natural numbers P and Q, if (∀ (n : Nat), P(n) implies Q(n)) then (∀ (m : Nat), P(m) implies Q(m)).'),
        ('final','nat_three_edge_chain','For all natural numbers a, b, c and d, if ((a is less than or equal to b) and ((b is less than or equal to c) and (c is less than or equal to d))) then (a is less than or equal to d).'),
        ('final','int_three_edge_chain','For all integers a, b, c and d, if ((a is less than or equal to b) and ((b is less than or equal to c) and (c is less than or equal to d))) then (a is less than or equal to d).'),
        ('final','nat_order_cycle','For all natural numbers a, b and c, if ((a is less than or equal to b) and ((b is less than or equal to c) and (c is less than or equal to a))) then (a equals c).'),
        ('final','triple_function_congruence','For all functions from natural numbers to natural numbers f and g, if (∀ (a : Nat), f(a) equals g(a)) then (∀ (b : Nat), f(f(f(b))) equals g(g(g(b)))).'),
        ('final','two_rule_function_chain','For all functions from natural numbers to natural numbers f, g and h, if ((∀ (a : Nat), f(a) equals g(a)) and (∀ (b : Nat), g(b) equals h(b))) then (∀ (c : Nat), f(f(c)) equals h(h(c))).'),
        ('final','three_part_nat_witness','For all natural numbers n, there exists a natural number m such that ((m equals n) and ((m + 0 equals n) and (m * 1 equals n))).'),
        ('final','false_order_equality','For all natural numbers a and b, if (a is less than or equal to b) then a equals b.'),
        ('final','false_function_identity','For all functions from natural numbers to natural numbers f and g, if (∀ (a : Nat), f(a) equals g(a)) then (∀ (b : Nat), f(b) equals b).'),
    ]
    tasks=[]
    for split,name,source in statements:
        parsed=formalize(source)
        if parsed['status']!='supported': raise ValueError(name+str(parsed))
        tasks.append({'id':name,'split':split,'goal':parsed['candidates'][0]['ir'],'original_statement':source,'license':'Apache-2.0'})
    prior=json.loads((folder/'tasks.json').read_text())
    exposed=[*prior['foundations'],*prior['problems'],*archived['symbolic']]
    fingerprints={structural_fingerprint(t['goal']) for t in exposed}
    if any(structural_fingerprint(t['goal']) in fingerprints for t in tasks):
        raise ValueError('new evaluation duplicates an exposed theorem')
    if len({structural_fingerprint(t['goal']) for t in tasks})!=len(tasks):raise ValueError('evaluation alpha duplicate')
    protocol={'format':'pcs-verified-refinement-v1','parent_checkpoint_sha256':parent['sha256'],'parent_id':parent['id'],
              'epochs':epochs,'seeds':list(seeds),'budget':64,'beam':4,'tasks_sha256':digest(tasks),
              'training':'independently replayed prior public audit successes; prioritize raw-parent failures, plus retained reusable-principle traces',
              'selection':'validation verified count, then fewer expansions; select before final evaluation; no automatic scientific authority',
              'evaluation':'new authored compositions; no exact alpha overlap with exposed corpus; shared theorem families, not external/private transfer',
              'compute':'CPU only; no external model calls or paid infrastructure'}
    write(output/'protocol.json',protocol);write(output/'tasks.json',tasks)
    root=Path(__file__).resolve().parents[3]
    sources=[*Path(__file__).parent.glob('*.py'),root/'formal/PCSProofProbe.lean',root/'formal/PCSProofWorker.lean',root/'formal/PCSReuseWorker.lean']
    write(output/'source-manifest.json',{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)})
    library=json.loads((folder/'library.json').read_text());write(output/'library.json',library)
    env=LibraryEnvironment(library,heldout=tasks,timeout=30)
    try:
        parent_status={t['id']:t['result']['status'] for t in archived['raw_selected_reuse']}
        records=[t for t in archived['symbolic'] if t['result']['status']=='verified']
        records.sort(key=lambda t:(parent_status[t['id']]=='verified',t['id']))
        retained=json.loads((folder/'training-trajectories.json').read_text())
        records += [t for t in retained if t['result']['status']=='verified']
        checked=[]
        for r in records:
            observed=env.observe(r['goal'],r['result']['receipt']['actions'])
            receipt=env.verify(r['goal'],r['result']['receipt']['actions'])
            feedback={'goal':r['goal'],'receipt':receipt,'original_statement':r['original_statement'],
                      'hint_exposure':'public authored symbolic search or checked reusable lemma; no human trajectories'}
            item=intake_feedback(env,feedback,tasks,license='Apache-2.0',source_revision='4034db308d171b46c41e7e9ba2723e7fe4db6647')
            item['id']=r['id'];item['previous_raw_model_failed']=parent_status.get(r['id'])!='verified'
            checked.append(item)
        write(output/'training-trajectories.json',checked)
        models={'parent':ReuseNetwork.load(folder/parent['checkpoint'],parent['sha256'])}
        reports={}
        for seed in seeds:
            model=ReuseNetwork.load(folder/parent['checkpoint'],parent['sha256'])
            reports[f'refined-{seed}']=imitate(model,checked,epochs=epochs,seed=seed,candidate_provider=env.candidates)
            models[f'refined-{seed}']=model
            print('refined',seed,reports[f'refined-{seed}']['examples'],'verified transitions',flush=True)
        write(output/'training.json',reports)
        entries=[]
        for name,model in models.items():
            sha=model.save(output/(name+'.json'),{'parent_sha256':parent['sha256'],'training_sha256':digest(checked),
                  'library_sha256':env.library_sha256,'protocol_sha256':digest(protocol),'status':'experimental'})
            entries.append({'id':name,'checkpoint':name+'.json','sha256':sha,'parameters':sum(p.numel() for p in model.parameters()),
                            'architecture':model.architecture,'approval':'experimental-local','pcs_authority':False})
        def run(tasks_,runner):
            env.observations.clear();calls=env.invocations;begin=time.monotonic()
            records=[{**t,'result':runner(t['goal'])} for t in tasks_]
            return records,{**metrics(records),'all_observe_and_verify_invocations':env.invocations-calls,
                            'whole_evaluation_wall_seconds':time.monotonic()-begin}
        validation=[t for t in tasks if t['split']=='validation'];final=[t for t in tasks if t['split']=='final']
        evaluations={'validation':{},'final':{}};summaries={'validation':{},'final':{}}
        for name,model in models.items():
            evaluations['validation'][name],summaries['validation'][name]=run(validation,lambda g,m=model:search(env,g,m.rank,budget=64,beam=4))
            print('validation',name,summaries['validation'][name],flush=True)
        selected=max(models,key=lambda n:(summaries['validation'][n]['verified'],-summaries['validation'][n]['expansions']))
        # Selection is frozen to disk before any new final task is searched.
        write(output/'registry.json',{'format':'pcs-reuse-model-registry-v1','models':entries,'selected_local_experiment':selected,
              'library_sha256':env.library_sha256,'production_authority':False,'selection_frozen_before_final':True})
        for name,model in models.items():
            evaluations['final'][name],summaries['final'][name]=run(final,lambda g,m=model:search(env,g,m.rank,budget=64,beam=4))
            print('final',name,summaries['final'][name],flush=True)
        evaluations['final']['symbolic'],summaries['final']['symbolic']=run(final,lambda g:search(_BasicActionView(env),g,budget=64,beam=4))
        evaluations['final']['selected_portfolio'],summaries['final']['selected_portfolio']=run(final,lambda g:search_portfolio(env,g,models[selected].rank,budget=64,beam=4))
        replay=[]
        for r in evaluations['final']['selected_portfolio']:
            if r['result']['status']=='verified':
                fresh=replay_library_receipt(r['goal'],r['result']['receipt'],cache=env.cache)
                replay.append({'id':r['id'],'receipt_sha256':digest(fresh),'axioms':fresh['kernel']['axioms']})
        write(output/'independent-final-replay.json',replay)
        (output/'evaluations.json.gz').write_bytes(gzip.compress(json.dumps(evaluations,sort_keys=True,separators=(',',':')).encode(),mtime=0))
        write(output/'summary.json',{'metrics':summaries,'selected':selected,'training_tasks':len(checked),
              'training_policy_failures':sum(t['previous_raw_model_failed'] for t in checked),'wall_seconds':time.monotonic()-started,
              'gpu_used':False,'financial_spend':0,'library_construction_invocations':env.construction_invocations,
              'library_construction_seconds':env.construction_seconds,'instrumented_lean_invocations':env.invocations})
        write(output/'SHA256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--experiment',required=True);p.add_argument('--output',required=True)
    p.add_argument('--epochs',type=int,default=16)
    a=p.parse_args();refine(a.experiment,a.output,a.epochs)
