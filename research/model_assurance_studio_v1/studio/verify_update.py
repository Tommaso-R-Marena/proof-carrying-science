"""Independent, standard-library-only checking of safe *scoped* model upgrades.

A reviewer, not the model author, supplies the trusted policy and exact old/new
model SHA-256. Standalone update verification proves a bound on behavioral drift.
Composition additionally verifies an old-model property certificate and derives
an updated-model bound from baseline + drift (exact rational arithmetic).
No claim of generalized, floating-point, or deployment safety.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from .update_kernel import verify as verify_dual
from .relational_kernel import rational,digest,Unsupported
from .verify_relational import verify_with_policy,strict_load,POLICY_SCHEMA

UPDATE_POLICY_SCHEMA='pcs-model-update-reviewer-policy-v0.6'


def _matches(box1,box2):
    return (isinstance(box1,list) and isinstance(box2,list) and len(box1)==len(box2) and
            all(isinstance(a,list) and isinstance(b,list) and len(a)==len(b)==2 and
                all(rational(x)==rational(y) for x,y in zip(a,b)) for a,b in zip(box1,box2)))


def verify_update_policy(old_raw,new_raw,cert,policy):
    try:
        if not isinstance(policy,dict) or set(policy)!={'schema','old_model_sha256','new_model_sha256',
            'input_box','output_coefficients','upper_limit'} or policy['schema']!=UPDATE_POLICY_SCHEMA:
            return False,'reviewer model-update policy schema or fields'
        if policy['old_model_sha256']!=digest(old_raw) or policy['new_model_sha256']!=digest(new_raw):
            return False,'reviewer-pinned old/new model SHA-256 mismatch'
        if not _matches(policy['input_box'],cert['input_box']):
            return False,'reviewer input domain changed'
        rel=cert['relation']
        if len(policy['output_coefficients'])!=len(rel['output_coefficients']) or any(
            rational(a)!=rational(b) for a,b in zip(policy['output_coefficients'],rel['output_coefficients'])):
            return False,'reviewer output relation changed'
        if rational(policy['upper_limit'])!=rational(rel['upper_limit']):
            return False,'reviewer drift threshold changed'
        return verify_dual(old_raw,new_raw,cert)
    except Exception as exc:
        return False,'malformed update policy: '+type(exc).__name__


def verify_composition(old_raw,new_raw,baseline_cert,baseline_policy,update_cert,update_policy,
                       *,required_updated_upper_limit):
    """Conclude c·f_new(x) <= old_limit + drift_limit <= required limit, all x in B."""
    try:
        ok,why=verify_with_policy(old_raw,baseline_cert,baseline_policy)
        if not ok:return False,'baseline verification failed: '+str(why)
        ok,why=verify_update_policy(old_raw,new_raw,update_cert,update_policy)
        if not ok:return False,'update verification failed: '+str(why)
        if baseline_policy['schema']!=POLICY_SCHEMA:return False,'baseline policy schema'
        if not _matches(baseline_policy['input_box'],update_policy['input_box']):
            return False,'baseline and update assumed different input domains'
        bc=baseline_policy['output_coefficients'];uc=update_policy['output_coefficients']
        if len(bc)!=len(uc) or any(rational(a)!=rational(b) for a,b in zip(bc,uc)):
            return False,'baseline and update concern different output claims'
        old_upper=rational(baseline_policy['upper_limit'])
        delta_upper=rational(update_policy['upper_limit'])
        new_upper=old_upper+delta_upper
        target=rational(required_updated_upper_limit)
        if new_upper>target:return False,'composed upper bound exceeds reviewer acceptance limit'
        return True,{'status':'PROVED_CONDITIONALLY','updated_model_sha256':digest(new_raw),
                     'derived_new_model_upper_bound':str(new_upper),
                     'required_updated_upper_limit':str(target),
                     'mechanism':'old model verified universal bound + same-input verified update drift',
                     'scope':'idealized exact-real screened ONNX; no IEEE-754/ONNX Runtime/Lean/deployment guarantee'}
    except Exception as exc:
        return False,'invalid composition: '+type(exc).__name__


def main():
    p=argparse.ArgumentParser(description='Independent proof-gated neural model update verification')
    sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('drift',help='verify two-model behavioral drift proof')
    for name in ('old_model','new_model','update_certificate','update_policy'):v.add_argument(name)
    c=sub.add_parser('compose',help='verify baseline + drift and infer bounded updated model')
    for name in ('old_model','new_model','baseline_certificate','baseline_policy',
                 'update_certificate','update_policy'):c.add_argument(name)
    c.add_argument('--required-new-upper',required=True,help='independent acceptance threshold, exact rational')
    args=p.parse_args()
    try:
        from pathlib import Path
        old=Path(args.old_model).read_bytes();new=Path(args.new_model).read_bytes()
        ucert=strict_load(args.update_certificate);upol=strict_load(args.update_policy)
        if args.command=='drift':passed,reason=verify_update_policy(old,new,ucert,upol)
        else:
            passed,reason=verify_composition(old,new,strict_load(args.baseline_certificate),
                strict_load(args.baseline_policy),ucert,upol,
                required_updated_upper_limit=args.required_new_upper)
        print(('VERIFIED CONDITIONAL MODEL UPDATE: ' if passed else 'REJECTED: ')+str(reason))
        return 0 if passed else 1
    except Exception as exc:
        print('REJECTED: invalid inputs: '+type(exc).__name__)
        return 1

if __name__=='__main__':raise SystemExit(main())
