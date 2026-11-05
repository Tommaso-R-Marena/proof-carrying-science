"""Reviewer-pinned, fail-closed, multi-region model-update admission gate.

The host, not a model, must choose the trusted policy SHA-256. Each region
must carry complete conditional proof-gated update certificates for EVERY
competing output. Input membership uses the exact finite binary32 values of
host-supplied uint32 words, never an approximate decimal comparison.

The result is CONDITIONAL input admissibility, not production authorization:
no actual model is executed, no Lean kernel has checked these results, and a
separate trusted host must enforce the same model hash and byte-level input.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from .relational_kernel import rational, canonical
from .reviewer_gate_v08 import verify as review_update, SCHEMA as UPDATE_SCHEMA
from .dense_nn import screen_onnx
from .ieee754 import from_bits
from .verify_relational import strict_load

POLICY_SCHEMA = 'pcs-operating-envelope-policy-v0.9'
BUNDLE_SCHEMA = 'pcs-operating-envelope-certificate-set-v0.9'
MAX_REGIONS = 12
MAX_BUNDLE_BYTES = 4_000_000
MAX_POLICY_BYTES = 65_536


def _hash(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def _digest_ok(v):
    return type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v)


def _box(box,width):
    if type(box) is not list or len(box)!=width:
        raise ValueError('box width mismatch')
    parsed=[]
    for pair in box:
        if type(pair) is not list or len(pair)!=2:raise ValueError('box pair shape')
        a,b=rational(pair[0]),rational(pair[1])
        if a>b:raise ValueError('inverted box')
        parsed.append((a,b))
    return tuple(parsed)


def verify_envelope(old:bytes, new:bytes, bundle:dict, policy:dict,
                    expected_policy_sha256:str)->dict:
    """Independently check the entire certificate set. All-or-nothing verdict."""
    result={'schema':'pcs-operating-envelope-review-v0.9','status':'OPEN',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'onnx_runtime_equivalence':'NOT_ESTABLISHED',
            'deployment_authorization':'NOT_ESTABLISHED'}
    try:
        if type(old) is not bytes or type(new) is not bytes:
            raise ValueError('model must be exact bytes')
        if not _digest_ok(expected_policy_sha256):raise ValueError('missing trusted policy fingerprint')
        if type(policy) is not dict or set(policy)!={'schema','old_model_sha256','new_model_sha256','regions'}:
            raise ValueError('policy fields')
        if policy['schema']!=POLICY_SCHEMA or len(canonical(policy))>MAX_POLICY_BYTES:
            raise ValueError('policy version or budget')
        if _hash(canonical(policy))!=expected_policy_sha256:
            raise ValueError('policy is not independently pinned')
        if not (_digest_ok(policy['old_model_sha256']) and _digest_ok(policy['new_model_sha256'])):
            raise ValueError('invalid pinned model hashes')
        if _hash(old)!=policy['old_model_sha256'] or _hash(new)!=policy['new_model_sha256']:
            raise ValueError('model bytes differ from trusted policy')
        if type(bundle) is not dict or set(bundle)!={'schema','policy_sha256','old_model_sha256','new_model_sha256','entries'}:
            raise ValueError('bundle fields')
        if bundle['schema']!=BUNDLE_SCHEMA or len(canonical(bundle))>MAX_BUNDLE_BYTES:
            raise ValueError('bundle version or budget')
        if (bundle['policy_sha256']!=expected_policy_sha256 or
            bundle['old_model_sha256']!=policy['old_model_sha256'] or
            bundle['new_model_sha256']!=policy['new_model_sha256']):
            raise ValueError('bundle not bound to independently approved policy and model hashes')
        oldspec=screen_onnx(old);newspec=screen_onnx(new)
        if (oldspec['input_width']!=newspec['input_width'] or
            oldspec['output_width']!=newspec['output_width']):
            raise ValueError('updated model interface changed')
        width=oldspec['input_width'];outputs=oldspec['output_width']
        if outputs<2:raise ValueError('at least two model outputs required')
        regions=policy['regions'];entries=bundle['entries']
        if (type(regions) is not list or type(entries) is not list or
            not 1<=len(regions)<=MAX_REGIONS or len(regions)!=len(entries)):
            raise ValueError('region count/budget')
        verified=[];used=set();checked=0
        for r,e in zip(regions,entries):
            if type(r) is not dict or set(r)!={'id','box','class_index','minimum_margin','baseline_upper_limit',
                                             'drift_upper_limit','required_float32_upper_limit'}:
                raise ValueError('region policy fields')
            if type(e) is not dict or set(e)!={'region_id','comparisons'}:
                raise ValueError('region evidence fields')
            ident=r['id'];winner=r['class_index']
            if (type(ident) is not str or not 1<=len(ident)<=48 or not ident.isascii() or
                not all(ch.isalnum() or ch in '-_' for ch in ident) or ident in used):
                raise ValueError('invalid/duplicated region ID')
            used.add(ident)
            if type(winner) is not int or not 0<=winner<outputs:
                raise ValueError('invalid proposed output class')
            box=_box(r['box'],width)
            minimum=rational(r['minimum_margin'])
            baseline=rational(r['baseline_upper_limit'])
            drift=rational(r['drift_upper_limit'])
            fp_upper=rational(r['required_float32_upper_limit'])
            if minimum<=0 or fp_upper>-minimum or baseline+drift>fp_upper:
                raise ValueError('margin/bound insufficient for proposed region')
            comparisons=e['comparisons']
            if (e['region_id']!=ident or type(comparisons) is not list or
                len(comparisons)!=outputs-1):
                raise ValueError('not all competing classes covered')
            competitors=[j for j in range(outputs) if j!=winner]
            for j,comp in zip(competitors,comparisons):
                if type(comp) is not dict or set(comp)!={'other_class_index','baseline_certificate','drift_certificate'}:
                    raise ValueError('malformed comparison proof')
                if type(comp['other_class_index']) is not int or comp['other_class_index']!=j:
                    raise ValueError('missing/duplicated/out-of-order competitor')
                coeffs=[0]*outputs;coeffs[j]=1;coeffs[winner]=-1
                nested_policy={'schema':UPDATE_SCHEMA,
                    'old_model_sha256':policy['old_model_sha256'],
                    'new_model_sha256':policy['new_model_sha256'],
                    'input_box':r['box'], 'output_coefficients':[str(x) for x in coeffs],
                    'baseline_upper_limit':str(baseline),
                    'drift_upper_limit':str(drift),
                    'required_updated_upper_limit':str(fp_upper),
                    'required_float32_upper_limit':str(fp_upper)}
                observation=review_update(old,new,comp['baseline_certificate'],comp['drift_certificate'],nested_policy)
                if observation['status']!='PROVED_CONDITIONALLY':
                    raise ValueError(f'certificate for {ident}/{j} rejected: {observation.get("reason", "no evidence")[:95]}')
                checked+=1
            verified.append({'id':ident,'box':box,'class_index':winner,'minimum_margin':minimum})
        return dict(result,status='PROVED_CONDITIONALLY',
                    policy_sha256=expected_policy_sha256,model_sha256=_hash(new),
                    checked_comparisons=checked,region_count=len(verified),
                    verified_regions=verified,
                    evidence_scope='restricted screened ONNX, conservative exact-real + assumed binary32 rounding; NOT Lean or runtime equivalence')
    except (ValueError,TypeError,KeyError,OverflowError,ArithmeticError,MemoryError) as exc:
        return dict(result,reason=f'{type(exc).__name__}: {str(exc)[:175]}')


def _decide_verified(review:dict, new:bytes, input_words:list[str])->dict:
    """Host-provided FP32 *bit words* only. Rechecking model digest prevents substitution."""
    ret={'schema':'pcs-operating-envelope-decision-v0.9','status':'ABSTAIN',
         'deployment_authorization':'NOT_ESTABLISHED'}
    try:
        if review.get('status')!='PROVED_CONDITIONALLY':
            raise ValueError('envelope has not passed independent review')
        if type(new) is not bytes or _hash(new)!=review['model_sha256']:
            raise ValueError('model changed after certificate review')
        if type(input_words) is not list or not input_words or len(input_words)>16:
            raise ValueError('invalid input shape')
        if any(type(w) is not str or len(w)!=8 or any(ch not in '0123456789abcdef' for ch in w)
               for w in input_words):
            raise ValueError('FP32 inputs require eight lowercase hexadecimal digits per element')
        vec=tuple(from_bits(int(w,16)) for w in input_words)
        matching=[]
        for region in review['verified_regions']:
            if len(vec)==len(region['box']) and all(lo<=x<=hi for x,(lo,hi) in zip(vec,region['box'])):
                matching.append(region)
        if not matching:return dict(ret,reason='no fully verified operating region covers exact input')
        winners={r['class_index'] for r in matching}
        if len(winners)!=1:return dict(ret,reason='inconsistent region decisions: fail closed')
        # Must bind the same approved bytes and exact float32 input forwarded by the host.
        return dict(ret,status='ADMIT_CONDITIONALLY',class_index=next(iter(winners)),
                    minimum_margin=str(min(r['minimum_margin'] for r in matching)),
                    region_ids=[r['id'] for r in matching],
                    policy_sha256=review['policy_sha256'],model_sha256=review['model_sha256'],
                    input_bits=input_words,
                    authority='CONDITIONAL_PYTHON_EVIDENCE_ONLY; host must enforce same bytes, policy and numerical assumptions')
    except (ValueError,TypeError,KeyError,OverflowError,MemoryError) as exc:
        return dict(ret,reason=f'{type(exc).__name__}: {str(exc)[:175]}')


class OperatingEnvelopeGate:
    """Trusted-host facade; never accepts a caller-supplied preverified report.

    Instantiate once with independently trusted policy identity, check every
    certificate before allowing any input, and keep the verified state private.
    Python object isolation is NOT an adversarial OS process boundary.
    """
    __slots__ = ('__review', '__new')

    def __init__(self, old:bytes, new:bytes, bundle:dict, policy:dict,
                 expected_policy_sha256:str):
        self.__review=verify_envelope(old,new,bundle,policy,expected_policy_sha256)
        self.__new=bytes(new)

    def review(self)->dict:
        return {k:v for k,v in self.__review.items() if k!='verified_regions'}

    def admit(self,input_words:list[str])->dict:
        return _decide_verified(self.__review,self.__new,input_words)


def main(argv=None):
    p=argparse.ArgumentParser(description='Independently reviewed, fail-closed classifier operating envelope')
    p.add_argument('old_model');p.add_argument('new_model');p.add_argument('certificate_bundle');p.add_argument('reviewer_policy')
    p.add_argument('--trusted-policy-sha256',required=True,help='MUST be obtained independently of model/provider/bundle')
    p.add_argument('--input-bits',nargs='+',help='exact model input words, eight lowercase hex digits each')
    a=p.parse_args(argv)
    try:
        old=Path(a.old_model).read_bytes();new=Path(a.new_model).read_bytes()
        bundle=strict_load(a.certificate_bundle);policy=strict_load(a.reviewer_policy)
        guard=OperatingEnvelopeGate(old,new,bundle,policy,a.trusted_policy_sha256)
        report=guard.review()
        if a.input_bits is not None:
            response={'review':report,
                      'decision':guard.admit(a.input_bits)}
            good=response['decision']['status']=='ADMIT_CONDITIONALLY'
        else:
            response=report
            good=report['status']=='PROVED_CONDITIONALLY'
    except (OSError,ValueError,UnicodeError) as exc:
        response={'status':'OPEN','reason':type(exc).__name__};good=False
    print(json.dumps(response,sort_keys=True,indent=2))
    return 0 if good else 2

if __name__=='__main__':raise SystemExit(main())
