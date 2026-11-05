"""UNTRUSTED proposer for finite correlated binary32 proof candidates.

Candidate creation must NEVER approve an independent review policy.  The
standard-library replayer recomputes all constraints and exact source hashes.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from studio.affine_fp32_v13 import POLICY_SCHEMA,propose,verify
from studio.affine_envelope_v13 import SCHEMA
from studio.relational_kernel import canonical,rational

ROOT=Path(__file__).resolve().parents[1]


def generated():
    model=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    policy=json.loads((ROOT/'validation/v09_demo_envelope_reviewer_policy.json').read_text())
    pinned=hashlib.sha256(canonical(policy)).hexdigest()
    entries=[]
    for region in policy['regions']:
        comps=[]
        for j in range(3):
            if j==region['class_index']:continue
            coeffs=[0]*3;coeffs[j]=1;coeffs[region['class_index']]=-1
            sub={'schema':POLICY_SCHEMA,'model_sha256':hashlib.sha256(model).hexdigest(),
                 'input_box':region['box'],'output_coefficients':[str(x) for x in coeffs],
                 'upper_limit':str(-rational(region['minimum_margin']))}
            result=propose(model,sub)
            if result['status']!='CANDIDATE_REPLAYED':
                raise ValueError('affine producer cannot prove every reviewer comparison')
            comps.append({'other_class_index':j,'certificate':result['certificate']})
        entries.append({'region_id':region['id'],'comparisons':comps})
    return {'schema':SCHEMA,'policy_sha256':pinned,
            'model_sha256':hashlib.sha256(model).hexdigest(),'entries':entries}


def main():
    obj=generated()
    dest=ROOT/'validation/v13_affine_iris_candidate.json'
    dest.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    print('Wrote untrusted candidate:',dest,'bytes',dest.stat().st_size)
    print('Review independently: python -S scripts/reproduce_v13_affine.py')

if __name__=='__main__':main()
