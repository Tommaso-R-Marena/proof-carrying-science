"""Beam search over independently observed useful successors, not proposal slots.

Invalid/no-op attempts still consume the exact expansion budget. They do not
prevent lower-ranked actions from being tried. State deduplication uses typed
kernel trees with local identifiers alpha-normalized, never displayed strings.
"""
from copy import deepcopy
import math,time
from .induction_ir import digest
from .environment import state_nodes
from .memory_environment import structural_rank

def state_identity(state):
    result=[]
    for g in state['goals']:
        ids={l['id']:f'v{i}' for i,l in enumerate(g['locals'])};metas={}
        def normal(e):
            value=e['value']
            if e['kind']=='local':value=ids.get(value,'unknown_local:'+value)
            if e['kind'] in {'forall','lambda'}:value=''
            if e['kind']=='meta':
                if value not in metas:metas[value]=f'm{len(metas)}'
                value=metas[value]
            return {'kind':e['kind'],'value':value,'children':[normal(c) for c in e['children']]}
        result.append({'goal':normal(g['expression']),'locals':[normal(l['expression']) for l in g['locals']]})
    return digest(result)

def memory_search(env,goal,rank=None,*,budget=96,depth=18,beam=4):
    if type(budget) is not int or not 1<=budget<=4096 or not 1<=depth<=24 or not 1<=beam<=32:
        raise ValueError('invalid checked-successor beam budget')
    goal=deepcopy(goal);identity=digest(goal);started=time.monotonic();calls=env.invocations
    initial=env.observe(goal,[])['states'][-1];frontier=[([],initial)];seen={state_identity(initial)};attempts=[]
    def result(status,receipt=None,states=None):
        if digest(goal)!=identity or receipt and receipt['goal_sha256']!=identity:raise RuntimeError('goal tampering')
        return {'status':status,'receipt':receipt,'states':states or [],'attempts':attempts,
                'expansions':len(attempts),'lean_invocations':env.invocations-calls,
                'wall_seconds':time.monotonic()-started,'algorithm':'typed_checked_successor_beam_v1'}
    for _ in range(depth):
        children=[]
        for path,state in frontier:
            if state_nodes(state)>4096:continue
            options=env.candidates(state);scores=(rank or structural_rank)(deepcopy(state),deepcopy(options))
            if len(scores)!=len(options) or any(type(v) not in {int,float} or not math.isfinite(v) for v in scores):raise ValueError('invalid policy scores')
            useful=0;proposed=0
            for i in sorted(range(len(options)),key=lambda i:(-scores[i],i)):
                if len(attempts)>=budget:break
                action=options[i]
                proposed+=1
                try:observed=env.observe(goal,path+[action])
                except RuntimeError as ex:
                    attempts.append({'path':path,'state':state,'action':action,'status':'resource_exhaustion','error':str(ex)[-1000:]});continue
                attempt={'path':path,'state':state,'action':action,'status':observed['status']};attempts.append(attempt)
                if observed['status']=='invalid':
                    if proposed>=4*beam:break
                    continue
                if observed['status']=='closed':
                    receipt=env.verify(goal,path+[action]);return result('verified',receipt,observed['states'])
                after=observed['states'][-1];fingerprint=state_identity(after)
                if fingerprint in seen:
                    attempt['verified_progress']=False
                    if proposed>=4*beam:break
                    continue
                seen.add(fingerprint);attempt['verified_progress']=True
                children.append((scores[i],path+[action],after));useful+=1
                if useful>=beam or proposed>=2*beam:break
            if len(attempts)>=budget:break
        frontier=[(p,s) for _,p,s in sorted(children,key=lambda x:-x[0])[:beam]]
        if not frontier or len(attempts)>=budget:break
    return result('unknown')
