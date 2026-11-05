"""Untrusted numerical proposer of exactly checkable Farkas proofs.

A third-party optimizer can suggest multipliers, but no optimizer status or
objective is accepted as verification evidence. Every release is checked by
studio.relational_kernel.check with exact Fractions and original model bytes.
"""
from __future__ import annotations
from fractions import Fraction
import math
from .relational_kernel import build, check, canonical, digest, rational, relation, SCHEMA, Unsupported, cut


def propose(raw_model, input_box, coefficients, upper_limit, *, timeout=5):
    try:
        from .dense_nn import screen_onnx, Unsupported as DenseUnsupported
        from scipy.optimize import linprog
        import numpy as np
        if timeout<0.5 or timeout>20:raise Unsupported('invalid timeout')
        spec=screen_onnx(raw_model)
        poly=build(spec,input_box)
        coeffs,limit=relation(coefficients,upper_limit,spec['output_width'])
        c=[Fraction(0)]*poly['variable_count']
        for i,v in zip(poly['output_variables'],coeffs):c[i]=v
        A=np.zeros((len(poly['rows']),len(c)),dtype=np.float64)
        b=np.empty(len(poly['rows']),dtype=np.float64)
        for k,(row,rhs) in enumerate(poly['rows']):
            b[k]=float(rhs)
            for j,v in row.items():A[k,j]=float(v)
        target=-np.array([float(v) for v in c])
        ans=linprog(target,A_ub=A,b_ub=b,bounds=[(None,None)]*len(c),
                    method='highs',options={'time_limit':timeout})
        if not ans.success or ans.ineqlin is None:
            return {'status':'OPEN','reason':'Numerical relaxation did not solve; never a safety proof',
                    'solver_status':int(ans.status)}
        # For min -c^T x, HiGHS marginal = - dual multiplier for max c^T x.
        rawdual=-np.asarray(ans.ineqlin.marginals,dtype=float)
        multipliers={}
        for k,raw in enumerate(rawdual):
            if not math.isfinite(raw):raise Unsupported('nonfinite optimizer multiplier')
            if raw>1e-9:
                q=Fraction(float(raw)).limit_denominator(1000000)
                if q>0:multipliers[k]=q
        # Exact dual stationarity repair: rational rounding and numerical noise
        # are absorbed via the VALID global variable bound rows. This step is
        # checked algebraically and can only weaken the obtained upper bound.
        represented=[Fraction(0)]*len(c)
        for idx,q in multipliers.items():
            for j,v in poly['rows'][idx][0].items():represented[j]=cut(represented[j]+q*v)
        for j,(wanted,got) in enumerate(zip(c,represented)):
            delta=cut(wanted-got)
            if delta:
                rowid=poly['bound_ids'][j][0 if delta>0 else 1]
                if rowid is None:raise Unsupported('bound row missing')
                multipliers[rowid]=cut(multipliers.get(rowid,Fraction(0))+abs(delta))
        multipliers={k:q for k,q in multipliers.items() if q>0}
        certificate={'schema':SCHEMA,'scope':'exact-real-screened-onnx-outer-polytope',
                     'model_sha256':digest(raw_model),
                     'input_box':[[str(rational(a)),str(rational(b))] for a,b in input_box],
                     'relation':{'output_coefficients':[str(v) for v in coeffs],
                                 'upper_limit':str(limit)},
                     'multipliers':[[i,str(q)] for i,q in sorted(multipliers.items())]}
        certificate['certificate_sha256']=digest(canonical(certificate))
        ok,verdict=check(raw_model,certificate)
        if not ok:
            return {'status':'OPEN','reason':'Exact verifier withheld proof: '+str(verdict)[:180],
                    'optimizer_objective':float(-ans.fun)}
        return {'status':'PROVED_CONDITIONALLY','certificate':certificate,
                'verification':verdict,'optimizer_objective':float(-ans.fun),
                'scope':'Exact-real screened ONNX semantics; no arbitrary ONNX/float32/Lean certification'}
    except (ImportError,Unsupported,DenseUnsupported,ValueError,TypeError,OverflowError,MemoryError,ArithmeticError) as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:180]}
