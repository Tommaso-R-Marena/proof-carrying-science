"""Reviewable float32 safety bounds for a *specified*, sequential evaluator.

This is an exact-rational abstract interpreter of the following chosen model:
all scalar multiplications and additions are separately rounded binary32 RN-even;
a matrix dot product iterates over its weights in increasing row index; GEMM bias
is added after the product; Relu/Identity are exact in numerical value.  It does
NOT describe arbitrary ONNX Runtime optimizations, FMA, FTZ, signed zeros, or GPU.
Proof method: interval arithmetic plus monotonicity of RN-even for finite values.
No optimizer is involved. No untrusted model code is executed.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
import json
from .ieee754 import round_value, add_interval, times_constant, UnsupportedFP32
from .relational_kernel import rational
from .dense_nn import screen_onnx, Unsupported

SCHEMA='pcs-fp32-sequential-interval-v0.7'
POLICY_SCHEMA='pcs-fp32-sequential-reviewer-policy-v0.7'
MAX_BOX_DIGITS=256


def _canonical(v)->bytes:
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def digest(v:bytes)->str:
    return sha256(v).hexdigest()


def _bound(q):
    z=rational(q)
    if z.numerator.bit_length()>1024 or z.denominator.bit_length()>1024:
        raise UnsupportedFP32('rational bounds too large')
    return z


def checked_policy(model:bytes, policy:dict):
    if not isinstance(policy,dict) or set(policy)!={'schema','model_sha256','input_box','output_coefficients','upper_limit'} or policy['schema']!=POLICY_SCHEMA:
        raise UnsupportedFP32('reviewer policy shape')
    if policy['model_sha256']!=digest(model):
        raise UnsupportedFP32('reviewer-pinned model digest mismatch')
    spec=screen_onnx(model)
    box=policy['input_box']
    cs=policy['output_coefficients']
    if not isinstance(box,list) or len(box)!=spec['input_width'] or not isinstance(cs,list) or len(cs)!=spec['output_width']:
        raise UnsupportedFP32('reviewer dimension mismatch')
    parsed_box=[]
    for pair in box:
        if not isinstance(pair,list) or len(pair)!=2:raise UnsupportedFP32('invalid input box entry')
        a,b=_bound(pair[0]),_bound(pair[1])
        if a>b:raise UnsupportedFP32('reversed input box entry')
        parsed_box.append((a,b))
    coeffs=[_bound(x) for x in cs]
    if not any(coeffs):raise UnsupportedFP32('zero relation')
    upper=_bound(policy['upper_limit'])
    return spec,parsed_box,coeffs,upper


def intervals(spec,box):
    if len(box)!=spec['input_width']:raise UnsupportedFP32('input dimension mismatch')
    env={spec['input']:box}
    weights=spec['weights']
    for node in spec['nodes']:
        op,ins,out=node['op'],node['inputs'],node['out']
        if op in ('MatMul','Gemm'):
            dynamic=env[ins[0]];w=weights[ins[1]]
            n,m=w['shape'];vals=[Fraction.from_float(f) for f in w['values']]
            ys=[]
            for j in range(m):
                acc=(Fraction(0),Fraction(0))
                for i in range(n):
                    term=times_constant(dynamic[i],vals[i*m+j])
                    acc=add_interval(acc,term)
                if op=='Gemm':
                    bias=Fraction.from_float(weights[ins[2]]['values'][j])
                    acc=add_interval(acc,(bias,bias))
                ys.append(acc)
        elif op=='Add':
            if ins[0] in weights:
                ys=[add_interval((Fraction.from_float(f),)*2,x) for f,x in zip(weights[ins[0]]['values'],env[ins[1]])]
            elif ins[1] in weights:
                ys=[add_interval(x,(Fraction.from_float(f),)*2) for x,f in zip(env[ins[0]],weights[ins[1]]['values'])]
            else:
                ys=[add_interval(x,y) for x,y in zip(env[ins[0]],env[ins[1]])]
        elif op=='Relu':
            ys=[(max(0,x),max(0,y)) for x,y in env[ins[0]]]
        elif op=='Identity':
            ys=list(env[ins[0]])
        else:raise UnsupportedFP32('operator outside screened subset')
        env[out]=ys
    return env[spec['output']]


def sequential_eval(spec,inputs):
    """Exact software reference. Inputs must be representable f32 values."""
    if len(inputs)!=spec['input_width']:raise UnsupportedFP32('input shape')
    xs=[]
    for x in inputs:
        q=Fraction(x)
        if round_value(q)!=q:raise UnsupportedFP32('input not exactly binary32')
        xs.append(q)
    env={spec['input']:xs}
    weights=spec['weights']
    for node in spec['nodes']:
        op,ins,out=node['op'],node['inputs'],node['out']
        if op in ('MatMul','Gemm'):
            dy=env[ins[0]]; w=weights[ins[1]];n,m=w['shape']
            ys=[]
            for j in range(m):
                acc=Fraction(0)
                for i in range(n):
                    p=round_value(dy[i]*Fraction.from_float(w['values'][i*m+j]))
                    acc=round_value(acc+p)
                if op=='Gemm':
                    acc=round_value(acc+Fraction.from_float(weights[ins[2]]['values'][j]))
                ys.append(acc)
        elif op=='Add':
            if ins[0] in weights:
                ys=[round_value(Fraction.from_float(c)+x) for c,x in zip(weights[ins[0]]['values'],env[ins[1]])]
            elif ins[1] in weights:
                ys=[round_value(x+Fraction.from_float(c)) for x,c in zip(env[ins[0]],weights[ins[1]]['values'])]
            else:
                ys=[round_value(x+y) for x,y in zip(env[ins[0]],env[ins[1]])]
        elif op=='Relu':ys=[max(Fraction(0),x) for x in env[ins[0]]]
        elif op=='Identity':ys=list(env[ins[0]])
        else:raise UnsupportedFP32('unsupported')
        env[out]=ys
    return env[spec['output']]


def relation_upper(outputs,coeffs):
    return sum((c*(hi if c>0 else lo) for (lo,hi),c in zip(outputs,coeffs)),Fraction(0))


def issue(model:bytes,policy:dict):
    """Generate a report; OPEN on policy, parse, arithmetic or coverage failure."""
    try:
        spec,box,cs,limit=checked_policy(model,policy)
        outs=intervals(spec,box)
        calculated=relation_upper(outs,cs)
        approved=calculated<=limit
        report={'schema':SCHEMA,'model_sha256':digest(model),'policy_sha256':digest(_canonical(policy)),
            'status':'PROVED_CONDITIONALLY' if approved else 'OPEN',
            'output_intervals':[[str(x),str(y)] for x,y in outs],
            'computed_upper_bound':str(calculated),'required_upper_limit':str(limit),
            'scope':'IEEE binary32 value arithmetic with roundTiesToEven; ordered nonfused serial dot products; no signed-zero/exceptions/FTZ/FMA/reassociation',
            'external_runtime_equivalence':'NOT_ESTABLISHED',
            'lean_kernel_verification':'NOT_ESTABLISHED'}
        report['receipt_sha256']=digest(_canonical(report))
        return report
    except (Unsupported,UnsupportedFP32,ValueError,TypeError,KeyError,OverflowError,MemoryError) as exc:
        return {'schema':SCHEMA,'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:150],
                'external_runtime_equivalence':'NOT_ESTABLISHED','lean_kernel_verification':'NOT_ESTABLISHED'}


def verify(model:bytes,policy:dict,report:dict):
    fresh=issue(model,policy)
    if fresh['status']!='PROVED_CONDITIONALLY':return False,'No proven bound under externally supplied policy'
    if not isinstance(report,dict) or report!=fresh:return False,'Report changed or did not match a fresh independent computation'
    return True,{'verified_upper_bound':fresh['computed_upper_bound'],
                  'scope':fresh['scope'],'status':'CONDITIONALLY_CHECKED_IN_PYTHON'}


def main():
    import argparse
    from pathlib import Path
    from .verify_relational import strict_load
    p=argparse.ArgumentParser(description='Review float32 sequential numerical bounds; NOT ONNX Runtime or Lean verified')
    p.add_argument('model');p.add_argument('policy');p.add_argument('--receipt');p.add_argument('--output')
    a=p.parse_args()
    model=Path(a.model).read_bytes();policy=strict_load(a.policy)
    if a.receipt:
        ok,reason=verify(model,policy,strict_load(a.receipt))
        print(('VERIFIED RESTRICTED BINARY32: ' if ok else 'REJECTED: ')+str(reason))
        return 0 if ok else 1
    result=issue(model,policy)
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PROVED_CONDITIONALLY' else 2

if __name__=='__main__':raise SystemExit(main())
