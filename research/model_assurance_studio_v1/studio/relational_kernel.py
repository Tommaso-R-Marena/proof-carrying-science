"""Small, fail-closed exact-rational proof checker for screened ONNX ReLU models.

All computations here are stdlib Fractions. We accept a Farkas witness consisting
of nonnegative multipliers over an explicitly reconstructed *outer polytope*.
We reconstruct exact interval bounds from model input and float32 weights,
independently of the optimizer, then verify the dual identity and inequality.

Trust boundary: Python, Fraction, this code and screened ONNX decoder.
This is NOT a Lean kernel result, IEEE-754 proof, or a general ONNX verifier.
"""
from __future__ import annotations
import hashlib
import json
import math
from fractions import Fraction

SCHEMA = 'pcs-relational-farkas-real-v0.6'
MAX_VARIABLES = 256
MAX_ROWS = 1800
MAX_WITNESS = 1800
MAX_RATIONAL_BITS = 512

class Unsupported(ValueError): pass


def rational(value):
    if isinstance(value, str):
        if not value or len(value) > 200 or any(c not in '-+0123456789/.eE' for c in value):
            raise Unsupported('invalid rational encoding')
        # Resource preflight: Fraction("1e100000000") attempts to materialize
        # an enormous power of ten *before* we can apply MAX_RATIONAL_BITS.
        # Reject excessive exponents without allocating the giant integer.
        # This applies to every reviewer/certificate rational parsed by PCS.
        if 'e' in value.lower():
            parts=value.lower().split('e')
            if len(parts)!=2:
                raise Unsupported('invalid rational exponent')
            exponent=parts[1]
            digits=exponent.lstrip('+-')
            if not digits.isdigit() or len(digits)>4 or abs(int(exponent))>MAX_RATIONAL_BITS:
                raise Unsupported('rational exponent resource limit')
        q = Fraction(value)
    elif isinstance(value, float):
        if not math.isfinite(value): raise Unsupported('nonfinite rational')
        q = Fraction.from_float(value)
    elif type(value) is int:
        q = Fraction(value)
    else:
        raise Unsupported('untrusted rational type')
    if max(q.numerator.bit_length(),q.denominator.bit_length()) > MAX_RATIONAL_BITS:
        raise Unsupported('rational resource limit')
    return q


def cut(q):
    return rational(str(q))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()


def relation(coefficients, limit, width):
    if not isinstance(coefficients,list) or len(coefficients)!=width or width<1 or width>16:
        raise Unsupported('output coefficient vector length must equal output width')
    c=[rational(x) for x in coefficients]
    if not any(c):raise Unsupported('zero output relation')
    return c,rational(limit)


def _sum_affine(terms, bias=Fraction(0)):
    # interval enclosure of a rational affine expression
    a=b=cut(bias)
    for coef,(lo,hi) in terms:
        x=cut(coef)
        a=cut(a+min(x*lo,x*hi))
        b=cut(b+max(x*lo,x*hi))
    return a,b


