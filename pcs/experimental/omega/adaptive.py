"""Bounded counterexample-guided best-first repair and a trained nonlinear ranker.

Witness screening is partial evaluation, not a free equivalence oracle. Both its
work and every generated proposal are recorded. Only exhaustive checks accept.
The trainable MLP consumes syntax; checker labels are training-only targets.
"""
from copy import deepcopy
import math
import random

from .logic import actions, action_id, apply_action, check, digest, evaluate, exact, integer, task, walk
from .learning import features, source_digest
from .search import structural_distance

DIMENSION, HIDDEN = 95, 12


def vector(value, action):
    proposed = apply_action(value['candidate'], action, value['variables'])
    before = structural_distance(value['source'], value['candidate'])
    after = structural_distance(value['source'], proposed)
    return features(value, action, 'graph') + [before / 63, after / 63,
        (before - after) / 63, float(proposed == value['source'])]


def predict(xs, model):
    hidden = [math.tanh(sum(w*x for w,x in zip(row, xs)) + b)
              for row,b in zip(model['input_weights'], model['hidden_bias'])]
    return sum(w*h for w,h in zip(model['output_weights'], hidden)) + model['output_bias'], hidden


def validate(model):
    exact(model, {'format','dimension','hidden','input_weights','hidden_bias','output_weights',
        'output_bias','training','authority','model_sha256'}, 'nonlinear checkpoint')
    if (model['format'] != 'pcs-omega-nonlinear-v2' or type(model['dimension']) is not int or
        model['dimension'] != DIMENSION or type(model['hidden']) is not int or
        model['hidden'] != HIDDEN or model['authority'] != 'NONE'):
        raise ValueError('Unsupported nonlinear checkpoint')
    def weights(value, size):
        if type(value) is not list or len(value) != size or any(type(w) not in (int,float) or
                not math.isfinite(w) or abs(w)>100 for w in value):
            raise ValueError('Invalid nonlinear weights')
    if type(model['input_weights']) is not list or len(model['input_weights']) != HIDDEN:
        raise ValueError('Invalid input layer')
    for row in model['input_weights']: weights(row, DIMENSION)
    weights(model['hidden_bias'], HIDDEN); weights(model['output_weights'], HIDDEN)
    weights([model['output_bias']],1)
    meta = exact(model['training'], {'algorithm','seed','epochs','examples','task_ids',
        'task_digests','families','corpus_sha256','source_digest'}, 'training')
    if meta['algorithm'] != 'syntax-MLP-weighted-logistic-SGD': raise ValueError('Unsupported trainer')
    integer(meta['seed'],0,2**32-1,'seed');integer(meta['epochs'],1,100,'epochs')
    integer(meta['examples'],1,131072,'examples')
    import re
    for field in ('task_ids','task_digests','families'):
        v=meta[field]
        if type(v) is not list or not 1<=len(v)<=1024 or any(type(x) is not str or not 1<=len(x)<=128 for x in v) or len(set(v))!=len(v):
            raise ValueError('Invalid training bindings')
    if len(meta['task_ids'])!=len(meta['task_digests']): raise ValueError('Mismatched task bindings')
    for v in meta['task_digests']+[meta['corpus_sha256'],meta['source_digest']]:
        if type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v): raise ValueError('Invalid training digest')
    if model['model_sha256'] != digest({k:v for k,v in model.items() if k!='model_sha256'}):
        raise ValueError('Nonlinear checkpoint digest mismatch')
    return model


def train(corpus, *, seed=20261009, epochs=32):
    from .corpus import validate_corpus
    validate_corpus(corpus);integer(seed,0,2**32-1,'seed');integer(epochs,1,100,'epochs')
    records=[r for r in corpus['records'] if r['partition']=='train']
    rng=random.Random(seed)
    model={'format':'pcs-omega-nonlinear-v2','dimension':DIMENSION,'hidden':HIDDEN,
        'input_weights':[[rng.uniform(-.1,.1) for _ in range(DIMENSION)] for _ in range(HIDDEN)],
        'hidden_bias':[0.0]*HIDDEN,'output_weights':[rng.uniform(-.1,.1) for _ in range(HIDDEN)],
        'output_bias':0.0,'authority':'NONE'}
    examples=[]
    for record in records:
        value=record['task']
        for action in actions(value['candidate'], value['variables']):
            proposed=apply_action(value['candidate'],action,value['variables'])
            examples.append((vector(value,action),float(check({**value,'candidate':proposed})['equivalent'])))
    for epoch in range(epochs):
        rng.shuffle(examples)
        for xs,label in examples:
            score,hs=predict(xs,model)
            error=(1/(1+math.exp(-max(-30,min(30,score))))-label)*(8 if label else 1)
            lr=.025/(1+epoch*.03)
            old=list(model['output_weights'])
            for j in range(HIDDEN):
                delta=error*old[j]*(1-hs[j]*hs[j])
                model['input_weights'][j]=[w-lr*(delta*x+.0001*w) for w,x in zip(model['input_weights'][j],xs)]
                model['hidden_bias'][j]-=lr*delta
                model['output_weights'][j]-=lr*(error*hs[j]+.0001*old[j])
            model['output_bias']-=lr*error
    model['training']={'algorithm':'syntax-MLP-weighted-logistic-SGD','seed':seed,'epochs':epochs,
        'examples':len(examples),'task_ids':[r['id'] for r in records],
        'task_digests':[r['task_sha256'] for r in records], 'families':sorted({r['family'] for r in records}),
        'corpus_sha256':digest(records),'source_digest':source_digest()}
    model['model_sha256']=digest(model)
    return validate(model)


