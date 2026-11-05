"""Experimental adversarial counterexample generator using HiGHS MILP via SciPy.

Only bounded screened dense ONNX operators can be encoded. Solver optimizations
are floating-point approximations and NEVER proof of model safety. Candidate
inputs are checked again against the exact rational interpreter, and separately
against NumPy/PyTorch only when the caller explicitly requests replay.
A solver returning 'no counterexample' means OPEN, never SAFE.
"""
from __future__ import annotations
import math
import time
from fractions import Fraction
from .dense_nn import _execute_intervals,Unsupported,_f32

MAX_VARIABLES=256
MAX_RELUS=80
MAX_ABS_COEFF=100_000

class ChallengeUnsupported(Exception):pass


def build_milp(spec,policy):
    import numpy as np
    from scipy.optimize import Bounds,LinearConstraint
    lo=float(policy['input_min']);hi=float(policy['input_max'])
    if not -1e6<=lo<=hi<=1e6:raise ChallengeUnsupported('MILP supports small bounded numeric input ranges')
    envb=_execute_intervals(spec,[(Fraction.from_float(lo),Fraction.from_float(hi))]*spec['input_width'],return_env=True)
    widths={spec['input']:spec['input_width']}
    output_names={}
    low=[];high=[];kind=[];rows=[];lowrows=[];hirows=[]
    varnames=[]
    def alloc(name,n,bounds,integ=0):
        if len(low)+n>MAX_VARIABLES:raise ChallengeUnsupported('MILP variable count budget')
        ids=[]
        for j in range(n):
            a,b=bounds[j]
            a=float(a);b=float(b)
            if not all(math.isfinite(x) and abs(x)<=MAX_ABS_COEFF for x in (a,b)):
                raise ChallengeUnsupported('Intermediate intervals exceed numerical budget')
            ids.append(len(low));low.append(a);high.append(b);kind.append(integ);varnames.append(f'{name}_{j}')
        return ids
    def equation(coeffs,constant=0):
        rows.append(coeffs);lowrows.append(float(constant));hirows.append(float(constant))
    def inequality(coeffs,upper):
        rows.append(coeffs);lowrows.append(-np.inf);hirows.append(float(upper))
    output_names[spec['input']]=alloc(spec['input'],spec['input_width'],envb[spec['input']])
    unstable=0
    for node in spec['nodes']:
        op,ins,out=node['op'],node['inputs'],node['out']
        bounds=envb[out];n=len(bounds)
        ids=alloc(out,n,bounds)
        output_names[out]=ids
        if op in ('MatMul','Gemm'):
            x=output_names[ins[0]];w=spec['weights'][ins[1]]
            if len(w['shape'])!=2:raise ChallengeUnsupported('unexpected weight shape')
            inwidth,outwidth=w['shape']
            for j,y in enumerate(ids):
                coeff={y:1.}
                for i,xi in enumerate(x):
                    wij=float(w['values'][i*outwidth+j]);coeff[xi]=coeff.get(xi,0)-wij
                bias=float(spec['weights'][ins[2]]['values'][j]) if op=='Gemm' else 0.
                equation(coeff,bias)
        elif op=='Add':
            for j,y in enumerate(ids):
                coeff={y:1.};bias=0.
                for name in ins:
                    if name in spec['weights']:
                        b=spec['weights'][name]['values'];bias+=float(b[j])
                    else:
                        idx=output_names[name][j];coeff[idx]=coeff.get(idx,0)-1.
                equation(coeff,bias)
        elif op=='Identity':
            for j,y in enumerate(ids):equation({y:1.,output_names[ins[0]][j]:-1.})
        elif op=='Relu':
            for j,y in enumerate(ids):
                x=output_names[ins[0]][j]
                L=float(envb[ins[0]][j][0]);U=float(envb[ins[0]][j][1])
                if L>=0:equation({y:1.,x:-1.})
                elif U<=0:equation({y:1.},0)
                else:
                    unstable+=1
                    if unstable>MAX_RELUS:raise ChallengeUnsupported('too many unstable ReLU units')
                    binary=alloc('relu_gate',1,[(0,1)],integ=1)[0]
                    # 0 <= y; x <= y; y <= x-L(1-d); y <= U*d
                    inequality({x:1.,y:-1.},0.)
                    inequality({y:1.,x:-1.,binary:-L},-L)
                    inequality({y:1.,binary:-U},0.)
        else:raise ChallengeUnsupported('unsupported node')
        if len(rows)>1500:raise ChallengeUnsupported('constraint budget')
    nvar=len(low)
    A=np.zeros((len(rows),nvar),dtype=np.float64)
    for k,row in enumerate(rows):
        for i,value in row.items():
            if not math.isfinite(value) or abs(value)>MAX_ABS_COEFF:
                raise ChallengeUnsupported('numerically risky coefficient')
            A[k,i]=value
    return {'variable_names':varnames,'bounds':Bounds(np.array(low),np.array(high)),
            'integrality':np.array(kind,dtype=int),'constraints':LinearConstraint(A,np.array(lowrows),np.array(hirows)),
            'inputs':output_names[spec['input']], 'outputs':output_names[spec['output']],
            'variables':nvar,'constraints_count':len(rows),'unstable_relu_units':unstable}


