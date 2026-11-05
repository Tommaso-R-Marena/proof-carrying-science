"""Portable stdlib-only independent replay of the frozen v0.9 demonstration."""
from __future__ import annotations
import json
from pathlib import Path
from studio.operating_envelope_v09 import OperatingEnvelopeGate
from studio.guarded_reference_infer_v09 import reference_infer
from studio.verify_relational import strict_load

ROOT=Path(__file__).resolve().parents[1]
PIN='aec03cc456c9f6c77e548cffa1dc1503d795c1934d97d114afe4b4a0d7418c6d'

def main():
    p=strict_load(ROOT/'validation/v09_demo_envelope_reviewer_policy.json')
    e=strict_load(ROOT/'validation/v09_demo_envelope_evidence.json')
    inputs=strict_load(ROOT/'validation/v09_demo_input_words.json')
    old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
    new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    gate=OperatingEnvelopeGate(old,new,e,p,PIN)
    verdict=gate.review()
    if verdict['status']!='PROVED_CONDITIONALLY':
        print(json.dumps(verdict,sort_keys=True,indent=2));return 2
    examples={}
    for k,words in sorted(inputs.items()):
        example=reference_infer(gate,new,words)
        if example['status']!='EXECUTED_CONDITIONALLY':
            print(json.dumps(example,indent=2));return 2
        examples[k]={'class_index':example['class_index'],
                     'observed_margin':example['observed_margin']}
    blocked=reference_infer(gate,new,['00000000']*4)
    if blocked['status']!='ABSTAIN':return 2
    print(json.dumps({'status':'PROVED_CONDITIONALLY',
         'region_count':verdict['region_count'],
         'checked_comparisons':verdict['checked_comparisons'],
         'policy_sha256':PIN,'anchor_inference':examples,
         'out_of_region_status':blocked['status'],
         'lean_kernel_verification':'NOT_ESTABLISHED',
         'runtime_conformance':'NOT_ESTABLISHED'},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
