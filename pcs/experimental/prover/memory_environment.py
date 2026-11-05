"""Grounded Std retrieval plus immutable, independently rebuilt lemma memory.

The curated terms below are trusted source, never model/user-supplied Lean.
Every alias is elaborated and axiom-audited against the actual Lean environment.
The memory and primitive catalog have separate byte identities. No predictions
or producer receipts can authorize an entry.
"""
from copy import deepcopy
from pathlib import Path
import hashlib

from .library import LibraryEnvironment,FORMAT
from .environment import candidates,act,reference_expression,_symbolic_priority
from .induction_language import formalize
from .induction_ir import digest,theorem
from .discovery import spine,type_of

PRIMITIVES = [
 ('nat_left_cancel','For all natural numbers a, b and c, if (a + b) equals (a + c) then b equals c.','intro a b c h; exact Nat.add_left_cancel h','Nat.add_left_cancel'),
 ('nat_right_cancel','For all natural numbers a, b and c, if (a + c) equals (b + c) then a equals b.','intro a b c h; exact Nat.add_right_cancel h','Nat.add_right_cancel'),
 ('nat_succ_cancel','For all natural numbers a and b, if the successor of a equals the successor of b then a equals b.','intro a b h; exact Nat.succ.inj h','Nat.succ.inj'),
 ('nat_succ_nonzero','For all natural numbers n, not (the successor of n equals 0).','intro n; exact Nat.succ_ne_zero n','Nat.succ_ne_zero'),
 ('nat_order_cancel','For all natural numbers a, b and c, if (a + c) ≤ (b + c) then a ≤ b.','intro a b c h; exact Nat.le_of_add_le_add_right h','Nat.le_of_add_le_add_right'),
 ('nat_succ_order','For all natural numbers a and b, if the successor of a ≤ the successor of b then a ≤ b.','intro a b h; exact Nat.succ_le_succ_iff.mp h','Nat.succ_le_succ_iff'),
 ('nat_distribution','For all natural numbers a, b and c, a * (b + c) equals ((a * b) + (a * c)).','intro a b c; exact Nat.left_distrib a b c','Nat.left_distrib'),
 ('list_reverse_size','For all lists of natural numbers xs, the length of (the reversal of xs) equals the length of xs.','intro xs; exact List.length_reverse','List.length_reverse'),
 ('list_reverse_append','For all lists of natural numbers xs and ys, the reversal of (xs appended to ys) equals ((the reversal of ys) appended to (the reversal of xs)).','intro xs ys; exact List.reverse_append','List.reverse_append'),
 ('list_reverse_twice','For all lists of natural numbers xs, the reversal of (the reversal of xs) equals xs.','intro xs; exact List.reverse_reverse xs','List.reverse_reverse'),
 ('list_left_cancel','For all lists of natural numbers xs, ys and zs, if (xs appended to ys) equals (xs appended to zs) then ys equals zs.','intro xs ys zs h; exact (List.append_right_inj xs).mp h','List.append_right_inj'),
 ('list_right_cancel','For all lists of natural numbers xs, ys and zs, if (xs appended to zs) equals (ys appended to zs) then xs equals ys.','intro xs ys zs h; exact (List.append_left_inj zs).mp h','List.append_left_inj'),
 ('list_reverse_cancel','For all lists of natural numbers xs and ys, if the reversal of xs equals the reversal of ys then xs equals ys.','intro xs ys h; exact List.reverse_inj.mp h','List.reverse_inj'),
]

def primitive_specs():
    specs=[]
    for i,(identity,statement,proof,source_name) in enumerate(PRIMITIVES):
        parsed=formalize(statement)
        if parsed['status']!='supported':raise ValueError('primitive failed typed lowering: '+identity)
        specs.append({'id':identity,'name':f'PCSKnownL{i}','goal':parsed['candidates'][0]['ir'],
                      'proof':proof,'source_name':source_name,'license':'Apache-2.0',
                      'source':'Lean 4.28 Std, commit 7e01a1bf5c70fc6167d49c345d3bf80596e9a79b'})
    return specs