def search(value, *, model=None, checks=8, depth=3, proposals=256):
    value=deepcopy(task(value));integer(checks,1,128,'checker budget')
    integer(depth,1,4,'depth');integer(proposals,1,1024,'proposal budget')
    if model is not None: model=deepcopy(validate(model))
    initial=check(value);used=1;screened=0;witnesses=[];attempts=[];frontier=[]
    seen={digest(value['candidate'])};solution=None
    if initial['equivalent']: solution={'candidate':value['candidate'],'receipt':initial}
    else: witnesses.append(initial['counterexample']['assignment'])
    def expand(formula,level):
        if level>=depth:return
        current={**value,'candidate':formula}
        for action in actions(formula,value['variables']):
            candidate=apply_action(formula,action,value['variables'])
            score=predict(vector(current,action),model)[0] if model else 0
            # An explicit structural residual keeps the strong baseline visible.
            priority=structural_distance(value['source'],candidate)-score
            frontier.append((priority,level+1,action_id(action),digest(formula),action,candidate))
        frontier.sort(key=lambda row:row[:4])
    if solution is None:expand(value['candidate'],0)
    while frontier and used<checks and len(attempts)<proposals and solution is None:
        _,level,_,parent,action,candidate=frontier.pop(0)
        key=digest(candidate)
        if key in seen:continue
        seen.add(key);failure=None
        for assignment in witnesses:
            screened+=1
            if evaluate(value['source'],assignment)!=evaluate(candidate,assignment):
                failure=deepcopy(assignment);break
        receipt=None
        if failure is None:
            receipt=check({**value,'candidate':candidate});used+=1
            if receipt['equivalent']:solution={'candidate':candidate,'receipt':receipt}
            else:
                assignment=receipt['counterexample']['assignment']
                if assignment not in witnesses:witnesses.append(assignment)
        attempts.append({'parent_sha256':parent,'action':action,'candidate':candidate,'depth':level,
            'rejected_by_witness':failure,'receipt':receipt})
        if solution is None:expand(candidate,level)
    result={'format':'pcs-omega-adaptive-episode-v2','original_task':value,'model_sha256':model['model_sha256'] if model else None,
        'budget':{'checks':checks,'depth':depth,'proposals':proposals},'initial_receipt':initial,
        'attempts':attempts,'checks_used':used,'witness_evaluations':screened,'solution':solution,
        'status':'BOOLEAN_VERIFIED' if solution else 'BUDGET_OR_SEARCH_EXHAUSTED',
        'pcs_authority':False,'lean_kernel_checked':False}
    result['episode_sha256']=digest(result)
    return result


def replay(episode):
    exact(episode,{'format','original_task','model_sha256','budget','initial_receipt','attempts','checks_used',
        'witness_evaluations','solution','status','pcs_authority','lean_kernel_checked','episode_sha256'},'adaptive episode')
    if episode['format']!='pcs-omega-adaptive-episode-v2' or episode['pcs_authority'] is not False or episode['lean_kernel_checked'] is not False:
        raise ValueError('Invalid adaptive authority')
    import re
    if episode['model_sha256'] is not None and (type(episode['model_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',episode['model_sha256'])):
        raise ValueError('Invalid checkpoint binding')
    value=task(episode['original_task']);budget=exact(episode['budget'],{'checks','depth','proposals'})
    integer(budget['checks'],1,128,'checks');integer(budget['depth'],1,4,'depth');integer(budget['proposals'],1,1024,'proposals')
    initial=check(value)
    if digest(initial)!=digest(episode['initial_receipt']):raise ValueError('Forged initial receipt')
    if type(episode['attempts']) is not list or len(episode['attempts'])>budget['proposals']:raise ValueError('Proposal budget exceeded')
    states={digest(value['candidate']):(value['candidate'],0)};used=1;screened=0
    witnesses=[] if initial['equivalent'] else [initial['counterexample']['assignment']]
    solution={'candidate':value['candidate'],'receipt':initial} if initial['equivalent'] else None
    for row in episode['attempts']:
        exact(row,{'parent_sha256','action','candidate','depth','rejected_by_witness','receipt'})
        if solution or used>=budget['checks'] or row['parent_sha256'] not in states:raise ValueError('Invalid or terminated transition')
        parent,level=states[row['parent_sha256']];candidate=apply_action(parent,row['action'],value['variables'])
        integer(row['depth'],1,budget['depth'],'depth');key=digest(candidate)
        if candidate!=row['candidate'] or key in states or row['depth']!=level+1:raise ValueError('Forged repair')
        states[key]=(candidate,level+1);failure=None
        for assignment in witnesses:
            screened+=1
            if evaluate(value['source'],assignment)!=evaluate(candidate,assignment):failure=assignment;break
        if row['rejected_by_witness']!=failure:raise ValueError('Forged partial evaluation')
        if failure is None:
            receipt=check({**value,'candidate':candidate});used+=1
            if digest(receipt)!=digest(row['receipt']):raise ValueError('Forged full check')
            if receipt['equivalent']:solution={'candidate':candidate,'receipt':receipt}
            elif receipt['counterexample']['assignment'] not in witnesses:witnesses.append(receipt['counterexample']['assignment'])
        elif row['receipt'] is not None:raise ValueError('Witness rejection cannot claim full check')
    integer(episode['checks_used'],1,budget['checks'],'checks used');integer(episode['witness_evaluations'],0,16384,'witness evaluations')
    if used!=episode['checks_used'] or screened!=episode['witness_evaluations'] or digest(solution)!=digest(episode['solution']) or episode['status']!=('BOOLEAN_VERIFIED' if solution else 'BUDGET_OR_SEARCH_EXHAUSTED'):
        raise ValueError('Forged result or work accounting')
    if episode['episode_sha256']!=digest({k:v for k,v in episode.items() if k!='episode_sha256'}):raise ValueError('Episode digest mismatch')
    return True
