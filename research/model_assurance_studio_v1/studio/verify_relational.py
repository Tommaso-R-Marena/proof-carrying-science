"""Independent verifier: model + proof + externally selected reviewer policy.

Uses no SciPy or model execution. Exit 0 only after the exact Farkas identity,
conditional property, and reviewer-owned claim are checked.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .relational_kernel import check, rational, Unsupported

POLICY_SCHEMA='pcs-relational-reviewer-policy-v0.6'

def verify_with_policy(model:bytes,certificate:dict,policy:dict):
    try:
        if not isinstance(policy,dict) or set(policy)!={'schema','input_box','output_coefficients','upper_limit'} or policy['schema']!=POLICY_SCHEMA:
            return False,'reviewer policy structure or version mismatch'
        if not isinstance(policy['input_box'],list) or not isinstance(policy['output_coefficients'],list):
            return False,'invalid reviewer policy arrays'
        certbox=certificate['input_box']; certrel=certificate['relation']
        if len(policy['input_box'])!=len(certbox):return False,'input dimension changed'
        if any(not isinstance(p,list) or len(p)!=2 or [rational(v) for v in p]!=[rational(v) for v in c]
               for p,c in zip(policy['input_box'],certbox)):
            return False,'certificate altered the reviewer input domain'
        if len(policy['output_coefficients'])!=len(certrel['output_coefficients']):
            return False,'output relation dimension changed'
        if [rational(v) for v in policy['output_coefficients']]!=[rational(v) for v in certrel['output_coefficients']]:
            return False,'certificate altered reviewer output coefficients'
        if rational(policy['upper_limit'])!=rational(certrel['upper_limit']):
            return False,'certificate altered reviewer output limit'
        if certificate.get('schema')=='pcs-activation-case-cover-real-v0.6':
            from .activation_proof import verify as verify_cases
            return verify_cases(model,certificate)
        return check(model,certificate)
    except (ValueError,TypeError,KeyError,Unsupported,OverflowError,MemoryError) as e:
        return False,'invalid reviewer policy/certificate: '+type(e).__name__


def strict_pairs(pairs):
    out={}
    for name,value in pairs:
        if name in out:raise ValueError('duplicate JSON field: '+name[:40])
        out[name]=value
    return out

def strict_load(path):
    return json.loads(Path(path).read_text(),object_pairs_hook=strict_pairs,
                      parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))

def main():
    p=argparse.ArgumentParser(description='Verify conditional real-arithmetic neural invariant against independent reviewer policy')
    p.add_argument('model',help='exact original ONNX file')
    p.add_argument('certificate',help='untrusted proposed certificate JSON')
    p.add_argument('policy',help='independently obtained reviewer policy JSON')
    a=p.parse_args()
    try:
        model=Path(a.model).read_bytes(); cert=strict_load(a.certificate);pol=strict_load(a.policy)
        good,why=verify_with_policy(model,cert,pol)
        print(('VERIFIED CONDITIONAL REAL PROPERTY: ' if good else 'REJECTED: ')+str(why))
        return 0 if good else 1
    except (OSError,UnicodeError,json.JSONDecodeError,ValueError) as e:
        print('REJECTED: invalid input: '+type(e).__name__)
        return 1

if __name__=='__main__':raise SystemExit(main())
