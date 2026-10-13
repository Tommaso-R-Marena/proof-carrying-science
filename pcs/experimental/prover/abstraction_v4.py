"""Cross-type, proof-state-bound equality-transport anti-unification.

A restricted structural proposal generator: elaborated local hypotheses must be
an equality chain of one identical unary context, and the target must connect
its endpoints. No statement becomes true merely because this pattern matches.
The proposed type-polymorphic theorem intentionally omits injectivity; a real
Lean counterexample triggers an explicit premise repair before admission.
"""
from copy import deepcopy
from itertools import product
from .induction_ir import digest

CANDIDATE='∀ (α β : Type) (f : α → β) (a b c : α), f a = f b → f b = f c → a = c'
REPAIRED='∀ (α β : Type) (f : α → β) (a b c : α), Function.Injective f → f a = f b → f b = f c → a = c'
COUNTEREXAMPLE='¬ ('+CANDIDATE+')'
COUNTER_PROOF='''  intro h
  have bad : (0 : Nat) = 1 := h Nat Nat (fun _ => 0) 0 0 1 rfl rfl
  exact Nat.noConfusion bad'''
REPAIR_ACTIONS=[{'kind':'intro','argument':'h'+str(i)} for i in range(9)]+[{'kind':'apply_local','argument':'h6'},{'kind':'apply_lemma','argument':'Eq.trans'},{'kind':'exact_local','argument':'h7'},{'kind':'exact_local','argument':'h8'}]

def application(expression):
    args=[];head=expression
    while head.get('kind')=='application':
        if len(head.get('children',[]))!=2:raise ValueError('malformed elaborated application')
        head,arg=head['children'];args.append(arg)
    return head,list(reversed(args))

def equality(expression):
    head,args=application(expression)
    if head.get('kind')!='constant' or head.get('value','').split(':')[0]!='Eq' or len(args)!=3:
        raise ValueError('actual elaborated equality required')
    return args

def abstract_context(term,local_id):
    """Abstract one endpoint while preserving all other elaborated syntax."""
    count=0
    def visit(node):
        nonlocal count
        if node.get('kind')=='local' and node.get('value')==local_id:
            count+=1;return {'kind':'typed_endpoint_hole','value':'α','children':[]}
        if set(node)!={'kind','value','children'}:raise ValueError('canonical Lean Expr required')
        return {**deepcopy(node),'children':[visit(child) for child in node['children']]}
    result=visit(term)
    if count!=1:raise ValueError('restricted unary context requires exactly one endpoint')
    return result

def source_pattern(source):
    receipt=source['receipt'];state=source['state']
    if receipt.get('kernel')!=receipt.get('independent_kernel') or receipt.get('goal_sha256')!=digest(source['statement']) or receipt.get('pcs_authority') is not False:
        raise ValueError('independently checked immutable source required')
    if not set(receipt['kernel']['axioms'])<={'propext','Classical.choice','Quot.sound'}:raise ValueError('unapproved source axioms')
    if len(state.get('goals',[]))!=1:raise ValueError('one source obligation required')
    goal=state['goals'][0];locals_=goal['locals']
    if len(locals_)!=5:raise ValueError('three typed endpoints and two equality hypotheses required')
    a,b,c,h0,h1=locals_;domain,left,right=equality(goal['expression'])
    if left!={'kind':'local','value':a['id'],'children':[]} or right!={'kind':'local','value':c['id'],'children':[]}:
        raise ValueError('source target does not bind chain endpoints')
    if any(v['expression']!=domain for v in [a,b,c]):raise ValueError('endpoint types disagree')
    codomain,x,y=equality(h0['expression']);codomain2,y2,z=equality(h1['expression'])
    if codomain!=codomain2 or y!=y2:raise ValueError('hypotheses are not a typed equality chain')
    contexts=[abstract_context(t,v['id']) for t,v in [(x,a),(y,b),(y2,b),(z,c)]]
    if any(context!=contexts[0] for context in contexts[1:]):raise ValueError('different unary contexts')
    return {'domain':domain,'codomain':codomain,'unary_context':contexts[0],'source_goal_sha256':receipt['goal_sha256'],'source_state_sha256':digest(state),'independent_kernel':receipt['independent_kernel']}

def propose(sources):
    if len(sources)<2 or len({s['id'] for s in sources})<2:raise ValueError('two distinct checked source proofs required')
    patterns=[source_pattern(s) for s in sources]
    if len({digest([p['domain'],p['codomain'],p['unary_context']]) for p in patterns})<2:
        raise ValueError('alpha-renamed copies do not establish cross-type abstraction')
    return {'format':'pcs-cross-type-equality-transport-proposal-v4','candidate':CANDIDATE,'candidate_sha256':digest(CANDIDATE),'source_patterns':patterns,'source_ids':[s['id'] for s in sources],'generalized_holes':['domain Type α','codomain Type β','unary context f : α → β'],'missing_premise_candidate':'Function.Injective f','semantically_certified':False,'novel_mathematics_claim':False}


def counterexample_search():
    """Exhaustive small witness proposals; only subsequent kernel proof refutes."""
    trials=[]
    for name,function in [('identity',lambda x:x),('constant_zero',lambda x:0)]:
        for a,b,c in product(range(2),repeat=3):
            trial={'function':name,'endpoints':[a,b,c],'premises':function(a)==function(b) and function(b)==function(c),'conclusion':a==c}
            trials.append(trial)
            if trial['premises'] and not trial['conclusion']:
                proof=f'  intro h\n  have bad : ({a} : Nat) = {c} := h Nat Nat (fun _ => 0) {a} {b} {c} rfl rfl\n  exact Nat.noConfusion bad'
                return {'status':'candidate_counterexample','trials':trials,'witness':trial,'proof':proof,'certified':False}
    return {'status':'unknown','trials':trials,'certified':False}
