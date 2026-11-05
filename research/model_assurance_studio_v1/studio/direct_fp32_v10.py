"""Direct, independently replayed conditional binary32 partition certificates.

This deliberately does NOT use an ideal-real certificate, error propagation,
SciPy, or neural-network optimisation. The checker recomputes the deterministic
exact-rational interval interpretation of ordered, nonfused RN-even operations
on each leaf and checks a complete binary cover of a reviewer-pinned input box.

Claims concern ONLY the screened ONNX subset executed under the specified
software value semantics. No Lean verification, official ONNX Runtime
conformance, hostile process isolation, or deployment authorization is implied.
"""
from __future__ import annotations

import hashlib
from fractions import Fraction
from .dense_nn import screen_onnx, Unsupported
from .fp32_assurance import intervals, relation_upper
from .ieee754 import from_bits, UnsupportedFP32
from .relational_kernel import canonical, rational

POLICY_SCHEMA = 'pcs-direct-fp32-reviewer-policy-v0.10'
CERT_SCHEMA = 'pcs-direct-fp32-partition-certificate-v0.10'
REPORT_SCHEMA = 'pcs-direct-fp32-review-result-v0.10'
MAX_POLICY_BYTES = 32_768
MAX_CERT_BYTES = 250_000
MAX_LEAVES = 128
MAX_DEPTH = 16
MAX_OPS = 10_000


def _digest(value:bytes)->str:
    return hashlib.sha256(value).hexdigest()


def _fail(message):
    raise ValueError(message)


def _policy(model:bytes, policy:dict, independently_trusted_policy_sha256:str):
    if type(model) is not bytes or type(policy) is not dict:
        _fail('exact model bytes and reviewer policy required')
    if type(independently_trusted_policy_sha256) is not str or len(independently_trusted_policy_sha256)!=64 or any(c not in '0123456789abcdef' for c in independently_trusted_policy_sha256):
        _fail('reviewer-owned SHA256 fingerprint required')
    if set(policy)!={'schema','model_sha256','input_box','output_coefficients','upper_limit'} or policy.get('schema')!=POLICY_SCHEMA:
        _fail('unsupported policy schema or fields')
    if len(canonical(policy)) > MAX_POLICY_BYTES:
        _fail('oversize reviewer policy')
    if _digest(canonical(policy))!=independently_trusted_policy_sha256:
        _fail('reviewer policy fingerprint mismatch')
    if policy['model_sha256'] != _digest(model):
        _fail('model bytes differ from reviewer policy')
    spec=screen_onnx(model)
    bx=policy['input_box'];cs=policy['output_coefficients']
    if type(bx) is not list or len(bx)!=spec['input_width'] or type(cs) is not list or len(cs)!=spec['output_width']:
        _fail('reviewer box/relation dimension mismatch')
    if len(bx)>16 or len(cs)>16:
        _fail('reviewer dimension budget')
    box=[]
    for pair in bx:
        if type(pair) is not list or len(pair)!=2:
            _fail('box must contain a pair for each dimension')
        a,b = rational(pair[0]),rational(pair[1])
        if a>b:_fail('inverted reviewer input box')
        box.append((a,b))
    coeff=[rational(x) for x in cs]
    if not any(coeff):_fail('zero relation is not supported')
    return spec,tuple(box),tuple(coeff),rational(policy['upper_limit'])


