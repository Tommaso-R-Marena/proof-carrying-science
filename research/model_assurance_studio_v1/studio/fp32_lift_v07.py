"""Conditional IEEE-754 binary32 error budget lifting *exact-real* certificates.

A real-valued margin / model-update certificate proves c.f_real <= L.
For all float32 input values in the same box, we compute E_j such that
|f_float,j - f_real,j| <= E_j assuming a finite IEEE-754 RN-even execution
with one rounding per multiply/add or fewer (including fused multiply-add),
without lowered-precision intermediates, unsafe reassociation of repeated
terms, FTZ, dynamic operators, or exceptional arithmetic. No assumption about
matrix multiplication summation order is needed for this conservative budget.

For a dot of n terms, at most K=2(n+1) rounding steps, each satisfies
  |RN(t)-t| <= u*|t| + eta, u=2^-24, eta=2^-150.
With S the sum of absolute magnitudes of input terms and bias, an error
recurrence E_{k+1} <= (1+u)E_k + u*S + eta implies
  E_K <= ((1+u)^K-1) * S + (((1+u)^K-1)/u) * eta.
Errors in previously rounded neuron values add sum |w_i|*E_i. This is a
conservative model, not universal ONNX Runtime equivalence. A finite magnitude
check rejects potential overflow. All bounds are exact Fractions.

IMPORTANT: the formulas and their implementation are still Python TCB;
they have NOT been kernel-checked in Lean. Avoid using this for deployment
without formal review and runtime conformance evidence.
"""
from __future__ import annotations
from fractions import Fraction
from .dense_nn import _execute_intervals,screen_onnx,Unsupported
from .ieee754 import MAX_FINITE,UnsupportedFP32
from .relational_kernel import rational,digest
from .verify_relational import verify_with_policy
from .verify_update import verify_composition

U=Fraction(1,1<<24)
ETA=Fraction(1,1<<150)


def _limit(q):
    if q.numerator.bit_length()>2048 or q.denominator.bit_length()>2048:
        raise UnsupportedFP32('error arithmetic budget exceeded')
    return q


def _magnitude(interval):
    return max(abs(interval[0]),abs(interval[1]))


def _rounding_bound(K:int,S:Fraction):
    if S<0 or not 1<=K<=128:raise UnsupportedFP32('invalid floating point budget')
    power=(1+U)**K
    err=(power-1)*(S+ETA/U)
    if _limit(power*S+err)>=MAX_FINITE:
        raise UnsupportedFP32('unable to rule out overflow in arithmetic')
    return _limit(err)


def output_errors(spec,box):
    real_env=_execute_intervals(spec,box,return_env=True)
    env_err={spec['input']:[Fraction(0)]*spec['input_width']}
    weights=spec['weights']
    for node in spec['nodes']:
        op,ins,out=node['op'],node['inputs'],node['out']
        if op in ('MatMul','Gemm'):
            n,m=weights[ins[1]]['shape'];w=weights[ins[1]]['values']
            ys=[]
            for j in range(m):
                transmitted=Fraction(0);S=Fraction(0)
                for i in range(n):
                    wt=abs(Fraction.from_float(w[i*m+j]));E=env_err[ins[0]][i]
                    M=_magnitude(real_env[ins[0]][i])
                    transmitted+=E*wt;S+=(M+E)*wt
                if op=='Gemm':S+=abs(Fraction.from_float(weights[ins[2]]['values'][j]))
                # A correctly rounded dot can use <=2n+1 rounding stages.
                K=2*n+(2 if op=='Gemm' else 1)
                ys.append(_limit(transmitted+_rounding_bound(K,S)))
        elif op=='Add':
            if ins[0] in weights:
                const=weights[ins[0]]['values'];dy=ins[1]
                ys=[]
                for j,c in enumerate(const):
                    err=env_err[dy][j]
                    M=_magnitude(real_env[dy][j])+abs(Fraction.from_float(c))+err
                    ys.append(_limit(err+_rounding_bound(1,M)))
            elif ins[1] in weights:
                const=weights[ins[1]]['values'];dy=ins[0]
                ys=[]
                for j,c in enumerate(const):
                    err=env_err[dy][j]
                    M=_magnitude(real_env[dy][j])+abs(Fraction.from_float(c))+err
                    ys.append(_limit(err+_rounding_bound(1,M)))
            else:
                a,b=ins
                ys=[]
                for j in range(len(env_err[a])):
                    err=env_err[a][j]+env_err[b][j]
                    M=_magnitude(real_env[a][j])+_magnitude(real_env[b][j])+err
                    ys.append(_limit(err+_rounding_bound(1,M)))
        elif op in ('Relu','Identity'):
            ys=list(env_err[ins[0]])
        else:
            raise UnsupportedFP32('operator outside accepted error analysis')
        env_err[out]=ys
    return env_err[spec['output']]


