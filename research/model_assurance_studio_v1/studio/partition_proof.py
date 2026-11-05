"""Finite, checkable subdivision of a restricted neural network input box.

This is a bounded *real arithmetic* certificate, not an IEEE-754, ONNX Runtime,
or Lean proof. Every leaf is recomputed using exact rational interval arithmetic;
checking the binary tree validates that its leaves cover the entire input box.
The result remains conditional on the restricted screened interpreter's semantics.
"""
from __future__ import annotations
from fractions import Fraction
from hashlib import sha256
import json
from .dense_nn import _budget, _execute_intervals, Unsupported

class Incomplete(Exception):
    pass

SCOPE='Exact-real screened operator semantics only; not floating-point runtime guarantee'


def assumptions(spec, policy):
    low=Fraction.from_float(float(policy['input_min']))
    high=Fraction.from_float(float(policy['input_max']))
    target=(Fraction.from_float(float(policy['output_min'])), Fraction.from_float(float(policy['output_max'])))
    return [(low,high) for _ in range(spec['input_width'])],target


def _enclosure(spec, box, target):
    b=_execute_intervals(spec,box)
    return b, all(a>=target[0] and c<=target[1] for a,c in b)


def make_certificate(spec, policy, *, max_leaves=64):
    """Return proof or scoped OPEN, never accept a partial cover as a proof."""
    if type(max_leaves) is not int or not 1<=max_leaves<=128:raise ValueError('bad partition budget')
    box,target=assumptions(spec,policy)
    count={'leaves':0, 'nodes':0, 'split_nodes':0}

    def build(box):
        count['nodes']+=1
        if count['nodes']>2*max_leaves-1:raise Incomplete('partition node budget exhausted')
        bounds,ok=_enclosure(spec,box,target)
        if ok:
            count['leaves']+=1
            if count['leaves']>max_leaves:raise Incomplete('partition leaf budget exhausted')
            return {'kind':'leaf','bounds':[[str(a),str(b)] for a,b in bounds]}
        axes=[i for i,(a,b) in enumerate(box) if a<b]
        if not axes:raise Incomplete('Exact input point violates output limits (candidate only)')
        # Largest actual span; ties use the earliest axis. The method is sound,
        # though not necessarily efficient for high-dimensional networks.
        axis=max(axes,key=lambda i:(box[i][1]-box[i][0],-i))
        split=_budget((box[axis][0]+box[axis][1])/2)
        if split in box[axis]:raise Incomplete('unable to subdivide bounded rational box')
        count['split_nodes']+=1
        left=list(box);right=list(box)
        left[axis]=(box[axis][0],split)
        right[axis]=(split,box[axis][1])
        return {'kind':'split','axis':axis,'at':str(split),
                'left':build(left),'right':build(right)}
    try:
        tree=build(box)
    except (Incomplete,Unsupported,OverflowError,ValueError) as e:
        return {'status':'OPEN','reason':str(e)[:200],**count,'budget':max_leaves}
    # Semantic commitment is distinct from the signed/unsigned source-artifact SHA.
    spec_sha256=sha256(json.dumps(spec,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    proof={'schema':'pcs-dense-real-partition-certificate-v0.5','screened_model_sha256':spec_sha256,'input_box':[[str(a),str(b)] for a,b in box],
           'target':list(map(str,target)),'tree':tree,'leaves':count['leaves'],
           'scope':SCOPE}
    proof['certificate_sha256']=sha256(json.dumps(proof,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'status':'PROVED_CONDITIONALLY','certificate':proof,'leaves':count['leaves'],
            'split_nodes':count['split_nodes'],'budget':max_leaves}


def verify_certificate(spec, policy, proof, *, max_leaves=128):
    """Recalculate every claimed leaf and check coverage from exact split endpoints.

    Verification trusts the interpreter and Python's integer/rational arithmetic;
    it is not a kernel check. Pathological, oversized or malformed proofs fail.
    """
    try:
        if not isinstance(proof,dict) or set(proof)!={'schema','screened_model_sha256','input_box','target','tree','leaves','scope','certificate_sha256'}:
            return False,'invalid certificate fields'
        claimed=proof['certificate_sha256']
        body={k:v for k,v in proof.items() if k!='certificate_sha256'}
        if claimed!=sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest():
            return False,'certificate digest mismatch'
        if proof['schema']!='pcs-dense-real-partition-certificate-v0.5':return False,'unknown certificate schema'
        if proof['scope']!=SCOPE:return False,'certificate scope was altered'
        expected_spec_hash=sha256(json.dumps(spec,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if proof['screened_model_sha256']!=expected_spec_hash:return False,'screened model semantics changed'
        box,target=assumptions(spec,policy)
        if proof['input_box']!=[[str(a),str(b)] for a,b in box] or proof['target']!=list(map(str,target)):
            return False,'input box/target mismatch'
        work=[(proof['tree'],box,1)]
        leaves=0;nodes=0
        while work:
            node,part,depth=work.pop()
            nodes+=1
            if nodes>2*max_leaves-1 or depth>2*max_leaves:return False,'certificate size limit'
            if not isinstance(node,dict):return False,'bad tree node'
            if node.get('kind')=='leaf':
                if set(node)!={'kind','bounds'}:return False,'unexpected leaf fields'
                bounds,ok=_enclosure(spec,part,target)
                if not ok or node['bounds']!=[[str(a),str(b)] for a,b in bounds]:
                    return False,'leaf not valid or enclosure changed'
                leaves+=1
                if leaves>max_leaves:return False,'too many leaves'
            elif node.get('kind')=='split':
                if set(node)!={'kind','axis','at','left','right'}:return False,'unexpected split fields'
                axis=node['axis']
                if type(axis) is not int or not 0<=axis<len(part):return False,'invalid axis'
                if not isinstance(node['at'],str) or len(node['at'])>200:return False,'bad split encoding'
                at=Fraction(node['at'])
                if at.numerator.bit_length()>512 or at.denominator.bit_length()>512:return False,'split rational budget'
                a,b=part[axis]
                if not (a<at<b):return False,'non-covering split'
                left=list(part);right=list(part)
                left[axis]=(a,at);right[axis]=(at,b)
                work.append((node['right'],right,depth+1))
                work.append((node['left'],left,depth+1))
            else:return False,'invalid node kind'
        if leaves!=proof['leaves']:return False,'leaf count mismatch'
        return True, f'{leaves} leaves recomputed; full input-box cover and scoped real-output bounds checked'
    except (Unsupported,TypeError,ValueError,KeyError,OverflowError,ZeroDivisionError,RecursionError) as e:
        return False,'invalid certificate: '+type(e).__name__
