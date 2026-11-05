"""Bounded exact rational interval evaluator for a small ONNX elementwise subset.

The result describes real arithmetic under stated bounds and limited graph
semantics. Its implementation is NOT Lean verified or a certificate of IEEE-754
behavior. Unsupported operators / excess precision cause explicit abstention.
"""
from __future__ import annotations
from fractions import Fraction
import math

SUPPORTED={'Identity':1,'Neg':1,'Relu':1,'Abs':1,'Add':2,'Sub':2,'Mul':2,'Div':2}
MAX_BITS=512
MAX_NODES=512

def guard(x):
    if max(x.numerator.bit_length(),x.denominator.bit_length())>MAX_BITS:
        raise ArithmeticError('Exact rational computation exceeded the 512-bit budget')
    return x

def compute(op, vals):
    if op not in SUPPORTED or len(vals)!=SUPPORTED[op]:
        raise ValueError(f'Unsupported operator or arity: {op}')
    (a,b)=vals[0]
    if op=='Identity':out=a,b
    elif op=='Neg':out=-b,-a
    elif op=='Relu':out=max(a,Fraction(0)),max(b,Fraction(0))
    elif op=='Abs':out=(Fraction(0) if a<=0<=b else min(abs(a),abs(b))),max(abs(a),abs(b))
    else:
        c,d=vals[1]
        if op=='Add':out=a+c,b+d
        elif op=='Sub':out=a-d,b-c
        elif op=='Mul':
            ps=(a*c,a*d,b*c,b*d);out=min(ps),max(ps)
        else:
            if c<=0<=d:raise ValueError('Division by an interval including zero; no real-valued enclosure')
            lo,hi=min(Fraction(1,c),Fraction(1,d)),max(Fraction(1,c),Fraction(1,d))
            ps=(a*lo,a*hi,b*lo,b*hi);out=min(ps),max(ps)
    for f in out:guard(f)
    return out

def enclose(nodes,inputs,outputs,initializers,policy):
    if len(nodes)>MAX_NODES:raise ValueError('Exact rational checker only supports 512 nodes')
    left=Fraction(str(policy['input_min']));right=Fraction(str(policy['input_max']))
    env={name:(left,right) for name in inputs}
    for name, bounds in initializers.items():
        if bounds is None:raise ValueError('Unavailable initializer data')
        # Inspectable binary floats convert exactly to their finite rationals.
        if name not in env:env[name]=(Fraction.from_float(float(bounds[0])),Fraction.from_float(float(bounds[1])))
    for ins,outs,op,domain,nested in nodes:
        if domain not in ('','ai.onnx') or nested or len(outs)!=1 or not outs[0]:
            raise ValueError('Unsupported domain, nested graph, or operator output count')
        if any(x not in env for x in ins):raise ValueError('Unbound operator input')
        if outs[0] in env:raise ValueError('Ambiguous output definition')
        env[outs[0]]=compute(op,[env[k] for k in ins])
    if any(x not in env for x in outputs):raise ValueError('Unbound graph output')
    lo=min(env[o][0] for o in outputs);hi=max(env[o][1] for o in outputs)
    req_lo=Fraction(str(policy['output_min']));req_hi=Fraction(str(policy['output_max']))
    return {'interval':(lo,hi),'target':(req_lo,req_hi),
            'exact_fractions':[str(lo),str(hi)],
            'conclusion':'WITHIN' if req_lo<=lo and hi<=req_hi else
                         ('DISJOINT' if hi<req_lo or lo>req_hi else 'OVERLAP')}