def verify(model:bytes, policy:dict, certificate:dict, independently_trusted_policy_sha256:str)->dict:
    """Whole-cover soundness is enforced by recursive rederivation from the root.

    Any failure yields OPEN, not a partial acceptance. A SHA digest authenticates
    bytes only relative to an independently chosen reviewer trust anchor.
    """
    report={'schema':REPORT_SCHEMA,'status':'OPEN','lean_kernel_verification':'NOT_ESTABLISHED',
            'external_runtime_equivalence':'NOT_ESTABLISHED','deployment_authorization':'NOT_ESTABLISHED'}
    try:
        spec,box,coeff,limit=_policy(model,policy,independently_trusted_policy_sha256)
        if type(certificate) is not dict or set(certificate)!={'schema','policy_sha256','model_sha256','tree'}:
            _fail('malformed partition certificate')
        if certificate['schema']!=CERT_SCHEMA or certificate['model_sha256']!=_digest(model) or certificate['policy_sha256']!=independently_trusted_policy_sha256:
            _fail('certificate not bound to exact policy/model')
        if len(canonical(certificate))>MAX_CERT_BYTES:
            _fail('oversize partition certificate')
        checked=0;visited=0;worst=None

        def check_leaf_tree(tree,region,depth):
            nonlocal checked,visited,worst
            visited+=1
            if visited>2*MAX_LEAVES or depth>MAX_DEPTH:
                _fail('partition complexity limit exceeded')
            if type(tree) is not dict:
                _fail('invalid partition node')
            kind=tree.get('kind')
            if kind=='leaf':
                if set(tree)!={'kind','upper_bound'}:
                    _fail('invalid leaf fields')
                checked+=1
                if checked>MAX_LEAVES:
                    _fail('too many partition leaves')
                bound=relation_upper(intervals(spec,list(region)),coeff)
                if rational(tree['upper_bound'])!=bound:
                    _fail('untrusted leaf bound differs from independent calculation')
                if bound>limit:
                    _fail('unverified leaf: claim limit exceeded')
                worst=bound if worst is None else max(worst,bound)
                return
            if kind=='split':
                if set(tree)!={'kind','axis','at','left','right'}:
                    _fail('invalid split fields')
                axis=tree['axis']
                if type(axis) is not int or not 0<=axis<len(region):
                    _fail('invalid split axis')
                at=rational(tree['at'])
                lo,hi=region[axis]
                if not lo<at<hi:
                    _fail('split must strictly partition a nondegenerate interval')
                left=list(region);right=list(region)
                left[axis]=(lo,at);right[axis]=(at,hi)
                check_leaf_tree(tree['left'],tuple(left),depth+1)
                check_leaf_tree(tree['right'],tuple(right),depth+1)
                return
            _fail('unknown partition node')
        check_leaf_tree(certificate['tree'],box,0)
        if checked<1 or worst is None:
            _fail('certificate contains no proved leaves')
        return dict(report,status='PROVED_CONDITIONALLY',model_sha256=_digest(model),
                    policy_sha256=independently_trusted_policy_sha256,
                    leaf_count=checked,proven_upper_bound=str(worst),
                    required_upper_limit=str(limit),
                    semantic_scope='Exact rational interval checking of finite correctly rounded nonfused ordered binary32 operations, screened ONNX only')
    except (ValueError,TypeError,KeyError,OverflowError,ArithmeticError,MemoryError,RecursionError,
            UnsupportedFP32,Unsupported) as exc:
        return dict(report,reason=type(exc).__name__+': '+str(exc)[:160])


class DirectFP32Gate:
    """Host-controlled gate. A Python object is NOT a security boundary."""
    __slots__=('__model','__box','__review','__policy')

    def __init__(self, model:bytes, policy:dict, certificate:dict, trusted_policy_sha256:str):
        # Own the exact input data rather than retaining caller-owned dictionaries.
        from .verify_relational import strict_pairs
        import json
        self.__model=bytes(model)
        self.__policy=json.loads(canonical(policy),object_pairs_hook=strict_pairs)
        self.__review=verify(self.__model,self.__policy,certificate,trusted_policy_sha256)
        self.__box=tuple((rational(a),rational(b)) for a,b in self.__policy['input_box']) if self.__review['status']=='PROVED_CONDITIONALLY' else ()

    def review(self):
        return dict(self.__review)

    def admit(self, words:list[str])->dict:
        result={'schema':'pcs-direct-fp32-decision-v0.10','status':'ABSTAIN',
                'deployment_authorization':'NOT_ESTABLISHED'}
        try:
            if self.__review['status']!='PROVED_CONDITIONALLY':
                _fail('review not proved')
            if type(words) is not list or len(words)!=len(self.__box):
                _fail('wrong binary32 word count')
            if any(type(s) is not str or len(s)!=8 or any(c not in '0123456789abcdef' for c in s) for s in words):
                _fail('binary32 input must be exact lowercase hexadecimal words')
            values=[from_bits(int(s,16)) for s in words]
            if not all(lo<=v<=hi for v,(lo,hi) in zip(values,self.__box)):
                _fail('outside reviewer-pinned proved input box')
            return dict(result,status='ADMIT_CONDITIONALLY',input_bits=list(words),
                        model_sha256=self.__review['model_sha256'],
                        policy_sha256=self.__review['policy_sha256'],
                        proven_upper_bound=self.__review['proven_upper_bound'],
                        scope='only the reviewer-defined linear output inequality under specified software binary32 semantics')
        except (ValueError,TypeError,KeyError,OverflowError,MemoryError) as exc:
            return dict(result,reason=type(exc).__name__+': '+str(exc)[:120])
