"""Typed anti-unification, checker-controlled admission and reuse measurement.

Generalization is a proposal, not an inference rule. Each candidate may be false;
sampling screens it, and only an independent Lean proof admits it to the pool.
"""
from copy import deepcopy
from .induction_ir import digest,expression,theorem,var
from .data import structural_fingerprint
from .discovery import propose,lift_state
from .environment import search
from .memory_falsify import falsify
from .library import FORMAT
from .memory_search import memory_search

def anti_unify(left,right):
    if left['binders']!=right['binders']:raise ValueError('incompatible abstraction contexts')
    variables={b['name']:b['type'] for b in left['binders']};binders=deepcopy(left['binders']);holes={}
    def merge(a,b):
        if a==b:return deepcopy(a)
        if a.get('op')==b.get('op') and set(a)==set(b) and a['op'] not in {'forall','exists','var','number'}:
            scalar_keys=[k for k in a if type(a[k]) is not dict]
            if all(a[k]==b[k] for k in scalar_keys):
                return {k:merge(a[k],b[k]) if type(a[k]) is dict else a[k] for k in a}
        at=expression(a,variables)[0];bt=expression(b,variables)[0]
        if at!=bt:raise ValueError('incompatible abstraction types')
        identity=digest([a,b])
        if identity not in holes:
            index=len(holes);name='w'+str(index)
            while name in variables:
                index+=1;name='w'+str(index)
            holes[identity]=name;variables[name]=at;binders.append({'name':name,'type':at})
        return var(holes[identity])
    result={'format':'pcs-math-ir-v1','binders':binders,'body':merge(left['body'],right['body'])}
    used=set()
    def names(e):
        if e.get('op')=='var':used.add(e['name'])
        for child in e.values():
            if type(child) is dict:names(child)
    names(result['body']);result['binders']=[b for b in binders if b['name'] in used]
    theorem(result);return result

def proposals(training,*,maximum=24):
    # The existing kernel-state lift/cuts remain a baseline, preserved exactly.
    result=[{**p,'mechanism':'kernel_state_cut'} for p in propose(training,maximum=maximum)]
    states=[]
    for t in training:
        if t['split']!='train':raise ValueError('abstraction training firewall')
        for s in t['result'].get('states',[]):
            try:goal=lift_state(s)
            except (ValueError,KeyError,IndexError):continue
            states.append((t,s,goal))
    generated=[];seen={p['candidate_sha256'] for p in result}
    for i,(t,s,left) in enumerate(states):
        for u,r,right in states[i+1:]:
            if t['id']==u['id']:continue
            try:
                goal=anti_unify(left,right);identity=structural_fingerprint(goal)
            except (ValueError,KeyError):continue
            if identity in seen:continue
            seen.add(identity)
            generated.append({'goal':goal,'candidate_sha256':identity,'mechanism':'typed_anti_unification',
                'source_task':t['id'],'source_family':t['family'],'source_state_sha256':digest(s),
                'second_source_task':u['id'],'second_state_sha256':digest(r),
                'whole_training_goal':False})
            if len(generated)>=maximum//2:break
        if len(generated)>=maximum//2:break
    # Reserve explicit budget for the new mechanism rather than silently fill
    # it with earlier cuts. Every proposal records its exact producing states.
    return result[:maximum-len(generated)]+generated

def admitted_pool(env,training,heldout,*,maximum=24,budget=96,source_revision):
    forbidden={structural_fingerprint(t['goal']) for t in heldout}
    primitives={structural_fingerprint(e['goal']) for e in env.catalog}
    if any(t['split']!='train' or structural_fingerprint(t['goal']) in forbidden for t in training):
        raise ValueError('discovery data firewall')
    accepted=[];audit=[]
    for proposal in proposals(training,maximum=maximum):
        if proposal['candidate_sha256'] in forbidden or proposal['candidate_sha256'] in primitives:
            audit.append({**proposal,'status':'excluded_evaluation_or_existing_primitive'});continue
        before,seconds=env.invocations,env.seconds
        counter=falsify(env,proposal['goal'])
        if counter['status']=='verified_counterexample':
            audit.append({**proposal,'status':'refuted','falsification':counter,
                          'lean_calls':env.invocations-before,'lean_seconds':env.seconds-seconds});continue
        source=next((t for t in training if t['result']['status']=='verified' and structural_fingerprint(t['goal'])==proposal['candidate_sha256']),None)
        if source is not None:
            # Reuse of an entire training theorem is explicitly marked and
            # freshly compiled; it is never called a new mathematical cut.
            actions=source['result']['receipt']['actions']
            try:
                receipt=env.verify(proposal['goal'],actions);observed=env.observe(proposal['goal'],actions)
                result={'status':'verified','receipt':receipt,'states':observed['states'],
                        'expansions':0,'attempts':[],'mechanism':'independent_training_proof_replay'}
            except RuntimeError:result=search(env,proposal['goal'],budget=budget,beam=4)
        else:result=search(env,proposal['goal'],budget=budget,beam=4)
        record={**proposal,'status':result['status'],'falsification':counter,
                'search':result,'lean_calls':env.invocations-before,'lean_seconds':env.seconds-seconds}
        if result['status']=='verified':
            receipt=env.verify(proposal['goal'],result['receipt']['actions'])
            record['independent_receipt_sha256']=digest(receipt)
            accepted.append({'entry':{'goal':proposal['goal'],'actions':receipt['actions'],
                    'license':'Apache-2.0','source_revision':source_revision},
                'identity':proposal['candidate_sha256'],'mechanism':proposal['mechanism'],
                'whole_training_goal':proposal['whole_training_goal'],
                'discovery_cost_calls':env.invocations-before,'source':proposal})
            record['lean_calls']=env.invocations-before;record['lean_seconds']=env.seconds-seconds
        audit.append(record)
    return accepted,audit

def marginal_utility(baseline,with_lemma,budget):
    """Observed bounded-search benefit, not an estimate of optimal proof cost."""
    b=baseline['result']['status']=='verified';l=with_lemma['result']['status']=='verified'
    return int(l)-int(b),baseline['cost']['all_lean_calls']-with_lemma['cost']['all_lean_calls']

def choose_memory(pool,measurements,*,capacity=6):
    if type(capacity) is not int or not 0<=capacity<=6:raise ValueError('memory capacity')
    if any(x['split']!='utility' for rows in measurements.values() for x in rows):
        raise ValueError('utility admission may not read selection/final labels')
    ranked=[]
    for candidate in pool:
        rows=measurements[candidate['identity']]
        solves=sum(r['solve_delta'] for r in rows);saved=sum(r['calls_saved'] for r in rows)
        # The observed single-lemma utility is a proposal for subset selection,
        # not a submodularity assertion. Synergy must be measured separately.
        if solves>0 or solves==0 and saved>0:
            ranked.append((solves,saved,candidate['identity'],candidate))
    ranked.sort(key=lambda r:(-r[0],-r[1],r[2]))
    selected=[x[-1] for x in ranked[:capacity]]
    return {'format':FORMAT,'entries':[deepcopy(c['entry']) for c in selected]},selected
