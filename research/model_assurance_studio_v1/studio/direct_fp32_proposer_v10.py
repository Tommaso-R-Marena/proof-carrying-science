"""Untrusted heuristic producer of binary32 cover candidates.

Never grants assurance: every generated tree must be independently replayed by
studio.direct_fp32_v10.verify against a reviewer-owned policy fingerprint.
"""
from __future__ import annotations
from fractions import Fraction
from .direct_fp32_v10 import (_policy, _digest, CERT_SCHEMA, MAX_DEPTH,
                             MAX_LEAVES, verify)
from .fp32_assurance import intervals, relation_upper
from .dense_nn import Unsupported
from .ieee754 import UnsupportedFP32
from .relational_kernel import canonical


def propose(model:bytes,policy:dict, *, max_leaves=64, max_depth=12)->dict:
    try:
        if type(max_leaves) is not int or not 1<=max_leaves<=MAX_LEAVES or type(max_depth) is not int or not 0<=max_depth<=MAX_DEPTH:
            raise ValueError('invalid search budgets')
        trusted=_digest(canonical(policy)) # NOT an independent reviewer trust pin
        spec,box,coeff,limit=_policy(model,policy,trusted)
        budget=[max_leaves]

        def score(region):
            return relation_upper(intervals(spec,list(region)),coeff)

        def rec(region,depth):
            calculated=score(region)
            if calculated<=limit:
                budget[0]-=1
                if budget[0]<0:raise ValueError('leaf budget exceeded')
                return {'kind':'leaf','upper_bound':str(calculated)}
            if depth>=max_depth or budget[0]<2:
                raise ValueError('unable to prove entire box within partition budget')
            ranked=[]
            for dim,(a,b) in enumerate(region):
                if a>=b:continue
                mid=(a+b)/2
                left=list(region);right=list(region)
                left[dim]=(a,mid);right[dim]=(mid,b)
                a_score=score(tuple(left)); b_score=score(tuple(right))
                ranked.append((max(a_score,b_score),a_score+b_score,dim,mid,tuple(left),tuple(right)))
            if not ranked:raise ValueError('no further strict split possible')
            _,__,dim,mid,left,right=min(ranked)
            # Budget counts leaves (not interior nodes). Reserving a second leaf
            # must occur before descending the first; the final verifier remains authoritative.
            return {'kind':'split','axis':dim,'at':str(mid),
                    'left':rec(left,depth+1),'right':rec(right,depth+1)}
        tree=rec(box,0)
        cert={'schema':CERT_SCHEMA,'policy_sha256':trusted,'model_sha256':_digest(model),'tree':tree}
        checked=verify(model,policy,cert,trusted)
        if checked['status']!='PROVED_CONDITIONALLY':
            raise ValueError('independent review rejected proposer output')
        return {'status':'CANDIDATE_REPLAYED','certificate':cert,'replay_result':checked,
                'warning':'Proposer-derived policy digest is NOT independently trusted; reviewer must obtain it through a separate controlled channel'}
    except (ValueError,TypeError,KeyError,OverflowError,ArithmeticError,MemoryError,RecursionError,Unsupported,UnsupportedFP32) as exc:
        return {'status':'OPEN','reason':type(exc).__name__+': '+str(exc)[:160]}
