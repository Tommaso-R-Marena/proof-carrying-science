"""Independent, deterministic replay of the packaged v0.7 evidence.

Requires the project source files and evidence JSON to be present. Runs
standard-library-only checkers; it NEVER treats absent Lean/ORT as a pass.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio.fp32_assurance import verify
from studio.fp32_lift_v07 import lift_single,lift_update
from studio.lean_export_v07 import export_relational,export_update
from studio.verify_relational import verify_with_policy
from studio.verify_update import verify_update_policy


def load(n):return json.loads((ROOT/'validation'/n).read_text())
def sample(n):return (ROOT/'samples'/n).read_bytes()

def main():
    old=sample('demo_trained_iris_mlp.onnx');new=sample('demo_trained_iris_updated.onnx')
    dense=sample('demo_dense_neural_violation.onnx')
    ok,result=verify(dense,load('v07_dense_fp32_reviewer_policy.json'),load('v07_dense_fp32_receipt.json'))
    assert ok,result
    print('PASS finite-rounding interval receipt with exact reviewer policy')
    basecert=load('v06_iris_property_1_certificate.json');basepol=load('v06_iris_property_1_reviewer_policy.json')
    driftcert=load('v06_update_drift_certificate.json');driftpol=load('v06_update_reviewer_policy.json')
    assert verify_with_policy(old,basecert,basepol)[0]
    assert verify_update_policy(old,new,driftcert,driftpol)[0]
    print('PASS baseline and update exact-real mathematical certificates')
    assert lift_single(old,basecert,basepol,'-499/1000')==load('v07_iris_fp32_margin.json')
    assert lift_update(old,new,basecert,basepol,driftcert,driftpol,'-37/100')==load('v07_iris_update_fp32_margin.json')
    print('PASS exact-rational conservative binary32 model and update envelopes')
    assert export_relational(old,basecert,basepol)==(ROOT/'validation/v07_iris_baseline_uncompiled.lean').read_text()
    assert export_update(old,new,driftcert,driftpol)==(ROOT/'validation/v07_iris_drift_uncompiled.lean').read_text()
    print('PASS byte-for-byte deterministic Lean source generation (not Lean compilation)')
    assert load('v07_iris_fp32_margin.json')['lean_kernel_verification']=='NOT_ESTABLISHED'
    assert load('v07_iris_update_fp32_margin.json')['runtime_conformance']=='NOT_ESTABLISHED'
    print('PASS no trust upgrade from absent Lean or official ONNX Runtime evidence')
    return 0

if __name__=='__main__':raise SystemExit(main())