def input_box_from_policy(p):
    box=[]
    for pair in p['input_box']:
        a,b=rational(pair[0]),rational(pair[1])
        if a>b:raise UnsupportedFP32('invalid box')
        box.append((a,b))
    return box


def error_contribution(model,policy):
    spec=screen_onnx(model);box=input_box_from_policy(policy)
    if len(box)!=spec['input_width']:raise UnsupportedFP32('wrong input dimension')
    cs=[rational(c) for c in policy['output_coefficients']]
    if len(cs)!=spec['output_width']:raise UnsupportedFP32('wrong output relation')
    errors=output_errors(spec,box)
    margin=_limit(sum((abs(c)*e for c,e in zip(cs,errors)),Fraction(0)))
    return errors,margin


def lift_single(model,certificate,policy,required_float_upper):
    try:
        ok,why=verify_with_policy(model,certificate,policy)
        if not ok:return {'status':'OPEN','reason':'Exact-real certificate rejected: '+str(why)[:160]}
        errors,extra=error_contribution(model,policy)
        b=rational(policy['upper_limit']);required=rational(required_float_upper)
        bound=b+extra
        return {'schema':'pcs-fp32-lifted-relational-v0.7',
            'status':'PROVED_CONDITIONALLY' if bound<=required else 'OPEN',
            'model_sha256':digest(model),'ideal_real_upper_bound':str(b),
            'absolute_error_bound_per_output':[str(e) for e in errors],
            'verified_float32_rounding_cushion':str(extra),
            'derived_float32_upper_bound':str(bound),'reviewer_required_upper_limit':str(required),
            'scope':'for float32 inputs within input box; finite correctly rounded binary32 operations; no FTZ/lower precision; no claim of deployed ONNX Runtime equivalence',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'runtime_conformance':'NOT_ESTABLISHED',
            'note':'Conditional analytic bound; runtime kernels must satisfy assumed rounding/finite-operation contract'}
    except (Unsupported,UnsupportedFP32,ValueError,TypeError,KeyError,OverflowError,MemoryError,ArithmeticError) as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:160]}


def lift_update(old,new,baseline_cert,baseline_policy,update_cert,update_policy,required_float_upper):
    try:
        b=rational(baseline_policy['upper_limit']);d=rational(update_policy['upper_limit'])
        ok,why=verify_composition(old,new,baseline_cert,baseline_policy,update_cert,update_policy,
                                   required_updated_upper_limit=str(b+d))
        if not ok:return {'status':'OPEN','reason':'Exact-real update rejected: '+str(why)[:160]}
        errors,extra=error_contribution(new,baseline_policy)
        bound=_limit(b+d+extra)
        required=rational(required_float_upper)
        return {'schema':'pcs-fp32-lifted-update-v0.7',
            'status':'PROVED_CONDITIONALLY' if bound<=required else 'OPEN',
            'old_model_sha256':digest(old),'new_model_sha256':digest(new),
            'verified_real_baseline_upper_bound':str(b),'verified_real_drift_upper_bound':str(d),
            'new_model_rounding_cushion':str(extra),'per_output_error_bounds':[str(x) for x in errors],
            'derived_float32_upper_bound':str(bound),'reviewer_required_upper_limit':str(required),
            'scope':'conditional IEEE binary32 RN-even finite operations, consistent model input; not a universal runtime proof',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'runtime_conformance':'NOT_ESTABLISHED'}
    except (Unsupported,UnsupportedFP32,ValueError,TypeError,KeyError,OverflowError,MemoryError,ArithmeticError) as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:160]}


def main():
    import argparse,json
    from pathlib import Path
    from .verify_relational import strict_load
    p=argparse.ArgumentParser(description='Lift independently checked real model certificates using exact rational FP32 error bounds')
    sub=p.add_subparsers(dest='mode',required=True)
    s=sub.add_parser('relation');s.add_argument('model');s.add_argument('certificate');s.add_argument('policy');s.add_argument('--required-float-upper',required=True)
    u=sub.add_parser('update');
    for name in ('old','new','baseline_certificate','baseline_policy','drift_certificate','drift_policy'):u.add_argument(name)
    u.add_argument('--required-float-upper',required=True)
    a=p.parse_args()
    if a.mode=='relation':
        report=lift_single(Path(a.model).read_bytes(),strict_load(a.certificate),strict_load(a.policy),a.required_float_upper)
    else:
        report=lift_update(Path(a.old).read_bytes(),Path(a.new).read_bytes(),strict_load(a.baseline_certificate),strict_load(a.baseline_policy),strict_load(a.drift_certificate),strict_load(a.drift_policy),a.required_float_upper)
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='PROVED_CONDITIONALLY' else 2

if __name__=='__main__':raise SystemExit(main())
