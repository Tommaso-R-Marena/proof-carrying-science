"""Recompute illustrative v0.7 receipts from original bytes and explicit policies.

Does not claim Lean / official ONNX Runtime verification when tools are absent.
"""
from __future__ import annotations
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio.fp32_assurance import issue,verify,POLICY_SCHEMA,digest
from studio.fp32_lift_v07 import lift_single,lift_update
from studio.lean_export_v07 import export_relational,export_update
from studio.lean_status_v07 import check_proof
from studio.onnxruntime_crosscheck_v07 import compare as check_ort


def load(filename):return json.loads((ROOT/'validation'/filename).read_text())
def save(filename,obj):
    path=ROOT/'validation'/filename
    path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    return str(path)


def main():
    v=ROOT/'validation'
    raw=(ROOT/'samples/demo_dense_neural_violation.onnx').read_bytes()
    policy={'schema':POLICY_SCHEMA,'model_sha256':digest(raw),
         'input_box':[['-1','1'],['-1','1']],'output_coefficients':['1','0'],'upper_limit':'5/4'}
    receipt=issue(raw,policy)
    assert receipt['status']=='PROVED_CONDITIONALLY'
    assert verify(raw,policy,receipt)[0]
    save('v07_dense_fp32_reviewer_policy.json',policy)
    save('v07_dense_fp32_receipt.json',receipt)
    old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
    new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    old_cert=load('v06_iris_property_1_certificate.json');old_pol=load('v06_iris_property_1_reviewer_policy.json')
    drift_cert=load('v06_update_drift_certificate.json');drift_pol=load('v06_update_reviewer_policy.json')
    baseline=lift_single(old,old_cert,old_pol,'-499/1000')
    update=lift_update(old,new,old_cert,old_pol,drift_cert,drift_pol,'-37/100')
    assert baseline['status']==update['status']=='PROVED_CONDITIONALLY'
    save('v07_iris_fp32_margin.json',baseline)
    save('v07_iris_update_fp32_margin.json',update)
    (v/'v07_iris_baseline_uncompiled.lean').write_text(export_relational(old,old_cert,old_pol))
    (v/'v07_iris_drift_uncompiled.lean').write_text(export_update(old,new,drift_cert,drift_pol))
    for name in ('v07_iris_baseline_uncompiled.lean','v07_iris_drift_uncompiled.lean'):
        outcome=check_proof(v/name)
        save(name+'.check.json',outcome)
    save('v07_official_onnxruntime_status.json',check_ort(old,count=12))
    summary={'schema':'pcs-v07-validation-summary','independently_replayed_binary32':True,
       'old_model_sha256':digest(old),'new_model_sha256':digest(new),
       'real_model_bound':'-1/2','real_update_drift':'1/8','real_updated_bound':'-3/8',
       'rounding_margin_original_approx':float(__import__('fractions').Fraction(baseline['verified_float32_rounding_cushion'])),
       'rounding_margin_updated_approx':float(__import__('fractions').Fraction(update['new_model_rounding_cushion'])),
       'new_margin_lower_bound_approx':-float(__import__('fractions').Fraction(update['derived_float32_upper_bound'])),
       'claimed_minimum_margin_for_fp32_under_assumptions':'0.37',
       'lean_kernel_status':'NOT_ESTABLISHED',
       'onnxruntime_status':'NOT_ESTABLISHED',
       'security':'Not a sandbox; no external model execution in upload server'}
    save('v07_summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
