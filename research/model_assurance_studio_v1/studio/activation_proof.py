"""Activation-case covering proofs for restricted ReLU ONNX neural networks.

A verifier checks EVERY branch of z<=0 or z>=0 with exact rational Farkas
multipliers. A leaf either proves a universal affine output inequality or
proves its branch infeasible. No SciPy is imported by the verification path.

A complete tree is a conditional mathematical statement for screened exact-real
semantics, not Lean, IEEE-754, ONNX Runtime or biological/general AI safety.
"""
from __future__ import annotations
from fractions import Fraction
import math
from .relational_kernel import (build,relation,rational,cut,digest,canonical,Unsupported,
                                 MAX_RATIONAL_BITS,MAX_WITNESS)

SCHEMA='pcs-activation-case-cover-real-v0.6'
SCOPE='exact-real-screened-onnx-activation-case-cover'
MAX_LEAVES=64


def unstable_units(spec, poly):
    out=[]
    for node in spec['nodes']:
        if node['op']!='Relu':continue
        for j,(a,b) in enumerate(poly['bounds'][node['inputs'][0]]):
            if a<0<b:out.append((node['out'],j,node['inputs'][0]))
    return out


def augmented(poly, units, phases):
    """Proof branches cover z<=0 and z>=0; the ReLU equalities follow.

    inactive: z<=0 and y<=0 (base already y>=0);
    active: z>=0 and y<=z (base already y>=z).
    """
    rows=list(poly['rows'])
    for (name,j,source),state in phases:
        x=poly['variables'][source][j];y=poly['variables'][name][j]
        if state=='inactive':rows.extend([({x:Fraction(1)},Fraction(0)),({y:Fraction(1)},Fraction(0))])
        elif state=='active':rows.extend([({x:Fraction(-1)},Fraction(0)),({y:Fraction(1),x:Fraction(-1)},Fraction(0))])
        else:raise Unsupported('invalid phase state')
    return rows


def _verify_dual(rows, count, target, limit, witness, contradiction=False):
    if not isinstance(witness,list) or not 1<=len(witness)<=MAX_WITNESS:return False
    a={}; b=Fraction(0);seen=set()
    for term in witness:
        if not isinstance(term,list) or len(term)!=2 or type(term[0]) is not int:return False
        ix=term[0]
        if ix in seen or ix<0 or ix>=len(rows):return False
        seen.add(ix)
        m=rational(term[1])
        if m<=0:return False
        rr,bb=rows[ix]
        b=cut(b+m*bb)
        for k,v in rr.items():
            a[k]=cut(a.get(k,Fraction(0))+m*v)
    a={k:v for k,v in a.items() if v}
    if a!=target:return False
    return b<0 if contradiction else b<=limit


def verify(raw_model, certificate):
    try:
        from .dense_nn import screen_onnx
        if not isinstance(certificate,dict) or set(certificate)!={'schema','scope','model_sha256','input_box','relation','tree','leaves','certificate_sha256'}:
            return False,'certificate structure'
        if certificate['schema']!=SCHEMA or certificate['scope']!=SCOPE:
            return False,'scope/schema mismatch'
        if len(canonical(certificate))>400000:return False,'certificate size limit'
        if certificate['certificate_sha256']!=digest(canonical({k:v for k,v in certificate.items() if k!='certificate_sha256'})):
            return False,'certificate digest'
        if digest(raw_model)!=certificate['model_sha256']:return False,'model bytes mismatch'
        spec=screen_onnx(raw_model)
        poly=build(spec,certificate['input_box'])
        rel=certificate['relation']
        if not isinstance(rel,dict) or set(rel)!={'output_coefficients','upper_limit'}:return False,'claim structure'
        cs,upper=relation(rel['output_coefficients'],rel['upper_limit'],spec['output_width'])
        target={i:c for i,c in zip(poly['output_variables'],cs) if c}
        units=unstable_units(spec,poly)
        unit_keys={(name,j):(name,j,source) for name,j,source in units}
        leaves=0;branches=0
        stack=[(certificate['tree'],[],frozenset())]
        while stack:
            node,phases,used=stack.pop()
            if not isinstance(node,dict):return False,'invalid case node'
            kind=node.get('kind')
            if kind=='branch':
                if set(node)!={'kind','node_name','unit','inactive','active'}:return False,'branch fields'
                key=(node['node_name'],node['unit'])
                if type(node['unit']) is not int or key not in unit_keys or key in used:
                    return False,'invalid or repeated phase split'
                branches+=1
                if branches>=MAX_LEAVES:return False,'branch budget'
                u=unit_keys[key];new=used|{key}
                stack.append((node['active'],phases+[(u,'active')],new))
                stack.append((node['inactive'],phases+[(u,'inactive')],new))
            elif kind in ('proved','infeasible'):
                if set(node)!={'kind','multipliers'}:return False,'leaf fields'
                leaves+=1
                if leaves>MAX_LEAVES:return False,'leaf budget'
                rows=augmented(poly,units,phases)
                desired={} if kind=='infeasible' else target
                if not _verify_dual(rows,poly['variable_count'],desired,upper,node['multipliers'],contradiction=kind=='infeasible'):
                    return False,'Farkas witness failed in a leaf'
            else:return False,'incomplete proof tree'
        if leaves!=certificate['leaves'] or leaves!=branches+1:return False,'invalid coverage/leaf count'
        return True,{'status':'PROVED_CONDITIONALLY','fully_checked_cases':leaves,
                     'phase_splits':branches,'property':'output_coefficients dot outputs <= upper_limit',
                     'trust_boundary':'Exact-real screened ONNX + Python rational checker; not Lean or runtime'}
    except Exception as exc:
        return False,type(exc).__name__+': '+str(exc)[:130]


