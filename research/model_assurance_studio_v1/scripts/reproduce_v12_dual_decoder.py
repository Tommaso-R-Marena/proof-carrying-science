"""Replay both model decoders and both mathematical proof routes. No inference engines."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from studio.protobuf_dual_decoder_v12 import crosscheck,DualDecoderAssuranceGate
from studio.relational_kernel import canonical

ROOT=Path(__file__).resolve().parents[1]
PIN='aec03cc456c9f6c77e548cffa1dc1503d795c1934d97d114afe4b4a0d7418c6d'


def main():
    samples=ROOT/'samples'
    validation=ROOT/'validation'
    load=lambda name:json.loads((validation/name).read_text(encoding='utf8'))
    old=(samples/'demo_trained_iris_mlp.onnx').read_bytes()
    new=(samples/'demo_trained_iris_updated.onnx').read_bytes()
    policy=load('v09_demo_envelope_reviewer_policy.json')
    if hashlib.sha256(canonical(policy)).hexdigest()!=PIN:
        raise SystemExit('REFUSED: checked-in demonstration policy changed')
    checks=[crosscheck(old),crosscheck(new)]
    if any(c['status']!='AGREE' for c in checks):
        print(json.dumps({'status':'NOT_ESTABLISHED','decoders':checks},indent=2))
        raise SystemExit(2)
    gate=DualDecoderAssuranceGate(old,new,load('v09_demo_envelope_evidence.json'),
             load('v10_direct_fp32_partition_evidence.json'),policy,PIN)
    review=gate.review()
    inputs=load('v09_demo_input_words.json')
    observations=[]
    if review['status']=='PROVED_CONDITIONALLY':
        for index,expected in [('22',0),('62',1),('118',2)]:
            decision=gate.admit(inputs[index]);execution=gate.reference_infer(inputs[index])
            observations.append({'input_id':index,'decision':decision['status'],
                                 'execution':execution['status'],'class_index':decision.get('class_index')})
            if decision['status']!='ADMIT_CONDITIONALLY' or execution['status']!='EXECUTED_CONDITIONALLY' or decision['class_index']!=expected:
                raise SystemExit('REFUSED: reference execution did not match proof gate')
    outsider=gate.reference_infer(['00000000']*4)
    report={'schema':'pcs-independent-decoder-demonstration-v0.12',
            'status':'REPLAY_PASSED' if review['status']=='PROVED_CONDITIONALLY' and outsider['status']=='ABSTAIN' else 'NOT_ESTABLISHED',
            'model_decoders':checks,'review':review,'examples':observations,
            'uncovered_input_execution':outsider['status'],
            'official_onnx_checker':'NOT_RUN','lean_kernel_verification':'NOT_ESTABLISHED',
            'runtime_equivalence':'NOT_ESTABLISHED',
            'important_limitation':'This is a local experimental Python replay. Checked-in policy hash is NOT an independently managed trust root.'}
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0 if report['status']=='REPLAY_PASSED' else 2


if __name__=='__main__':raise SystemExit(main())