def build(spec, input_box):
    """Reconstruct a sound outer polytope in deterministic order.

    Records are (sparse coefficient map, upper bound): sum a_i x_i <= b.
    Every actual exact-real execution lies in this outer polytope.
    """
    n=spec['input_width']
    if not isinstance(input_box,list) or len(input_box)!=n:raise Unsupported('input box shape')
    box=[]
    for pair in input_box:
        if not isinstance(pair,(list,tuple)) or len(pair)!=2:raise Unsupported('input bounds format')
        a,b=rational(pair[0]),rational(pair[1])
        if a>b:raise Unsupported('inverted input box')
        box.append((a,b))
    weights=spec['weights']; rows=[]; bounds={}; variables={};bound_ids={};count=0
    def row(pairs,rhs):
        r={}
        for idx,x in pairs:
            x=cut(x)
            if x:r[idx]=cut(r.get(idx,Fraction(0))+x)
        r={k:v for k,v in r.items() if v}
        if not r: # tautology or contradiction: latter should not arise
            if cut(rhs)<0:raise Unsupported('inconsistent constructed polytope')
            return None
        if len(rows)>=MAX_ROWS:raise Unsupported('too many linear constraints')
        rows.append((r,cut(rhs)))
        return len(rows)-1
    def assign(name,bds):
        nonlocal count
        width=len(bds)
        if count+width>MAX_VARIABLES:raise Unsupported('too many analysis variables')
        ids=list(range(count,count+width));count+=width
        bounds[name]=bds;variables[name]=ids
        for j,(lo,hi) in enumerate(bds):
            uid=row([(ids[j],1)],hi)
            lid=row([(ids[j],-1)],-lo)
            bound_ids[ids[j]]=(uid,lid)
        return ids
    assign(spec['input'],box)
    for node in spec['nodes']:
        op,ins,name=node['op'],node['inputs'],node['out']
        if name in variables:raise Unsupported('duplicate node output')
        if op in ('MatMul','Gemm'):
            source=ins[0]
            if source not in variables:raise Unsupported('missing activation')
            w=weights[ins[1]]
            k,m=w['shape'];old=variables[source]
            if len(old)!=k:raise Unsupported('matrix shape mismatch')
            bds=[];expressions=[]
            for j in range(m):
                expression=[(cut(rational(w['values'][i*m+j])),old[i]) for i in range(k)]
                bias=cut(rational(weights[ins[2]]['values'][j])) if op=='Gemm' else Fraction(0)
                bds.append(_sum_affine([(coef,bounds[source][i]) for i,(coef,_) in enumerate(expression)],bias))
                expressions.append((expression,bias))
            fresh=assign(name,bds)
            for y,(expression,bias) in zip(fresh,expressions):
                parts=[(y,1)]+[(idx,-coef) for coef,idx in expression]
                row(parts,bias)
                row([(idx,-v) for idx,v in parts],-bias)
        elif op=='Add':
            dyn=[v for v in ins if v not in weights]
            const=[v for v in ins if v in weights]
            if len(dyn) not in (1,2) or len(dyn)+len(const)!=2:raise Unsupported('unsupported Add')
            if len(dyn)==2 and const:raise Unsupported('ambiguous Add')
            k=len(variables[dyn[0]])
            if any(len(variables[d])!=k for d in dyn):raise Unsupported('Add shape mismatch')
            bds=[]; expressions=[]
            for j in range(k):
                exp=[(Fraction(1),variables[d][j]) for d in dyn]
                bias=sum((rational(weights[z]['values'][j]) for z in const),Fraction(0))
                a,b=_sum_affine([(Fraction(1),bounds[d][j]) for d in dyn],bias)
                bds.append((a,b)); expressions.append((exp,bias))
            fresh=assign(name,bds)
            for y,(exp,bias) in zip(fresh,expressions):
                p=[(y,1)]+[(z,-v) for v,z in exp]
                row(p,bias);row([(i,-v) for i,v in p],-bias)
        elif op in ('Identity','Relu'):
            source=ins[0]
            if source not in variables:raise Unsupported('missing input activation')
            original=bounds[source]
            outb=[(max(0,a),max(0,b)) if op=='Relu' else (a,b) for a,b in original]
            fresh=assign(name,outb)
            for j,y in enumerate(fresh):
                x=variables[source][j];lo,hi=original[j]
                if op=='Identity' or lo>=0:
                    row([(y,1),(x,-1)],0);row([(y,-1),(x,1)],0)
                elif hi<=0:
                    row([(y,1)],0);row([(y,-1)],0)
                else:
                    # Convex-hull overapproximation of y=max(0,x) on [lo,hi]:
                    # -y<=0, x-y<=0, (hi-lo)*y-hi*x<=-hi*lo
                    row([(y,-1)],0);row([(x,1),(y,-1)],0)
                    row([(y,hi-lo),(x,-hi)],-hi*lo)
        else:
            raise Unsupported('unknown operation')
    if spec['output'] not in variables:raise Unsupported('output missing')
    if len(variables[spec['output']])!=spec['output_width']:raise Unsupported('output width')
    return {'rows':rows,'variable_count':count,'variables':variables,'bounds':bounds,
            'bound_ids':bound_ids,'output_variables':variables[spec['output']], 'input_box':box}


def check(raw_model, certificate):
    """Fail closed, returning (bool, reason). Does not call an optimizer."""
    try:
        from .dense_nn import screen_onnx  # parser is explicit TCB, never numerical optimizer
        if not isinstance(certificate,dict) or set(certificate)!={'schema','model_sha256','input_box','relation','multipliers','certificate_sha256','scope'}:
            return False,'certificate structure'
        if certificate['schema']!=SCHEMA or certificate['scope']!='exact-real-screened-onnx-outer-polytope':
            return False,'unknown claim scope'
        if len(canonical(certificate))>300000:return False,'certificate size budget'
        expected=digest(canonical({k:v for k,v in certificate.items() if k!='certificate_sha256'}))
        if certificate['certificate_sha256']!=expected:return False,'certificate digest mismatch'
        if certificate['model_sha256']!=digest(raw_model):return False,'model byte digest mismatch'
        spec=screen_onnx(raw_model)
        poly=build(spec,certificate['input_box'])
        rel=certificate['relation']
        if not isinstance(rel,dict) or set(rel)!={'output_coefficients','upper_limit'}:
            return False,'invalid output relation'
        coeffs,limit=relation(rel['output_coefficients'],rel['upper_limit'],spec['output_width'])
        target={i:coef for i,coef in zip(poly['output_variables'],coeffs) if coef}
        multipliers=certificate['multipliers']
        if not isinstance(multipliers,list) or not 1<=len(multipliers)<=MAX_WITNESS:
            return False,'malformed Farkas multipliers'
        accum={};rhs=Fraction(0);seen=set()
        for term in multipliers:
            if not isinstance(term,list) or len(term)!=2 or type(term[0]) is not int:
                return False,'malformed multiplier entry'
            idx,qtext=term
            if idx in seen or idx<0 or idx>=len(poly['rows']):return False,'duplicate/out-of-range multiplier'
            seen.add(idx)
            q=rational(qtext)
            if q<=0:return False,'nonpositive multiplier'
            row,upper=poly['rows'][idx]
            rhs=cut(rhs+q*upper)
            for col,v in row.items():
                accum[col]=cut(accum.get(col,Fraction(0))+q*v)
        accum={k:v for k,v in accum.items() if v}
        if accum!=target:return False,'Farkas dual vector identity failed'
        if rhs>limit:return False,'Farkas upper bound is insufficient'
        return True,{'status':'PROVED_CONDITIONALLY','verified_upper_bound':str(rhs),
                     'required_upper_limit':str(limit),'variables':poly['variable_count'],
                     'linear_constraints':len(poly['rows']),'nonzero_multipliers':len(multipliers),
                     'trust_boundary':'Python/Fraction + ONNX subset decoder + exact-relaxation constructor; not Lean or IEEE float32'}
    except Exception as exc:
        # Uploaded/malformed models and proofs never crash the reviewer CLI.
        return False,type(exc).__name__+': '+str(exc)[:140]