def _repair_dual(rows,poly,original,goal,limit,*,infeasible=False):
    """Convert an approximate nonnegative LP dual to exact rationals.

    Every variable has preconstructed two-sided rational bounds. Use them to
    correct residual components exactly; verify final identity and RHS.
    """
    multipliers={i:Fraction(float(x)).limit_denominator(1000000)
                 for i,x in enumerate(original) if math.isfinite(float(x)) and float(x)>1e-9}
    multipliers={k:v for k,v in multipliers.items() if v>0}
    represented=[Fraction(0)]*poly['variable_count']
    for k,q in multipliers.items():
        for j,v in rows[k][0].items():represented[j]=cut(represented[j]+q*v)
    for j,v in enumerate(represented):
        delta=cut(goal[j]-v)
        if delta:
            ix=poly['bound_ids'][j][0 if delta>0 else 1]
            if ix is None:raise Unsupported('missing bound row')
            multipliers[ix]=cut(multipliers.get(ix,Fraction(0))+abs(delta))
    terms=[[k,str(v)] for k,v in sorted(multipliers.items()) if v>0]
    if len(terms)>MAX_WITNESS or not _verify_dual(rows,poly['variable_count'],
                                                  {j:v for j,v in enumerate(goal) if v},limit,terms,
                                                  contradiction=infeasible):
        return None
    return terms


def _suggest_infeasible(rows,poly,*,timeout):
    import numpy as np
    from scipy.optimize import linprog
    n=poly['variable_count'];m=len(rows)
    A=np.zeros((n+1,m),dtype=float)
    rhs=np.zeros(n+1,dtype=float);rhs[-1]=1.
    b=np.empty(m)
    for i,(r,limit) in enumerate(rows):
        b[i]=float(limit);A[-1,i]=1.
        for j,v in r.items():A[j,i]=float(v)
    res=linprog(b,A_eq=A,b_eq=rhs,bounds=[(0,None)]*m,method='highs',options={'time_limit':timeout})
    if not res.success or res.fun is None or res.fun>=-1e-8:return None
    return _repair_dual(rows,poly,res.x,[Fraction(0)]*n,Fraction(0),infeasible=True)


def _suggest_property(rows,poly,target,limit,*,timeout):
    import numpy as np
    from scipy.optimize import linprog
    n=poly['variable_count'];m=len(rows)
    A=np.zeros((m,n),dtype=float);b=np.empty(m,dtype=float)
    c=np.zeros(n,dtype=float)
    for j,v in target.items():c[j]=float(v)
    for i,(r,upper) in enumerate(rows):
        b[i]=float(upper)
        for j,v in r.items():A[i,j]=float(v)
    ans=linprog(-c,A_ub=A,b_ub=b,bounds=[(None,None)]*n,method='highs',options={'time_limit':timeout})
    if ans.success:
        proposed=_repair_dual(rows,poly,-np.asarray(ans.ineqlin.marginals),
                              [target.get(i,Fraction(0)) for i in range(n)],limit)
        if proposed is not None:return 'proved',proposed
    elif ans.status==2:
        proposed=_suggest_infeasible(rows,poly,timeout=timeout)
        if proposed is not None:return 'infeasible',proposed
    return None,None


def propose(raw_model,input_box,coefficients,upper_limit,*,max_leaves=16,timeout=3):
    try:
        from .dense_nn import screen_onnx
        if type(max_leaves) is not int or not 1<=max_leaves<=MAX_LEAVES:raise Unsupported('leaf budget')
        if not 0.5<=timeout<=10:raise Unsupported('timeout')
        spec=screen_onnx(raw_model);poly=build(spec,input_box)
        cs,limit=relation(coefficients,upper_limit,spec['output_width'])
        target={i:c for i,c in zip(poly['output_variables'],cs) if c}
        units=unstable_units(spec,poly)
        count=[0]
        class Open(Exception):pass
        def visit(phases,used):
            rows=augmented(poly,units,phases)
            typ,cert=_suggest_property(rows,poly,target,limit,timeout=timeout)
            if cert is not None:
                count[0]+=1
                if count[0]>max_leaves:raise Open('case leaf budget exhausted')
                return {'kind':typ,'multipliers':cert}
            nextu=next((u for u in units if (u[0],u[1]) not in used),None)
            if nextu is None:raise Open('no proof for at least one activation region')
            if len(used)>=12:raise Open('activation branch depth budget exhausted')
            if count[0]+2>max_leaves:raise Open('not enough budget to complete both branches')
            key=(nextu[0],nextu[1])
            inactive=visit(phases+[(nextu,'inactive')],used|{key})
            active=visit(phases+[(nextu,'active')],used|{key})
            return {'kind':'branch','node_name':nextu[0],'unit':nextu[1],
                    'inactive':inactive,'active':active}
        try:tree=visit([],frozenset())
        except Open as ex:return {'status':'OPEN','reason':str(ex)}
        cert={'schema':SCHEMA,'scope':SCOPE,'model_sha256':digest(raw_model),
              'input_box':[[str(rational(a)),str(rational(b))] for a,b in input_box],
              'relation':{'output_coefficients':[str(v) for v in cs],'upper_limit':str(limit)},
              'tree':tree,'leaves':count[0]}
        cert['certificate_sha256']=digest(canonical(cert))
        good,info=verify(raw_model,cert)
        if not good:return {'status':'OPEN','reason':'exact case-cover verifier rejected proposed tree: '+str(info)}
        return {'status':'PROVED_CONDITIONALLY','certificate':cert,'verification':info}
    except Exception as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:180]}
