"""Reviewer-pinned intersection of two distinct assurance derivations.

The v0.9 gate checks exact-real relational + same-input update Farkas proofs,
then a conservative float32 error lift. This additional gate ALSO requires a
separate direct float32 partition cover for every reviewer-required competitor.

Both checkers share Python and screened ONNX semantics: this is *not* independent
implementation diversity, an OS security boundary, or Lean kernel assurance.
"""
from __future__ import annotations
import json
from .operating_envelope_v09 import OperatingEnvelopeGate, _hash, _digest_ok
from .relational_kernel import canonical, rational
from .direct_fp32_v10 import POLICY_SCHEMA, verify as verify_direct
from .guarded_reference_infer_v09 import reference_infer

SCHEMA='pcs-dual-operating-envelope-evidence-v0.10'
REPORT_SCHEMA='pcs-dual-operating-envelope-review-v0.10'
MAX_DUAL_BUNDLE_BYTES=3_000_000


def verify_dual(old:bytes,new:bytes,real_bundle:dict,direct_bundle:dict,
                reviewer_policy:dict,trusted_policy_sha256:str)->dict:
    result={'schema':REPORT_SCHEMA,'status':'OPEN',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'runtime_equivalence':'NOT_ESTABLISHED',
            'deployment_authorization':'NOT_ESTABLISHED'}
    try:
        gate=OperatingEnvelopeGate(old,new,real_bundle,reviewer_policy,trusted_policy_sha256)
        real=gate.review()
        if real['status']!='PROVED_CONDITIONALLY':
            raise ValueError('original real+error-lift review rejected: '+str(real.get('reason','unknown'))[:95])
        if type(direct_bundle) is not dict or set(direct_bundle)!={'schema','policy_sha256','model_sha256','entries'}:
            raise ValueError('direct evidence bundle fields')
        if direct_bundle['schema']!=SCHEMA or len(canonical(direct_bundle))>MAX_DUAL_BUNDLE_BYTES:
            raise ValueError('direct evidence version or byte budget')
        if direct_bundle['policy_sha256']!=trusted_policy_sha256 or direct_bundle['model_sha256']!=_hash(new):
            raise ValueError('direct evidence detached from independently pinned policy or updated model')
        entries=direct_bundle['entries'];regions=reviewer_policy['regions']
        if type(entries) is not list or len(entries)!=len(regions):
            raise ValueError('direct evidence missing a complete reviewer region')
        checked=0;leaves=0
        # All reviewer policies are derived by the trusted checker; they are
        # never taken from certificates or the untrusted producer's bundle.
        for region,entry in zip(regions,entries):
            if type(entry) is not dict or set(entry)!={'region_id','comparisons'} or entry['region_id']!=region['id']:
                raise ValueError('missing, reordered or substituted region')
            winner=region['class_index']
            output_count= len(real_bundle['entries'][0]['comparisons'])+1
            expected=[k for k in range(output_count) if k!=winner]
            comps=entry['comparisons']
            if type(comps) is not list or len(comps)!=len(expected):
                raise ValueError('missing competing class direct proof')
            for j,item in zip(expected,comps):
                if type(item) is not dict or set(item)!={'other_class_index','certificate'} or type(item['other_class_index']) is not int or item['other_class_index']!=j:
                    raise ValueError('misaligned competing class direct proof')
                coeff=[0]*output_count;coeff[winner]=-1;coeff[j]=1
                derived={'schema':POLICY_SCHEMA,'model_sha256':_hash(new),
                         'input_box':region['box'],
                         'output_coefficients':[str(x) for x in coeff],
                         'upper_limit':str(-rational(region['minimum_margin']))}
                digest=_hash(canonical(derived))
                direct=verify_direct(new,derived,item['certificate'],digest)
                if direct['status']!='PROVED_CONDITIONALLY':
                    raise ValueError('direct float32 proof rejected: '+str(direct.get('reason','unknown'))[:100])
                checked+=1;leaves+=direct['leaf_count']
        return dict(result,status='PROVED_CONDITIONALLY',
                    real_certificate_comparisons=real['checked_comparisons'],
                    direct_float32_comparisons=checked,
                    checked_fp32_partition_leaves=leaves,
                    region_count=len(regions),
                    model_sha256=_hash(new),policy_sha256=trusted_policy_sha256,
                    evidence_scope='intersection of conditional v0.9 real+rounding and v0.10 direct RN-even interval proofs; shared Python/screened-ONNX TCB')
    except (ValueError,TypeError,KeyError,OverflowError,ArithmeticError,MemoryError,RecursionError) as exc:
        return dict(result,reason=type(exc).__name__+': '+str(exc)[:160])


class DualAssuranceGate:
    """Minimal wrapper: both complete proofs must succeed before dispatch."""
    __slots__=('__review','__inner','__new')
    def __init__(self,old:bytes,new:bytes,real_bundle:dict,direct_bundle:dict,
                 policy:dict,trusted_policy_sha256:str):
        # Freeze by JSON round-trip and bytes snapshot, preventing later caller
        # mutations from affecting this gate's verified state.
        self.__inner=None
        self.__new=b''
        self.__review={'schema':REPORT_SCHEMA,'status':'OPEN',
                       'lean_kernel_verification':'NOT_ESTABLISHED',
                       'runtime_equivalence':'NOT_ESTABLISHED',
                       'deployment_authorization':'NOT_ESTABLISHED'}
        try:
            old=bytes(old);new=bytes(new)
            real_bundle=json.loads(canonical(real_bundle))
            direct_bundle=json.loads(canonical(direct_bundle))
            policy=json.loads(canonical(policy))
            self.__review=verify_dual(old,new,real_bundle,direct_bundle,policy,trusted_policy_sha256)
            if self.__review['status']=='PROVED_CONDITIONALLY':
                self.__inner=OperatingEnvelopeGate(old,new,real_bundle,policy,trusted_policy_sha256)
                self.__new=new
        except (TypeError,ValueError,KeyError,MemoryError,OverflowError,RecursionError) as exc:
            self.__review=dict(self.__review,reason='Invalid gate inputs: '+type(exc).__name__)

    def review(self)->dict:
        return dict(self.__review)

    def admit(self,words:list[str])->dict:
        if self.__inner is None:
            return {'status':'ABSTAIN','reason':'Both evidence families are required for admission',
                    'deployment_authorization':'NOT_ESTABLISHED'}
        outcome=self.__inner.admit(words)
        if outcome['status']=='ADMIT_CONDITIONALLY':
            outcome['dual_fp32_evidence']='REPLAYED'
        return outcome

    def reference_infer(self,words:list[str])->dict:
        if self.__inner is None:
            return {'status':'ABSTAIN','reason':'Dual evidence incomplete; model execution denied',
                    'deployment_authorization':'NOT_ESTABLISHED'}
        # Reference computation remains available only via this method, which
        # requires the complete earlier dual review. No arbitrary model path.
        outcome=reference_infer(self.__inner,self.__new,words)
        if outcome['status']=='EXECUTED_CONDITIONALLY':
            outcome['dual_fp32_evidence']='REPLAYED'
        return outcome