def search(spec,policy,*,timeout=8):
    start=time.perf_counter()
    try:
        import numpy as np
        from scipy.optimize import milp
        if not 1<=timeout<=15:raise ChallengeUnsupported('time budget')
        model=build_milp(spec,policy)
        checked=0
        goals=[]
        for output_idx in model['outputs']:
            for direction in (-1,1):
                if time.perf_counter()-start>timeout:raise ChallengeUnsupported('whole search timeout')
                # SciPy minimizes c.dot(x). Negative coefficient maximizes output.
                c=np.zeros(model['variables'],dtype=float)
                c[output_idx]=direction
                result=milp(c,integrality=model['integrality'],bounds=model['bounds'],
                            constraints=model['constraints'],
                            options={'time_limit':max(0.05,timeout-(time.perf_counter()-start)),
                                     'mip_rel_gap':0.0,'disp':False})
                checked+=1
                if result.x is None or not all(math.isfinite(float(z)) for z in result.x):
                    goals.append({'status':int(result.status),'message':str(result.message)[:80]});continue
                point=[float(result.x[i]) for i in model['inputs']]
                inlo=float(policy['input_min']);inhi=float(policy['input_max'])
                # Solver solutions can be epsilon outside boundaries. We do not
                # silently project an out-of-box result into a claimed witness.
                if not all(inlo<=x<=inhi for x in point):
                    goals.append({'status':'NUMERIC_POINT_OUTSIDE_BOX'});continue
                # Actual reference workers cast input to binary32. Bind witness
                # and the rational recheck to those EXACT representable values.
                f32_point=[_f32(x) for x in point]
                if not all(math.isfinite(x) and inlo<=x<=inhi for x in f32_point):
                    goals.append({'status':'FLOAT32_POINT_OUTSIDE_BOX'});continue
                point=f32_point
                # Reject any candidate that fails independent exact rational
                # recomputation of the screen-level model and strict bounds.
                exact=_execute_intervals(spec,[(Fraction.from_float(x),Fraction.from_float(x)) for x in point])
                tmin=Fraction.from_float(float(policy['output_min']));tmax=Fraction.from_float(float(policy['output_max']))
                if any(a<tmin or b>tmax for a,b in exact):
                    return {'status':'IDEALIZED_VIOLATION_CANDIDATE',
                            'witness':{'inputs':{spec['input']:point},
                                       'idealized_outputs':[str(a) for a,b in exact],
                                       'trials':checked,'status':'IDEALIZED_RATIONAL_VIOLATION',
                                       'source':'solver-guided MILP; exact rational candidate recomputation'},
                            'goals_solved':checked,
                            'variables':model['variables'],'linear_constraints':model['constraints_count'],
                            'unstable_relu_units':model['unstable_relu_units'],
                            'limitation':'MILP numerical search does not prove absence of violations or ONNX Runtime equivalence'}
        return {'status':'OPEN_NO_REPRODUCED_WITNESS','goals_solved':checked,'variables':model['variables'],
                'linear_constraints':model['constraints_count'], 'unstable_relu_units':model['unstable_relu_units'],
                'limitation':'Solver results are numerical, no lack-of-counterexample safety proof'}
    except (ChallengeUnsupported,Unsupported,ValueError,OverflowError,MemoryError,ArithmeticError,ImportError) as exc:
        return {'status':'INDETERMINATE','reason':type(exc).__name__+': '+str(exc)[:130],
                'limitation':'Unsupported or unavailable MILP; NO safety verdict'}
