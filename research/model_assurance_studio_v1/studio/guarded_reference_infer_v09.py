"""Executable reference proof-gated inference for a screened tiny ONNX model.

A trusted host creates the OperatingEnvelopeGate from independently pinned
policy bytes. The gate is checked BEFORE any reference model computation.
Outputs use a deterministic correctly rounded software float32 interpreter,
not an actual ONNX Runtime, hardware kernel, secure sandbox, or Lean authority.
"""
from __future__ import annotations
from .operating_envelope_v09 import OperatingEnvelopeGate
from .dense_nn import screen_onnx
from .ieee754 import from_bits,round_bits
from .fp32_assurance import sequential_eval


def reference_infer(gate:OperatingEnvelopeGate, model:bytes, input_bits:list[str])->dict:
    outcome={'schema':'pcs-guarded-reference-inference-v0.9','status':'ABSTAIN',
             'runtime_equivalence':'NOT_ESTABLISHED','deployment_authorization':'NOT_ESTABLISHED'}
    try:
        if type(gate) is not OperatingEnvelopeGate:raise ValueError('missing verified gate instance')
        # Capture request words once: caller-owned lists may mutate concurrently.
        words=list(input_bits) if type(input_bits) is list else input_bits
        decision=gate.admit(words)
        if decision['status']!='ADMIT_CONDITIONALLY':
            return dict(outcome,reason='Gate abstained before model computation: '+decision.get('reason','unknown'))
        if decision['model_sha256']!=__import__('hashlib').sha256(model).hexdigest():
            return dict(outcome,reason='exact model changed between admission and reference execution')
        spec=screen_onnx(model)
        values=[from_bits(int(word,16)) for word in words]
        outputs=sequential_eval(spec,values)
        winner=int(decision['class_index'])
        if not (0<=winner<len(outputs)) or any(outputs[winner]<=outputs[k] for k in range(len(outputs)) if k!=winner):
            return dict(outcome,reason='Observed software output contradicts conditional prediction; no authority granted')
        return dict(outcome,status='EXECUTED_CONDITIONALLY',
                    class_index=winner,
                    input_bits=list(words),
                    output_bits=[f'{round_bits(x):08x}' for x in outputs],
                    observed_margin=str(min(outputs[winner]-outputs[k] for k in range(len(outputs)) if k!=winner)),
                    gate_evidence={k:decision[k] for k in ('policy_sha256','model_sha256','region_ids','minimum_margin')},
                    scope='checked certificate gate followed by screened exact float32 software reference, not an official production inference runtime')
    except (ValueError,KeyError,TypeError,OverflowError,MemoryError,ArithmeticError) as exc:
        return dict(outcome,reason=type(exc).__name__+': '+str(exc)[:150])
