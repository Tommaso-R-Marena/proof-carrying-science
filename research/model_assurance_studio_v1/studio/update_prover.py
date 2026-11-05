"""Untrusted SciPy LP proposer for two-model drift certificates.

A successful optimizer flag is NEVER a proof; only update_kernel.verify
establishes the conditional exact-real claim.
"""
from __future__ import annotations
from fractions import Fraction
import math
from .update_kernel import joint,verify,SCHEMA,SCOPE
from .relational_kernel import relation,build,rational,cut,digest,canonical,Unsupported


def propose(old_raw,new_raw,input_box,coefficients,upper_limit,*,timeout=5):
    try:
        import numpy as np
        from scipy.optimize import linprog
        from .dense_nn import screen_onnx
        old=screen_onnx(old_raw);new=screen_onnx(new_raw)
        poly=joint(old,new,input_box)
        cs,limit=relation(coefficients,upper_limit,old['output_width'])
        goal=[Fraction(0)]*poly['variable_count']
        for idx,c in zip(poly['old_outputs'],cs):goal[idx]=cut(goal[idx]-c)
        for idx,c in zip(poly['new_outputs'],cs):goal[idx]=cut(goal[idx]+c)
        rows=poly['rows'];A=np.zeros((len(rows),len(goal)),dtype=np.float64)
        b=np.zeros(len(rows));obj=np.array([-float(v) for v in goal])
        for i,(r,up) in enumerate(rows):
            b[i]=float(up)
            for j,v in r.items():A[i,j]=float(v)
        res=linprog(obj,A_ub=A,b_ub=b,bounds=[(None,None)]*len(goal),method='highs',
                    options={'time_limit':timeout})
        if not res.success or res.ineqlin is None:
            return {'status':'OPEN','reason':'No mathematical certificate generated; numerical LP status cannot establish safety'}
        dual=-np.asarray(res.ineqlin.marginals,dtype=float)
        lambdas={i:Fraction(float(q)).limit_denominator(1000000)
                 for i,q in enumerate(dual) if math.isfinite(float(q)) and float(q)>1e-9}
        represented=[Fraction(0)]*len(goal)
        for i,q in lambdas.items():
            for j,a in rows[i][0].items():represented[j]=cut(represented[j]+q*a)
        for j,(wanted,got) in enumerate(zip(goal,represented)):
            delta=cut(wanted-got)
            if delta:
                rowid=poly['bound_ids'][j][0 if delta>0 else 1]
                lambdas[rowid]=cut(lambdas.get(rowid,Fraction(0))+abs(delta))
        cert={'schema':SCHEMA,'scope':SCOPE,'old_sha256':digest(old_raw),'new_sha256':digest(new_raw),
              'input_box':[[str(rational(a)),str(rational(b))] for a,b in input_box],
              'relation':{'output_coefficients':[str(x) for x in cs],'upper_limit':str(limit)},
              'multipliers':[[k,str(v)] for k,v in sorted(lambdas.items()) if v>0]}
        cert['certificate_sha256']=digest(canonical(cert))
        yes,explanation=verify(old_raw,new_raw,cert)
        if not yes:
            # Numerical dual multipliers may miss a sharp equality by a tiny
            # rounding residual. Recover a sparse exact dual from the active
            # constraint support; STILL require the independent rational checker.
            from .exact_dual_recovery import recover
            exact=recover(rows,goal,dual)
            if exact:
                cert['multipliers']=[[k,str(v)] for k,v in sorted(exact.items())]
                cert['certificate_sha256']=digest(canonical({k:v for k,v in cert.items() if k!='certificate_sha256'}))
                yes,explanation=verify(old_raw,new_raw,cert)
        if not yes:return {'status':'OPEN','reason':'Exact reviewer declined numerical proposal: '+str(explanation)[:180]}
        return {'status':'PROVED_CONDITIONALLY','certificate':cert,'verification':explanation,
                'limitation':'Exact-real screened ONNX equivalence, NOT runtime/floating point/overall safety'}
    except Exception as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:180]}
