"""Separate-process allowlisted NumPy float32 dense network evaluator.

This is NOT ONNX Runtime, a hostile-binary parser, or an OS security sandbox.
"""
from __future__ import annotations
import json
import math
import struct
import sys

def execute(spec):
    import numpy as np
    if spec.get('schema')!='pcs-screened-dense-nn-v0.4':raise ValueError('invalid schema')
    nodes=spec['nodes'];weights=spec['weights'];vals=spec['values'];bound=spec['target']
    n=spec['input_width']
    if (not 1<=n<=16 or len(vals)!=n or not 1<=len(nodes)<=64 or
        sum(len(w['values']) for w in weights.values())>1024):raise ValueError('limits')
    env={spec['input']:np.asarray([vals],dtype=np.float32)}
    for name,w in weights.items():
        if name in env:raise ValueError('name collision')
        env[name]=np.asarray(w['values'],dtype=np.float32).reshape(w['shape'])
    with np.errstate(all='ignore'):
        for node in nodes:
            op,ins,out=node['op'],node['inputs'],node['out']
            if out in env or any(x not in env for x in ins):raise ValueError('bad graph')
            if op=='MatMul' and len(ins)==2:v=np.matmul(env[ins[0]],env[ins[1]])
            elif op=='Gemm' and len(ins)==3:v=np.add(np.matmul(env[ins[0]],env[ins[1]]),env[ins[2]])
            elif op=='Add' and len(ins)==2:v=np.add(env[ins[0]],env[ins[1]])
            elif op=='Relu' and len(ins)==1:v=np.maximum(env[ins[0]],np.float32(0))
            elif op=='Identity' and len(ins)==1:v=env[ins[0]].copy()
            else:raise ValueError('unsupported operator')
            env[out]=v
    final=env.get(spec['output'])
    if final is None or final.shape!=(1,spec['output_width']):raise ValueError('wrong output shape')
    out=[float(z) for z in final.ravel()]
    if any(not math.isfinite(v) for v in out):return {'status':'INDETERMINATE','reason':'nonfinite float32 output'}
    violation=[i for i,v in enumerate(out) if not(bound[0]<=v<=bound[1])]
    return {'status':'VIOLATION_REPRODUCED' if violation else 'CANDIDATE_NOT_REPRODUCED',
            'runtime':'numpy-float32-dense-reference','numpy':np.__version__,
            'outputs':out,'violating_indices':violation,
            'output_bits_hex':[struct.pack('<f',x).hex() for x in out],
            'scope':'Screened dense ONNX subset translated to NumPy operators; not ONNX Runtime equivalence'}

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('input budget exceeded')
        print(json.dumps(execute(json.loads(raw)),allow_nan=False,sort_keys=True))
    except Exception as exc:
        print(json.dumps({'status':'INDETERMINATE','reason':type(exc).__name__},sort_keys=True))