def conclusion(expr):
    while expr['kind']=='forall':expr=expr['children'][1]
    return expr

def universal_view(expr):
    """Rebase de Bruijn references across premise and conclusion scopes."""
    scope=[];premises=[]
    def rebase(e,names):
        if e['kind']=='bound':
            index=int(e['value'])
            if index>=len(names):raise ValueError('unbound catalog reference')
            return {**e,'value':names[-1-index]}
        return {**e,'children':[rebase(c,names+[f'nested{len(names)}'] if e['kind'] in {'forall','lambda'} and i==1 else names) for i,c in enumerate(e['children'])]}
    while expr['kind']=='forall':
        domain,body=expr['children']
        try:type_of(domain);variable=True
        except ValueError:variable=False
        if not variable:premises.append(rebase(domain,scope))
        scope.append(('q' if variable else 'proof')+str(len(scope)))
        expr=body
    return rebase(expr,scope),premises

def local_propositions(state):
    result=[]
    def visit(e):
        result.append(e);h,args=spine(e)
        if h['kind']=='constant' and h['value'].split(':')[0]=='And' and len(args)==2:
            for child in args:visit(child)
    for local in state['goals'][0]['locals']:
        try:type_of(local['expression'])
        except ValueError:visit(local['expression'])
    return result

def grounded_application(state,premise):
    body,conditions=universal_view(premise);bindings={}
    if not pattern_matches(body,state['goals'][0]['expression'],bindings):return False
    for condition in conditions:
        found=False
        for local in local_propositions(state):
            proposed=deepcopy(bindings)
            if pattern_matches(condition,local,proposed):
                bindings=proposed;found=True;break
        if not found:return False
    return True

def bound_normal(e,scope=()):
    value=e['value']
    if e['kind']=='bound' and value.isdigit():
        i=int(value);value=scope[-1-i] if i<len(scope) else 'external'+value
    return {**e,'value':value,'children':[bound_normal(c,(*scope,'b'+str(len(scope))) if e['kind'] in {'forall','lambda'} and i==1 else scope) for i,c in enumerate(e['children'])]}

def pattern_matches(pattern,expr,bindings=None,_normalized=False):
    """Repeated bound variables must have consistent instantiations.

    A matching result is retrieval evidence, never a proof of applicability.
    """
    bindings={} if bindings is None else bindings
    if not _normalized:pattern,expr=bound_normal(pattern),bound_normal(expr)
    if pattern['kind']=='bound':
        key=pattern['value']
        if key not in bindings:bindings[key]=expr;return True
        return bindings[key]==expr
    value_equal=pattern['value']==expr['value'] or pattern['kind'] in {'forall','lambda'}
    return pattern['kind']==expr['kind'] and value_equal and len(pattern['children'])==len(expr['children']) and all(pattern_matches(a,b,bindings,True) for a,b in zip(pattern['children'],expr['children']))

def contains_match(expr,pattern):
    return pattern_matches(pattern,expr) or any(contains_match(c,pattern) for c in expr['children'])

def residual_distance(a,b):
    if a==b:return 0
    if a['kind']!=b['kind'] or a['value']!=b['value'] or len(a['children'])!=len(b['children']):
        def size(e):return 1+sum(size(c) for c in e['children'])
        return size(a)+size(b)
    return sum(residual_distance(x,y) for x,y in zip(a['children'],b['children']))

def rewrite_projection(expr,pattern,replacement):
    bindings={}
    def instantiate(e):
        if e['kind']=='bound':
            if e['value'] not in bindings:raise ValueError('uninstantiated rewrite variable')
            return deepcopy(bindings[e['value']])
        return {**e,'children':[instantiate(c) for c in e['children']]}
    if pattern_matches(pattern,expr,bindings):
        try:return instantiate(replacement),True
        except ValueError:pass
    children=deepcopy(expr['children'])
    for i,child in enumerate(children):
        changed,ok=rewrite_projection(child,pattern,replacement)
        if ok:children[i]=changed;return {**expr,'children':children},True
    return expr,False

