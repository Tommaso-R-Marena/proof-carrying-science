"""Deterministic untrusted producer for the six Iris direct-binary32 proofs.

The verifier does NOT trust this generator; replay with the separate reviewer.
"""
from pathlib import Path
import json
from studio.direct_fp32_v10 import POLICY_SCHEMA
from studio.direct_fp32_proposer_v10 import propose
from studio.dual_envelope_v10 import SCHEMA, verify_dual
from studio.relational_kernel import canonical
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[1]

def main():
    old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
    new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    policy=json.loads((ROOT/'validation/v09_demo_envelope_reviewer_policy.json').read_text())
    real_bundle=json.loads((ROOT/'validation/v09_demo_envelope_evidence.json').read_text())
    pin=sha256(canonical(policy)).hexdigest()
    entries=[]
    for region in policy['regions']:
        comps=[]
        for j in range(3):
            if j==region['class_index']:continue
            coeff=[0]*3;coeff[j]=1;coeff[region['class_index']]=-1
            derived={'schema':POLICY_SCHEMA,'model_sha256':sha256(new).hexdigest(),
                     'input_box':region['box'],'output_coefficients':[str(x) for x in coeff],
                     'upper_limit':str(-__import__('fractions').Fraction(region['minimum_margin']))}
            candidate=propose(new,derived,max_leaves=128,max_depth=16)
            if candidate['status']!='CANDIDATE_REPLAYED':
                raise RuntimeError('proposer could not certify '+region['id']+': '+str(candidate.get('reason')))
            comps.append({'other_class_index':j,'certificate':candidate['certificate']})
        entries.append({'region_id':region['id'],'comparisons':comps})
    bundle={'schema':SCHEMA,'policy_sha256':pin,'model_sha256':sha256(new).hexdigest(),'entries':entries}
    result=verify_dual(old,new,real_bundle,bundle,policy,pin)
    if result['status']!='PROVED_CONDITIONALLY':
        raise RuntimeError('independent dual review rejected: '+str(result.get('reason')))
    path=ROOT/'validation/v10_direct_fp32_partition_evidence.json'
    path.write_bytes(json.dumps(bundle,sort_keys=True,indent=2).encode()+b'\n')
    summary=ROOT/'validation/v10_direct_fp32_review.json'
    summary.write_bytes(json.dumps(result,sort_keys=True,indent=2).encode()+b'\n')
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=='__main__':main()
