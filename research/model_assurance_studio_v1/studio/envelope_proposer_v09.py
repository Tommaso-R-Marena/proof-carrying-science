"""Untrusted proposer: generates a complete region-certification bundle.

Uses SciPy to suggest dual multipliers; the reviewer does not import SciPy.
Never produces a deployment approval. Policy must be independently pinned.
"""
from __future__ import annotations
from .relational_prover import propose as prove_baseline
from .update_prover import propose as prove_drift
from .relational_kernel import canonical
from .operating_envelope_v09 import (POLICY_SCHEMA,BUNDLE_SCHEMA,_hash,verify_envelope)
from .dense_nn import screen_onnx


def propose(old:bytes,new:bytes,policy:dict):
    try:
        if type(policy) is not dict or policy.get('schema')!=POLICY_SCHEMA:
            raise ValueError('unsupported policy')
        if _hash(old)!=policy['old_model_sha256'] or _hash(new)!=policy['new_model_sha256']:
            raise ValueError('untrusted proposer model differs from policy')
        spec=screen_onnx(new)
        entries=[]
        for r in policy['regions']:
            comparisons=[]
            for j in range(spec['output_width']):
                if j==r['class_index']:continue
                coeffs=[0]*spec['output_width'];coeffs[j]=1;coeffs[r['class_index']]=-1
                old_cert=prove_baseline(old,r['box'],[str(c) for c in coeffs],r['baseline_upper_limit'])
                drift_cert=prove_drift(old,new,r['box'],[str(c) for c in coeffs],r['drift_upper_limit'])
                if old_cert['status']!='PROVED_CONDITIONALLY' or drift_cert['status']!='PROVED_CONDITIONALLY':
                    return {'status':'OPEN','reason':f'no complete proof for {r["id"]}/{j}',
                            'baseline_reason':old_cert.get('reason'),'drift_reason':drift_cert.get('reason')}
                comparisons.append({'other_class_index':j,
                                    'baseline_certificate':old_cert['certificate'],
                                    'drift_certificate':drift_cert['certificate']})
            entries.append({'region_id':r['id'],'comparisons':comparisons})
        packet={'schema':BUNDLE_SCHEMA,'policy_sha256':_hash(canonical(policy)),
                'old_model_sha256':_hash(old),'new_model_sha256':_hash(new),'entries':entries}
        result=verify_envelope(old,new,packet,policy,_hash(canonical(policy)))
        if result['status']!='PROVED_CONDITIONALLY':
            return {'status':'OPEN','reason':'independent verifier rejected entire bundle: '+result.get('reason','')}
        return {'status':'PROVED_CONDITIONALLY','bundle':packet,
                'note':'Untrusted proposer output. Reviewer must pin policy fingerprint via an independent channel.'}
    except Exception as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:150]}
