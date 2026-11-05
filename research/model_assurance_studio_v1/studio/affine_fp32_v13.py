"""Correlation-preserving *conditional* binary32 value semantics (research v0.13).

This is a new independent rederivation route, NOT a Lean kernel proof. For the
screened ONNX subset, every scalar is represented as an affine function of
bounded independent variables: one shared noise symbol per input coordinate,
and fresh bounded symbols for each non-exact correctly-rounded operation and
unstable ReLU. Shared upstream values keep shared symbols, preserving linear
relationships between different logits. No independence or probabilistic
assumption about the error variables is used: every symbol may take ANY value
in [-1,1].

Under the explicit scalar RN-even/non-fused/non-FTZ/finite-execution model:
 |round32(z) - z| <= 2^-24 |z| + 2^-150.
This overapproximation is deliberately conservative, even for subnormals.
Rounder endpoint checks refuse boxes that could overflow to nonfinite results.
The only accepted claim is a reviewer-owned linear inequality over a fixed box.

This does not validate general ONNX or ONNX Runtime, hardware semantics, Lean,
public deployment, independent policy custody, or arbitrary AI/model safety.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from .dense_nn import screen_onnx, Unsupported
from .ieee754 import round_value, UnsupportedFP32
from .relational_kernel import rational, canonical

POLICY_SCHEMA = 'pcs-affine-fp32-policy-v0.13'
CERT_SCHEMA = 'pcs-affine-fp32-certificate-v0.13'
REVIEW_SCHEMA = 'pcs-affine-fp32-review-v0.13'
MAX_POLICY_BYTES = 32768
MAX_CERT_BYTES = 2048
MAX_SYMBOLS = 800
MAX_TERMS = 15000
MAX_BITS = 3072
MAX_MODEL_INPUTS = 16
_EPS = Fraction(1, 1 << 24)
_MIN_HALF_SUBNORMAL = Fraction(1, 1 << 150)


def _q(value):
    q = value if type(value) is Fraction else rational(value)
    if max(q.numerator.bit_length(),q.denominator.bit_length()) > MAX_BITS:
        raise ValueError('affine rational resource limit')
    return q


@dataclass(frozen=True)
class Affine:
    center: Fraction
    terms: dict[int, Fraction]

    def bound(self):
        radius = _q(sum((abs(q) for q in self.terms.values()), Fraction(0)))
        return _q(self.center - radius), _q(self.center + radius)


class _Engine:
    def __init__(self):
        self.next_id = 0
        self.symbols = 0
        self.operations = 0
        self.terms_seen = 0

    def new(self, q):
        q = _q(q)
        if q == 0:
            return {}
        if self.next_id >= MAX_SYMBOLS:
            raise ValueError('too many independent error symbols')
        ident = self.next_id
        self.next_id += 1
        self.symbols += 1
        return {ident: q}

    def form(self, center, terms=None):
        center = _q(center)
        raw = terms or {}
        t = {i:_q(c) for i,c in raw.items() if c}
        self.terms_seen += len(t)
        if self.terms_seen > MAX_TERMS:
            raise ValueError('affine expression budget exceeded')
        return Affine(center,t)

    def _round(self, x):
        """Append an error symbol whose magnitude bounds RN-even for every x.

        Enclosure endpoints are computed from exact rationals, including all
        previous independent error symbols. RN-even is monotone on finite
        inputs, so rounding both endpoints also checks potential overflow.
        """
        lo,hi = x.bound()
        round_value(lo);round_value(hi)
        if not x.terms:
            return self.form(round_value(x.center))
        radius = _q(_EPS * max(abs(lo),abs(hi)) + _MIN_HALF_SUBNORMAL)
        terms = x.terms.copy()
        terms.update(self.new(radius))
        self.operations += 1
        return self.form(x.center,terms)

    def scale(self,x,w):
        w = _q(w)
        if not w:
            return self.form(0)
        exact = self.form(x.center*w,{k:v*w for k,v in x.terms.items()})
        return self._round(exact)

    def add(self,x,y):
        terms = x.terms.copy()
        for k,v in y.terms.items():
            terms[k] = _q(terms.get(k,Fraction(0))+v)
            if not terms[k]:del terms[k]
        return self._round(self.form(x.center+y.center,terms))

    def relu(self,x):
        lo,hi=x.bound()
        if lo>=0:return x
        if hi<=0:return self.form(0)
        # For every z in [lo,hi]: ReLU(z)-lambda*z in [0,E].
        slope=_q(hi/(hi-lo))
        err=_q((-lo*hi)/(hi-lo))
        terms={k:_q(v*slope) for k,v in x.terms.items()}
        terms.update(self.new(err/2))
        return self.form(_q(x.center*slope+err/2),terms)


def _derive(spec, box):
    if len(box)!=spec['input_width'] or spec['input_width']>MAX_MODEL_INPUTS:
        raise ValueError('input dimension mismatch')
    e = _Engine()
    xs=[]
    for lo,hi in box:
        if lo>hi:raise ValueError('inverted reviewer domain')
        # Require finite possible binary32 inputs: the actual admitted values
        # form a subset of this real-number box.
        round_value(lo);round_value(hi)
        center=_q((lo+hi)/2)
        radius=_q((hi-lo)/2)
        xs.append(e.form(center,e.new(radius)))
    env={spec['input']:xs}
    weights=spec['weights']
    for node in spec['nodes']:
        op,ins,out=node['op'],node['inputs'],node['out']
        if op in ('MatMul','Gemm'):
            source=env[ins[0]]
            matrix=weights[ins[1]]
            n,m=matrix['shape']
            ys=[]
            for j in range(m):
                accumulator=e.form(0)
                for i in range(n):
                    product=e.scale(source[i],Fraction.from_float(matrix['values'][i*m+j]))
                    accumulator=e.add(accumulator,product)
                if op=='Gemm':
                    accumulator=e.add(accumulator,e.form(Fraction.from_float(weights[ins[2]]['values'][j])))
                ys.append(accumulator)
        elif op=='Add':
            if ins[0] in weights or ins[1] in weights:
                constant=ins[0] if ins[0] in weights else ins[1]
                dynamic=ins[1] if ins[0] in weights else ins[0]
                ys=[e.add(x,e.form(Fraction.from_float(c)))
                    for x,c in zip(env[dynamic],weights[constant]['values'])]
            else:
                ys=[e.add(x,y) for x,y in zip(env[ins[0]],env[ins[1]])]
        elif op=='Relu':
            ys=[e.relu(x) for x in env[ins[0]]]
        elif op=='Identity':
            ys=list(env[ins[0]])
        else:
            raise ValueError('operation outside reviewed RN-even grammar')
        env[out]=ys
    return env[spec['output']],e


def _policy(model,policy,independent_sha):
    if type(model) is not bytes or type(policy) is not dict:
        raise ValueError('immutable model bytes and reviewer policy required')
    if type(independent_sha) is not str or len(independent_sha)!=64 or any(x not in '0123456789abcdef' for x in independent_sha):
        raise ValueError('reviewer-controlled digest required')
    if (set(policy)!={'schema','model_sha256','input_box','output_coefficients','upper_limit'}
        or policy.get('schema')!=POLICY_SCHEMA
        or len(canonical(policy))>MAX_POLICY_BYTES
        or sha256(canonical(policy)).hexdigest()!=independent_sha
        or sha256(model).hexdigest()!=policy.get('model_sha256')):
        raise ValueError('reviewer policy/bytes binding failed')
    spec=screen_onnx(model)
    box=policy['input_box'];coeffs=policy['output_coefficients']
    if type(box) is not list or len(box)!=spec['input_width'] or type(coeffs) is not list or len(coeffs)!=spec['output_width']:
        raise ValueError('reviewer policy dimensions')
    intervals=[]
    for pair in box:
        if type(pair) is not list or len(pair)!=2:
            raise ValueError('invalid reviewer box element')
        lo,hi=_q(pair[0]),_q(pair[1])
        if lo>hi:raise ValueError('inverted input domain')
        intervals.append((lo,hi))
    c=[_q(v) for v in coeffs]
    if not any(c):raise ValueError('no nonzero relation coefficients')
    return spec,intervals,c,_q(policy['upper_limit'])


def _bound(model,policy,trusted_sha):
    spec,box,coeff,limit=_policy(model,policy,trusted_sha)
    output,engine=_derive(spec,box)
    center=_q(sum((c*v.center for c,v in zip(coeff,output)),Fraction(0)))
    terms={}
    for c,value in zip(coeff,output):
        for k,v in value.terms.items():
            terms[k]=_q(terms.get(k,Fraction(0))+c*v)
            if not terms[k]:del terms[k]
    upper=_q(center+sum((abs(x) for x in terms.values()),Fraction(0)))
    return upper,limit,engine


def propose(model:bytes,policy:dict)->dict:
    """Untrusted producer: its self-derived policy digest is NOT a trust anchor."""
    try:
        sha=sha256(canonical(policy)).hexdigest()
        upper,limit,engine=_bound(model,policy,sha)
        # Short, conservative dyadic witness; raw rational bounds may have
        # hundreds of digits, and are never blindly parsed as authority.
        scaled=upper*(1<<40)
        coarse=Fraction(-(-scaled.numerator//scaled.denominator),1<<40)
        cert={'schema':CERT_SCHEMA,'model_sha256':sha256(model).hexdigest(),
              'policy_sha256':sha,'upper_bound':str(coarse)}
        result=verify(model,policy,cert,sha)
        return {'status':'CANDIDATE_REPLAYED' if result['status']=='PROVED_CONDITIONALLY' else 'OPEN',
                'certificate':cert,'review':result,
                'warning':'Derived digest is NOT independently reviewed; a reviewer must pin policy and model bytes separately'}
    except (TypeError,ValueError,KeyError,ArithmeticError,OverflowError,MemoryError,RecursionError,
            Unsupported,UnsupportedFP32) as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:150]}


def verify(model:bytes,policy:dict,certificate:dict,trusted_policy_sha256:str)->dict:
    """Independently rederive the whole relation, no solver or proposal trusted."""
    result={'schema':REVIEW_SCHEMA,'status':'OPEN',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'onnxruntime_equivalence':'NOT_ESTABLISHED',
            'deployment_authorization':'NOT_ESTABLISHED'}
    try:
        if type(certificate) is not dict or set(certificate)!={'schema','model_sha256','policy_sha256','upper_bound'}:
            raise ValueError('unsupported affine certificate fields')
        if (len(canonical(certificate))>MAX_CERT_BYTES or certificate['schema']!=CERT_SCHEMA
            or certificate['model_sha256']!=sha256(model).hexdigest()
            or certificate['policy_sha256']!=trusted_policy_sha256):
            raise ValueError('certificate/model/reviewer binding invalid')
        computed,limit,engine=_bound(model,policy,trusted_policy_sha256)
        claimed=_q(certificate['upper_bound'])
        if claimed<computed:
            raise ValueError('untrusted affine upper bound understates the rederived result')
        if claimed>limit or computed>limit:
            raise ValueError('relation not established over entire reviewer box')
        return dict(result,status='PROVED_CONDITIONALLY',
                    model_sha256=sha256(model).hexdigest(),
                    policy_sha256=trusted_policy_sha256,
                    proven_upper_bound=str(computed),
                    required_upper_limit=str(limit),
                    input_error_symbols=engine.symbols,
                    rounding_operations=engine.operations,
                    scope='restricted real-rational affine outer approximation with a per-operation binary32 RN-even error bound; no FMA/FTZ/signed-zero/exceptions')
    except (TypeError,ValueError,KeyError,ArithmeticError,OverflowError,MemoryError,RecursionError,
            Unsupported,UnsupportedFP32) as exc:
        return dict(result,reason=type(exc).__name__+': '+str(exc)[:160])


def main(argv=None):
    """Reviewer-oriented CLI: accepts only a separately pinned SHA-256 policy."""
    import argparse
    import json
    from pathlib import Path
    from .verify_relational import strict_load
    parser=argparse.ArgumentParser(description='Recheck a conditional affine binary32 certificate; no Lean/ONNX Runtime assurance')
    parser.add_argument('model');parser.add_argument('policy');parser.add_argument('certificate')
    parser.add_argument('--trusted-policy-sha256',required=True,
                        help='MUST come from a reviewer-controlled channel, never the submitted certificate')
    parser.add_argument('--report')
    args=parser.parse_args(argv)
    try:
        raw=Path(args.model).read_bytes()
        policy=strict_load(args.policy)
        cert=strict_load(args.certificate)
        result=verify(raw,policy,cert,args.trusted_policy_sha256)
    except (OSError,TypeError,ValueError,MemoryError) as exc:
        result={'schema':REVIEW_SCHEMA,'status':'OPEN','reason':type(exc).__name__,
                'lean_kernel_verification':'NOT_ESTABLISHED',
                'onnxruntime_equivalence':'NOT_ESTABLISHED'}
    summary=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if args.report:
        Path(args.report).write_text(summary,encoding='utf-8')
    print(summary,end='')
    return 0 if result['status']=='PROVED_CONDITIONALLY' else 2


if __name__=='__main__':
    raise SystemExit(main())