def premise_score(state,action):
    if not state.get('goals'):return -100.
    target=state['goals'][0]['expression']
    if action['kind']=='intro' and target['kind']=='forall':return 20.
    if action['kind'] in {'induct_nat','induct_list'}:
        proofs=[]
        for local in state['goals'][0]['locals']:
            try:type_of(local['expression'])
            except ValueError:proofs.append(local['expression'])
        if action['kind']=='induct_list':return 1. if proofs else 9.
        def has_succ(e):return e['kind']=='constant' and e['value'].split(':')[0]=='Nat.succ' or any(has_succ(c) for c in e['children'])
        if any(has_succ(p) for p in proofs):return 1. if len(proofs)>1 else 10.
    score=float(_symbolic_priority(state,action))
    catalog={e['name']:e['expression'] for e in state.get('available_lemmas',[])}
    premise=catalog.get(action['argument']) or (reference_expression(state,action['argument']) if type(action['argument']) is str and action['kind'] in {'apply','rewrite','rewrite_back'} else None)
    if premise is None:return score
    body,_=universal_view(premise);head,args=spine(body)
    if action['kind']=='apply':
        if pattern_matches(premise,target):return 18.
        if grounded_application(state,premise):return 15.
        # A specific local rule can be useful backward chaining even when its
        # antecedent remains to be proved. Global generic cancellation rules
        # receive no such promotion merely for matching an arbitrary equality.
        if action['argument'] not in catalog and pattern_matches(body,target):return 11.
        return -4.
    if action['kind'] in {'rewrite','rewrite_back'} and head['kind']=='constant' and head['value'].split(':')[0]=='Eq' and len(args)==3:
        side=args[1 if action['kind']=='rewrite' else 2]
        # A bare quantified variable would match everything and expand rather
        # than compress it. This conservative screen removes that search trap.
        if side['kind']=='bound':return -8.
        if target['kind']=='forall' or not contains_match(target,side):return -4.
        rewritten,ok=rewrite_projection(target,side,args[2 if action['kind']=='rewrite' else 1])
        h,before=spine(target);h2,after=spine(rewritten)
        if ok and h['kind']=='constant' and h['value'].split(':')[0]=='Eq' and len(before)==3 and len(after)==3:
            old_distance=residual_distance(before[1],before[2]);new_distance=residual_distance(after[1],after[2])
            if new_distance==0:return 19.
            if new_distance<old_distance:return 14.+min(2.,(old_distance-new_distance)/20.)
            return -5.
        return 8.
    return score

def structural_rank(state,options):return [premise_score(state,a) for a in options]

