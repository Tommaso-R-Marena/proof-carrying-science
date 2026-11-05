"""Local interactive workflow for proof-gated updates in a bounded ONNX subset.

This is research intake/verification, never authorization of an arbitrary model
in a production runtime. Reviewer pins input policy and model hashes externally.
"""
from __future__ import annotations
from .relational_kernel import digest,rational,Unsupported
from .relational_prover import propose as old_propose
from .activation_proof import propose as case_propose
from .update_prover import propose as update_propose
from .verify_relational import POLICY_SCHEMA
from .verify_update import UPDATE_POLICY_SCHEMA,verify_composition

class ModelUpdateError(ValueError):pass

MAX_PAIR_BYTES=8*1024*1024

def parse_update_policy(p):
    if not isinstance(p,dict) or set(p)!={'input_box','output_coefficients','baseline_upper_limit',
                                           'drift_upper_limit','required_new_upper_limit'}:
        raise ModelUpdateError('Require reviewer-chosen input box, output coefficients and three exact upper limits')
    box=p['input_box'];coeff=p['output_coefficients']
    if not isinstance(box,list) or not 1<=len(box)<=16:raise ModelUpdateError('input_box shape')
    if not isinstance(coeff,list) or not 1<=len(coeff)<=16:raise ModelUpdateError('output_coefficients shape')
    try:
        for pair in box:
            if not isinstance(pair,list) or len(pair)!=2 or rational(pair[0])>rational(pair[1]):
                raise ModelUpdateError('Each box bound must be ordered')
        if not any(rational(x) for x in coeff):raise ModelUpdateError('zero output relation')
        for value in ('baseline_upper_limit','drift_upper_limit','required_new_upper_limit'):
            rational(p[value])
    except (Unsupported,ValueError,ZeroDivisionError) as exc:
        raise ModelUpdateError('Invalid exact rational: '+str(exc)[:80]) from exc
    return p


def compare(old_bytes,new_bytes,policy):
    p=parse_update_policy(policy)
    if not old_bytes or not new_bytes or len(old_bytes)+len(new_bytes)>MAX_PAIR_BYTES:
        raise ModelUpdateError('Both original/updated models required; combined maximum 8 MiB')
    # No source file extraction or uploaded executable runs. Untrusted numerical
    # LPs propose proofs; only exact reviewer checks can admit a scoped claim.
    props=p['output_coefficients'];box=p['input_box']
    base=old_propose(old_bytes,box,props,p['baseline_upper_limit'])
    if base['status']!='PROVED_CONDITIONALLY':
        base=case_propose(old_bytes,box,props,p['baseline_upper_limit'],max_leaves=32,timeout=2)
    update=update_propose(old_bytes,new_bytes,box,props,p['drift_upper_limit'])
    bp={'schema':POLICY_SCHEMA,'input_box':box,'output_coefficients':props,
        'upper_limit':p['baseline_upper_limit']}
    up={'schema':UPDATE_POLICY_SCHEMA,'old_model_sha256':digest(old_bytes),
        'new_model_sha256':digest(new_bytes),'input_box':box,
        'output_coefficients':props,'upper_limit':p['drift_upper_limit']}
    outcome={'schema':'pcs-model-update-assessment-v0.6',
             'old_model_sha256':digest(old_bytes),'new_model_sha256':digest(new_bytes),
             'baseline':base,'update':update,'baseline_reviewer_policy':bp,
             'update_reviewer_policy':up,'requested_new_upper_limit':p['required_new_upper_limit'],
             'status':'OPEN','limits':[
                'Only screened ONNX real-arithmetic grammar is considered; not full ONNX, IEEE-754 or official runtime',
                'Generated review policy is a suggestion: obtain and pin trusted expectations independently before acceptance',
                'A scoped model relation is not a claim of model alignment, generalized safety, or clinical validity']}
    if base['status']=='PROVED_CONDITIONALLY' and update['status']=='PROVED_CONDITIONALLY':
        good,verdict=verify_composition(old_bytes,new_bytes,base['certificate'],bp,
                        update['certificate'],up,required_updated_upper_limit=p['required_new_upper_limit'])
        outcome['composition']=verdict
        if good:outcome['status']='PROVED_CONDITIONALLY'
    return outcome
