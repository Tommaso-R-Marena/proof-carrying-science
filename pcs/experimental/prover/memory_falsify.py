"""Cheap bounded falsification followed by proof of the original claim's negation.

Sampling never establishes a universal theorem. Only a fresh Lean axiom-audited
proof of ¬ originalGoal authorizes a counterexample result. Terms are generated
from a finite typed whitelist, never submitted Lean source.
"""
from itertools import product
from .induction_ir import theorem,expression,canonical_declaration,digest,TYPES

DOMAINS={'Nat':[0,1,2],'Int':[0,1,2],'Prop':[False,True],
         'NatList':[[],[0],[1],[0,1]],'NatFn':['zero','identity','successor'],
         'NatPred':['always','never','is_zero']}

def evaluate(e,values):
    op=e['op']
    if op=='var':return values[e['name']]
    if op=='number':return e['value']
    if op=='nil':return []
    if op in {'true','false'}:return op=='true'
    if op in {'forall','exists'}:
        results=[bool(evaluate(e['body'],{**values,e['name']:v})) for v in DOMAINS[e['type']]]
        return all(results) if op=='forall' else any(results)
    if op=='cons':return [evaluate(e['head'],values)]+evaluate(e['tail'],values)
    if op=='apply':
        f=evaluate(e['fn'],values);a=evaluate(e['arg'],values)
        return {'zero':lambda:0,'identity':lambda:a,'successor':lambda:a+1,
                'always':lambda:True,'never':lambda:False,'is_zero':lambda:a==0}[f]()
    if 'arg' in e:
        a=evaluate(e['arg'],values)
        return {'succ':lambda:a+1,'length':lambda:len(a),'reverse':lambda:list(reversed(a)),
                'not':lambda:not a}[op]()
    a,b=evaluate(e['left'],values),evaluate(e['right'],values)
    return {'and':lambda:a and b,'or':lambda:a or b,'implies':lambda:not a or b,
            'iff':lambda:bool(a)==bool(b),'eq':lambda:a==b,'le':lambda:a<=b,
            'add':lambda:a+b,'mul':lambda:a*b,'append':lambda:a+b}[op]()

def witness_term(t,v):
    if not any(type(v) is type(x) and digest(v)==digest(x) for x in DOMAINS[t]):
        raise ValueError('witness outside typed finite whitelist')
    if t in {'Nat','Int'}:return f'({v} : {t})'
    if t=='Prop':return 'True' if v else 'False'
    if t=='NatList':return '(['+','.join(str(n) for n in v)+'] : List Nat)'
    return {'zero':'(fun (_ : Nat) => (0 : Nat))','identity':'(fun (x : Nat) => x)',
            'successor':'(fun (x : Nat) => Nat.succ x)','always':'(fun (_ : Nat) => True)',
            'never':'(fun (_ : Nat) => False)','is_zero':'(fun (x : Nat) => x = 0)'}[v]

def check_witness(env,goal,witness):
    goal=canonical_declaration(goal);statement=theorem(goal)
    if set(witness)!={b['name'] for b in goal['binders']}:raise ValueError('witness variables mismatch')
    terms=[witness_term(b['type'],witness[b['name']]) for b in goal['binders']]
    declarations=' '.join(f'({b["name"]} : {TYPES[b["type"]]})' for b in goal['binders'])
    body=expression(goal['body'],{b['name']:b['type'] for b in goal['binders']})[1]
    ground=f'((fun {declarations} => {body}) '+ ' '.join(terms)+')' if declarations else body
    instantiated='h '+ ' '.join(terms) if terms else 'h'
    proof=f'intro h\n  have bad := {instantiated}\n  have wrong : ¬ ({ground}) := by decide\n  exact wrong bad'
    kernel=env._source(f'theorem pcs_refuted : ¬ ({statement}) := by\n  {proof}\n#pcs_audit pcs_refuted\n','PCS_KERNEL:')
    if not set(kernel['axioms'])<={'propext','Classical.choice','Quot.sound'}:raise ValueError('unapproved counterexample axioms')
    return {'format':'pcs-memory-counterexample-v1','original_goal_sha256':digest(goal),
            'statement':statement,'witness':witness,'proof':proof,'kernel':kernel,
            'lean':env.version,'adapter_sha256':env.source_sha,'pcs_authority':False}

def falsify(env,goal,*,limit=128):
    if type(limit) is not int or not 1<=limit<=256:raise ValueError('falsification bound')
    goal=canonical_declaration(goal);theorem(goal)
    tested=0;attempts=[]
    for row in product(*(DOMAINS[b['type']] for b in goal['binders'])):
        if tested>=limit:break
        tested+=1;witness={b['name']:v for b,v in zip(goal['binders'],row)}
        try:false=not bool(evaluate(goal['body'],witness))
        except (ValueError,KeyError,TypeError):return {'status':'unsupported_fragment','tested':tested,'receipt':None}
        if not false:continue
        try:
            receipt=check_witness(env,goal,witness)
            return {'status':'verified_counterexample','tested':tested,'receipt':receipt,'attempts':attempts}
        except RuntimeError as ex:attempts.append({'witness':witness,'status':'unchecked_sample','error':str(ex)[-1000:]})
    return {'status':'not_refuted_in_bound','tested':tested,'receipt':None,'attempts':attempts}