class MemoryEnvironment(LibraryEnvironment):
    default_rank=staticmethod(structural_rank)

    def __init__(self,library=None,*,heldout=(),**kwargs):
        self.primitives=primitive_specs()
        self.primitive_catalog_sha256=digest(self.primitives)
        library={'format':FORMAT,'entries':[]} if library is None else library
        if len(library.get('entries',[]))>6:raise ValueError('memory capacity exceeded')
        self.memory_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        super().__init__(library,heldout=heldout,**kwargs)
        for entry in self.catalog:
            entry['origin']='primitive' if entry['name'].startswith('PCSKnownL') else 'discovered_memory'

    def _initial_declarations(self):
        return ''.join(f'theorem {p["name"]} : {theorem(p["goal"])} := by\n  {p["proof"]}\n' for p in self.primitives)

    def _initial_catalog(self):
        entries=[]
        for p in self.primitives:
            audit=self._source(f'#pcs_audit {p["name"]}\n','PCS_KERNEL:')
            if not set(audit['axioms'])<={'propext','Classical.choice','Quot.sound'}:raise ValueError('unapproved primitive axioms')
            entries.append({'name':p['name'],'goal':p['goal'],'kernel':audit,'proof_steps':0,
                            'statement':theorem(p['goal']),'source_name':p['source_name'],
                            'source':p['source'],'license':p['license']})
        return entries

    def _cache_identity(self):return digest([self.library_sha256,self.primitive_catalog_sha256])

    def candidates(self,state):
        options=candidates(state,induction=True)
        if not state.get('goals'):return options
        locals_={l['name'] for g in state['goals'] for l in g['locals']}
        for entry in self.catalog:
            if entry['name'] in locals_:continue
            options.append(act('apply',entry['name']))
            head,args=spine(conclusion(entry['kernel']['expression']))
            if head['kind']=='constant' and head['value'].split(':')[0]=='Eq':
                options.extend([act('rewrite',entry['name']),act('rewrite_back',entry['name'])])
        head,args=spine(state['goals'][0]['expression'])
        if head['kind']=='constant' and head['value'].split(':')[0]=='Eq' and len(args)==3 and args[0]['kind']=='constant' and args[0]['value'].split(':')[0]=='Nat':
            for a in [act('normalize','nat'),act('simp')]:
                if a not in options:options.append(a)
        # Backward local equalities were absent from the original action provider.
        for local in state['goals'][0]['locals']:
            if local['expression']['kind']=='application':
                head,args=spine(local['expression'])
                if head['kind']=='constant' and head['value'].split(':')[0]=='Eq':
                    a=act('rewrite_back',local['name'])
                    if a not in options:options.append(a)
        # Lean's induction tactic preserves the hypotheses; the independent
        # kernel check remains mandatory. The original environment's narrower
        # no-hypothesis action domain is preserved for historical checkpoints.
        used={l['name'] for g in state['goals'] for l in g['locals']}
        fresh=[f'h{i}' for i in range(100) if f'h{i}' not in used][:3]
        for local in state['goals'][0]['locals']:
            if not local['name'].startswith('h') or not local['name'][1:].isdigit():continue
            if local['type']=='Nat' and len(fresh)>=2:
                a=act('induct_nat',' '.join([local['name'],*fresh[:2]]))
                if a not in options:options.append(a)
            if local['type']=='List Nat' and len(fresh)>=3:
                a=act('induct_list',' '.join([local['name'],*fresh]))
                if a not in options:options.append(a)
        if state['goals'][0]['expression']['kind']=='forall':
            # Introducing a binder is the general move. Keep genuinely matched
            # whole-theorem shortcuts; avoid wasting the entire successor beam
            # on irrelevant tactics under unopened binders.
            catalog={e['name']:e['kernel']['expression'] for e in self.catalog}
            return [a for a in options if a['kind']=='intro' or a['kind']=='apply' and a['argument'] in catalog and pattern_matches(catalog[a['argument']],state['goals'][0]['expression'])]
        return options[:96]

    def verify(self,goal,actions):
        r=super().verify(goal,actions)
        r.update(environment='pcs-grounded-memory-v1',primitive_catalog_sha256=self.primitive_catalog_sha256,
                 memory_source_sha256=self.memory_source_sha256)
        return r

def replay_memory_receipt(goal,receipt,*,heldout=(),cache=None):
    if receipt.get('goal_sha256')!=digest(goal) or receipt.get('statement')!=theorem(goal):raise ValueError('changed original goal')
    if receipt.get('library_sha256')!=digest(receipt.get('library')):raise ValueError('forged memory identity')
    env=MemoryEnvironment(receipt['library'],heldout=heldout,cache=cache,timeout=30)
    try:
        fresh=env.verify(goal,receipt['actions'])
        for field in ['proof','primitive_catalog_sha256','memory_source_sha256','library_declarations','library_sha256','adapter_sha256','lean']:
            if fresh.get(field)!=receipt.get(field):raise ValueError('memory/primitive/checker binding mismatch')
        return fresh
    finally:env.close()
