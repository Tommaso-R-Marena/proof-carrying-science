"""Stdlib-only independent reviewer replay; no solver/protobuf needed for math.

Combined protobuf + proof gate needs installed google.protobuf and never falls
back. Exit nonzero for any failure. This is Python TCB, NOT Lean/ONNX Runtime.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from studio.affine_fp32_v13 import POLICY_SCHEMA,verify as verify_affine
from studio.affine_envelope_v13 import AffineEnvelopeGate
from studio.fp32_assurance import intervals,relation_upper
from studio.dense_nn import screen_onnx
from studio.relational_kernel import canonical
from fractions import Fraction

ROOT=Path(__file__).resolve().parents[1]

def main():
    old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
    new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    real=json.loads((ROOT/'validation/v09_demo_envelope_evidence.json').read_text())
    bundle=json.loads((ROOT/'validation/v13_affine_iris_candidate.json').read_text())
    policy=json.loads((ROOT/'validation/v09_demo_envelope_reviewer_policy.json').read_text())
    trusted=hashlib.sha256(canonical(policy)).hexdigest()
    # Independent mathematical replay with *only the Python standard library*.
    n=0
    for region,entry in zip(policy['regions'],bundle['entries']):
        for competitor,item in zip([j for j in range(3) if j!=region['class_index']],entry['comparisons']):
            coeffs=[0]*3;coeffs[competitor]=1;coeffs[region['class_index']]=-1
            from studio.relational_kernel import rational
            sub={'schema':POLICY_SCHEMA,'model_sha256':hashlib.sha256(new).hexdigest(),
                 'input_box':region['box'],'output_coefficients':[str(c) for c in coeffs],
                 'upper_limit':str(-rational(region['minimum_margin']))}
            sha=hashlib.sha256(canonical(sub)).hexdigest()
            ans=verify_affine(new,sub,item['certificate'],sha)
            if ans['status']!='PROVED_CONDITIONALLY':
                raise RuntimeError(f'Affine checker failed: {region["id"]}: {ans}')
            n+=1
    # Correlation challenge: interval-based proof OPEN, affine proof ACCEPTED.
    correlated=(ROOT/'samples/demo_correlated_fp32_margin_v13.onnx').read_bytes()
    box=[(Fraction(-1000),Fraction(1000))]*2
    ibp=relation_upper(intervals(screen_onnx(correlated),box),[Fraction(1),Fraction(-1)])
    sub={'schema':POLICY_SCHEMA,'model_sha256':hashlib.sha256(correlated).hexdigest(),
         'input_box':[['-1000','1000']]*2,'output_coefficients':['1','-1'],'upper_limit':'-1/2'}
    cert=json.loads((ROOT/'validation/v13_correlated_margin_candidate.json').read_text())
    valid=verify_affine(correlated,sub,cert,hashlib.sha256(canonical(sub)).hexdigest())
    if ibp<=Fraction(-1,2) or valid['status']!='PROVED_CONDITIONALLY':
        raise RuntimeError('correlation challenge fails to separate verifier capabilities')
    summary={'schema':'pcs-v13-correlation-replay','math_comparisons_checked':n,
             'correlation_standard_interval_upper':str(ibp),
             'correlation_affine_bound_below_required_limit':True,
             'lean_kernel_verification':'NOT_ESTABLISHED',
             'onnxruntime_equivalence':'NOT_ESTABLISHED'}
    # This optional runtime gate is not available with -S. Its absence is
    # REPORTED, not treated as an accepted independent protobuf check.
    try:
        import google.protobuf
        gate=AffineEnvelopeGate(old,new,real,bundle,policy,trusted)
        summary['complete_gate_review']=gate.review()
        if summary['complete_gate_review']['status']!='PROVED_CONDITIONALLY':
            raise RuntimeError('independent double-decoder + proof gate did not admit')
        vectors=json.loads((ROOT/'validation/v09_demo_input_words.json').read_text())
        for item,words in vectors.items():
            if gate.reference_infer(words)['status']!='EXECUTED_CONDITIONALLY':
                raise RuntimeError('reference inference was not conditionally admitted: '+item)
        if gate.reference_infer(['00000000']*4)['status']!='ABSTAIN':
            raise RuntimeError('out-of-region reference inference failed to abstain')
        summary['admitted_reference_examples']=len(vectors)
        summary['out_of_region_reference_result']='ABSTAIN'
    except ImportError:
        summary['complete_gate_review']={'status':'NOT_ESTABLISHED','reason':'Independent protobuf dependency unavailable'}
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':sys.exit(main())
