"""Research-only proof-gated model inference with correlated FP32 certificates.

Alternative to, NOT a silent replacement of, the v0.12 partition-certified
runtime. Every output-class comparison requires: (i) existing exact-real
baseline/update+error-lift evidence, (ii) independently checked Google protobuf
numerical-semantic agreement on both exact model byte strings, and (iii) a
new separately rederived correlated binary32 affine certificate.

The trusted policy hash must be supplied by an independent reviewer; hashes or
thresholds from a user-uploaded certificate are never used as trust anchors.
The optional scalar evaluator is not an OS sandbox or official ONNX Runtime.
"""
from __future__ import annotations
import hashlib
import json
from .affine_fp32_v13 import POLICY_SCHEMA as AFFINE_POLICY_SCHEMA,verify as verify_affine
from .operating_envelope_v09 import OperatingEnvelopeGate
from .protobuf_dual_decoder_v12 import crosscheck
from .guarded_reference_infer_v09 import reference_infer
from .relational_kernel import rational,canonical

SCHEMA='pcs-correlated-binary32-envelope-v0.13'
REVIEW_SCHEMA='pcs-correlated-binary32-envelope-review-v0.13'
MAX_EVIDENCE_BYTES=200_000


def digest(value:bytes):return hashlib.sha256(value).hexdigest()


def review(old:bytes,new:bytes,real_bundle:dict,affine_bundle:dict,policy:dict,trusted_policy_sha256:str):
    outcome={'schema':REVIEW_SCHEMA,'status':'OPEN','deployment_authorization':'NOT_ESTABLISHED',
             'lean_kernel_verification':'NOT_ESTABLISHED','onnxruntime_equivalence':'NOT_ESTABLISHED'}
    try:
        if type(old) is not bytes or type(new) is not bytes:
            raise ValueError('immutable model bytes required')
        if type(affine_bundle) is not dict or set(affine_bundle)!={'schema','policy_sha256','model_sha256','entries'}:
            raise ValueError('incomplete or unsupported affine evidence bundle')
        if len(canonical(affine_bundle))>MAX_EVIDENCE_BYTES or affine_bundle['schema']!=SCHEMA:
            raise ValueError('affine evidence schema or size budget')
        if affine_bundle['policy_sha256']!=trusted_policy_sha256 or affine_bundle['model_sha256']!=digest(new):
            raise ValueError('affine evidence does not match externally trusted policy and updated model bytes')
        oldview,newview=crosscheck(old),crosscheck(new)
        if oldview['status']!='AGREE' or newview['status']!='AGREE':
            raise ValueError('independent protobuf decoder did not agree; no fallback')
        old_gate=OperatingEnvelopeGate(old,new,real_bundle,policy,trusted_policy_sha256)
        oldreview=old_gate.review()
        if oldreview['status']!='PROVED_CONDITIONALLY':
            raise ValueError('exact-real proof/update/error-lift checker refused evidence')
        from .dense_nn import screen_onnx
        output_count=screen_onnx(new)['output_width']
        regs=policy['regions']
        entries=affine_bundle['entries']
        if type(entries) is not list or len(entries)!=len(regs):
            raise ValueError('missing complete reviewer region set')
        checked=0;total_symbols=0
        for region,entry in zip(regs,entries):
            if type(entry) is not dict or set(entry)!={'region_id','comparisons'} or entry['region_id']!=region['id']:
                raise ValueError('missing or reordered reviewer region')
            winner=region['class_index']
            expected=[i for i in range(output_count) if i!=winner]
            comps=entry['comparisons']
            if type(comps) is not list or len(comps)!=len(expected):
                raise ValueError('incomplete class comparison evidence')
            for item,j in zip(comps,expected):
                if type(item) is not dict or set(item)!={'other_class_index','certificate'} or type(item['other_class_index']) is not int or item['other_class_index']!=j:
                    raise ValueError('missing, reordered or duplicated class comparison')
                coeffs=[0]*output_count;coeffs[j]=1;coeffs[winner]=-1
                # Derived from the approved independent policy, NOT from any
                # submitted certificate or user-supplied 'verified' report.
                subpolicy={'schema':AFFINE_POLICY_SCHEMA,'model_sha256':digest(new),
                           'input_box':region['box'],
                           'output_coefficients':[str(c) for c in coeffs],
                           'upper_limit':str(-rational(region['minimum_margin']))}
                subsha=digest(canonical(subpolicy))
                chk=verify_affine(new,subpolicy,item['certificate'],subsha)
                if chk['status']!='PROVED_CONDITIONALLY':
                    raise ValueError('correlated binary32 claim not established: '+chk.get('reason','OPEN')[:100])
                checked+=1;total_symbols+=chk['input_error_symbols']
        return dict(outcome,status='PROVED_CONDITIONALLY',
                    old_model_sha256=digest(old),model_sha256=digest(new),
                    policy_sha256=trusted_policy_sha256,verified_regions=len(regs),
                    affine_class_comparisons=checked,
                    total_affine_error_symbols_checked=total_symbols,
                    scope='replayed exact-real update + correlated binary32 affine bound + two-decoder agreement; shared Python/model semantics remain TCB')
    except (TypeError,ValueError,KeyError,ArithmeticError,OverflowError,MemoryError,RecursionError) as exc:
        return dict(outcome,reason=type(exc).__name__+': '+str(exc)[:160])


class AffineEnvelopeGate:
    __slots__=('__review','__inner','__new')

    def __init__(self,old,new,real_bundle,affine_bundle,policy,trusted_policy_sha256):
        self.__inner=None;self.__new=b''
        try:
            old=bytes(old);new=bytes(new)
            real_bundle=json.loads(canonical(real_bundle))
            affine_bundle=json.loads(canonical(affine_bundle))
            policy=json.loads(canonical(policy))
            self.__review=review(old,new,real_bundle,affine_bundle,policy,trusted_policy_sha256)
            if self.__review['status']=='PROVED_CONDITIONALLY':
                self.__inner=OperatingEnvelopeGate(old,new,real_bundle,policy,trusted_policy_sha256)
                self.__new=new
        except (TypeError,ValueError,KeyError,ArithmeticError,MemoryError,OverflowError) as exc:
            self.__review={'schema':REVIEW_SCHEMA,'status':'OPEN','reason':type(exc).__name__,
                           'deployment_authorization':'NOT_ESTABLISHED'}

    def review(self):return dict(self.__review)

    def admit(self,words):
        if self.__inner is None:
            return {'status':'ABSTAIN','reason':'One or more reviewer-owned claims or decoders unverified'}
        decision=self.__inner.admit(words)
        if decision.get('status')=='ADMIT_CONDITIONALLY':
            return dict(decision,affine_binary32_evidence='REPLAYED')
        return decision

    def reference_infer(self,words):
        if self.__inner is None:
            return {'status':'ABSTAIN','reason':'Proofs absent; execution refused'}
        result=reference_infer(self.__inner,self.__new,words)
        if result.get('status')=='EXECUTED_CONDITIONALLY':
            return dict(result,affine_binary32_evidence='REPLAYED')
        return result
